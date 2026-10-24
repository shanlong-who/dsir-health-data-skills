# GHE geography and statistical interpretation

## Geography and discovery

The bundled `metadata/who_countries.json` is a 194-member DSIR snapshot.
`metadata/provenance.json` records its source commit, file checksums and regional
and income-classification vintages. Preserve M49 leading zeros and Namibia's
literal ISO2 code `NA`. Cook Islands and Niue have missing World Bank groups.
No R package is needed to read these JSON files.

Use this mapping for exact names and identifiers, then verify the source area
code against GHE discovery. It does not include every reporting territory.
An exact API area code outside the mapping can retain a missing country label;
do not assign a nearby Member State. Ambiguous/unrecognized inputs require
clarification. A partial set of resolved locations is not the full user request.

WHO regions, UN regions and income groups are different. A historical year does
not establish historical membership. This initial GHE client does not create
regional aggregates. If the user wants constituent-country results, explicitly
state the dated grouping and selected members; do not present their average
rate or sum of overlapping categories as an official regional estimate.

Following DSIR, years and sex use official reference views. Area discovery is
the latest year's all-cause/all-age/both-sex slice. Ages and causes use the
first available WHO Member State in ISO3 order as a reference country.
These lists are bounded discovery evidence, not proof of historical coverage.
An unconfirmed code is scoped to that reference catalogue. `coverage` retrieves
selected source identifiers and counts rows before measures are pivoted; it
does not count deaths or establish which measure values are nonmissing.

## Measures and causes

`metadata/measures.json` reproduces DSIR 0.11.0's field mapping. Discovery exposes
only mappings whose provider fields actually exist. Keep deaths, YLL, YLD,
DALY, their rates and their percentages separate. Death counts are persons;
YLL/YLD/DALY counts are years. Values are not rescaled into thousands.

All-age rates are crude; selected-age rates are age-specific. No new
age-standardized rate is calculated. A requested age-standardized analysis
needs a separately validated method, non-overlapping age-specific inputs and
an identified standard population, so it is outside this query client.

Counts preserve available provider uncertainty bounds. Rates and percentages
do not inherit count bounds; unknown bounds stay null. Missing measure values
are retained and distinguished from genuine numeric zero.

Cause names, levels, groups, `rankable` and `single_cause` flags are retained as
available. The public source does not provide a parent-code field.
`cause_group` is not a parent identifier. Do not combine all causes with their
components, overlap age bands, sum rates/percentages or assume a selection is
mutually exclusive from its level or rankable flag alone.

WHO describes GHE as estimates synthesized from multiple sources and methods.
See the [official GHE methods overview](https://www.who.int/data/global-health-estimates).
That page is supplementary context, not an API release identifier. A retrieval
date, reference year or methods-document date does not establish the vintage
of returned observations. Keep `release = null` until actual evidence identifies
it, and never merge snapshots or sources by assumed equivalence.
