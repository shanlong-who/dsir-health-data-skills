suppressPackageStartupMessages({
  library(DSIR)
  library(jsonlite)
  library(digest)
})
source("scripts/ghe_spec.R")
# Selection without an area filter includes territories absent from a recent reference slice.
# Each regional query selects a single sex. The pilot selects one country and one year.
requests <- if (pilot) list(sex.codes) else as.list(sex.codes)
fetch <- function(sexes) {
  result <- ghe_data(area = if (pilot) "PHL", year = if (pilot) 2023L,
                     sex = sexes, age = "TOTAL", cause = 0, measure = "deaths")
  acquisition <- dsir_metadata(result)$sources
  stopifnot(nrow(acquisition) == 1L, acquisition$status == "success", acquisition$complete,
            acquisition$endpoint == endpoint, acquisition$backend == "xmart",
            acquisition$record_count == nrow(result), nrow(result) > 0L,
            all(result$sex %in% sexes))
  list(rows = as.data.frame(result[result$iso3 %in% roster$area_code, ]),
       source = acquisition)
}
batches <- lapply(requests, fetch)
d <- do.call(rbind, lapply(batches, "[[", "rows"))
names(d)[names(d) == "iso3"] <- "area_code"
d$area_name <- roster$area_name[match(d$area_code, roster$area_code)]
d <- d[do.call(order, d[key]), c(key, "area_name", "cause_name", "value", "low", "high", "unit", "population")]
validate_rows(d)
dir.create(file.path(out, "areas"), recursive = TRUE, showWarnings = FALSE)
write.csv(d, file.path(out, "observations.csv"), row.names = FALSE, na = "", fileEncoding = "UTF-8")
for (code in unique(d$area_code)) {
  write.csv(d[d$area_code == code, ], file.path(out, "areas", paste0(code, ".csv")),
            row.names = FALSE, na = "", fileEncoding = "UTF-8")
}
stale <- setdiff(list.files(file.path(out, "areas")), paste0(unique(d$area_code), ".csv"))
if (length(stale)) stop("Stale area files in output directory: ", paste(stale, collapse = ", "))
sources <- do.call(rbind, lapply(batches, "[[", "source"))
p <- list(product = product, actual_backend = "xmart", table = "DEX_CMS/GHE_FULL", scope = scope,
          selection = indicator, package_version = as.character(packageVersion("DSIR")),
          retrieved_at = max(sources$retrieved_at), run_id = Sys.getenv("GITHUB_RUN_ID", "local"),
          sources = sources, roster_source = "https://www.who.int/westernpacific/about/where-we-work",
          geography_basis = if (pilot) "Philippines, 2023 pilot" else "Current Western Pacific roster applied to all available years",
          observations_sha256 = digest(file = file.path(out, "observations.csv"), algo = "sha256"))
write_metadata(p, file.path(out, "provenance.json"))
cat(nrow(d), "observations from", length(unique(d$area_code)), "of", nrow(roster), "areas\n")
