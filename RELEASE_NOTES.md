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
