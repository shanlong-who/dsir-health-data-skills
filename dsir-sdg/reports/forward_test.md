# Independent forward test of dsir-sdg

Test date: 2026-09-16. Live catalogue release: `2026.Q2.G.02`.

The tester received five natural-language requests, read the skill and its three
referenced rule/schema documents, and used its client against the real public UN
SDG API. No other agent's report, answer, or intended result was read. The tester
did not change implementation files. Two defects were reported to the parent
agent, and the parent's subsequent fixes were retested separately below.

## Runtime and evidence

- Working directory: `<validation-workspace>`.
- Existing interpreter: `<maintainer-home>/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`.
- `doctor` reported Python `3.12.14`, `indicator_count=251`, `r_required=false`.
- Initial sandbox networking failed after three attempts with `un_api_request_failed`
  and Windows connection refusal. The identical read-only check succeeded with
  approved network access. This was an execution limitation, not missing UN data.
- All outputs are under `reports/forward/`. Nothing was installed or published.
- `response.json` and the complete `observations.csv` were read for interpretation;
  the eight-row CLI preview was not treated as the full result.
- All 16 manifest hashes and all four JSON/CSV/context row-count checks passed;
  see `forward/23-artifact-checks.json`.

Command notation below: `P` means the interpreter path above, and `C` means
`dsir-sdg/scripts/cli.py`. Commands were run as PowerShell `& 'P' 'C' ...`, with
`2>&1 | Tee-Object -FilePath 'dsir-sdg/reports/forward/NAME'` to retain output.
Where shown, `-X utf8` was between `P` and `C`; it was a temporary workaround
before the parent fixed the CLI. Numbers identify retained logs, not inferred steps.

| Log | Actual client arguments | Outcome |
|---|---|---|
| 00-doctor.txt | `doctor` | Network failure in sandbox |
| 01-doctor-network.txt | `doctor` | `ok`, 251 indicators |
| 02-search-uhc.json | `search "UHC SCI"` | One matching series |
| 03-locations-wpro.json | `locations "Western Pacific Region"` | `99047`, WHO Western Pacific |
| 04-search-tb.json | `search "tuberculosis incidence"` | Indicator and series found |
| 05-search-catastrophic.json | `search "catastrophic health expenditure above 10%"` | `no_matches`; threshold warning |
| 06-search-child.json | `search "child mortality"` | Initially `no_matches` |
| 07-locations-countries.json | `locations China Japan Philippines` | `156`, `392`, `608` |
| 08-describe-uhc.json | `describe 3.8.1` | 2025 methodology, index unit |
| 09-describe-tb.json | `describe 3.3.2` | Incidence per 100,000 population |
| 10-describe-financial.json | `describe 3.8.2` | 40% discretionary-budget measure |
| 11-search-mortality.json | `search mortality` | Initially Unicode output error |
| 12-search-financial.json | `search "health expenditures"` | Revised indicator/series found |
| 13-get-wpro.json | `-X utf8 C get 3.8.1 --locations WPRO --series SH_ACS_UNHC_25 --output-dir dsir-sdg/reports/forward/wpro-uhc` | `filters_no_data` |
| 14-get-comparison.json | `-X utf8 C get 3.8.1 --locations CHN JPN PHL --series SH_ACS_UNHC_25 --output-dir dsir-sdg/reports/forward/country-uhc` | 72 rows, QA pass |
| 15-get-tb.json | `-X utf8 C get 3.3.2 --locations PHL --series SH_TBS_INCD --year-from 2015 --dimension "Sex=BOTHSEX" --dimension "Age=ALLAGE" --dimension "Location=ALLAREA" --output-dir dsir-sdg/reports/forward/phl-tb` | `filters_no_data` after retrieving 25 rows |
| 16-search-mortality-utf8.json | `-X utf8 C search mortality` | 19 matches; ten displayed |
| 17-get-tb-no-dimensions.json | `-X utf8 C get 3.3.2 --locations PHL --series SH_TBS_INCD --year-from 2015 --output-dir dsir-sdg/reports/forward/phl-tb-inspect` | 10 rows, QA pass |
| 18-describe-child.json | `-X utf8 C describe 3.2.1` | Four series: two ages, rates and counts |
| 19-describe-neonatal.json | `-X utf8 C describe 3.2.2` | Neonatal rate and count |
| 20-search-10pct.json | `-X utf8 C search "10%"` | Nine lexical matches; none is the requested measure |
| 21-search-mortality-fixed.json | `search mortality` | Plain interpreter succeeds after fix |
| 22-search-child-fixed.json | `search "child mortality"` | Three matches after alias fix |

