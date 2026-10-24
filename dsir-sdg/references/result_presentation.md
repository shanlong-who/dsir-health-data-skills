# SDG result presentation

Use the full saved response and QA, not the terminal preview. This is a default
layout, not a compulsory report. Answer in the user's language, honor requested
brevity and keep exported field names and reusable artifact filenames in English.

## Choose the response size

| Task or result | Recommended response |
| --- | --- |
| One value | A sentence or small table with indicator and series codes, country/year, stratum, unit and UN SDG source; include essential caveats and provenance. No compulsory chart. |
| Indicator or series discovery | Candidate codes, official descriptions and meaningful differences. No invented observations or chart. |
| Multiple places, years or strata | Use the standard report below, sized to the question. |
| Files only | Link the requested exports and `response.json` with a short source/status note and any material warning. |
| Verified empty selection | State the selected series/filters and verified empty status, then a useful next step. No zero-valued row, numerical finding or chart. |
| Request, parsing, pagination or QA failure | Explain what failed and remains unverified. Retain available diagnostics; partial rows are not a verified result table. |

User-requested formats take precedence. Do not add empty headings or fabricate
metadata to complete a template. Essential context can be compact or linked.

## Standard data report

1. **Query status.** Read `status`, `qa`, `coverage_by_location`, `pages`,
   `retrieved_row_count` and the request evidence together. Completed pagination
   does not mean every requested country, year or stratum has observations.
   The SDG response does not have GHO's `provenance.complete` field; do not invent
   it or infer completeness from a single HTTP success.
2. **Compact metadata.** Give the indicator code/description, actual series
   code/description and methodology, geography, requested filters and observed
   coverage. Identify the UN SDG Global Database and actual API URL; retain
   custodian/original-source text separately. Decode unit and Nature codes using
   returned metadata when available. Preserve undecoded codes and say what is
   unknown. Report a release only from returned evidence, and retrieval time
   separately. Label saved snapshots with their original dates.
3. **Table.** Use readable area names, observation years, estimates, units and
   all varying population dimensions. Shared context may appear once above the
   table. Preserve published display strings and uncertainty bounds. For
   `<0.1`, show the threshold without inventing an exact estimate. Show each
   country's actual year for latest-value comparisons. Identify displayed
   subsets and link the complete export.
4. **Chart when useful.** Plot verified finite `value_num` values with meaningful
   returned bounds. Keep missing periods visible: no zero filling, interpolation
   or line across gaps. Separate different series, methods, units and strata.
   Include indicator/series, unit, years, population and UN SDG source in the
   figure or caption. Skip charts for single values, discovery, failures and
   requests that exclude them.
5. **Findings.** Give only findings supported by source values or deterministic
   calculations using the full selected data. Retain inputs and calculation
   code for analytical artifacts. Distinguish percentage points from relative
   percentage change, and index points from both. Relative change from zero is
   undefined. Do not infer causation or significance from a chart, average
   country indexes into a regional estimate, or mix overlapping strata.
6. **Limits and downloads.** State material missingness, QA warnings, release
   uncertainty and comparability limits near affected results. Offer actual
   `observations.csv`, `response.json`, `raw.json` and `manifest.json` artifacts.
   `dsir_clean.csv` is for interoperability; its 15 columns alone omit SDG units
   and dimensions. Link charts or calculation files only if they exist.

## SDG-specific interpretation

An SDG indicator is not one homogeneous statistic. Never splice two series or
methodologies simply because they share an indicator number. In particular,
an index is not a percentage, and a changed financial-protection threshold or
denominator answers a different question. Verify current descriptions rather
than treating a historical test expectation as a current definition.

Use `observation_context`, aligned to the clean rows, for dimensions, attributes,
source and footnotes. Null `dim1`/`dim2`/`dim3` in the core does not mean all ages
or both sexes. Missing dimensions are unknown, not an implicit total category.
If source details contradict one another, show the conflict instead of choosing
the most convenient interpretation.

Keep original exports unchanged. Presentation labels, gap markers and derived
calculations belong in separate files. Official methodological context is cited
separately; it cannot establish the release or replace the retrieved values.
See [output schema](output_schema.md) for the row/context linkage.
