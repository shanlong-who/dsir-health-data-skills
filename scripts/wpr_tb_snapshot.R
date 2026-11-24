suppressPackageStartupMessages({
  library(DSIR)
  library(digest)
  library(jsonlite)
})

indicator.code <- "MDG_0000000020"
expected.unit <- "Tuberculosis incidence (per 100 000 population)"
roster.url <- "https://www.who.int/westernpacific/about/where-we-work"
out <- Sys.getenv("DSIR_SNAPSHOT_DIR", "snapshots/wpr-tb")
roster <- read.csv("config/wpr-areas.csv", colClasses = "character")
stopifnot(nrow(roster) == 38L, !anyNA(roster), !anyDuplicated(roster$area_code),
          !anyDuplicated(roster$m49), all(wpro_cty %in% roster$area_code),
          as.character(packageVersion("DSIR")) == "0.15.0")

# The country filter omits special administrative regions. Use unrestricted
# discovery and observations, then match the current WPR roster locally.
started <- Sys.time()
coverage <- gho_coverage(indicator.code, spatial_type = NULL, backend = "xmart")
source.count <- gho_count(indicator.code, backend = "xmart")
stopifnot(nrow(coverage) > 0L, !anyNA(coverage), !anyDuplicated(coverage$location),
          sum(coverage$n_obs) == source.count)
options(DSIR.who_page_size = 300L)
world <- gho_data(indicator.code, backend = "xmart", keep_dimensions = TRUE,
                  keep_metadata = TRUE)
meta <- dsir_metadata(world)
stopifnot(identical(meta$result$status, "success"), isTRUE(meta$result$complete),
          nrow(world) == source.count, all(world$id == indicator.code),
          all(world$provider == "xmart"), !anyNA(world$location),
          all(meta$sources$retrieval_status == "live"),
          length(meta$sources$retrieved_at) == 1L, !is.na(meta$sources$retrieved_at))
elapsed <- round(as.numeric(difftime(Sys.time(), started, units = "secs")), 2)

match_roster <- function(location) {
  i <- match(location, roster$area_code)
  missing <- is.na(i)
  i[missing] <- match(location[missing], roster$m49)
  i
}
index <- match_roster(world$location)
data <- as.data.frame(world[!is.na(index), ])
data$area_code <- roster$area_code[index[!is.na(index)]]
data$area_name <- roster$area_name[index[!is.na(index)]]
data <- data[order(data$area_code, data$year), , drop = FALSE]
geo.index <- match_roster(coverage$location)
expected <- coverage[!is.na(geo.index), ]
expected$area_code <- roster$area_code[geo.index[!is.na(geo.index)]]
stopifnot(nrow(data) > 0L, !anyDuplicated(expected$area_code),
          setequal(data$area_code, expected$area_code))
for (i in seq_len(nrow(expected))) {
  years <- data$year[data$area_code == expected$area_code[i]]
  stopifnot(length(years) == expected$n_obs[i], min(years) == expected$year_min[i],
            max(years) == expected$year_max[i])
}
stopifnot(!anyNA(data$year), all(data$time_type == "YEAR"),
          !anyDuplicated(data[c("area_code", "year")]),
          !anyNA(data$observation_id), all(nzchar(data$observation_id)),
          !anyDuplicated(data$observation_id), all(data$unit == expected.unit),
          all(data$measure_field == "RATE_PER_100000_N"))
for (field in c("value_num", "low", "high")) {
  x <- data[[field]]
  stopifnot(is.numeric(x), all(is.na(x) | (is.finite(x) & x >= 0)))
}
stopifnot(all(data$low <= data$high, na.rm = TRUE),
          all(data$low <= data$value_num, na.rm = TRUE),
          all(data$value_num <= data$high, na.rm = TRUE))

for (key in names(data)[vapply(data, is.list, logical(1))]) {
  data[[key]] <- vapply(data[[key]], function(x) as.character(toJSON(as.list(x), na = "null")), character(1))
}
dir.create(file.path(out, "areas"), recursive = TRUE, showWarnings = FALSE)
csv <- file.path(out, "observations.csv")
write.csv(data, csv, row.names = FALSE, na = "", fileEncoding = "UTF-8")
window <- seq(min(data$year), max(data$year))
area.coverage <- lapply(seq_len(nrow(roster)), function(i) {
  code <- roster$area_code[i]
  rows <- data[data$area_code == code, , drop = FALSE]
  missing.years <- setdiff(window, rows$year)
  has.data <- nrow(rows) > 0L
  status <- "no_observations"
  path <- NULL
  if (has.data) {
    path <- paste0("areas/", code, ".csv")
    write.csv(rows, file.path(out, path), row.names = FALSE, na = "", fileEncoding = "UTF-8")
    status <- if (length(missing.years) || anyNA(rows[c("value_num", "low", "high")])) "partial" else "complete"
  }
  list(area_code = code, area_name = roster$area_name[i], status = status,
       rows = nrow(rows), first_year = if (has.data) min(rows$year), last_year = if (has.data) max(rows$year),
       missing_years_in_window = I(missing.years), missing_value_years = I(rows$year[is.na(rows$value_num)]),
       missing_low_years = I(rows$year[is.na(rows$low)]), missing_high_years = I(rows$year[is.na(rows$high)]),
       csv_path = path)
})
statuses <- vapply(area.coverage, "[[", character(1), "status")
qa <- list(retrieval = "complete", geography_and_years = if (all(statuses == "complete")) "complete" else "partial",
           roster_areas = nrow(roster), observed_areas = length(unique(data$area_code)),
           no_observations = sum(statuses == "no_observations"),
           expected_area_years = nrow(roster) * length(window), observed_area_years = nrow(data),
           absent_area_years = nrow(roster) * length(window) - nrow(data),
           missing_estimates = sum(is.na(data$value_num)), missing_lower_bounds = sum(is.na(data$low)),
           missing_upper_bounds = sum(is.na(data$high)), duplicate_area_years = 0L,
           duplicate_observation_ids = 0L, invalid_units = 0L, invalid_bounds = 0L)
prov <- list(product = "WHO Global Health Observatory", indicator_code = indicator.code,
             unit = expected.unit, actual_backend = "xmart", package_version = as.character(packageVersion("DSIR")),
             roster_source = roster.url, geography_basis = "Current WHO Western Pacific roster applied to all years.",
             selection = "Unrestricted DSIR gho_data, matched to the roster after retrieval. Counts and ranges cross-checked with gho_coverage.",
             global_source_rows = source.count, sources = meta$sources, query = meta$query,
             retrieved_at = meta$sources$retrieved_at[[1]], query_seconds = elapsed,
             run_id = Sys.getenv("GITHUB_RUN_ID"), run_attempt = Sys.getenv("GITHUB_RUN_ATTEMPT"),
             workflow_commit = Sys.getenv("GITHUB_SHA"), first_year = min(window), last_year = max(window),
             completeness = qa, areas = area.coverage, observations_sha256 = digest(file = csv, algo = "sha256"))
write_json(prov, file.path(out, "provenance.json"), auto_unbox = TRUE, pretty = TRUE,
           na = "null", null = "null", digits = NA)
print(qa)
