"""Independent DSIR cleaning and location contracts using synthetic observations."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from clean import CORE_FIELDS, clean_records, observation_context
from locations import resolve_locations
from sdg_client import SDGError


COUNTRIES = [
    {"m49_code": "608", "iso3": "PHL", "name_short": "Philippines", "name_official": "Philippines"},
    {"m49_code": "156", "iso3": "CHN", "name_short": "China", "name_official": "China"},
    {"m49_code": "418", "iso3": "LAO", "name_short": "Lao PDR", "name_official": "Lao People's Democratic Republic"},
]


def observation(**overrides):
    row = {"indicator": ["3.2.1"], "series": "SH_DYN_MORT", "seriesDescription": "Synthetic under-five mortality rate",
           "geoAreaCode": "608", "geoAreaName": "Philippines", "timePeriodStart": 2020,
           "value": "10.5", "lowerBound": "9.0", "upperBound": "12.0",
           "dimensions": {"Sex": "F"}, "attributes": {"Units": "PER_1000_LIVE_BIRTHS", "Nature": "E"},
           "source": "Synthetic test source", "footnotes": ["Synthetic test footnote"]}
    row.update(overrides)
    return row


class CleanTests(unittest.TestCase):
    def test_exact_15_column_DSIR_mapping(self):
        result = clean_records([observation()], COUNTRIES)
        self.assertEqual(tuple(result[0]), CORE_FIELDS)
        self.assertEqual(result, [{"source": "sdg", "id": "3.2.1", "indicator": "Synthetic under-five mortality rate",
                                  "location": "608", "iso3": "PHL", "location_name": "Philippines", "year": 2020,
                                  "value": "10.5", "value_num": 10.5, "low": 9.0, "high": 12.0,
                                  "series": "SH_DYN_MORT", "dim1": None, "dim2": None, "dim3": None}])

    def test_censored_values_not_interpreted_as_numeric(self):
        rows = [observation(value=value) for value in ("<0.1", ">95", "NA", "", None, "1,000", "1e-3", " 2.5 ")]
        result = clean_records(rows, COUNTRIES)
        self.assertEqual([r["value_num"] for r in result], [None, None, None, None, None, None, 0.001, 2.5])
        self.assertEqual([r["value"] for r in result], [r["value"] for r in rows])

    def test_nonfinite_values_use_json_missingness(self):
        result = clean_records([observation(value="Inf", lowerBound="NaN", upperBound="-Inf")], COUNTRIES)[0]
        self.assertIsNone(result["value_num"])
        self.assertIsNone(result["low"])
        self.assertIsNone(result["high"])
        self.assertEqual(result["value"], "Inf")

    def test_country_name_precedence_and_nonmember_fallback(self):
        rows = [observation(geoAreaCode="418", geoAreaName="Lao People's Democratic Republic"),
                observation(geoAreaCode="772", geoAreaName="Tokelau"),
                observation(geoAreaCode="99047", geoAreaName="WHO Western Pacific")]
        result = {r["location"]: r for r in clean_records(rows, COUNTRIES)}
        self.assertEqual(result["418"]["location_name"], "Lao PDR")
        self.assertEqual(result["418"]["iso3"], "LAO")
        self.assertIsNone(result["772"]["iso3"])
        self.assertEqual(result["772"]["location_name"], "Tokelau")
        self.assertEqual(result["99047"]["location_name"], "WHO Western Pacific")
        self.assertIsNone(result["99047"]["iso3"])

    def test_first_indicator_semantics_and_context_keeps_all_links(self):
        raw = [observation(indicator=["3.2.1", "99.0.0"]), observation(indicator=[])]
        cleaned = clean_records(raw, COUNTRIES)
        self.assertEqual(cleaned[0]["id"], "3.2.1")
        self.assertIsNone(cleaned[1]["id"])
        self.assertEqual(observation_context(raw)[0]["indicator"], ["3.2.1", "99.0.0"])

    def test_missing_columns_and_empty_input(self):
        self.assertEqual(clean_records([], COUNTRIES), [])
        output = clean_records([{}], COUNTRIES)[0]
        self.assertEqual(output["source"], "sdg")
        self.assertTrue(all(v is None for k, v in output.items() if k != "source"))

    def test_stable_sort_keeps_strata_duplicates_and_context_alignment(self):
        records = [observation(timePeriodStart=2022, dimensions={"Sex": "F"}),
                   observation(geoAreaCode="156", dimensions={"Sex": "M"}),
                   observation(timePeriodStart=2022, dimensions={"Sex": "M"}),
                   observation(timePeriodStart=None), observation(geoAreaCode=None)]
        records.append(deepcopy(records[0]))
        before = deepcopy(records)
        cleaned, context = clean_records(records, COUNTRIES), observation_context(records)
        self.assertEqual(len(cleaned), 6)
        self.assertEqual([r["location"] for r in cleaned], ["156", "608", "608", "608", "608", None])
        self.assertEqual([r["raw_row_index"] for r in context], [1, 0, 2, 5, 3, 4])
        for index, item in enumerate(context):
            self.assertEqual(item["clean_row_index"], index)
            self.assertEqual(item["dimensions"], records[item["raw_row_index"]]["dimensions"])
            self.assertEqual(cleaned[index]["location"], records[item["raw_row_index"]]["geoAreaCode"])
        self.assertEqual(records, before)

    def test_context_preserves_units_sources_and_footnotes(self):
        raw = [observation(time_detail="2019-2021", timeCoverage="Three-year mean", basePeriod="2015", valueType="String")]
        context = observation_context(raw)[0]
        for field in ("attributes", "source", "footnotes", "time_detail", "timeCoverage", "basePeriod", "valueType"):
            self.assertEqual(context[field], raw[0][field])

    def test_integer_year_coercion_matches_R_semantics(self):
        records = [observation(timePeriodStart="2020.9"), observation(timePeriodStart="n/a")]
        self.assertEqual([r["year"] for r in clean_records(records, COUNTRIES)], [2020, None])

    def test_invalid_input_is_rejected(self):
        for records in (None, {}, [1]):
            with self.assertRaises(TypeError):
                clean_records(records, COUNTRIES)


class FakeAreas:
    def areas(self):
        return [{"geoAreaCode": row[0], "geoAreaName": row[1]} for row in [
            ("608", "Philippines"), ("156", "China"), ("418", "Lao People's Democratic Republic"),
            ("772", "Tokelau"), ("99047", "WHO Western Pacific"), ("1", "World"),
            ("90001", "Duplicate example"), ("90002", "Duplicate example")]]


class LocationTests(unittest.TestCase):
    def resolve(self, names):
        with patch("locations.load_countries", return_value=COUNTRIES):
            return resolve_locations(names, client=FakeAreas())

    def test_iso3_common_name_and_m49_are_same_area(self):
        result = self.resolve(["phl", "Philippines", "0608", "菲律宾"])
        self.assertEqual(result["status"], "ok")
        self.assertEqual({r["code"] for r in result["locations"]}, {"608"})

    def test_wpro_aliases_resolve_official_aggregate(self):
        result = self.resolve(["WPRO", "WPR", "Western Pacific Region", "西太区"])
        self.assertEqual(result["status"], "ok")
        self.assertEqual({r["code"] for r in result["locations"]}, {"99047"})
        self.assertTrue(all(r["scope_note"] and r["iso3"] is None for r in result["locations"]))

    def test_nonmember_area_stays_resolvable(self):
        result = self.resolve(["Tokelau", "772"])
        self.assertEqual(result["status"], "ok")
        self.assertTrue(all(r["code"] == "772" and r["iso3"] is None for r in result["locations"]))

    def test_world_is_un_area1(self):
        result = self.resolve(["global", "全球", "World"])
        self.assertEqual({r["code"] for r in result["locations"]}, {"1"})

    def test_unknown_and_fuzzy_names_are_not_silently_selected(self):
        for query in ("Atlantis", "Philipines"):
            result = self.resolve(query)
            self.assertEqual(result["status"], "needs_clarification")
            self.assertEqual(result["locations"], [])
        self.assertTrue(self.resolve("Philipines")["unresolved"][0]["candidates"])

    def test_duplicate_official_name_is_ambiguous(self):
        result = self.resolve("Duplicate example")
        self.assertEqual(result["status"], "needs_clarification")
        self.assertEqual(result["unresolved"][0]["reason"], "ambiguous")
        self.assertEqual(len(result["unresolved"][0]["candidates"]), 2)

    def test_partial_success_still_requires_clarification(self):
        result = self.resolve(["PHL", "Atlantis"])
        self.assertEqual(result["status"], "needs_clarification")
        self.assertEqual(result["locations"][0]["code"], "608")

    def test_invalid_shapes_fail_explicitly(self):
        for value in ([], None, 608, [None], [""]):
            with self.assertRaises(SDGError) as caught:
                self.resolve(value)
            self.assertEqual(caught.exception.code, "invalid_query")


if __name__ == "__main__":
    unittest.main()
