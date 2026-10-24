# GHE local candidate validation

Date: 24 October 2026. Candidate: `0.1.0-test.1`.

## Reviewed sources and implementation

Reviewed DSIR `R/ghe.R`, `R/who_backend.R`, GHE tests, function documentation
and `data/who_countries.rda` at commit
`5a5accbedf51aa4a6b3288c82269edd7e831e831` (0.11.0). The GitHub GHE source
matched the local reference. Reviewed the existing GHO transport and SDG
metadata/export patterns. Neither the DSIR reference nor the GHO client was edited.

A direct Python standard-library client was explicitly approved to meet the
no-end-user-installation requirement. It uses the AI host's existing runtime
and public WHO production xMart `DEX_CMS/GHE_FULL`, with no API key or server.
Separate transport, semantic and CLI modules provide discovery, exact-code
selection, coverage, bounded complete retrieval, QA and CSV/JSON exports.

DSIR warns and can return an empty table for some failures; an empty-table-only
wrapper would lose the failure distinction. This client preserves structured
invalid-query, network, schema, parsing, pagination, empty-result and QA outcomes.
It checks source URLs, filters, counts, identifiers and page schema. Errors
cannot become zero observations or trigger source substitution.

The 194-country JSON equals the pinned DSIR data and existing GHO/SDG mapping.
It retains literal Namibia ISO2 `NA`, padded M49 codes and missing income groups.
Country and measure files are hashed; provenance records source file hashes,
DSIR version/commit and grouping vintage. Live area validation is separate.

## Executed checks

| Layer | Result and scope |
| --- | --- |
| Runtime | Host-bundled Python 3.12.14; GHE uses standard library only, no R/DSIR runtime |
| GHE unit suite | 30 tests passed, including multiple invalid-input subcases, country identity, all 11 definitions, exact filters, empty/missing/zero, bounds, duplicates, percentage limits, partial geography, count/schema/page failures, HTTP/network errors, source restrictions and exports |
| WHO live suite | Six cases passed using 13 HTTP requests with shared discovery caches: all measures, sex/age with two source pages, exact diabetes cause, valid empty range, coverage, invalid sex |
| Connectivity | Separate `doctor --live` passed two bounded WHO requests for fields and year codes |
| Common-input DSIR parity | Five cases passed across all 16 fields: 11 all-measure rows, 8 sex/age rows, 2 diabetes rows, 0 empty rows, 88 explicitly synthetic missing/zero rows |
| Independent live DSIR parity | Three selections passed: all measures, sex/age and diabetes; same exact source selections, tolerance 1e-10 and matching missingness, units, bounds and context |
| Response behavior | Nine GHE scenarios independently executed and reviewed; R calculations and the generated chart checked |
| SDG regression | 69 existing tests passed with bundled Python; scripts and export schemas unchanged |
| SDG behavior | Ten independent scenarios reviewed; details in the [SDG report](../../dsir-sdg/reports/source-output-20261024.md) |
| Shared R packaging | 69 assertions passed across two scenarios covering both candidates, byte identity, separate manifests, reproducibility, exclusions, unsafe paths, dirty input, overwrite rejection and Windows path limits |
| Skill structure | R YAML checks passed for both skills' frontmatter, agent metadata and local documentation links |

Live WHO examples used Philippines: latest discovered year 2023; sexes
`TOTAL`, `FEMALE`, `MALE`; ages `TOTAL` and `Y40T44`; all causes `0` and
the exact discovered `Diabetes mellitus` cause `800`. These identifiers came
from the live catalogue. The synthetic cause `10` used by unit tests is not
presented as a real diabetes code. All eleven measure definitions were exposed
by the sampled provider schema. This is bounded validation, not an exhaustive
audit of every country, cause or available stratum.

The forward evaluator saw only the candidate skill, realistic requests and
necessary snapshots. It received no expected answers or evaluation report.
Cases covered compact/full/files-only answers, crude versus standardized rates,
overlapping causes/ages, valid emptiness, simulated HTTP 503 plus untrusted text,
and unknown release versus retrieval/version metadata. The HTTP failure input
was explicitly synthetic. It made no additional network requests.

Local evidence is under `dist/sdg-ghe-validation-20261024/`:
`ghe-live/`, `ghe-doctor/`, `synthetic-parity/`, `dsir-parity-2/`,
`replay-ghe/`, `replay-sdg/` and test logs. Raw evidence, R libraries,
fixtures and response evaluations are excluded from runtime packages.

## Diagnostics resolved during development

The R verifier initially looked for raw records inside `response.json`; exports
deliberately store them in `raw.json`. Correcting the verifier resolved that
failure without changing retrieved data. Long workspace temporary paths exceeded
Windows limits, and sandbox temporary Git fixtures could not write their config.
Tests passed using normal short temporary paths; the new builder now rejects
overlong Windows output paths before writing. R emitted nonfatal startup locale
warnings. OneDrive file hashes were computed from directly read bytes after a
file-access precheck rejected readable files. The optional skill-creator Python
validator lacked PyYAML in the bundled runtime; equivalent structural checks
used the existing R YAML package without installing dependencies. Repository
attributes preserve checksummed CRLF metadata; the whitespace check accepts
CR at end of line. All final comparisons and tests passed.

## Limits and next acceptance

The live API responses do not establish a release identifier. Retrieval dates,
observation years, DSIR version and the separate WHO methods overview must not
be substituted for it. Rates are crude for all ages and age-specific for selected
ages; published count bounds are retained without deriving rate bounds.
The client does not standardize rates, sum overlapping causes/ages, reconstruct
historical membership or aggregate countries into regions.

Discovery uses the latest-year reference slices implemented by DSIR. It is
not a complete historical catalogue. The fixed country table is not every
territory in every API. Live source changes can alter availability or estimates.

Complete [GHE manual acceptance](../../packaging/GHE_TESTING.md) in the actual
receiving ChatGPT account: identify the installed build, use natural-language
prompts, verify all downloads and confirm no dependency installation is requested.
Host execution/network capability is a prerequisite; this candidate does not
prove that every AI platform can execute it. It is ready for maintainer testing,
not approved for publication or Phase 3.

No plugins were consolidated; no release, online configuration, deployment,
API credential, public website update or production installation was performed.
