#!/usr/bin/env Rscript

required_packages <- c("digest", "jsonlite", "zip")
missing_packages <- required_packages[!vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing_packages)) {
  stop("Install the required R packages first: ", paste(missing_packages, collapse = ", "), call. = FALSE)
}

script_arg <- grep("^--file=", commandArgs(), value = TRUE)
script_path <- if (length(script_arg)) sub("^--file=", "", script_arg[[1]]) else
  "packaging/build_gho_test_package.R"
repo_root <- normalizePath(file.path(dirname(script_path), ".."), winslash = "/", mustWork = TRUE)
default_version <- "0.1.4-test.3"
marketplace_name <- "dsir-gho-local-test"
runtime_directories <- c("scripts", "references", "agents")
fixed_zip_time <- as.POSIXct("2026-01-01 00:00:00", tz = "UTC")

abort <- function(..., call. = FALSE) stop(..., call. = call.)

join_relative <- function(root, relative) {
  parts <- strsplit(relative, "/", fixed = TRUE)[[1]]
  do.call(file.path, as.list(c(root, parts)))
}

git_output <- function(root, args) {
  output <- suppressWarnings(system2("git", c("-C", shQuote(root), args), stdout = TRUE, stderr = TRUE))
  status <- attr(output, "status")
  if (is.null(status)) status <- 0L
  if (status != 0L) abort("Git command failed: git ", paste(args, collapse = " "), "\n", paste(output, collapse = "\n"))
  output
}

repository_state <- function(root) {
  list(
    commit = git_output(root, c("rev-parse", "HEAD"))[[1]],
    dirty = length(git_output(root, c("status", "--porcelain", "--untracked-files=all"))) > 0L,
    tracked = git_output(root, "ls-files")
  )
}

safe_source_path <- function(root, relative, tracked) {
  if (length(relative) != 1L || !nzchar(relative) || grepl("(^/|(^|/)\\.\\.?(/|$)|\\\\|:)", relative)) {
    abort("Unsafe repository-relative path: ", relative)
  }
  if (!relative %in% tracked) abort("Required file is not tracked: ", relative)
  path <- join_relative(root, relative)
  if (!file.exists(path) || dir.exists(path)) abort("Required source file is missing: ", relative)
  resolved <- normalizePath(path, winslash = "/", mustWork = TRUE)
  prefix <- paste0(root, "/")
  if (!startsWith(resolved, prefix)) abort("Source path escapes the repository: ", relative)
  parts <- strsplit(relative, "/", fixed = TRUE)[[1]]
  path_parts <- vapply(seq_along(parts), function(i) {
    join_relative(root, paste(parts[seq_len(i)], collapse = "/"))
  }, character(1))
  links <- Sys.readlink(path_parts)
  if (any(!is.na(links) & nzchar(links))) abort("Symbolic-link source files are not accepted: ", relative)
  path
}

read_source <- function(root, relative, tracked) {
  path <- safe_source_path(root, relative, tracked)
  readBin(path, what = "raw", n = as.integer(file.info(path)$size))
}

sha256_raw <- function(value) digest::digest(value, algo = "sha256", serialize = FALSE)
sha256_file <- function(path) sha256_raw(readBin(path, "raw", n = file.info(path)$size))

json_raw <- function(value) charToRaw(paste0(jsonlite::toJSON(
  value, auto_unbox = TRUE, pretty = TRUE, null = "null", na = "null", digits = NA
), "\n"))

write_raw <- function(path, value) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  con <- file(path, open = "wb")
  on.exit(close(con), add = TRUE)
  writeBin(value, con)
}

