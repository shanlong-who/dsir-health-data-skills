# DSIR GHO design

## Purpose and scope

Provide a self-contained agent skill that discovers and retrieves public WHO GHO data directly. The runtime is Python 3.10+ using only the standard library. The delivered interface supports environment checks, indicator search, indicator inspection, location resolution, and bounded observation retrieval with CSV and JSON output.

The package does not require an R session, a DSIR installation, an MCP endpoint, authentication credentials, a web service, or Docker. It covers WHO GHO; UN SDG and other source APIs require their own clients and selection rules.

## Relationship to DSIR

The reference package is DSIR 0.9.0 at Git revision `e2ff673`. The parent project's source review covers its 20 R source files. That review informs the GHO workflow and cleaned schema; it does not make the Python runtime an R wrapper or imply that every DSIR feature has been ported.

| DSIR responsibility | Portable implementation |
| --- | --- |
| GHO indicator discovery | Read and search the live indicator catalogue; rank actual catalogue entries. |
| GHO dimension inspection | Preserve available dimension labels and observe years and dimension values from source records. |
| GHO observation retrieval | Issue direct HTTPS requests, follow validated pagination, and retain source observations. |
| GHO cleaning | Produce the same ordered 15-field analytical view, with additional evidence stored separately. |
| Country and region handling | Resolve supported location inputs to source codes, keeping countries and aggregate variants distinct. |
| Reproducibility | Save the normalized query, retrieval time, request trace, metadata, QA, and original records with the result. |

R is a source reference for behavior and compatibility, not a runtime dependency. The previous R service remains a separate project component.

## Processing flow

1. The agent clarifies the analytical concept only when alternatives would change the result.
2. The client obtains catalogue candidates and verifies the selected indicator.
3. Indicator inspection exposes available metadata, dimension vocabulary, and observed coverage. Missing definition or unit evidence remains explicit.
4. Location resolution identifies the geography codes. Regional source aggregates are not automatically expanded into countries or calculated from country averages.
5. Retrieval applies explicit geography, year, and dimension selections, checks the returned records, and tracks pagination.
6. Cleaning creates the 15-column data view. Context rows align with the cleaned data and include zero-based clean and raw indices. Original raw records and extra source fields remain available outside the fixed schema. Coverage lists observed years and row counts per requested location, including locations with no matching records.
7. Export writes `data.csv`, `response.json`, and `raw.json` into a new output directory, plus `manifest.json` with SHA-256 checksums. Existing output directories are refused. The terminal output is a summary and a preview of up to 12 rows.

Search aliases and fuzzy matching help find catalogue entries; they cannot create an indicator, manufacture a code, or prove a unit. The runtime must obtain observation values from the source rather than from examples or regression-test expectations.

## Data decisions

**Measure selection.** Treat rate, count, percentage, index, and other measures as distinct. TB incidence is ambiguous when the user has not specified rate or number. UHC service coverage differs from financial protection. Present the relevant official candidates when the user's wording does not settle the choice.

**Metadata.** An explicit unit in an official indicator name or verified source field is evidence for that unit. A small bundled set of reviewed WHO metadata summaries also supplies definitions and units when the live code and official name match. These summaries retain their source URLs, review date, and stated basis; they are not refreshed with every query. Numeric range, familiarity, and model memory are not unit evidence. Keep a missing definition missing; do not substitute the title for a complete methodology description.

**Geography.** Keep source location code, type, and label together. `WPR` and `WPR_WO_IDN` may coexist for an indicator and must remain distinguishable. Their labels describe the series being retrieved; they do not establish historical membership for every year. Do not silently choose a regional variant or derive a regional statistic by averaging countries.

**Dimensions.** `Dim1`, `Dim2`, and `Dim3` have indicator-specific meanings. Use verified dimension types and values, retain source codes, and avoid merging rows that differ in strata. Observing a code separately does not establish that every possible combination exists.

