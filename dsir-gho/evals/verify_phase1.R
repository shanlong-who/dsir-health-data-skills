library(jsonlite)
library(pkgload)

# Compare independent same-backend extracts only. No cross-backend merging.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 3L) {
  stop("Usage: Rscript verify_phase1.R DSIR_source skill_live_directory new_output_directory")
}
source.path <- normalizePath(args[[1]], winslash = "/", mustWork = TRUE)
skill.path <- normalizePath(args[[2]], winslash = "/", mustWork = TRUE)
output.path <- args[[3]]
if (dir.exists(output.path)) stop("Use a new output directory.")
dir.create(output.path, recursive = TRUE)
load_all(source.path, quiet = TRUE, helpers = FALSE)

results <- list()
for (backend in c("legacy", "xmart")) {
  case.name <- if (backend == "legacy") "legacy-default-dtp" else "xmart-dtp"
  skill.result <- read_json(file.path(skill.path, case.name, "response.json"), simplifyVector = TRUE)
  stopifnot(skill.result$provenance$backend == backend, skill.result$provenance$complete)
  warning.messages <- character()
  check <- tryCatch(withCallingHandlers({
    raw <- gho_data("WHS4_100", area = c("PHL", "CHN"), spatial_type = "country",
                    year_from = 2020, year_to = 2021, backend = backend)
    provenance <- attr(raw, "who_provenance")
    stopifnot(is.data.frame(raw), nrow(raw) > 0L, isTRUE(provenance$complete))
    clean <- as.data.frame(gho_clean(raw))
    skill.data <- as.data.frame(skill.result$data)
    # Same rows and ordering for this explicit two-country, two-year sample.
    clean <- clean[order(clean$location, clean$year), , drop = FALSE]
    skill.data <- skill.data[order(skill.data$location, skill.data$year), , drop = FALSE]
    rownames(clean) <- rownames(skill.data) <- NULL
    stopifnot(identical(names(clean), names(skill.data)), nrow(clean) == nrow(skill.data))
    comparison <- vapply(names(clean), function(field) {
      left <- clean[[field]]
      right <- skill.data[[field]]
      if (all(is.na(left)) && all(is.na(right))) return(TRUE)
      isTRUE(all.equal(left, right, tolerance = 1e-10, check.attributes = FALSE))
    }, logical(1))
    saveRDS(raw, file.path(output.path, paste0(backend, "-raw.rds")))
    write_json(list(data = clean, provenance = provenance),
               file.path(output.path, paste0(backend, "-dsir.json")),
               auto_unbox = TRUE, pretty = TRUE, null = "null", na = "null", digits = NA)
    list(passed = all(comparison), rows = nrow(clean), field_matches = as.list(comparison))
  }, warning = function(w) {
    warning.messages <<- c(warning.messages, conditionMessage(w))
    invokeRestart("muffleWarning")
  }), error = function(e) list(passed = FALSE, error = conditionMessage(e)))
  check$warnings <- warning.messages
  results[[backend]] <- check
  print(check)
}
report <- list(completed_at = format(Sys.time(), tz = "UTC", usetz = TRUE),
               r_version = R.version.string, dsir_version = as.character(packageVersion("DSIR")),
               scope = "Independent same-backend WHS4_100, PHL/CHN, 2020/2021; no cross-backend equivalence claim",
               results = results)
write_json(report, file.path(output.path, "summary.json"), auto_unbox = TRUE,
           pretty = TRUE, null = "null", na = "null")
if (!all(vapply(results, function(x) isTRUE(x$passed), logical(1)))) stop("Same-backend comparison failed.")
