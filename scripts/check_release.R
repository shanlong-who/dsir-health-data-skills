suppressPackageStartupMessages({
  library(curl)
  library(jsonlite)
  library(openssl)
  library(yaml)
})

raw.base <- "https://raw.githubusercontent.com/shanlong-who/dsir-health-data-skills/"
sha256_hex <- function(bytes) paste(as.character(sha256(bytes)), collapse = "")
read_bytes <- function(path) readBin(path, "raw", n = file.size(path))
as_json <- function(bytes) fromJSON(rawToChar(bytes), simplifyVector = FALSE)
save_report <- function(report, path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  contents <- toJSON(report, auto_unbox = TRUE, pretty = TRUE, null = "null", digits = NA)
  writeBin(charToRaw(enc2utf8(paste0(contents, "\n"))), path)
}

release_bytes <- function(url, transport) {
  spec <- substring(url, nchar(raw.base) + 1L)
  if (!startsWith(url, raw.base) ||
      !grepl("^[a-f0-9]{40}/snapshots/[a-z0-9-]+/(catalog\\.(json|sha256)|manifest\\.json)$", spec)) {
    stop("Expected an immutable snapshot URL: ", url)
  }
  if (transport == "public") {
    path <- tempfile()
    handle <- new_handle(failonerror = TRUE, connecttimeout = 15, timeout = 60)
    for (attempt in 1:3) {
      attempt.result <- try(curl_download(url, path, handle = handle, mode = "wb"), silent = TRUE)
      if (!inherits(attempt.result, "try-error")) return(read_bytes(path))
      if (attempt < 3L) Sys.sleep(attempt)
    }
    stop("Public download failed: ", url)
  }
  stopifnot(identical(transport, "git"))
  path <- tempfile()
  object <- sub("/", ":", spec, fixed = TRUE)
  status <- system2("git", c("cat-file", "blob", object), stdout = path)
  if (status != 0L) stop("Git object unavailable: ", object)
  read_bytes(path)
}

read_package <- function(archive) {
  entries <- utils::unzip(archive, list = TRUE)$Name
  if (anyDuplicated(entries)) stop("Duplicate package paths")
  text_entry <- function(path) {
    if (!path %in% entries) stop("Missing package file: ", path)
    con <- unz(archive, path, encoding = "UTF-8")
    on.exit(close(con))
    paste(readLines(con, warn = FALSE), collapse = "\n")
  }
  meta <- fromJSON(text_entry("plugin.json"), simplifyVector = FALSE)
  skill.path <- paste0("skills/", meta$name, "/SKILL.md")
  stopifnot(identical(grep("^skills/[^/]+/SKILL\\.md$", entries, value = TRUE), skill.path))
  skill <- text_entry(skill.path)
  parts <- strsplit(skill, "\n", fixed = TRUE)[[1]]
  cuts <- which(parts == "---")
  stopifnot(length(cuts) >= 2L, cuts[1] == 1L)
  front <- yaml.load(paste(parts[2:(cuts[2] - 1L)], collapse = "\n"))
  stopifnot(identical(front$name, meta$name), nzchar(front$description))
  list(name = meta$name, version = meta$version, skill = skill)
}

check_release <- function(archive, expected, transport = "public") {
  required <- c("plugin_name", "plugin_version", "snapshot", "scope", "run_id", "retrieved_at", "catalog", "manifest")
  stopifnot(setequal(names(expected), required), all(vapply(expected[required[1:6]], function(x) {
    is.character(x) && length(x) == 1L && !is.na(x) && nzchar(x)
  }, logical(1))), expected$scope == "regional", expected$snapshot == "wpr-ghe-deaths",
  grepl("^[0-9]+$", expected$run_id))
  for (ref in expected[c("catalog", "manifest")]) {
    stopifnot(setequal(names(ref), c("url", "sha256")), length(ref$url) == 1L,
              length(ref$sha256) == 1L, grepl("^[a-f0-9]{64}$", ref$sha256))
  }
  package <- read_package(archive)
  # Check the URLs an ordinary Chat is actually instructed to open.
  links <- regmatches(package$skill, gregexpr("https?://[^)[:space:]>]+", package$skill))[[1]]
  pick_link <- function(pattern) {
    hits <- unique(links[grepl(pattern, links)])
    if (length(hits) != 1L) stop("Expected one package URL matching ", pattern)
    hits[[1]]
  }
  catalog.url <- pick_link("/catalog\\.json$")
  manifest.url <- pick_link("/manifest\\.json$")
  bytes <- release_bytes(catalog.url, transport)
  sidecar <- trimws(rawToChar(release_bytes(sub("json$", "sha256", catalog.url), transport)))
  catalog.hash <- sha256_hex(bytes)
  catalog <- as_json(bytes)
  ghe <- Filter(function(x) identical(x$indicator$code, "GHE/0/deaths"), catalog$indicators)
  if (length(ghe) != 1L) stop("Expected one GHE deaths entry")
  entry <- ghe[[1]]
  m.bytes <- release_bytes(manifest.url, transport)
  m <- as_json(m.bytes)
  manifest.hash <- sha256_hex(m.bytes)
  actual <- list(plugin_name = package$name, plugin_version = package$version,
                 snapshot = entry$id, scope = entry$scope, run_id = entry$run_id,
                 retrieved_at = entry$retrieved_at, catalog = list(url = catalog.url, sha256 = catalog.hash),
                 manifest = list(url = manifest.url, sha256 = manifest.hash))
  diffs <- names(expected)[!vapply(names(expected), function(k) identical(actual[[k]], expected[[k]]), logical(1))]
  checks <- c(catalog_sidecar = identical(sidecar, paste0(catalog.hash, "  catalog.json")),
              linked_manifest = identical(manifest.url, entry$manifest$url),
              manifest_digest = identical(manifest.hash, entry$manifest$sha256),
              manifest_length = identical(as.numeric(length(m.bytes)), as.numeric(entry$manifest$bytes)),
              manifest_identity = identical(c(m$snapshot,m$scope,m$run_id,m$retrieved_at),
                                            c(entry$id,entry$scope,entry$run_id,entry$retrieved_at)),
              dimensions = identical(entry$indicator, m$indicator),
              regional_roster = identical(m$completeness$roster_areas, 38L) &&
                identical(sort(vapply(m$geography$areas, "[[", character(1), "area_code")),
                          sort(read.csv("config/wpr-areas.csv")$area_code)),
              skill_identity = grepl(sprintf("is `%s`, scope `%s`, run `%s`", entry$id, entry$scope, entry$run_id),
                                     package$skill, fixed = TRUE))
  issues <- c(diffs, names(checks)[!checks])
  list(status = if (length(issues)) "rejected" else "passed", issues = as.list(issues),
       archive_sha256 = sha256_hex(read_bytes(archive)), expected = expected, actual = actual,
       checks = as.list(checks), transport = transport)
}

if (sys.nframe() == 0L) {
  args <- commandArgs(TRUE)
  if (length(args) != 4L) stop("Usage: check_release.R package.zip release.json public|git report.json")
  result <- tryCatch(check_release(args[1], read_json(args[2]), args[3]),
                     error = function(e) list(status = "rejected", issues = list(conditionMessage(e))))
  save_report(result, args[4])
  cat(result$status, paste(unlist(result$issues), collapse = ", "), "\n")
  if (result$status != "passed") quit(status = 1L)
}
