# Development-only reference runner. R is not required by the installed skill.
library(callr)

arguments <- commandArgs(trailingOnly = TRUE)
if (length(arguments) != 3L) {
  cat("Usage: Rscript parity.R spec.json reference.json process_status.json\n")
  quit(status = 0L)
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
    source_file <- file.path(spec$source_dir, "R", "gho.R")
    if (!file.exists(source_file)) stop("The pinned original DSIR R/gho.R source is missing.")
    # Evaluate unmodified original source in an isolated environment. No source
    # file or package namespace is changed. Helpers/data come from installed DSIR.
    sys.source(source_file, envir = reference)
    source_matches_installed <- list(
      gho_data = identical(body(reference$gho_data), body(DSIR::gho_data)),
      gho_clean = identical(body(reference$gho_clean), body(DSIR::gho_clean))
    )
    report <- list(
      status = "running", r_version = R.version.string,
      dsir_version = as.character(utils::packageVersion("DSIR")),
      source_file = normalizePath(source_file, winslash = "/"),
      source_revision = spec$source_revision,
      source_md5 = unname(tools::md5sum(source_file)),
      source_matches_installed = source_matches_installed,
      who_countries = DSIR::who_countries,
      queries = list(), common_raw = list()
    )
    save_report <- function() {
      jsonlite::write_json(report, output_path, pretty = TRUE, auto_unbox = TRUE,
                           dataframe = "rows", na = "null", null = "null", digits = NA)
    }
    observe <- function(code) {
      warnings <- character()
      answer <- tryCatch(withCallingHandlers(
        force(code),
        warning = function(w) {
          warnings <<- c(warnings, conditionMessage(w))
          invokeRestart("muffleWarning")
        },
        message = function(m) invokeRestart("muffleMessage")
      ), error = function(e) list(status = "error", message = conditionMessage(e)))
      answer$warnings <- as.list(warnings)
      answer
    }

    for (query in spec$queries) {
      cat("R live reference:", query$id, "\n")
      result <- observe({
        args <- query$args
        r_args <- list(indicator = args$indicator)
        if (!is.null(args$locations)) r_args$area <- unlist(args$locations, use.names = FALSE)
        if (!is.null(args$spatial_type)) r_args$spatial_type <- tolower(args$spatial_type)
        if (!is.null(args$year_from)) r_args$year_from <- args$year_from
        if (!is.null(args$year_to)) r_args$year_to <- args$year_to
        for (key in names(args$dimensions)) {
          r_args[[key]] <- unlist(args$dimensions[[key]], use.names = FALSE)
        }
        raw <- do.call(reference$gho_data, r_args)
        cleaned <- reference$gho_clean(raw)
        list(status = "ok", id = query$id, raw = raw, clean = cleaned,
             raw_rows = nrow(raw), clean_rows = nrow(cleaned),
             raw_columns = as.list(names(raw)), clean_columns = as.list(names(cleaned)),
             clean_types = as.list(vapply(cleaned, typeof, character(1))))
      })
      result$id <- query$id
      report$queries[[length(report$queries) + 1L]] <- result
      save_report()
    }

    # Diagnose transformations independently of API revisions or row ordering by
    # feeding the Python response and catalogue into the original R cleaner.
    common <- jsonlite::fromJSON(spec$common_raw_path, simplifyVector = FALSE)
    to_frame <- function(rows) {
      if (!length(rows)) return(data.frame())
      jsonlite::fromJSON(jsonlite::toJSON(rows, auto_unbox = TRUE, null = "null", digits = NA),
                        simplifyVector = TRUE)
    }
    reference$.dsi_cache$gho_indicator_catalog <- to_frame(common$catalogue)
    for (query in common$queries) {
      result <- observe({
        cleaned <- reference$gho_clean(to_frame(query$records))
        list(status = "ok", id = query$id, clean = cleaned,
             clean_rows = nrow(cleaned), clean_columns = as.list(names(cleaned)),
             clean_types = as.list(vapply(cleaned, typeof, character(1))))
      })
      result$id <- query$id
      report$common_raw[[length(report$common_raw) + 1L]] <- result
    }
    report$status <- "complete"
    save_report()
    TRUE
  }, args = list(spec_path, output_path), timeout = 1800, stdout = "", stderr = "")
}, error = function(e) {
  child_error <<- conditionMessage(e)
  FALSE
})

# The outer R process exits successfully after recording child-process failure;
# the Python orchestrator treats a failed child as a failed audit, never a pass.
process_json <- paste0(
  '{"parent_exit_policy":0,"child_ok":', if (isTRUE(child_ok)) "true" else "false",
  ',"message":', if (is.null(child_error)) "null" else encodeString(child_error, quote = '"'),
  "}"
)
writeLines(process_json, process_path, useBytes = TRUE)
quit(status = 0L)