select_runtime <- function(root, tracked) {
  selected <- c("dsir-gho/SKILL.md", "dsir-gho/LICENSE")
  for (relative in tracked) {
    parts <- strsplit(relative, "/", fixed = TRUE)[[1]]
    runtime_file <- length(parts) >= 3L && parts[[1]] == "dsir-gho" &&
      parts[[2]] %in% runtime_directories &&
      !any(startsWith(parts, ".") | parts %in% c("__pycache__", ".venv", "outputs")) &&
      tolower(tools::file_ext(relative)) %in% c("py", "md", "json", "yaml", "yml")
    if (runtime_file) selected <- c(selected, relative)
  }
  selected <- sort(unique(selected))
  required <- paste0("dsir-gho/", c("SKILL.md", "LICENSE", "scripts/cli.py",
    "scripts/gho_client.py", "scripts/xmart.py", "agents/openai.yaml"))
  if (!all(required %in% selected)) abort("One or more required GHO runtime files are not tracked.")
  setNames(lapply(sub("^dsir-gho/", "", selected), function(relative) {
    read_source(root, paste0("dsir-gho/", relative), tracked)
  }), sub("^dsir-gho/", "", selected))
}

validate_names <- function(files) {
  names <- names(files)
  if (is.null(names) || anyDuplicated(names) || any(!nzchar(names))) abort("Package file names must be unique and relative.")
  bad <- vapply(names, function(name) {
    parts <- strsplit(name, "/", fixed = TRUE)[[1]]
    startsWith(name, "/") || grepl("[\\\\:]", name) || any(parts %in% c("", ".", ".."))
  }, logical(1))
  if (any(bad)) abort("Unsafe package path: ", names[which(bad)[[1]]])
}

write_archive <- function(path, files) {
  validate_names(files)
  stage <- tempfile("dsir-gho-zip-")
  dir.create(stage)
  on.exit(unlink(stage, recursive = TRUE, force = TRUE), add = TRUE)
  temporary_archive <- tempfile("dsir-gho-package-", fileext = ".zip")
  on.exit(unlink(temporary_archive, force = TRUE), add = TRUE)
  staged_paths <- vapply(names(files), function(relative) join_relative(stage, relative), character(1))
  for (i in seq_along(files)) write_raw(staged_paths[[i]], files[[i]])
  Sys.setFileTime(unlist(staged_paths, use.names = FALSE), fixed_zip_time)
  zip::zipr(temporary_archive, files = sort(names(files)), root = stage,
    recurse = FALSE, compression_level = 9, include_directories = FALSE, mode = "mirror")
  listing <- zip::zip_list(temporary_archive)
  expected_names <- sort(names(files))
  if (anyDuplicated(listing$filename) || !identical(sort(listing$filename), expected_names)) {
    abort("ZIP member names differ from the build inputs: ", basename(path))
  }
  for (relative in sort(names(files))) {
    member <- unz(temporary_archive, relative, open = "rb")
    content <- readBin(member, what = "raw", n = as.integer(listing$uncompressed_size[match(relative, listing$filename)]))
    close(member)
    if (!identical(content, files[[relative]])) abort("Packaged bytes differ from source: ", relative)
  }
  if (!file.copy(temporary_archive, path, overwrite = FALSE)) abort("Could not copy validated archive to: ", path)
  archive_size <- file.info(temporary_archive)$size
  expected_hash <- sha256_file(temporary_archive)
  if (!identical(sha256_file(path), expected_hash)) abort("Copied archive differs from validated archive: ", basename(path))
  list(file = basename(path), bytes = unname(archive_size), sha256 = expected_hash)
}

same_path <- function(left, right) {
  if (.Platform$OS.type == "windows") identical(tolower(left), tolower(right)) else identical(left, right)
}

build_destination <- function(root, output_directory) {
  if (length(output_directory) != 1L || is.na(output_directory) || !nzchar(output_directory)) {
    abort("Supply one new output directory under dist.")
  }
  output_directory <- gsub("\\\\", "/", output_directory)
  output_input <- if (grepl("^([A-Za-z]:/|/)", output_directory)) output_directory else file.path(root, output_directory)
  parent_input <- dirname(output_input)
  boundary_error <- "Output must be a new direct child of the repository's ignored dist directory."
  if (!same_path(basename(parent_input), "dist") || basename(output_input) %in% c(".", "..")) abort(boundary_error)
  ancestor <- normalizePath(dirname(parent_input), winslash = "/", mustWork = TRUE)
  if (!same_path(ancestor, root)) abort(boundary_error)
  dist_root <- file.path(root, "dist")
  link <- Sys.readlink(dist_root)
  if (!is.na(link) && nzchar(link)) abort("The dist directory must not be a symbolic link or junction.")
  if (file.exists(dist_root) && !dir.exists(dist_root)) abort("The dist path is not a directory.")
  if (dir.exists(dist_root) && !same_path(normalizePath(dist_root, winslash = "/", mustWork = TRUE), dist_root)) {
    abort("The dist directory resolves outside its expected repository path.")
  }
  destination <- file.path(dist_root, basename(output_input))
  if (file.exists(destination)) abort("Refusing to overwrite an existing build directory: ", destination)
  destination
}

