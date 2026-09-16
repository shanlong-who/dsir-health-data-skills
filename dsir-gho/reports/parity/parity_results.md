# Original DSIR versus Python parity

Generated: 2026-09-09T05:29:01.244458+00:00

Overall: PASS.
Live queries: 15 passed, 0 failed.
Common-raw cleaning checks: 16 passed, 0 failed.

Reference: DSIR 0.9.0; R version 4.6.1 (2026-06-24 ucrt); original commit `e2ff6735d174769b55f9a3e55f9f36c75ce9f397`.

Each comparison checks the 15 ordered fields, R/Python scalar types, row counts and multiplicity, dimensions, per-column missingness, raw display values, indicator/location labels, and numeric values with absolute tolerance 1e-10 and relative tolerance 1e-12.

R executes the original source without editing the original repository or installed package. The R child result is checked independently of the successful parent exit. Test evidence is not runtime data.

| Query | Live parity | Common-raw parity | Rows (Python/R) |
| --- | --- | --- | --- |
| main_01_wpr_uhc | PASS | PASS | 24/24 |
| main_02_phl_measles | PASS | PASS | 11/11 |
| tb_rate_phl | PASS | PASS | 10/10 |
| tb_number_phl | PASS | PASS | 10/10 |
| tb_hiv_rate_phl | PASS | PASS | 9/9 |
| tb_hiv_number_phl | PASS | PASS | 10/10 |
| financial_reported_phl | PASS | PASS | 13/13 |
| financial_estimated_wpr | PASS | PASS | 6/6 |
| financial_millions_wpr | PASS | PASS | 6/6 |
| life_expectancy_sex_phl | PASS | PASS | 21/21 |
| obesity_age_sex_phl | PASS | PASS | 30/30 |
| health_expenditure_currency_phl | PASS | PASS | 9/9 |
| doctors_rate_phl | PASS | PASS | 8/8 |
| anaemia_pregnancy_phl | PASS | PASS | 27/27 |
| vaccine_percentage_phl | PASS | PASS | 11/11 |
