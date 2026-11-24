# Phase 5 GHE deaths pilot

The [Phase 5 catalog](https://raw.githubusercontent.com/shanlong-who/dsir-health-data-skills/refs/heads/pilot/wpr-ghe-phase5/snapshots/phase5/catalog.json) reuses the three pinned Phase 4 entries and adds WHO Global Health Estimates all-cause deaths. Its GHE manifest records the active scope and valid observation years for each area and sex. The Phase 4 catalog remains available on its original branch.

The first release selects the Philippines in 2023, all ages and all causes, with FEMALE, MALE and TOTAL records. The regional release uses the same filters across all available years and the 38-area roster. Each country's TOTAL row is the published both-sex estimate. Estimates and bounds retain source precision and use deaths as their unit.

The workflow checks DSIR acquisition status and the complete dimensional key, then independently compares all rows and bounds against disjoint WHO xMart queries. It publishes data, its manifest and the catalog together after verification. The regional stage is enabled by changing the scope file only after the ordinary Chat pilot has passed. The pilot data and manifest retain pinned addresses.

To check the current release, run `Rscript --vanilla scripts/verify_ghe.R --public` from the matching checkout. The checker downloads the catalog and each GHE file, recalculates SHA-256 with OpenSSL and matches each area CSV to the full table.

## Ordinary Chat acceptance

1. For the Philippines, what are the latest female and both-sex all-cause death estimates in this snapshot? Give year, bounds, age group, units and the country CSV. Is an age-standardized death rate for the same year available?
2. For a different Western Pacific country, report the most recent male and both-sex observations. Give each year, estimate, bounds, original source and country CSV. Explain which snapshot covers the request.
