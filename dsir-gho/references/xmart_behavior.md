# WHO public xMart GHO behavior

Reference: DSIR 0.11.0, commit `885464b1fade2f8b6d02dde93f9080e4b3f4f2a5`.
The installed runtime is independent of R. [Reference hashes](metadata/dsir_reference.json)
identify the unmodified source files used for maintainer parity.

## Discovery and routes

The English `DATA_/IND_DIRECTORY_WIDE` directory supplies verified GHO codes,
names, units and routes. Multiple directory entries can share a GHO code.
Catalogue names follow the first entry; retrieval prefers a downloadable entry
and an exact `IND_PER_CODE` match, as in DSIR. The observation's published
`IndicatorName` takes precedence during cleaning, including a missing source name.

Only `DATA_/RELAY...` object identifiers are extracted from `DWNL_QUERY` and
`IND_PUBLISH_TABLE`. Their hostnames and embedded filters are never followed.
All requests use `https://xmart-api-public.who.int`. Unknown codes and unsupported
routes are explicit failures; legacy catalogue presence does not establish xMart
availability. GHE mart/table routes are outside this adapter.

## Retrieval and integrity

Normal retrieval uses stable ordering, `$top`, `$skip` and `$count=true`.
Counts must remain stable and match the final row count. Missing/duplicate
`Sys_PK`, repeated pages, schema/type changes, premature termination and resource
limits fail the request. Pagination and redirects must remain on the selected
production resource. The default page size is 5000; the public cap is 120000.

Queries over 1800 encoded query bytes use read-only POST to `/$query` with
`text/plain`. Provenance records the actual method, query URL, body checksum and
response checksum. The API supports retrieval only; this POST does not publish data.

Dimension discovery uses grouped queries in batches of at most six fields.
Grouped `@odata.count` may count facts rather than groups, so a short page verifies
completion; a full page requires another request. No observation values are cached
on disk. Successful reference lookups have a 600-second in-memory cache.

## Dimensions, measures and geography

Prefer named fields and exact native values shown by `describe`. Wide tables map
core positions from the schema: sex, age, then other dimension fields alphabetically.
An all-null field still occupies its position. Long tables preserve each row's
`DIM_n_CODE`/member pairing. Positions beyond three and all derived named native
dimensions remain in context and raw files. Named filters are checked against the
schema or observed long-table type positions; absent fields never remove a filter.

Canonical positional sex codes map to `TOTAL`/`MALE`/`FEMALE` or the observed
population-sex codes. `AGEGROUP_` remains supported for positional age filters.
Named values are exact provider codes and do not receive these translations.

Numeric fields come from `VALUE_NUMERIC` on long tables or a single active `_N`
measure family on wide tables, with its `_NL`/`_NU` bounds. Multiple active families
are a failure. Missing numeric values stay missing. Original display labels remain
strings; when a label is absent, the numeric value is formatted as DSIR does.

Geography is resolved through live `REF_GEO`, preserving zero-padded M49 values.
WHO group mappings (953-958 and global 001) are checked against that reference.
WHO Africa and UN Africa are distinct groups. Regional variants are accepted only
when verified in this backend; legacy variants are never substituted. Nonannual
time strings remain in context and have a missing core year when not coercible.

The core CSV keeps exactly 15 columns. `source_raw.json` preserves the original
provider records, and the same row index links them to normalized `raw.json`.
No imputation, aggregation, invented identifier or guessed unit is performed.
