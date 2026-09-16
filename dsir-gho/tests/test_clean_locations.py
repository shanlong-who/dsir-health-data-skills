"""Synthetic contracts for DSIR cleaning, geographic resolution and QA."""

from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from clean import CORE_FIELDS, clean_records
from locations import load_countries, resolve_locations
from qa import qa_records


CATALOGUE = [{"IndicatorCode": "X", "IndicatorName": "Example estimate", "Language": "EN"}]


def observation(**overrides):
    row = {"IndicatorCode": "X", "SpatialDim": "PHL", "SpatialDimType": "COUNTRY",
           "TimeDim": 2020, "Value": "12.3 [10.0-14.0]", "NumericValue": 12.3,
           "Low": 10.0, "High": 14.0, "Dim1": "SEX_BTSX", "Dim2": None, "Dim3": None}
    row.update(overrides)
    return row


class FakeClient:
    def __init__(self):
        self.calls = []
        self.values = {
            "COUNTRY": [{"Code": "TKL", "Title": "Tokelau", "ParentCode": "WPR"}],
            "REGION": [{"Code": "WPR", "Title": "Western Pacific Region", "ParentCode": None},
                       {"Code": "WPR_WO_IDN", "Title": "Western Pacific excluding Indonesia", "ParentCode": "WPR"}],
            "GLOBAL": [{"Code": "GLOBAL", "Title": "World", "ParentCode": None}],
        }

    def dimension_values(self, dimension):
        self.calls.append(dimension)
        return self.values[dimension]


class CleanTests(unittest.TestCase):
    def test_exact_mapping_and_catalogue_precedence(self):
        raw = [observation(IndicatorName="Do not use this source name")]
        original = deepcopy(raw)
        cleaned = clean_records(raw, CATALOGUE)
        self.assertEqual(list(cleaned[0]), list(CORE_FIELDS))
        self.assertEqual(cleaned, [{
            "source": "gho", "id": "X", "indicator": "Example estimate",
            "location": "PHL", "iso3": "PHL", "location_name": "Philippines",
            "year": 2020, "value": "12.3 [10.0-14.0]", "value_num": 12.3,
            "low": 10.0, "high": 14.0, "series": None,
            "dim1": "SEX_BTSX", "dim2": None, "dim3": None,
        }])
        self.assertEqual(raw, original)

    def test_missing_columns_empty_data_and_first_catalogue_match(self):
        self.assertEqual(clean_records([], CATALOGUE), [])
        row = clean_records([{"IndicatorCode": "X", "SpatialDim": "LAO"}], CATALOGUE * 2)[0]
        self.assertEqual(row["location_name"], "Lao PDR")
        self.assertIsNone(row["year"])
        self.assertIsNone(row["value_num"])
        self.assertIsNone(row["dim1"])
        first = clean_records([observation()], CATALOGUE + [{"IndicatorCode": "X", "IndicatorName": "Other"}])[0]
        self.assertEqual(first["indicator"], "Example estimate")

    def test_stable_sort_does_not_drop_duplicates_or_dimensions(self):
        raw = [observation(SpatialDim=None), observation(TimeDim=None),
               observation(Dim1="SEX_FMLE"), observation(Dim1="SEX_MLE"),
               observation(SpatialDim="IDN"), observation(Dim1="SEX_MLE")]
        cleaned = clean_records(raw, CATALOGUE)
        self.assertEqual([row["location"] for row in cleaned], ["IDN", "PHL", "PHL", "PHL", "PHL", None])
        self.assertEqual([row["dim1"] for row in cleaned[1:4]], ["SEX_FMLE", "SEX_MLE", "SEX_MLE"])
        self.assertIsNone(cleaned[4]["year"])
        self.assertEqual(len(cleaned), len(raw))

    def test_value_is_independent_of_numeric_and_strings_are_literal(self):
        rows = [observation(Value="<0.1", NumericValue=0.05),
                observation(Value="NA", NumericValue=None),
                observation(Value="", NumericValue="invalid"),
                observation(Value=None, NumericValue="3.4", TimeDim="2020.9")]
        cleaned = clean_records(rows, CATALOGUE)
        self.assertEqual([row["value"] for row in cleaned], ["<0.1", "NA", "", None])
        self.assertEqual([row["value_num"] for row in cleaned], [0.05, None, None, 3.4])
        self.assertEqual(cleaned[-1]["year"], 2020)

    def test_nonmember_region_variant_and_case_sensitive_country_identity(self):
        locations = ["WPR", "GLOBAL", "TKL", "WPR_WO_IDN", "phl", "IDN"]
        out = {row["location"]: row for row in clean_records([observation(SpatialDim=loc) for loc in locations], CATALOGUE)}
        self.assertEqual(out["WPR"]["location_name"], "Western Pacific")
        self.assertEqual(out["GLOBAL"]["location_name"], "Global")
        self.assertEqual(out["IDN"]["iso3"], "IDN")
        for code in ("WPR", "GLOBAL", "TKL", "WPR_WO_IDN", "phl"):
            self.assertIsNone(out[code]["iso3"])
        self.assertIsNone(out["WPR_WO_IDN"]["location_name"])

    def test_invalid_inputs_and_nonfinite_numbers(self):
        with self.assertRaises(TypeError):
            clean_records(None, CATALOGUE)
        out = clean_records([observation(NumericValue=float("inf"), TimeDim="n/a")], CATALOGUE)[0]
        self.assertIsNone(out["value_num"])
        self.assertIsNone(out["year"])


