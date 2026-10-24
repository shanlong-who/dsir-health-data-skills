# Phase 2: approved GHE test architecture

Updated: 24 October 2026. The maintainer has explicitly authorized GHE
implementation and a host-supplied Python client. No deployment is authorized.

## Decision

Phase 1 passed local engineering checks. The maintainer subsequently requested
SDG instruction improvements and the start of GHE, with no end-user software
installation. GHE is now an independent local test candidate. This authorization
does not establish that GHO, SDG or GHE has passed installed-account acceptance.

Use a separate `dsir-ghe` skill and plugin within this repository. Keep
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
  successful empty query. The new adapter retains explicit outcome evidence;
  inspecting zero rows alone is insufficient.
- Current provenance records backend, table, filter, retrieval time, completeness
  and row count. It does not establish a release identifier or full methodology.
  The new skill retains available official release/method references and must
  report an unknown release when it cannot verify one. Retrieval date is not
  release date. Do not join different vintages by assumption.

The [DSIR GHE documentation](https://shanlong-who.github.io/DSIR/reference/ghe_data.html)
confirms these interface semantics. WHO's
[GHE overview and methods](https://www.who.int/data/global-health-estimates)
describe model-based estimates from multiple sources and currently link the
2000-2023 methods. The new client passed six bounded cases in its live WHO
suite and three independent live DSIR comparisons. See the
[validation report](dsir-ghe/reports/validation-20261024.md) for exact scope.

## Packaging options

| Option | Benefits | Costs and limits | Recommendation |
| --- | --- | --- | --- |
| Independent GHE skill/plugin in this repository | Separate validation and releases; clear data-source choice; existing GHO/SDG entry points remain stable | Another small instruction and packaging surface | Preferred for Phase 2 |
| Add GHE to a combined GHO/SDG plugin | One installation and shared discovery | Broader routing and regression scope; easier source confusion; changes existing entry points | Reassess only after GHE is stable |
| Common MCP or REST service | Central R execution and dependency management for clients that can call it | Hosting, access control, operations, cost and platform-specific integration | Defer until a verified runtime constraint requires it |

## Runtime choice is separate from packaging

The maintainer's default remains R. On 24 October the maintainer explicitly
approved a separate GHE exception: a Python standard-library client in the
AI host's supplied environment, with R reserved for independent validation.
No end-user interpreter, dependency or key installation is requested.

| Runtime option | Reuse and tradeoff | Decision gate |
| --- | --- | --- |
| Local R adapter calling DSIR | Highest semantic reuse; needs R, DSIR and HTTPS in the host | Used for development validation only |
| Direct portable API client | Existing script-plugin pattern without a server; duplicates some DSIR semantics and needs parity checks | Selected and explicitly approved; host Python 3.12.14 tested |
| Remote R wrapper | Reuses DSIR when client-side R is unavailable | Consider only after local execution is shown unsuitable and hosting is approved |

The host must supply Python 3.10+, permitted WHO HTTPS and file output.
If these are unavailable, report an unsupported environment; do not install
software for the end user or introduce a server silently. A plugin ZIP does
not itself create runtime permissions. The target account still needs testing.

## Implemented scope and acceptance gate

Before publication or a broader phase:

1. Accept the GHO candidate using default-legacy measles, explicit-xMart DTP3,
   age/sex filtering, an empty selection and an invalid query. Confirm backend
   disclosure and CSV/JSON evidence in the intended agent environment.
2. Accept SDG source boundaries and adaptive presentation using its
   [test guide](packaging/SDG_TESTING.md).
3. Accept GHE in the intended account using its [test guide](packaging/GHE_TESTING.md),
   including no end-user installations, exact selections, exports and failures.

The first implementation offers discovery (dimensions and causes),
coverage checks, and bounded retrieval/export. These are user tasks rather than
one plugin tool for each R function. Begin acceptance with deaths and death
rates; the eleven current provider-supported definitions have also been
compared with DSIR in the bounded sample. Defer
automatic disease aggregation, rankings across overlapping categories and new
age-standardization calculations.

Mocked failures, missingness, schema and pagination tests pass, alongside
common-input and independent live DSIR comparisons. Release uncertainty remains
explicit. These checks establish a local candidate, not general equivalence to
GHO/SDG series or readiness for a public release.

## Other DSIR functions

Useful future additions include explicit QA summaries, reproducible changes
over time and exports. Assess each against actual natural-language demand and
test it independently. Age standardization, life tables, country-derived
aggregates and cause hierarchies require validated statistical contracts and
reference inputs. They are not implemented in this candidate. A single combined
plugin, common MCP/REST service and broader platform adapters remain deferred.
