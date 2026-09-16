# DSIR GHO Health Data Skill

Use natural language to discover and retrieve WHO Global Health Observatory data.

Powered by the data-access and cleaning logic developed in the DSIR R package.

A portable skill for finding and downloading WHO Global Health Observatory data. It combines `SKILL.md` with a Python 3.10+ client that uses only the standard library and calls WHO directly over HTTPS.

There is no R dependency, DSIR runtime, MCP server, Docker image, service to host, or API key. The agent environment needs Python, permission to run the scripts, and internet access to WHO GHO. This package is separate from the earlier R service in the parent project.

## Install for local Codex

Extract the release ZIP. Keep the `dsir-gho` folder together. From PowerShell inside that folder, run:

```powershell
& .\packaging\install.ps1
```

On macOS or Linux, from the same folder:

```sh
sh packaging/install.sh
```

Both installers copy the folder to `~/.agents/skills/dsir-gho`. They stop if that destination already exists and make no runtime, network, or security-policy changes. If PowerShell execution is restricted, use your organization's approved script procedure or the manual method below; changing the policy is not part of installation.

For a manual install, create `~/.agents/skills` if needed, then copy the entire `dsir-gho` folder into it. Do not overwrite an existing copy without reviewing it. Codex detects newly installed skills; if the skill does not appear, restart Codex. This user-level discovery path is documented in [OpenAI's Build skills guide](https://learn.chatgpt.com/docs/build-skills).

Start a new task and ask:

> Use $dsir-gho to find UHC service coverage data for the Philippines and China, 2015–2023. Save the data and explain the source and any missing years.

In ChatGPT surfaces with installed skills, use the `@` skill selector. Availability and installation differ by surface; see [execution environments](references/execution_environments.md).

## Check the environment

From the extracted folder, run these examples using the available Python 3.10+ executable:

```sh
python scripts/cli.py doctor
python scripts/cli.py search "universal health coverage"
python scripts/cli.py locations Philippines China WPR WPR_WO_IDN
```

Some systems use `python3` instead of `python`; Windows may also provide `py -3`. The agent should select an executable that meets the version requirement. No third-party packages need installing.

Use the code returned by `search` to inspect an indicator:

```text
python scripts/cli.py describe CODE
python scripts/cli.py get CODE --locations PHL CHN --year-from 2015 --year-to 2023 --output-dir outputs/uhc-phl-chn
```

Replace `CODE` with a verified indicator code. Add `--dim1`, `--dim2`, or `--dim3` only after checking the indicator's observed dimension values. Query countries and regional aggregates in separate calls. Run `python scripts/cli.py get --help` for the supported arguments. The optional global `--page-size` setting goes before the subcommand. For example, after verifying the UHC code:

```sh
python scripts/cli.py --page-size 10 get UHC_INDEX_REPORTED --locations WPR --output-dir outputs/uhc-wpr-small-pages
```

## Example requests

1. “请帮我查询西太平洋区域 UHC Service Coverage Index 历年来的结果。”
2. “菲律宾2015年以来的麻疹报告病例是多少？”
3. “比较中国、日本和菲律宾历年的 UHC SCI。”
4. “WHO有没有 catastrophic health expenditure above 10% 的指标？”
5. “查询菲律宾 TB incidence。”
6. “Download the Philippines' TB incidence rate from 2015 onward, including uncertainty bounds and source details.”
7. “Which years and sex groups are available for life expectancy at birth in WHO GHO?”
8. “Compare the published WPR and WPR_WO_IDN UHC service coverage series and explain which regional variant each represents.”

The skill should clarify a measure such as ambiguous TB incidence before retrieval, and retain different regional variants and strata separately.

## Files produced by a retrieval

| File | Use |
| --- | --- |
| `data.csv` | The 15-column DSIR-compatible observation table. |
| `response.json` | Full cleaned data with query details, metadata, location coverage, row-to-source mappings, QA, and provenance. |
| `raw.json` | Original source observations for verification and reuse. |
| `manifest.json` | SHA-256 checksums of the three result files. |

The command prints a concise JSON summary and a preview of up to 12 rows. Read the saved files for the complete result. Existing output directories are refused, so select a new directory for each retrieval. The [output schema](references/output_schema.md) explains missing values, dimensions, geography, and numeric fields.

`coverage_by_location` includes the observed years and row count for each requested location, including locations with no matching data. `observation_context` aligns with the cleaned rows and provides zero-based indices for tracing each row to `raw.json`.

For Python callers, the `scripts` directory exposes `gho_client.get_gho_data()`, `indicator_search.search_indicators()`, `indicator_search.describe_indicator()`, `locations.resolve_locations()`, `clean.clean_records()`, and `qa.qa_records()`. Add that directory to the import path when calling these functions from another project. The CLI handles the complete retrieval, QA, and export sequence.

## Selecting data correctly

- Indicator search uses the source catalogue. Similar wording can describe different measures; TB incidence as a rate and as a case count are separate choices.
- UHC service coverage and UHC financial protection are different concepts.
- Country observations and source-published regional aggregates are different geographic selections. `WPR` and `WPR_WO_IDN` remain separate source variants.
- Available years and strata come from observations. A requested year range does not guarantee an observation for every year.
- Unknown units and definitions remain missing. Explicit source titles and a small set of reviewed WHO metadata summaries provide evidence where available. The summaries carry a review date and are not refreshed on every query.

See [indicator selection](references/indicator_selection_rules.md) and [location selection](references/location_rules.md) for the detailed rules.

## Tests and evaluation

From the skill folder, run the Python unit tests and offline transport/cleaning checks:

```sh
python -m unittest discover -s tests -v
python evals/run_evals.py --offline --output reports/my_offline_evals.json
```

When the environment can reach WHO directly, run the live evaluation cases:

```sh
python evals/run_evals.py --output reports/my_live_evals.json
```

Each evaluation run writes JSON and a Markdown summary. Choose a new report filename to preserve previous evidence. The [evaluation cases](evals/cases.json) include the five main questions above, catalogue discovery, geography, dimensions, empty selections, and failure conditions. The [recorded offline report](reports/eval_offline_results.md) documents the included offline run.

The default live report path is `reports/eval_results.json`. The original-DSIR comparison runner writes `reports/parity/parity_results.json` by default. Read a report's timestamp, mode, passed/failed counts, and remaining review items before citing it. Automated API and data contracts do not by themselves prove that an assistant followed the natural-language skill instructions.

Original-DSIR parity checks are maintainer validation against the reference R source. Repeating those comparisons requires that separate R reference environment; ordinary skill use and the Python tests above do not require R.

## ChatGPT distribution

This ZIP is a standalone skill package. Uploading it as an ordinary chat attachment or as Custom GPT Knowledge is not documented here as an executable skill installation method. A host must actually load the skill and run its scripts.

OpenAI documents skills-only plugins for reusable installation across supported ChatGPT surfaces. Such a wrapper could distribute this same skill without adding an MCP server. This release does not create or publish that plugin. Public plugin distribution requires a separate submission and review; workspace publishing has separate administration requirements. See [plugin packaging](https://developers.openai.com/plugins/build/plugins) and [plugin submission](https://developers.openai.com/plugins/deploy/submission).

In ChatGPT Work, code and shell network access depends on the account's available tools, workspace policy, and the Work network setting. A browsing tool being online does not prove that Python can reach WHO. See [Work network access](https://learn.chatgpt.com/docs/enterprise/chatgpt-work-overview).

## Implementation background

The interface follows the GHO workflow and 15-column cleaned schema reviewed in DSIR 0.9.0, source revision `e2ff673`. The Python client runs independently of the R package. See [design](DESIGN.md) for the implementation boundary and reproducibility approach.

WHO GHO is the data source. Review [WHO's GHO API information](https://www.who.int/data/gho/info/gho-odata-api) for source context. The package does not establish endorsement by WHO, and software packaging does not change the source's data-reuse terms.
