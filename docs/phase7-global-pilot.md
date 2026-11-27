# Phase 7 global snapshot pilot

Release 0.7.0 packages five global country and area datasets from the 24 November 2026 DSIR 0.15.0 audit. SDG 3.6.1 supplies two independent series. The four existing indicators and the two road traffic series provide 25,896 observations across 962 compact country files. The Phase 6 v0.6.0 plugin and Western Pacific data remain the baseline.

Open the catalog at a fixed Git commit. Resolve every manifest, geography table, provenance file, and country CSV path against the directory of that catalog at the same commit. The manifests record series, units, supported dimensions, retrieval times and country files, with sizes and SHA-256 digests. The SDG releases use the global reporting type. The road traffic series provide 2021 observations in this release.

To rebuild from the Phase 7 audit directory, run the commands below from the repository root. Use a clean checkout before the first Phase 7 data commit to generate a fresh snapshot directory.

```sh
Rscript --vanilla scripts/build_global_phase7.R /path/to/phase7-audit
Rscript --vanilla scripts/verify_global_phase7.R
```

The offline verifier checks all files. Pass the public commit-pinned catalog URL as its argument to verify all public manifests and provenance plus country CSVs used in the blind tests. The ordinary Chat plugin reads those public files when answering. The release requires no additional runtime or hosting service.
