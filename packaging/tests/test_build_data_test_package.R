library(testthat)

builder <- new.env(parent = globalenv())
repository.root <- normalizePath(test_path("..", ".."), winslash = "/", mustWork = TRUE)
withr::with_dir(repository.root, sys.source("packaging/build_data_test_package.R", envir = builder))
h <- builder$helpers

data_fixture <- function() {
  root <- tempfile("data-package-test-")
  dir.create(root)
  root <- normalizePath(root, winslash = "/", mustWork = TRUE)
  boundary <- paste0(normalizePath(tempdir(), winslash = "/", mustWork = TRUE), "/")
  stopifnot(startsWith(root, boundary))
  withr::defer(unlink(root, recursive = TRUE), envir = parent.frame())
  files <- list(".gitignore" = charToRaw("/dist/\n.env\n__pycache__/\n"),
    "packaging/assets/dsir-logo.jpg" = as.raw(c(1, 2, 255)))
  for (skill in c("dsir-sdg", "dsir-ghe")) {
    paths <- c("SKILL.md", "LICENSE", "scripts/cli.py", "agents/openai.yaml",
      "references/metadata/who_countries.json", "references/metadata/provenance.json",
      "references/result_presentation.md",
      if (skill == "dsir-ghe") c("scripts/ghe_client.py", "scripts/transport.py", "references/metadata/measures.json")
      else "scripts/sdg_client.py")
    for (path in paths) files[[paste0(skill, "/", path)]] <- charToRaw(paste("canonical", skill, path))
    for (path in c("plugin.json", ".codex-plugin/plugin.json", "README.md")) {
      source <- file.path(repository.root, "plugins", skill, path)
      files[[paste0("plugins/", skill, "/", path)]] <- readBin(source, "raw", n = file.info(source)$size)
    }
    files[[paste0("packaging/", toupper(sub("dsir-", "", skill)), "_TESTING.md")]] <- charToRaw("acceptance guide")
    files[[paste0("plugins/", skill, "/skills/", skill, "/scripts/cli.py")]] <- charToRaw("STALE")
    files[[paste0(skill, "/reports/raw.json")]] <- charToRaw("not a runtime input")
    files[[paste0(skill, "/evals/verify.R")]] <- charToRaw("not a runtime input")
  }
  for (path in names(files)) h$write_raw(file.path(root, path), files[[path]])
  h$git_output(root, c("init", "--quiet"))
  h$git_output(root, c("config", "core.autocrlf", "false"))
  h$git_output(root, c("add", "."))
  h$git_output(root, c("-c", "user.name=DSIR-tests", "-c", "user.email=tests@example.invalid",
    "commit", "--quiet", "-m", shQuote("Create synthetic packaging fixture")))
  h$write_raw(file.path(root, "dsir-ghe/scripts/.env"), charToRaw("SYNTHETIC_SECRET"))
  root
}

member_bytes <- function(path, name) {
  listing <- zip::zip_list(path)
  connection <- unz(path, name, "rb")
  on.exit(close(connection))
  readBin(connection, "raw", n = listing$uncompressed_size[match(name, listing$filename)])
}

test_that("both data packages use canonical bytes and separate identities", {
  root <- data_fixture()
  before <- h$repository_state(root)
  for (skill in c("dsir-sdg", "dsir-ghe")) {
    report <- builder$build_data_package(skill, paste0("dist/", skill), root = root)
    expect_false(report$source_dirty)
    expect_identical(report$source_commit, before$commit)
    expect_false(report$r_required)
    expect_false(report$automatic_fallback)
    expect_identical(report$runtime_source, paste0(skill, "/"))
    output <- file.path(root, "dist", skill)
    plugin <- file.path(output, report$artifacts[[1]]$file)
    standalone <- file.path(output, report$artifacts[[2]]$file)
    for (file in names(report$runtime_files)) {
      a <- member_bytes(plugin, paste0(skill, "/skills/", skill, "/", file))
      b <- member_bytes(standalone, paste0(skill, "/", file))
      expect_identical(a, b)
      expect_identical(h$sha256_raw(a), report$runtime_files[[file]])
    }
    entries <- zip::zip_list(plugin)$filename
    expect_false(any(grepl("(evals|reports|\\.env|__pycache__)", entries)))
    manifest <- jsonlite::fromJSON(rawToChar(member_bytes(plugin, paste0(skill, "/plugin.json"))))
    expect_identical(manifest$name, skill)
    expect_identical(manifest$version, report$package_version)
    expect_identical(h$sha256_file(plugin), report$artifacts[[1]]$sha256)
    repeat.build <- builder$build_data_package(skill, paste0("dist/", skill, "-repeat"), root = root)
    expect_identical(report$artifacts, repeat.build$artifacts)
    expect_error(builder$build_data_package(skill, paste0("dist/", skill), root = root), "overwrite")
  }
  expect_identical(h$repository_state(root), before)
})

test_that("new builder rejects unsafe, unreviewed or mismatched inputs", {
  root <- data_fixture()
  expect_error(builder$build_data_package("dsir-gho", "dist/a", root = root), "Select")
  expect_error(builder$build_data_package("dsir-ghe", "dist/a", version = "1.0.0", root = root), "test")
  expect_error(builder$build_data_package("dsir-ghe", "../outside", root = root), "direct child")
  expect_error(builder$build_data_package("dsir-ghe", "dist/a/b", root = root), "direct child")
  if (.Platform$OS.type == "windows") expect_error(builder$build_data_package(
    "dsir-ghe", paste0("dist/", strrep("x", 200)), root = root), "too long")
  h$write_raw(file.path(root, "dsir-ghe/SKILL.md"), charToRaw("unreviewed change"))
  expect_error(builder$build_data_package("dsir-ghe", "dist/dirty", root = root), "Commit and review")
  expect_false(dir.exists(file.path(root, "dist/dirty")))
  dev <- builder$build_data_package("dsir-ghe", "dist/development", root = root, allow_dirty = TRUE)
  expect_true(dev$source_dirty)
  h$write_raw(file.path(root, "plugins/dsir-ghe/.codex-plugin/plugin.json"), h$json_raw(list(name = "wrong")))
  expect_error(builder$build_data_package("dsir-ghe", "dist/mismatch", root = root, allow_dirty = TRUE), "disagree")
  expect_false(dir.exists(file.path(root, "dist/mismatch")))
})
