"""Verify provenance joins and lossless JSON export independently of networking."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cli import build_response, write_result
from gho_client import GHOClient, GHOError


class ExportTests(unittest.TestCase):
    def build(self):
        client = GHOClient()
        client._catalogue = [{"IndicatorCode": "X", "IndicatorName": "Synthetic measure"}]
        records = [
            {"Id": 10, "IndicatorCode": "X", "SpatialDim": "PHL", "SpatialDimType": "COUNTRY", "TimeDim": 2021, "NumericValue": 7, "Value": "NA"},
            {"Id": 11, "IndicatorCode": "X", "SpatialDim": "PHL", "SpatialDimType": "COUNTRY", "TimeDim": 2020, "NumericValue": None, "Value": ""},
        ]
        result = {"records": records, "indicator": client._catalogue[0], "status": "ok", "provenance": {"complete": True},
                  "query": {"indicator": "X", "locations": ["PHL", "JPN"], "spatial_type": "COUNTRY", "year_from": None, "year_to": None, "dimensions": {}}}
        return build_response(result, client), records

    def test_context_preserves_raw_and_clean_linkage(self):
        response, records = self.build()
        self.assertEqual([r["Id"] for r in response["observation_context"]], [11, 10])
        for cleaned, context in zip(response["data"], response["observation_context"]):
            original = records[context["raw_row_index"]]
            self.assertEqual(original["TimeDim"], cleaned["year"])
            self.assertEqual(original["Id"], context["Id"])
        self.assertEqual(response["coverage_by_location"][1]["row_count"], 0)
        self.assertIn("locations_without_data", [issue["code"] for issue in response["qa"]["issues"]])

    def test_export_hashes_and_literal_strings(self):
        response, records = self.build()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "new-pull"
            files = write_result(output, response, records)
            saved = json.loads(Path(files["response_json"]).read_text(encoding="utf-8"))
            self.assertEqual(saved["data"][0]["value"], "")
            self.assertIsNone(saved["data"][0]["value_num"])
            self.assertEqual(saved["data"][1]["value"], "NA")
            manifest = json.loads((output / "manifest.json").read_text())
            for name, digest in manifest["files"].items():
                self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), digest)
            with self.assertRaises(GHOError) as caught:
                write_result(output, response, records)
            self.assertEqual(caught.exception.code, "output_exists")


if __name__ == "__main__":
    unittest.main()
