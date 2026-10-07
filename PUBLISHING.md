# Publishing and reproducibility

## Listing-only update: GHO plugin 0.1.3

Pre-release `v2026.10.07.1` updates the subtitle (30 characters), category
(`Data & Analytics`), purpose and limitations, and website/privacy/support URLs.
GitHub Pages serves static files from `main:/docs`; no visitor scripts or forms
are included. The policy describes runtime exports, direct WHO requests and
independent host, WHO and GitHub data handling.

Rebuild with `python packaging/build_gho_plugin.py` using the original
`dsir-gho-0.1.1.zip` (SHA-256
`cdfcb748d581daf2afe93d32384f42aa2f424f77d7e63f7e6dd3316dc8c1fd31`).
Run `Rscript packaging/validate_gho_listing.R` to verify both manifests, final
listing limits, exact ZIP contents and unchanged runtime. The script writes the
new package's `SHA256SUMS.txt` and `release_manifest.json` under `dist/listing-0.1.3`.
The historical maintenance finalizer below belongs to the original 0.1.2 release.
Do not use it to overwrite historical metadata or assets. This update retains
the existing live-validation gate and leaves SDG unchanged.

## Release identity and validation status

- Owner and author: Shanlong Ding (`shanlong-who`).
- Maintenance candidate: `v2026.10.07`; published on GitHub as a pre-release.
- GHO plugin: 0.1.2; underlying skill: 0.1.1.
- GHO reference: DSIR 0.11.0, commit `885464b1fade2f8b6d02dde93f9080e4b3f4f2a5`.
- SDG plugin and skill: 0.1.0, unchanged; its reference remains DSIR 0.9.0.
- Previous public collection: `v2026.09.16`, source commit `8ea1a2561760dc901a3780fea8f78c02aed28881`.

The GHO default backend is WHO public production xMart. Legacy is an explicit
compatibility path. GHE remains outside the GHO plugin. Runtime packages require
only Python 3.10+ and its standard library; R is a maintainer parity dependency.

The maintenance candidate passes offline checks and pinned common-input source
parity. Fresh live requests on 7 October 2026 reached three one-row JSON probes,
but complete count/order requests and the indicator directory returned HTTP 302
to `http://www.who.int/sorry/`. Both the portable runtime and the unmodified
DSIR reference failed independent directory retrieval. The 17 independent live
parity cases remain unverified. The candidate must not be promoted as a
live-validated release until those checks pass. See
[validation](dsir-gho/reports/VALIDATION.md) and [release notes](RELEASE_NOTES.md).

The pre-release hosts the reviewed candidate ZIPs and their checksums without
claiming successful complete live retrieval. Repository `main` contains the
migration and audit evidence. The prior stable release is retained. The files in
`releases/v2026.10.07/` record the original build state, including `published = false`
at build time; the hosted `release_manifest.json` adds publication metadata.

## Run offline tests

From the repository root:

```sh
python -m unittest discover -s dsir-gho/tests -v
python -m unittest discover -s dsir-sdg/tests -v
python dsir-gho/evals/run_evals.py --offline --output dsir-gho/reports/new-offline.json
```

The original dated casebook covers legacy. New xMart tests explicitly cover
directory routes, wide and long dimensions, native filters, read-only POST,
counted and grouped pagination, integrity failures and lossless exports.

## Fresh live checks and pinned R parity

Use a clean checkout of the exact DSIR commit above. The parity runner refuses
another revision or modified reference files. It loads the original GHO source
files and bundled country RDA in an isolated R process; it does not use or replace
an installed DSIR package. Required R libraries are `callr`, `jsonlite`,
`digest`, `httr2`, `cli`, `tibble`, and `vctrs`.

```sh
python dsir-gho/evals/run_xmart_live.py --output dsir-gho/reports/new-live.json
python dsir-gho/evals/run_parity.py --source-dir /path/to/pinned/DSIR --rscript Rscript --offline --output-dir dsir-gho/reports/new-parity-offline
python dsir-gho/evals/run_parity.py --source-dir /path/to/pinned/DSIR --rscript Rscript --output-dir dsir-gho/reports/new-parity-live
```

Use an explicit Rscript path if it is not on PATH. Reports distinguish fresh live
runs, synthetic typed common inputs, and saved-evidence recomparison. Numeric
tolerances remain absolute `1e-10` and relative `1e-12`. No observations,
unknown routes or missing source fields are changed to make an audit pass.
One-row probes never count as complete retrievals. Failed redirects do not
trigger legacy fallback.

The country snapshot was revalidated against all 194 rows of the pinned source.
Its RDA and exported JSON are unchanged. GHO reference hashes are recorded in
`dsir-gho/references/metadata/dsir_reference.json`. Historical September reports
remain historical; they do not establish xMart behavior.

## Rebuild packages

```sh
python dsir-gho/packaging/build_release.py --output-dir dist
python packaging/build_gho_plugin.py
Rscript packaging/finalize_gho_maintenance.R
```

The finalizer checks local package hashes and records the live-validation gate.
It produces `SHA256SUMS.txt` and `release_manifest.json`. The unchanged SDG
runtime ZIPs may be copied from the previous release; their hashes must match
that release. Do not rebuild or silently replace previously published assets.

The GHO standalone and plugin runtime ZIPs exclude tests, R parity scripts and
recorded observations. The separate GHO source archive retains maintainer
evidence. Extracted plugin contents under `plugins/dsir-gho/` must match the
new standalone runtime. ZIP timestamps are fixed for reproducibility.

Before a stable release, rerun failed/blocked live checks and independent parity,
validate the extracted package, review the diff, and verify uploaded asset
sizes and SHA-256 hashes through the GitHub API. GitHub publication is separate
from a plugin directory submission or review.
