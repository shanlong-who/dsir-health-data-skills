#!/usr/bin/env Rscript
# Reuse audited GHO archive/path helpers without altering the GHO build.
script.arg <- grep("^--file=", commandArgs(), value = TRUE)
script.path <- if (length(script.arg)) sub("^--file=", "", script.arg[[1]]) else
  "packaging/build_data_test_package.R"
data.repo.root <- normalizePath(file.path(dirname(script.path), ".."), winslash = "/", mustWork = TRUE)
helpers <- new.env(parent = globalenv())
sys.source(file.path(data.repo.root, "packaging/build_gho_test_package.R"), envir = helpers)

select_data_runtime <- function(root, skill, tracked) {
  selected <- c(paste0(skill, "/SKILL.md"), paste0(skill, "/LICENSE"))
  for (relative in tracked) {
    parts <- strsplit(relative, "/", fixed = TRUE)[[1]]
    if (length(parts) >= 3L && parts[[1]] == skill &&
        parts[[2]] %in% c("scripts", "references", "agents") &&
        !any(startsWith(parts, ".") | parts %in% c("__pycache__", ".venv", "outputs")) &&
        tolower(tools::file_ext(relative)) %in% c("py", "md", "json", "yaml", "yml")) {
      selected <- c(selected, relative)
    }
  }
  selected <- sort(unique(selected))
  required <- paste0(skill, "/", c("SKILL.md", "LICENSE", "scripts/cli.py", "agents/openai.yaml",
    "references/metadata/who_countries.json", "references/metadata/provenance.json",
    "references/result_presentation.md",
    if (skill == "dsir-ghe") c("scripts/ghe_client.py", "scripts/transport.py", "references/metadata/measures.json")
    else "scripts/sdg_client.py"))
  if (!all(required %in% selected)) helpers$abort("Required runtime inputs are not tracked.")
  setNames(lapply(selected, function(path) helpers$read_source(root, path, tracked)),
    substring(selected, nchar(skill) + 2L))
}

