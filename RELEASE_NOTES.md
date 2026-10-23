# GHO Phase 1 repair — unreleased, 23 October 2026

The current source defaults to legacy, matching released DSIR 0.11.0 when its
session option is unset. Select xMart explicitly with `--backend xmart`; no
automatic fallback occurs. Legacy pages default to 1,000 rows and xMart pages
to 5,000. The existing commands and 15-column exports remain available.

Repair backend-specific catalogue provenance, selected-route metadata, valid
numeric/dotted codes, dimension validation and incomplete-response checks.
Distinguish verified catalogue absence, empty observations, invalid selections,
network/HTTP failures and malformed or incomplete retrieval. Preserve
`response.json` and raw source evidence with CSV exports. The R comparison tool
requires separate review of definitions, dimensions and releases before matching
observations across backends.

Validation: 114 GHO unit tests, 10 offline scenarios, 58 R comparison assertions,
13 bounded live cases, a local plugin CLI check and independent same-backend
DTP3 comparisons passed. The housekeeping run also passed all 69 unchanged SDG
tests. See the [Phase 1 report](dsir-gho/reports/phase1-20261023.md) for exact scope
and timestamps. Cross-backend equivalence and general catalogue coverage are
not established; user-facing acceptance remains pending.

This is a source update. Version strings still identify the previous packaging
baseline; no release ZIP, installed plugin or SDG implementation was changed.
Historical pinned DSIR hashes and release evidence retain their original scope.
The [Phase 2 assessment](PHASE2.md) contains recommendations only.

# GHO listing and privacy update — 7 October 2026

Pre-release `v2026.10.07.1` contains GHO plugin 0.1.3. The subtitle is now
`Find and download WHO GHO data` (30 characters), the category is `Data & Analytics`,
and both manifests include the public website, privacy policy and support links.
The listing explains the plugin's data purpose and existing live-validation limits.
The static policy website is published from `main:/docs` on GitHub Pages.

The GHO 0.1.1 runtime is unchanged and byte-identical to the prior standalone ZIP.
No API behavior, output contract or SDG files changed. The 0.1.2 assets and prior
release remain intact. This listing update does not resolve the pending complete
live retrieval or independent live parity checks documented below.

# GHO xMart maintenance candidate — 7 October 2026

Candidate collection: `v2026.10.07`. GHO plugin 0.1.2; GHO skill 0.1.1.
Author and maintainer: Shanlong Ding (`shanlong-who`).
GitHub publication status: pre-release; complete live validation remains pending.

The GHO default backend now follows DSIR 0.11.0 at commit
`885464b1fade2f8b6d02dde93f9080e4b3f4f2a5`: public xMart directory discovery,
production RELAY routes, read-only long queries, stable counted/grouped pagination,
native named dimensions, wide/long normalization and source provenance.

The 15-column CSV contract remains unchanged. Native xMart records are exported
as `source_raw.json`; normalized observations remain in `raw.json`. Missing
numeric data and unknown metadata remain missing. Original labels and all source
dimensions are preserved outside the core table. Ambiguous measure families and
incomplete retrievals are errors.

Legacy GHO requires an explicit `--backend legacy` selection and is recorded in
provenance. xMart errors do not trigger fallback. GHE is outside the GHO plugin.
The SDG component and its 0.1.0 runtime assets are unchanged.

Offline GHO tests, retained legacy failure contracts and 13 pinned-source
common-input R comparisons passed. All 194 country rows match the pinned RDA.
Fresh live checks reached three incomplete one-row JSON probes, but complete
queries and the directory redirected to WHO's sorry page. Seventeen independent
live parity comparisons remain unverified.

These packages are published as maintenance candidates. They do not establish
successful complete live retrieval. Rerun the live checks, independent parity and
extracted runtime validation before promoting a stable release. Checksums identify the
exact candidate files; they do not establish upstream availability.
