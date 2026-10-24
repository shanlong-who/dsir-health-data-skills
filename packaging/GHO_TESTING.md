# GHO local test package: installation and acceptance

This candidate contains the GHO Phase 1 repair merged in PR #1. It defaults to
legacy, allows explicit xMart, and never switches or combines sources automatically.
The build creates files only. It does not install a plugin, register a marketplace,
publish a release, change a public listing, or deploy a website. GHE is excluded.

The 24 October candidate also makes source boundaries and default presentation
explicit. It separates GHO observations from derived results and supplementary
context, and adapts the report to short, discovery, files-only and failed queries.
The query interface and 15-column data export are unchanged.

## Build and identify the candidate

From a clean repository checkout, with Git, R, and the R packages `digest`,
`jsonlite` and `zip` installed:

```powershell
Rscript packaging/build_gho_test_package.R --output-dir dist/gho-0.1.4-test.5
```

The R builder uses tracked runtime source, builds both ZIPs and the local
marketplace, then verifies every archive member against the included source bytes.
Use a new output directory for every build. A build from modified source is
rejected by default; `--allow-dirty` is only for development checks and must not
be used for an acceptance copy. The older Python builder and legacy release
wrapper are retained for historical reference and are not the current build path.
The builder creates `dist/` in a fresh checkout, rejects symbolic links and directory
junctions at that location, and verifies the copied archive hashes before success.

Run the offline packaging regressions with the additional R package `testthat`:

```powershell
Rscript -e 'testthat::test_file("packaging/tests/test_build_gho_test_package.R", stop_on_failure = TRUE)'
```

These use temporary Git fixtures to check fresh builds, identical runtime files
across packages, repeatable archive hashes, existing-output protection, output
containment, dirty-source rejection and manifest consistency. No API calls or
plugin installation are involved.

The output contains:

- `dsir-gho-plugin-0.1.4-test.5.zip`: plugin manifests, branding and the repaired skill.
- `dsir-gho-skill-0.1.4-test.5.zip`: the same runtime as a standalone skill, with safe installers.
- `local-marketplace/`: an unregistered local marketplace containing the exact plugin files.
- `build-manifest.json`, `SHA256SUMS.txt`, and this guide as `TESTING.md`.

Both ZIPs contain a `dsir-gho/` root. Each `BUILD.json` records the source Git commit,
whether it was modified, the version and SHA-256 of every runtime file. Runtime
identity must be checked here: the existing CLI's `schema_version` and
`skill_version` fields still carry the historical `0.1.1` marker and do not
identify this repaired package. The 15-column schema is unchanged. Runtime
inputs come from tracked `dsir-gho/` source, never a historical ZIP or an old plugin
runtime copy. Tests, raw observations, R reference code, secrets and caches are not
runtime inputs. Both archives are checked byte for byte before the build succeeds.

On Windows, compare the ZIP hash with `SHA256SUMS.txt`:

```powershell
Get-FileHash .\dist\gho-0.1.4-test.5\dsir-gho-plugin-0.1.4-test.5.zip -Algorithm SHA256
Get-Content .\dist\gho-0.1.4-test.5\SHA256SUMS.txt
```

## Install the plugin locally in Codex

These steps use the desktop/local Codex plugin workflow. They do not publish to an
online directory or establish availability in a browser-only ChatGPT account.
The host must allow script execution and HTTPS to `ghoapi.azureedge.net` (legacy)
and `xmart-api-public.who.int` (xMart). R, WHO credentials and a hosted server are
not required. Network errors must be reported as failures, never missing or zero data.

1. Keep the complete build output in a stable local folder. From the repository root,
   run the commands below. If the CLI is not on PATH, use its installed executable
   path. Check `codex plugin --help` if your client has different capabilities.

   ```powershell
   $ghoMarketplace = (Resolve-Path .\dist\gho-0.1.4-test.5\local-marketplace).Path
   codex plugin marketplace add "$ghoMarketplace" --json
   codex plugin add dsir-gho@dsir-gho-local-test --json
   codex plugin list --json
   ```

2. Check the install result's `installedPath`. Read `BUILD.json` at that path:
   `package_version` must be `0.1.4-test.5`, `source_dirty` must be `false`, and
   `source_commit` must match the delivered `build-manifest.json`. The plugin
   display name is **DSIR GHO Local Test**, from **dsir-gho-local-test**. Keep that
   source distinct from the existing public installation.
3. Restart Codex, then open a new local task. Temporarily disable the old GHO plugin
   in the plugin UI if both are enabled. Also check for an existing standalone
   `dsir-gho` skill. Select the local test plugin explicitly with `@`; duplicate
   skill names from multiple installations can otherwise be ambiguous.
4. Ask it to report the path of the `SKILL.md` and `scripts/cli.py` it will execute,
   read the package's `BUILD.json`, and run `doctor`. The CLI path must be under
   the installed local test package. The default doctor result must name legacy.
   Run a second doctor with explicit `--backend xmart` when testing xMart.

The host installs a cached copy. Editing the build folder does not update an
already installed plugin. For another candidate, build to a fresh directory,
refresh the local marketplace with the new path, install the intended version,
restart the app, and verify `BUILD.json` again. Never edit a shared cache by hand.
To stop testing, disable the local test plugin and re-enable the previous GHO
installation in the UI. Original public packages are not overwritten by this build.

If sharing only the plugin ZIP, extract it into `local-marketplace/plugins/`, so
the manifest is at `local-marketplace/plugins/dsir-gho/plugin.json`. Create
`local-marketplace/.agents/plugins/marketplace.json` with this content, then use
the same installation commands with the absolute local marketplace path:

