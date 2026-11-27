suppressPackageStartupMessages({
  library(curl)
  library(jsonlite)
  library(openssl)
  library(readr)
})
args <- commandArgs(TRUE)
root <- "snapshots/phase7"
base.url <- if(length(args)) sub("catalog.json$", "", args[1]) else NULL
if (!is.null(base.url)) {
  stopifnot(grepl("^https://raw.githubusercontent.com/shanlong-who/dsir-health-data-skills/[0-9a-f]{40}/snapshots/phase7/$",base.url))
}
read_bytes <- function(path) {
  if (is.null(base.url)) return(readBin(file.path(root,path),"raw",n=file.size(file.path(root,path))))
  response <- curl_fetch_memory(paste0(base.url,path),handle=new_handle(failonerror=TRUE,timeout=30,connecttimeout=10))
  stopifnot(response$status_code==200)
  response$content
}
read_link <- function(link) {
  bytes <- read_bytes(link$path)
  check.sha <- paste(as.character(sha256(bytes)),collapse="")
  stopifnot(length(bytes)==link$bytes,check.sha==link$sha256)
  rawToChar(bytes)
}
read_rows <- function(text) read_csv(I(text),col_types=cols(.default=col_character()),show_col_types=FALSE)
local.catalog <- readBin(file.path(root,"catalog.json"),"raw",n=file.size(file.path(root,"catalog.json")))
catalog.bytes <- read_bytes("catalog.json")
stopifnot(identical(catalog.bytes,local.catalog))
catalog <- parse_json(rawToChar(catalog.bytes))
stopifnot(catalog$release=="0.7.0",catalog$scope=="global_country_area",catalog$snapshot_date=="2026-11-24")
geography <- read_rows(read_link(catalog$geography))
stopifnot(nrow(geography)==248L,!anyDuplicated(geography$iso3))
sample.areas <- list(tb=c("BRA","VNM"),dtp3=c("BRA","VNM"),sba="VNM",ghe=c("BRA","VNM"),road=c("BRA","VNM","NIU"))
tested <- list()
files <- 0L
observations <- 0L
for(id in names(catalog$datasets)) {
  entry <- catalog$datasets[[id]]
  m <- parse_json(read_link(entry$manifest))
  stopifnot(m$release==catalog$release,m$scope==catalog$scope,m$dataset==id,
            m$indicator==entry$indicator,identical(m$series,entry$series),
            length(m$areas)==m$area_count,all(names(m$areas) %in% geography$iso3))
  source <- parse_json(read_link(m$provenance))
  stopifnot(source$export_rows==m$row_count,all(vapply(source$sources,function(s) isTRUE(s$complete),logical(1))))
  selected <- if (is.null(base.url)) names(m$areas) else sample.areas[[id]]
  tested[[id]] <- setNames(vector("list",length(sample.areas[[id]])),sample.areas[[id]])
  for(area in selected) {
    csv <- m$areas[[area]]
    stopifnot(identical(csv$path,paste0(id,"/areas/",area,".csv")))
    r <- read_rows(read_link(csv))
    series <- setNames(m$series,vapply(m$series,`[[`,character(1),"code"))
    stopifnot(nrow(r)==csv$rows,all(r$area_code==area),all(r$series_code %in% names(series)),
              !anyNA(r$estimate),!anyDuplicated(r[setdiff(names(r),c("estimate","low","high","audit_unit"))]),
              all(r$audit_unit==vapply(series[r$series_code],`[[`,character(1),"unit")))
    if (area %in% sample.areas[[id]]) tested[[id]][[area]] <- r
    files <- files+1L
    observations <- observations+nrow(r)
  }
  stopifnot(sum(vapply(m$areas,`[[`,integer(1),"rows"))==m$row_count)
}
tb.common <- Reduce(intersect,lapply(tested$tb,`[[`,"year"))
stopifnot(max(as.integer(tb.common))==2024, all(vapply(tested$tb,function(r) nrow(r[r$year=="2024",])==1L,logical(1))))
stopifnot(!("2020" %in% tested$sba$VNM$year),all(c("2021","2022") %in% tested$sba$VNM$year))
common <- intersect(tested$dtp3$VNM$year,tested$sba$VNM$year)
stopifnot(max(as.integer(common))==2022)
for (z in tested$ghe) stopifnot(setequal(z$sex[z$year=="2023"],c("MALE","FEMALE","TOTAL")),all(z$measure=="deaths"))
niue <- tested$road$NIU
count <- niue[niue$series_code=="SH_STA_TRAFN" & niue$year=="2021",]
rate <- niue[niue$series_code=="SH_STA_TRAF" & niue$year=="2021",]
stopifnot(nrow(count)==1L,nrow(rate)==1L,as.numeric(count$estimate)==0,
          is.na(count$low),is.na(count$high),count$audit_unit=="Deaths",rate$audit_unit=="Deaths per 100000 population")
if(is.null(base.url)) stopifnot(files==962L,observations==25896L)
cat("Verified", length(catalog$datasets), "manifests,", files, "country CSVs and", observations,
    "rows. Passed cross-region, missing-year, common-year, GHE strata and SDG count/rate/zero checks.\n")
