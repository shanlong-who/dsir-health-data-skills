# DSIR Snapshot Pilot Phase 2

This pilot publishes a dated WHO GHO tuberculosis incidence series for the current WHO Western Pacific countries and areas. The [official roster](https://www.who.int/westernpacific/about/where-we-work) applies to the full historical series, including years before Indonesia changed regions. The snapshot contains country and area observations. Rates for WHO regional aggregates are a different geographic series.

Start with the [current manifest](https://raw.githubusercontent.com/shanlong-who/dsir-health-data-skills/refs/heads/pilot/wpr-tb-phase2/snapshots/wpr-tb/manifest.json). Follow its commit-pinned links for the complete CSV, provenance and country or area CSVs. Every offered file has a byte count and SHA-256. The manifest has a detached checksum next to it. The manifest distinguishes successful retrieval from completeness across the roster and years. A missing row, a missing estimate or bound, and a reported zero each have a different meaning.

The workflow reads the unrestricted WHO xMart coverage index and observation count through DSIR. It pages through the full indicator with no geographic-type filter so that special administrative regions are included. It selects roster locations locally and checks per-area counts and years against the index. Duplicate keys or IDs, invalid units or bounds and incomplete retrieval block publication. Source gaps are described in the manifest. A second reader checks the exported tables and their hashes before a single push publishes the files and catalog. The Phase 2 branch uses the public GitHub Actions standard Ubuntu runner.

## Next ordinary Chat acceptance questions

Select **DSIR Snapshot Pilot Phase 2** in a fresh ordinary Chat. Supply only the question. Give the tester the expected answers separately to keep the exercise blind.

1. What is the latest tuberculosis incidence estimate for Viet Nam, including the reported bounds, unit and observation year? Give the retrieval date, run ID and links to the area CSV, manifest and provenance.
2. Compare Hong Kong SAR and Macao SAR in 2012. Give each estimate, both bounds and its original observation ID, citing each area file.
3. Can this snapshot answer the 2024 tuberculosis incidence question for Guam and Thailand? Explain the evidence for each separately. Could you provide the WHO regional rate from the same snapshot?
4. What does the snapshot show for the Philippines in 2012? Does it also have a Philippine observation for 2025? State the evidence for each.
5. Does the snapshot contain Indonesia in 2010? Explain the geographic basis for historical inclusion. Report the number of roster entries, areas with observations and absent area-years.
6. Download the full observations CSV and report the last eight characters of its SHA-256. Say explicitly whether you computed it on the downloaded file or read the recorded digest. Compare it with the manifest and provide both file links.
