"""Explicitly synthetic common inputs; never a runtime observation source."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_xmart import directory, wide, long, GEO, FixtureTransport
from gho_client import GHOClient
from clean import clean_records


def common_inputs():
    cases = [
        ("wide_bounds_dimensions", [wide()]),
        ("long_row_specific_dimensions", [long(), long(Sys_PK=2, DIM_1_CODE="DIM_AGE", DIM_MEMBER_1_CODE="Y40T44")]),
        ("long_canonical_sex_age", [long(DIM_1_CODE="DIM_SEX", DIM_MEMBER_1_CODE="TOTAL", DIM_2_CODE="DIM_AGE", DIM_MEMBER_2_CODE="Y40T44")]),
        ("wide_nonannual_time", [wide(DIM_TIME="2023-Q1", DIM_TIME_TYPE="QUARTER")]),
        ("wide_literal_missing_numeric", [wide(AMOUNT_N=None, VALUE_LABEL="NA")]),
        ("wide_missing_display", [wide(VALUE_LABEL=None, AMOUNT_N=123.12345678912345)]),
        ("wide_small_display", [wide(VALUE_LABEL=None, AMOUNT_N=0.00001)]),
        ("wide_large_display", [wide(VALUE_LABEL=None, AMOUNT_N=100000)]),
        ("wide_nonmember_name", [wide(DIM_GEO_CODE_M49="772", GEO_NAME_SHORT="Tokelau")]),
        ("wide_who_region", [wide(DIM_GEO_CODE_M49="958", DIM_GEO_CODE_TYPE="WHOREGION")]),
        ("wide_all_null_dimension", [wide(DIM_SEX=None)]),
    ]
    result = []
    for label, native in cases:
        client = GHOClient(transport=FixtureTransport(native))
        context = client._xmart.context("TEST")
        normalized = client._xmart.normalize(native, context)
        result.append({"id": label, "synthetic": True, "native": native, "context": context,
                       "geo": GEO, "records": normalized, "clean": clean_records(normalized, client.catalogue())})
    result.append({"id": "empty_clean", "synthetic": True, "records": [], "clean": []})
    scalar = [{"IndicatorCode": "TEST", "IndicatorName": "Synthetic edge measure", "SpatialDim": "PHL",
               "TimeDim": "2020.9", "Value": "<0.1", "NumericValue": None, "Dim1": "SEX_BTSX"}]
    scalar += [dict(scalar[0]), {"IndicatorCode": "TEST", "IndicatorName": None, "SpatialDim": "TKL",
                "SpatialName": "Tokelau", "Value": "", "NumericValue": "not available"}]
    result.append({"id": "core_missingness_duplicates", "synthetic": True, "records": scalar,
                   "clean": clean_records(scalar, [])})
    return {"catalogue": [{"IndicatorCode": "TEST", "IndicatorName": "Synthetic xMart measure", "Language": "EN"}],
            "queries": result,
            "purpose": "Transformation-only test fixtures. All numeric values and indicator identities are synthetic."}
