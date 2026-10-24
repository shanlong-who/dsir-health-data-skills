# GHE local test: installation and acceptance

Candidate `0.1.0-test.1` is independent of GHO and SDG. It needs the AI host's
existing Python 3.10+, HTTPS to `xmart-api-public.who.int` and writable output.
Users do not install R, Python packages or DSIR, supply keys, or download data
manually. If the host has no permitted runtime/network, report that limitation.
Do not provision software or substitute another source.

## Build and identify

Maintainers, from a clean Git checkout with R and `digest`, `jsonlite`, `zip`:

```text
Rscript packaging/build_data_test_package.R --skill dsir-ghe --output-dir dist/ghe-0.1.0-test.1
```

The builder creates `dsir-ghe-plugin-0.1.0-test.1.zip`,
`dsir-ghe-skill-0.1.0-test.1.zip`, `local-marketplace/`, `SHA256SUMS.txt`
and `build-manifest.json`. It verifies every archive member, refuses an
existing output directory and excludes tests, R, API snapshots and caches.
`BUILD.json` must show this version, the delivered source commit and
`source_dirty: false`. The CLI schema version alone does not identify a build.
The script does not install, submit, publish or deploy anything.

## Install one candidate

For a ChatGPT account with an approved plugin import/test workflow, provide
only the **plugin ZIP** through that workflow. Do not upload the repository,
R sources or validation data. Attaching a ZIP to an ordinary conversation
does not install or enable it. Account/workspace support must be verified;
this local test does not prove browser-only account execution.

For local Codex, use the generated local marketplace:

```powershell
$gheMarketplace = (Resolve-Path .\dist\ghe-0.1.0-test.1\local-marketplace).Path
codex plugin marketplace add "$gheMarketplace" --json
codex plugin add dsir-ghe@dsir-ghe-local-test --json
codex plugin list --json
```

Check `codex plugin --help` if your client differs. Verify `BUILD.json` at the
reported installed path, then restart the app and open a fresh local task.
Select **DSIR GHE Local Test** with `@`. Ensure no duplicate standalone GHE
skill is active. Ask the agent to show the skill/CLI path and build identity,
then run `doctor --live` using the host runtime. Expect `r_required: false`,
no third-party dependencies, 194 bundled countries and successful WHO access.
Never edit the installed cache manually.

Alternatively extract the standalone ZIP into an isolated project's
`.agents/skills/`, preserving the whole `dsir-ghe/` folder. Use only one method.
Ask `Use $dsir-ghe ...`. Do not replace an existing copy without reviewing it.
Disable the test plugin to stop testing. This build does not change public installs.

## Manual acceptance prompts

1. “List the available GHE measures and find the diabetes mellitus cause.”
   Verify actual codes, units and discovery scope. Do not guess codes.
2. “Give me Philippines all-cause deaths for the latest available year, one
   sentence.” Expect a compact answer retaining year, estimate status and source.
3. “Compare female and male death rates at ages 40–44 in the Philippines
   during 2022–2023, with a table, chart, findings and files.” Verify complete
   rows, sex/age labels, units, chart gaps and deterministic calculations.
4. “Give only the diabetes deaths and death-rate CSV/JSON files.”
   Expect actual downloads and minimal scope/provenance, no compulsory chart.
5. “Give the age-standardized diabetes rate.” It must explain that the selected
   GHE rate is not an age-standardized result and never relabel it.
6. “Add all-cause and diabetes deaths.” It must avoid double counting.
7. “Query all-cause deaths for the inclusive range 2099–2099.” A complete empty
   query must not be called zero mortality. An exact unknown year can instead
   fail catalogue validation; both outcomes must be explained accurately.
8. Try an invalid sex/cause code, and separately deny script network access.
   Invalid selection and request failure must remain distinct from no observations.
9. “Resolve Namibia, NA and 516.” Check exact country mapping to NAM.
   A WHO region is not automatically an available aggregate or a country average.

Read full `response.json`, `data.csv`, `raw.json` and `manifest.json`. Verify
country/year/sex/age/cause/measure, units, missing values, provider intervals,
request source and hashes. Retrieval time is not release time; an unknown
API release must stay unknown. A failed QA result must not support a final chart.

Record target app/account, package version/commit, exact prompt, returned files,
expected scope, status and any limitation. These account-level checks remain
required before a public release; successful local queries alone are insufficient.