For rows 13–20, the `C` token is shown explicitly to make the position of
`-X utf8` unambiguous; all other rows list only the arguments following `C`.
The retained logs are exact client stdout. Describe summaries printed separately
to the terminal were depth-limited for display, but the retained JSON is complete.

## 1. Western Pacific UHC SCI, all available years

Request: “请帮我从联合国SDG数据库查询西太平洋区域UHC Service Coverage Index历年来的结果。”

Selection: indicator `3.8.1`, **Coverage of essential health services**; series
`SH_ACS_UNHC_25`, **Universal health coverage (UHC) service coverage index, 2025
methodology**. Geography resolves exactly to `99047`, **WHO Western Pacific**.
No year bounds or country-derived aggregation were used.

Exact result fields from `forward/wpro-uhc/response.json`:

```json
{
  "status": "filters_no_data",
  "row_count": 0,
  "retrieved_row_count": 0,
  "pages": 1,
  "coverage_by_location": [{"location": "99047", "years": [], "row_count": 0}],
  "qa.status": "warning",
  "qa.issues[0].code": "locations_without_data",
  "baseline_probe.global_indicator_rows": 5184
}
```

The region-scoped request succeeded and returned zero rows. A separate global
probe confirmed 5,184 indicator observations. This is absent coverage for this
regional scope, not `indicator_no_data` and not an API outage.

Clarification required: **yes, before changing scope**. Ask whether individual
member-country results are acceptable. Regional membership in the current
release does not reconstruct historical membership.

Chinese answer:

> 我已核对联合国 SDG 数据库。UHC SCI 对应指标 3.8.1（基本卫生服务覆盖），当前序列为 `SH_ACS_UNHC_25`，采用 2025 年方法，单位为指数。西太平洋区域解析为 WHO Western Pacific（99047），但当前发布没有该地区的 UHC SCI 观测值；同一指标在全球范围有数据。因此无法从这次查询列出西太区历年地区值，也不能用其他地理分区或国家简单平均代替。检索日期为 2026-09-16。您是否希望改为查看西太区成员国的历年结果？若需要按历史成员构成汇总，还需明确成员范围。

