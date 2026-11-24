suppressPackageStartupMessages({
  library(DSIR)
  library(digest)
  library(jsonlite)
})

source("scripts/wpr_indicator.R")
indicator.code <- spec$code
expected.unit <- spec$unit
roster.url <- "https://www.who.int/westernpacific/about/where-we-work"
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
          all(data$measure_field == spec$measure))
for (field in c("value_num", "low", "high")) {
  x <- data[[field]]
  stopifnot(is.numeric(x), all(is.na(x) | (is.finite(x) & x >= 0 & x <= spec$maximum)))
}
stopifnot(all(data$low <= data$high, na.rm = TRUE),
          all(data$low <= data$value_num, na.rm = TRUE),
          all(data$value_num <= data$high, na.rm = TRUE))

source("scripts/write_wpr_tables.R")
files <- write_wpr_tables(data, roster, required.fields, out)
prov <- list(product = "WHO Global Health Observatory", indicator_code = indicator.code,
             unit = expected.unit, actual_backend = "xmart", package_version = as.character(packageVersion("DSIR")),
             roster_source = roster.url, geography_basis = "Current WHO Western Pacific roster applied to all years.",
             selection = "Unrestricted DSIR gho_data, matched to the roster after retrieval. Counts and ranges cross-checked with gho_coverage.",
             global_source_rows = source.count, sources = meta$sources, query = meta$query,
             retrieved_at = meta$sources$retrieved_at[[1]], query_seconds = elapsed,
             run_id = Sys.getenv("GITHUB_RUN_ID"), run_attempt = Sys.getenv("GITHUB_RUN_ATTEMPT"),
             workflow_commit = Sys.getenv("GITHUB_SHA"), first_year = files$first_year, last_year = files$last_year,
             completeness = files$qa, areas = files$areas, observations_sha256 = files$observations_sha256)
if (dtp3) {
  prov$estimate_type <- spec$estimate_type
  prov$indicator_metadata <- spec$metadata_url
  prov$bounds_expected <- spec$bounds_expected
}
write_json(prov, file.path(out, "provenance.json"), auto_unbox = TRUE, pretty = TRUE,
           na = "null", null = "null", digits = NA)
print(files$qa)
