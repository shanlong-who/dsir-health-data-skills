suppressPackageStartupMessages({
  library(dplyr)
  library(jsonlite)
  library(readr)
})
phase7 <- "snapshots/phase7"
cache <- "../20261127-phase8-cache"
read_text <- function(path) read_csv(path,col_types=cols(.default=col_character()),show_col_types=FALSE)
rules <- read_text("config/phase8-series.csv")
roster <- read_text(file.path(phase7,"geography.csv"))
roster$area_code <- roster$iso3
roster$source_geo_code <- roster$m49
roster$roster_source <- "UN M49"
roster <- bind_rows(roster,data.frame(area_code="SDG-412",name="Kosovo",source_geo_code="412",
                                     roster_source="UN SDG 3.2.1 GeoAreas"))
capture <- function(id) readRDS(file.path(cache,paste0(id,".rds")))
load_batches <- function(ids) {
  parts <- lapply(ids,capture)
  list(rows=bind_rows(lapply(parts,`[[`,"rows")),sources=bind_rows(lapply(parts,`[[`,"sources")))
}
same_rows <- function(a,b,keys,fields) {
  z <- merge(a,b,by=keys,suffixes=c(".a",".b"))
  stopifnot(nrow(z)==nrow(b))
  for(f in fields) stopifnot(isTRUE(all.equal(z[[paste0(f,".a")]],z[[paste0(f,".b")]],tolerance=1e-12)))
}
get_uhc <- function() {
  id <- if(file.exists(file.path(cache,"uhc.rds"))) "uhc" else "uhc-fast"
  p <- capture(id)
  x <- p$rows
  coverage <- readRDS(file.path(cache,"uhc-coverage.rds"))
  observed <- summarise(x,n_obs=n(),year_min=min(year),year_max=max(year),.by=location)
  stopifnot(setequal(observed$location,coverage$location))
  same_rows(observed,coverage,"location",c("n_obs","year_min","year_max"))
  stopifnot(all(vapply(x[grep("^dim_",names(x))],function(col) all(is.na(col)|col==""),logical(1))))
  area <- coalesce(match(x$location,roster$iso3),match(x$location,roster$m49))
  aggregate <- is.na(area)
  stopifnot(all(x$id=="UHC_INDEX_REPORTED"),all(x$time_type=="YEAR"),
            all(x$spatial_type[aggregate] %in% c("REGION","GLOBAL","WORLDBANKINCOMEGROUP")),
            !any(x$spatial_type[!aggregate] %in% c("REGION","GLOBAL","WORLDBANKINCOMEGROUP")),
            !anyDuplicated(x$observation_id))
  z <- x[!aggregate,]
  z$area_code <- roster$area_code[area[!aggregate]]
  u <- read_text("../20261127-phase8-preflight/xmart.csv")
  same_rows(z,mutate(u,year=as.integer(year),across(c(value_num,low,high),as.numeric)),
            c("location","year"),c("value_num","low","high"))
  list(rows=transmute(z,area_code,year,series_code=id,source_unit=measure_field,estimate=value_num,low,high),
       sources=p$sources, excluded=distinct(x[aggregate,],location,location_name,spatial_type))
}
get_child <- function() {
  geography <- readRDS(file.path(cache,"sdg-geo.rds"))
  codes <- sort(unique(as.character(geography$data$geoAreaCode)))
  batches <- sprintf("sdg-batch-%02d",seq_len(ceiling(length(codes)/8L)))
  p <- load_batches(batches)
  x <- p$rows
  stopifnot(setequal(x$location,codes), nrow(x)==sum(p$sources$record_count))
  ref <- capture("sdg-probe")$rows
  same_rows(x,ref,c("location","year","series","dim_age","dim_sex","dim_reporting_type"),
            c("value_num","low","high","attr_units"))
  z <- mutate(x,area_code=roster$area_code[match(as.integer(location),as.integer(roster$source_geo_code))])
  aggregates <- c(1,9,15,21,30,34,35,53,62,143,145,150,199,202,419,432,513,543,722,747,753)
  stopifnot(setequal(as.integer(z$location[is.na(z$area_code)]),aggregates),all(z$id=="3.2.1"))
  z <- filter(z,!is.na(area_code))
  stopifnot(all(z$dim_reporting_type=="G"),all(z$dim_sex %in% c("FEMALE","MALE","BOTHSEX")),
            !anyNA(z$dim_age))
  named <- grep("^dim_[a-z]",names(z),value=TRUE)
  stopifnot(all(vapply(z[setdiff(named,c("dim_age","dim_sex","dim_reporting_type"))],
                       function(col) all(is.na(col)|col==""),logical(1))))
  rule <- rules[rules$dataset=="child",]
  stopifnot(all(z$dim_age==rule$source_age[match(z$series,rule$series)]))
  list(rows=transmute(z,area_code,year,series_code=series,source_unit=attr_units,estimate=value_num,low,high,
                      age=dim_age,sex=dim_sex,dim_reporting_type),
       sources=p$sources, excluded=filter(geography$data,geoAreaCode %in% aggregates),
       geography=list(endpoint=geography$url,authorized_areas=length(codes),
                      retrieved_at=format(geography$retrieved,"%FT%TZ",tz="UTC")))
}
get_ghe <- function() {
  batches <- expand.grid(age=c("TOTAL","Y40T44"),cause=c(0,1140),sex=c("TOTAL","FEMALE","MALE"),
                         stringsAsFactors=FALSE)
  ids <- with(batches,paste("ghe",age,cause,sex,sep="-"))
  p <- load_batches(ids)
  x <- p$rows
  stopifnot(nrow(x)==2L*sum(p$sources$record_count),all(x$iso3 %in% roster$iso3),
            setequal(x$sex,batches$sex),setequal(x$age,batches$age),setequal(x$cause_code,as.character(batches$cause)),
            all(is.na(x$low[x$measure=="death_rate"])),all(is.na(x$high[x$measure=="death_rate"])))
  exact <- read_text("../20261127-phase8-preflight/ghe_small.csv")
  same_rows(x,mutate(exact,year=as.integer(year),across(c(value,low,high),as.numeric)),
            c("iso3","year","sex","age","cause_code","measure"),c("value","low","high"))
  list(rows=transmute(x,area_code=iso3,year,series_code=measure,source_unit=unit,estimate=value,low,high,
                      age,sex,cause_code,measure),sources=p$sources)
}
