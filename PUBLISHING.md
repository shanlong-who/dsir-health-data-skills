# Publishing and reproducibility

## Release identity

- Repository owner and author: Shanlong Ding (`shanlong-who`).
- Collection release: `v2026.09.16`.
- GHO plugin: 0.1.1; underlying skill: 0.1.0.
- SDG plugin and skill: 0.1.0.
- Reference: DSIR 0.9.0, revision `e2ff6735d174769b55f9a3e55f9f36c75ce9f397`.

The four downloadable runtime ZIPs are the previously validated artifacts,
unchanged for GitHub publication. `SHA256SUMS.txt` records their byte-level hashes.
`plugins/` contains the exact extracted plugin contents. The repository source
adds a publication README, attribution, and portable maintainer defaults.

Only the two independent skills are included. The earlier server project,
local libraries, authentication material, interpreter caches and failed
preflight reports are excluded. Machine-specific paths in the retained
validation reports are replaced by placeholders. Observation values, test
outcomes, source hashes and timestamps are unchanged. Those reports document
historical runs; they are not new live checks performed at publication time.

Component READMEs describe the original standalone releases and may refer to
separate source ZIPs. This GitHub repository and GitHub's source archives provide
the full source for both components. The SDG component license's inherited WHO
data footer does not describe the SDG data source: SDG observations are from UN
SDG, and the UN's applicable data and metadata terms govern that content.

## Run offline tests

From the repository root, with Python 3.10 or later:

```sh
python -m unittest discover -s dsir-gho/tests -v
python -m unittest discover -s dsir-sdg/tests -v
```

See each `evals/README.md` for live checks. For R parity only, install the reference
R dependencies and pass `--source-dir` with a checkout of the recorded DSIR source.
`--rscript` defaults to `Rscript` on PATH; an explicit executable path is accepted.
Run `python dsir-gho/evals/run_parity.py --help` or the equivalent SDG command
before choosing arguments. A current API response may differ from a recorded
response; investigate differences instead of changing observations to pass.

## Rebuild packages

From the repository root:

```sh
python dsir-gho/packaging/build_release.py --output-dir dist
python packaging/build_gho_plugin.py
python dsir-sdg/packaging/build_release.py
```

Builds write to `dist/` and update the extracted plugin directories. Use a clean
checkout and review changes. ZIP timestamps and maintainer-source adjustments
can change archive hashes; compare runtime file contents as well as version
numbers. Do not replace published assets silently; use a new release for changes.

## Distribution boundary

GitHub Releases is the public source and download channel for these artifacts.
It is separate from a plugin directory's submission and review process. A
compatible host with script execution and API network access remains required.
