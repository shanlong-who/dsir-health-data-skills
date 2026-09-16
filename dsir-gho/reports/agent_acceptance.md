# Codex agent acceptance rehearsal

This is a **GPT agent rehearsal under Codex on one Windows execution environment**. It is not validation of every ChatGPT account, plan, installation path, or network policy. The agent read the completed `SKILL.md` and its selection/location rules, then executed the bundled CLI against the public WHO GHO service. No regional aggregates were calculated from country data. Runtime code was not edited during this review.

- Environment: Python 3.12.14; no R was invoked by the skill workflow.
- Doctor: live WHO access passed at 2026-09-09T05:27:57.814043+00:00 after host-authorized public-network escalation.
- Rehearsal date: 2026-09-09.
- Catalogue verified during search: 3098 live entries.
- Main artifact: [WPR response](agent-acceptance-wpr/response.json).

## Scenario 1: Western Pacific UHC history

User request: “请帮我查询西太平洋区域 UHC Service Coverage Index 历年来的结果。”

Interpretation: the official WHO-published Western Pacific regional aggregate, identified as `WPR`. The phrase asks for a regional result and does not ask for country-level rows. The interpretation is stated in the answer; no fixed Member State expansion is performed.

Executed CLI sequence, with the confirmed Python executable and normal page size 1000:

```text
scripts/cli.py doctor
scripts/cli.py search "UHC Service Coverage Index"
scripts/cli.py describe UHC_INDEX_REPORTED
scripts/cli.py locations "西太平洋区域" WPR_WO_IDN "菲律宾"
scripts/cli.py get UHC_INDEX_REPORTED --locations WPR --spatial-type REGION --output-dir reports/agent-acceptance-wpr
scripts/cli.py get UHC_INDEX_REPORTED --locations WPR_WO_IDN --spatial-type REGION --output-dir reports/agent-acceptance-wpr-variant
```

Evidence retained: [search](agent-search-uhc.json), [description](agent-describe-uhc.json), [location resolution](agent-locations.json), [WPR CLI output](agent-get-wpr.json), and [variant CLI output](agent-get-wpr-variant.json).

The live catalogue confirmed `UHC_INDEX_REPORTED` / `UHC Service Coverage Index (SDG 3.8.1)`. It also returned data-availability and service sub-index candidates; those were not substituted for the overall service-coverage index. The description identified observed years 2000–2023 across all locations and empty Dim1–Dim3 value sets. Geographic resolution separately identified `WPR` as “Western Pacific” and `WPR_WO_IDN` as “Western Pacific without Indonesia”.

The final WPR query returned 24 raw rows, 24 cleaned rows and 24 CSV rows. WHO's declared count matched the retrieved count, completeness was true, all manifest checksums matched, and QA was `pass` with no issues. The full saved data were inspected; the 12-row terminal preview was not used as the complete time series.

### Grounded Chinese answer produced by the rehearsal

