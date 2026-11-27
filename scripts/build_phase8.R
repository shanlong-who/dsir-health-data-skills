suppressPackageStartupMessages(library(openssl))
source("scripts/phase8_data.R")

out <- "snapshots/phase8"
if (dir.exists(out)) stop("Build into a checkout without an existing Phase 8 snapshot.")
stage <- tempfile(".phase8-",tmpdir=dirname(out))
dir.create(stage)
describe <- function(path) {
  full <- file.path(stage,path)
  connection <- file(full,"rb")
  on.exit(close(connection))
  list(path=path,sha256=paste(as.character(sha256(connection)),collapse=""),bytes=unname(file.size(full)))
}
save_json <- function(data,path) {
  text <- toJSON(data,pretty=TRUE,auto_unbox=TRUE,null="null",na="null",digits=NA)
  writeBin(charToRaw(enc2utf8(paste0(text,"\n"))),file.path(stage,path))
}
copy_pinned <- function(link) {
  path <- link$path
  stopifnot(file.copy(file.path(phase7,path),file.path(stage,path)))
  actual <- describe(path)
  stopifnot(actual$sha256==link$sha256,actual$bytes==link$bytes)
}
write_snapshot <- function(id,input) {
  r <- filter(rules,dataset==id)
  x <- input$rows
  dimensions <- if(is.na(r$key_dimensions[1])) character() else strsplit(r$key_dimensions[1],"|",fixed=TRUE)[[1]]
  key <- c("area_code","year","series_code",dimensions)
  i <- match(x$series_code,r$series)
  stopifnot(!anyNA(x[key]),!anyDuplicated(x[key]),setequal(x$series_code,r$series),
            all(x$area_code %in% roster$area_code),all(x$source_unit==r$source_unit[i]),
            all(x$year==as.integer(x$year)),
            all(is.na(x$estimate)|is.finite(x$estimate)),all(x$estimate>=0,na.rm=TRUE),
            all(x$low<=x$high,na.rm=TRUE),all(x$estimate<=x$high,na.rm=TRUE),all(x$low<=x$estimate,na.rm=TRUE))
  if(id=="uhc") stopifnot(all(x$estimate<=100,na.rm=TRUE))
  x$audit_unit <- r$unit[i]
  columns <- c("area_code","year","series_code","audit_unit","estimate","low","high",dimensions)
  x <- x[do.call(order,x[key]),columns]
  parts <- split(x,x$area_code)
  dir.create(file.path(stage,id,"areas"),recursive=TRUE)
  descriptors <- lapply(names(parts),function(area) {
    path <- paste0(id,"/areas/",area,".csv")
    write_csv(parts[[area]],file.path(stage,path),na="",eol="\n")
    c(describe(path),list(rows=nrow(parts[[area]])))
  })
  names(descriptors) <- names(parts)
  summarize <- function(z) list(first_year=min(z$year),last_year=max(z$year),areas=length(unique(z$area_code)),
      rows=nrow(z),valid_estimates=sum(!is.na(z$estimate)),missing_bounds=sum(is.na(z$low)|is.na(z$high)))
  series <- lapply(seq_len(nrow(r)),function(n) {
    z <- x[x$series_code==r$series[n],]
    dim.values <- setNames(lapply(dimensions,function(f) as.list(sort(unique(z[[f]])))),dimensions)
    c(list(code=r$series[n],name=r$name[n],unit=r$unit[n],denominator=r$denominator[n],
           source_unit=r$source_unit[n],dimensions=dim.values),summarize(z))
  })
  breakdown <- if(length(dimensions)) summarise(x,first_year=min(year),last_year=max(year),
    areas=n_distinct(area_code),rows=n(),valid_estimates=sum(!is.na(estimate)),.by=all_of(c("series_code",dimensions))) else NULL
  retrieved <- sort(unique(input$sources$retrieved_at))
  prov.path <- paste0(id,"/provenance.json")
  save_json(list(dsir_version="0.15.0",sources=input$sources,export_rows=nrow(x),
                 geographic_aggregates=input$excluded,geo_source=input$geography),prov.path)
  manifest.path <- paste0(id,"/manifest.json")
  save_json(list(release="0.8.0",dataset=id,product=r$source[1],indicator=r$indicator[1],backend=r$backend[1],
                 retrieved_from=retrieved[1],retrieved_through=tail(retrieved,1),scope="global_country_area",
                 area_count=length(parts),row_count=nrow(x),geography="geography.csv",series=series,
                 key_dimensions=as.list(dimensions),coverage_by_stratum=breakdown,areas=descriptors,
                 provenance=describe(prov.path)),manifest.path)
  cat(id,length(parts),"areas,",nrow(x),"rows,",min(x$year),"through",max(x$year),"\n")
  list(indicator=r$indicator[1],product=r$source[1],series=series,manifest=describe(manifest.path))
}
baseline <- read_json(file.path(phase7,"catalog.json"))
catalog <- baseline
catalog$release <- "0.8.0"
catalog$snapshot_date <- "2026-11-27"
catalog$baseline <- list(release="0.7.0",data_commit="04f9802eaf8053cddaccda0e4abd84a04be72887",carried_datasets=as.list(names(baseline$datasets)))
write_csv(roster,file.path(stage,"geography.csv"),na="",eol="\n")
catalog$geography <- describe("geography.csv")
for(id in names(baseline$datasets)) {
  entry <- baseline$datasets[[id]]
  m <- read_json(file.path(phase7,entry$manifest$path))
  dir.create(file.path(stage,id,"areas"),recursive=TRUE)
  for(link in c(m$areas,list(m$provenance))) copy_pinned(link)
  m$release <- "0.8.0"
  m$origin_release <- "0.7.0"
  save_json(m,entry$manifest$path)
  catalog$datasets[[id]]$manifest <- describe(entry$manifest$path)
}
readers <- list(uhc=get_uhc,child=get_child,ghe_extended=get_ghe)
for(id in names(readers)) catalog$datasets[[id]] <- write_snapshot(id,readers[[id]]())
source("scripts/phase8_index.R")
catalog$index <- write_index(catalog)
save_json(catalog,"catalog.json")
stopifnot(file.rename(stage,out))
