# Live UN SDG API inspection

Inspected on 2026-09-16. Endpoint:
`https://unstats.un.org/sdgs/UNSDGAPIV5/v1/sdg/`.
Live catalogue release: `2026.Q2.G.02`. Raw evidence and exact request hashes are
in `reports/live/catalogues.json`, query result files and parity reports. These
snapshots are development evidence only, excluded from installed runtime ZIPs.

## Observed structure

- Indicator/List: 251 entries, with indicator code, description, goal, target,
  tier and nested series descriptions.
- Series/List: 713 entries, linked indicator lists and a release identifier.
- GeoArea/List: 460 country, territory and aggregate group records, using numeric
  string codes. The list contains extended codes longer than three digits.
- Indicator/Data: `size`, `totalElements`, `totalPages`, `pageNumber`, dimension
  and attribute code lists, and `data` records. A seven-row page-size test
  retrieved 72 UHC country observations through 11 pages, confirming the final
  count and full time coverage.
- Series/{code}/Dimensions and /Attributes: code lists with both API `code` and
  SDMX aliases. The aliases need not equal observation dictionary values.

## Decisions supported by the responses

UHC indicator 3.8.1 currently links to `SH_ACS_UNHC_25`, labelled 2025 methodology.
China, Japan and the Philippines each returned 24 annual observations covering
2000-2023. This is the current-release historical series, not a reconstruction
of what each earlier release would have reported.

WHO Western Pacific resolves to area 99047 in the catalogue, but this release
returned no UHC rows for that group. A successful global UHC probe reported
5,184 rows. This is `filters_no_data`, not an invalid location, service failure,
or globally unavailable indicator. Do not substitute another regional group.

SDG 3.8.2 currently links to `SH_OOP_XPD_EARNNET40`: a 40% household discretionary
budget definition. It must not answer an older 10%/25% total household-budget
question by substitution.

The Philippine TB series returned only Reporting Type in its observation
dimensions, despite series metadata advertising Age/Sex/Location code lists.
Adding those absent dimension keys removes all rows. Code-list availability is
not proof that a field is populated in a particular area. Inspect raw contexts
and preserve user-requested population restrictions explicitly.

The suicide series uses FEMALE/MALE in the JSON observations; metadata also
contains F/M as SDMX aliases. Local filtering must use the JSON API codes.

## Execution limits

This machine's restricted sandbox initially refused outbound connections.
Approved read-only network execution reached the same public UN service. That
does not prove all ChatGPT accounts permit script networking. The skill reports
this distinction, and its doctor command verifies the actual host at runtime.
