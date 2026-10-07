# GHO evaluation and pinned-source parity

These maintainer checks are excluded from runtime packages. End users need no R.
The current reference is DSIR 0.11.0 at commit
`885464b1fade2f8b6d02dde93f9080e4b3f4f2a5`.

## Offline contracts

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
