suppressPackageStartupMessages({
  library(digest)
  library(jsonlite)
})
source("scripts/ghe_spec.R")
args <- commandArgs(TRUE)
stopifnot(length(args) == 2L, args[1] %in% c("manifest", "catalog"), grepl("^[0-9a-f]{40}$", args[2]))
revision <- args[2]
descriptor <- function(path) {
  list(url = paste0(raw.base, revision, "/", path), bytes = file.size(path),
       sha256 = digest(file = path, algo = "sha256"))
}
write_index <- function(x, folder, name) {
  dir.create(folder, recursive = TRUE, showWarnings = FALSE)
  path <- file.path(folder, paste0(name, ".json"))
  write_metadata(x, path)
  writeLines(paste(digest(file = path, algo = "sha256"), basename(path), sep = "  "),
             file.path(folder, paste0(name, ".sha256")))
}
manifest.path <- file.path(out, "manifest.json")
if (args[1] == "manifest") {
  d <- read.csv(file.path(out, "observations.csv"), na.strings = "")
  validate_rows(d)
  p <- read_json(file.path(out, "provenance.json"))
  window <- seq(min(d$year), max(d$year))
  area_entry <- function(i) {
    code <- roster$area_code[i]
    a <- d[d$area_code == code, ]
    strata <- lapply(sex.codes, function(s) {
      values <- a[a$sex == s, ]
      list(sex = s, observed_years = as.list(values$year),
           nonmissing_years = as.list(values$year[!is.na(values$value)]))
    })
    status <- if (!nrow(a)) "no_observations" else if (
      nrow(a) == length(window) * length(sex.codes) && !anyNA(a$value)) "complete" else "partial"
    list(area_code = code, area_name = roster$area_name[i], rows = nrow(a), status = status,
         first_year = if (nrow(a)) min(a$year), last_year = if (nrow(a)) max(a$year),
         strata = strata, observations = if (nrow(a)) descriptor(file.path(out, "areas", paste0(code, ".csv"))))
  }
  expected <- nrow(roster) * length(window) * length(sex.codes)
  obs <- descriptor(file.path(out, "observations.csv"))
  stopifnot(identical(obs$sha256, p$observations_sha256))
  m <- list(schema_version = "2.0", snapshot = snapshot.id, run_id = p$run_id, scope = scope,
            data_commit = revision, retrieved_at = p$retrieved_at, indicator = indicator,
            observation_key = key, geography = list(region = "WHO Western Pacific Region", basis = p$geography_basis,
                    roster_source = p$roster_source, areas = lapply(seq_len(nrow(roster)), area_entry)),
            years = list(first = min(window), last = max(window)),
            completeness = list(retrieval = "complete", roster_areas = nrow(roster), observed_areas = length(unique(d$area_code)),
                  expected_area_year_sex = expected, observed_rows = nrow(d), absent_area_year_sex = expected - nrow(d),
                  missing_estimates = sum(is.na(d$value)), missing_lower_bounds = sum(is.na(d$low)), missing_upper_bounds = sum(is.na(d$high))),
            files = list(observations = obs, provenance = descriptor(file.path(out, "provenance.json"))))
  write_index(m, out, "manifest")
} else {
  # Phase 4 is the immutable base for all Phase 5 catalogs.
  baseline <- "snapshots/catalog.json"
  stopifnot(digest(file = baseline, algo = "sha256") == "1becbecfa2226a96303853a77476c24428ec84ceccf79c9eeccb0051004c54fd")
  catalog <- read_json(baseline)
  m <- read_json(manifest.path)
  catalog$indicators[[4]] <- list(id = snapshot.id, indicator = m$indicator, product = product, backend = "xmart",
          scope = scope, aliases = c("number of deaths", "all causes mortality count"), years = m$years,
          run_id = m$run_id, retrieved_at = m$retrieved_at, manifest = descriptor(manifest.path))
  write_index(catalog, catalog.dir, "catalog")
}
