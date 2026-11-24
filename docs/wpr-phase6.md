# Phase 6 snapshot release rehearsal

The release checker reads the catalog and manifest URLs from the packaged Skill and compares their content with an independently supplied release record. It checks file integrity, the regional roster, snapshot ID, scope, acquisition time and workflow run. The original 0.5.1 plugin remains the accepted baseline.

Run these commands from the repository root with R, curl, openssl, jsonlite, zip and yaml installed:

```sh
Rscript --vanilla scripts/replay_release.R replay.json public
Rscript --vanilla scripts/check_release.R releases/phase6/dsir-snapshot-release-pilot-0.6.0.zip releases/phase6/release.json public public-check.json
```

The optional fourth argument to the replay command is the path to an existing 0.5.1 ZIP (after the report path and transport). Otherwise it uses the 0.5.1 source in this checkout. The replay accepts the regional catalog and rejects a test copy pointing to the authentic Philippines catalog and manifest. The release checker returns a nonzero exit status for a rejected candidate.

On the Phase 6 branch the workflow repeats the replay against Git objects, refreshes only GHE, validates against WHO xMart, pins the data, manifest and catalog, then builds the plugin ZIP from that release record. Phase 4 catalog entries keep their own acquisition dates and run IDs. The candidate is tested in ordinary Chat after public-file verification.

The two ordinary Chat checks cover Viet Nam male and both-sex deaths and Guam coverage, then Viet Nam DTP3 coverage and skilled birth attendance, including the most recent common year and the missing 2020 birth-attendance observation.
