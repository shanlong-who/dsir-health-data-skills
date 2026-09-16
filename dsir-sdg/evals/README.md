# SDG evaluation cases

The casebook contains 40 real user questions. Indicator codes, series and area
codes were checked against the UN SDG catalogue release `2026.Q2.G.02` on
2026-09-16. These are development expectations, not a runtime data cache.
The installed skill always confirms identities against the current API.

Each case states the expected indicator or candidates, series, locations, year
logic, clarification decision and important response limitations. Cases cover
UHC, maternal and child health, communicable diseases, NCDs, vaccines, financial
protection, water and sanitation, nutrition, regional definitions and invalid
requests. The UN SDG catalogue covers all SDGs; the initial casebook emphasizes
the health-data workflows used to validate this release.

## Automated checks

Run from the skill directory with Python 3.10 or later:

```text
python -m unittest discover -s tests -v
python evals/run_evals.py --validate-only
python evals/run_evals.py --catalogue-only --output reports/eval_catalogue_results.json
python evals/run_evals.py --output reports/eval_results.json
```

The first command uses synthetic observations and injected transports. It does
not use live UN data. The second checks the casebook structure without a network
request. Catalogue mode verifies current indicator/series/area identities and
runs search, location-resolution and invalid-input contracts. It explicitly
marks observation and metadata retrieval as not run. Full mode also runs data
and metadata contracts. It can take several minutes because pagination must
finish before the client applies year and dimension filters.

To repeat selected contracts, or deliberately exercise pagination:

```text
python evals/run_evals.py --case wpr_uhc_history --page-size 7 --output reports/eval_wpr_pagination.json
python evals/run_evals.py --case financial_current --merge-from reports/eval_results.json
```

For an offline review of previously downloaded official catalogues, supply a
folder containing `Indicator_List.json`, `Series_List.json` and
`GeoArea_List.json`:

```text
python evals/run_evals.py --catalogue-only --catalogue-dir PATH_TO_SNAPSHOT --output reports/eval_snapshot_results.json
```

The report labels this evidence as a downloaded snapshot, not a fresh API check.
No catalogue snapshot is needed to run the installed skill.

## What a pass means

The runner uses the explicit expected arguments in `cases.json`. It checks
verified identities, pagination completion, series/area/year filters, DSIR core
shape, context preservation, nonempty results where expected and basic QA.
It records current years, row counts, API request evidence and any warnings.
No observation values are hardcoded as permanent truths. The WPR UHC case
records a release-specific zero-coverage expectation, with its observation date
and release noted. A future change in coverage should trigger review rather than
be hidden by accepting every result.

The runner **does not call a language model**. A contract pass does not prove
that an assistant understood the question, selected the right code without
help, asked for clarification, interpreted the results correctly or cited the
source. Those decisions remain marked `natural_language_review: pending`.
The fixed-membership regional question is a review scenario only; it does not
compute a regional average.

## Manual assistant review

Start a fresh task with the installed skill, submit the exact `user_question`
without the expected codes, and retain the assistant's answer and tool evidence.
Assess it against the case fields:

- Did the assistant verify the indicator and the actual series, rather than
  treating the SDG indicator number as one homogeneous measure?
- Did it resolve the intended UN area and requested years without silently
  broadening the query?
- Did it clarify a vaccine, occupation or incompatible financial-protection
  definition when `should_clarify` is true?
- Did it preserve sex, age, reporting-type and other strata, including units,
  source, footnotes and uncertainty bounds?
- Did it cite the UN SDG Global Database and state any underlying WHO custodian
  information separately?
- Did it distinguish a failed request, unknown identifier, globally empty
  indicator and empty filter result without inventing values?

Priority acceptance cases are `wpr_uhc_history`, `uhc_three_countries`,
`tb_rate_phl`, `under5_ambiguous`, `financial_old10`, `sdg_legacy_series` and
`suicide_by_sex`.

The 2025 UHC series `SH_ACS_UNHC_25` must not be silently spliced onto legacy
`SH_ACS_UNHC`. The current financial-protection series
`SH_OOP_XPD_EARNNET40` measures a threshold of 40% of discretionary budget. It is
not an interchangeable answer to the historical 10% of total-budget question.
The official `99047` area is WHO Western Pacific as represented by the current
UN release; its availability does not establish a historical fixed-membership
series or license averaging country UHC indexes.
For release `2026.Q2.G.02`, the UHC area query has no observations although the
global indicator has data. The correct answer is the explicit empty-filter
result, not a fabricated regional estimate. An initial nonempty test expectation
was corrected after inspecting live coverage; the prior failure is retained.

Dimension filters use the metadata `code` field and values observed in row
context. For example, suicide mortality uses `FEMALE` and `MALE`; the separate
`sdmx` fields `F` and `M` are not interchangeable filter values. The initial
suicide test made that distinction incorrectly; the corrected test retains its
previous failure in the report history.

## Parity testing

R parity is a separate developer-only check. Compare the same raw records
through DSIR `sdg_clean()` and the skill cleaner, using the 15 core fields,
including missingness and row multiplicity. Compare API retrieval using the
same indicator/area/year scope and account for the additional series and
dimension filters supplied by the skill. A change in the upstream release or
metadata is a reason to investigate, not to edit returned observations to make
tests pass. R is never needed by users of the packaged skill.
