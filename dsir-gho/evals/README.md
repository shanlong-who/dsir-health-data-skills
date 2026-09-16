# Evaluation and original-DSIR parity

These are development checks, not dependencies of the installed skill. The skill runs with Python's standard library. Only the optional reference-parity audit requires R and the original DSIR source/package.

## Evaluation cases

`cases.json` contains 46 cases, including the user's five original prompts. There are **29 nonsynthetic natural-language health-data questions**, four additional location-resolution questions, and 13 clearly labelled synthetic failure or invalid-input questions. All expected indicator candidates were verified in the live WHO catalogue on 9 September 2026. A deliberately invalid indicator string and injected failure responses are explicitly test inputs, not proposed WHO indicators.

Every case contains `user_question`, `expected_indicator_code` or `expected_candidates`, `expected_locations`, `expected_year_logic`, `should_clarify`, and `important_notes`. The compatible `prompt` field repeats `user_question`. These question-level expectations supplement the executable `operation`, `args` and `expect` contract; they are not assertions that a model produced the expected response. Location-only and intentionally unmatched searches use an empty candidate array instead of inventing an indicator.

Validate the schema, consistency with executable arguments and the minimum of 20 nonsynthetic health-data questions locally:

```text
python evals/run_evals.py --validate-only --output reports/casebook_validation.json
```

This validation runs before every evaluation and can be run alone without contacting WHO. It checks field presence/types and cross-field consistency; semantic question quality and `should_clarify` behavior still require human review.

The casebook covers:

- Official WPR UHC aggregates and all-year coverage.
- PHL measles reported cases since 2015 and a three-country UHC comparison.
- Ambiguous financial-protection and TB choices.
- Count, rate, percentage, currency, age, sex and pregnancy dimensions.
- Current country/area/region resolution and Indonesia-related aggregate codes.
- Missing filter combinations, invalid codes and invalid year ranges.
- Network failure, retries, malformed response schemas, incomplete/cyclic paging and unsafe links.
- A forced live seven-row page size, verified against the reported total.
- Preservation of missingness, literal values and duplicate observations.

Run from the skill directory or use the appropriate absolute paths:

```text
python evals/run_evals.py --offline --output reports/eval_offline_results.json
python evals/run_evals.py
python evals/run_evals.py --case main_01_wpr_uhc --case main_05_tb_ambiguity --output reports/selected_cases.json
```

To retain earlier evidence and recheck only affected cases, add `--merge-from reports/eval_results.json`. The updated report records the rechecked IDs and preserves their previous results; unchanged cases retain their earlier execution dates. This does not rerun or refresh every case.

The live runner uses the actual runtime functions and WHO endpoint. Every search candidate is checked against the freshly retrieved catalogue. Data cases check the returned indicator, country/region, years, dimensions, observation count and completion/provenance contract. Reports contain actual observed results; dates and coverage are not hard-coded as newly retrieved facts.

An API contract is **not** a test of a model's natural-language response. No model is called by `run_evals.py`. Each case with `review` criteria remains `manual_review_pending` even when its API contract passes. To evaluate skill behavior, start a fresh assistant conversation with the installed skill, submit the exact prompt, retain the response and produced files, and independently score every listed criterion. Record the model, date, response, evidence paths, score and reviewer. Do not relabel these criteria as passed based only on an API call or static skill inspection.

For the TB prompt, a correct review outcome includes clarification of rate versus count and overall versus HIV-positive TB; a top-ranked candidate alone is insufficient. For WPR UHC, check that the assistant selects the official region series and explains the current group versus the explicit series without Indonesia. For financial protection, check reported versus estimated values and percentage versus millions.

## Original DSIR parity

`run_parity.py` compares 15 distinct, real indicator queries. Most are complete PHL series since 2015; WPR UHC and both estimated financial-protection series use all available years. Python and R independently retrieve the same requested filters. Each raw response and each cleaned table is retained as test evidence under `reports/parity/`.

```text
python evals/run_parity.py --source-dir "C:/path/to/original/DSIR" --rscript "C:/path/to/R/bin/Rscript.exe"
```

On the development laptop the defaults point to the original sibling DSIR repository and R 4.6.1. Installed DSIR 0.9.0 supplies package helpers and country metadata. The R reference reads the original `R/gho.R` into an isolated environment, uses its unmodified `gho_data()` and `gho_clean()`, and records the original revision and source hash. It also checks that those function bodies match the installed package. No original repository or installed package file is changed.

`parity.R` loads `callr` in the parent and executes the reference in a child. It records child success or failure separately. The parent exits zero after recording a child error so that native child-process failures remain inspectable; the Python runner still fails the audit when child execution was unsuccessful.

Every query comparison checks:

1. All 15 columns and their exact order.
2. String, integer and numeric scalar types.
3. Raw and cleaned row counts, row keys and duplicate multiplicity.
4. Location/indicator labels, raw display values, dimensions and year values.
5. Missingness in every column.
6. Numeric estimates and interval bounds with absolute tolerance `1e-10` and relative tolerance `1e-12`.

The 15 fields are `source`, `id`, `indicator`, `location`, `iso3`, `location_name`, `year`, `value`, `value_num`, `low`, `high`, `series`, `dim1`, `dim2`, and `dim3`.

A second comparison feeds each exact Python raw response and catalogue into the original R cleaner. This separates transformation discrepancies from source revisions or retrieval differences. Additional explicitly synthetic edge cases test literal `NA`, blank/raw threshold strings, missing scalar fields, an unrecognized DSIR aggregate label, integer coercion and duplicate rows. Those values are not presented as WHO observations.

When code changes affect only comparison logic, recompare saved evidence without another download:

```text
python evals/run_parity.py --reuse-evidence
```

This mode is labelled as saved-evidence recomparison in the report. It must not be reported as a new live run. A failure in live parity with a pass on identical raw inputs calls for inspecting the saved responses before diagnosing a cleaner bug. Reports remain evidence; neither retrieval nor cleaning reads these files during normal skill use.
