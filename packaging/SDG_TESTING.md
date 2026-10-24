# SDG local test: installation and acceptance

Candidate `0.1.1-test.2` adds source boundaries and adaptive presentation.
Its query scripts, tool interface and existing CSV/JSON formats are unchanged.
It remains independent of GHO and GHE and retrieves UN SDG observations.

## Build and identify

Maintainers use a clean checkout, R and `digest`, `jsonlite`, `zip`:

```text
Rscript packaging/build_data_test_package.R --skill dsir-sdg --output-dir dist/sdg-0.1.1-test.2
```

Outputs: `dsir-sdg-plugin-0.1.1-test.2.zip`,
`dsir-sdg-skill-0.1.1-test.2.zip`, `local-marketplace/`, checksums, manifest
and this guide. The canonical runtime comes from root `dsir-sdg/`, not old
embedded plugin copies. All member bytes are checked; tests, R and snapshots
are excluded. No installation, submission or publication occurs.

## Install one candidate

In a compatible ChatGPT plugin import/test workflow use only the **plugin ZIP**.
Normal chat attachments are not installations. Actual account/workspace
availability and script/network permissions must be verified.

For a local Codex test:

```powershell
$sdgMarketplace = (Resolve-Path .\dist\sdg-0.1.1-test.2\local-marketplace).Path
codex plugin marketplace add "$sdgMarketplace" --json
codex plugin add dsir-sdg@dsir-sdg-local-test --json
codex plugin list --json
```

Check the installed path's `BUILD.json`: version `0.1.1-test.2`,
`source_dirty: false` and the delivered commit. Restart and start a fresh
local task, disable the old SDG copy while testing, and select **DSIR SDG Local
Test** with `@`. Ask the agent to identify the skill/CLI path and run `doctor`.
The host supplies Python 3.10+ and HTTPS to `unstats.un.org`; no R or API key.
Do not change the shared cache by hand.

Alternatively extract the standalone ZIP's complete `dsir-sdg/` folder into
an isolated project's `.agents/skills/`. Use one installation method at a time.
Use `$dsir-sdg` in the request. Disable the test plugin to return to the prior
installation. Existing published packages are not replaced.

## Manual acceptance

1. “One sentence: latest Philippines UHC service coverage from UN SDG.”
   Keep actual year, unit (index, not percent), source and verified series.
2. “Give a Philippines UHC trend report.” Expect compact metadata, a useful
   table/chart, deterministic findings and limitations; avoid empty sections.
3. “Files only.” Provide actual `observations.csv`, `response.json`,
   `raw.json` and `manifest.json` with minimal context.
4. “Find catastrophic health spending over 10%.” Check exact series and
   definitions. Do not substitute the current 40% discretionary-budget series.
5. “Give the WHO Western Pacific regional UHC index.” A country list or
   average is not a verified regional aggregate.
6. Deny script network access. Request failure must not mean zero or no data,
   and another website must not silently replace UN observations.
7. Supply a comparator with a different unit/threshold. Explain comparability
   before calculating differences. Keep explicit external comparisons labelled.
8. Ask about an official methodological explanation. Separate supplementary
   context from retrieved UN observations; WHO custodian text does not make
   the retrieval a GHO query.

Read the full result, not just the terminal preview. Retain dimensions, row
units, actual coverage and QA evidence. `dsir_clean.csv` is the historical
15-column interoperability export; `observations.csv` retains more context.
There is no GHO-style `provenance.complete` flag to invent for SDG.

Record app/account, package identity, prompt, output files and any limitation.
The target-account natural-language checks are still needed before publication.
