# DSIR Health Data Skills

**Author and maintainer: [Shanlong Ding](https://github.com/shanlong-who)**

The 7 October 2026 maintenance candidate aligns GHO with DSIR 0.11.0's
public xMart backend: GHO plugin 0.1.3 and skill 0.1.1. Offline tests and 13
common-input R comparisons passed; independent live retrieval remains unverified.
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
| [plugins](plugins/) | Exact extracted contents of the GHO candidate and unchanged SDG plugin ZIPs |
| [packaging](packaging/) | Shared GHO plugin builder and branding asset |
| [PUBLISHING.md](PUBLISHING.md) | Build steps, release provenance and validation scope |
| [releases/v2026.10.07](releases/v2026.10.07/) | Candidate ZIP checksums and the original build manifest |

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