class LocationTests(unittest.TestCase):
    def test_metadata_snapshot_has_complete_identifiers(self):
        countries = load_countries()
        self.assertEqual(len(countries), 194)
        self.assertEqual(len({row["iso3"] for row in countries}), 194)
        self.assertEqual({row["iso3"]: row for row in countries}["NAM"]["iso2"], "NA")
        self.assertEqual({row["iso3"]: row for row in countries}["BRA"]["m49_code"], "076")
        self.assertEqual({row["iso3"]: row for row in countries}["IDN"]["who_region"], "WPR")
        self.assertEqual(sum(row["who_region"] == "WPR" for row in countries), 28)
        self.assertEqual(sum(row["who_region"] == "SEAR" for row in countries), 10)
        self.assertIn("Côte d'Ivoire", {row["name_official"] for row in countries})

    def test_export_hash_matches_provenance(self):
        folder = Path(__file__).resolve().parents[1] / "references" / "metadata"
        provenance = json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256((folder / "who_countries.json").read_bytes()).hexdigest(), provenance["export_sha256"])

    def test_country_codes_names_and_reviewable_aliases(self):
        out = resolve_locations(["phl", "Indonesia", "Lao PDR", "UK", "越南", "NA"])
        self.assertEqual(out["status"], "ok")
        self.assertEqual([row["code"] for row in out["locations"]], ["PHL", "IDN", "LAO", "GBR", "VNM", "NAM"])

    def test_congo_and_korea_require_explicit_choice(self):
        for query, codes in [("Congo", {"COG", "COD"}), ("Korea", {"KOR", "PRK"})]:
            out = resolve_locations(query)
            self.assertEqual(out["status"], "needs_clarification")
            self.assertEqual({row["code"] for row in out["candidates"]}, codes)
            self.assertEqual(out["locations"], [])
        self.assertEqual(resolve_locations("Democratic Republic of the Congo")["locations"][0]["code"], "COD")

    def test_wpr_aliases_use_official_aggregate_not_static_members(self):
        client = FakeClient()
        for query in ("WPR", "WPRO", "西太平洋地区", "Western Pacific"):
            out = resolve_locations(query, client=client)
            self.assertEqual(out["status"], "ok")
            self.assertEqual(len(out["locations"]), 1)
            self.assertEqual(out["locations"][0]["code"], "WPR")
            self.assertEqual(out["locations"][0]["matched_by"], "official_aggregate")
            self.assertEqual(out["locations"][0]["spatial_type"], "region")

    def test_live_nonmember_and_region_variant(self):
        client = FakeClient()
        out = resolve_locations(["Tokelau", "WPR_WO_IDN"], client=client)
        self.assertEqual(out["status"], "ok")
        self.assertEqual([row["code"] for row in out["locations"]], ["TKL", "WPR_WO_IDN"])
        self.assertEqual(client.calls.count("REGION"), 1)
        self.assertEqual(resolve_locations("WPR_WO_IDN")["status"], "unknown_location")

    def test_unknown_batch_member_is_reported_and_service_errors_propagate(self):
        out = resolve_locations(["PHL", "Not a location"])
        self.assertEqual(out["status"], "unknown_location")
        self.assertEqual(out["unresolved"], ["Not a location"])
        self.assertEqual(out["locations"][0]["code"], "PHL")
        class BrokenClient:
            def dimension_values(self, dimension):
                raise RuntimeError("Metadata service unavailable")
        with self.assertRaisesRegex(RuntimeError, "Metadata service unavailable"):
            resolve_locations("WPR", client=BrokenClient())


