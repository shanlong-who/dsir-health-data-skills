# WHO API and metadata audit

Verified on 9 September 2026 using public WHO endpoints. This document records observations; the skill must refresh metadata and data at execution time. Files in `reports/` and the development `.runtime/new-gho-audit/` directory are test evidence, never runtime indicator data.

## Current endpoints and lifecycle

The following endpoints returned HTTP 200:

| Endpoint | Observed content |
| --- | --- |
| `https://ghoapi.azureedge.net/api/Indicator` | 3,098 codes, names and languages |
| `https://ghoapi.azureedge.net/api/Dimension` | 202 dimension types |
| `https://ghoapi.azureedge.net/api/DIMENSION/COUNTRY/DimensionValues` | 234 country/area codes, titles and parent regions |
| `https://ghoapi.azureedge.net/api/DIMENSION/REGION/DimensionValues` | 43 regional and aggregate groups |
| `https://ghoapi.azureedge.net/api/Indicator('UHC_INDEX_REPORTED')` | One catalogue entity |
| `https://ghoapi.azureedge.net/api/Indicator('UHC_INDEX_REPORTED')/Dimensions` | Declared dimensions |
| `https://ghoapi.azureedge.net/api/UHC_INDEX_REPORTED` | Observation collection |
| `https://ghoapi.azureedge.net/api/$metadata` | OData entity schema, about 12 MB |

