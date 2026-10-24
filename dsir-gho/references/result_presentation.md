# GHO result presentation

Use this guide after inspecting the full saved response and QA. It defines a
default presentation, not a compulsory report for every request. Explain results
in the user's language and honor requested brevity, tables, charts or file formats.
Exported field names and reusable artifact filenames remain English.

## Choose the response size

| Task or result | Recommended response |
| --- | --- |
| One value or a short factual answer | One sentence or a small table with indicator/code, source/backend, place, year, population and unit; add an essential caveat and provenance/download link. No compulsory chart or findings section. |
| Indicator discovery | Candidate codes, names and the distinctions needed to select one. No observation table, invented values or chart. |
| Multiple years, places or strata | Use the standard report below, sized to the question. |
| Files only | Link the requested files and the provenance sidecar, with one short source/status note. Include material warnings even when no narrative was requested. |
| Verified empty selection | State the selected source and filters, explain the verified empty status, and give a useful next step. Do not produce zero-valued rows, a chart or numerical findings. |
| Request, parsing, paging or QA failure | State what failed and what remains unverified. Retain available diagnostic artifacts. Partial rows are diagnostic evidence, not a verified result table or chart. |

Materially different formats requested by the user take precedence over the
default layout. Keep essential evidence either visible or in clearly linked
metadata; do not create empty headings or placeholder values to fill a template.

## Standard data report

### 1. Query status

Start with a short status statement. Distinguish completed retrieval from full
coverage of every requested country/year/stratum. Put any limitation that changes
the interpretation near the affected result, even if limitations also appear later.
Read `status`, `provenance.complete`, `qa` and `coverage_by_location` together;
`status = ok` alone is not enough.

### 2. Compact metadata card

Include the following, grouping fields when that improves readability:

- Exact indicator name and code, from `indicator`.
- WHO GHO, selected backend, and API origin from `provenance`; link the actual
  query or returned metadata URL when available.
- Unit and denominator, with their evidence. Use observation context where units
  or measures vary by row. If unavailable or contradictory, state that explicitly;
  do not infer a unit from the magnitude of a number.
- Requested geography, time range and population filters from `query`, with
  actual observed coverage from the rows and `coverage_by_location`. Null core
  dimensions do not establish an all-age or both-sex population.
- Retrieval timestamp from `provenance`. Show a release/version and whether the
  values are observations or model estimates only when source evidence establishes
  them. Otherwise say "release not confirmed" or "estimate type not confirmed".
  Retrieval time is not publication time. Identify saved snapshots as such.

Full request traces and long methodology descriptions belong in linked metadata
or supplementary notes rather than in the opening card. Cite any external official
method note separately; do not silently insert it into the original API response.

### 3. Result table

Use readable labels with geography, observation year, estimate, unit and any
varying population dimensions. Shared units or strata may be stated once above
the table. Preserve published display text, missingness and meaningful returned
uncertainty bounds; do not turn a threshold such as `<0.1` into a numeric estimate.
Show the year for each country's "latest" value. Do not imply that different years
form a same-year ranking. Label a displayed subset and link the complete export.

The presentation can add labels and rearrange columns. Keep the existing
15-column `data.csv` and source JSON unchanged; store presentation or derived
data separately. See [output schema](output_schema.md) for row/context linkage.

### 4. Visualization when useful

Use a time-series chart for a meaningful trend or a comparison chart for
comparable groups. Skip it for a single point, discovery, empty results, failed
validation or a user request without charts. Include indicator, unit, years,
population and source/backend in the chart or its caption.

Plot verified finite `value_num` values; preserve returned bounds when relevant.
Keep gaps visible: do not fill them with zero, interpolate, or join a line across
missing periods as though observations were present. A separate gap marker in
plotting data is a presentation device, not an imputed source observation.
Separate differing units, strata, methodologies and backends. Do not invent
uncertainty intervals or silently aggregate counts or rates to simplify a chart.

### 5. Key findings

Usually give two to four useful findings, or fewer when the evidence supports
less. Each finding must point to table values or a reproducible calculation.
Calculate changes, ranks and summaries with deterministic code, using the full
selected data rather than terminal previews. Retain the calculation and its
inputs when producing an analytical artifact; if computation is unavailable,
report source values without an unverified derived finding.

Distinguish percentage-point differences from relative percentage changes;
relative change is undefined when the baseline is zero. Do not infer a cause
from a trend or claim statistical significance from visual differences alone.
Keep source observations, derived calculations and externally sourced contextual
explanations identifiable. A low value is not necessarily a favorable outcome.

### 6. Limitations and downloads

Mention material gaps, metadata uncertainty, QA warnings and comparability limits
without repeating every technical detail. Link the produced `data.csv` together
with `response.json`; provide `raw.json`, `manifest.json` and, for xMart,
`source_raw.json` when available. Link only artifacts that exist. Include any
separate chart or calculation artifact that was actually generated. For failed
exports, explain what could not be saved instead of presenting nonexistent files.
