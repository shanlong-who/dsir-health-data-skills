# DSIR Snapshot Pilot Phase 3

The [indicator catalog](https://raw.githubusercontent.com/shanlong-who/dsir-health-data-skills/refs/heads/pilot/wpr-multi-phase3/snapshots/catalog.json) indexes two Western Pacific snapshots. Open an indicator's pinned manifest to find its full CSV, provenance and individual area CSVs. The catalog links the accepted Phase 2 tuberculosis snapshot and a separately retrieved DTP3 snapshot. Each manifest carries its own run ID, source timestamp, indicator unit and geographic and temporal coverage.

| Indicator | Code | Unit | Bounds |
| --- | --- | --- | --- |
| Tuberculosis incidence | MDG_0000000020 | Cases per 100,000 population | Read the reported lower and upper estimates |
| DTP3 coverage (WHO/UNICEF estimates) | WHS4_100 | Percentage of one-year-olds | WHO metadata specifies no confidence intervals |

The geographic reference is the current WHO Western Pacific roster for both historical series. Check each geography entry individually. The most recent year is the most recent nonmissing estimate in this snapshot for the requested place. For a common year, intersect the two sets of observed years with a nonmissing estimate. A reported zero is eligible.

## Ordinary Chat acceptance

Select **DSIR Snapshot Pilot Phase 3** in a new Chat and ask this question without attaching data, links or expected values.

> For Viet Nam, what is the latest estimate for each indicator in the catalog? What is the latest year with an estimate for both? Give each unit, the available bounds and both area CSV links. If a file is inaccessible, identify it.

One coverage follow-up is to repeat the question for Hong Kong SAR. Confirm which series is available and whether a common year exists.

## Reproduce the file check

From the Phase 3 branch root, run `Rscript --vanilla scripts/verify_catalog.R --public` with the R packages curl, jsonlite and openssl installed. It downloads the public files, checks their digests, verifies each area CSV against its full table and prints the Viet Nam results. The test also exercises a gap between the two latest years, an empty intersection and a reported zero.

[WHO DTP3 indicator metadata](https://data.who.int/indicators/i/F8E084C) · [WHO Western Pacific roster](https://www.who.int/westernpacific/about/where-we-work)
