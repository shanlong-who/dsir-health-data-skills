# The Phase 2 entry points default to tuberculosis.
snapshot.id <- match.arg(Sys.getenv("DSIR_SNAPSHOT_ID", "wpr-tb"), c("wpr-tb", "wpr-dtp3"))
dtp3 <- identical(snapshot.id, "wpr-dtp3")
spec <- if (dtp3) {
  list(code = "WHS4_100", name = "DTP3 immunization coverage among one-year-olds",
       unit = "Diphtheria-tetanus-pertussis (DTP3) immunization coverage among 1-year-olds (%)",
       measure = "RATE_PER_100_N", maximum = 100, bounds_expected = FALSE,
       estimate_type = "WHO/UNICEF estimates of national immunization coverage (WUENIC)",
       metadata_url = "https://data.who.int/indicators/i/F8E084C")
} else {
  list(code = "MDG_0000000020", name = "Tuberculosis incidence",
       unit = "Tuberculosis incidence (per 100 000 population)", measure = "RATE_PER_100000_N",
       maximum = Inf, bounds_expected = TRUE)
}
out <- Sys.getenv("DSIR_SNAPSHOT_DIR", file.path("snapshots", snapshot.id))
required.fields <- if (spec$bounds_expected) c("value_num", "low", "high") else "value_num"
