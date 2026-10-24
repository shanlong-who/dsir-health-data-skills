# GHE result presentation and export

Use the full saved response, including QA and provenance. This is a default,
not a mandatory report. Answer in the user's language and honor brevity or
files-only requests. Reusable artifact filenames and exported fields stay English.

For a standard comparison:

1. State whether retrieval completed and whether all requested selections have
   observations. Explain material failures before any values.
2. Give compact metadata: WHO GHE, xMart table and actual request links, cause
   codes/names, measure, unit, rate type where applicable, countries, years, sex
   and age, retrieval time and available release evidence. Label missing release
   or method details as unknown. Identify saved snapshots with their dates.
3. Show a readable table with all varying strata and units. Preserve missingness
   and available uncertainty bounds. Distinguish persons, years, rates per
   100,000 and percentages. Show the actual year of each latest-country estimate.
4. Add a chart only when it helps the task. Use verified numeric values, label
   source/unit/strata, show gaps without interpolation or a line across missing
   years, and separate incompatible measures. Never invent intervals.
5. Give useful findings supported by source values or deterministic calculations.
   Retain inputs and calculation code for analytical artifacts. Distinguish
   absolute changes, percentage points and relative changes; a zero baseline
   cannot support relative percentage change. No inferred causal explanation
   or statistical significance.
6. State material limitations and link the actual data and provenance files.

For a single value, combine the essential metadata with a short sentence or
small table and a provenance link. Discovery needs only candidates and relevant
distinctions. Files-only requests need links and a short source/status note.
Empty or failed results need the outcome, filters and useful next step, without
invented zeros, numerical findings or a compulsory chart.

## Export contract

`data.csv` and `response.json.data` retain DSIR's 16 GHE fields:
`iso3, location_name, year, sex, age, cause_code, cause_name, measure, value, low,
high, population, unit, level, cause_group, rankable`. This is not GHO's 15-column
core. Source rows are pivoted into one row per requested measure and sorted by
country/year/sex/age/cause/measure. All-missing measures are retained.

`observation_context` links each clean row to `raw_row_index` and `source_row_id`,
and records provider field and rate type. `raw.json` retains the actual selected
source records and their original field values; it is not a full-table download.
`manifest.json` hashes the exported files. A failed request may have only a
diagnostic `response.json` and manifest; never link a nonexistent CSV.

Keep original files unchanged. Put plot labels, gap markers and derived results
in separate artifacts. Relevant external method context and any explicitly
authorized other-source comparison remain separately attributed and do not
alter the GHE export.
