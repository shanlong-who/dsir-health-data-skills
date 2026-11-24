suppressPackageStartupMessages({library(httr2); library(magrittr)})
source("scripts/ghe_spec.R")
# Use raw xMart fields and disjoint roster queries to cross-check the DSIR export.
# Include all 38 codes in the regional audit, even those with no DSIR rows.
observed <- read.csv(file.path(out, "observations.csv"), na.strings = "", colClasses = c(cause_code = "character"))
compare.fields <- c("area_code", "year", "sex", "age", "cause_code", "value", "low", "high")
fields <- c("DIM_COUNTRY_CODE", "DIM_YEAR_CODE", "DIM_SEX_CODE", "DIM_AGEGROUP_CODE",
            "DIM_GHECAUSE_CODE", "VAL_DTHS_COUNT_NUMERIC", "VAL_DTHS_COUNT_LOW", "VAL_DTHS_COUNT_HIGH")
fetch_batch <- function(codes) {
  selection <- paste0("DIM_COUNTRY_CODE in ('", paste(codes, collapse = "','"),
                      "') and DIM_GHECAUSE_CODE eq 0 and DIM_AGEGROUP_CODE eq 'TOTAL'",
                      " and DIM_SEX_CODE in ('FEMALE','MALE','TOTAL')")
  if (pilot) selection <- paste(selection, "and DIM_YEAR_CODE eq 2023")
  query <- request(endpoint) %>% req_url_query(`$filter` = selection, `$select` = paste(fields, collapse = ","),
                     `$top` = 5000L, `$count` = "true", `$orderby` = "Sys_PK")
  response <- query %>% req_timeout(100) %>% req_retry(max_tries = 3) %>% req_perform() %>%
    resp_body_json(simplifyVector = TRUE)
  count <- response[["@odata.count"]]
  stopifnot(length(count) == 1L, !is.na(count), count < 5000L,
            is.null(response[["@odata.nextLink"]]))
  if (count == 0L) {
    stopifnot(length(response$value) == 0L || NROW(response$value) == 0L)
    return(observed[FALSE, compare.fields])
  }
  rows <- response$value
  stopifnot(nrow(rows) == count, all(fields %in% names(rows)))
  rows <- setNames(rows[fields], compare.fields)
  rows$cause_code <- as.character(rows$cause_code)
  rows
}
groups <- split(roster$area_code, ceiling(seq_len(nrow(roster)) / 6L))
reference <- do.call(rbind, lapply(groups, fetch_batch))
sort_rows <- function(data) {
  data <- data[do.call(order, data[c("area_code", "year", "sex")]), compare.fields]
  rownames(data) <- NULL
  data
}
stopifnot(isTRUE(all.equal(sort_rows(reference), sort_rows(observed), tolerance = 1e-12, check.attributes = FALSE)))
cat(nrow(reference), "rows independently matched via raw WHO xMart fields across", nrow(roster), "roster areas.\n")
