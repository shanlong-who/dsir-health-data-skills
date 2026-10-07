# Validate the listing-only package against the immutable standalone runtime.
library(jsonlite)
library(digest)

script_arg <- grep("^--file=", commandArgs(), value = TRUE)
root <- normalizePath(file.path(dirname(sub("^--file=", "", script_arg)), ".."), winslash = "/")
version <- "0.1.3"
artifact <- file.path(root, "dist", paste0("dsir-gho-plugin-", version, ".zip"))
source_zip <- file.path(root, "dist/dsir-gho-0.1.1.zip")
sha256 <- function(path) digest(file = path, algo = "sha256", serialize = FALSE)
stopifnot(identical(sha256(source_zip), "cdfcb748d581daf2afe93d32384f42aa2f424f77d7e63f7e6dd3316dc8c1fd31"))
archive_files <- unzip(artifact, list = TRUE)$Name
stopifnot(!anyDuplicated(archive_files), !any(grepl("(^/|(^|/)\\.\\.(/|$)|\\\\)", archive_files)))
unpack <- tempfile("gho_listing_")
source_unpack <- tempfile("gho_original_")
dir.create(unpack)
dir.create(source_unpack)
unzip(artifact, exdir = unpack)
unzip(source_zip, exdir = source_unpack)
plugin <- file.path(unpack, "dsir-gho")
portable <- fromJSON(file.path(plugin, "plugin.json"), simplifyVector = FALSE)
compatibility <- fromJSON(file.path(plugin, ".codex-plugin/plugin.json"), simplifyVector = FALSE)
listing <- portable$extensions$com.openai$interface
stopifnot(identical(listing, compatibility$interface), identical(portable$version, version), identical(compatibility$version, version))
stopifnot(nchar(listing$displayName, type = "chars") <= 30L,
          nchar(listing$shortDescription, type = "chars") == 30L,
          nchar(listing$longDescription, type = "chars") <= 4000L,
          identical(listing$category, "Data & Analytics"),
          identical(listing$privacyPolicyURL, "https://shanlong-who.github.io/dsir-health-data-skills/privacy.html"))
for (field in c("websiteURL", "privacyPolicyURL", "supportURL")) {
  stopifnot(startsWith(listing[[field]], "https://"), nchar(listing[[field]]) <= 1024L)
}
source_files <- list.files(file.path(source_unpack, "dsir-gho"), recursive = TRUE, all.files = TRUE)
runtime_files <- source_files[grepl("^(scripts/|references/|agents/|SKILL[.]md$|LICENSE$)", source_files)]
packaged_runtime <- list.files(file.path(plugin, "skills/dsir-gho"), recursive = TRUE, all.files = TRUE)
stopifnot(setequal(runtime_files, packaged_runtime))
for (relative in runtime_files) {
  stopifnot(identical(sha256(file.path(source_unpack, "dsir-gho", relative)),
                      sha256(file.path(plugin, "skills/dsir-gho", relative))))
}
for (relative in sub("^dsir-gho/", "", archive_files)) {
  stopifnot(identical(sha256(file.path(plugin, relative)), sha256(file.path(root, "plugins/dsir-gho", relative))))
}
report <- fromJSON(file.path(root, "dist", paste0("dsir-gho-plugin-", version, "-checksums.json")), simplifyVector = FALSE)
stopifnot(identical(report$sha256, sha256(artifact)))
report$listing_validation_passed <- TRUE
report$runtime_file_count_verified <- length(runtime_files)
report$subtitle_characters <- nchar(listing$shortDescription)
report$category <- listing$category
report$privacy_policy_url <- listing$privacyPolicyURL
report$live_validation_repeated <- FALSE
report$stable_release_validation_passed <- FALSE
report$previous_release <- "v2026.10.07"
out <- file.path(root, "dist/listing-0.1.3")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
invisible(file.copy(artifact, file.path(out, basename(artifact)), overwrite = TRUE))
writeBin(charToRaw(paste0(report$sha256, "  ", basename(artifact), "\n")), file.path(out, "SHA256SUMS.txt"))
writeBin(charToRaw(paste0(toJSON(report, auto_unbox = TRUE, pretty = TRUE), "\n")), file.path(out, "release_manifest.json"))
audit_dir <- file.path(root, "releases/v2026.10.07.1")
dir.create(audit_dir, recursive = TRUE, showWarnings = FALSE)
invisible(file.copy(file.path(out, c("release_manifest.json", "SHA256SUMS.txt")), audit_dir, overwrite = TRUE))
cat("Listing validation passed; ", length(runtime_files), " runtime files unchanged; SHA-256: ", report$sha256, "\n", sep = "")
