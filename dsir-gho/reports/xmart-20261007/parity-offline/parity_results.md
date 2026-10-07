# DSIR 0.11.0 xMart parity

Generated: 2026-10-07T00:15:40.590462+00:00
Reference commit: \`885464b1fade2f8b6d02dde93f9080e4b3f4f2a5\`.

Common-input source parity: 10 passed; 3 failed.
Independent live parity: 0 passed; 0 unverified.
Synthetic fixtures validate transformations only; they are never WHO data.
The exact source files and bundled data are loaded without using the installed DSIR package.

| Check | Result |
| --- | --- |
| wide_bounds_dimensions | PASS |
| long_row_specific_dimensions | PASS |
| long_canonical_sex_age | PASS |
| wide_nonannual_time | PASS |
| wide_literal_missing_numeric | FAIL |
| wide_missing_display | FAIL |
| wide_small_display | PASS |
| wide_large_display | FAIL |
| wide_nonmember_name | PASS |
| wide_who_region | PASS |
| wide_all_null_dimension | PASS |
| empty_clean | PASS |
| core_missingness_duplicates | PASS |
