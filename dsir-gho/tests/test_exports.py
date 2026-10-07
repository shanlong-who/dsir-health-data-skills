"""Verify provenance joins and lossless JSON export independently of networking."""
import hashlib
import json
import sys
import tempfile
import unittest
import csv
import io
from contextlib import redirect_stdout
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cli import build_response, write_result, main
from gho_client import GHOClient, GHOError


class ExportTests(unittest.TestCase):
    def build(self):
        client = GHOClient(backend="legacy")
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

    def test_xmart_cli_exports_native_raw_without_changing_core_schema(self):
        from test_xmart import FixtureTransport, wide
        from clean import CORE_FIELDS
        client = GHOClient(transport=FixtureTransport())
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "fresh"
            stream = io.StringIO()
            with patch("cli.GHOClient", return_value=client), redirect_stdout(stream):
                status = main(["get", "TEST", "--locations", "PHL", "--dimension", "DIM_SEX", "FEMALE",
                               "--output-dir", str(output)])
            self.assertEqual(status, 0, stream.getvalue())
            self.assertEqual(json.loads((output / "source_raw.json").read_text()), [wide()])
            with (output / "data.csv").open(encoding="utf-8-sig", newline="") as handle:
                self.assertEqual(next(csv.reader(handle)), list(CORE_FIELDS))
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(len(manifest["files"]), 4)
            for name, digest in manifest["files"].items():
                self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), digest)
            response = json.loads((output / "response.json").read_text())
            self.assertEqual(response["provenance"]["backend"], "xmart")
            self.assertEqual(response["observation_context"][0]["raw_row_index"], 0)


if __name__ == "__main__":
    unittest.main()
