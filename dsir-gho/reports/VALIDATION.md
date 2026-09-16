# Version 0.1.0 validation

Validation date: 9 September 2026. The runtime was tested with Python 3.12.14 on Windows. R 4.6.1 and DSIR 0.9.0 were used only for the separate reference comparison.

| Check | Result | Evidence |
| --- | --- | --- |
| Offline unit tests | 54 passed | [Test output](unit_tests.txt) |
| Casebook schema | All 46 cases contain the requested fields; 29 real health-data questions, 4 location questions, 13 synthetic cases | [Schema report](casebook_validation.json) |
| Executable eval contracts | 46 passed | [Evaluation report](eval_results.md) |
| Independent live R/Python comparisons | 15 distinct indicators passed | [Parity report](parity/parity_results.md) |
| Common-raw cleaning comparisons | 16 passed | [Parity details](parity/parity_results.json) |
| Main natural-language workflows | Five completed in a Codex agent rehearsal | [Answers and tool evidence](agent_acceptance.md) |
| Packaged runtime with R unavailable | Passed: official WPR UHC, 24 rows, 2000–2023, four forced pages, QA pass | [Package check](package_validation.json) |
| Windows and Unix installers | Isolated installation and existing-destination refusal passed | See installation notes below |

The source package and previous service were not modified. The reference repository remains at `e2ff6735d174769b55f9a3e55f9f36c75ce9f397` with a clean working tree.

## What these results establish

The client fetches complete source observations and reproduces the DSIR 15-column cleaning semantics for the tested indicators. Comparisons cover identifiers, location labels, years, raw display values, numeric estimates, bounds, dimensions, per-column missingness, row counts and multiplicity. Numeric comparison tolerances are `1e-10` absolute and `1e-12` relative; the comparator was also checked against intentionally corrupted results.

The main regional test uses the WHO-published `WPR` series. It does not reconstruct or average country observations. The separate `WPR_WO_IDN` series remains distinct. Coverage is observed from the current WHO response, not assumed from older documentation or a fixed country vector.

The runtime package was extracted and its actual CLI run with an empty `PATH` and an unavailable `R_HOME`. Import/help, connectivity, data retrieval, four-page completion, cleaning and QA passed. The original machine has R installed for development, but the skill scripts neither locate nor invoke it.

## Limits of the evaluation

The automated runner does not call a language model. It correctly leaves 11 response-review criteria pending in its own report. Five main cases have separate recorded Codex agent rehearsals; the remaining response reviews were not performed. This is not a multi-model benchmark or a test of installation in an ordinary ChatGPT account.

Two initial harness assertions expected uppercase location types, while the documented resolver returns lowercase. Those assertions were corrected and rechecked; the report retains the earlier failure evidence. No WHO observation was changed to make a test pass.

The Windows sandbox blocked a standard temporary-directory operation during the export test. The suite passed under normal host-approved temporary-file permissions. This was an execution-environment restriction, not a data or cleaning discrepancy.

## Packaging and installation checks

Both installers were exercised with isolated temporary skill roots and refused a second installation without changing the existing skill. Neither the user's default skill directory nor runtime/network settings were changed.

The release validator checks ZIP integrity, safe archive paths, packaged Markdown links, the skill's name and description, UI invocation metadata, importability, and optional live WHO access. The bundled OpenAI YAML validator requires a development-only PyYAML dependency unavailable in this environment, so narrow standard-library checks were used instead. PyYAML is not a skill runtime dependency.

The compact runtime archive excludes recorded observations, tests and R parity scripts. The separate source archive contains the complete project and validation evidence. Test evidence is never read as a fallback for new data requests.

## Known limitations and next steps

See [technical design](../DESIGN.md) for the platform boundary, WHO endpoint retirement notice, metadata coverage, regional membership limits, and the recommended next-version sequence. See [README](../README.md) for installation and sharing instructions.
