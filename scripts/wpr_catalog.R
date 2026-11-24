suppressPackageStartupMessages({
  library(digest)
  library(jsonlite)
})
base <- "https://raw.githubusercontent.com/shanlong-who/dsir-health-data-skills/"
tb.revision <- "c9b2af42e92fd1383120ef5e0e1364b8e509e664"
phase4 <- identical(Sys.getenv("DSIR_SNAPSHOT_ID"), "wpr-sba")
new.revision <- Sys.getenv("SNAPSHOT_MANIFEST_COMMIT")
dtp.revision <- if (phase4) "b0d0ceff0236906345686be867b7965ebb8cf402" else new.revision
stopifnot(grepl("^[0-9a-f]{40}$", new.revision))
catalog_entry <- function(id, revision, aliases) {
  path <- file.path("snapshots", id, "manifest.json")
  m <- read_json(path)
  hash <- digest(file = path, algo = "sha256")
  if (id == "wpr-tb") stopifnot(hash == "9900a033456a4a2fc98626f7001def5e49237b06b96e46d303b50ad1a6098519")
  if (phase4 && id == "wpr-dtp3") stopifnot(hash == "13ee52e5ce9b9694ab61889e55a6fc2b0193cfc10dbb4438802032e2d0ebda58")
  stopifnot(m$snapshot == id)
  list(id = id, indicator = m$indicator, aliases = aliases, years = m$years,
       retrieved_at = m$retrieved_at, run_id = m$run_id,
       manifest = list(url = paste0(base, revision, "/", path), sha256 = hash))
}
entries <- list(catalog_entry("wpr-tb", tb.revision, c("TB incidence", "tuberculosis incidence")),
                catalog_entry("wpr-dtp3", dtp.revision, c("DTP3", "DPT3", "third-dose DTP coverage")))
if (phase4) {
  entries[[3L]] <- catalog_entry("wpr-sba", new.revision, c("skilled birth attendance", "skilled attendance at birth", "SH_STA_BRTC"))
  entries <- lapply(entries, function(entry) {
    p <- read_json(file.path("snapshots", entry$id, "provenance.json"))
    entry$product <- p$product
    entry$backend <- p$actual_backend
    entry
  })
}
catalog <- list(schema_version = "1.0", region = "WHO Western Pacific Region", indicators = entries)
path <- "snapshots/catalog.json"
write_json(catalog, path, auto_unbox = TRUE, pretty = TRUE, null = "null")
writeLines(paste0(digest(file = path, algo = "sha256"), "  catalog.json"), "snapshots/catalog.sha256")