**Missingness.** Missing data, suppressed values, source text values, and retrieval failures have different meanings. Preserve the reported text, use source numeric fields where available, and do not turn missing observations into zero. A complete request means the selected source response was retrieved; it does not prove full country-year coverage.

## Execution and distribution boundary

The same skill folder can be copied into a local Codex skill directory or used as the content of a future skills-only plugin. Installation provides instructions and files. The agent host supplies Python, command execution, filesystem access, and network permissions.

Local installation copies files to `~/.agents/skills/dsir-gho` and refuses to overwrite an existing directory. The installers do not install a runtime, alter shell security settings, or grant network access. A custom installation root is supported for isolated verification.

For ChatGPT Work, direct HTTPS access requires permitted code/shell networking. Public browsing access is a separate capability. Ordinary chat attachments and Custom GPT Knowledge uploads are not represented as skill installation. See [execution environments](references/execution_environments.md) for the verified platform guidance.

## Verification and reproducibility

Offline tests should cover parsing and cleaning, location ambiguity, catalogue matching, pagination and failure behavior, export structure, and missing metadata. Live checks should use small source queries to verify end-to-end behavior, including UHC country observations and distinct WPR variants. Expected live values belong in validation records, never as fallback observations in runtime code.

For an analytical result, retain all three data files and their checksum manifest. Record the selected indicator and geography variant in any downstream chart or table. A later run can return revised observations; use the recorded retrieval time and request details when comparing snapshots.

Tests of this client establish implementation behavior in the tested environment. They do not establish that every recipient's ChatGPT account can install a skill or run network-enabled Python.

## Known limitations in version 0.1.0

- Installation in ordinary ChatGPT is not guaranteed. An execution-capable skill host with Python and WHO HTTPS access is required. The release is locally installable in Codex; a public ChatGPT plugin has not been submitted or published.
- WHO's legacy notice announced retirement of this OData API. It remained available in the recorded live tests. An endpoint or schema change can require a client update; failed requests cannot provide new observations.
- The API does not publish complete clinical definitions and units in its basic catalogue. Three reviewed WHO metadata notes supplement explicit name-based units. Other unavailable fields stay null, and notes can become stale.
- All-year requests mean every observation returned for that selection, not a promise of annual completeness or data for the current calendar year. Historical releases can change; row-count snapshots in test reports are dated evidence.
- DSIR's country table is a versioned 194-Member snapshot. Live GHO reporting areas are broader. Preserve a non-Member location's null DSIR ISO3/name while using the live resolver label separately.
- The skill retrieves official regional series and explains variants. It does not reconstruct year-specific membership or calculate a regional estimate from country values. Historical membership questions that materially affect interpretation need clarification.
- Pagination verifies counts, detects repeated observation IDs, validates links and enforces explicit resource limits. WHO does not provide a transaction snapshot token: a release changed mid-query without a count change could still require a repeat pull.
- There is no permanent observation or catalogue cache. Each CLI process verifies fresh metadata; this increases requests but avoids silent reuse of stale catalogues. `describe` can be slower for indicators with many observations.
- Automated evaluation checks function contracts. The separate Codex agent rehearsal provides natural-language evidence for five main questions. It is not a cross-platform or multi-model evaluation; other response-review cases remain pending.
- The runtime excludes modelling, charts and generated estimates. WHO-published estimated series are allowed and identified as estimates made by WHO.

## Suggested next version

1. Test installation, script execution and HTTPS access in the intended colleagues' actual ChatGPT Work environment. Record the environment and permission outcome before making distribution promises.
2. If that environment supports it, package the same files as a skills-only plugin and follow the platform's publishing review. This does not require an MCP or R server.
3. Monitor WHO's documented successor API and add an adapter only after verifying catalogue, geography, unit and observation parity. Keep GHO as the sole data scope.
4. Add a small, reviewed metadata expansion with explicit version dates; extend aliases only from failed real questions and verified catalogue entries.
5. Run the full natural-language casebook against the chosen GPT host, retaining responses and tool outputs. Add coverage checks for requested dimension combinations and larger pulls using evidence from actual failures.
