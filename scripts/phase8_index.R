write_index <- function(catalog) {
  audit <- "../20261124-global-phase7/catalogs"
  dir.create(file.path(stage,"index"))
  save_table <- function(x,name) {
    path <- paste0("index/",name,".csv")
    write_csv(x,file.path(stage,path),na="",eol="\n")
    describe(path)
  }
  published <- bind_rows(lapply(names(catalog$datasets),function(id) {
    d <- catalog$datasets[[id]]
    m <- read_json(file.path(stage,d$manifest$path))
    bind_rows(lapply(d$series,function(s) data.frame(dataset=id,product=d$product,backend=m$backend,
          indicator=d$indicator,series=s$code,name=s$name,unit=s$unit,first_year=s$first_year,
          last_year=s$last_year,areas=s$areas,rows=s$rows,status="snapshot_available",manifest=d$manifest$path)))
  }))
  gho <- read_text(file.path(audit,"gho-indicators.csv"))
  pub.gho <- filter(published,dataset %in% c("uhc","tb","dtp3"))
  gh <- transmute(gho,code=IndicatorCode,name=IndicatorName,backend,
                  dataset=pub.gho$dataset[match(paste(backend,IndicatorCode),paste(pub.gho$backend,pub.gho$series))])
  gh$status <- ifelse(is.na(gh$dataset),"discoverable_availability_pending","snapshot_available")
  d <- capture("sdg-directory")
  sdg <- bind_rows(lapply(seq_len(nrow(d$data)),function(i) {
    x <- d$data$series[[i]]
    if(!is.data.frame(x)||!nrow(x)) return(NULL)
    transmute(x,indicator=d$data$code[i],series=code,name=description,source_release=release)
  }))
  stopifnot(!anyDuplicated(sdg[c("indicator","series")]))
  pub.sdg <- filter(published,dataset %in% c("road","sba","child"))
  sdg$dataset <- pub.sdg$dataset[match(paste(sdg$indicator,sdg$series),paste(pub.sdg$indicator,pub.sdg$series))]
  sdg$status <- ifelse(is.na(sdg$dataset),"discoverable_availability_pending","snapshot_available")
  ghe.causes <- read_text(file.path(audit,"ghe-causes.csv"))
  ghe.measures <- read_text(file.path(audit,"ghe-measures.csv"))
  ghe.causes$status <- ifelse(ghe.causes$cause_code %in% c("0","1140"),"selected_strata_snapshotted","discoverable_availability_pending")
  ghe.measures$status <- ifelse(ghe.measures$code %in% c("deaths","death_rate"),"selected_strata_snapshotted","discoverable_availability_pending")
  list(published=save_table(published,"published-series"),gho=save_table(gh,"gho-indicators"),
       sdg=save_table(sdg,"sdg-series"),ghe_causes=save_table(ghe.causes,"ghe-causes"),ghe_measures=save_table(ghe.measures,"ghe-measures"),
       discovery=list(gho_and_ghe_audit_date="2026-11-24",sdg_retrieved_at=format(d$retrieved,"%FT%TZ",tz="UTC"),
                      pending="Discovery entries require availability checks. GHE causes and measures do not imply a full cross-product."))
}
