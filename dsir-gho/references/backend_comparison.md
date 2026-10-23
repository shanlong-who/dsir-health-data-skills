# GHO backend identity and comparison

| Interface | Default source | Explicit selection |
| --- | --- | --- |
| DSIR 0.11.0 GHO, session option unset | `https://ghoapi.azureedge.net/api` | `backend = "legacy"` or `backend = "xmart"` |
| GHO Skill, local Phase 1 candidate | `https://ghoapi.azureedge.net/api` | `--backend xmart` or `--backend legacy`, before the subcommand |

DSIR's explicit argument overrides `DSIR.who_backend`; an unset option means
legacy. The Skill does not read that R option. Neither project silently falls
back. A failed or empty request is not permission to use the other source.

The local Phase 1 candidate uses 1000-row legacy pages and 5000-row xMart pages.
An explicit legacy page size above 1000 fails locally. Existing commands remain
valid, but callers relying on the previous xMart default must add `--backend xmart`.
Published archives and installed copies have not been replaced by this local work.

Automatic fallback is disabled. A possible future opt-in policy would require
explicit prior user authorization, verified catalogue absence (not HTTP 404 alone),
the identical target code, validated target dimensions, and a separately labelled
complete extraction. It must record both attempts and cannot fill gaps or merge
releases. Current APIs do not establish release equivalence, so explicit backend
selection is the smaller and safer Phase 1 design. Network, parsing, pagination,
parameter and empty-selection outcomes must never trigger fallback.

The Skill's pinned reference, DSIR commit
`885464b1fade2f8b6d02dde93f9080e4b3f4f2a5`, precedes
[`5ee3a41`](https://github.com/shanlong-who/DSIR/commit/5ee3a41feca301c9dd007e323235268aa7a4dc91),
which restored the default before DSIR 0.11.0 was released. The historical
reference hashes remain valid evidence for that snapshot; they are not hashes
of final DSIR 0.11.0. Do not rewrite old reports to imply otherwise.

## Tell users which source was queried

Keep the entire export directory. The CSV has exactly 15 core columns;
`source = "gho"` identifies the data family and cannot identify its backend.
Read `response.json` fields `provenance.backend`, `base_url`, `query_url`,
`table`, `filter`, `retrieved_at` and `complete`. For xMart, also retain
`provenance.route`, native source fields and `source_raw.json`. The selected
`IND_ID` and `IND_PER_CODE` matter when several directory entries share a code.
`manifest.json` protects file integrity, not semantic equivalence.

For DSIR, retain raw `Provider`, the `who_provenance` attribute in an RDS,
and cleaned `provider` with `keep_metadata = TRUE`. CSV loses R attributes.
Use the same explicit backend for discovery, descriptions, dimensions and data.
Even same-backend queries can differ in time, filters or transformations.

## Review before matching values

Check both live catalogues and official definitions, units, target population,
estimate type, geography, annual/nonannual time basis, all native dimensions,
numeric measure families, publication state and dataset release information.
An identical GHO code or near-identical title is only a candidate mapping.
Record evidence for every mapping, including absent dimensions. A null field
does not automatically mean a population total. Do not align `Dim1` positions
without checking their types and native code lists.

Construct a complete observation key after that review. Keep extra strata and
geographic variants distinct. Duplicate keys prevent an unambiguous comparison;
do not deduplicate or aggregate them to force agreement. Match independently
retrieved complete extracts, report unmatched keys and missingness, and compare
numeric values and bounds using declared tolerances. Keep source display labels
separate from numeric equivalence. Do not impute, splice sources or substitute
another indicator. Retrieval and load timestamps are not dataset release IDs.

## Three different validation questions

1. Offline transport/cleaning contracts validate controlled inputs.
2. Same-backend R/Skill parity compares two implementations against the same
   selected source. The pinned runner explicitly selects xMart in R.
3. Cross-backend comparison checks separately reviewed legacy and xMart
   definitions and independent observations. The first two cannot prove this.

The 7 October 2026 reports passed offline and common-input tests while leaving
17 independent live cases unverified. A later narrow live sample does not
complete that suite or validate other indicators, locations, strata or years.

## Maintainer R comparison tool

`evals/compare_backends.R` is excluded from runtime packages. It requires R and
jsonlite only; the regression tests also use testthat. It performs no network
request and changes no observations. Supply an approved review with reviewer,
date, exact backend codes, complete `key_fields`, and `checks` for `catalogues`,
`definition`, `unit`, `population`, `estimate_type`, `geography`, `time`,
`dimensions` and `release`. Each check requires `status = "verified"` and a
nonempty evidence reference. Approval is a recorded metadata review, never an
inference from equal numbers. Review evidence can describe distinct known
releases; a comparison then measures revision differences rather than asserting
the same vintage. Unresolved releases remain unverified.

Each extract is a list with `indicator_code`, a `data` frame, and `provenance`
containing `backend`, `complete = TRUE`, `query_url` and `retrieved_at`. Map
native keys explicitly before calling the tool; it performs no guessed mappings.
For DSIR, explicitly adapt its `retrieved` timestamp and xMart table/filter
provenance to this audit structure while retaining the original provenance.

```r
library(jsonlite)
source("dsir-gho/evals/compare_backends.R")

review <- read_json("review.json", simplifyVector = TRUE)
result <- compare_backend_extracts(legacy_extract, xmart_extract, review,
                                  key_fields = review$key_fields)
write_json(result, "comparison.json", pretty = TRUE, auto_unbox = TRUE,
           na = "null", null = "null")
```

The tool blocks unreviewed metadata, mismatched source codes, incomplete pulls,
unknown or duplicate keys, and omitted reviewed dimensions. It reports coverage
differences, NA/value differences and changed bounds separately. `equal` means
agreement only within the approved selection and numeric tolerance. Empty or
disjoint extracts report `no_overlap`, never equality.
