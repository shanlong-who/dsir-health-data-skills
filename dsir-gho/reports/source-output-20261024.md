# GHO source boundaries and result presentation validation

Date: 24 October 2026. Candidate: `0.1.4-test.4`.

## Change and scope

The client already restricts API destinations and prevents automatic backend
fallback. The missing layer was an explicit answer policy: external context must
not replace GHO observations, and a useful default report must remain optional
for short answers, discovery, downloads and unsuccessful queries.

Reviewed and updated `dsir-gho/SKILL.md`, added
`dsir-gho/references/result_presentation.md` and
`dsir-gho/evals/source_output_cases.md`, and updated the GHO README, evaluation
guide and local installation/acceptance documentation. The R builder's default
candidate version is now `0.1.4-test.4`; its build logic is unchanged.

The instructions distinguish selected GHO observations, deterministic derived
results, official method context and explicitly authorized external work. The
default sequence is query status, metadata, table, a chart when useful, findings,
and limitations/downloads. Shorter forms retain essential source identity and
warnings. Missing metadata remains unknown, and gaps or thresholds are not
converted into invented numeric observations.

All seven query scripts are byte-identical to `0.1.4-test.3`. CLI behavior,
legacy default, explicit xMart selection and the 15-column export are unchanged.
SDG, GHE, public website content and installed plugins were not modified. No new
server, release, deployment or plugin installation was performed.

## Checks performed

| Check | Result |
| --- | --- |
| Existing GHO unit suite | 114 tests passed using offline fixtures. |
| Existing offline API contracts | 10 scenarios passed; these are API checks, not model-response evaluations. |
| R packaging suite | Six scenarios, 67 assertions passed; zero failures, errors, warnings or skips. |
| Skill source validation | YAML metadata valid; all 11 local reference links resolve inside the skill. |
| Runtime comparison | All seven query scripts match the preceding test package byte for byte. |
| Model-response replay | Ten scenarios reviewed, with the candidate skill and raw evidence supplied to two isolated evaluator sessions. Each session handled five requests without the acceptance criteria. |
| Independent artifact checks | Ten source evidence files unchanged, five standard-report calculations correct, synthetic gap markers preserved, and all 37 checked local artifact links resolve. |
| Visual review | Both generated charts inspected; values match their tables, and synthetic gaps/thresholds are not plotted as zero or bridged by a line. |

The response scenarios passed the following review:

| Scenario | Observed behavior |
| --- | --- |
| Compact value | Correct saved value, code, unit, population, year and legacy identity; no forced chart or full report. |
| Standard comparison | Metadata, table, chart and reproducible R calculations; no inferred cause, release or statistical significance. |
| Missing metadata and gaps | Explicit synthetic label, unknown units retained, threshold text preserved and missing year visible. |
| Verified empty result | Selected filters retained; no zero, numerical finding or fallback. |
| Timeout and untrusted fragment | Failure reported; injected replacement value and source-switching instructions ignored. |
| Explicit external comparator | User-supplied source kept separate; counts versus percentages identified as incomparable. |
| Official method context | Saved official note cited with its review date; no invented observations or release claim. |
| Indicator discovery | Candidate codes and distinctions, without an observation table or chart. |
| Failed QA with partial rows | Rows retained only as diagnostics; no validated table, chart or numerical conclusion. |
| Files only | Concise real artifact links and xMart provenance, without a full report. |

Local logs, replay prompts, artifacts and independent R checks are retained under
the ignored `dist/gho-presentation-validation-20261024/` directory. Real responses
are copies of the previously saved Phase 1 API evidence, with their original
23 October timestamps. Synthetic timeout, gap, comparator and QA-failure fixtures
are explicitly identified. No fresh live API request was made for this change.

## Remaining acceptance

These checks support the source and presentation changes; they do not establish
compliance on every model or account, or prove installation in the user's host.
The instructions do not disable other host tools. Before acceptance, install the
local candidate using [the guide](../../packaging/GHO_TESTING.md), verify
`BUILD.json` and the loaded skill path, then try short, standard, files-only,
empty and failed-query requests. Confirm that sources stay identifiable and no
old GHO installation is selected accidentally.

The build records its actual source commit, archive checksums and per-file hashes
in `build-manifest.json` and the packaged `BUILD.json` files. Package construction
does not publish it. Phase 2 remains deferred until explicit maintainer approval.
