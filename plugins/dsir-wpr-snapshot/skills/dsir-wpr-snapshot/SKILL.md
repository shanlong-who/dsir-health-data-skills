---
name: dsir-wpr-snapshot
description: Look up or compare tuberculosis incidence and WHO/UNICEF DTP3 coverage by country, area and year in dated Western Pacific snapshots. Also use for coverage limits, latest common years, source metadata and CSV downloads.
---

# Western Pacific indicator snapshots

Read the [indicator catalog](https://raw.githubusercontent.com/shanlong-who/dsir-health-data-skills/refs/heads/pilot/wpr-multi-phase3/snapshots/catalog.json). Resolve each requested measure separately by indicator name, aliases and code. For "both indicators", use both catalog entries. Clarify ambiguities such as an unspecified vaccine or TB measure. Identify unsupported indicators explicitly.

Follow each matched entry's manifest URL and check its indicator, run ID, unit, retrieval time and geography. Use the pinned URLs for the rest of the answer. In each manifest find the requested area in `geography.areas`. Distinguish an area outside the roster, an area with no observations, an absent year, and a reported zero. A place can have TB data and no DTP3 data. Current WPR membership applies to historical observations; regional aggregates require a separately published series.

Read each area's `observations.url` and filter by `area_code`, indicator code and year. If that file is inaccessible, try the same manifest's `files.observations.url`. Read actual rows before giving numbers. Use the manifest's provenance URL for source questions. If a required file remains inaccessible, identify the file and give only verified results. Do not fill gaps from a different source or estimate type.

For a latest query, take the maximum year with a nonmissing point estimate for each requested indicator separately. For the latest common year, intersect the years having nonmissing estimates in all requested series at this place; take the maximum of that intersection and look up each value again in that year. Gaps can occur within either series. If the intersection is empty, say so. Do not derive a common year from global date ranges. Compare years side by side and preserve each indicator's denominator. Do not subtract or sum percentages and per-population incidence rates.

Report observation year, value, native unit, reported bounds and the retrieval date for each source. For DTP3 use the WHO/UNICEF estimated share of one-year-olds with three DTP doses. Label missing bounds as unreported. Leave zero distinct from missing. For TB report cases per 100,000 population. Describe "latest" as latest in these dated snapshots. Link each CSV actually used and provide the catalog, manifest, provenance or observation IDs on request. Distinguish recorded checksums from hashes computed on downloaded bytes.
