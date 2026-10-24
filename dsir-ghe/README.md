# DSIR GHE Health Estimates

A separate local test skill for WHO Global Health Estimates. End users enable
the plugin and ask questions. The AI host supplies Python 3.10+, permitted
HTTPS and file output; no end-user R, DSIR, pip packages, API key or DSIR server
is required. A host without these capabilities cannot run this candidate.
See [execution environments](references/execution_environments.md).

## Scope

- Discover available measures, areas, years, sex, age and causes.
- Resolve countries against the bundled 194-member DSIR `who_countries`
  snapshot and live GHE availability. Preserve ISO2 `NA` and padded M49 codes.
- Retrieve exact selections from WHO public xMart `DEX_CMS/GHE_FULL`.
- Export the 16-column DSIR GHE schema, selected raw observations, row context,
  request evidence, source metadata and checksums.
- Keep missing estimates, valid empty queries, invalid selections, failed
  requests, incomplete pages and failed QA distinct.

Supported measures follow verified DSIR definitions and actual API fields:
deaths, YLL, YLD, DALY, their rates and available percentages. Counts retain
provider bounds. Rates are all-age crude or age-specific; no age standardization,
automatic regional aggregation or cause-total summation is performed.
Release identifiers remain unknown when the response does not establish them.
These are WHO estimates from multiple inputs, not raw registered-death counts.

The mapping and definitions are exported from DSIR 0.11.0 commit
`5a5accbedf51aa4a6b3288c82269edd7e831e831`. Their file checksums and snapshot
scope are in [metadata provenance](references/metadata/provenance.json).
Region/income groupings are dated DSIR attributes; they are not present-day
coverage claims or definitions for every API territory.

## Test and build

Use the host-provided interpreter for the runtime tests:

```text
python -m unittest discover -s dsir-ghe/tests -v
python dsir-ghe/scripts/cli.py doctor
```

Maintainers build from a clean checkout using R:

```text
Rscript packaging/build_data_test_package.R --skill dsir-ghe --output-dir dist/ghe-0.1.0-test.1
```

See [installation and acceptance](../packaging/GHE_TESTING.md) and
[validation](reports/validation-20261024.md). R is a development dependency
for independent comparisons with DSIR, never a plugin runtime dependency.
This source has no publication or deployment step.
