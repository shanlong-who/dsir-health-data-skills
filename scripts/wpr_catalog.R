suppressPackageStartupMessages({
  library(digest)
  library(jsonlite)
})
base <- "https://raw.githubusercontent.com/shanlong-who/dsir-health-data-skills/"
tb.revision <- "c9b2af42e92fd1383120ef5e0e1364b8e509e664"
dtp.revision <- Sys.getenv("SNAPSHOT_MANIFEST_COMMIT")
stopifnot(grepl("^[0-9a-f]{40}$", dtp.revision))
catalog_entry <- function(id, revision, aliases) {
  path <- file.path("snapshots", id, "manifest.json")
  m <- read_json(path)
  hash <- digest(file = path, algo = "sha256")
  if (id == "wpr-tb") stopifnot(hash == "9900a033456a4a2fc98626f7001def5e49237b06b96e46d303b50ad1a6098519")
  stopifnot(m$snapshot == id)
  list(id = id, indicator = m$indicator, aliases = aliases, years = m$years,
       retrieved_at = m$retrieved_at, run_id = m$run_id,
       manifest = list(url = paste0(base, revision, "/", path), sha256 = hash))
}
entries <- list(catalog_entry("wpr-tb", tb.revision, c("TB incidence", "tuberculosis incidence")),
                catalog_entry("wpr-dtp3", dtp.revision, c("DTP3", "DPT3", "third-dose DTP coverage")))
catalog <- list(schema_version = "1.0", region = "WHO Western Pacific Region", indicators = entries)
path <- "snapshots/catalog.json"
write_json(catalog, path, auto_unbox = TRUE, pretty = TRUE, null = "null")
writeLines(paste0(digest(file = path, algo = "sha256"), "  catalog.json"), "snapshots/catalog.sha256")
