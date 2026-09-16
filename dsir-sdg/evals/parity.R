# Development-only reference runner. The distributed skill does not use R.
library(callr)
library(jsonlite)

arguments <- commandArgs(trailingOnly = TRUE)
if (length(arguments) != 3L) {
  stop("Usage: Rscript parity.R spec.json reference.json process_status.json")
}
spec_path <- normalizePath(arguments[[1L]], winslash = "/", mustWork = TRUE)
output_path <- normalizePath(arguments[[2L]], winslash = "/", mustWork = FALSE)
process_path <- normalizePath(arguments[[3L]], winslash = "/", mustWork = FALSE)

child_error <- NULL
child_ok <- tryCatch({
  callr::r(function(spec_path, output_path) {
    library(DSIR)
    library(jsonlite)

    spec <- jsonlite::fromJSON(spec_path, simplifyVector = FALSE)
    reference <- new.env(parent = asNamespace("DSIR"))
    files <- c("clean_schema.R", "m49_to_iso3.R", "iso3_to_m49.R",
               "http.R", "sdg.R", "sdg_coverage.R")
    source_paths <- file.path(spec$source_dir, "R", files)
    if (!all(file.exists(source_paths))) stop("Required original DSIR source is missing.")
    for (source_path in source_paths) sys.source(source_path, envir = reference)
    # Source the versioned country asset too; never silently use another release.
    load(file.path(spec$source_dir, "data", "who_countries.rda"), envir = reference)
    report <- list(
      status = "running", run_id = spec$run_id, r_version = R.version.string,
      dsir_installed_version = as.character(utils::packageVersion("DSIR")),
      dsir_source_version = read.dcf(file.path(spec$source_dir, "DESCRIPTION"))[1, "Version"],
      source_revision = spec$source_revision,
      source_md5 = as.list(stats::setNames(unname(tools::md5sum(source_paths)), files)),
      source_matches_installed = list(
        sdg_data = identical(body(reference$sdg_data), body(DSIR::sdg_data)),
        sdg_clean = identical(body(reference$sdg_clean), body(DSIR::sdg_clean))),
      who_countries = reference$who_countries,
      common_raw = list(), live_queries = list()
    )
    save_report <- function() {
      jsonlite::write_json(report, output_path, pretty = TRUE, auto_unbox = TRUE,
                           dataframe = "rows", na = "null", null = "null", digits = NA)
    }
    observe <- function(code) {
      warnings <- character()
      result <- tryCatch(withCallingHandlers(
        force(code),
        warning = function(w) {
          warnings <<- c(warnings, conditionMessage(w))
          invokeRestart("muffleWarning")
        },
        message = function(m) invokeRestart("muffleMessage")
      ), error = function(e) list(status = "error", message = conditionMessage(e)))
      result$warnings <- as.list(warnings)
      result
    }
    to_frame <- function(rows) {
      if (!length(rows)) return(data.frame())
      jsonlite::fromJSON(jsonlite::toJSON(rows, auto_unbox = TRUE,
                                        null = "null", digits = NA), simplifyVector = TRUE)
    }
    clean_result <- function(raw) {
      cleaned <- reference$sdg_clean(raw)
      list(status = "ok", clean = cleaned, raw_rows = nrow(raw),
           clean_rows = nrow(cleaned), clean_columns = as.list(names(cleaned)),
           clean_types = as.list(vapply(cleaned, typeof, character(1))))
    }
    common <- jsonlite::fromJSON(spec$common_raw_path, simplifyVector = FALSE)
    for (query in common$queries) {
      cat("R common-input cleaning:", query$id, "\n")
      result <- observe(clean_result(to_frame(query$records)))
      result$id <- query$id
      report$common_raw[[length(report$common_raw) + 1L]] <- result
      save_report()
    }
    if (isTRUE(spec$live_r)) {
      for (query in common$queries) {
        if (isTRUE(query$synthetic)) next
        cat("R independent live retrieval:", query$id, "\n")
        result <- observe({
          args <- query$args
          if (is.null(args$indicator)) args$indicator <- query$indicator
          r_args <- list(indicator = unlist(args$indicator, use.names = FALSE))
          if (!is.null(args$locations)) r_args$area <- as.character(unlist(args$locations, use.names = FALSE))
          if (!is.null(args$year_from)) r_args$year_from <- args$year_from
          if (!is.null(args$year_to)) r_args$year_to <- args$year_to
          if (!is.null(args$page_size)) r_args$page_size <- args$page_size
          raw <- do.call(reference$sdg_data, r_args)
          # DSIR accepts no series/dimension argument. Apply documented subset
          # rules only when the comparison snapshot explicitly requests them.
          if (!is.null(args$series) && nrow(raw) > 0L) {
            raw <- raw[raw$series %in% unlist(args$series, use.names = FALSE), , drop = FALSE]
          }
          if (!is.null(args$dimensions) && nrow(raw) > 0L) {
            for (dimension in names(args$dimensions)) {
              if (!dimension %in% names(raw$dimensions)) stop("Requested dimension absent from R data.")
              keep <- raw$dimensions[[dimension]] %in% unlist(args$dimensions[[dimension]], use.names = FALSE)
              raw <- raw[keep, , drop = FALSE]
            }
          }
          result <- clean_result(raw)
          result$raw <- raw
          result
        })
        result$id <- query$id
        report$live_queries[[length(report$live_queries) + 1L]] <- result
        save_report()
      }
    }
    report$status <- "complete"
    save_report()
    TRUE
  }, args = list(spec_path, output_path), timeout = 2400, stdout = "", stderr = "")
}, error = function(e) {
  child_error <<- conditionMessage(e)
  FALSE
})

jsonlite::write_json(list(child_ok = isTRUE(child_ok), message = child_error),
                     process_path, auto_unbox = TRUE, null = "null", pretty = TRUE)
# The caller checks child_ok and every reference result, not just this exit code.
quit(status = 0L)