build_package <- function(output_directory, version = default_version, root = repo_root, allow_dirty = FALSE) {
  root <- normalizePath(root, winslash = "/", mustWork = TRUE)
  if (length(version) != 1L || !grepl("^[0-9]+\\.[0-9]+\\.[0-9]+-test\\.[0-9]+$", version)) {
    abort("Only local test versions are allowed, for example 0.1.4-test.3.")
  }
  destination <- build_destination(root, output_directory)

  state <- repository_state(root)
  if (state$dirty && !allow_dirty) abort("Commit and review source changes before an acceptance build. --allow-dirty is for development checks only.")
  runtime <- select_runtime(root, state$tracked)
  portable_path <- safe_source_path(root, "plugins/dsir-gho/plugin.json", state$tracked)
  compatibility_path <- safe_source_path(root, "plugins/dsir-gho/.codex-plugin/plugin.json", state$tracked)
  portable <- jsonlite::fromJSON(rawToChar(readBin(portable_path, "raw", n = file.info(portable_path)$size)), simplifyVector = FALSE)
  compatibility <- jsonlite::fromJSON(rawToChar(readBin(compatibility_path, "raw", n = file.info(compatibility_path)$size)), simplifyVector = FALSE)
  if (is.null(portable$extensions[["com.openai"]])) abort("Portable plugin manifest is missing its OpenAI interface.")
  interface <- portable$extensions[["com.openai"]]$interface
  identity_fields <- c("name", "version", "description", "author", "license", "keywords")
  if (!identical(portable$name, "dsir-gho") || !identical(compatibility$skills, "./skills/") ||
      !identical(portable$extensions[["com.openai"]]$interface, compatibility$interface) ||
      any(!vapply(identity_fields, function(field) identical(portable[[field]], compatibility[[field]]), logical(1)))) {
    abort("Plugin manifests disagree on identity, skill path or interface.")
  }
  portable$version <- version
  compatibility$version <- version
  interface$displayName <- "DSIR GHO Local Test"
  interface$longDescription <- paste(
    "Find WHO GHO indicators and retrieve public health statistics by country, region, year and verified dimensions.",
    "Export CSV and JSON with source details and completeness checks.",
    "Uses legacy by default and xMart only when explicitly selected; no automatic source fallback.",
    "Local test candidate; no public release is implied. Requires Python 3.10+ and permitted HTTPS access."
  )
  portable$extensions[["com.openai"]]$interface <- interface
  compatibility$interface <- interface

  runtime_hashes <- lapply(runtime, sha256_raw)
  metadata <- list(package_version = version, mode = "local_test", source_commit = state$commit,
    source_dirty = state$dirty, runtime_source = "dsir-gho/", default_backend = "legacy",
    automatic_fallback = FALSE, runtime_files = runtime_hashes, published = FALSE,
    marketplace_registered = FALSE)
  build_info <- json_raw(metadata)
  guide_path <- safe_source_path(root, "packaging/GHO_TESTING.md", state$tracked)
  plugin_readme <- safe_source_path(root, "plugins/dsir-gho/README.md", state$tracked)
  logo <- safe_source_path(root, "plugins/dsir-gho/assets/dsir-logo.jpg", state$tracked)
  plugin <- setNames(runtime, paste0("skills/dsir-gho/", names(runtime)))
  plugin <- c(plugin, list("plugin.json" = json_raw(portable),
    ".codex-plugin/plugin.json" = json_raw(compatibility), "assets/dsir-logo.jpg" = readBin(logo, "raw", n = file.info(logo)$size),
    "LICENSE" = runtime[["LICENSE"]], "README.md" = readBin(plugin_readme, "raw", n = file.info(plugin_readme)$size),
    "TESTING.md" = readBin(guide_path, "raw", n = file.info(guide_path)$size), "BUILD.json" = build_info))
  standalone_readme <- charToRaw(paste0("# DSIR GHO local test skill ", version,
    "\n\nThis standalone skill contains the same runtime as the local test plugin.\n",
    "Use one installation method at a time. See [TESTING.md](TESTING.md) for installation, acceptance checks and limitations.\n",
    "Source identity and runtime file hashes are in BUILD.json. No publication is performed.\n"))
  standalone <- c(runtime, list("README.md" = standalone_readme,
    "TESTING.md" = readBin(guide_path, "raw", n = file.info(guide_path)$size), "BUILD.json" = build_info))
  for (installer in c("install.ps1", "install.sh")) {
    relative <- paste0("dsir-gho/packaging/", installer)
    standalone[[paste0("packaging/", installer)]] <- read_source(root, relative, state$tracked)
  }
  validate_names(plugin)
  validate_names(standalone)

  if (!dir.create(destination, recursive = TRUE, showWarnings = FALSE)) abort("Could not create build directory: ", destination)
  plugin_with_root <- setNames(plugin, paste0("dsir-gho/", names(plugin)))
  standalone_with_root <- setNames(standalone, paste0("dsir-gho/", names(standalone)))
  plugin_artifact <- write_archive(file.path(destination, paste0("dsir-gho-plugin-", version, ".zip")),
    plugin_with_root)
  standalone_artifact <- write_archive(file.path(destination, paste0("dsir-gho-skill-", version, ".zip")), standalone_with_root)
  report <- c(metadata, list(artifacts = list(plugin_artifact, standalone_artifact),
    archive_validation = "all_entries_match_build_inputs", local_marketplace = "local-marketplace",
    marketplace_name = marketplace_name))
  write_raw(file.path(destination, "build-manifest.json"), json_raw(report))
  checksums <- paste0(vapply(report$artifacts, function(item) paste(item$sha256, "  ", item$file), character(1)), collapse = "\n")
  write_raw(file.path(destination, "SHA256SUMS.txt"), charToRaw(paste0(checksums, "\n")))
  write_raw(file.path(destination, "TESTING.md"), readBin(guide_path, "raw", n = file.info(guide_path)$size))
  marketplace_root <- file.path(destination, "local-marketplace")
  for (relative in names(plugin)) write_raw(join_relative(file.path(marketplace_root, "plugins", "dsir-gho"), relative), plugin[[relative]])
  catalog <- list(name = marketplace_name, interface = list(displayName = "DSIR GHO Local Test"),
    plugins = list(list(name = "dsir-gho", source = list(source = "local", path = "./plugins/dsir-gho"),
      policy = list(installation = "AVAILABLE", authentication = "ON_INSTALL"), category = "Data & Analytics")))
  write_raw(file.path(marketplace_root, ".agents", "plugins", "marketplace.json"), json_raw(catalog))
  report
}

parse_arguments <- function(args) {
  parsed <- list(output_directory = NULL, version = default_version, allow_dirty = FALSE)
  i <- 1L
  while (i <= length(args)) {
    value <- args[[i]]
    if (identical(value, "--allow-dirty")) {
      parsed$allow_dirty <- TRUE
      i <- i + 1L
    } else if (value %in% c("--output-dir", "--version")) {
      if (i == length(args)) abort("Missing value for ", value)
      if (value == "--output-dir") parsed$output_directory <- args[[i + 1L]] else parsed$version <- args[[i + 1L]]
      i <- i + 2L
    } else {
      abort("Unknown builder argument: ", value)
    }
  }
  if (is.null(parsed$output_directory)) abort("Supply --output-dir dist/<new-test-directory>.")
  parsed
}

if (sys.nframe() == 0L) {
  arguments <- parse_arguments(commandArgs(trailingOnly = TRUE))
  result <- build_package(arguments$output_directory, arguments$version, repo_root, arguments$allow_dirty)
  cat(jsonlite::toJSON(result, auto_unbox = TRUE, pretty = TRUE, null = "null"), "\n", sep = "")
}
