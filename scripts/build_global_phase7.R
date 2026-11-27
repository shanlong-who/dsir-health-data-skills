suppressPackageStartupMessages({
  library(dplyr)
  library(jsonlite)
  library(openssl)
  library(readr)
})
args <- commandArgs(TRUE)
if (length(args) != 1L) stop("Usage: Rscript scripts/build_global_phase7.R audit-directory")
audit <- args[1]
destination <- "snapshots/phase7"
if (dir.exists(destination)) stop("Build into a checkout without an existing Phase 7 snapshot.")
out <- tempfile(".phase7-",tmpdir=dirname(destination))

read_text <- function(path) read_csv(file.path(audit, path), col_types=cols(.default=col_character()), show_col_types=FALSE)
describe_file <- function(path) {
  file.path.full <- file.path(out, path)
  connection <- file(file.path.full, "rb")
  on.exit(close(connection))
  list(path=path, sha256=paste(as.character(sha256(connection)),collapse=""), bytes=unname(file.size(file.path.full)))
}
save_json <- function(x, path) {
  payload <- toJSON(x, pretty=TRUE, auto_unbox=TRUE, na="null", null="null", digits=NA)
  writeBin(charToRaw(enc2utf8(paste0(payload,"\n"))), file.path(out,path))
}
dir.create(out, recursive=TRUE)
roster <- read_text("audit/m49-geography.csv")
stopifnot(!anyNA(roster$iso3), !anyDuplicated(roster$iso3), !anyDuplicated(roster$m49))
write_csv(roster, file.path(out, "geography.csv"), na="", eol="\n")

spec <- read_text("config/series.csv")
summary <- read_text("audit/coverage-summary.csv")
by.area <- read_text("audit/country-years.csv")
source.payload <- read_json(file.path(audit,"audit/provenance.json"))
phase6 <- read_text("audit/baseline-check.csv")
stopifnot(all(phase6$matched_keys==phase6$baseline_rows),
          all(phase6$estimate_differences=="0"), all(phase6$low_differences=="0"),
          all(phase6$high_differences=="0"))
sources <- c(tb="WHO Global Health Observatory", dtp3="WHO Global Health Observatory (WHO/UNICEF WUENIC)",
             sba="United Nations Global SDG Indicators Database", ghe="WHO Global Health Estimates",
             road="United Nations Global SDG Indicators Database")
denominators <- setNames(c("Population", "One-year-old children", "Live births", NA,
                          "Population", NA),c("MDG_0000000020","WHS4_100","SH_STA_BRTC","deaths","SH_STA_TRAF","SH_STA_TRAFN"))
entries <- list()
for (id in unique(spec$dataset)) {
  rules <- filter(spec, dataset==id)
  totals <- filter(summary, dataset==id, scope=="Indicator")
  source.csv <- file.path(audit, totals$file)
  connection <- file(source.csv,"rb")
  source.sha <- paste(as.character(sha256(connection)),collapse="")
  close(connection)
  stopifnot(source.sha==totals$sha256)
  rows <- read_text(totals$file)
  dims <- switch(id, ghe=c("age","sex","cause_code","measure"), sba="dim_reporting_type",
                 road="dim_reporting_type", character())
  columns <- c("area_code","year","series_code","audit_unit","estimate","low","high",dims)
  keys <- c("area_code","year","series_code",dims)
  stopifnot(!anyDuplicated(rows[keys]), nrow(rows)==as.integer(totals$rows),
            n_distinct(rows$area_code)==as.integer(totals$areas), all(rows$area_code %in% roster$iso3))
  parts <- split(rows[columns],rows$area_code)
  dir.create(file.path(out, id, "areas"), recursive=TRUE)
  areas <- lapply(names(parts),function(area) {
    x <- parts[[area]]
    path <- paste0(id,"/areas/",area,".csv")
    write_csv(x, file.path(out,path), na="", eol="\n")
    replay <- read_csv(file.path(out,path), col_types=cols(.default=col_character()), show_col_types=FALSE)
    stopifnot(identical(as.data.frame(x),as.data.frame(replay)))
    c(describe_file(path), list(rows=nrow(x)))
  })
  names(areas) <- names(parts)
  series <- lapply(seq_len(nrow(rules)),function(i) {
    r <- rules[i,]
    code <- coalesce(r$series,r$indicator)
    s <- filter(rows,series_code==code)
    h <- filter(by.area,dataset==id,series==code)
    stopifnot(nrow(h)==nrow(roster), sum(as.integer(h$rows))==nrow(s))
    list(code=code, name=r$name, unit=r$unit, denominator=unname(denominators[[code]]),
         first_year=min(as.integer(s$year)), last_year=max(as.integer(s$year)),
         areas=n_distinct(s$area_code), rows=nrow(s))
  })
  provenance.path <- paste0(id,"/provenance.json")
  provenance <- source.payload[[id]]
  stopifnot(length(provenance$sources)>0, all(vapply(provenance$sources,function(s) s$complete,logical(1))))
  save_json(c(list(audit_csv_sha256=source.sha, DSIR_version="0.15.0"), provenance),provenance.path)
  fetched <- sort(unique(vapply(provenance$sources,function(s) s$retrieved_at,character(1))))
  manifest.path <- paste0(id,"/manifest.json")
  manifest <- list(release="0.7.0",dataset=id,product=unname(sources[[id]]),indicator=rules$indicator[1],
                   backend=provenance$sources[[1]]$backend,
                   retrieved_from=fetched[1],retrieved_through=tail(fetched,1),
                   scope="global_country_area",area_count=length(areas),row_count=nrow(rows),
                   geography="geography.csv",series=series,
                   dimensions=switch(id,ghe=list(age="TOTAL",sex=as.list(c("FEMALE","MALE","TOTAL")),cause_code="0",measure="deaths"),
                     sba=list(reporting_type="G"),road=list(reporting_type="G"),list()),
                   areas=areas, provenance=describe_file(provenance.path))
  save_json(manifest,manifest.path)
  entries[[id]] <- list(indicator=rules$indicator[1], product=unname(sources[[id]]),
                        series=series, manifest=describe_file(manifest.path))
}
catalog <- list(schema_version="1.0", release="0.7.0", scope="global_country_area",
                snapshot_date="2026-11-24",
                relative_to="Directory containing catalog.json at the same Git commit",
                geography=describe_file("geography.csv"), datasets=entries)
save_json(catalog,"catalog.json")
stopifnot(length(entries)==5L, sum(lengths(lapply(entries,`[[`,"series")))==6L)
total.csv <- list.files(out,pattern="\\.csv$",recursive=TRUE)
stopifnot(file.rename(out,destination))
cat("Built", length(total.csv)-1L, "country CSVs from", length(entries), "datasets\n")
