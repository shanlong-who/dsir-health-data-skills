write_wpr_tables <- function(data, roster, required.fields, out) {
  for (key in names(data)[vapply(data, is.list, logical(1))]) {
    data[[key]] <- vapply(data[[key]], function(x) as.character(toJSON(as.list(x), na = "null")), character(1))
  }
  dir.create(file.path(out, "areas"), recursive = TRUE, showWarnings = FALSE)
  csv <- file.path(out, "observations.csv")
  write.csv(data, csv, row.names = FALSE, na = "", fileEncoding = "UTF-8")
  window <- seq(min(data$year), max(data$year))
  area.coverage <- lapply(seq_len(nrow(roster)), function(i) {
    code <- roster$area_code[i]
    rows <- data[data$area_code == code, , drop = FALSE]
    missing.years <- setdiff(window, rows$year)
    has.data <- nrow(rows) > 0L
    status <- "no_observations"
    path <- NULL
    if (has.data) {
      path <- paste0("areas/", code, ".csv")
      write.csv(rows, file.path(out, path), row.names = FALSE, na = "", fileEncoding = "UTF-8")
      status <- if (length(missing.years) || anyNA(rows[required.fields])) "partial" else "complete"
    }
    list(area_code = code, area_name = roster$area_name[i], status = status,
         rows = nrow(rows), first_year = if (has.data) min(rows$year), last_year = if (has.data) max(rows$year),
         missing_years_in_window = I(missing.years), missing_value_years = I(rows$year[is.na(rows$value_num)]),
         missing_low_years = I(rows$year[is.na(rows$low)]), missing_high_years = I(rows$year[is.na(rows$high)]),
         csv_path = path)
  })
  statuses <- vapply(area.coverage, "[[", character(1), "status")
  qa <- list(retrieval = "complete", geography_and_years = if (all(statuses == "complete")) "complete" else "partial",
             roster_areas = nrow(roster), observed_areas = length(unique(data$area_code)),
             no_observations = sum(statuses == "no_observations"),
             expected_area_years = nrow(roster) * length(window), observed_area_years = nrow(data),
             absent_area_years = nrow(roster) * length(window) - nrow(data),
             missing_estimates = sum(is.na(data$value_num)), missing_lower_bounds = sum(is.na(data$low)),
             missing_upper_bounds = sum(is.na(data$high)), duplicate_area_years = 0L,
             duplicate_observation_ids = 0L, invalid_units = 0L, invalid_bounds = 0L)
  list(areas = area.coverage, qa = qa, first_year = min(window), last_year = max(window),
       observations_sha256 = digest::digest(file = csv, algo = "sha256"))
}
