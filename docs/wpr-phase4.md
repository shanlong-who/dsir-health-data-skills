# DSIR Snapshot Pilot Phase 4

The [catalog](https://raw.githubusercontent.com/shanlong-who/dsir-health-data-skills/refs/heads/pilot/wpr-sdg-phase4/snapshots/catalog.json) indexes tuberculosis incidence and DTP3 coverage from WHO GHO, and skilled birth attendance from the UN Global SDG Indicators Database. Each entry points to its own immutable manifest, area CSVs, full CSV and provenance. The two GHO entries reuse their accepted snapshots.

The added SDG series is SH_STA_BRTC under indicator 3.1.2. The unit is the percentage of live births attended by skilled health personnel. The pipeline retrieves the full history for the current WHO Western Pacific roster in disjoint batches of UN M49 geography codes through DSIR. It verifies the global reporting type, unit, numeric range, area-year uniqueness, observation gaps and file hashes. Survey and administrative observation years can be irregular. The local record key identifies the series, geographic code, year and reporting type. Source attributes, time coverage and footnotes are retained.

## Ordinary Chat acceptance

Select DSIR Snapshot Pilot Phase 4 and ask this question in a fresh ordinary Chat without supplying files or expected values.

> For Viet Nam, what are the most recent DTP3 coverage and skilled birth attendance estimates in these snapshots? What is the latest year in which both have an estimate and what are both values in that year? What does the source say about skilled birth attendance in 2020? Give each denominator, each data source and both area CSV links.

To independently verify the catalog, use `Rscript --vanilla scripts/verify_catalog.R --phase4 --public` with curl, jsonlite and openssl installed. This verifies the pinned files and compares only the two requested indicators.

[UN SDG 3.1.2 metadata](https://unstats.un.org/sdgs/metadata/files/Metadata-03-01-02.pdf) · [WHO Western Pacific roster](https://www.who.int/westernpacific/about/where-we-work)
