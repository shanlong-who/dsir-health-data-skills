# DSIR source audit

Historical September legacy audit. Current GHO behavior follows DSIR 0.11.0 at
`885464b1fade2f8b6d02dde93f9080e4b3f4f2a5`; see [xMart behavior](../references/xmart_behavior.md)
and [source hashes](../references/metadata/dsir_reference.json). The findings below
retain their historical scope and do not validate xMart.

The standalone skill was based on a read-only inspection of DSIR **0.9.0**,
commit `e2ff6735d174769b55f9a3e55f9f36c75ce9f397` (`Edition 0.9.0`). The source
working tree was clean before and after inspection. No source package files
were changed. This document records implementation behavior, not an independent
verification of every historical statement in DSIR documentation.

## Inspection scope

All **20 R source files** were fully read. Paths below are relative to the DSIR
package root, which was separate from the new `dsir-gho` project.

| Source file | Decision for this skill |
| --- | --- |
| `R/gho.R` | Port discovery, retrieval and cleaning semantics; inspect availability and dimension helpers. |
| `R/http.R` | Preserve transient retry intent; use explicit errors for incomplete or failed downloads. |
| `R/clean_schema.R` | Preserve exact 15-column order and scalar types. |
| `R/data.R` | Preserve the documented Member State scope and versioned naming snapshot. |
| `R/iso3_to_region.R` | Use country-region metadata as a lookup, not an aggregation recipe. |
| `R/iso3_to_m49.R` | Inspect identifier semantics; a standalone conversion API is outside scope. |
| `R/m49_to_iso3.R` | Inspect identifier semantics; SDG-specific conversion is outside scope. |
| `R/bind_indicators.R` | Preserve the principle of stable schemas and retained row order; cross-source binding is outside scope. |
| `R/snapshot.R` | Preserve the principle that a failed refresh must not replace a good result; RDS support is outside scope. |
| `R/sdg.R` | Read and exclude UN SDG endpoints, filtering and cleaning. |
| `R/sdg_coverage.R` | Read and exclude UN SDG series aggregation. |
| `R/aarr.R` | Read and exclude progress-rate estimation. |
| `R/age_standardize.R` | Read and exclude direct standardization and uncertainty calculations. |
| `R/life_table.R` | Read and exclude life-table construction. |
| `R/geomean.R` | Read and exclude analytical aggregation. |
| `R/ggpie.R` | Read and exclude plotting. |
| `R/theme_dsi.R` | Read and exclude both plotting themes and their shared helper. |
| `R/scale_dsi_col.R` | Read and exclude plotting scales. |
| `R/flextable_defaults.R` | Read and exclude R table formatting. |
| `R/DSIR-package.R` | Read and exclude R namespace/package machinery. |

Also inspected: `data-raw/who_countries.R`; the shipped `who_countries` and
regional `.rda` datasets; GHO, cleaning and geography tests; relevant README,
NEWS and vignette sections. `data-raw/who_std_pop.R` is unrelated to GHO
retrieval and is not a source for this skill.

The source `AGENTS.md` describes an older 0.7.0 state. Current R implementation
and tests take precedence when they disagree. For example, current HTTP
timeout is 30 seconds, not the earlier 20 seconds described in that file.

## Discovery, requests and pagination

- `R/gho.R:42-79`: catalogue endpoint `/api/Indicator`; output columns
  `IndicatorCode`, `IndicatorName`, `Language`. Scalar search strings split
  on whitespace; a vector retains each element verbatim. Terms use
  case-insensitive literal substrings and AND semantics. Search apostrophes
  are doubled before URL encoding.
- `R/gho.R:125-224`: data endpoint `/api/{indicator}`. Spatial type, area,
  inclusive year bounds and dimension filters combine with AND. Area and
  dimension alternatives use OData `in`. An area without explicit spatial
  type implies country in DSIR.
- `R/http.R:13-23`: JSON Accept header, 30-second timeout, three attempts,
  capped exponential backoff, retry HTTP 429/500/502/503/504 and connection
  failures; 400/404 are not retried.
- `R/gho.R:640-699`: follow `@odata.nextLink`, append pages without removing
  duplicates, skip empty `value` arrays. A failed later page discards the
  whole result. The new skill reports a failure explicitly instead of
  returning an empty table that could be mistaken for absence of data.
- `R/gho.R:254-265,291-340,386-422,459-470`: lightweight availability,
  count, coverage and dimension queries use `$top`, `$count` and `$select`.
  Coverage counts observations across strata, not unique years. Dimension
  values are not dimension labels; labels need their own codelist lookup.

## Exact DSIR core cleaning contract

The canonical schema is `R/clean_schema.R:18-35`. Cleaning is implemented at
`R/gho.R:587-636`.

