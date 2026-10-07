# DSIR GHO design

## Scope and reference

This portable GHO client follows DSIR 0.11.0 at commit
`885464b1fade2f8b6d02dde93f9080e4b3f4f2a5`. It runs with Python 3.10+ and the
standard library. R is used only to validate the original source. No R runtime,
MCP server, credentials or hosted service is required for end users.

The scope is WHO GHO. GHE is not added to this plugin. SDG remains a separate
component. See [xMart behavior](references/xmart_behavior.md) for the adapter
rules and [source hashes](references/metadata/dsir_reference.json) for provenance.

## Processing

1. Verify indicator candidates in the live English xMart directory.
2. Resolve a supported RELAY route without following directory hostnames.
3. Inspect the table schema and observed dimensions. Resolve requested areas
   through live geography references; do not expand regional membership.
4. Apply exact native named dimensions, or the supported positional code
   translations. Missing requested dimensions are errors, never unrestricted queries.
5. Retrieve complete pages with stable ordering and row-count checks. Use read-only
   `/$query` POST for long queries. Grouped metadata uses short-page completion.
6. Normalize wide/long source records as DSIR does. Reject ambiguous numeric families.
7. Preserve exactly 15 core columns and every original provider row. Extra dimensions,
   types, measure fields, time detail, source metadata and identities stay outside
   the core table.
8. Export into a fresh directory with four data files and a checksum manifest.
   Terminal previews are limited; analysis must read the complete saved result.

`source_raw.json` holds unchanged xMart records. `raw.json` holds their normalized
DSIR observation view. The raw row index links both arrays to sorted cleaned rows.
No imputation, aggregation or source-row deduplication is performed.

## Failure and provenance

Unknown codes, unsupported routes, malformed responses, failed requests, changed
counts, repeated IDs, schema/type drift, resource limits and unsafe redirects are
explicit failures. A verified empty selection is distinct from all of them.

The backend is selected explicitly and recorded. xMart errors never switch to
legacy. Compatibility requests use `--backend legacy` and the legacy GHO origin.
Provenance includes origin, table, filter, directory evidence, request method,
request-body hash, response hashes, retrieval times, completion state, skill
version and pinned DSIR source hashes.

Successful xMart reference lookups use a 600-second in-memory cache. No test report,
saved observation or disk cache is read as a fallback for a new request.

## Validation and limits

Offline tests cover both adapters and transformation/export contracts. R common
inputs check all 15 core fields, numeric tolerance, missingness, multiplicity and
retained context against unmodified source files. Typed fixtures preserve literal
JSON strings such as `"NA"`; they are clearly synthetic, never WHO values.

Fresh live checks and independent R retrieval are separate evidence. On 7 October
2026, single-row probes succeeded but complete queries and directory retrieval
redirected to WHO's sorry page. Independent live parity remains unverified.
The maintenance packages are candidates until that gate passes.

A complete retrieval does not guarantee every requested country-year or stratum.
The API does not expose a transaction snapshot token; source revisions can change
results between requests. Observed dimensions do not prove every combination is
available. Units come from live directory fields; missing definitions stay missing.

All-year queries retain observed source coverage. Source-published regional groups
remain distinct and do not establish historical membership. The Member State naming
snapshot is versioned; a published `SpatialName` fills other location names as in
DSIR 0.11.0. Neither offline contracts nor the historical agent rehearsals establish
new model-behavior or platform-installation results.