[Actual regional data query](https://unstats.un.org/sdgs/UNSDGAPIV5/v1/sdg/Indicator/Data?indicator=3.8.1&pageSize=1000&areaCode=99047&page=1).
The exported `forward/wpro-uhc/observations.csv` is empty and is evidence of this
query, not a usable regional time series.

## 2. China, Japan and Philippines UHC SCI over time

Request: “比较中国、日本和菲律宾历年的UHC SCI。”

Selection: the same verified indicator and 2025-methodology series as case 1.
Areas: China `156` / `CHN`, Japan `392` / `JPN`, Philippines `608` / `PHL`.

Exact result: `status=ok`, `row_count=72`, `retrieved_row_count=72`, `pages=1`,
`qa.status=pass`, `qa.issues=[]`, `qa.missing_numeric=0`. Each country has exactly
24 observations, every year from 2000 through 2023. All contexts contain
`dimensions={"Reporting Type":"G"}` and
`attributes={"Nature":"E","Units":"INDEX"}`. The unit is an index, not a
percentage. No age or sex breakdown is present. All uncertainty bounds are null.
Observation source: `WHO Global Health Observatory (GHO),December 2025 update`.
Access was through UN SDG, not a direct GHO query.

Clarification required: **no**. The ordinary UHC service-coverage comparison
clearly maps to the catalogue's single current series; the method is disclosed.

Chinese answer:

> 已取得中国、日本和菲律宾 2000—2023 年的完整 UHC SCI 序列，均采用联合国当前的 2025 年方法（SDG 3.8.1，`SH_ACS_UNHC_25`）。2023 年日本为 86、中国为 85、菲律宾为 69；较 2000 年分别提高 10、21 和 13 个指数点。日本在全部观测年份均高于另两国，中国与日本的差距缩小。数值单位为指数，非百分比；API 未提供这些值的不确定性上下限。以下保留原始数值文本。

| Year | China | Japan | Philippines |
|---|---:|---:|---:|
| 2000 | 64 | 76 | 56 |
| 2001 | 64 | 77 | 56 |
| 2002 | 65 | 77 | 57 |
| 2003 | 66 | 78 | 57 |
| 2004 | 67 | 78 | 57 |
| 2005 | 68 | 79 | 58 |
| 2006 | 69 | 79 | 59 |
| 2007 | 70 | 80 | 59 |
| 2008 | 71 | 80 | 62 |
| 2009 | 72 | 80 | 61 |
| 2010 | 73 | 81 | 59 |
| 2011 | 74 | 81 | 63 |
| 2012 | 75 | 82 | 64 |
| 2013 | 77 | 82 | 65 |
| 2014 | 78 | 82 | 66 |
| 2015 | 79 | 82 | 66 |
| 2016 | 80 | 83 | 68 |
| 2017 | 81 | 83 | 68 |
| 2018 | 81 | 84 | 67 |
| 2019 | 82 | 84 | 66 |
| 2020 | 83 | 84 | 69 |
| 2021 | 84 | 85 | 68 |
| 2022 | 84 | 85 | 69 |
| 2023 | 85 | 86 | 69 |

> 来源：联合国 SDG 数据库，原始来源字段为 WHO GHO 2025 年 12 月更新；检索日期 2026-09-16。三国记录均为全球报告口径的国家估计，未细分年龄或性别。最新观测年为 2023 年，不能当作 2026 年值；也不应与旧方法直接拼接。

[Actual three-country query](https://unstats.un.org/sdgs/UNSDGAPIV5/v1/sdg/Indicator/Data?indicator=3.8.1&pageSize=1000&areaCode=156&areaCode=392&areaCode=608&page=1).
Complete export: `forward/country-uhc/observations.csv`.

## 3. Philippines TB incidence since 2015

Request: “菲律宾2015年以来的TB incidence是多少？”

Selection: `3.3.2`, **Tuberculosis incidence per 100,000 population**;
`SH_TBS_INCD`, **Tuberculosis incidence (per 100,000 population)**; Philippines
`608` / `PHL`; inclusive `year_from=2015`.

The first query applied catalogue-advertised `Sex=BOTHSEX`, `Age=ALLAGE`, and
`Location=ALLAREA`. It retrieved 25 rows but filtered every row out. The unfiltered
stratum inspection revealed that actual records only contain
`dimensions={"Reporting Type":"G"}`. The presence of codes in series metadata
does not prove they are populated in every observation. Retrying without these
extra dimension filters was necessary; no user-facing no-data conclusion was made.

Final exact fields: `status=ok`, `row_count=10`, `retrieved_row_count=25`,
`pages=1`, `coverage_by_location[0].years=[2015,...,2024]`, `qa.status=pass`,
`qa.issues=[]`, `qa.missing_numeric=0`. All attributes are
`{"Nature":"G","Units":"PER_100000_POP"}`. Footnote:
`Data extracted as of 2026-01-05 based on data originally compiled for the 2025 WHO Global TB Report`.

Clarification required: **no**. The conventional TB incidence rate is the exact
catalogue match and the denominator is stated.

Chinese answer:

> 菲律宾 2015 年以来的结核病发病率如下，单位为每 10 万人口。采用 SDG 3.3.2、序列 `SH_TBS_INCD`。截至本次查询，最新观测为 2024 年：625，API 给出的下限和上限为 344—1020。表中保留原始数值文本和返回的上下限；接口材料未注明这些区间的置信水平，故不额外标注为 95% 区间。

| Year | Value | Lower bound | Upper bound |
|---|---:|---:|---:|
| 2015 | 550 | 309 | 860 |
| 2016 | 554 | 311 | 866 |
| 2017 | 554 | 311 | 866 |
| 2018 | 554 | 311 | 866 |
| 2019 | 554 | 311 | 866 |
| 2020 | 544 | 304 | 863 |
| 2021 | 579 | 325 | 934 |
| 2022 | 627 | 346 | 1010 |
| 2023 | 632 | 348 | 1020 |
| 2024 | 625 | 344 | 1020 |

> 这些是全国层面的全球监测记录，API 观测仅标注 `Reporting Type=G`，未提供年龄或性别拆分。来源为联合国 SDG 数据库，原始来源注明 WHO Global Tuberculosis Report 2025；源数据提取日期为 2026-01-05，本次检索日期为 2026-09-16。

[Actual Philippines TB query](https://unstats.un.org/sdgs/UNSDGAPIV5/v1/sdg/Indicator/Data?indicator=3.3.2&pageSize=1000&areaCode=608&page=1).
The year constraint is applied locally after complete retrieval.
Complete verified export: `forward/phl-tb-inspect/observations.csv`.

## 4. Philippines catastrophic health expenditure above 10%, since 2015

Request: “请查询菲律宾2015年以来catastrophic health expenditure above10%的比例。”

Live search returned `status=no_matches`, `total_matches=0` for the exact concept.
Broader discovery and `describe 3.8.2` verified the current definition:

- Indicator `3.8.2`: **Proportion of population with positive out-of-pocket household expenditures on health exceeding 40 per cent of household discretionary budget**.
- Only current series: `SH_OOP_XPD_EARNNET40`.
- Series description: **Proportion of the population with positive out-of-pocket household expenditure on health exceeding 40% of household discretionary budget, by location, quintile, type of household and characteristics of the head of household (%)**.
- Unit metadata: `PERCENT` / Percentage.
- Methodological full definition: `definition=null`; inspect official metadata
  for additional interpretation, rather than inferring from a code.

The additional literal `search "10%"` returned unrelated lexical matches, such as
health-worker density per 10,000 population. These were correctly rejected.
No data query for the revised measure was presented as answering the requested
10% measure. No requested observation export was created.

Clarification required: **yes**. Confirm the 10% denominator and whether to use
another source for the older measure or change to the current measure.

Chinese answer:

> 目前不能把联合国当前 3.8.2 数据直接作为您要的“超过 10%”结果。2026-09-16 核对的现行目录中，3.8.2 已改为“家庭自付卫生支出超过家庭可自由支配预算 40% 的人口比例”（`SH_OOP_XPD_EARNNET40`，单位为 %）。阈值和分母都与“超过家庭总支出或收入 10%”不同。您这里的 10% 是指家庭总支出或收入吗？如是，应继续找该旧口径的其他数据来源；若您希望改用现行 40% 口径，可另行查询菲律宾 2015 年以来的数据。

[Live indicator catalogue queried](https://unstats.un.org/sdgs/UNSDGAPIV5/v1/sdg/Indicator/List),
[live series catalogue queried](https://unstats.un.org/sdgs/UNSDGAPIV5/v1/sdg/Series/List).

## 5. Philippines child mortality

Request: “菲律宾儿童死亡情况怎样？”

This is materially ambiguous: age definition, rate versus count, and time period
are unspecified. Discovery must not turn a keyword score into metric selection.

The original `search "child mortality"` returned no matches. A broader mortality
search located relevant indicators, and `describe` verified these six distinct
series:

| Indicator | Series | Official description | Unit |
|---|---|---|---|
| 3.2.1 | SH_DYN_MORT | Under-five mortality rate, by sex (deaths per 1,000 live births) | PER_1000_LIVE_BIRTHS |
| 3.2.1 | SH_DYN_MORTN | Under-five deaths (number) | NUMBER |
| 3.2.1 | SH_DYN_IMRT | Infant mortality rate (deaths per 1,000 live births) | PER_1000_LIVE_BIRTHS |
| 3.2.1 | SH_DYN_IMRTN | Infant deaths (number) | NUMBER |
| 3.2.2 | SH_DYN_NMRT | Neonatal mortality rate (deaths per 1,000 live births) | PER_1000_LIVE_BIRTHS |
| 3.2.2 | SH_DYN_NMRTN | Neonatal deaths (number) | NUMBER |

Metadata offers both sexes and female/male categories. The definitions and
available years are null in `describe`; coverage requires an observation query.
No mortality series was silently selected and no numerical answer was invented.

Clarification required: **yes**. Ask age/statistic/time selection, offering the
standard under-five rate as a possible choice. A later search alias returning
the under-five series still does not resolve the user's ambiguity.

Chinese answer:

> 联合国 SDG 数据库有几种不同的“儿童死亡”指标：5 岁以下死亡率或死亡人数（3.2.1），婴儿死亡率或死亡人数（同属 3.2.1），以及新生儿死亡率或死亡人数（3.2.2）。死亡率的分母是每 1,000 活产，人数则是死亡总数，不能混用。您希望看哪一种，以及最新年份还是历年趋势？若是总体比较，建议先看菲律宾男女合计的 5 岁以下死亡率 `SH_DYN_MORT`。目录核对日期为 2026-09-16；待口径明确后再核对实际年份和观测值。

[Live indicator catalogue queried](https://unstats.un.org/sdgs/UNSDGAPIV5/v1/sdg/Indicator/List),
[under-five dimension metadata queried](https://unstats.un.org/sdgs/UNSDGAPIV5/v1/sdg/Series/SH_DYN_MORT/Dimensions).

## Defects, recovery and verification

1. **Windows Unicode stdout failure — fixed and independently verified.**
   Plain documented invocation `search mortality` failed with
   `error.code=local_processing_failed` and message
   `'charmap' codec can't encode character '\u2011' in position 1071: character maps to <undefined>`.
   The nonbreaking hyphen in the official under-five label triggered this.
   Original evidence: `11-search-mortality.json`. Workaround evidence:
   `16-search-mortality-utf8.json`. The parent reported adding automatic UTF-8
   stdout/stderr configuration; plain invocation then succeeded with
   `status=ok`, `total_matches=19`, preserving `Under‑5 mortality rate`:
   `21-search-mortality-fixed.json`.

2. **Natural-language discoverability gap — fixed and independently verified.**
   `child mortality` initially returned `no_matches` despite relevant catalogue
   series. Original evidence: `06-search-child.json`. After the parent added a
   term alias, the same plain command returned `expanded_query="under five mortality"`,
   `status=ok`, `total_matches=3`, first match `SH_DYN_MORT`:
   `22-search-child-fixed.json`. It remains essential to clarify the user's
   intended age range and rate/count before retrieving values.

3. **Metadata versus observed-dimension pitfall — documentation/workflow concern.**
   The client faithfully applies explicit filters, but series metadata may list
   dimensions absent from the selected area's records. In the TB case,
   three catalogue-confirmed total-population codes produced zero filtered rows;
   actual records carry only Reporting Type. The initial skill instruction to
   use metadata-established codes does not alone prevent this. Recommend
   inspecting actual dimensions first, and retrying without unpopulated
   dimensions before concluding that the requested scope has no data. Evidence:
   `09-describe-tb.json`, `15-get-tb.json`, `17-get-tb-no-dimensions.json`.

4. **Literal percentage search is lexical — not a correctness defect if reviewed.**
   `search "10%"` can label `10,000` or `10-14` matches as “all keywords match”.
   The current skill already requires literal threshold and denominator checking,
   which prevented a wrong selection here. `20-search-10pct.json` preserves this
   limitation for future search-quality improvement.

The three substantive retrievals all used a single data page. This forward suite
therefore verifies complete handling of these scopes but does not independently
exercise a multi-page download. Cases 1, 4 and 5 correctly end in missing-scope or
clarification outcomes; those are not fabricated numerical successes.
