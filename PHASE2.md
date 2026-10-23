# Phase 2 readiness and implementation options

Assessment date: 23 October 2026. This is a recommendation, not approval to
implement GHE or deploy a service.

## Decision

Phase 1 has passed its local engineering checks. Complete the maintainer's
GHO user-facing acceptance before starting GHE implementation. A source PR is
not an installed-plugin test or a release. No GHE code is included in this change.

Recommend a separate `dsir-ghe` skill and plugin within this repository. Keep
GHO and SDG entry points stable. Reuse DSIR's GHE function semantics and tests;
share small implementation helpers only when a concrete second use justifies
them. Do not start a general provider framework or hosted service now.

## Evidence and remaining gaps

Reviewed DSIR 0.11.0 at `5a5accbedf51aa4a6b3288c82269edd7e831e831`:
`R/ghe.R`, `R/who_backend.R`, `tests/testthat/test-ghe.R`, and generated function
documentation. The current GHO and SDG skills are separate script clients in
skills-only plugin wrappers. Neither uses the older R service prototype.

- `ghe_data()` retrieves `DEX_CMS/GHE_FULL` from WHO public production xMart.
  It validates selections, checks pagination, retains units and uncertainty
  fields, and returns one row per selected measure and stratum.
- `ghe_dimensions()` and `ghe_causes()` provide discovery. Age, area and cause
  discovery uses latest-year reference slices; it does not prove coverage for
  every country/year. `ghe_coverage()` checks selected source observations.
- The code defines deaths, YLL, YLD, DALY, their rates and selected percentages;
  available measures are restricted to fields actually exposed by the API.
  These definitions are not a claim that every measure has nonmissing data.
- Existing death rates are crude for all ages or age-specific for a selected
  age group. They must not be labelled age-standardized. Rate/percentage bounds
  are not reconstructed from counts. Counts use persons or years, not thousands.
- Cause groups are not parent identifiers. Cause totals and their components,
  and overlapping age groups, cannot safely be summed together without an
  independently verified non-overlapping mapping.
- Some DSIR failures warn and return a typed empty table. A thin wrapper that
  only serializes that table would lose the distinction between failure and a
  successful empty query. The future adapter needs explicit outcome evidence;
  inspecting zero rows alone is insufficient.
- Current provenance records backend, table, filter, retrieval time, completeness
  and row count. It does not establish a release identifier or full methodology.
  A future skill must retain available official release/method references and
  report an unknown release when it cannot verify one. Retrieval date is not
  release date. Do not join different vintages by assumption.

The [DSIR GHE documentation](https://shanlong-who.github.io/DSIR/reference/ghe_data.html)
confirms these interface semantics. WHO's
[GHE overview and methods](https://www.who.int/data/global-health-estimates)
describe model-based estimates from multiple sources and currently link the
2000-2023 methods. No new live GHE retrieval was run for this readiness review.

## Packaging options

| Option | Benefits | Costs and limits | Recommendation |
| --- | --- | --- | --- |
| Independent GHE skill/plugin in this repository | Separate validation and releases; clear data-source choice; existing GHO/SDG entry points remain stable | Another small instruction and packaging surface | Preferred for Phase 2 |
| Add GHE to a combined GHO/SDG plugin | One installation and shared discovery | Broader routing and regression scope; easier source confusion; changes existing entry points | Reassess only after GHE is stable |
| Common MCP or REST service | Central R execution and dependency management for clients that can call it | Hosting, access control, operations, cost and platform-specific integration | Defer until a verified runtime constraint requires it |

## Runtime choice is separate from packaging

The maintainer's default is R. The earlier Python exception covers maintenance
of the existing GHO client; it does not authorize a new Python GHE client.

| Runtime option | Reuse and tradeoff | Decision gate |
| --- | --- | --- |
| Local R adapter calling DSIR | Highest semantic reuse and consistent R maintenance; needs R, DSIR and HTTPS in the actual host | Preferred initial R validation path; verify the intended agent can execute it before promising non-R-user distribution |
| Direct portable API client | Can follow the existing script-plugin pattern without a server; duplicates some DSIR semantics and needs independent parity checks | Requires explicit language approval and evidence about the target runtime |
| Remote R wrapper | Reuses DSIR when client-side R is unavailable | Consider only after local execution is shown unsuitable and hosting is approved |

No platform's R execution ability is assumed in this review. Non-R users can
use an R-backed tool when the runtime is supplied, but the present plugin
package itself does not provision R. The target account/runtime must be tested.

## Gate to start, and bounded first scope

Before implementation:

1. Accept the GHO candidate using default-legacy measles, explicit-xMart DTP3,
   age/sex filtering, an empty selection and an invalid query. Confirm backend
   disclosure and CSV/JSON evidence in the intended agent environment.
2. Explicitly authorize Phase 2 and choose a feasible runtime after checking
   the target host. Source publication alone does not satisfy this gate.
3. Agree the minimum query contract and statistical labels: exact cause codes,
   country/year/sex/age, supported measures, missingness, model-estimate status,
   source/release provenance, and prohibited aggregations.

The first implementation should offer discovery (dimensions and causes),
coverage checks, and bounded retrieval/export. These are user tasks rather than
one plugin tool for each R function. Begin acceptance with deaths and death
rates; add other provider-supported measures only after separate tests. Defer
automatic disease aggregation, rankings across overlapping categories and new
age-standardization calculations.

Use mocked network responses for error, missing-value, schema and pagination
regressions. Then run a few real country/year/sex/age/cause queries and compare
against independently loaded DSIR with the same source selection. Record
release uncertainty explicitly. Passing these checks would establish a GHE
candidate, not general equivalence to GHO or SDG series.
