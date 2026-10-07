# Development-only parity against the exact DSIR 0.11.0 source files.
library(callr)
library(jsonlite)

arguments <- commandArgs(trailingOnly = TRUE)
if (length(arguments) != 3L) stop("Usage: Rscript parity.R spec.json reference.json process_status.json")
spec_path <- normalizePath(arguments[[1L]], winslash = "/", mustWork = TRUE)
output_path <- normalizePath(arguments[[2L]], winslash = "/", mustWork = FALSE)
process_path <- normalizePath(arguments[[3L]], winslash = "/", mustWork = FALSE)
child_error <- NULL

child_ok <- tryCatch({
  callr::r(function(spec_path, output_path) {
    library(jsonlite)
    library(digest)
    library(httr2)
    library(cli)
    library(tibble)
    library(vctrs)

    spec <- jsonlite::fromJSON(spec_path, simplifyVector = FALSE)
    reference <- new.env(parent = globalenv())
    source_files <- unlist(spec$source_files, use.names = FALSE)
    for (file in source_files[grepl("^R/", source_files)]) {
      sys.source(file.path(spec$source_dir, file), envir = reference)
    }
    load(file.path(spec$source_dir, "data", "who_countries.rda"), envir = reference)
    options(DSIR.who_backend = "xmart", DSIR.who_base_url = "https://xmart-api-public.who.int")
    hashes <- lapply(source_files, function(file) digest::digest(
      file = file.path(spec$source_dir, file), algo = "sha256", serialize = FALSE))
    names(hashes) <- source_files
    description <- read.dcf(file.path(spec$source_dir, "DESCRIPTION"))
    report <- list(status = "running", r_version = R.version.string,
                   dsir_version = unname(description[1, "Version"]),
                   source_revision = spec$source_revision, source_hashes = hashes,
                   reference_mode = "unmodified pinned source and source RDA; installed DSIR unused",
                   who_countries = reference$who_countries, queries = list(), common_raw = list())
    save_report <- function() {
      jsonlite::write_json(report, output_path, pretty = TRUE, auto_unbox = TRUE,
                           dataframe = "rows", na = "null", null = "null", digits = NA)
    }
    observe <- function(code) {
      warnings <- character()
      answer <- tryCatch(withCallingHandlers(force(code),
        warning = function(w) {
          warnings <<- c(warnings, conditionMessage(w))
          invokeRestart("muffleWarning")
        }, message = function(m) invokeRestart("muffleMessage")
      ), error = function(e) list(status = "error", message = conditionMessage(e)))
      answer$warnings <- as.list(warnings)
      answer
    }
    catalogue_available <- FALSE
    if (!isTRUE(spec$offline)) {
      cat("R fresh xMart directory reference\n")
      catalog_result <- observe({
        catalog <- reference$gho_indicators()
        list(status = if (nrow(catalog)) "ok" else "unverified", rows = nrow(catalog))
      })
      report$catalogue <- catalog_result
      catalogue_available <- identical(catalog_result$status, "ok")
    }
    for (query in spec$queries) {
      cat("R live reference:", query$id, "\n")
      if (!catalogue_available) {
        result <- list(id = query$id, status = "blocked", reason = "Independent R xMart directory retrieval failed")
      } else {
        result <- observe({
          args <- query$args
          r_args <- list(indicator = args$indicator)
          if (!is.null(args$locations)) r_args$area <- unlist(args$locations, use.names = FALSE)
          if (!is.null(args$spatial_type)) r_args$spatial_type <- tolower(args$spatial_type)
          if (!is.null(args$year_from)) r_args$year_from <- args$year_from
          if (!is.null(args$year_to)) r_args$year_to <- args$year_to
          named <- list()
          for (key in names(args$dimensions)) {
            values <- unlist(args$dimensions[[key]], use.names = FALSE)
            if (key %in% c("dim1", "dim2", "dim3")) r_args[[key]] <- values else named[[key]] <- values
          }
          if (length(named)) r_args$dimensions <- named
          raw <- do.call(reference$gho_data, r_args)
          cleaned <- reference$gho_clean(raw)
          list(status = if (nrow(raw)) "ok" else "unverified", raw = raw, clean = cleaned,
               raw_rows = nrow(raw), clean_rows = nrow(cleaned),
               clean_columns = as.list(names(cleaned)), clean_types = as.list(vapply(cleaned, typeof, character(1))))
        })
      }
      result$id <- query$id
      report$queries[[length(report$queries) + 1L]] <- result
      save_report()
    }
    common <- jsonlite::fromJSON(spec$common_raw_path, simplifyVector = FALSE)
    to_frame <- function(rows) {
      if (!length(rows)) return(data.frame())
      # Build typed scalar columns directly. jsonlite's data-frame simplifier
      # can convert an all-"NA" string column to logical NA, corrupting this
      # transformation-only input before the reference cleaner sees it.
      fields <- unique(unlist(lapply(rows, names), use.names = FALSE))
      columns <- lapply(fields, function(field) {
        values <- lapply(rows, function(row) row[[field]])
        if (any(vapply(values, is.character, logical(1)))) {
          return(vapply(values, function(value) if (is.null(value)) NA_character_ else as.character(value), character(1)))
        }
        if (any(vapply(values, is.numeric, logical(1)))) {
          return(vapply(values, function(value) if (is.null(value)) NA_real_ else as.numeric(value), numeric(1)))
        }
        vapply(values, function(value) if (is.null(value)) NA else as.logical(value), logical(1))
      })
      names(columns) <- fields
      as.data.frame(columns, stringsAsFactors = FALSE, check.names = FALSE)
    }
    reference$.dsi_cache$gho_indicator_catalog <- to_frame(common$catalogue)
    reference$.dsi_cache$gho_catalog_key <- "xmart|https://xmart-api-public.who.int"
    for (query in common$queries) {
      result <- observe({
        if (!is.null(query$native)) {
          # Memory-only input fixtures, equivalent to the source's own mock tests.
          # No source function body is replaced and no observations are published.
          reference$.who_cache[["xmart|https://xmart-api-public.who.int|geo"]] <-
            list(time = Sys.time(), value = tibble::as_tibble(to_frame(query$geo)))
          context <- query$context
          context$dimensions <- unlist(context$dimensions, use.names = FALSE)
          context$fields <- unlist(context$fields, use.names = FALSE)
          raw <- reference$.xmart_gho_normalize(to_frame(query$native), context)
        } else raw <- to_frame(query$records)
        cleaned <- reference$gho_clean(raw)
        list(status = "ok", normalized = if (!is.null(query$native)) raw else NULL,
             clean = cleaned, clean_rows = nrow(cleaned), clean_columns = as.list(names(cleaned)),
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
jsonlite::write_json(list(child_ok = isTRUE(child_ok), message = child_error),
                    process_path, pretty = TRUE, auto_unbox = TRUE, null = "null")
quit(status = if (isTRUE(child_ok)) 0L else 1L)
