suppressPackageStartupMessages({
  library(DSIR)
  library(curl)
  library(jsonlite)
})
args <- commandArgs(TRUE)
task <- args[1]
cache <- "../20261127-phase8-cache"
dir.create(cache,showWarnings=FALSE)
sdg.base <- "https://unstats.un.org/sdgs/UNSDGAPIV5/v1/sdg"
checkpoint <- function(id, retrieve, multiplier=1L) {
  path <- file.path(cache,paste0(id,".rds"))
  if(file.exists(path)) return(invisible(NULL))
  start <- Sys.time()
  x <- retrieve()
  metadata <- dsir_metadata(x)
  source <- metadata$sources
  stopifnot(nrow(x)>0L,nrow(source)==1L,source$complete,source$status=="success",
            source$retrieval_status=="live",nrow(x)==source$record_count*multiplier)
  if(source$backend=="unsdg") {
    pages <- source$query[[1]]
    stopifnot(pages$pages_received==pages$expected_pages,pages$expected_rows==nrow(x))
  }
  partial <- tempfile("batch-",tmpdir=cache)
  saveRDS(list(rows=as.data.frame(x),sources=source,started=start,finished=Sys.time()),partial)
  stopifnot(file.rename(partial,path))
  cat(id,nrow(x),"rows\n")
}
if(task=="uhc") {
  options(DSIR.who_page_size=300L)
  checkpoint("uhc",function() gho_data("UHC_INDEX_REPORTED",backend="xmart",keep_dimensions=TRUE,keep_metadata=TRUE))
} else if(task=="uhc_coverage") {
  data <- gho_coverage("UHC_INDEX_REPORTED",spatial_type=NULL,backend="xmart")
  stopifnot(nrow(data)>0L,all(c("location","n_obs","year_min","year_max") %in% names(data)))
  saveRDS(data,file.path(cache,"uhc-coverage.rds"))
} else if(task=="ghe") {
  age <- args[2]
  cause <- as.integer(args[3])
  stopifnot(age %in% c("TOTAL","Y40T44"),cause %in% c(0,1140))
  for(sex in c("TOTAL","FEMALE","MALE")) {
    id <- paste("ghe",age,cause,sex,sep="-")
    checkpoint(id,function() ghe_data(age=age,cause=cause,sex=sex,measure=c("deaths","death_rate")),2L)
  }
} else if(task=="sdg_geography") {
  url <- paste0(sdg.base,"/Indicator/3.2.1/GeoAreas")
  fetched <- curl_fetch_memory(url,handle=new_handle(failonerror=TRUE,timeout=100))
  data <- fromJSON(rawToChar(fetched$content),simplifyDataFrame=TRUE)
  stopifnot(nrow(data)>0L)
  saveRDS(list(data=data,url=url,retrieved=Sys.time()),file.path(cache,"sdg-geo.rds"))
} else if(task=="sdg_directory") {
  data <- sdg_indicators()
  source <- dsir_metadata(data)$sources
  stopifnot(nrow(data)>0L,nrow(source)==1L,source$complete,source$status=="success")
  saveRDS(list(data=data,url=source$endpoint,retrieved=Sys.time()),file.path(cache,"sdg-directory.rds"))
} else if (task=="sdg_probe") {
  checkpoint("sdg-probe",function() sdg_data("3.2.1",area="704",page_size=500L,keep_dimensions=TRUE,keep_metadata=TRUE))
} else if (task=="sdg_batch") {
  geo <- readRDS(file.path(cache,"sdg-geo.rds"))$data
  codes <- sort(unique(as.character(geo$geoAreaCode)))
  groups <- split(codes,ceiling(seq_along(codes)/8L))
  index <- as.integer(args[2])
  workers <- as.integer(args[3])
  stopifnot(index>=1L,index<=workers)
  for (i in seq_along(groups)[(seq_along(groups)-1L)%%workers==index-1L]) {
    tryCatch(checkpoint(sprintf("sdg-batch-%02d",i),function() {
      x <- sdg_data("3.2.1",area=groups[[i]],page_size=500L,keep_dimensions=TRUE,keep_metadata=TRUE)
      stopifnot(setequal(x$location,groups[[i]]))
      x
    }),error=function(e) message("Batch ",i," needs retry: ",conditionMessage(e)))
  }
} else stop("Unknown task")
