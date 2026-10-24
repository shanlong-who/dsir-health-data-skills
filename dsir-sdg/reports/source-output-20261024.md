# SDG source boundaries and adaptive output validation

Date: 24 October 2026. Local candidate: `0.1.1-test.1`.

## Change and cause

The query client already retains UN series, dimensions, pagination evidence,
QA and exports. Its instructions needed a clearer boundary between UN
observations, deterministic calculations and supplementary context, and a
default result layout that can simplify to fit the task.

Changed `SKILL.md` and added `references/result_presentation.md` and response
acceptance cases. No query scripts, CLI parameters or data export schemas were
changed. A WHO custodian/source attribution in UN rows does not relabel a
UN API retrieval as GHO. External values cannot replace an absent/failed query.

## Evidence

- All 69 existing unit tests passed using the host-bundled Python 3.12.14.
- Ten independent response scenarios were reviewed: compact answer, full
  report/chart, files only, changed financial-protection threshold/denominator,
  absent regional aggregate, timeout with untrusted instructions, incompatible
  comparator, source attribution, censored/missing years, and failed QA.
- Real API snapshots retained their **16 September 2026** timestamps.
  Synthetic timeout, comparator, gaps, and failed QA inputs were labelled.
  No fresh UN API request was made for these instruction-only changes.
- All eight original exported files from the two replay inputs matched their
  SHA-256 manifests. R computed all reported differences. Both generated charts
  were visually checked and retained gaps; UHC values remained index points.
- Replay surfaced a denominator discrepancy between 3.8.2 series metadata and
  its footnote. The response exposed it and did not substitute that series for
  the requested 10%-of-income measure.

Local evidence: `dist/sdg-ghe-validation-20261024/replay-sdg/` and
`sdg-unit-tests-bundled.log`. These are excluded from runtime packages.
Packaging validation is shared with the GHE candidate and recorded in its
[report](../../dsir-ghe/reports/validation-20261024.md).

## Remaining acceptance

Install the identified candidate in the intended account and run
[SDG acceptance](../../packaging/SDG_TESTING.md). Confirm the executed path,
package commit, exact source/series/units, adaptive output and actual downloads.
Saved-output evaluation does not verify every model or account.
No online plugin configuration, release, website or production service changed.
