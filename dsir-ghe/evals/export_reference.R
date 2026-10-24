library(jsonlite)
library(digest)
library(DSIR)

# Run from the repository root with the pinned DSIR in an isolated R library.
source.root <- "../reference/DSIR"
target.root <- "dsir-ghe/references/metadata"
source.commit <- system2("git", c("-C", shQuote(source.root), "rev-parse", "HEAD"), stdout = TRUE)
stopifnot(identical(source.commit, "5a5accbedf51aa4a6b3288c82269edd7e831e831"),
          as.character(packageVersion("DSIR")) == "0.11.0")
hash_file <- function(path) digest(readBin(path, "raw", n = file.info(path)$size),
                                   algo = "sha256", serialize = FALSE)
country.environment <- new.env()
load(file.path(source.root, "data/who_countries.rda"), envir = country.environment)
country.data <- as.data.frame(country.environment$who_countries)
existing.path <- "dsir-sdg/references/metadata/who_countries.json"
stopifnot(isTRUE(all.equal(country.data, fromJSON(existing.path), check.attributes = FALSE)),
          nrow(country.data) == 194L, !anyDuplicated(country.data$iso3),
          !anyDuplicated(country.data$m49_code))
dir.create(target.root, recursive = TRUE, showWarnings = FALSE)
stopifnot(file.copy(existing.path, file.path(target.root, "who_countries.json"), overwrite = FALSE))
measures <- getFromNamespace(".ghe_measures", "DSIR")()
write_json(measures, file.path(target.root, "measures.json"), pretty = TRUE,
           auto_unbox = TRUE, na = "null", digits = NA)
provenance <- list(
  source_package = "DSIR", source_version = "0.11.0", source_commit = source.commit,
  source_repository = "https://github.com/shanlong-who/DSIR",
  source_files = list(
    countries = list(path = "data/who_countries.rda",
      sha256 = hash_file(file.path(source.root, "data/who_countries.rda"))),
    measures = list(path = "R/ghe.R", sha256 = hash_file(file.path(source.root, "R/ghe.R")))),
  exported_on = as.character(Sys.Date()), row_count = nrow(country.data),
  export_method = "Country JSON reused after equality verification against pinned RDA; measure definitions exported from pinned DSIR using R.",
  files = list(
    who_countries = hash_file(file.path(target.root, "who_countries.json")),
    measures = hash_file(file.path(target.root, "measures.json"))),
  country_scope = "WHO Member States in a fixed DSIR snapshot, not all provider areas or historical membership.",
  regional_vintage_as_documented_by_dsir = "May 2025; Indonesia assigned to WPR.",
  income_vintage_as_documented_by_dsir = "World Bank FY2027, based on 2025 GNI per capita.",
  notes = c("M49 codes retain leading zeros; Namibia's ISO2 is the literal string NA.",
    "Country mappings do not establish GHE data availability.",
    "Measure definitions are retained only when their fields exist in the current API schema.",
    "This package is an independent DSIR tool, not an official WHO product."))
write_json(provenance, file.path(target.root, "provenance.json"), pretty = TRUE,
           auto_unbox = TRUE, na = "null")
cat("Exported", nrow(country.data), "country records and", nrow(measures), "measure definitions.\n")
