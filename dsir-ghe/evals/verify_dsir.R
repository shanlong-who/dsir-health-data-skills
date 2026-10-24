#!/usr/bin/env Rscript
# Independent transformation replay by default; --live also re-queries WHO.
library(DSIR)
library(jsonlite)
library(httr2)
library(testthat)

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3L) {
  stop("Usage: verify_dsir.R <live-evidence-directory> <synthetic-directory> <new-output-directory> [--live]")
}
live.root <- normalizePath(args[[1]], winslash = "/", mustWork = TRUE)
fixture.root <- normalizePath(args[[2]], winslash = "/", mustWork = TRUE)
output.root <- args[[3]]
live.enabled <- "--live" %in% args
stopifnot(as.character(packageVersion("DSIR")) == "0.11.0", !file.exists(output.root))
dir.create(output.root, recursive = TRUE)
options(DSIR.who_max_rows = 5000L)

read_result <- function(path) {
  result <- fromJSON(file.path(path, "response.json"), simplifyVector = FALSE)
  result$raw <- fromJSON(file.path(path, "raw.json"), simplifyVector = FALSE)
  result
}
as_frame <- function(rows) {
  fromJSON(toJSON(rows, auto_unbox = TRUE, null = "null", digits = NA))
}
query_arguments <- function(query) {
  keep <- c("area", "year", "year_from", "year_to", "sex", "age", "cause", "measure")
  lapply(query[intersect(keep, names(query))], function(value) if (is.null(value)) NULL else unlist(value))
}
assert_same <- function(actual, expected) {
  fields <- c("iso3", "location_name", "year", "sex", "age", "cause_code", "cause_name",
    "measure", "value", "low", "high", "population", "unit", "level", "cause_group", "rankable")
  stopifnot(identical(names(actual), fields), nrow(actual) == length(expected))
  if (!length(expected)) return(invisible(TRUE))
  expected <- as_frame(expected)
  keys <- c("iso3", "year", "sex", "age", "cause_code", "measure")
  actual <- actual[do.call(order, actual[keys]), ]
  expected <- expected[do.call(order, expected[keys]), ]
  for (field in fields) {
    a <- actual[[field]]
    b <- expected[[field]]
    stopifnot(identical(is.na(a), is.na(b)))
    present <- !is.na(a)
    if (field %in% c("year", "value", "low", "high", "population", "level")) {
      stopifnot(isTRUE(all.equal(as.numeric(a[present]), as.numeric(b[present]), tolerance = 1e-10)))
    } else {
      stopifnot(identical(as.character(a[present]), as.character(b[present])))
    }
  }
  invisible(TRUE)
}

replay_dsir <- function(result) {
  definitions <- getFromNamespace(".ghe_measures", "DSIR")()
  dimensions <- function(dimension = "measure") {
    if (dimension == "measure") return(definitions)
    value <- if (dimension == "year" && is.null(result$query$year)) c(2022L, 2023L) else
      unlist(result$query[[dimension]])
    data.frame(code = as.character(value), label = as.character(value))
  }
  fields <- if (length(result$raw)) names(result$raw[[1]]) else
    c("Sys_PK", "DIM_COUNTRY_CODE", "DIM_YEAR_CODE", "DIM_SEX_CODE", "DIM_AGEGROUP_CODE",
      "DIM_GHECAUSE_CODE", "DIM_GHECAUSE_TITLE", "ATTR_POPULATION_NUMERIC",
      "FLAG_LEVEL", "DIM_CAUSE_GROUP", "FLAG_RANKABLE", definitions$field)
  local_mocked_bindings(ghe_dimensions = dimensions,
    ghe_causes = function(search = NULL) data.frame(cause_code = unlist(result$query$cause)),
    .xmart_fields = function(path) fields, .package = "DSIR")
  body <- charToRaw(toJSON(list("@odata.count" = length(result$raw), value = result$raw),
    auto_unbox = TRUE, null = "null", digits = NA))
  with_mocked_responses(function(req) response(status_code = 200L,
    headers = list("content-type" = "application/json"), body = body),
    do.call(ghe_data, query_arguments(result$query)))
}

cases <- list("all-measures" = file.path(live.root, "all-measures"),
  "sex-age-paging" = file.path(live.root, "sex-age-paging"),
  "diabetes" = file.path(live.root, "diabetes"),
  "verified-empty" = file.path(live.root, "verified-empty"),
  "synthetic-missing-zero" = fixture.root)
report <- list(dsir_version = as.character(packageVersion("DSIR")),
  dsir_reference_commit = "5a5accbedf51aa4a6b3288c82269edd7e831e831",
  executed_at = format(Sys.time(), tz = "UTC", usetz = TRUE), live_enabled = live.enabled, cases = list())
for (name in names(cases)) {
  result <- read_result(cases[[name]])
  modes <- if (live.enabled && name %in% c("all-measures", "sex-age-paging", "diabetes")) c("replay", "live") else "replay"
  for (mode in modes) {
    warnings <- character()
    actual <- withCallingHandlers(
      if (mode == "live") do.call(ghe_data, query_arguments(result$query)) else replay_dsir(result),
      warning = function(w) { warnings <<- c(warnings, conditionMessage(w)); invokeRestart("muffleWarning") })
    if (length(warnings)) stop(paste(warnings, collapse = "\n"))
    assert_same(actual, result$data)
    write.csv(actual, file.path(output.root, paste0(name, "-", mode, ".csv")), row.names = FALSE, na = "")
    item <- list(case = name, mode = mode, rows = nrow(actual), fields_compared = 16L,
      passed = TRUE, warnings = warnings, dsir_provenance = attr(actual, "who_provenance"),
      synthetic = identical(name, "synthetic-missing-zero"))
    report$cases[[length(report$cases) + 1L]] <- item
    cat(name, mode, nrow(actual), "rows: PASS\n")
  }
}
report$passed <- TRUE
write_json(report, file.path(output.root, "results.json"), auto_unbox = TRUE, pretty = TRUE,
  null = "null", na = "null", digits = NA)
