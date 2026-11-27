# Phase 8 global health series pilot

The Phase 8 pilot keeps the six Phase 7 series and adds the GHO xMart UHC service coverage index, four UN SDG 3.2.1 series, and GHE counts and rates for all causes and stroke. The GHE release includes all ages and age 40–44, with female, male and both-sex estimates. Published all-age rates are crude and rates at age 40–44 are age-specific. The input rate fields have no uncertainty bounds.

The release is driven by `config/phase8-series.csv`. Its catalog links to country files through data manifests, and provides a small index of published series with observed geography and years. Additional discovery files identify source entries with availability pending. GHE cause and measure indexes express dictionary membership and identify selected strata. Coverage for a particular combination is in the GHE manifest. Country files for the six Phase 7 series keep their original digests and provenance.

UN SDG country and area coverage includes Kosovo under its source code 412. The catalog assigns the stable file key `SDG-412`. The added geography row has no M49 or ISO3 code. Source-defined geographic aggregates are listed in provenance.

## Build and verify

Run the R scripts from the repository root. The configured cache is the sibling directory `../20261127-phase8-cache`. The build also reads the accepted Phase 7 catalog audit and Phase 8 preflight directories. Checkpoint files are written only after completeness tests pass.

1. Run `scripts/fetch_phase8.R` with `uhc`, `uhc_coverage`, `sdg_geography`, `sdg_directory` and `sdg_probe`.
2. Run `scripts/fetch_phase8.R ghe <age> <cause>` for `TOTAL` and `Y40T44`, with cause `0` and `1140`. Each run handles three sex strata.
3. For UN SDG, run `scripts/fetch_phase8.R sdg_batch <worker> 5` for worker numbers 1 through 5. They can run concurrently. Rerun incomplete workers to resume from verified batches.
4. Run `scripts/build_phase8.R` followed by `scripts/verify_phase8.R`. These scripts use the same phase-specific directories and can be run with `Rscript --vanilla` in R 4.6.2.
5. Run `scripts/verify_phase8.R` again with the immutable public catalog URL. The public check reopens the catalogs, all manifests, provenance files and country files used for ordinary Chat acceptance. The local check reads every country CSV.

[WHO UHC index](https://www.who.int/data/gho/data/indicators/indicator-details/GHO/uhc-index-of-service-coverage) · [UN SDG 3.2.1 metadata](https://unstats.un.org/sdgs/metadata/files/Metadata-03-02-01.pdf) · [WHO Global Health Estimates](https://www.who.int/data/global-health-estimates)
