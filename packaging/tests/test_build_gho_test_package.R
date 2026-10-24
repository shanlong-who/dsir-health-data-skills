# Run from the repository root:
# Rscript -e 'testthat::test_file("packaging/tests/test_build_gho_test_package.R")'
library(testthat)

builder <- new.env(parent = globalenv())
repository.root <- normalizePath(test_path("..", ".."), winslash = "/", mustWork = TRUE)
withr::with_dir(repository.root, sys.source("packaging/build_gho_test_package.R", envir = builder))

new_fixture <- function() {
  fixture.base <- tempfile("gho-packaging-test-")
  dir.create(fixture.base)
  fixture.base <- normalizePath(fixture.base, winslash = "/", mustWork = TRUE)
  temp.root <- normalizePath(tempdir(), winslash = "/", mustWork = TRUE)
  stopifnot(startsWith(fixture.base, paste0(temp.root, "/")))
  withr::defer(unlink(fixture.base, recursive = TRUE), envir = parent.frame())
  root <- file.path(fixture.base, "repository")
  dir.create(root)
  identity <- list(name = "dsir-gho", version = "0.1.4-test.1", description = "Synthetic fixture",
    author = list(name = "Packaging tests"), license = "MIT", keywords = list("WHO"))
  interface <- list(displayName = "GHO", longDescription = "Synthetic fixture")
  files <- list(
    ".gitignore" = charToRaw("/dist/\n**/__pycache__/\n.env\n"),
    "dsir-gho/SKILL.md" = charToRaw("current skill"),
    "dsir-gho/LICENSE" = charToRaw("MIT"),
    "dsir-gho/scripts/cli.py" = charToRaw("current repaired client"),
    "dsir-gho/scripts/gho_client.py" = charToRaw("legacy default"),
    "dsir-gho/scripts/xmart.py" = charToRaw("explicit xmart"),
    "dsir-gho/agents/openai.yaml" = charToRaw("current agent"),
    "dsir-gho/references/schema.md" = charToRaw("schema"),
    "dsir-gho/packaging/install.ps1" = charToRaw("installer"),
    "dsir-gho/packaging/install.sh" = charToRaw("installer"),
    "plugins/dsir-gho/plugin.json" = builder$json_raw(c(identity,
      list(extensions = list("com.openai" = list(interface = interface))))),
    "plugins/dsir-gho/.codex-plugin/plugin.json" = builder$json_raw(c(identity,
      list(skills = "./skills/", interface = interface))),
    "packaging/assets/dsir-logo.png" = as.raw(c(1, 2, 255)),
    "plugins/dsir-gho/README.md" = charToRaw("readme"),
    "plugins/dsir-gho/skills/dsir-gho/scripts/cli.py" = charToRaw("STALE COPY"),
    "packaging/GHO_TESTING.md" = charToRaw("guide"),
    "dsir-gho/tests/fixture.json" = charToRaw("observations"),
    "dsir-gho/reports/raw.json" = charToRaw("observations")
  )
  for (name in names(files)) builder$write_raw(file.path(root, name), files[[name]])
  builder$git_output(root, c("init", "--quiet"))
  builder$git_output(root, c("config", "core.autocrlf", "false"))
  builder$git_output(root, c("add", "."))
  builder$git_output(root, c("-c", "user.name=DSIR-tests", "-c", "user.email=tests@example.invalid",
    "commit", "--quiet", "-m", shQuote("Create synthetic packaging fixture")))
  builder$write_raw(file.path(root, "dsir-gho/scripts/__pycache__/ignored.pyc"), charToRaw("cache"))
  builder$write_raw(file.path(root, "dsir-gho/scripts/.env"), charToRaw("SYNTHETIC_SECRET"))
  root
}

read_member <- function(path, member) {
  listing <- zip::zip_list(path)
  connection <- unz(path, member, open = "rb")
  on.exit(close(connection))
  readBin(connection, "raw", n = listing$uncompressed_size[match(member, listing$filename)])
}

