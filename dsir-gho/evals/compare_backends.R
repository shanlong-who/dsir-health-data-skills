# Maintainer-only comparison of independently retrieved backend extracts.
# Callers supply reviewed, explicitly mapped keys; this file never queries WHO.
library(jsonlite)

backend_review_issues <- function(review) {
  nonempty <- function(x) is.character(x) && length(x) == 1L &&
    !is.na(x) && nzchar(trimws(x))
  issues <- character()
  if (!isTRUE(review$approved)) issues <- c(issues, "Review is not approved.")
  for (field in c("reviewed_by", "reviewed_at", "legacy_code", "xmart_code")) {
    if (!nonempty(review[[field]])) issues <- c(issues, paste("Missing", field))
  }
  checks <- c("catalogues", "definition", "unit", "population", "estimate_type",
              "geography", "time", "dimensions", "release")
  for (field in checks) {
    check <- review$checks[[field]]
    if (!identical(check$status, "verified") || !nonempty(check$evidence)) {
      issues <- c(issues, paste("Unverified", field))
    }
  }
  issues
}

compare_backend_extracts <- function(legacy, xmart, review, key_fields,
                                     value_fields = c("value_num", "low", "high"),
                                     abs_tol = 1e-10, rel_tol = 1e-12) {
  issues <- backend_review_issues(review)
  if (length(issues)) return(list(status = "unverified", issues = issues,
                                   values_compared = FALSE))
  if (!identical(key_fields, unlist(review$key_fields, use.names = FALSE))) {
    stop("Key fields must match the complete reviewed dimension mapping.")
  }
  if (!length(key_fields) || anyDuplicated(c(key_fields, value_fields)) ||
      !length(value_fields)) stop("Supply distinct, complete keys and numeric value fields.")
  if (length(abs_tol) != 1L || length(rel_tol) != 1L ||
      !is.finite(abs_tol) || !is.finite(rel_tol) || abs_tol < 0 || rel_tol < 0) {
    stop("Tolerances must be finite and non-negative.")
  }
  extracts <- list(legacy = legacy, xmart = xmart)
  keys <- list()
  for (backend in names(extracts)) {
    extract <- extracts[[backend]]
    if (!identical(extract$indicator_code, review[[paste0(backend, "_code")]])) {
      return(list(status = "unverified", issues = paste("Indicator differs from review:", backend),
                  values_compared = FALSE))
    }
    provenance <- extract$provenance
    if (!identical(provenance$backend, backend) || !isTRUE(provenance$complete) ||
        any(!vapply(provenance[c("query_url", "retrieved_at")],
                    function(x) is.character(x) && length(x) == 1L &&
                      !is.na(x) && nzchar(x), logical(1))) ||
        !all(c("query_url", "retrieved_at") %in% names(provenance))) {
      return(list(status = "incomplete", issues = paste("Unverified retrieval:", backend),
                  values_compared = FALSE))
    }
    data <- extract$data
    if (!is.data.frame(data) || !all(c(key_fields, value_fields) %in% names(data))) {
      stop("Each extract must contain all reviewed key and value fields.")
    }
    if (anyNA(data[key_fields])) stop("Unknown key values cannot establish matching strata.")
    if (!all(vapply(data[value_fields], function(x) is.numeric(x) &&
                    all(is.na(x) | is.finite(x)), logical(1)))) {
      stop("Value fields must be numeric; missing values must remain NA.")
    }
    keys[[backend]] <- vapply(seq_len(nrow(data)), function(i) {
      toJSON(lapply(data[i, key_fields, drop = FALSE], as.character), auto_unbox = TRUE)
    }, character(1))
    if (anyDuplicated(keys[[backend]])) {
      return(list(status = "ambiguous_keys", issues = paste("Duplicate reviewed keys:", backend),
                  values_compared = FALSE))
    }
  }
  legacy_only <- which(!keys$legacy %in% keys$xmart)
  xmart_only <- which(!keys$xmart %in% keys$legacy)
  left <- which(keys$legacy %in% keys$xmart)
  right <- match(keys$legacy[left], keys$xmart)
  differences <- list()
  for (field in value_fields) {
    a <- legacy$data[[field]][left]
    b <- xmart$data[[field]][right]
    equal <- (is.na(a) & is.na(b)) | (!is.na(a) & !is.na(b) &
               abs(a - b) <= abs_tol + rel_tol * pmax(abs(a), abs(b)))
    changed <- which(!equal)
    if (length(changed)) {
      differences[[field]] <- cbind(legacy$data[left[changed], key_fields, drop = FALSE],
        data.frame(field = field, legacy = a[changed], xmart = b[changed],
                   delta = b[changed] - a[changed]))
    }
  }
  list(status = if (!length(left)) "no_overlap" else if
       (length(differences) || length(legacy_only) || length(xmart_only)) "differences" else "equal",
       values_compared = length(left) > 0L, matched_rows = length(left),
       legacy_only = legacy$data[legacy_only, key_fields, drop = FALSE],
       xmart_only = xmart$data[xmart_only, key_fields, drop = FALSE],
       differences = differences, review = review,
       key_fields = key_fields, value_fields = value_fields,
       provenance = lapply(extracts, `[[`, "provenance"),
       tolerance = list(absolute = abs_tol, relative = rel_tol))
}
