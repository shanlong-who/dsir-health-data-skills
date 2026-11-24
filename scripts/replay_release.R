suppressPackageStartupMessages(library(zip))
source("scripts/check_release.R")
args <- commandArgs(TRUE)
if (length(args) < 1L || length(args) > 3L) stop("Usage: replay_release.R report.json [public|git] [baseline.zip]")
transport <- if (length(args) >= 2L) args[2] else "public"
expected <- read_json("config/release-baseline-0.5.1.json")
work <- tempfile("release-replay-")
dir.create(work)
name <- expected$plugin_name
skill.path <- paste0("skills/", name, "/SKILL.md")
files <- c("plugin.json", skill.path)
if (length(args) == 3L) {
  good <- normalizePath(args[3], winslash = "/", mustWork = TRUE)
} else {
  good <- file.path(work, "accepted.zip")
  zipr(good, files, root = file.path("plugins", name), include_directories = FALSE, mode = "mirror")
}
positive <- check_release(good, expected, transport)
stage <- file.path(work, "old-candidate")
dir.create(stage)
members <- utils::unzip(good, list = TRUE)$Name
stopifnot(all(members %in% c(files, ".codex-plugin/plugin.json")))
utils::unzip(good, files = members, exdir = stage)
path <- file.path(stage, skill.path)
lines <- readLines(path, encoding = "UTF-8")
pilot.catalog <- paste0(raw.base, "2a2e030b29344c10e401f4d2168ebd5ad3aa7030/snapshots/phase5/catalog.json")
pilot.manifest <- paste0(raw.base, "da1c9991fb1c55466ba50f659da43ac585bd3c13/snapshots/phl-ghe-deaths/manifest.json")
lines <- gsub(expected$catalog$url, pilot.catalog, lines, fixed = TRUE)
lines <- gsub(expected$manifest$url, pilot.manifest, lines, fixed = TRUE)
lines <- gsub("is `wpr-ghe-deaths`, scope `regional`, run `45379887521`",
              "is `phl-ghe-deaths`, scope `philippines`, run `45379334336`", lines, fixed = TRUE)
writeLines(lines, path, useBytes = TRUE)
old <- file.path(work, "old-candidate.zip")
zipr(old, members, root = stage, include_directories = FALSE, mode = "mirror")
negative <- check_release(old, expected, transport)
passed <- positive$status == "passed" && negative$status == "rejected" &&
  all(c("snapshot", "scope", "run_id", "catalog", "manifest") %in% unlist(negative$issues)) &&
  all(unlist(negative$checks[c("catalog_sidecar", "linked_manifest", "manifest_digest", "manifest_identity")]))
report <- list(status = if (passed) "passed" else "failed",
               checked_at_utc = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
               accepted_regional = positive, stale_philippines = negative)
save_report(report, args[1])
cat("Regional:", positive$status, " Philippines:", negative$status,
    " Reasons:", paste(unlist(negative$issues), collapse = ", "), "\n")
if (!passed) quit(status = 1L)
