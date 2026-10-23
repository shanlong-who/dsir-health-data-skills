# GHO backend consistency audit

Audit date: 22 October 2026. This narrow current-source audit does not complete
the historical live validation suite.

| Project | Public main audited | Default GHO backend |
| --- | --- | --- |
| DSIR 0.11.0 | `5a5accbedf51aa4a6b3288c82269edd7e831e831` | legacy, when the R session option is unset |
| GHO Skill 0.1.1 / plugin 0.1.3 | `f95a853c9715914338230ca90a1be57da4268b82` | xMart |

DSIR's explicit argument overrides its session option. The Skill's global CLI
option precedes the subcommand. No automatic fallback occurs. The Skill's
pinned R reference, `885464b1fade2f8b6d02dde93f9080e4b3f4f2a5`, predates
`5ee3a41feca301c9dd007e323235268aa7a4dc91`, which restored DSIR's legacy
default before release. Historical source hashes and validation reports remain
unchanged. "Aligned" describes that earlier xMart adapter and its contracts.

## Actual consequences

Equal 15-column outputs identify neither the backend nor semantic equivalence.
The core `source = "gho"` identifies the data family only. DSIR preserves raw
`Provider`, `who_provenance` and optional cleaned `provider`; the Skill identifies
its backend in `response.json`. CSV alone loses essential context. Users can
otherwise mistake different catalogues, dimensions or publication vintages for
a software discrepancy, or combine incompatible observations.

The existing pinned parity runner explicitly selects xMart in R. Its offline
mode compares synthetic common inputs. Neither proves equality of legacy and
xMart observations or validates the final DSIR default.

## WHS4_100 candidate review

The [recorded review](../evals/whs4_100_review.json) is **not approved**.
[WHO GHO registry 88](https://www.who.int/data/gho/indicator-metadata-registry/imr-details/88)
and [WHO indicator F8E084C](https://data.who.int/indicators/i/48D7D19/F8E084C)
identify DTP3 third-dose coverage: vaccinated surviving infants as a percentage
of the surviving-infant population in the year. The observations do not supply
the numerator and denominator counts; none were reconstructed.

Targeted live catalogues returned one legacy entry and eight xMart rows: the
main indicator in six languages, an MNCAH variant and an entry without a download
route. Both clients selected xMart `IND_ID = F8E084CWHS4_100`,
`IND_PER_CODE = WHS4_100`, from `DATA_/RELAY_WHS`, with `RATE_PER_100_N`.
The other xMart entries were not treated as equivalent.

Independent complete extractions were limited to PHL, annual 2020 and 2021.
Each returned two rows. Same-backend saved-result comparisons matched all 15 core
fields between DSIR and the Skill. Observed values were 83 and 69 percent,
respectively, in each extract; missing bounds were retained. This small sample
does not establish general cross-backend parity.

Legacy Dim1-Dim3 and their types are null in this selection; all 24 native xMart
breakdown fields are null. xMart explicitly records `PUBLISHED`; legacy's rows
do not expose the publication-state dimension listed in its catalogue. Legacy
row-update time is in July 2025, while xMart load time is in May 2026. These
timestamp concepts cannot establish identical dataset release IDs.
Publication-state mapping and release identity remain unverified. The
[comparison gate](backend-20261022/comparability_gate.json) reports `unverified`
with `values_compared = false`.

The [evidence bundle](backend-20261022/evidence.json) retains catalogue entries,
request URLs, retrieval times, provenance, native observations, source versions,
QA and error diagnostics. Its [SHA-256](backend-20261022/SHA256SUMS.txt) protects
integrity. Rereading it is saved-evidence review, not a fresh retrieval.
Reports and native observations are excluded from runtime distribution.

## Confirmed legacy paging issue

The unchanged Skill's `--backend legacy` request used `$top=5000` and returned
HTTP 400. The response explicitly stated a maximum of 1000. The same source
query succeeded with 1000 and 100. A complete Skill export using
`--backend legacy --page-size 1000` succeeded with verified count 2.
This is a paging incompatibility, not missing observations or network failure.
The documented workaround preserves the source. Runtime paging and backend
defaults were not changed; automatic legacy page-size selection remains a
separate runtime maintenance item.

## Tests and limits

| Check | Result |
| --- | --- |
| Existing Skill offline suite | 94 tests passed; process exit 0 |
| DSIR offline suite, including two new backend tests | 297 tests reported; 1150 passed assertions, zero failures/errors, 30 live tests skipped, zero warnings |
| New maintainer R comparison-tool suite | 7 tests; 58 passed assertions, zero failures/errors |
| Narrow same-backend independent DSIR/Skill retrieval | Two observations agree on each backend; legacy page-size override required |
| Verified cross-backend numerical parity | Not established; metadata gate closed |
| Historical 17-case independent xMart live suite | Not rerun or completed |
| Full DSIR package check | Installation failed at lazy loading; 1 error and 1 warning |

R 4.6.0 on this Windows host completed assertions and saved summaries, then
exited with `-1073741819` (access violation). The package-check process also
failed. Installing the unchanged public-main snapshot separately reproduced the
lazy-loading failure. A clean package-check pass is not claimed. The check used
`--no-manual --no-vignettes --as-cran` and a build without vignettes. Its incoming
warning included the unchanged released version and missing prebuilt vignette
index. Process/check failures remain separate from assertion results.

New DSIR tests preserve different synthetic backend estimates and missing bounds,
retain provider identity after binding, preserve the core schema, and prohibit
legacy-to-xMart fallback. New R comparison tests require metadata review, complete
source-specific extracts and full keys; they cover row order, strata, coverage
gaps, values/bounds, NA versus zero, tolerance, duplicate keys and disjoint data.
Synthetic values are never presented as WHO observations.

## Delivered scope

Documentation and packaged-source instructions distinguish defaults and require
provenance with CSV delivery. A maintainer-only R comparison tool and tests were
added. Runtime code, both backend defaults, historical hashes/reports, release
archives and SDG files were unchanged. No release was rebuilt or published.
Publication-state and dataset-release review, the wider live suite, the legacy
page-size runtime issue, and a clean package check remain explicit follow-up items.
