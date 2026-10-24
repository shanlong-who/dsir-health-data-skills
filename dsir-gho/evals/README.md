# GHO evaluation and pinned-source parity

These maintainer checks are excluded from runtime packages. End users need no R.
The current reference is DSIR 0.11.0 at commit
`885464b1fade2f8b6d02dde93f9080e4b3f4f2a5`.

This is an earlier development snapshot with an xMart default, not the final
0.11.0 behavior. Released DSIR defaults to legacy. The existing parity runner
sets xMart explicitly in R and tests same-backend implementation parity; it
does not compare legacy observations with xMart observations. Keep historical
source hashes and reports unchanged.

## Phase 1 acceptance

From the repository root, use a fresh output directory for every run:

```sh
python -m unittest discover -s dsir-gho/tests -v
python dsir-gho/evals/phase1_live.py --output-dir /writable/new-live-directory
Rscript dsir-gho/evals/verify_phase1.R /path/to/DSIR /writable/new-live-directory /writable/new-r-directory
```

The first command is offline. The second makes small live WHO queries and saves
catalogues, source rows, exports and a status summary. Use `--suite base` or
`--suite extended` for a subset, or `--case NAME` to repeat one failed case.
The R check loads the specified DSIR source with test helpers disabled, retrieves
each backend independently, and compares all 15 fields for PHL/CHN DTP3 in
2020/2021. It never tests cross-backend equality. It needs jsonlite and pkgload
plus DSIR dependencies. Configure TEMP/TMP to a writable directory if the host's
sandbox cannot create normal test temporary files.

## Cross-backend regression

See [the comparison protocol](../references/backend_comparison.md). Run from
the repository root:

```r
testthat::test_file("dsir-gho/tests/test_backend_comparison.R")
```

`compare_backends.R` requires a reviewed metadata mapping and independent,
complete extracts. Its synthetic tests cover blocked metadata/release reviews,
different source identifiers, reordered rows, different strata/coverage, changed
values/bounds, NA versus zero, tolerance, duplicate keys and no overlap. They do
not label any real indicator comparable or perform live validation.

## Offline contracts

Source-boundary and adaptive-format checks are described in
[source and output acceptance](source_output_cases.md). They evaluate actual
model responses using saved evidence or labelled fixtures; passing the API tests
does not prove these presentation behaviors. Keep replay outputs outside runtime
packages and distinguish saved snapshots from fresh API retrievals.

From the repository root:

```sh
python -m unittest discover -s dsir-gho/tests -v
python dsir-gho/evals/run_evals.py --offline --output dsir-gho/reports/new-offline.json
python dsir-gho/evals/run_evals.py --validate-only --output dsir-gho/reports/new-casebook-schema.json
```

The dated 46-case casebook targets the original legacy catalogue and retains its
September expectations. Its injected failure contracts remain offline tests.
A live run requires explicit `--backend legacy`; it must not be relabeled as
xMart validation. Manual model-response review criteria remain separate.

## Fresh xMart checks

```sh
python dsir-gho/evals/run_xmart_live.py --output dsir-gho/reports/new-live.json
```

The runner checks source references, stable relay paging, directory discovery,
named dimensions, complete/empty retrieval, search and describe. Reports distinguish
one-row probes from complete requests, and retain upstream failures and dependent
blocked cases. Saved reports never supply runtime routes or observations.

## DSIR 0.11.0 R parity

Use a clean reference checkout at the exact commit. The runner verifies the commit
and source hashes, loads the original R/helper files and source RDA into an isolated
R process, and does not depend on an installed DSIR version. The R libraries are
`callr`, `jsonlite`, `digest`, `httr2`, `cli`, `tibble`, and `vctrs`.

```sh
python dsir-gho/evals/run_parity.py --source-dir /path/to/DSIR --rscript Rscript --offline --output-dir dsir-gho/reports/new-common-parity
python dsir-gho/evals/run_parity.py --source-dir /path/to/DSIR --rscript Rscript --output-dir dsir-gho/reports/new-live-parity
```

Offline mode compares 13 clearly synthetic typed inputs against original
normalization and cleaning: wide/long dimensions, row-specific types, bounds,
nonannual times, absent display/numeric fields, numeric formatting, source names,
non-Member labels, empty data, literal strings and duplicate multiplicity.

The live mode adds independent source retrieval for the original 15 indicators
and two named-dimension requests. It records incompatible/unknown codes and
directory failures; those are not parity passes. It also compares the same raw
inputs to diagnose transformations independently of live retrieval.

Every core comparison checks 15 ordered fields, nullable scalar types, row counts,
multiplicity, dimensions, names, display values and per-column missingness.
Numeric tolerances are `1e-10` absolute and `1e-12` relative, including retained
normalized context. Typed fixture frames avoid JSON simplification changing a
literal `"NA"` before it reaches the R cleaner. Synthetic values are never
presented as WHO observations.

`--reuse-evidence` recomputes comparisons from the selected output directory and
must be reported as saved-evidence recomparison. The runner refuses source hashes
from another snapshot. Preserve previous reports when rerunning.