test_that("a fresh checkout builds matching artifacts from tracked runtime", {
  root <- new_fixture()
  before <- builder$repository_state(root)
  expect_false(dir.exists(file.path(root, "dist")))
  report <- builder$build_package("dist/first", root = root)
  expect_false(report$source_dirty)
  expect_identical(report$source_commit, before$commit)
  expect_identical(builder$repository_state(root), before)
  output <- file.path(root, "dist/first")
  plugin <- file.path(output, report$artifacts[[1]]$file)
  skill <- file.path(output, report$artifacts[[2]]$file)
  expect_identical(rawToChar(read_member(plugin, "dsir-gho/skills/dsir-gho/scripts/cli.py")), "current repaired client")
  expect_false(any(grepl("tests/|reports/|__pycache__|\\.env", zip::zip_list(plugin)$filename)))
  for (relative in names(report$runtime_files)) {
    content <- read_member(plugin, paste0("dsir-gho/skills/dsir-gho/", relative))
    expect_identical(builder$sha256_raw(content), report$runtime_files[[relative]])
    expect_identical(content, read_member(skill, paste0("dsir-gho/", relative)))
  }
  for (member in zip::zip_list(plugin)$filename) {
    path <- file.path(output, "local-marketplace/plugins", member)
    expect_identical(read_member(plugin, member), readBin(path, "raw", n = file.info(path)$size))
  }
  portable <- jsonlite::fromJSON(rawToChar(read_member(plugin, "dsir-gho/plugin.json")))
  compatibility <- jsonlite::fromJSON(rawToChar(read_member(plugin, "dsir-gho/.codex-plugin/plugin.json")))
  expect_identical(portable$version, builder$default_version)
  expect_identical(compatibility$version, builder$default_version)
  expect_identical(portable$extensions[["com.openai"]]$interface, compatibility$interface)
  expect_identical(compatibility$skills, "./skills/")
  second <- builder$build_package("dist/second", root = root)
  expect_identical(report$artifacts, second$artifacts)
  for (artifact in report$artifacts) expect_identical(builder$sha256_file(file.path(output, artifact$file)), artifact$sha256)
})

test_that("output cannot overwrite existing files or escape dist", {
  root <- new_fixture()
  invalid <- c("new-build", "plugins/new-build", "dist/nested/new-build", "dist/..",
    file.path(dirname(root), "dist/outside"))
  if (.Platform$OS.type != "windows") invalid <- c(invalid, "DIST/new-build")
  for (path in invalid) expect_error(builder$build_package(path, root = root), "new direct child")
  expect_false(dir.exists(file.path(root, "dist")))
  sentinel <- file.path(root, "dist/existing/keep.txt")
  builder$write_raw(sentinel, charToRaw("keep"))
  expect_error(builder$build_package("dist/existing", root = root), "Refusing to overwrite")
  expect_identical(readBin(sentinel, "raw", n = 4L), charToRaw("keep"))
  expect_identical(list.files(dirname(sentinel)), "keep.txt")
})

test_that("linked dist directories are rejected before writing", {
  root <- new_fixture()
  target <- file.path(dirname(root), "outside")
  dir.create(target)
  link <- file.path(root, "dist")
  linked <- if (.Platform$OS.type == "windows") Sys.junction(target, link) else file.symlink(target, link)
  skip_if_not(linked, "Directory links are unavailable on this host")
  expect_error(builder$build_package("dist/escape", root = root), "link|junction|outside")
  expect_length(list.files(target, all.files = TRUE, no.. = TRUE), 0L)
})

test_that("dirty source requires an explicit development build", {
  root <- new_fixture()
  builder$write_raw(file.path(root, "unexpected.txt"), charToRaw("unreviewed"))
  expect_error(builder$build_package("dist/rejected", root = root), "Commit and review")
  expect_false(dir.exists(file.path(root, "dist")))
  report <- builder$build_package("dist/development", root = root, allow_dirty = TRUE)
  expect_true(report$source_dirty)
})

test_that("invalid source and manifest mismatch fail without creating a package", {
  root <- new_fixture()
  manifest <- file.path(root, "plugins/dsir-gho/.codex-plugin/plugin.json")
  value <- jsonlite::fromJSON(manifest, simplifyVector = FALSE)
  value$version <- "unexpected"
  builder$write_raw(manifest, builder$json_raw(value))
  expect_error(builder$build_package("dist/mismatch", root = root, allow_dirty = TRUE), "manifests disagree")
  expect_false(dir.exists(file.path(root, "dist")))
  expect_error(builder$safe_source_path(root, "../outside", character()), "Unsafe")
  expect_error(builder$safe_source_path(root, "dsir-gho/scripts/not-tracked.py", character()), "not tracked")
  expect_error(builder$validate_names(setNames(list(charToRaw("x")), "../escape")), "Unsafe")
})

test_that("only test versions and explicit CLI arguments are accepted", {
  root <- new_fixture()
  for (version in c("0.1.4", "../escape", "0.1.4-test.3/extra")) {
    expect_error(builder$build_package("dist/rejected", version = version, root = root), "Only local test")
  }
  expect_false(dir.exists(file.path(root, "dist")))
  expect_error(builder$parse_arguments(character()), "Supply --output-dir")
  expect_error(builder$parse_arguments("--version"), "Missing value")
  expect_error(builder$parse_arguments("--unknown"), "Unknown")
})