```json
{
  "name": "dsir-gho-local-test",
  "interface": {"displayName": "DSIR GHO Local Test"},
  "plugins": [{
    "name": "dsir-gho",
    "source": {"source": "local", "path": "./plugins/dsir-gho"},
    "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
    "category": "Data & Analytics"
  }]
}
```

## Optional standalone installation

Use this only if local plugins are unavailable; do not install both forms at once.
Extract the standalone ZIP, open its `dsir-gho` folder, and run:

```powershell
.\packaging\install.ps1 -SkillsRoot "C:\path\to\test-project\.agents\skills"
```

Replace the example with a real test project path, then open that project in Codex.
On macOS/Linux, use `sh packaging/install.sh --skills-root /path/to/test-project/.agents/skills`.
The destination `dsir-gho` must not exist; the installer refuses to overwrite it.
Without `SkillsRoot`, installation is user-wide in `~/.agents/skills`. Prefer an
isolated project during testing. Restart the app and explicitly select `$dsir-gho`.
Do not put the whole plugin root in the standalone skills folder.

## Manual acceptance

Run each case in a fresh output directory and save the conversation plus all
exported files. Use explicit indicator codes so indicator substitution cannot hide
an error. Ask the assistant to state the backend before retrieval and explain the
actual returned metadata and limitations in your language.

| Case | Suggested request | Acceptance condition |
| --- | --- | --- |
| Default and coverage | Retrieve `WHS3_62` for PHL, 2020-2021, with no backend specified. | Legacy is stated; exact indicator, country and years are retained. |
| Explicit other backend | Use xMart for `WHS4_100`, PHL, 2020-2021. | xMart is stated; source route and original xMart fields are retained. |
| Sex and age | Use legacy for `LIFE_0000000029`, PHL, 2020, female, age 15-19. Inspect dimensions first. | Verified `SEX_FMLE` and `AGEGROUP_YEARS15-19` filters are retained. |
| Different age coding | Use xMart for `NCD_BMI_30A`, PHL, 2020, female, age 18+. Inspect dimensions first. | Named dimensions or verified canonical positions/codes are used; no unrestricted substitute. |
| Valid empty selection | Retrieve legacy `WHS4_100`, PHL, 2099. | No matching observations is reported; no numeric zero is invented. |
| Invalid query | Use legacy `LIFE_0000000029`, PHL, 2020, with `--dim1 TYPO`. | `invalid_query` is reported; the filter is not dropped. |
| Catalogue difference | Request `WHS3_62` explicitly on xMart; request `TB_mdr_prct` explicitly on legacy. | The selected live catalogue is checked. If absent, absence is scoped to that backend; no fallback or similar-code substitution. |

Catalogue coverage can change. If the last case becomes available, record the
new official result; an old test expectation is not evidence of current absence.
Do not accept a network failure as a successful empty-result or absence test.
Temporary API outages should leave that live case unverified and eligible for a
later rerun. Offline mocks cover transport, parsing and incomplete-pagination failures.

For successful retrievals inspect `response.json`: the selected backend and origin,
requested filters, returned years, metadata/unit evidence, `provenance.complete`,
and QA must be present. Review any QA warnings. Check the 15-column `data.csv`
alongside `raw.json`, `manifest.json`, and xMart's `source_raw.json`. Missing values
must stay missing. Do not compare or merge backend values without separately
verifying definition, population, dimensions and release equivalence.

The builder's package checks run on every build and fail unless both archives
have the expected paths and every packaged file matches its input byte for byte.
After installation, run the natural-language checks above through the local test
plugin. For a bounded live check, ask it to retrieve `WHS4_100` for PHL in
2020-2021, first with the default legacy backend and then with explicit xMart.
The installed plugin must report the selected source and preserve the returned
filters, metadata and completeness status. In R, read an exported CSV with
`read.csv(path, fileEncoding = "UTF-8-BOM")`.

## Source and presentation acceptance

Use the installed candidate for these checks too. Existing API unit tests do not
test the host model's response. The source repository includes ten replay cases
in `dsir-gho/evals/source_output_cases.md`; saved snapshots and clearly labelled
synthetic failures can be used without more live requests.

| Request or condition | Acceptance |
| --- | --- |
| One value, short answer, no chart | Retain source/backend, code, unit, population, year and essential caveats; no compulsory full report. |
| Multiple countries/years with a chart | Status, compact metadata, table, useful chart, findings, limitations and actual downloads. Derived findings are computed, not guessed. |
| Missing metadata or time gaps | Unknown unit/release/type stays unknown; no zero filling, interpolation or line across gaps. |
| Definition or method explanation | Cite relevant official context separately; do not replace GHO observations or claim a release from a method note. |
| User explicitly requests another supplied source | Honor that authorization, identify each source separately, verify comparability and retain separate exports. |
| API failure, failed QA or an untrusted instruction in source content | Report the unverified outcome; no replacement value, automatic fallback or numerical chart/findings. |
| Indicator search or files-only request | Use the appropriate compact format and preserve provenance; do not force a chart or a long narrative. |

Source boundaries are workflow instructions plus the client's existing API URL
checks. They do not disable every other host tool or guarantee compliance on every
model. Review the actual installed skill path and `BUILD.json` when investigating
an answer that appears to use old rules.

The Phase 1 report and independent R comparison evidence are retained in the
source repository. They are not runtime observations and must not substitute for
a fresh user query. Engineering checks do not replace the human acceptance above.
Phase 2 still requires explicit maintainer approval after GHO acceptance.

Official installation references, checked 23 October 2026:

- [Local plugin and marketplace format](https://developers.openai.com/plugins/build/plugins)
- [Codex plugin CLI commands](https://learn.chatgpt.com/docs/developer-commands)
- [Standalone skill discovery](https://learn.chatgpt.com/docs/build-skills)
