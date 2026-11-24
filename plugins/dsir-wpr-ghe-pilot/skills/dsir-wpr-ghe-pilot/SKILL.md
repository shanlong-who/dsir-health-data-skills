---
name: dsir-wpr-ghe-pilot
description: Read and compare dated Western Pacific health snapshots for GHE all-cause deaths by sex, TB incidence, DTP3 immunization coverage and skilled birth attendance. Use for counts, years, uncertainty bounds, coverage and data downloads.
---

# Western Pacific health snapshots

For release 0.5.1 open the [fixed regional catalog](https://raw.githubusercontent.com/shanlong-who/dsir-health-data-skills/17016b3f12e6729e1d151ac21a37a3455a62b662/snapshots/phase5/catalog.json). Follow the matched entry's pinned manifest. The GHE entry for this release is `wpr-ghe-deaths`, scope `regional`, run `45379887521`. Open its [fixed regional GHE manifest](https://raw.githubusercontent.com/shanlong-who/dsir-health-data-skills/a7382185415466540ef91c3f5d32decf5eb18ecd/snapshots/wpr-ghe-deaths/manifest.json) and check all three identifiers before classifying any country or giving an estimate. A Philippines-only manifest belongs to an earlier pilot. If a reader returns that old manifest, open the fixed links above, inspect the regional geography and select the requested area anew. If the release identity cannot be verified, report a file-access problem and withhold coverage claims. Use the full manifest or search its area entries by exact ISO3 when the initial excerpt is truncated. Resolve only requested measures and clarify ambiguous queries.

Read the area's pinned observations URL. If inaccessible, use the same manifest's full observations CSV and select the area explicitly. Read real rows before giving numbers. Never substitute different sources for an inaccessible file or missing observation. Provide the CSV link actually used. Report dates of observation and retrieval separately. Cite catalog, manifest and provenance when relevant. Distinguish SHA-256 recorded in metadata from one you actually recomputed.

## Selecting GHE deaths

GHE returns WHO estimates. Match the full key: area_code, year, sex, age, cause_code and measure. Use age TOTAL, cause_code 0 (All Causes) and measure deaths only. There are distinct FEMALE, MALE and TOTAL source records. For a combined or unqualified population use the published TOTAL row and label it. For a sex-specific request select that exact sex. Never add a total to its sex components or sum subgroup bounds. Preserve source decimals and give the point estimate and low and high from the same row. Unit is deaths (persons). This snapshot has no age-standardized rate, cause-specific count, age subgroup or DALY; say the requested dimension or measure is outside the snapshot. Never reconstruct one from the count or population column. This lookup makes no live request to WHO.

## Other indicators and coverage

For WHO GHO tuberculosis incidence report cases per 100,000 population. For DTP3, report WHO/UNICEF WUENIC coverage among one-year-olds. For UN SDG 3.1.2 select SH_STA_BRTC, reporting type G, and report the percentage of live births attended by skilled health personnel. Preserve each source and denominator. Missing bounds are unreported. Never compare percentages with different denominators by subtraction.

Use geography.areas and, for GHE, the specific sex stratum's available years. Distinguish outside roster, in roster with no observations, an unavailable stratum or measure, year outside the snapshot, an absent year inside it, a row with a missing estimate, and a recorded zero. Summarize absent combinations separately from missing values in existing rows. Keep such missing years out of tables labelled original observations. Never impute, extrapolate or treat missing as zero.

For latest, select the maximum year with a nonmissing estimate separately for each exact selection. For the most recent common year, intersect those observed year sets and look up each value in the maximum common year. If the intersection is empty, report it. Label results as latest within the snapshot. Give the native unit, reported bounds and separate source for each indicator. Regional aggregates require their own published series.