build_data_package <- function(skill, output_directory, version = NULL,
                               root = data.repo.root, allow_dirty = FALSE) {
  if (!identical(skill, "dsir-sdg") && !identical(skill, "dsir-ghe")) helpers$abort("Select dsir-sdg or dsir-ghe.")
  if (is.null(version)) version <- if (skill == "dsir-sdg") "0.1.1-test.1" else "0.1.0-test.1"
  if (length(version) != 1L || !grepl("^[0-9]+\\.[0-9]+\\.[0-9]+-test\\.[0-9]+$", version)) {
    helpers$abort("Only local test versions are allowed.")
  }
  root <- normalizePath(root, winslash = "/", mustWork = TRUE)
  destination <- helpers$build_destination(root, output_directory)
  state <- helpers$repository_state(root)
  if (state$dirty && !allow_dirty) helpers$abort("Commit and review source before an acceptance build.")
  runtime <- select_data_runtime(root, skill, state$tracked)
  read_input <- function(path) helpers$read_source(root, path, state$tracked)
  portable <- jsonlite::fromJSON(rawToChar(read_input(paste0("plugins/", skill, "/plugin.json"))), simplifyVector = FALSE)
  compatibility <- jsonlite::fromJSON(rawToChar(read_input(paste0("plugins/", skill, "/.codex-plugin/plugin.json"))), simplifyVector = FALSE)
  interface <- portable$extensions[["com.openai"]]$interface
  identity <- c("name", "version", "description", "author", "license", "keywords")
  if (is.null(interface) || !identical(portable$name, skill) ||
      !identical(compatibility$skills, "./skills/") || !identical(interface, compatibility$interface) ||
      any(!vapply(identity, function(key) identical(portable[[key]], compatibility[[key]]), logical(1)))) {
    helpers$abort("Plugin manifests disagree on identity or interface.")
  }
  label <- paste("DSIR", toupper(sub("dsir-", "", skill)), "Local Test")
  portable$version <- compatibility$version <- version
  interface$displayName <- label
  interface$longDescription <- paste(interface$longDescription,
    "Local test candidate only. Use the host-supplied Python runtime; end users do not install R, DSIR or packages.")
  portable$extensions[["com.openai"]]$interface <- compatibility$interface <- interface
  guide <- read_input(paste0("packaging/", toupper(sub("dsir-", "", skill)), "_TESTING.md"))
  metadata <- list(package_version = version, mode = "local_test", source_commit = state$commit,
    source_dirty = state$dirty, runtime_source = paste0(skill, "/"),
    runtime_files = lapply(runtime, helpers$sha256_raw), host_supplied_python = "3.10+",
    r_required = FALSE, api_key_required = FALSE, automatic_fallback = FALSE,
    published = FALSE, marketplace_registered = FALSE)
  build.info <- helpers$json_raw(metadata)
  plugin <- setNames(runtime, paste0("skills/", skill, "/", names(runtime)))
  plugin <- c(plugin, list("plugin.json" = helpers$json_raw(portable),
    ".codex-plugin/plugin.json" = helpers$json_raw(compatibility),
    "assets/dsir-logo.jpg" = read_input("packaging/assets/dsir-logo.jpg"),
    "LICENSE" = runtime[["LICENSE"]], "README.md" = read_input(paste0("plugins/", skill, "/README.md")),
    "TESTING.md" = guide, "BUILD.json" = build.info))
  standalone <- c(runtime, list("README.md" = charToRaw(paste0("# ", label, "\n\n",
    "Same runtime as the plugin. Read TESTING.md before choosing one installation method.\n",
    "BUILD.json identifies the source commit and runtime hashes. No publication is performed.\n")),
    "TESTING.md" = guide, "BUILD.json" = build.info))
  helpers$validate_names(plugin)
  helpers$validate_names(standalone)
  local.paths <- file.path(destination, "local-marketplace", "plugins", skill, names(plugin))
  if (.Platform$OS.type == "windows" && any(nchar(local.paths) >= 260L)) {
    helpers$abort("Windows output paths are too long. Use a shorter checkout or build directory name.")
  }
  if (!dir.create(destination, recursive = TRUE, showWarnings = FALSE)) helpers$abort("Cannot create build directory.")
  artifacts <- lapply(c("plugin", "skill"), function(type) {
    files <- if (type == "plugin") plugin else standalone
    helpers$write_archive(file.path(destination, paste0(skill, "-", type, "-", version, ".zip")),
      setNames(files, paste0(skill, "/", names(files))))
  })
  marketplace.name <- paste0(skill, "-local-test")
  report <- c(metadata, list(artifacts = artifacts, archive_validation = "all_entries_match_build_inputs",
    local_marketplace = "local-marketplace", marketplace_name = marketplace.name))
  helpers$write_raw(file.path(destination, "build-manifest.json"), helpers$json_raw(report))
  helpers$write_raw(file.path(destination, "SHA256SUMS.txt"), charToRaw(paste0(
    paste(vapply(artifacts, function(item) paste(item$sha256, " ", item$file), character(1)), collapse = "\n"), "\n")))
  helpers$write_raw(file.path(destination, "TESTING.md"), guide)
  marketplace.root <- file.path(destination, "local-marketplace")
  for (relative in names(plugin)) helpers$write_raw(
    helpers$join_relative(file.path(marketplace.root, "plugins", skill), relative), plugin[[relative]])
  catalogue <- list(name = marketplace.name, interface = list(displayName = label),
    plugins = list(list(name = skill, source = list(source = "local", path = paste0("./plugins/", skill)),
      policy = list(installation = "AVAILABLE", authentication = "ON_INSTALL"), category = "Data & Analytics")))
  helpers$write_raw(file.path(marketplace.root, ".agents/plugins/marketplace.json"), helpers$json_raw(catalogue))
  report
}

parse_data_arguments <- function(args) {
  out <- list(skill = NULL, output_directory = NULL, version = NULL, allow_dirty = FALSE)
  i <- 1L
  while (i <= length(args)) {
    if (args[[i]] == "--allow-dirty") {
      out$allow_dirty <- TRUE
      i <- i + 1L
    } else if (args[[i]] %in% c("--skill", "--output-dir", "--version") && i < length(args)) {
      key <- switch(args[[i]], "--skill" = "skill", "--output-dir" = "output_directory", "--version" = "version")
      out[[key]] <- args[[i + 1L]]
      i <- i + 2L
    } else helpers$abort("Unknown or incomplete builder argument: ", args[[i]])
  }
  if (is.null(out$skill) || is.null(out$output_directory)) helpers$abort("Supply --skill and --output-dir.")
  out
}

if (sys.nframe() == 0L) {
  result <- do.call(build_data_package, parse_data_arguments(commandArgs(trailingOnly = TRUE)))
  cat(jsonlite::toJSON(result, auto_unbox = TRUE, pretty = TRUE, null = "null"), "\n")
}
