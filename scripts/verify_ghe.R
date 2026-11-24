suppressPackageStartupMessages({
  library(jsonlite)
  library(openssl)
  library(curl)
})
source("scripts/ghe_spec.R")
public <- "--public" %in% commandArgs(TRUE)
revision <- Sys.getenv("DSIR_GHE_CATALOG_REVISION", "refs/heads/pilot/wpr-ghe-phase5")
prefix <- paste0(raw.base, revision, "/")
root <- if (public) tempfile("ghe-check-") else "."
hash_file <- function(path) {
  con <- file(path, "rb")
  on.exit(close(con))
  paste(as.character(sha256(con)), collapse = "")
}
fetch <- function(relative, url) {
  path <- file.path(root, relative)
  if (public) {
    dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
    for (attempt in seq_len(3L)) {
      result <- try(curl_download(url, path, mode = "wb", quiet = TRUE), silent = TRUE)
      if (!inherits(result, "try-error")) break
      if (attempt == 3L) stop(result)
      Sys.sleep(attempt)
    }
  }
  stopifnot(file.exists(path))
  path
}
verify_file <- function(relative, descriptor, revision) {
  stopifnot(grepl("^[0-9a-f]{40}$", revision),
            identical(descriptor$url, paste0(raw.base, revision, "/", relative)))
  path <- fetch(relative, descriptor$url)
  stopifnot(identical(hash_file(path), descriptor$sha256), file.size(path) == descriptor$bytes)
  path
}
catalog.file <- file.path(catalog.dir, "catalog.json")
catalog.path <- fetch(catalog.file, paste0(prefix, catalog.file))
sidecar <- paste0(catalog.dir, "/catalog.sha256")
stopifnot(identical(readLines(fetch(sidecar, paste0(prefix, sidecar))),
                    paste(hash_file(catalog.path), "catalog.json", sep = "  ")))
catalog <- read_json(catalog.path)
base.path <- "snapshots/catalog.json"
stopifnot(hash_file(base.path) == "1becbecfa2226a96303853a77476c24428ec84ceccf79c9eeccb0051004c54fd",
          identical(catalog$indicators[1:3], read_json(base.path)$indicators), length(catalog$indicators) == 4L)
entry <- catalog$indicators[[4L]]
manifest.rev <- strsplit(sub(raw.base, "", entry$manifest$url, fixed = TRUE), "/", fixed = TRUE)[[1]][1]
m <- read_json(verify_file(file.path(out, "manifest.json"), entry$manifest, manifest.rev))
stopifnot(entry$id == snapshot.id, identical(m$indicator, entry$indicator), identical(m$scope, scope),
          identical(m$run_id, entry$run_id), identical(m$retrieved_at, entry$retrieved_at),
          identical(unlist(m$observation_key), key), m$indicator$measure == "deaths",
          m$indicator$unit == "deaths", m$indicator$cause_code == "0", m$indicator$age == "TOTAL",
          identical(unlist(m$indicator$sex), sex.codes), m$indicator$product == product)
read_table <- function(path) read.csv(path, na.strings = "", colClasses = c(cause_code = "character"))
data <- read_table(verify_file(file.path(out, "observations.csv"), m$files$observations, m$data_commit))
p <- read_json(verify_file(file.path(out, "provenance.json"), m$files$provenance, m$data_commit))
stopifnot(identical(p$observations_sha256, m$files$observations$sha256),
          identical(p$run_id, m$run_id), identical(p$retrieved_at, m$retrieved_at),
          all(vapply(p$sources, function(x) isTRUE(x$complete) && x$status == "success" && x$endpoint == endpoint, logical(1))))
validate_rows(data)
codes <- vapply(m$geography$areas, "[[", character(1), "area_code")
stopifnot(identical(codes, roster$area_code), m$years$first == min(data$year), m$years$last == max(data$year))
possible <- nrow(roster) * length(seq(m$years$first, m$years$last)) * length(sex.codes)
cpl <- m$completeness
stopifnot(cpl$observed_rows == nrow(data), cpl$observed_areas == length(unique(data$area_code)),
          cpl$expected_area_year_sex == possible, cpl$absent_area_year_sex == possible - nrow(data),
          cpl$missing_estimates == sum(is.na(data$value)), cpl$missing_lower_bounds == sum(is.na(data$low)),
          cpl$missing_upper_bounds == sum(is.na(data$high)))
for (area in m$geography$areas) {
  rows <- data[data$area_code == area$area_code, ]
  stopifnot(nrow(rows) == area$rows, is.null(area$observations) == (nrow(rows) == 0L))
  if (nrow(rows)) {
    csv <- read_table(verify_file(file.path(out, "areas", paste0(area$area_code, ".csv")), area$observations, m$data_commit))
    rownames(rows) <- NULL
    stopifnot(identical(csv, rows), min(rows$year) == area$first_year, max(rows$year) == area$last_year)
  }
  status <- if (!nrow(rows)) "no_observations" else if (nrow(rows) == possible/nrow(roster) && !anyNA(rows$value)) "complete" else "partial"
  stopifnot(identical(status, area$status), identical(vapply(area$strata, "[[", character(1), "sex"), sex.codes))
  for (s in area$strata) {
    slice <- rows[rows$sex == s$sex, ]
    stopifnot(identical(as.integer(unlist(s$observed_years)), slice$year),
              identical(as.integer(unlist(s$nonmissing_years)), slice$year[!is.na(slice$value)]))
  }
}
phl <- data[data$area_code == "PHL" & data$year == 2023L, ]
stopifnot(nrow(phl) == 3L, setequal(phl$sex, sex.codes), all(complete.cases(phl[c("value","low","high")])))
print(phl[c("sex", "age", "year", "value", "low", "high", "unit")], digits = 12L, row.names = FALSE)
cat("Verified catalog, manifest, provenance, full CSV and", cpl$observed_areas,
    "area CSVs;", nrow(data), "observations for", nrow(roster), "roster areas.\n")
