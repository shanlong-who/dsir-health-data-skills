suppressPackageStartupMessages({
  library(curl)
  library(jsonlite)
  library(openssl)
})

public <- "--public" %in% commandArgs(TRUE)
root <- if (public) file.path(tempdir(), "wpr-phase3") else "snapshots"
dir.create(root, recursive = TRUE, showWarnings = FALSE)
raw.base <- "https://raw.githubusercontent.com/shanlong-who/dsir-health-data-skills/"
catalog.url <- paste0(raw.base, "refs/heads/pilot/wpr-multi-phase3/snapshots/catalog.json")
fetch <- function(url, path) {
  if (public) {
    dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
    for (i in 1:3) {
      result <- try(curl_download(url, path, mode = "wb", quiet = TRUE), silent = TRUE)
      if (!inherits(result, "try-error")) break
      if (i == 3L) stop(result)
      Sys.sleep(i)
    }
  }
  stopifnot(file.exists(path))
  path
}
hash_file <- function(path) {
  con <- file(path, "rb")
  on.exit(close(con))
  as.character(sha256(con))
}
catalog.path <- fetch(catalog.url, file.path(root, "catalog.json"))
sidecar <- fetch(sub("json$", "sha256", catalog.url), file.path(root, "catalog.sha256"))
stopifnot(identical(readLines(sidecar), paste0(hash_file(catalog.path), "  catalog.json")))
catalog <- read_json(catalog.path)
ids <- vapply(catalog$indicators, "[[", character(1), "id")
stopifnot(length(ids) == 2L, setequal(ids, c("wpr-tb", "wpr-dtp3")))
check_entry <- function(entry) {
  id <- entry$id
  folder <- file.path(root, id)
  verify <- function(descriptor, relative, commit) {
    stopifnot(grepl("^[a-f0-9]{40}$", commit),
              identical(descriptor$url, paste0(raw.base, commit, "/snapshots/", id, "/", relative)))
    path <- fetch(descriptor$url, file.path(folder, relative))
    stopifnot(identical(hash_file(path), descriptor$sha256))
    if (!is.null(descriptor$bytes)) stopifnot(file.size(path) == descriptor$bytes)
    path
  }
  revision <- strsplit(sub(raw.base, "", entry$manifest$url, fixed = TRUE), "/", fixed = TRUE)[[1]][1]
  m <- read_json(verify(entry$manifest, "manifest.json", revision))
  stopifnot(identical(m$indicator, entry$indicator), identical(m$run_id, entry$run_id),
            identical(m$retrieved_at, entry$retrieved_at), identical(m$years, entry$years),
            identical(m$snapshot, id))
  if (id == "wpr-dtp3") {
    stopifnot(m$indicator$code == "WHS4_100", identical(m$indicator$bounds_expected, FALSE),
              grepl("WUENIC", m$indicator$estimate_type, fixed = TRUE))
  }
  p <- read_json(verify(m$files$provenance, "provenance.json", m$data_commit))
  stopifnot(identical(p$run_id, m$run_id), identical(p$observations_sha256, m$files$observations$sha256))
  full <- read.csv(verify(m$files$observations, "observations.csv", m$data_commit),
                   colClasses = "character", encoding = "UTF-8", na.strings = "")
  areas <- m$geography$areas
  covered <- Filter(function(a) !is.null(a$observations), areas)
  stopifnot(length(covered) == m$completeness$observed_areas,
            nrow(full) == m$completeness$observed_area_years)
  for (area in covered) {
    path <- verify(area$observations, paste0("areas/", area$area_code, ".csv"), m$data_commit)
    slice <- read.csv(path, colClasses = "character", encoding = "UTF-8", na.strings = "")
    expected <- full[full$area_code == area$area_code, , drop = FALSE]
    rownames(expected) <- NULL
    stopifnot(identical(slice, expected))
  }
  vn <- read.csv(file.path(folder, "areas", "VNM.csv"), encoding = "UTF-8")
  stopifnot(all(vn$area_code == "VNM"), all(vn$id == m$indicator$code),
            all(vn$unit == m$indicator$unit), !anyDuplicated(vn$year))
  list(series = vn, summary = list(id = id, retrieved_at = m$retrieved_at, run_id = m$run_id,
       years = m$years, completeness = m$completeness,
       area_codes = vapply(covered, "[[", character(1), "area_code"),
       independently_hashed_files = 3L + length(covered), csv_sha256 = m$files$observations$sha256))
}
info <- setNames(lapply(catalog$indicators, check_entry), ids)
latest_years <- function(series) {
  years <- lapply(series, function(x) x$year[!is.na(x$value_num)])
  common <- Reduce(intersect, years)
  list(latest = vapply(years, function(y) if (length(y)) max(y) else NA_integer_, integer(1)),
       shared = if (length(common)) max(common) else NA_integer_)
}
# These cases distinguish set intersection from the earlier of the two latest years.
a <- data.frame(year = c(2019L, 2020L, 2022L), value_num = c(0, NA, 5))
b <- data.frame(year = c(2019L, 2020L, 2021L), value_num = c(4, 7, 6))
stopifnot(latest_years(list(a, b))$shared == 2019L,
          is.na(latest_years(list(a, b[2:3, ]))$shared))
series <- lapply(info, "[[", "series")
dates <- latest_years(series)
fields <- c("id", "area_code", "year", "value_num", "low", "high", "unit", "observation_id")
rows_at <- function(years) {
  lapply(names(series), function(id) series[[id]][series[[id]]$year %in% years[[id]], fields, drop = FALSE])
}
evidence <- list(public_downloads = public, catalog_sha256 = hash_file(catalog.path),
                 indicators = lapply(info, "[[", "summary"), latest = rows_at(dates$latest),
                 common_year = dates$shared, common_rows = rows_at(setNames(rep(dates$shared, length(ids)), ids)))
cat(toJSON(evidence, auto_unbox = TRUE, na = "null", pretty = TRUE), "\n")
report <- Sys.getenv("PHASE3_RESULT_FILE")
if (nzchar(report)) write_json(evidence, report, auto_unbox = TRUE, pretty = TRUE, na = "null")
