# GHE validation

Run offline synthetic transport, selection, QA and export tests first:

```text
python -m unittest discover -s dsir-ghe/tests -v
```

The bundled interpreter must be provided by the host; the plugin does not
install a runtime or depend on R. Test fixture values are explicitly synthetic.

## Bounded WHO checks and independent R comparison

From the repository root, use new output directories:

```text
python dsir-ghe/evals/run_live.py --live --output-dir dist/ghe-live-new
python dsir-ghe/evals/export_parity_fixture.py --output-dir dist/ghe-synthetic-new
Rscript dsir-ghe/evals/verify_dsir.R dist/ghe-live-new dist/ghe-synthetic-new dist/ghe-parity-new --live
```

The live suite discovers actual codes, checks all supported measures, forces
small-page sex/age retrieval, verifies an exact diabetes cause, a successful
empty range, coverage and an invalid sex. It does not infer missing numbers.
R must load the pinned DSIR 0.11.0 reference in an isolated development library.
The verifier compares all 16 fields, missingness and units at tolerance 1e-10,
replays actual raw rows and a synthetic missing/zero case, and independently
re-queries three WHO selections when `--live` is supplied. Omitting that flag
replays saved evidence without live requests. R is excluded from runtime ZIPs.

`export_reference.R` is a maintainer tool to export a fresh pinned reference.
It refuses to overwrite existing metadata; do not run it as a routine user step.
Source commit, country and measure checksums are included in the runtime.

## Response behavior

Use the realistic prompts in [manual acceptance](../../packaging/GHE_TESTING.md).
For independent forward tests, give an evaluator only the skill, requests and
required raw artifacts, not the validation report or intended answers.
Retain original timestamps; explicitly label synthetic failures.
Review exact provenance, chart inputs, deterministic calculations, missing
values, crude versus age-specific rates, and overlapping age/cause categories.

The [24 October report](../reports/validation-20261024.md) separates local
automated checks, saved-output response evaluation and outstanding target-account
acceptance. No passing replay guarantees every model or execution environment.
