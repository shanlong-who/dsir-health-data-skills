"""Semantic search, observation QA and portable export contracts."""
import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from indicator_search import search_indicators, describe_indicator
from clean import clean_records, CORE_FIELDS
from qa import qa_records
from cli import build_response, write_result, filter_args
from sdg_client import SDGError


class CatalogueClient:
    trace = []

    def indicators(self):
        return [{"code": "3.8.1", "description": "Coverage of essential health services"},
                {"code": "3.2.1", "description": "Under-five mortality rate"},
                {"code": "3.8.2", "description": "Financial protection in health"}]

    def series(self):
        return [{"code": "UHC_TEST", "indicator": ["3.8.1"], "description": "Universal health coverage service coverage index"},
                {"code": "RATE_TEST", "indicator": ["3.2.1"], "description": "Under-five mortality rate, by sex"},
                {"code": "COUNT_TEST", "indicator": ["3.2.1"], "description": "Under-five deaths (number)"},
                {"code": "FIN_TEST", "indicator": ["3.8.2"], "description": "Population with out-of-pocket household expenditure exceeding 40% of discretionary budget"}]

    def indicator(self, code):
        return next(r for r in self.indicators() if r["code"] == code)

    def indicator_series(self, code):
        return [r for r in self.series() if code in r["indicator"]]

    def request(self, path):
        return [{"id": "Sex", "codes": [{"code": "F"}, {"code": "M"}]}] if path.endswith("Dimensions") else [{"id": "Units", "codes": [{"code": "INDEX"}]}]


def observation(**overrides):
    row = {"indicator": ["3.8.1"], "series": "UHC_TEST", "seriesDescription": "Synthetic test index",
           "geoAreaCode": "608", "geoAreaName": "Philippines", "timePeriodStart": 2020,
           "value": "50", "dimensions": {"Sex": "BOTHSEX"}, "attributes": {"Units": "INDEX"},
           "source": "Synthetic source", "footnotes": ["Synthetic note"]}
    row.update(overrides)
    return row


class SearchTests(unittest.TestCase):
    def search(self, query):
        return search_indicators(query, client=CatalogueClient(), limit=30)

    def test_exact_code_returns_only_verified_indicator_and_series(self):
        result = self.search("3.2.1")
        self.assertEqual({r["indicator_code"] for r in result["matches"]}, {"3.2.1"})
        self.assertEqual({r["series_code"] for r in result["matches"] if r["series_code"]}, {"RATE_TEST", "COUNT_TEST"})

    def test_unknown_code_does_not_fuzzy_match_another_indicator(self):
        for query in ("99.99.99", "SH_NONEXISTENT_CODE"):
            self.assertEqual(self.search(query)["status"], "no_matches")

    def test_common_alias_search_uses_catalogue_candidates(self):
        result = self.search("UHC SCI")
        self.assertEqual(result["matches"][0]["series_code"], "UHC_TEST")
        self.assertIn("expanded_query", result)

    def test_typo_fuzzy_search_marks_relevance(self):
        result = self.search("mortality raet")
        self.assertTrue(any(r["series_code"] == "RATE_TEST" for r in result["matches"]))
        self.assertTrue(all(r["relevance"] for r in result["matches"]))

    def test_old_financial_threshold_adds_explicit_caution(self):
        result = self.search("catastrophic health expenditure 10%")
        self.assertTrue(any("40%" in note and "not a substitute" in note for note in result["notes"]))

    def test_invalid_query_rejected(self):
        for query in (None, "", "   "):
            with self.assertRaises(SDGError):
                self.search(query)

    def test_description_has_no_invented_definition_or_coverage(self):
        result = describe_indicator("3.8.1", client=CatalogueClient())
        self.assertIsNone(result["series"][0]["definition"])
        self.assertIsNone(result["series"][0]["available_years"])
        self.assertTrue(result["series"][0]["units"])

    def test_metadata_failure_preserved_without_invented_fields(self):
        class FailingMetadata(CatalogueClient):
            def request(self, path):
                raise SDGError("un_api_request_failed", "Synthetic metadata outage")
        result = describe_indicator("3.8.1", client=FailingMetadata())
        self.assertEqual(len(result["metadata_errors"]), 2)
        self.assertIsNone(result["series"][0]["dimensions"])
        self.assertEqual(result["series"][0]["units"], [])


