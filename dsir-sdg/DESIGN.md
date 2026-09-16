# DSIR SDG 0.1.0 design

## Boundaries and architecture

The model reasons about natural-language meaning; deterministic Python scripts
retrieve and transform public UN observations. No R execution is required at
runtime. The original DSIR package and existing GHO skill are unchanged.

| Component | Responsibility |
|---|---|
| SKILL.md | Indicator/series decisions, clarification, source-aware answer |
| sdg_client.py | Validated live catalogues, repeated area parameters, complete paging, timeouts/retries, filters |
| indicator_search.py | Exact/keyword/fuzzy discovery and series metadata |
| locations.py | Live UN code/name resolution plus DSIR ISO3 mapping |
| clean.py | DSIR 15-column core and aligned raw context |
| qa.py | Missingness, bounds, duplicate keys, strata and units |
| cli.py | Agent interface, complete exports, provenance |
| references | Semantic and location rules; small reviewed aliases and country metadata |
| evals/tests | API contracts, casebook, R parity, realistic agent use |

## Reference reuse and intentional changes

Reference is DSIR source 0.9.0, commit
`e2ff6735d174769b55f9a3e55f9f36c75ce9f397`. See the source audit for file-level
findings. Existing GHO logic informed the standalone layout, error envelopes,
trace hashes and non-overwriting exports; no GHO client is imported at runtime.

The core cleaner reproduces original first-indicator flattening, raw series
description, Member State names, numeric coercion, null semantics, null SDG
dim1/2/3 and stable sorting. Additional context preserves what that compact
schema intentionally discards. No cleaner fills labels or synthesizes values.

Intentional agent-oriented departures from the R interface:

1. A failed request raises a typed error rather than returning an empty tibble.
2. Pagination counters and final totals must agree; changed/repeated/missing
   pages fail closed rather than presenting a partial result.
3. Names and mixed ISO3/numeric location inputs are resolved first, with no
   silent dropping. The low-level data client accepts resolved UN numeric codes.
4. Current indicator/series catalogue validation precedes retrieval.
5. Series, population dimensions and attributes can be filtered locally. R has
   no direct equivalent arguments; parity distinguishes base retrieval from
   the additional filters.
6. Request retries include transient status/connection failures and malformed
   JSON, with bounded attempts. Default per-request timeout is 45 seconds.
7. Output limits are explicit errors, not silent truncation. Default maximums
   are 1,000,000 rows, 10,000 pages, 500 MB cumulative data-response bytes; each
   individual response is limited to 50 MB.

Years are filtered locally exactly because DSIR documents failures with UN
timePeriodStart/timePeriodEnd query parameters. Area/indicator filters use
repeated parameter keys, never comma-separated codes. Query scope is rechecked
against returned records.

## Metadata and governance

Country metadata is a versioned DSIR export, checked against all 194 current
reference Member State records. Live UN catalogues determine actual query codes
and territory/aggregate names. Static WHO region membership is not used to
calculate aggregates. Aliases contain a small set of search terms or location
names; every resulting code is verified live.

No observation dataset is included in either runtime distribution. Recorded
API observations in the source archive are test evidence only. The scripts do
not write to source services, send user credentials, or call an LLM API.
Requests expose the selected public indicator/area query to UN servers.

## Distribution and limits

Standalone ZIP, full source ZIP and skills-only plugin ZIP are built together.
The plugin includes portable and Codex compatibility manifests, with the
existing DSIR logo as composer icon and logo. Public publication, identity
verification and account installation are outside this local build.

No universal ChatGPT ZIP attachment installation or unrestricted cloud script
network access is promised. Installation is separate from execution ability.
Publisher website/privacy/support/terms URLs are not invented. Provide real
listing information when submitting publicly.

## Next version

Priorities after real user feedback: richer official reference-metadata access,
explicit version-aware series comparison, faster verified series-specific
retrieval for very large queries, and more geography/terminology aliases backed
by reproducible catalogue evidence. Preserve the clean schema and transparent
source boundaries. No server or modelling layer is needed for those changes.
