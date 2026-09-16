# DSIR SDG parity results

Generated: 2026-09-16T06:33:12.587957+00:00

Overall: PASS. Mode: `independent_live_R_and_common_input`.
Original DSIR 0.9.0, commit `e2ff6735d174769b55f9a3e55f9f36c75ce9f397`; R version 4.6.0 (2026-04-24 ucrt).
Distinct live-snapshot indicators: 13.
Bundled country mapping agrees with original source: True.
Common-input checks: 22 passed; 0 failed.
Independent R live retrieval checks: 13 passed; 0 failed.

Checks cover all 15 ordered fields, row sequence and multiplicity, scalar types, indicator, location, year, series, numeric values and bounds, and per-column missingness. Numeric tolerance: absolute 1e-10, relative 1e-12. The exact unmodified R source and its country asset are evaluated in an isolated environment. R is not bundled or needed by users.

Common-input checks do not independently prove retrieval parity. Independent live checks, when enabled, also compare raw dimensions and attributes. DSIR's dim1/dim2/dim3 are always missing for SDG; enriched skill output must preserve SDG dimensions separately.

| Case | Fixture | Common-input parity | Rows (Python/R) |
| --- | --- | --- | --- |
| live-3.8.1 | Live snapshot | PASS | 72/72 |
| live-3.1.1 | Live snapshot | PASS | 9/9 |
| live-3.1.2 | Live snapshot | PASS | 2/2 |
| live-3.2.1 | Live snapshot | PASS | 120/120 |
| live-3.2.2 | Live snapshot | PASS | 20/20 |
| live-3.3.1 | Live snapshot | PASS | 130/130 |
| live-3.3.2 | Live snapshot | PASS | 10/10 |
| live-3.3.3 | Live snapshot | PASS | 10/10 |
| live-3.4.1 | Live snapshot | PASS | 12/12 |
| live-3.4.2 | Live snapshot | PASS | 12/12 |
| live-3.8.2 | Live snapshot | PASS | 45/45 |
| live-2.2.1 | Live snapshot | PASS | 60/60 |
| live-6.1.1 | Live snapshot | PASS | 30/30 |
| synthetic_empty | Synthetic | PASS | 0/0 |
| synthetic_missing_columns | Synthetic | PASS | 1/1 |
| synthetic_censored_and_missing | Synthetic | PASS | 3/3 |
| synthetic_members_and_aggregates | Synthetic | PASS | 5/5 |
| synthetic_indicator_links | Synthetic | PASS | 2/2 |
| synthetic_atomic_indicator | Synthetic | PASS | 1/1 |
| synthetic_duplicate_dimensions | Synthetic | PASS | 3/3 |
| synthetic_numeric_formats | Synthetic | PASS | 4/4 |
| synthetic_all_member_locations | Synthetic | PASS | 194/194 |

| Independent R retrieval | Result | Raw dimensions and attributes |
| --- | --- | --- |
| live-3.8.1 | PASS | PASS |
| live-3.1.1 | PASS | PASS |
| live-3.1.2 | PASS | PASS |
| live-3.2.1 | PASS | PASS |
| live-3.2.2 | PASS | PASS |
| live-3.3.1 | PASS | PASS |
| live-3.3.2 | PASS | PASS |
| live-3.3.3 | PASS | PASS |
| live-3.4.1 | PASS | PASS |
| live-3.4.2 | PASS | PASS |
| live-3.8.2 | PASS | PASS |
| live-2.2.1 | PASS | PASS |
| live-6.1.1 | PASS | PASS |
