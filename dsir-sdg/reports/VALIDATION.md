# DSIR SDG 0.1.0 validation

Validation date: 2026-09-16. Result: ready for local skill/plugin distribution
testing. No public submission, review approval or installation into a receiving
ChatGPT account was performed.

## Evidence

| Check | Result | Evidence |
|---|---|---|
| Offline behavior tests | 69 passed, 0 failed | unit_tests.txt |
| Real-question casebook | 40 questions; 35 substantive health-data questions | ../evals/cases.json |
| Live catalogue contracts | 40 passed, 0 failed | eval_catalogue_results.json |
| Full live contracts | 40 passed, 0 failed | eval_results.json |
| Independent original-R retrieval parity | 13 indicators, 632 observations; all passed | parity/parity_results.md |
| Shared-input cleaner parity | 22 checks passed: 13 live snapshots + 9 synthetic inputs | parity/parity_results.json |
| DSIR country mapping | All 194 reference Member States matched | parity/parity_results.json |
| Independent natural-language rehearsal | 5 scenarios completed, with data/clarification/no-coverage outcomes | forward_test.md |
| Skill/plugin manifest validators | Both passed | package_validation.json |
| Relocated packaged runtime | Philippine TB, 2015-2024: 10 rows, QA pass, no R | package_validation.json |

Full contract mode includes 27 data scenarios, six searches, one metadata
scenario, three negative requests, two location scenarios and one membership
review scenario. These use explicit expected arguments and are not 40 independent
language-model decisions. The membership scenario leaves interpretation for
manual review. The five forward tests separately exercise natural-language
reasoning; no general accuracy percentage is inferred from this small sample.

## Principal end-to-end outcomes

1. Historical UHC in China, Japan and the Philippines: 72 observations,
   2000-2023, current 2025-methodology series; QA pass.
2. Philippine TB incidence since 2015: 10 observations, 2015-2024; QA pass.
3. WHO Western Pacific UHC from UN SDG: catalogue location resolves, but no
   matching observations. A global probe confirms the indicator has data.
   The response correctly reports filtered-scope absence and invents no average.
4. Catastrophic health expenditure above 10%: the current 40%-of-discretionary-
   budget series is identified as a different measure; clarification is required.
5. General child mortality: age group, rates versus counts, and years require
   clarification before producing a table.

The UHC retrieval test deliberately used seven rows per page and completed
11 pages. Exact total-count checks prevent first-page-only answers. Export
hashes, CSV/JSON row counts and context alignment were independently checked.

## Problems found and corrected

- Windows console encoding initially failed on a Unicode UN label. CLI stdout
  and stderr now use UTF-8; a cp1252 subprocess regression test and plain-Python
  live retest passed.
- The short phrase "child mortality" initially failed discovery. A small
  reviewed term alias now returns verified candidates; it does not automatically
  resolve age or rate/count ambiguity.
- An initial WPR eval expected nonempty UHC observations based solely on the
  area catalogue. Live evidence disproved that expectation. The case now checks
  an explicit no-coverage outcome, with the initial failure retained in history.
- An initial sex-filter eval used SDMX F/M aliases instead of JSON API
  FEMALE/MALE codes. Only the test arguments were corrected. Instructions now
  explain the distinction; source values were not changed.
- TB metadata advertised dimensions not populated in Philippine observations.
  Instructions now require inspection of actual row dimensions before optional
  filters, while preserving explicit user population requirements.

## Reference and limits

Parity uses unmodified DSIR 0.9.0 source at commit
`e2ff6735d174769b55f9a3e55f9f36c75ce9f397` under R 4.6.0. The installed DSIR 0.8.0
was not silently used as the reference: current functions and country metadata
were loaded directly from source. All 15 fields, row order/multiplicity, scalar
types, numeric values/bounds and missingness matched. Independent live R checks
also matched raw dimensions and attributes. No differences were forced to pass.

Live results describe the checked UN release, not a permanent promise about
coverage or values. Future revisions may require reviewing eval expectations.
The runtime requires script execution and permitted HTTPS to UN; these tests
do not establish availability in every user's ChatGPT environment. Statistical
model validity and public listing approval are outside the checks performed.