| Core column | Source or rule |
| --- | --- |
| `source` | Constant `gho`. |
| `id` | `IndicatorCode`, not WHO observation `Id`. |
| `indicator` | First matching catalogue `IndicatorName`; ignore any name field in the raw observation. |
| `location` | `SpatialDim`, retained even when outside the Member State table. |
| `iso3` | Exact case-sensitive match to the 194-country DSIR snapshot, otherwise null. |
| `location_name` | DSIR `name_short`, or the seven regional/global names below, otherwise null. |
| `year` | Integer conversion of `TimeDim`; fractional values truncate toward zero. |
| `value` | Raw `Value` converted to a string; empty strings and literal `NA` remain literal. |
| `value_num` | Numeric conversion of `NumericValue`, independently of `Value`. |
| `low`, `high` | Numeric conversion of `Low`, `High`. |
| `series` | Null for GHO. |
| `dim1`, `dim2`, `dim3` | Raw `Dim1`, `Dim2`, `Dim3` codes, without remapping or collapsing. |

Column order is exactly the table order. Missing source columns become typed
missing values. Python JSON uses null for missing scalars; the schema must
remain available even for an empty list. Rows sort by location then year,
missing values last, preserving input order for ties. No strata or duplicate
observations are dropped. No rate, total, sex combination or regional value
is calculated by the cleaner.

Regional names at `R/gho.R:489-515` are AFR = Africa, AMR = Americas,
SEAR = South-East Asia, EUR = Europe, EMR = Eastern Mediterranean,
WPR = Western Pacific and GLOBAL = Global. Variant aggregate codes such as
`WPR_WO_IDN` retain a null `location_name` in the exact core schema. Live
resolved labels belong in separate metadata, preserving DSIR compatibility.

DSIR lazily caches a successful nonempty indicator catalogue per R session
(`R/gho.R:474-485,519-527`). The Python cleaner receives the catalogue from
the caller and performs no network request. Finite JSON numeric values are
supported; non-finite values become null so output remains valid JSON and
QA identifies the missing estimate. This is a deliberate serialization
safeguard, not a claim that R's `Inf` and JSON null are identical.

## Geography snapshot and live resolution

`data-raw/who_countries.R:40-257` contains 194 Member States;
`:265-280` defines 13 short-name overrides; `:288-289` defines 14 PICs;
`:364-375` assembles the eight-column country table; `:414-420` derives
sorted region vectors. The original `.rda` was loaded in R 4.6.1 and exported
without executing the builder or rewriting source files. Hashes, version and
scope are in `references/metadata/provenance.json`.

Binary checks confirmed AFR 47, AMR 35, SEAR 10, EUR 53, EMR 21 and WPR 28.
All six shipped regional vectors exactly matched their sorted country-table
subsets. Indonesia is in WPR and absent from SEAR. Cook Islands and Niue are
included as WHO Members. Puerto Rico, Tokelau and other non-Member areas are
outside the snapshot. Namibia's ISO2 is the literal string `NA`; M49 codes
retain leading zeros. The income column is the FY2027 vintage documented by
DSIR and is not used to resolve a GHO query.

The versioned WPRO vector is:

```text
AUS BRN CHN COK FJI FSM IDN JPN KHM KIR KOR LAO MHL MNG MYS
NIU NRU NZL PHL PLW PNG SGP SLB TON TUV VNM VUT WSM
```

This vector is a reference snapshot, not a replacement for official regional
observations. The resolver accepts exact country identifiers/names and a
small, explicit alias dictionary. It resolves WPR/WPRO/Western Pacific aliases
to an official aggregate. Non-Member reporting areas and variant region
codes use live COUNTRY/REGION/GLOBAL codelists. `WPR_WO_IDN` must be verified
in live metadata; it is never implemented by removing Indonesia from a
downloaded or hardcoded country list. Congo and Korea require an explicit
choice. A bad item in a multi-location request is reported as unresolved;
successfully resolved neighbors do not turn the batch into a silent success.

## Observed bugs and compatibility boundaries

1. Area apostrophes are not escaped at `R/gho.R:173-176`, unlike search and
   dimension values. New requests should escape every OData string literal.
2. DSIR accepts an NA indicator as `/api/NA`, reversed year bounds and weakly
   validated year values at `R/gho.R:142,181-185`. These are validation gaps,
   not behaviors to reproduce in a new user-facing client.
3. `gho_dimensions(..., "TimeDim")` returns integer values even though its
   documentation says character. Preserve value meaning, not that inaccurate
   documentation claim.
4. The source pagination loop has no cycle/limit/next-link validation. Its
   final base `rbind` can fail if page columns differ. A new client should
   detect malformed/incomplete downloads explicitly.
5. `vignettes/DSIR.Rmd:176` incorrectly says GHO `location_name` is empty;
   current cleaner resolves Member and regional names.

## Verification

Read-only R probes confirmed catalog precedence, stable missing-value
ordering, retained literal strings, decimal-year truncation, non-Member
handling, the area-escaping bug, NA-indicator acceptance and the dimension
return-type mismatch. Synthetic Python tests exercise the exact schema,
values versus numeric estimates, duplicate/stratum preservation, country
snapshot identity and hash, ambiguous names, official aggregates, non-Member
live lookup, unresolved batch inputs, propagation of metadata failures and
QA detection of response/filter mismatch. These tests do not establish live
WHO service availability; live checks are recorded separately by the client.
