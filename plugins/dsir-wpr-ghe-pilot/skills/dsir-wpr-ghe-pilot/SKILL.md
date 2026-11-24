---
name: dsir-wpr-ghe-pilot
description: Read and compare dated Western Pacific health snapshots for GHE all-cause deaths by sex, TB incidence, DTP3 immunization coverage and skilled birth attendance. Use for counts, years, uncertainty bounds, coverage and data downloads.
---

# Western Pacific health snapshots

Always open the [Phase 5 catalog](https://raw.githubusercontent.com/shanlong-who/dsir-health-data-skills/refs/heads/pilot/wpr-ghe-phase5/snapshots/phase5/catalog.json). Resolve only requested measures and follow each entry's pinned manifest. Inspect its scope, years, geography, supported dimensions, unit, product, retrieval time and run. The GHE entry can cover just the Philippines in 2023 or a larger regional roster. Answer from the manifest reached in this chat. Do not rely on previous releases. When the question is ambiguous about the measure or comparison, clarify.

Read the area's pinned observations URL. If inaccessible, use the same manifest's full observations CSV and select the area explicitly. Read real rows before giving numbers. Never substitute different sources for an inaccessible file or missing observation. Provide the CSV link actually used. Report dates of observation and retrieval separately. Cite catalog, manifest and provenance when relevant. Distinguish SHA-256 recorded in metadata from one you actually recomputed.

## Selecting GHE deaths

GHE returns WHO estimates. Match the full key: area_code, year, sex, age, cause_code and measure. Use age TOTAL, cause_code 0 (All Causes) and measure deaths only. There are distinct FEMALE, MALE and TOTAL source records. For a combined or unqualified population use the published TOTAL row and label it. For a sex-specific request select that exact sex. Never add a total to its sex components or sum subgroup bounds. Preserve source decimals and give the point estimate and low and high from the same row. Unit is deaths (persons). This snapshot has no age-standardized rate, cause-specific count, age subgroup or DALY; say the requested dimension or measure is outside the snapshot. Never reconstruct one from the count or population column. This lookup makes no live request to WHO.

## Other indicators and coverage

For WHO GHO tuberculosis incidence report cases per 100,000 population. For DTP3, report WHO/UNICEF WUENIC coverage among one-year-olds. For UN SDG 3.1.2 select SH_STA_BRTC, reporting type G, and report the percentage of live births attended by skilled health personnel. Preserve each source and denominator. Missing bounds are unreported. Never compare percentages with different denominators by subtraction.

Use geography.areas and, for GHE, the specific sex stratum's available years. Distinguish outside roster, in roster with no observations, an unavailable stratum or measure, year outside the snapshot, an absent year inside it, a row with a missing estimate, and a recorded zero. Summarize absent combinations separately from missing values in existing rows. Keep such missing years out of tables labelled original observations. Never impute, extrapolate or treat missing as zero.

For latest, select the maximum year with a nonmissing estimate separately for each exact selection. For the most recent common year, intersect those observed year sets and look up each value in the maximum common year. If the intersection is empty, report it. Label results as latest within the snapshot. Give the native unit, reported bounds and separate source for each indicator. Regional aggregates require their own published series.
