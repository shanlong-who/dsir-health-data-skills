---
name: dsir-global-health-series-pilot
description: Retrieve dated global DSIR observations across WHO GHO, UN SDG and WHO GHE, or check which source series have been published in this pilot. Use for country series, latest years, bounds, CSV downloads and supported dimensions.
---

# DSIR global health snapshots

Open the [fixed Phase 8 catalog](https://raw.githubusercontent.com/shanlong-who/dsir-health-data-skills/b1c61e8901e9bb1d2bd4e20136b1804fc63b5ca0/snapshots/phase8/catalog.json) in this conversation. Confirm release 0.8.0 and scope `global_country_area`. Resolve each `path` against the directory of this catalog at the same Git commit, including paths inside manifests. Use a web reader or retrieval tool to read the files. Report a retrieval failure explicitly and withhold results that require the unavailable file.

## Read observations

1. Resolve the exact dataset and series. Load its manifest and use the `areas` entry to read each country CSV. Use the catalog geography CSV for name resolution. Join on `area_code` where provided, or ISO3 for standard country files. The UN SDG area Kosovo uses `SDG-412`, identified as UN SDG area code 412. Country files for other sources use their own coverage.
2. Match all requested years and dimensions. Latest means the greatest year with a nonblank estimate in each requested series or stratum. For a common year, intersect the nonblank estimate year sets. Preserve each published count, rate and bound. Numeric 0 is a value. A blank estimate or blank bound is missing as published. Distinguish a year outside the series range, a place without a dataset file, and a year or stratum without a matching row in a place file.
3. Report the exact series, place, requested dimensions, year, estimate, bounds, unit and denominator when applicable. Include its product, backend and retrieval time or interval from the manifest. Cite each CSV as a Markdown link with the literal, fully resolved HTTPS URL so links remain usable when copied. Link the manifest and open detailed provenance when requested.

## Series and dimensions

- `uhc` is GHO xMart `UHC_INDEX_REPORTED`, the UHC service coverage index on a 0–100 scale. Use the published index. There is no sex split in this export.
- `child` is UN SDG 3.2.1, reporting type `G`. `SH_DYN_IMRT` and `SH_DYN_IMRTN` are the infant mortality rate and death count, age `<1Y`. `SH_DYN_MORT` and `SH_DYN_MORTN` are the under-five rate and count, age `<5Y`. Rate units are deaths per 1,000 live births. Match the requested `FEMALE`, `MALE`, or `BOTHSEX` value, using and labeling the published `BOTHSEX` observation for unstratified requests. Infants are part of the under-five age group. Do not add those age groups.
- `ghe_extended` supplies deaths and death rates for all causes (`0`) and stroke (`1140`) and ages `TOTAL` and `Y40T44`. Use `FEMALE`, `MALE`, or `TOTAL` and label the stratum. The all-age death rate is crude. The 40–44 rate is age-specific, per 100,000 persons in that age group. Rate bounds are unreported. An age-standardized query is outside this release. The carried `ghe` dataset supplies the Phase 7 all-age, all-cause death-count baseline and its original retrieval metadata. Use `ghe_extended` whenever the user asks for the new dimensions or a rate.
- `tb` is GHO `MDG_0000000020`, incidence per 100,000 population. `dtp3` is GHO `WHS4_100`, coverage of one-year-olds. `sba` is SDG 3.1.2 series `SH_STA_BRTC`, percentage of live births, reporting type `G`.
- `road` is SDG 3.6.1. `SH_STA_TRAFN` is deaths. `SH_STA_TRAF` is deaths per 100,000 population. Read each original series with its own bounds. Treat blank bounds and zeros independently.

## Discovery and limits

The catalog's `index.published` lists directly answerable snapshots with their geographic counts and years. The broader GHO and SDG index files expose source codes, and the GHE files expose cause and measure dictionaries. A `discoverable_availability_pending` entry has no verified snapshot. For GHE, `selected_strata_snapshotted` applies to the exact combinations in the manifest. Use the source indexes to assist discovery when needed, then confirm snapshot availability in the catalog and manifest before returning values.

Do not switch source or version, interpolate, aggregate overlapping age groups, calculate bounds or derive rates. Global aggregate and regional observations are outside the country and area snapshot. Use each dataset's own latest observed year and retrieval time. For broad requests return a compact summary or files when the evidence supports it.
