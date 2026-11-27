suppressPackageStartupMessages({
  library(curl)
  library(digest)
  library(dplyr)
  library(jsonlite)
  library(readr)
})
args <- commandArgs(TRUE)
root <- "snapshots/phase8"
base <- if(length(args)) sub("catalog.json$","",args[1]) else NULL
if(!is.null(base)) stopifnot(grepl("^https://raw.githubusercontent.com/shanlong-who/dsir-health-data-skills/[a-f0-9]{40}/snapshots/phase8/$",base))
read_local <- function(path) readBin(path,"raw",n=file.size(path))
read_file <- function(path) {
  if(is.null(base)) return(read_local(file.path(root,path)))
  for(attempt in 1:3) {
    r <- try(curl_fetch_memory(paste0(base,path),handle=new_handle(failonerror=TRUE,timeout=30)),silent=TRUE)
    if(!inherits(r,"try-error")&&r$status_code==200) return(r$content)
  }
  stop("Cannot read public file ",path)
}
checked <- function(link) {
  b <- read_file(link$path)
  stopifnot(length(b)==link$bytes,digest(b,algo="sha256",serialize=FALSE)==link$sha256)
  rawToChar(b)
}
parse_rows <- function(s) read_csv(I(s),col_types=cols(.default=col_character()),show_col_types=FALSE)
catalog.bytes <- read_file("catalog.json")
stopifnot(identical(catalog.bytes,read_local(file.path(root,"catalog.json"))))
catalog <- parse_json(rawToChar(catalog.bytes))
baseline <- read_json("snapshots/phase7/catalog.json")
stopifnot(catalog$release=="0.8.0",catalog$baseline$release==baseline$release,length(catalog$datasets)==8L)
geography <- parse_rows(checked(catalog$geography))
stopifnot(nrow(geography)==249L,!anyDuplicated(geography$area_code),
          sum(geography$source_geo_code=="412",na.rm=TRUE)==1L)
indices <- setdiff(names(catalog$index),"discovery")
for(id in indices) invisible(checked(catalog$index[[id]]))
published <- parse_rows(checked(catalog$index$published))
stopifnot(nrow(published)==13L,all(published$status=="snapshot_available"),all(as.integer(published$rows)>0L))
sample.areas <- list(tb=c("BRA","VNM"),dtp3="VNM",sba="VNM",ghe="VNM",road="NIU",
                     uhc=c("BRA","PHL","VNM"),child=c("BRA","PHL","VNM","SDG-412"),ghe_extended=c("BRA","VNM"))
sample <- list()
all.rows <- 0L
verified.files <- 0L
for(id in names(catalog$datasets)) {
  v <- catalog$datasets[[id]]
  m <- parse_json(checked(v$manifest))
  provenance <- parse_json(checked(m$provenance))
  stopifnot(m$release=="0.8.0",m$dataset==id,identical(m$series,v$series),length(m$areas)==m$area_count,
            sum(vapply(m$areas,`[[`,integer(1),"rows"))==m$row_count,
            all(names(m$areas) %in% geography$area_code))
  if(id %in% names(baseline$datasets)) {
    old <- read_json(file.path("snapshots/phase7",baseline$datasets[[id]]$manifest$path))
    stopifnot(identical(old$areas,m$areas),identical(old$provenance,m$provenance),
              identical(old$series,m$series),m$origin_release=="0.7.0")
  } else {
    stopifnot(provenance$export_rows==m$row_count,
              all(vapply(provenance$sources,function(s) isTRUE(s$complete),logical(1))))
  }
  areas <- if(is.null(base)) names(m$areas) else sample.areas[[id]]
  for(area in areas) {
    r <- parse_rows(checked(m$areas[[area]]))
    key <- if(is.null(m$key_dimensions)) intersect(c("age","sex","cause_code","dim_reporting_type"),names(r)) else unlist(m$key_dimensions)
    stopifnot(nrow(r)==m$areas[[area]]$rows,all(r$area_code==area),!anyDuplicated(r[c("area_code","year","series_code",key)]),
              all(as.numeric(r$low)<=as.numeric(r$estimate),na.rm=TRUE),all(as.numeric(r$estimate)<=as.numeric(r$high),na.rm=TRUE))
    if(id=="child") stopifnot(all(r$sex %in% c("FEMALE","MALE","BOTHSEX")),all(r$age %in% c("<1Y","<5Y")),all(r$dim_reporting_type=="G"))
    if(id=="ghe_extended") stopifnot(all(r$age %in% c("TOTAL","Y40T44")),all(r$cause_code %in% c("0","1140")),
        all(is.na(r$low[r$series_code=="death_rate"])),all(is.na(r$high[r$series_code=="death_rate"])))
    if(area %in% sample.areas[[id]]) sample[[paste(id,area)]] <- r
    verified.files <- verified.files+1L
    all.rows <- all.rows+nrow(r)
  }
}
vn <- sample[["child VNM"]] %>% filter(year=="2024",sex=="FEMALE")
stopifnot(nrow(vn)==4L,all(as.numeric(vn$estimate)>0))
niue <- sample[["road NIU"]]
stopifnot(all(as.numeric(niue$estimate)==0),all(is.na(niue$low[niue$series_code=="SH_STA_TRAFN"])),
          all(as.numeric(niue$low[niue$series_code=="SH_STA_TRAF"])==0))
stopifnot(!any(sample[["sba VNM"]]$year=="2020"))
r <- sample[["ghe_extended VNM"]] %>% filter(age=="TOTAL",cause_code=="0",series_code=="deaths")
old <- sample[["ghe VNM"]]
k <- c("year","sex","estimate","low","high")
stopifnot(nrow(inner_join(r[k],old[k],by=k))==nrow(old))
cat("PASS:",length(catalog$datasets),"manifests,",verified.files,"country files,",all.rows,"rows and Phase 7 regression.\n")
