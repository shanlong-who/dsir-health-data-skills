# Assemble checksums and an explicit validation gate for the local maintenance candidate.
library(jsonlite)
library(digest)

dist_dir <- "dist"
report_dir <- "dsir-gho/reports/xmart-20261007"
runtime_files <- c("dsir-gho-0.1.1.zip", "dsir-gho-plugin-0.1.2.zip",
                   "dsir-sdg-0.1.0.zip", "dsir-sdg-plugin-0.1.0.zip")
source_file <- "dsir-gho-0.1.1-source.zip"
paths <- file.path(dist_dir, c(runtime_files, source_file))
if (any(!file.exists(paths))) stop("All candidate and unchanged SDG archives must be present in dist/.")

sha256 <- function(path) digest::digest(file = path, algo = "sha256", serialize = FALSE)
assets <- lapply(paths, function(path) list(
  file = basename(path), bytes = unname(file.info(path)$size), sha256 = sha256(path)
))
names(assets) <- basename(paths)
expected_sdg <- c(
  "dsir-sdg-0.1.0.zip" = "52417049da266941e8315ee22bdb48e5d2f2a5cb9393c4b5ef9eddaf000f2315",
  "dsir-sdg-plugin-0.1.0.zip" = "8e1f0755ea5e7acad6748b5bf37ec3217b153948df94958ce75d09523d8992c4"
)
for (file in names(expected_sdg)) {
  if (!identical(assets[[file]]$sha256, expected_sdg[[file]])) stop("Unchanged SDG artifact hash differs: ", file)
}
for (file in runtime_files) {
  entries <- utils::unzip(file.path(dist_dir, file), list = TRUE)$Name
  if (any(grepl("(^|/)(evals|reports|tests)/|\\.R$|__pycache__", entries))) {
    stop("Runtime archive contains maintainer evidence or R files: ", file)
  }
}

read_entry <- function(archive, entry) {
  entry_size <- utils::unzip(archive, list = TRUE)$Length[
    utils::unzip(archive, list = TRUE)$Name == entry
  ]
  if (length(entry_size) != 1) stop("Missing or duplicate archive entry: ", entry)
  stream <- unz(archive, entry, open = "rb")
  on.exit(close(stream))
  readBin(stream, what = "raw", n = entry_size)
}
read_json_entry <- function(archive, entry) {
  jsonlite::fromJSON(rawToChar(read_entry(archive, entry)), simplifyVector = FALSE)
}
skill_archive <- file.path(dist_dir, "dsir-gho-0.1.1.zip")
plugin_archive <- file.path(dist_dir, "dsir-gho-plugin-0.1.2.zip")
plugin <- read_json_entry(plugin_archive, "dsir-gho/plugin.json")
compatibility <- read_json_entry(plugin_archive, "dsir-gho/.codex-plugin/plugin.json")
if (!identical(plugin$version, "0.1.2") || !identical(compatibility$version, "0.1.2") ||
    !identical(plugin$author$name, "Shanlong Ding") || !identical(compatibility$skills, "./skills/")) {
  stop("Plugin identity, version or skill path differs from the candidate.")
}
skill_entries <- utils::unzip(skill_archive, list = TRUE)$Name
copied_entries <- skill_entries[grepl("^dsir-gho/(scripts/|references/|agents/|SKILL[.]md$|LICENSE$)", skill_entries)]
for (entry in copied_entries) {
  plugin_entry <- sub("^dsir-gho/", "dsir-gho/skills/dsir-gho/", entry)
  if (!identical(read_entry(skill_archive, entry), read_entry(plugin_archive, plugin_entry))) {
    stop("Plugin skill file differs from standalone runtime: ", entry)
  }
}
reference <- read_json_entry(plugin_archive, "dsir-gho/skills/dsir-gho/references/metadata/dsir_reference.json")
if (!identical(reference$source_commit, "885464b1fade2f8b6d02dde93f9080e4b3f4f2a5")) {
  stop("Packaged GHO reference does not match the pinned DSIR commit.")
}
parity <- jsonlite::fromJSON(file.path(report_dir, "parity-live/parity_results.json"), simplifyVector = FALSE)
live <- jsonlite::fromJSON(file.path(report_dir, "live_checks_final.json"), simplifyVector = FALSE)
package <- jsonlite::fromJSON(file.path(report_dir, "package_validation.json"), simplifyVector = FALSE)
release_ready <- isTRUE(parity$passed) && isTRUE(live$passed) && isTRUE(package$live_passed)
writeLines(vapply(assets[runtime_files], function(asset) paste(asset$sha256, asset$file, sep = "  "), character(1)),
           file.path(dist_dir, "SHA256SUMS.txt"), useBytes = TRUE)
writeLines(vapply(assets, function(asset) paste(asset$sha256, asset$file, sep = "  "), character(1)),
           file.path(dist_dir, "SOURCE_AND_RUNTIME_SHA256SUMS.txt"), useBytes = TRUE)
manifest <- list(
  candidate_tag = "v2026.10.07", generated_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
  status = if (release_ready) "validated_candidate" else "candidate_pending_live_validation",
  published = FALSE, release_ready = release_ready, author = "Shanlong Ding", owner = "shanlong-who",
  gho_plugin_version = "0.1.2", gho_skill_version = "0.1.1", sdg_version = "0.1.0",
  dsir_gho_reference = "885464b1fade2f8b6d02dde93f9080e4b3f4f2a5",
  independent_live_parity_passed = isTRUE(parity$live_parity_passed),
  common_input_parity_passed = isTRUE(parity$common_input_passed),
  fresh_live_counts = live$counts, extracted_runtime_live_passed = isTRUE(package$live_passed),
  plugin_manifests_verified = TRUE, plugin_runtime_files_verified = length(copied_entries),
  plugin_runtime_identical_to_standalone = TRUE,
  sdg_runtime_hashes_match_previous_github_release = TRUE,
  runtime_assets = unname(assets[runtime_files]), source_asset = assets[[source_file]],
  checksum_files = list(SHA256SUMS = sha256(file.path(dist_dir, "SHA256SUMS.txt")),
                        source_and_runtime = sha256(file.path(dist_dir, "SOURCE_AND_RUNTIME_SHA256SUMS.txt")))
)
jsonlite::write_json(manifest, file.path(dist_dir, "release_manifest.json"), pretty = TRUE,
                     auto_unbox = TRUE, null = "null", digits = NA)
cat("Candidate status:", manifest$status, "\n")
cat("Verified", length(assets), "archive hashes; SDG assets unchanged.\n")
