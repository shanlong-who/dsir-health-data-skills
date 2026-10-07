# GHO maintenance candidate validation

Validation date: 7 October 2026. Candidate plugin 0.1.2; skill 0.1.1.
Runtime: Python 3.14.6 on Windows. Reference: R 4.6.0 and the exact unmodified
DSIR 0.11.0 commit `885464b1fade2f8b6d02dde93f9080e4b3f4f2a5`.

| Check | Result | Evidence |
| --- | --- | --- |
| GHO offline unit tests | 94 passed | [Output](xmart-20261007/unit_tests.txt) |
| Unchanged SDG offline unit tests | 69 passed | [Output](xmart-20261007/sdg_unit_tests.txt) |
| Explicit legacy injected contracts | 10 passed | [Report](xmart-20261007/legacy_offline_final.json) |
| Typed common-input R source parity | 13 passed | [Report](xmart-20261007/parity-offline-final/parity_results.md) |
| Country metadata against pinned RDA | All 194 rows match; source/export hashes unchanged | [Provenance](../references/metadata/provenance.json) |
| Fresh one-row JSON probes | 3 passed; each marked incomplete | [Live report](xmart-20261007/live_checks_final.json) |
| Complete live requests | 4 failed; 6 dependent checks blocked | [Live report](xmart-20261007/live_checks_final.json) |
| Independent fresh R/client parity | 0 passed; 17 unverified; common-input checks still pass | [Report](xmart-20261007/parity-live/parity_results.md) |
| Extracted runtime without R | Static/import/help passed with empty PATH; live directory check failed with HTTP 302 | [Package report](xmart-20261007/package_validation.json) |

The skill-creator `quick_validate.py` was attempted but could not run because its
maintainer-only PyYAML dependency is absent. The package validator separately
checks the skill frontmatter, local links, invocation configuration, archive
integrity and executable imports/help. No new runtime dependency was introduced.

## What passed

Offline tests exercise live-directory routing using clearly synthetic envelopes,
wide and long normalization, native named dimensions, canonical positional sex/age
codes, dimensions beyond the core positions, preserved literal strings, exact CSV
column order, stable pagination, read-only long-query POST, incomplete-response
failures, geography mappings, provenance and native raw exports.

The R audit loads seven original GHO/helper source files plus the source country
RDA. It validates their SHA-256 hashes and exact commit, and does not use the older
installed DSIR package. Common inputs test both normalization and cleaning, not
only the final column names. Normalized context is compared with the same numeric
tolerance as the core table: absolute `1e-10`, relative `1e-12`.

The initial common-input run detected differences in R numeric display formatting
and in the test harness's automatic simplification of literal `"NA"`. Formatting
was aligned to R; fixtures now enter R as typed scalar columns without changing
their values. JSON numeric serialization rounding uses the documented tolerance.
Earlier failed reports are retained as diagnostic history.

## What remains unverified

The production endpoint returned HTTP 302 to `http://www.who.int/sorry/` for
the directory and complete count/order requests. The client rejects the cross-site
redirect and records a failure. The pinned R implementation followed it and
reported an HTML/JSON parsing failure. Neither result establishes empty data.

Single-row `REF_GEO`, `REF_DISAGGREGATIONS` and `RELAY_GHO` probes returned
JSON, but those incomplete probes do not establish directory or full retrieval
availability. No cached route, fabricated observation or legacy fallback was used.
The independent parity cases remain unverified, and the candidate is not ready
for a live-validated public release.

September 2026 reports elsewhere in this directory document the previous legacy
release. They are retained without relabeling their dates or outcomes and do not
validate the new xMart path. No new language-model rehearsal was conducted.
Runtime ZIPs exclude reports, tests and all R files.

Local file paths in the new audit specifications are replaced by portable tokens.
Source values, comparison results and source hashes are unchanged by this metadata
sanitization; rerunning the commands creates fresh machine-specific specifications.