The [official API documentation](https://www.who.int/data/gho/info/gho-odata-api) still links this service. The [WHO legacy notice](https://www.who.int/data/gho/legacy) says Athena is retired and announced GHO OData deprecation near the end of 2025. The OData endpoint remained operational during this audit. An Athena JSON request returned HTML. No replacement endpoint or continuity guarantee was inferred from the notice.

## Response schemas and paging

Catalogue entries contain `IndicatorCode`, `IndicatorName`, and `Language`; they do not contain clinical definitions or units. A keyed indicator request returns the entity directly, without `value`. `/Dimensions` returns `value` entries containing `IndicatorCode`, `Language`, `Dimension`, and `DimensionName`. `$expand=Dimensions` works on an indicator catalogue query.

Dimension-value rows contain `Code`, `Title`, `ParentDimension`, `Dimension`, `ParentCode`, and `ParentTitle`. UHC declares `PUBLISHSTATE`, `WORLDBANKINCOMEGROUP`, `WORLDBANKREGION`, `COUNTRY`, `REGION`, and `YEAR`. Declared dimensions do not mean that each observation has all those fields populated.

Observation fields include `Id`, `IndicatorCode`, `SpatialDimType`, `SpatialDim`, `ParentLocationCode`, `ParentLocation`, `TimeDimType`, `TimeDim`, `TimeDimensionValue`, `TimeDimensionBegin`, `TimeDimensionEnd`, `Dim1Type`/`Dim1` through `Dim3Type`/`Dim3`, `DataSourceDimType`, `DataSourceDim`, `Value`, `NumericValue`, `Low`, `High`, `Comments`, and `Date`. Preserve their original content alongside the 15-column DSIR view.

Live checks confirmed `$filter`, `and`, `or`, parentheses, `$orderby`, `$count=true`, `$top`, and `$skip`. Lowercase `contains(IndicatorName,'measles')` matched capitalized titles. A catalogue request with `$top=2&$count=true` returned two records and count 3098 without a next link; `$skip=2` returned the next two records. `Prefer: odata.maxpagesize=2` was ignored. Therefore a limited response without `@odata.nextLink` is not evidence that the complete collection was returned. Use stable ordering, a verified total, and managed paging when requesting a limited page; follow a valid next link when supplied.

Current SEX values are `SEX_BTSX`, `SEX_FMLE`, `SEX_MLE`, and `SEX_NOA`. A PHL life-expectancy query using `BTSX` returned zero records; the current `SEX_BTSX` returned 22. Other dimensions also use prefixes, for example `AGEGROUP_YEARS18-PLUS`. Resolve labels against the live codelist; do not copy obsolete examples blindly.

## Official regional results and Indonesia

`SpatialDimType='REGION'` and `SpatialDim='WPR'` returned an official UHC SCI series for every year 2000–2023: 24 records, 63 in 2000 and 81 in 2023. A separate official `WPR_WO_IDN` series also contains 24 years, with 65 in 2000 and 83 in 2023. Both had source update timestamp `2025-12-05T18:39:13.277+08:00` and null disaggregation fields.

The live region codelist names `WPR_WO_IDN` "Western Pacific without Indonesia" and `SEAR_W_IDN` "South-East Asia with Indonesia". Country `IDN` currently has parent `WPR`, even in observations for 2000. This current parent relationship is not a history of membership. A current-membership country selection must be labelled as such; use the requested official aggregate directly when available.

[WHO SEARO history](https://www.who.int/southeastasia/about/history) states that Indonesia moved on 23 May 2025. The [Indonesian Ministry of Health announcement](https://kemkes.go.id/id/indonesia-resmi-pindah-dari-who-south-east-asia-ke-western-pacific-regional-office) explicitly describes 23 May as the effective date. The formal [WHA78.25 resolution](https://apps.who.int/gb/ebwha/pdf_files/WHA78/A78_R25-en.pdf) was adopted on 27 May 2025. Retain both dates with their distinct meanings. A [WHO announcement](https://www.who.int/indonesia/news/detail/11-06-2025-welcoming-a-new-family-member--indonesia-s-flag-is-raised-at-the-who-western-pacific-regional-office) describes the June flag-raising ceremony; that ceremony is not the reassignment effective date.

The API codelist returned 35 WPR country/area locations, whereas the WHO announcement describes Indonesia and 37 other Member States and areas. Do not present API catalogue coverage as a complete institutional membership list. UHC had country observations for 28 of the current API WPR locations.

## Verified indicators and observed query coverage

The table summarizes complete queries for `PHL` or `WPR`. Year ranges are the union of those query results, not guaranteed global ranges. All requests returned HTTP 200. Counts are observations, including disaggregated rows.

| Catalogue code | Meaning | PHL/WPR rows | WPR rows | Observed years |
| --- | --- | ---: | ---: | --- |
| `UHC_INDEX_REPORTED` | UHC Service Coverage Index (SDG 3.8.1) | 48 | 24 | 2000–2023 |
| `WHS3_62` | Measles reported cases | 98 | 46 | 1974–2025 |
| `FINPROTECTION_CATA_TOT_10_POP` | Reported household health spending >10%, percentage | 55 | 0 | 1997–2015 |
| `FINPROTECTION_CATA_TOT_10_LEVEL_SH` | Estimated household health spending >10%, percentage | 6 | 6 | 2000–2019 |
| `FINPROTECTION_CATA_TOT_10_LEVEL_MILLION` | Estimated household health spending >10%, millions | 6 | 6 | 2000–2019 |
| `MDG_0000000020` | TB incidence per 100,000 per year | 50 | 25 | 2000–2024 |
| `TB_e_inc_num` | Incident TB case count | 50 | 25 | 2000–2024 |
| `TB_e_inc_tbhiv_100k` | HIV-positive TB incidence rate | 48 | 24 | 2000–2023 |
| `TB_e_inc_tbhiv_num` | HIV-positive incident TB count | 50 | 25 | 2000–2024 |
| `TB_Notification_agesex_num` | Detected new/relapse TB cases, age/sex | 26 | 0 | 2021 |
| `WHOSIS_000001` | Life expectancy at birth, years | 132 | 66 | 2000–2021 |
| `NCD_BMI_30A` | Adult obesity, age-standardized percentage | 270 | 135 | 1980–2024 |
| `GHED_CHE_pc_US_SHA2011` | Current health expenditure per capita, US dollars | 48 | 24 | 2000–2023 |
| `HWF_0001` | Medical doctors per 10,000 | 24 | 1 | 2000–2024 |
| `SA_0000001688` | Alcohol consumption, litres, three-year average | 50 | 25 | 2000–2024 |
| `WHS8_110` | Measles first-dose immunization coverage | 52 | 26 | 2000–2025 |
| `NUTRITION_ANAEMIA_REPRODUCTIVEAGE_PREV` | Anaemia prevalence in women of reproductive age | 144 | 72 | 2000–2023 |

The TB catalogue also contains `WHS3_522` (reported TB cases), and `TB_tot_newrel` and `TB_c_newinc`, which share the title "Tuberculosis - new and relapse cases". A general TB request requires clarification of rate, count, HIV population and notifications versus estimated incidence. Measles `WHS3_62` must not be confused with vaccination coverage `WHS8_110` or `MCV2`.

Reported financial hardship in PHL includes residence, household composition, household-head sex/age and survey data sources. Its observed national total uses `RESIDENCEAREATYPE_TOTL`; do not require all dimensions to be null. Estimated percentage and estimated millions are separate indicators. The absence of WPR rows in the reported indicator is not a network failure, and does not imply that the estimated percentage has no WPR data.

## Rich metadata and limitations

- [UHC metadata, IMR 4834](https://www.who.int/data/gho/indicator-metadata-registry/imr-details/4834): a unitless 0–100 index; regional aggregates use tracer indicators and corresponding denominators. An average of country indices is not the official regional method.
- [Measles metadata, IMR 60](https://www.who.int/data/gho/data/indicators/indicator-details/GHO/measles---number-of-reported-cases): reported cases compiled from surveillance, with regional totals calculated by summation.
- [TB incidence metadata, IMR 20](https://www.who.int/data/gho/data/indicators/indicator-details/GHO/incidence-of-tuberculosis-%28per-100-000-population-per-year%29): estimated incidence includes HIV-positive cases; counts and population-based rates are distinct measures.

Metadata pages and underlying observations can have different update schedules. For example, the TB-HIV rate probe ended in 2023 while the corresponding count ended in 2024. Never infer the latest year for one series from another. The English `data.who.int/indicators/i/B6D043E/A65146D` route returned 404 during this audit; a search hit for another language is not proof that the English page works.
