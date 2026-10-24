# DSIR Health Data Skills

**Author and maintainer: [Shanlong Ding](https://github.com/shanlong-who)**

**New local candidates (24 October 2026):** SDG `0.1.1-test.1` adds source
boundaries and adaptive results while keeping its query runtime unchanged.
GHE `0.1.0-test.1` adds a separate WHO GHE skill with bundled country metadata,
exact-code discovery, retrieval and CSV/JSON export. The host supplies Python;
end users do not install R, DSIR or additional packages. No hosted service,
plugin consolidation or public release is included.
See the [SDG test guide](packaging/SDG_TESTING.md), [GHE test guide](packaging/GHE_TESTING.md)
and [GHE validation](dsir-ghe/reports/validation-20261024.md).
These candidates still need acceptance in the intended ChatGPT account.
The [Phase 2 decision](PHASE2.md) records the approved scope and runtime.

**Local Phase 1 test candidate (24 October 2026):** GHO now defaults to legacy,
supports explicit xMart, and never automatically switches sources. Paging,
dimension validation and provenance have been repaired. See the
[Phase 1 report](dsir-gho/reports/phase1-20261023.md). Published downloads below
and installed plugins have not been updated; no new release was created.
PR #1 is merged. Build the repaired `0.1.4-test.4` candidate from current source
using the R-based [local test package guide](packaging/GHO_TESTING.md). The builder also
prepares an unregistered local marketplace for desktop acceptance; it does not
publish or install anything.

The GHO instructions now separate source observations, derived calculations and
supplementary context, with a default report that adapts to the task. See
[result presentation](dsir-gho/references/result_presentation.md) and
[response acceptance cases](dsir-gho/evals/source_output_cases.md). The
[24 October validation report](dsir-gho/reports/source-output-20261024.md)
records the regression tests, response replays and remaining manual checks.

The historical 7 October 2026 maintenance candidate follows an earlier DSIR
0.11.0 development snapshot's xMart backend: GHO plugin 0.1.3 and skill 0.1.1.
Its offline tests and 13 common-input R comparisons passed; its full independent
live suite remains unverified. The newer Phase 1 source has separate validation.
The listing and privacy update is available as the [v2026.10.07.1 pre-release](https://github.com/shanlong-who/dsir-health-data-skills/releases/tag/v2026.10.07.1).
See [release notes](RELEASE_NOTES.md), [validation](dsir-gho/reports/VALIDATION.md)
and [publishing](PUBLISHING.md) before using it.

Use natural language to discover and retrieve public health and development data.
Powered by the data-access and cleaning logic developed in the
[DSIR R package](https://github.com/shanlong-who/DSIR). Users do not need R or DSIR.

| Plugin | Data source | Plugin version | Download |
| --- | --- | --- | --- |
| DSIR GHO Health Data Skill | WHO Global Health Observatory | 0.1.3 (pre-release) | [GHO plugin ZIP](https://github.com/shanlong-who/dsir-health-data-skills/releases/download/v2026.10.07.1/dsir-gho-plugin-0.1.3.zip) |
| DSIR SDG Data Skill | UN SDG Global Database | 0.1.0 | [SDG plugin ZIP](https://github.com/shanlong-who/dsir-health-data-skills/releases/download/v2026.09.16/dsir-sdg-plugin-0.1.0.zip) |

[Maintenance candidate downloads and checksums](https://github.com/shanlong-who/dsir-health-data-skills/releases/tag/v2026.10.07)

[GHO plugin website](https://shanlong-who.github.io/dsir-health-data-skills/) ·
[Privacy policy](https://shanlong-who.github.io/dsir-health-data-skills/privacy.html).
The 0.1.3 plugin changes listing metadata only; the 0.1.1 skill runtime is unchanged.

## GHO backend selection and historical downloads

The published October candidate defaults to **WHO xMart**. This Phase 1
source and released DSIR 0.11.0 default to the **legacy GHO OData API** (DSIR's
session option can override that). Their common output
schema does not guarantee the same catalogue, definitions, dimensions, revisions
or values. For same-source comparisons, explicitly select the same backend in
both tools. See the [source comparison guide](dsir-gho/references/backend_comparison.md).

The Skill's pinned reference is the earlier DSIR commit
`885464b1fade2f8b6d02dde93f9080e4b3f4f2a5`, before
[`5ee3a41`](https://github.com/shanlong-who/DSIR/commit/5ee3a41feca301c9dd007e323235268aa7a4dc91)
restored DSIR's legacy default. "Aligned" refers to that snapshot's xMart
adapter and cleaning contracts. It does not mean alignment with the final
0.11.0 default or establish cross-backend data parity. Historical validation
reports and published release archives retain their original scope and contents.

The [22 October audit](dsir-gho/reports/backend-audit-20261022.md) records the
current code review, narrow independent live samples, offline regression results,
legacy paging limit, unresolved comparability checks and local R limitations.

## What the skills do

The agent searches the official indicator catalogue, confirms the measure and
location, retrieves all result pages, cleans the observations, checks the result,
and explains the source, units, years and limitations. It exports CSV and JSON.
It must clarify material ambiguity and distinguish API failures from empty data.
No estimates, regional averages or missing values are invented.

Example requests:

- Show historical UHC service coverage for the WHO Western Pacific Region.
- Get measles reported cases in the Philippines since 2015 from WHO GHO.
- Compare UHC service coverage in China, Japan and the Philippines.
- Find WHO indicators for catastrophic health expenditure above 10%.
- Get Philippine TB incidence since 2015 from UN SDG.
- Find the current financial protection measure under SDG 3.8.2.

GHO and UN SDG are distinct sources. Their releases, methods, geographic groups
and available years can differ. The skills preserve that distinction.
The new GHE candidate is a third distinct source for mortality and burden
estimates, with its own statistical interpretation and validation.

## Install and use

### Plugin package

Download the relevant **plugin ZIP** above. Use it in a compatible host's plugin
import or publishing workflow. The package contains its manifest, icons and
runtime skill. GitHub hosting does not register it in an OpenAI plugin directory.
Account features and workspace policy determine whether plugin import is available.
Attaching the ZIP to an ordinary ChatGPT conversation is not an installation step.

### Standalone skill for local Codex

The maintenance candidate also provides `dsir-gho-0.1.1.zip` and the unchanged
`dsir-sdg-0.1.0.zip`.
Extract the chosen ZIP, then copy the whole `dsir-gho` or `dsir-sdg` folder into
`~/.agents/skills/`. On Windows, this is the `.agents\skills` folder under your
user home. File Explorer is sufficient; no PowerShell command is required.
Preserve the folder structure and review any existing copy before replacing it.
Start a new task, or restart the host if it does not detect the skill.

Ask, for example:

> Use $dsir-gho to get measles reported cases in the Philippines since 2015.

> Use $dsir-sdg to compare UHC service coverage in China, Japan and the Philippines.

### Execution requirements

The host must load skills, run the bundled scripts using Python 3.10 or later,
write output files, and allow script HTTPS access to the selected public API.
Only the Python standard library is needed. There is no R dependency, API key,
MCP server or hosted service. Installation does not grant network permissions.
Ordinary browsing access does not guarantee that the script runtime can use HTTPS.

## Source and validation

| Path | Contents |
| --- | --- |
| [dsir-gho](dsir-gho/) | GHO runtime, design, tests, evaluation cases and validation reports |
| [dsir-sdg](dsir-sdg/) | SDG runtime, design, tests, evaluation cases and validation reports |
| [plugins](plugins/) | Current GHO plugin source and unchanged SDG plugin; GHO source differs from historical ZIPs |
| [packaging](packaging/) | Shared GHO plugin builder and branding asset |
| [PUBLISHING.md](PUBLISHING.md) | Build steps, release provenance and validation scope |
| [releases/v2026.10.07](releases/v2026.10.07/) | Candidate ZIP checksums and the original build manifest |
| [PHASE2.md](PHASE2.md) | GHE readiness and option comparison; implementation is not started |

The repository contains the full source. GitHub also supplies source ZIP and
tar archives on the release page; these are for development, not plugin import.

Historical legacy/SDG validation, conducted before the September publication:

| Check | GHO | SDG |
| --- | --- | --- |
| Offline unit tests | 54 passed | 69 passed |
| Evaluation contracts | 46 | 40 |
| Independent live R parity comparisons | 15 | 13 |
| Common-input parity comparisons | 16 | 22 |
| Independent natural-language rehearsals | 5 | 5 |

Read the [GHO validation report](dsir-gho/reports/VALIDATION.md) and
[SDG validation report](dsir-sdg/reports/VALIDATION.md) for dates, modes,
coverage and limitations. These are recorded results, not a guarantee of API
uptime or a general model accuracy score. Ordinary use does not require R;
repeating the original-R parity checks does.

## Author, license and data

Created and maintained by **Shanlong Ding**. Software is licensed under
[MIT](LICENSE). Original attribution notices are preserved in the component
licenses. WHO and UN retain their respective data and metadata terms; the
software license does not relicense their data. This is a personal DSIR project,
not an official WHO or UN service. See [AUTHORS.md](AUTHORS.md).
