suppressPackageStartupMessages({
  library(DSIR)
  library(jsonlite)
  library(digest)
})

stopifnot(as.character(packageVersion("DSIR")) == "0.15.0")
indicator.code <- "MDG_0000000020"
started.at <- Sys.time()
observations <- gho_data(indicator.code, area = "PHL", spatial_type = "country",
                         backend = "auto", keep_dimensions = TRUE, keep_metadata = TRUE)
query.seconds <- as.numeric(difftime(Sys.time(), started.at, units = "secs"))
metadata <- dsir_metadata(observations)
data <- as.data.frame(observations)
stopifnot(identical(metadata$result$status, "success"), isTRUE(metadata$result$complete),
          nrow(data) > 0L, all(data$id == indicator.code), all(data$iso3 == "PHL"),
          !anyNA(data$year), !anyDuplicated(data$year), length(unique(data$unit)) == 1L,
          !anyNA(data$unit), all(nzchar(data$unit)),
          all(is.na(data$low) | is.na(data$high) | data$low <= data$high),
          all(is.na(data$value_num) | is.na(data$low) | data$value_num >= data$low),
          all(is.na(data$value_num) | is.na(data$high) | data$value_num <= data$high))
data <- data[order(data$year), , drop = FALSE]
for (key in names(data)[vapply(data, is.list, logical(1))]) {
  data[[key]] <- vapply(data[[key]], function(x) as.character(toJSON(as.list(x), na = "null")), character(1))
}
usable <- data[!is.na(data$value_num), , drop = FALSE]
stopifnot(nrow(usable) > 0)
latest <- tail(usable, 1L)
out <- Sys.getenv("DSIR_SNAPSHOT_DIR", "snapshots/phl-tb")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
csv <- file.path(out, "observations.csv")
write.csv(data, csv, row.names = FALSE, na = "", fileEncoding = "UTF-8")
check <- read.csv(csv, colClasses = "character", fileEncoding = "UTF-8")
stopifnot(nrow(check) == nrow(data), identical(as.integer(check$year), data$year),
          isTRUE(all.equal(as.numeric(check$value_num), data$value_num)))
hash <- digest(file = csv, algo = "sha256")
provenance <- list(product = "WHO Global Health Observatory", indicator_code = indicator.code,
                   area = "PHL", requested_backend = "auto", actual_backend = unique(data$provider),
                   unit = latest$unit, retrieval_status = metadata$result$status, complete = metadata$result$complete,
                   sources = metadata$sources, query = metadata$query, package_version = as.character(packageVersion("DSIR")),
                   run_id = Sys.getenv("GITHUB_RUN_ID"), workflow_commit = Sys.getenv("GITHUB_SHA"),
                   query_seconds = round(query.seconds, 2), first_year = min(data$year), last_year = max(data$year),
                   row_count = nrow(data), latest = latest[c("year", "value_num", "low", "high")],
                   observations_sha256 = hash)
write_json(provenance, file.path(out, "provenance.json"), auto_unbox = TRUE,
           pretty = TRUE, na = "null", null = "null", digits = NA)
stopifnot(identical(read_json(file.path(out,"provenance.json"))$observations_sha256,hash))
lines <- c("# Philippines tuberculosis incidence", "",
           sprintf("WHO Global Health Observatory, indicator `%s`. Retrieved %s through DSIR %s (%s).",
                   indicator.code, metadata$sources$retrieved_at[1], provenance$package_version, provenance$actual_backend),
           "", sprintf("Latest estimate: %s per 100,000 population in %s (reported bounds %s to %s).",
                       latest$value_num, latest$year, latest$low, latest$high),
           "", sprintf("Coverage: %s annual observations, %s to %s. Snapshot run: %s.",
                       nrow(data), min(data$year), max(data$year), provenance$run_id), "",
           "[Observation CSV](observations.csv) and [provenance JSON](provenance.json).")
writeLines(lines, file.path(out,"README.md"), useBytes = TRUE)
cat(paste(lines,collapse="\n"), "\nQuery seconds:", provenance$query_seconds, "\n")
