suppressPackageStartupMessages(library(zip))
source("scripts/check_release.R")
source("scripts/ghe_spec.R")
args <- commandArgs(TRUE)
if (length(args) != 2L) stop("Usage: build_release.R catalog-commit expected-workflow-run")
revision <- args[1]
run.id <- args[2]
stopifnot(!pilot, catalog.dir == "snapshots/phase6", grepl("^[0-9a-f]{40}$", revision), grepl("^[0-9]+$", run.id))
destination <- "releases/phase6"
dir.create(destination, recursive = TRUE, showWarnings = FALSE)
settings <- read_json("config/phase6-plugin.json")
baseline <- read_json("config/release-baseline-0.5.1.json")
path <- file.path(catalog.dir, "catalog.json")
catalog <- read_json(path)
entries <- Filter(function(e) identical(e$id, snapshot.id), catalog$indicators)
stopifnot(length(entries) == 1L)
entry <- entries[[1]]
m <- read_json(file.path(out, "manifest.json"))
p <- read_json(file.path(out, "provenance.json"))
stopifnot(identical(scope, "regional"), identical(m$scope, scope), identical(entry$scope, scope),
          identical(p$run_id, run.id), identical(entry$run_id, run.id), identical(m$run_id, run.id),
          identical(m$retrieved_at, p$retrieved_at), identical(entry$retrieved_at, p$retrieved_at),
          p$retrieved_at > baseline$retrieved_at, run.id != baseline$run_id,
          length(p$sources) > 0L, all(vapply(p$sources, function(s) {
              identical(s$retrieval_status, "live") && identical(s$cache_hit, FALSE) && isTRUE(s$complete)
          }, logical(1))))
record <- list(plugin_name = settings$name, plugin_version = settings$version,
               snapshot = snapshot.id, scope = scope, run_id = run.id, retrieved_at = p$retrieved_at,
               catalog = list(url = paste0(raw.base, revision, "/", path), sha256 = sha256_hex(read_bytes(path))),
               manifest = list(url = entry$manifest$url, sha256 = entry$manifest$sha256))
save_report(record, file.path(destination, "release.json"))

# Generate the dated references from the release record. Keep the accepted query instructions.
template.root <- file.path("plugins", baseline$plugin_name)
meta <- read_json(file.path(template.root, "plugin.json"))
meta$name <- record$plugin_name
meta$version <- record$plugin_version
meta$extensions$com.openai$interface$displayName <- settings$display_name
stopifnot(nchar(meta$extensions$com.openai$interface$shortDescription) <= 30L)
lines <- readLines(file.path(template.root, "skills", baseline$plugin_name, "SKILL.md"), encoding = "UTF-8")
section <- grep(baseline$catalog$url, lines, fixed = TRUE)
stopifnot(length(section) == 1L, sum(lines == paste0("name: ", baseline$plugin_name)) == 1L)
lines[lines == paste0("name: ", baseline$plugin_name)] <- paste0("name: ", record$plugin_name)
lines[section] <- sprintf(paste(
  "For release %s open the [fixed regional catalog](%s). Resolve each requested indicator through its own pinned manifest.",
  "The GHE entry for this release is `%s`, scope `%s`, run `%s`.",
  "Open the [fixed regional GHE manifest](%s) and verify its identity and retrieval time (%s) before reporting coverage or estimates.",
  "Read the country rows for this release. Cite the exact catalog, manifest and country CSV URLs used so the answer is reproducible.",
  "If the release identity cannot be verified, state which file could not be verified and withhold the affected claims.",
  "For GHO and UN SDG, use their own run IDs, dates, units and manifests from this same catalog."),
  record$plugin_version, record$catalog$url, record$snapshot, record$scope, record$run_id, record$manifest$url, record$retrieved_at)
root <- tempfile("candidate-package-")
skill.path <- paste0("skills/", record$plugin_name, "/SKILL.md")
dir.create(file.path(root, dirname(skill.path)), recursive = TRUE)
save_report(meta, file.path(root, "plugin.json"))
writeLines(lines, file.path(root, skill.path), useBytes = TRUE)
archive <- file.path(normalizePath(destination), paste0(record$plugin_name, "-", record$plugin_version, ".zip"))
files <- c("plugin.json", skill.path)
zipr(archive, files, root = root, include_directories = FALSE, mode = "mirror")
stopifnot(setequal(utils::unzip(archive, list = TRUE)$Name, files))
cat("Built", basename(archive), "for run", record$run_id, "\n")