class QATests(unittest.TestCase):
    def qa(self, records):
        return qa_records(records, clean_records(records, countries=[]))

    def test_single_series_scope_is_valid(self):
        self.assertEqual(self.qa([observation()])["status"], "pass")

    def test_censored_numeric_missingness_warns_without_zero_fill(self):
        result = self.qa([observation(value="<0.1")])
        self.assertEqual(result["status"], "warning")
        self.assertEqual(result["missing_numeric"], 1)
        self.assertIn("nonnumeric_values", {r["code"] for r in result["issues"]})

    def test_multiple_strata_are_not_duplicate_observations(self):
        result = self.qa([observation(dimensions={"Sex": "F"}), observation(dimensions={"Sex": "M"})])
        self.assertEqual(len(result["summaries"]), 2)
        self.assertIn("multiple_strata", {r["code"] for r in result["issues"]})
        self.assertNotIn("duplicate_observation_keys", {r["code"] for r in result["issues"]})

    def test_duplicates_are_flagged_and_preserved(self):
        result = self.qa([observation(), observation()])
        self.assertEqual(result["row_count"], 2)
        self.assertIn("duplicate_observation_keys", {r["code"] for r in result["issues"]})

    def test_reversed_bounds_fail(self):
        result = self.qa([observation(lowerBound=60, upperBound=40)])
        self.assertEqual(result["status"], "fail")
        self.assertIn("reversed_interval", {r["code"] for r in result["issues"]})

    def test_missing_identity_fails(self):
        self.assertEqual(self.qa([observation(timePeriodStart=None)])["status"], "fail")

    def test_clean_row_loss_fails(self):
        self.assertEqual(qa_records([observation()], [])["status"], "fail")


class ExportTests(unittest.TestCase):
    def response(self, raw):
        return build_response({"records": raw, "indicator": {"code": "3.8.1"}, "series_catalogue": [],
                               "query": {"indicator": "3.8.1", "locations": ["608", "392"]},
                               "retrieved_row_count": len(raw), "pages": 1,
                               "metadata": {}, "baseline_probe": None, "status": "ok"}, CatalogueClient())

    def test_missing_requested_country_is_reported(self):
        response = self.response([observation()])
        self.assertEqual(response["coverage_by_location"][1], {"location": "392", "years": [], "row_count": 0})
        self.assertIn("locations_without_data", {i["code"] for i in response["qa"]["issues"]})

    def test_csv_includes_context_and_exact_DSIR_core(self):
        raw = [observation(dimensions={"Sex": "F"}), observation(dimensions={"Sex": "M"})]
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temp:
            destination = Path(temp) / "results"
            write_result(destination, self.response(raw), raw)
            with (destination / "observations.csv").open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 2)
            self.assertEqual(json.loads(rows[0]["dimensions_json"]), {"Sex": "F"})
            self.assertEqual(rows[0]["unit"], "INDEX")
            self.assertEqual(rows[0]["observation_source"], "Synthetic source")
            with (destination / "dsir_clean.csv").open(encoding="utf-8-sig", newline="") as stream:
                self.assertEqual(next(csv.reader(stream)), list(CORE_FIELDS))
            manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(all(hashlib.sha256((destination / name).read_bytes()).hexdigest() == digest for name, digest in manifest["files"].items()))

    def test_existing_directory_never_overwritten(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temp:
            with self.assertRaises(SDGError) as caught:
                write_result(temp, self.response([]), [])
            self.assertEqual(caught.exception.code, "output_exists")

    def test_dimension_filter_parser_preserves_repeated_values(self):
        self.assertEqual(filter_args(["Sex=F", "Sex=M", "Age=ALLAGE"]), {"Sex": ["F", "M"], "Age": ["ALLAGE"]})
        for value in ("Sex", "=F", "Sex="):
            with self.assertRaises(SDGError):
                filter_args([value])

    def test_cli_emits_utf8_official_labels_even_in_cp1252_environment(self):
        code = '''
import cli
class FakeClient:
    trace = []
    def indicators(self):
        return [{"code": "3.2.1", "description": "Caf\u00e9 under-five mortality rate"}]
    def series(self):
        return []
cli.SDGClient = lambda **kwargs: FakeClient()
raise SystemExit(cli.main(["search", "3.2.1"]))
'''
        environment = dict(os.environ, PYTHONIOENCODING="cp1252")
        process = subprocess.run([sys.executable, "-c", code],
                                 cwd=Path(__file__).resolve().parents[1] / "scripts",
                                 env=environment, capture_output=True, check=False)
        self.assertEqual(process.returncode, 0, process.stderr.decode("utf-8", errors="replace"))
        response = json.loads(process.stdout.decode("utf-8"))
        self.assertEqual(response["matches"][0]["name"], "Caf\u00e9 under-five mortality rate")


if __name__ == "__main__":
    unittest.main()