class QATests(unittest.TestCase):
    def test_valid_pull_passes_all_source_filters(self):
        raw = [observation()]
        out = qa_records(clean_records(raw, CATALOGUE), raw, {
            "indicator": "X", "area": ["PHL"], "spatial_type": "country",
            "year_from": 2020, "year_to": 2020, "dim1": "SEX_BTSX",
        })
        self.assertEqual(out["status"], "pass")
        self.assertTrue(out["counts"]["dimensions_preserved"])

    def test_duplicates_missingness_years_and_bounds_are_reported(self):
        raw = [observation(), observation(), observation(TimeDim="bad", NumericValue=None),
               observation(Low=20, High=10)]
        cleaned = clean_records(raw, CATALOGUE)
        before = deepcopy(cleaned)
        out = qa_records(cleaned, raw)
        self.assertEqual(out["status"], "fail")
        codes = {item["code"] for item in out["issues"]}
        self.assertTrue({"duplicate_rows", "missing_numeric", "nonnumeric_year", "reversed_bounds"} <= codes)
        self.assertEqual(out["counts"]["duplicate_rows"], 1)
        self.assertEqual(cleaned, before)

    def test_dimension_corruption_and_filter_mismatches_fail(self):
        raw = [observation()]
        cleaned = clean_records(raw, CATALOGUE)
        cleaned[0]["dim1"] = "SEX_MLE"
        out = qa_records(cleaned, raw, {"area": ["IDN"], "year_to": 2019, "dim1": "SEX_BTSX", "spatial_type": "region"})
        self.assertEqual(out["status"], "fail")
        codes = {item["code"] for item in out["issues"]}
        self.assertTrue({"dimensions_changed", "area_filter_mismatch", "year_filter_mismatch",
                         "dimension_filter_mismatch", "spatial_type_filter_mismatch"} <= codes)

    def test_cleaning_reordering_is_not_a_dimension_error(self):
        raw = [observation(SpatialDim="PHL"), observation(SpatialDim="IDN")]
        self.assertEqual(qa_records(clean_records(raw, CATALOGUE), raw)["status"], "pass")

    def test_empty_and_nonmember_outputs_are_not_false_passes(self):
        self.assertEqual(qa_records([], [])["status"], "warning")
        raw = [observation(SpatialDim="TKL")]
        out = qa_records(clean_records(raw, CATALOGUE), raw)
        self.assertEqual(out["status"], "warning")
        self.assertIn("missing_location_name", {item["code"] for item in out["issues"]})


if __name__ == "__main__":
    unittest.main()
