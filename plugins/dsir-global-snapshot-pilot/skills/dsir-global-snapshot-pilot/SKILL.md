---
name: dsir-global-snapshot-pilot
description: Look up and compare country or area estimates from the dated worldwide DSIR pilot for TB incidence, DTP3, skilled birth attendance, GHE all-cause deaths by sex, and SDG road traffic deaths and death rates. Use for years, coverage, units, bounds and CSV downloads.
---

# DSIR worldwide health snapshots

Use the public [Phase 7 fixed catalog](https://raw.githubusercontent.com/shanlong-who/dsir-health-data-skills/04f9802eaf8053cddaccda0e4abd84a04be72887/snapshots/phase7/catalog.json) for release 0.7.0, scope `global_country_area`, snapshot date 2026-11-24. Read it in this conversation. Use the available web reader or a file retrieval tool to read the literal URLs. A search result or remembered value cannot establish the contents of a snapshot.

## Read a country or area

1. Select the dataset and series from the catalog. Open its manifest and confirm the dataset, release, scope and series. Every `path` field in the catalog and manifests is relative to the directory of the fixed catalog URL, including paths inside a dataset manifest. To construct the actual URL, remove only `catalog.json` and append the exact `path` at the same commit. Use the verified manifest's `areas` map to obtain each requested country CSV. If a country name or code is ambiguous or absent from the map, open the catalog's `geography` CSV, which lists M49 codes, ISO3 codes, names and regions.
2. Open each requested country CSV. Filter `series_code`, `year` and the requested dimensions before reading `estimate`, `low`, `high` and `audit_unit`. For the latest year, choose the maximum year with a nonblank estimate for each requested geographic and series combination. For the latest common year, intersect the nonblank estimate years across the requested countries or series after dimension filters. If the intersection is empty, state that and show each latest result.
3. Report the requested rows in a compact table with place, series, dimensions when used, year, estimate, bounds, unit and denominator when supplied. Preserve source precision and cite the exact CSVs used. Give the data product, backend and retrieval time or interval from each manifest. If granular provenance is requested, open the manifest's `provenance` file.

## Select the exact series

- `tb` / `MDG_0000000020` is TB incidence per 100,000 population. `dtp3` / `WHS4_100` is DTP3 coverage among one-year-old children.
- `sba` / SDG 3.1.2 / `SH_STA_BRTC` is skilled birth attendance as a percentage of live births. Use reporting type `G`.
- `ghe` / cause `0` / `deaths` is all-age, all-cause deaths. Select `FEMALE`, `MALE`, or `TOTAL` as requested. The published `TOTAL` is the both-sex estimate. Keep its own bounds. If a request is unstratified, use the `TOTAL` row and label it. This snapshot supplies death counts for `age=TOTAL` only.
- `road` / SDG 3.6.1 includes two different series. `SH_STA_TRAF` is the death rate per 100,000 population. `SH_STA_TRAFN` is the published count of deaths. Filter each code independently, use its own units and bounds, and report both if requested. Use reporting type `G`. There is no sex breakdown in these files.

## Describe coverage and missingness

- A place missing from the M49 roster is outside the geographic scope. A place in the roster with no manifest entry has no observations for that dataset. A place file with other observations may still lack the requested series, year or stratum.
- Use the manifest's series year range to distinguish a year outside the snapshot from a missing year inside it. For a matching row, a blank estimate means missing. A numeric zero is a published estimate, including integer or decimal zero. Report each blank bound as unreported independently of the estimate.
- Aggregates such as WHO regions, income groups and the world are outside this country and area release. Unlisted indicators and unsupported dimensions are outside its scope. Use the fixed release throughout the answer. Do not fill gaps by interpolating, calculating derived rates or bounds, switching versions, or calling a different data source.
- If opening the catalog, manifest, or a requested CSV fails, identify the affected file and state which result could not be verified. A retrieval failure cannot establish missing data. For bulk requests provide links or a compact summary when the evidence supports it.
