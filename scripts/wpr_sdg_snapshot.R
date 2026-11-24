suppressPackageStartupMessages({
  library(DSIR)
  library(jsonlite)
})
source("scripts/wpr_indicator.R")
source("scripts/write_wpr_tables.R")
roster <- read.csv("config/wpr-areas.csv", colClasses = "character")
stopifnot(sdg, as.character(packageVersion("DSIR")) == "0.15.0", nrow(roster) == 38L,
          !anyNA(roster), !anyDuplicated(roster$m49), !anyDuplicated(roster$area_code))
started <- Sys.time()
m49 <- as.character(as.integer(roster$m49))
batches <- split(m49, ceiling(seq_along(m49) / 8L))
read_batch <- function(codes) {
  result <- sdg_data(spec$code, area = codes, series = spec$series, page_size = 100L,
                     keep_dimensions = TRUE, keep_metadata = TRUE)
  meta <- dsir_metadata(result)
  stopifnot(meta$result$status %in% c("success", "empty"), isTRUE(meta$result$complete),
            meta$result$rows == nrow(result), nrow(meta$sources) > 0L,
            all(meta$sources$backend == "unsdg"), all(meta$sources$retrieval_status == "live"),
            !anyNA(meta$sources$retrieved_at), setequal(meta$query$area_codes, codes))
  rows <- as.data.frame(result)
  stopifnot(all(rows$location %in% codes), all(rows$id == spec$code), all(rows$series == spec$series))
  list(rows = rows, sources = meta$sources, query = meta$query)
}
parts <- lapply(batches, read_batch)
data <- as.data.frame(do.call(vctrs::vec_rbind, unname(lapply(parts, "[[", "rows"))))
sources <- do.call(vctrs::vec_rbind, unname(lapply(parts, "[[", "sources")))
idx <- match(data$location, m49)
stopifnot(!anyNA(idx))
data$area_code <- roster$area_code[idx]
data$area_name <- roster$area_name[idx]
stopifnot(nrow(data) > 0L, all(data$source == "sdg"), all(data$attr_units == "PERCENT"),
          all(data$dim_reporting_type == "G"), !anyNA(data$year),
          !anyDuplicated(data[c("area_code", "year")]))
data$unit <- spec$unit
data$record_key <- paste("UNSDG", data$series, data$location, data$year, data$dim_reporting_type, sep = "/")
stopifnot(!anyDuplicated(data$record_key))
for (field in c("value_num","low","high")) {
  x <- data[[field]]
  stopifnot(is.numeric(x), all(is.na(x) | (is.finite(x) & x >= 0 & x <= 100)))
}
stopifnot(all(data$low <= data$value_num, na.rm = TRUE), all(data$value_num <= data$high, na.rm = TRUE),
          all(data$low <= data$high, na.rm = TRUE))
data <- data[order(data$area_code, data$year), , drop = FALSE]
files <- write_wpr_tables(data, roster, required.fields, out)
files$qa$duplicate_observation_ids <- NULL
files$qa$duplicate_record_keys <- 0L
prov <- list(product = "United Nations Global SDG Indicators Database", actual_backend = "unsdg",
             indicator_code = spec$code, series = spec$series, unit = spec$unit,
             source_unit = "PERCENT", reporting_type = "G", metadata_url = spec$metadata_url,
             record_key_definition = "Local key: provider, series, source M49 code, observation year and reporting type.",
             package_version = as.character(packageVersion("DSIR")),
             roster_source = "https://www.who.int/westernpacific/about/where-we-work",
             geography_basis = "Current WHO Western Pacific roster applied to all years.",
             selection = "DSIR sdg_data requested the 38 roster M49 codes in disjoint batches and selected the SDG series.",
             regional_source_rows = nrow(data), sources = sources, queries = unname(lapply(parts, "[[", "query")),
             retrieval_started_at = min(sources$retrieved_at), retrieved_at = max(sources$retrieved_at),
             query_seconds = round(as.numeric(difftime(Sys.time(), started, units = "secs")), 2),
             run_id = Sys.getenv("GITHUB_RUN_ID"), run_attempt = Sys.getenv("GITHUB_RUN_ATTEMPT"),
             workflow_commit = Sys.getenv("GITHUB_SHA"), first_year = files$first_year, last_year = files$last_year,
             completeness = files$qa, areas = files$areas, observations_sha256 = files$observations_sha256)
write_json(prov, file.path(out, "provenance.json"), auto_unbox = TRUE, pretty = TRUE,
           na = "null", null = "null", digits = NA)
print(files$qa)
