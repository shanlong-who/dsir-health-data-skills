suppressPackageStartupMessages({
  library(jsonlite)
  library(openssl)
})

source("scripts/wpr_indicator.R")
manifest <- read_json(file.path(out, "manifest.json"))
roster <- read.csv("config/wpr-areas.csv", colClasses = "character")
base.url <- paste0("https://raw.githubusercontent.com/shanlong-who/dsir-health-data-skills/",
                   manifest$data_commit, "/snapshots/", snapshot.id, "/")
sha256_file <- function(path) {
  stream <- file(path, open = "rb")
  on.exit(close(stream))
  paste(as.character(sha256(stream)), collapse = "")
}
verify_file <- function(descriptor, path) {
  file <- file.path(out, path)
  stopifnot(identical(descriptor$url, paste0(base.url, path)), file.exists(file),
            file.size(file) == descriptor$bytes, identical(sha256_file(file), descriptor$sha256))
  file
}
read_observations <- function(file) {
  read.csv(file, colClasses = "character", na.strings = "", encoding = "UTF-8",
           check.names = FALSE, stringsAsFactors = FALSE)
}
stopifnot(identical(readLines(file.path(out, "manifest.sha256")),
                    paste0(sha256_file(file.path(out, "manifest.json")), "  manifest.json")),
          grepl("^[0-9a-f]{40}$", manifest$data_commit))
data <- read_observations(verify_file(manifest$files$observations, "observations.csv"))
prov <- read_json(verify_file(manifest$files$provenance, "provenance.json"))
unit <- spec$unit
stopifnot(nrow(data) > 0L, identical(manifest$snapshot, snapshot.id), all(data$id == spec$code), all(data$unit == unit),
          all(data$measure_field == spec$measure), all(data$time_type == "YEAR"),
          identical(manifest$indicator$code, unique(data$id)), identical(manifest$indicator$unit, unit),
          !anyNA(data[c("area_code", "observation_id", "year")]), all(nzchar(data$observation_id)),
          !anyDuplicated(data[c("area_code", "year")]), !anyDuplicated(data$observation_id),
          all(data$area_code %in% roster$area_code), identical(prov$run_id, manifest$run_id),
          identical(prov$retrieved_at, manifest$retrieved_at),
          identical(prov$observations_sha256, manifest$files$observations$sha256),
          identical(prov$completeness, manifest$completeness))
numbers <- lapply(data[c("value_num", "low", "high")], as.numeric)
for (field in names(numbers)) {
  x <- numbers[[field]]
  stopifnot(identical(is.na(x), is.na(data[[field]])), all(is.na(x) | (is.finite(x) & x >= 0 & x <= spec$maximum)))
}
stopifnot(all(numbers$low <= numbers$value_num, na.rm = TRUE),
          all(numbers$value_num <= numbers$high, na.rm = TRUE),
          all(numbers$low <= numbers$high, na.rm = TRUE))
years <- as.integer(data$year)
stopifnot(all(as.character(years) == data$year),
          min(years) == manifest$years$first, max(years) == manifest$years$last)
window <- seq(min(years), max(years))
areas <- manifest$geography$areas
codes <- vapply(areas, "[[", character(1), "area_code")
stopifnot(!anyDuplicated(codes), setequal(codes, roster$area_code))
for (a in areas) {
  rows <- data[data$area_code == a$area_code, , drop = FALSE]
  y <- as.integer(rows$year)
  absent <- setdiff(window, y)
  stopifnot(a$rows == nrow(rows), identical(a$area_name, roster$area_name[match(a$area_code, roster$area_code)]),
            all(rows$area_name == a$area_name),
            identical(as.integer(unlist(a$missing_years_in_window)), absent))
  missing.fields <- c(value_num = "missing_value_years", low = "missing_low_years", high = "missing_high_years")
  for (column in names(missing.fields)) {
    recorded <- as.integer(unlist(a[[missing.fields[[column]]]]))
    stopifnot(identical(recorded, y[is.na(rows[[column]])]))
  }
  if (!nrow(rows)) {
    stopifnot(a$status == "no_observations", is.null(a$observations), is.null(a$first_year), is.null(a$last_year))
    next
  }
  status <- if (length(absent) || anyNA(rows[required.fields])) "partial" else "complete"
  stopifnot(a$status == status, a$first_year == min(y), a$last_year == max(y))
  slice <- read_observations(verify_file(a$observations, paste0("areas/", a$area_code, ".csv")))
  rownames(rows) <- NULL
  stopifnot(identical(slice, rows))
}
qa <- manifest$completeness
statuses <- vapply(areas, "[[", character(1), "status")
stopifnot(qa$retrieval == "complete", qa$roster_areas == nrow(roster),
          qa$observed_areas == length(unique(data$area_code)),
          qa$no_observations == sum(statuses == "no_observations"),
          qa$geography_and_years == if (all(statuses == "complete")) "complete" else "partial",
          qa$expected_area_years == nrow(roster) * length(window), qa$observed_area_years == nrow(data),
          qa$absent_area_years == qa$expected_area_years - nrow(data),
          qa$missing_estimates == sum(is.na(numbers$value_num)),
          qa$missing_lower_bounds == sum(is.na(numbers$low)), qa$missing_upper_bounds == sum(is.na(numbers$high)),
          all(unlist(qa[c("duplicate_area_years", "duplicate_observation_ids", "invalid_units", "invalid_bounds")]) == 0))
cat(sprintf("Verified %d roster entries, %d observations and %d area CSVs against the full file.\n",
            length(areas), nrow(data), length(unique(data$area_code))))