已查询 WHO GHO 官方发布的 **WPR（Western Pacific，西太平洋区域）**系列。指标为 **UHC Service Coverage Index (SDG 3.8.1)**，代码为 `UHC_INDEX_REPORTED`，单位是 **0–100 的无单位指数**。本次完整获得 **2000–2023 年、共 24 条年度记录**；最新可用年份为 **2023 年，指数为 81**。[WHO 指标元数据](https://www.who.int/data/gho/indicator-metadata-registry/imr-details/4834)

这里采用 WHO 已发布的区域汇总值。所有年份均取自当前返回的这一版本，没有自行平均或汇总各国数据。

| 年份 | UHC Service Coverage Index（WPR） |
| --- | ---: |
| 2000 | 63 |
| 2001 | 64 |
| 2002 | 64 |
| 2003 | 65 |
| 2004 | 66 |
| 2005 | 67 |
| 2006 | 68 |
| 2007 | 68 |
| 2008 | 69 |
| 2009 | 70 |
| 2010 | 71 |
| 2011 | 72 |
| 2012 | 73 |
| 2013 | 74 |
| 2014 | 75 |
| 2015 | 76 |
| 2016 | 77 |
| 2017 | 78 |
| 2018 | 78 |
| 2019 | 79 |
| 2020 | 80 |
| 2021 | 80 |
| 2022 | 81 |
| 2023 | 81 |

本次查询时间为 **2026-09-09T05:29:32.196804+00:00（UTC）**。Dim1、Dim2、Dim3 均为空，没有另外混合性别或年龄分层；来源未提供本序列的不确定性上下界。质量检查通过，24 条记录的年份和数值均不缺失，也没有重复记录。[WHO 本次数据查询](https://ghoapi.azureedge.net/api/UHC_INDEX_REPORTED?%24orderby=Id&%24filter=SpatialDimType%20eq%20%27REGION%27%20and%20SpatialDim%20in%20%28%27WPR%27%29&%24top=1000&%24skip=0&%24count=true)

需要区分的是，WHO 还单独发布 **`WPR_WO_IDN`（Western Pacific without Indonesia）**。该系列本次也返回 2000–2023 年数据，2023 年值为 **83**，与上述 WPR 的 **81** 不同。两条系列应分别保留，不能拼接或改成同一个区域名称；仅凭这些系列代码，也不能反推每一年实际采用的成员构成。该变体在 DSIR 兼容表中的地区名称为空，但实时元数据已确认其标签；这就是变体输出中的命名警告。[变体完整结果](agent-acceptance-wpr-variant/response.json)

指标定义和单位依据 Skill 附带、于 **2026-09-09** 核查的 WHO 元数据摘要；观测值是本次实时获取，元数据摘要并非每次查询都重新抓取。

下载文件：[完整 CSV](agent-acceptance-wpr/data.csv)、[结果与来源信息 JSON](agent-acceptance-wpr/response.json)、[WHO 原始记录 JSON](agent-acceptance-wpr/raw.json)、[文件校验清单](agent-acceptance-wpr/manifest.json)。

## Scenario 2: Philippines TB incidence ambiguity

User request: “查询菲律宾 TB incidence。”

The agent searched `TB incidence`, resolved Philippines to `PHL`, and described both the incidence-rate and incident-case-count candidates. It did **not** select the highest-ranked result automatically. The search ranked the count candidate first and supplied an explicit clarification note. No Philippines TB data pull was treated as authorized selection of one measure before clarification.

Executed additional CLI commands:

```text
scripts/cli.py search "TB incidence"
scripts/cli.py describe MDG_0000000020
scripts/cli.py describe TB_e_inc_num
```

Evidence: [TB search](agent-search-tb.json), [rate description](agent-describe-tb-rate.json), [count description](agent-describe-tb-count.json). Both descriptions reported observations across years 2000–2024 at the all-location inspection scope. This does not establish complete Philippines coverage; the actual selected Philippines pull must be checked after the measure is chosen.

### Correct Chinese clarification

菲律宾已识别为 `PHL`。WHO 的 TB incidence 对应两种不同指标：

| 指标 | WHO 代码 | 单位 |
| --- | --- | --- |
| Incidence of tuberculosis (per 100 000 population per year) | `MDG_0000000020` | 每 10 万人口每年 |
| Number of incident tuberculosis cases | `TB_e_inc_num` | 发病病例数 |

您需要查询菲律宾的**结核病发病率（每 10 万人口每年）**，还是**发病病例数**？也可以同时提供，两者会分别标注。[WHO 发病率指标](https://www.who.int/data/gho/data/indicators/indicator-details/GHO/incidence-of-tuberculosis-%28per-100-000-population-per-year%29)、[WHO 病例数指标](https://ghoapi.azureedge.net/api/Indicator('TB_e_inc_num'))

## Scenario 3: Philippines reported measles cases from 2015

User request: “菲律宾2015年以来的麻疹报告病例是多少？”

Selection reasoning: “reported cases” explicitly identifies surveillance counts. The live search also returned vaccine coverage and childhood death-share indicators, which answer different questions. The agent selected the verified `WHS3_62` / `Measles - number of reported cases` entry, described it, used the already-resolved Philippines code `PHL`, and applied the inclusive start year 2015. No end year was invented. The all-location description's latest year was checked again against the actual Philippines result.

```text
scripts/cli.py search measles --limit 20
scripts/cli.py describe WHS3_62
scripts/cli.py locations "中国" "日本" "菲律宾"
scripts/cli.py get WHS3_62 --locations PHL --spatial-type COUNTRY --year-from 2015 --output-dir reports/agent-acceptance-measles
```

Evidence: [search](agent-search-measles.json), [description](agent-describe-measles.json), [country resolution](agent-locations-countries.json), [CLI output](agent-get-measles.json), [full result](agent-acceptance-measles/response.json). The final output has 11 observations, confirmed WHO count 11, complete retrieval, QA `pass`, 15 CSV columns, matching raw/cleaned/CSV counts and valid file checksums. All rows are PHL/COUNTRY and satisfy the requested year filter.

### Grounded Chinese answer produced by the rehearsal

WHO GHO 返回菲律宾 **2015–2025 年**的麻疹报告病例，共 **11 条年度记录**。指标是 **`WHS3_62` — Measles - number of reported cases**，单位为**报告病例数**。[WHO 指标说明](https://www.who.int/data/gho/data/indicators/indicator-details/GHO/measles---number-of-reported-cases)

| 年份 | 麻疹报告病例数 |
| --- | ---: |
| 2015 | 619 |
| 2016 | 716 |
| 2017 | 2,428 |
| 2018 | 20,827 |
| 2019 | 48,525 |
| 2020 | 3,832 |
| 2021 | 206 |
| 2022 | 589 |
| 2023 | 2,892 |
| 2024 | 3,844 |
| 2025 | 5,042 |

本次最新可用记录是 **2025 年，5,042 例**。这是报告病例数，不能直接当作所有实际感染者的估计人数，也不是每 10 万人口发病率。2026 年没有出现在本次返回结果中，不能填成零。各行没有额外的 Dim1–Dim3 分层，来源未提供不确定性上下界；质量检查通过。

取数时间：**2026-09-09T05:33:42.592780+00:00（UTC）**。指标解释来自附带的 WHO 元数据摘要，审核日期为 2026-09-09；本次数值直接来自实时 API。

文件：[CSV](agent-acceptance-measles/data.csv)、[完整结果 JSON](agent-acceptance-measles/response.json)、[原始记录 JSON](agent-acceptance-measles/raw.json)、[校验清单](agent-acceptance-measles/manifest.json)。

## Scenario 4: Historical UHC comparison across China, Japan and the Philippines

User request: “比较中国、日本和菲律宾历年的 UHC SCI。”

Selection reasoning: the earlier live UHC search and description in this same rehearsal established the overall service-coverage index and its dimensions. The agent reused that verified indicator, resolved all three Chinese country names explicitly to CHN/JPN/PHL, then requested country records together. It did not use the WPR aggregate or average the three countries. Coverage was checked for each country after retrieval, rather than assuming all-location years imply complete country histories.

```text
scripts/cli.py search "UHC Service Coverage Index"
scripts/cli.py describe UHC_INDEX_REPORTED
scripts/cli.py locations "中国" "日本" "菲律宾"
scripts/cli.py get UHC_INDEX_REPORTED --locations CHN JPN PHL --spatial-type COUNTRY --output-dir reports/agent-acceptance-uhc-countries
```

The search and description evidence are shared with Scenario 1; they are not separate unexecuted commands. New evidence: [country resolution](agent-locations-countries.json), [country comparison CLI output](agent-get-uhc-countries.json), [complete result](agent-acceptance-uhc-countries/response.json). Retrieved 72 observations, matching WHO's count, with 24 unique country-year records per country and identical observed years 2000–2023. All raw spatial types are COUNTRY; no duplicate country-years, missing numeric values or extra strata were found. QA `pass` and every saved checksum passed.

### Grounded Chinese answer produced by the rehearsal

三国均有 **2000–2023 年**的完整年度 UHC SCI 序列，各 **24 条记录**。采用同一指标 **`UHC_INDEX_REPORTED` — UHC Service Coverage Index (SDG 3.8.1)**，单位为 **0–100 的无单位指数**。以下直接比较 WHO 发布的各国数值。[WHO 指标元数据](https://www.who.int/data/gho/indicator-metadata-registry/imr-details/4834)

| 年份 | 中国（CHN） | 日本（JPN） | 菲律宾（PHL） |
| --- | ---: | ---: | ---: |
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

最新共同年份 **2023 年**，日本为 **86**，中国为 **85**，菲律宾为 **69**。三国都可在相同年份范围内比较；没有把缺失年份补成零或用其他年份代替。Dim1–Dim3 均为空，来源未提供这批数据的不确定性上下界，因此这里仅比较点值，不作统计显著性判断。

取数时间：**2026-09-09T05:33:18.120433+00:00（UTC）**；72 条记录完整返回，质量检查通过。单位和定义来自附带、审核日期为 2026-09-09 的 WHO 元数据摘要。

文件：[完整比较 CSV](agent-acceptance-uhc-countries/data.csv)、[结果与来源 JSON](agent-acceptance-uhc-countries/response.json)、[原始记录 JSON](agent-acceptance-uhc-countries/raw.json)、[校验清单](agent-acceptance-uhc-countries/manifest.json)。

## Scenario 5: Discovery of catastrophic health expenditure above 10%

User request: “WHO有没有 catastrophic health expenditure above 10% 的指标？”

Selection reasoning: this is a discovery question. The agent should answer that suitable indicators exist and distinguish their definitions; it should not request a country unnecessarily or choose a reported/estimated variant on the user's behalf. A broad live search for “catastrophic health expenditure” returned no matches. Refining to the explicit >10% threshold triggered the skill's auditable text expansion and yielded three catalogue-confirmed candidates. This refinement did not manufacture indicator codes.

```text
scripts/cli.py search "catastrophic health expenditure" --limit 20
scripts/cli.py search "catastrophic health expenditure >10%" --limit 20
scripts/cli.py describe FINPROTECTION_CATA_TOT_10_POP
scripts/cli.py describe FINPROTECTION_CATA_TOT_10_LEVEL_SH
scripts/cli.py describe FINPROTECTION_CATA_TOT_10_LEVEL_MILLION
```

Evidence: [initial no-match search](agent-search-che.json), [refined search](agent-search-che10.json), [reported percentage description](agent-describe-che-reported.json), [estimated percentage description](agent-describe-che-estimated-percent.json), [estimated count description](agent-describe-che-estimated-count.json). All three live descriptions completed with matching declared counts: 6338 reported observations and 216 observations for each estimated variant. No invented geographic selection or unnecessary data export was used to answer an indicator-existence question.

### Grounded Chinese answer produced by the rehearsal

有。WHO GHO 当前目录中有以下 **家庭卫生支出超过家庭总预算 10%** 的指标，属于目录标注的 SDG 3.8.2 财务保护指标：

| WHO 指标代码 | 数据口径 | 输出单位 |
| --- | --- | --- |
| `FINPROTECTION_CATA_TOT_10_POP` | Reported data，受影响人口比例 | % |
| `FINPROTECTION_CATA_TOT_10_LEVEL_SH` | Estimated data，受影响人口比例 | % |
| `FINPROTECTION_CATA_TOT_10_LEVEL_MILLION` | Estimated data，受影响人数 | 百万人 |

**10% 是家庭预算占比的判定阈值；输出的百分比则是受影响人口比例。** 百万人口数和人口比例也不能混用。Reported 与 estimated 是来源明确区分的两种数据口径，不应直接合并成一条序列。[报告数据指标](https://ghoapi.azureedge.net/api/Indicator('FINPROTECTION_CATA_TOT_10_POP'))、[估计比例指标](https://ghoapi.azureedge.net/api/Indicator('FINPROTECTION_CATA_TOT_10_LEVEL_SH'))、[估计人数指标](https://ghoapi.azureedge.net/api/Indicator('FINPROTECTION_CATA_TOT_10_LEVEL_MILLION'))

本次检查中，reported 指标有国家数据，并带年龄、城乡、性别等不同分层；不能假设 Dim1 总是性别。它在所有地点合并后的观测年份范围为 **1985–2021**，不表示每个国家每年都有数据。两条 estimated 指标本次只观察到全球及区域/分组汇总，年份为 **2000, 2005, 2010, 2015, 2017, 2019**，没有观察到 COUNTRY 类型。

这些单位和 reported/estimated 区别由实时官方标题直接确认；接口未提供完整方法学定义，因此这里没有补写未经验证的估计方法。若后续下载，需要再确定地点、reported 或 estimated，以及人口比例或人数。

## Code review findings reported before edits

The live main scenario passed. The following robustness gaps were separately reproduced with small offline probes and reported to the root agent; they were not fixed by this reviewing agent:

1. **Direct Python API location validation bypass with an explicit type.** In the reviewed `GHOClient.get_gho_data`, location resolution ran only when `spatial_type` was absent. A direct call with `locations=["WPR", "PHL"]` and `spatial_type="REGION"` formed the mixed filter and returned `ok` from a mocked WPR response. The CLI resolves inputs first and was protected. The public API should validate all supplied locations and check any explicit type agrees.
2. **Interrupted HTTP reads can bypass structured failure handling.** An `http.client.IncompleteRead` raised during a request escaped as that exception rather than `GHOError`; it was neither retried nor handled by the CLI's existing exception branches. This matters for truncated/chunked responses. Catch the relevant HTTP transport exceptions as request failures.
3. **Malformed next-link ports can emit an unstructured exception.** `validate_url("https://ghoapi.azureedge.net:invalid/api/X")` raised a bare `ValueError` while reading `parsed.port`. Convert malformed URL parsing to the existing structured unsafe-link error.

The root agent subsequently fixed all three findings. Read-back confirmed unconditional location validation/type consistency, HTTPException handling and malformed-port conversion to GHOError. The root agent reported 53 passing unit tests at that checkpoint. The findings above are a review history, not unresolved release defects. Earlier observation-context ordering feedback was also sent to the root agent; context must identify its raw-order relationship or provide a stable row mapping because core cleaning sorts records.

## Acceptance boundary

All five requested prompts were rehearsed by this Codex agent using live CLI evidence: WPR UHC retrieval, Philippines TB clarification, Philippines measles retrieval, three-country UHC comparison, and CHE indicator discovery. The rehearsal validates discovery, appropriate selection, regional-code distinction, complete saved-result inspection, provenance, the exact core export schema and measure clarification in this Codex session. It does not validate arbitrary future indicators, future WHO API availability, every network policy, or installation/execution in all ChatGPT accounts. The saved numbers are dated acceptance evidence, not hardcoded runtime answers.
