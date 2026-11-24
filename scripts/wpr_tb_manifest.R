suppressPackageStartupMessages({
  library(digest)
  library(jsonlite)
})

out <- Sys.getenv("DSIR_SNAPSHOT_DIR", "snapshots/wpr-tb")
revision <- Sys.getenv("SNAPSHOT_DATA_COMMIT")
stopifnot(grepl("^[0-9a-f]{40}$", revision))
base.url <- paste0("https://raw.githubusercontent.com/shanlong-who/dsir-health-data-skills/",
                   revision, "/snapshots/wpr-tb/")
prov <- read_json(file.path(out, "provenance.json"))
describe_file <- function(path) {
  file <- file.path(out, path)
  list(url = paste0(base.url, path), bytes = file.size(file), sha256 = digest(file = file, algo = "sha256"))
}
areas <- lapply(prov$areas, function(area) {
  if (!is.null(area$csv_path)) area$observations <- describe_file(area$csv_path)
  area$csv_path <- NULL
  area
})
files <- list(observations = describe_file("observations.csv"), provenance = describe_file("provenance.json"))
stopifnot(identical(files$observations$sha256, prov$observations_sha256))
manifest <- list(schema_version = "1.0", snapshot = "wpr-tb", run_id = prov$run_id,
                 data_commit = revision, retrieved_at = prov$retrieved_at,
                 indicator = list(code = prov$indicator_code, name = "Tuberculosis incidence", unit = prov$unit),
                 geography = list(region = "WHO Western Pacific Region", basis = prov$geography_basis,
                                  roster_source = prov$roster_source, areas = areas),
                 years = list(first = prov$first_year, last = prov$last_year),
                 completeness = prov$completeness, files = files)
file <- file.path(out, "manifest.json")
write_json(manifest, file, auto_unbox = TRUE, pretty = TRUE, na = "null", null = "null", digits = NA)
writeLines(paste0(digest(file = file, algo = "sha256"), "  manifest.json"),
           file.path(out, "manifest.sha256"), useBytes = TRUE)
