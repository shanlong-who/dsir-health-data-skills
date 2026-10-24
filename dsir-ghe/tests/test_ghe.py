"""Synthetic API fixtures: these numbers are not WHO observations."""
import contextlib
import copy
import csv
import hashlib
import io
import itertools
import json
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from ghe_client import DATA_FIELDS, GHEClient, load_reference
from transport import BASE_URL, TABLE, GHEError, Transport, validate_url
from cli import main, write_result


class Fixture:
    def __init__(self):
        reference, _ = load_reference()
        self.definitions = reference["measures"]
        self.rows, self.calls = [], []
        combinations = itertools.product(("PHL", "CHN", "NAM"), (2022, 2023),
                                         ("TOTAL", "FEMALE", "MALE"), ("TOTAL", "Y40T44"), (0, 10))
        for identifier, (area, year, sex, age, cause) in enumerate(combinations, 1):
            row = {"Sys_PK": identifier, "DIM_COUNTRY_CODE": area, "DIM_YEAR_CODE": year,
                   "DIM_SEX_CODE": sex, "DIM_AGEGROUP_CODE": age, "DIM_GHECAUSE_CODE": cause,
                   "DIM_GHECAUSE_TITLE": "All Causes" if cause == 0 else "Synthetic Diabetes",
                   "ATTR_POPULATION_NUMERIC": 100000, "FLAG_LEVEL": 0 if cause == 0 else 1,
                   "DIM_CAUSE_GROUP": 1, "FLAG_RANKABLE": cause != 0, "FLAG_SINGLE_CAUSE": cause != 0}
            for index, definition in enumerate(self.definitions, 1):
                field = definition["field"]
                row[field] = index if definition["code"].endswith("_percent") else 100 + identifier + index
                if field.endswith("_COUNT_NUMERIC"):
                    row[field.removesuffix("_NUMERIC") + "_LOW"] = row[field] - 5
                    row[field.removesuffix("_NUMERIC") + "_HIGH"] = row[field] + 5
            self.rows.append(row)

    @staticmethod
    def matches(row, expression):
        for part in expression.split(" and "):
            if not part:
                continue
            if part.startswith("(") and part.endswith(")"):
                part = part[1:-1]
            field, operator, value = part.split(" ", 2)
            if operator == "in":
                allowed = [item.strip("'") for item in value[1:-1].split(",")]
                if str(row[field]) not in allowed:
                    return False
            elif operator == "eq" and str(row[field]) != value.strip("'"):
                return False
            elif operator == "ge" and row[field] < int(value):
                return False
            elif operator == "le" and row[field] > int(value):
                return False
        return True

    def __call__(self, url, *, method="GET", body=None):
        self.calls.append((url, method, body))
        parsed = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qs(body.decode() if body else parsed.query)
        if "REF_YEAR_COD" in url:
            return {"value": [{"CODE": 2022, "TITLE": "2022"}, {"CODE": 2023, "TITLE": "2023"}]}
        if "REF_SEX_COD" in url:
            return {"value": [{"CODE": code, "TITLE": code} for code in ("TOTAL", "FEMALE", "MALE")]}
        if "REF_AGE_COD" in url:
            return {"value": [{"CODE": "TOTAL", "TITLE": "All ages"}, {"CODE": "Y40T44", "TITLE": "40-44 years"}]}
        expression = query.get("$filter", [""])[0]
        rows = [copy.deepcopy(row) for row in self.rows if self.matches(row, expression)]
        total = len(rows)
        offset, size = int(query.get("$skip", [0])[0]), int(query.get("$top", [5000])[0])
        rows = rows[offset:offset + size]
        if "$select" in query:
            fields = query["$select"][0].split(",")
            rows = [{field: row[field] for field in fields if field in row} for row in rows]
        return {"@odata.count": total, "value": rows}


class GHETests(unittest.TestCase):
    def setUp(self):
        self.fixture = Fixture()
        self.client = GHEClient(transport=self.fixture, sleep=lambda _: None)
        self.selection = dict(area=["PHL"], year=[2023], sex=["TOTAL"], age=["TOTAL"],
                              cause=["0"], measure=["deaths", "death_rate"])

    def assert_code(self, code, function, *args, **kwargs):
        with self.assertRaises(GHEError) as error:
            function(*args, **kwargs)
        self.assertEqual(error.exception.code, code)
        return error.exception

    def selected_row(self):
        return next(row for row in self.fixture.rows if
                    (row["DIM_COUNTRY_CODE"], row["DIM_YEAR_CODE"], row["DIM_SEX_CODE"],
                     row["DIM_AGEGROUP_CODE"], row["DIM_GHECAUSE_CODE"]) == ("PHL", 2023, "TOTAL", "TOTAL", 0))

    def test_bundled_country_identity_and_integrity(self):
        reference, provenance = load_reference()
        countries = {row["iso3"]: row for row in reference["who_countries"]}
        self.assertEqual(len(countries), 194)
        self.assertEqual(countries["AFG"]["m49_code"], "004")
        self.assertEqual(countries["NAM"]["iso2"], "NA")
        self.assertIsNone(countries["COK"]["wb_income_group"])
        self.assertEqual(countries["IDN"]["who_region"], "WPR")
        self.assertEqual(provenance["source_version"], "0.11.0")

    def test_discovery_uses_real_fixture_fields_and_reference_slices(self):
        self.assertEqual(len(self.client.dimensions("measure")), 11)
        self.assertEqual([row["code"] for row in self.client.dimensions("year")], ["2022", "2023"])
        self.assertEqual({row["code"] for row in self.client.dimensions("sex")}, {"TOTAL", "FEMALE", "MALE"})
        self.assertEqual({row["code"] for row in self.client.dimensions("age")}, {"TOTAL", "Y40T44"})
        self.assertEqual(self.client.reference_area(), "CHN")
        self.assertEqual([row["cause_code"] for row in self.client.causes("synthetic diabetes")], ["10"])
        self.assertEqual(self.client.causes("diabetes impossible"), [])
        self.assertEqual(self.client.dimensions("cause"), self.client.causes())

    def test_all_measures_preserve_dsir_shape_units_and_raw_linkage(self):
        selection = {**self.selection, "measure": [row["code"] for row in self.fixture.definitions]}
        result = self.client.get_data(**selection)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["data"]), 11)
        self.assertEqual(tuple(result["data"][0]), DATA_FIELDS)
        self.assertEqual(result["provenance"]["source_rows"], 1)
        self.assertIsNone(result["provenance"]["release"])
        self.assertTrue(result["provenance"]["complete"])
        self.assertFalse(result["provenance"]["automatic_fallback"])
        for row, context in zip(result["data"], result["observation_context"]):
            raw = result["raw"][context["raw_row_index"]]
            self.assertEqual(row["value"], raw[context["provider_field"]])
            self.assertEqual(context["source_row_id"], raw["Sys_PK"])

    def test_country_year_sex_age_cause_filters_are_preserved(self):
        selection = {**self.selection, "area": ["PHL", "CHN"], "year": [2022, 2023],
                     "sex": ["FEMALE"], "age": ["Y40T44"], "cause": ["10"]}
        result = self.client.get_data(**selection)
        self.assertEqual(len(result["data"]), 8)
        self.assertEqual({row["sex"] for row in result["data"]}, {"FEMALE"})
        self.assertEqual({row["age"] for row in result["data"]}, {"Y40T44"})
        self.assertEqual({row["cause_code"] for row in result["data"]}, {"10"})
        rates = [context for row, context in zip(result["data"], result["observation_context"]) if row["measure"] == "death_rate"]
        self.assertTrue(all(context["rate_type"] == "age_specific" for context in rates))

    def test_missing_estimates_and_true_zero_remain_distinct(self):
        self.selected_row()["VAL_DTHS_COUNT_NUMERIC"] = None
        self.selected_row()["VAL_DTHS_RATE100K_NUMERIC"] = 0
        result = self.client.get_data(**self.selection)
        rows = {row["measure"]: row for row in result["data"]}
        self.assertIsNone(rows["deaths"]["value"])
        self.assertEqual(rows["death_rate"]["value"], 0)
        self.assertEqual(result["qa"]["missing_numeric"], 1)
        self.assertEqual(result["status"], "ok")

    def test_quality_limits_and_partial_location_coverage(self):
        self.selected_row()["VAL_PROP_DTHS_PERCENT"] = 100.1
        result = self.client.get_data(**{**self.selection, "measure": ["deaths_percent"]})
        self.assertEqual(result["status"], "qa_failed")
        self.assertIn("percentage_out_of_range", {issue["code"] for issue in result["qa"]["issues"]})
        self.fixture.rows = [row for row in self.fixture.rows if not
                             (row["DIM_COUNTRY_CODE"] == "CHN" and row["DIM_YEAR_CODE"] == 2022)]
        result = self.client.get_data(**{**self.selection, "area": ["PHL", "CHN"], "year": [2022]})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["qa"]["status"], "warning")
        self.assertEqual(result["qa"]["issues"][0]["locations"], ["CHN"])

    def test_identifier_type_changes_and_malformed_reference_codes(self):
        http = Transport(page_size=1, transport=lambda *args, **kwargs: {})
        with mock.patch.object(http, "request", side_effect=[
                {"@odata.count": 2, "value": [{"Sys_PK": 1}]},
                {"@odata.count": 2, "value": [{"Sys_PK": "1"}]}]):
            self.assert_code("incomplete_data", http.collection, "", ["Sys_PK"])
        for value in (None, "", " ", True, [], {}, 1.5):
            with self.subTest(value=value), mock.patch.object(http, "request", return_value={
                    "value": [{"CODE": value, "TITLE": "Synthetic label"}]}):
                self.assert_code("invalid_catalogue", http.reference, "DEX_CMS/REF_YEAR_COD", 100)

    def test_counts_have_bounds_rates_do_not_inherit_them(self):
        result = self.client.get_data(**self.selection)
        rows = {row["measure"]: row for row in result["data"]}
        self.assertIsNotNone(rows["deaths"]["low"])
        self.assertIsNone(rows["death_rate"]["low"])
        self.assertIsNone(rows["death_rate"]["high"])
        self.assertEqual(rows["death_rate"]["unit"], "per 100,000 population")
        self.assertEqual(next(ctx["rate_type"] for row, ctx in zip(result["data"], result["observation_context"])
                              if row["measure"] == "death_rate"), "crude")

    def test_invalid_selections_fail_without_widening(self):
        cases = [
            {"area": ["ZZZ"]}, {"sex": ["BOTHSEX"]}, {"age": ["ALLAGE"]}, {"cause": ["999999"]},
            {"cause": ["0 or 1 eq 1"]}, {"measure": ["age_standardized_rate"]}, {"measure": None},
            {"area": None}, {"year": [2023.5]}, {"year": [True]}, {"year": [2099]},
            {"year_from": 2020}, {"year": None, "year_from": 2024, "year_to": 2020},
            {"year": None, "year_from": [2020, 2021]}, {"sex": []}, {"cause": [True]}]
        for change in cases:
            with self.subTest(change=change):
                self.assert_code("invalid_query", self.client.get_data, **{**self.selection, **change})

    def test_absent_measure_field_is_not_filled_or_inferred(self):
        for row in self.fixture.rows:
            del row["VAL_DTHS_RATE100K_NUMERIC"]
        self.assertNotIn("death_rate", [row["code"] for row in self.client.dimensions("measure")])
        self.assert_code("invalid_query", self.client.get_data, **self.selection)

    def test_verified_empty_query_is_complete_without_zero_rows(self):
        result = self.client.get_data(**{**self.selection, "year": None, "year_from": 2099, "year_to": 2099})
        self.assertEqual(result["status"], "filters_no_data")
        self.assertEqual(result["data"], [])
        self.assertTrue(result["provenance"]["complete"])
        self.assertEqual(result["provenance"]["source_rows"], 0)
        self.assertEqual(result["coverage_by_location"][0]["years"], [])

    def test_latest_dated_mapping_is_not_a_regional_aggregate(self):
        result = self.client.locations(["Philippines", "NA", "156"])
        self.assertEqual([row["code"] for row in result["locations"]], ["PHL", "NAM", "CHN"])
        result = self.client.locations(["PHL", "WPRO", "Imaginary country"])
        self.assertEqual(result["status"], "needs_clarification")
        self.assertEqual(len(result["unresolved"]), 2)

    def test_provider_area_outside_country_mapping_retains_unknown_label(self):
        extra = copy.deepcopy(self.selected_row())
        extra.update(Sys_PK=10000, DIM_COUNTRY_CODE="XZZ")
        self.fixture.rows.append(extra)
        result = self.client.get_data(**{**self.selection, "area": ["XZZ"]})
        self.assertTrue(all(row["location_name"] is None for row in result["data"]))

    def test_coverage_counts_source_rows_not_measures_or_deaths(self):
        result = self.client.coverage(area=["PHL", "CHN"], sex=["TOTAL"], age=["TOTAL"], cause=["0"])
        self.assertEqual([row["source_rows"] for row in result["coverage_by_location"]], [2, 2])
        self.assertEqual(result["coverage_by_location"][0]["years"], [2022, 2023])

    def test_pagination_all_pages_and_original_filters(self):
        self.client.http.page_size = 2
        result = self.client.get_data(**{**self.selection, "year": [2022, 2023], "sex": ["FEMALE", "MALE"]})
        self.assertEqual(result["provenance"]["pages"], 2)
        self.assertEqual(result["provenance"]["source_rows"], 4)
        self.assertEqual(len(result["data"]), 8)

    def test_provider_ignoring_a_selected_filter_is_rejected(self):
        original = self.fixture.__call__
        def altered(url, **kwargs):
            result = original(url, **kwargs)
            if "$select=Sys_PK%2CDIM_COUNTRY_CODE%2CDIM_YEAR_CODE" in url:
                for row in result["value"]:
                    row["DIM_SEX_CODE"] = "MALE"
            return result
        self.client.http.transport = altered
        self.assert_code("invalid_response", self.client.get_data, **self.selection)

    def test_duplicate_strata_are_retained_but_fail_qa(self):
        duplicate = copy.deepcopy(self.selected_row())
        duplicate["Sys_PK"] = 10000
        self.fixture.rows.append(duplicate)
        result = self.client.get_data(**self.selection)
        self.assertEqual(result["status"], "qa_failed")
        self.assertEqual(len(result["raw"]), 2)

    def test_bad_values_fail_without_becoming_missing_or_zero(self):
        for value in ("<0.1", True, "not available"):
            with self.subTest(value=value):
                self.selected_row()["VAL_DTHS_COUNT_NUMERIC"] = value
                self.assert_code("invalid_response", self.client.get_data, **self.selection)
        self.selected_row()["VAL_DTHS_COUNT_NUMERIC"] = -1
        self.assertEqual(self.client.get_data(**self.selection)["status"], "qa_failed")

    def test_reversed_intervals_fail_qa(self):
        self.selected_row()["VAL_DTHS_COUNT_LOW"] = 1000
        self.assertEqual(self.client.get_data(**self.selection)["status"], "qa_failed")

    def test_missing_or_inconsistent_counts_and_identifiers_fail(self):
        examples = [
            [{"value": []}],
            [{"@odata.count": True, "value": []}],
            [{"@odata.count": 1.5, "value": []}],
            [{"@odata.count": 2, "value": []}],
            [{"@odata.count": 2, "value": [{"Sys_PK": 1}]}, {"@odata.count": 3, "value": [{"Sys_PK": 2}]}],
            [{"@odata.count": 2, "value": [{"Sys_PK": 1}]}, {"@odata.count": 2, "value": [{"Sys_PK": 1}]}],
            [{"@odata.count": 1, "value": [{"Sys_PK": None}]}]]
        for pages in examples:
            with self.subTest(pages=pages):
                stream = iter(pages)
                transport = Transport(page_size=1, transport=lambda *args, **kwargs: next(stream))
                self.assert_code("incomplete_data", transport.collection, "DIM_YEAR_CODE eq 2023", ["Sys_PK"])

    def test_schema_change_and_limits_reject_partial_downloads(self):
        pages = iter([{"@odata.count": 2, "value": [{"Sys_PK": 1, "a": 1}]},
                      {"@odata.count": 2, "value": [{"Sys_PK": 2}]}])
        transport = Transport(page_size=1, transport=lambda *args, **kwargs: next(pages))
        self.assert_code("invalid_response", transport.collection, "", ["Sys_PK"])
        for limits, code in (({"max_rows": 1}, "response_limit"), ({"max_pages": 1}, "incomplete_data")):
            transport = Transport(page_size=1, transport=lambda *a, **k: {"@odata.count": 2, "value": [{"Sys_PK": 1}]}, **limits)
            self.assert_code(code, transport.collection, "", ["Sys_PK"])

    def test_reference_truncation_and_malformed_codes(self):
        for payload in ({"value": [{"CODE": 1, "TITLE": "a"}] * 20},
                        {"value": [{"CODE": 1, "TITLE": "a"}], "@odata.nextLink": "next"}):
            self.assert_code("incomplete_data", Transport(transport=lambda *a, **k: payload).reference,
                             "DEX_CMS/REF_SEX_COD", 20)
        self.assert_code("invalid_catalogue", Transport(transport=lambda *a, **k: {"value": []}).reference,
                         "DEX_CMS/REF_SEX_COD", 20)

    def test_network_failure_is_not_absence_and_retries_are_bounded(self):
        attempts = []
        def failed(*args, **kwargs):
            attempts.append(1)
            raise TimeoutError("synthetic timeout")
        transport = Transport(transport=failed, retries=2, sleep=lambda _: None)
        error = self.assert_code("who_api_request_failed", transport.request, TABLE)
        self.assertEqual(error.details["failure_kind"], "network_error")
        self.assertEqual(len(attempts), 2)

    def test_http_404_and_503_do_not_become_missing_indicators(self):
        for status in (404, 503):
            calls = []
            def failed(url, **kwargs):
                calls.append(1)
                raise urllib.error.HTTPError(url, status, "synthetic", {}, None)
            transport = Transport(transport=failed, retries=2, sleep=lambda _: None)
            error = self.assert_code("who_api_request_failed", transport.request, TABLE)
            self.assertEqual(error.details["http_status"], status)
            self.assertEqual(len(calls), 1 if status == 404 else 2)

    def test_html_and_bad_json_are_failures(self):
        class Response(io.BytesIO):
            headers = {"Content-Type": "application/json"}
            def geturl(self):
                return BASE_URL + "/" + TABLE
        for content, code in ((b"not json", "invalid_response"), (b"<html>unavailable</html>", "api_unavailable")):
            transport = Transport(retries=1)
            transport.opener = mock.Mock()
            transport.opener.open.return_value = Response(content)
            self.assert_code(code, transport.request, TABLE)

    def test_truncated_oversize_response_is_a_limit_error_before_json_parsing(self):
        class Response(io.BytesIO):
            headers = {"Content-Type": "application/json"}
            def geturl(self):
                return BASE_URL + "/" + TABLE
        transport = Transport(max_bytes=20, retries=1)
        transport.opener = mock.Mock()
        transport.opener.open.return_value = Response(b'{"value":[' + b' ' * 100 + b']}')
        self.assert_code("response_limit", transport.request, TABLE)
        self.assertEqual(transport.trace[-1]["code"], "response_limit")

    def test_out_of_range_number_is_an_invalid_response(self):
        self.selected_row()["VAL_DTHS_COUNT_NUMERIC"] = 10 ** 400
        self.assert_code("invalid_response", self.client.get_data, **self.selection)

    def test_urls_and_pagination_cannot_change_source(self):
        for url in ("http://xmart-api-public.who.int/DEX_CMS/GHE_FULL",
                    BASE_URL + "/DATA_/RELAY_WHS", BASE_URL + "/DEX_CMS/OTHER",
                    BASE_URL + ":444/DEX_CMS/GHE_FULL", "https://evil.example/DEX_CMS/GHE_FULL",
                    "https://user@xmart-api-public.who.int/DEX_CMS/GHE_FULL",
                    BASE_URL + "/DEX_CMS/GHE_FULL#fragment"):
            with self.subTest(url=url):
                self.assert_code("unsafe_api_link", validate_url, url)
        payload = {"@odata.count": 2, "value": [{"Sys_PK": 1}], "@odata.nextLink": "https://evil.example/page"}
        self.assert_code("unsafe_api_link", Transport(transport=lambda *a, **k: payload).collection, "", ["Sys_PK"])

    def test_long_requests_use_only_official_query_endpoint(self):
        calls = []
        transport = Transport(transport=lambda url, **kwargs: calls.append((url, kwargs)) or {"value": []})
        transport.request(TABLE, {"$filter": "a" * 1900})
        self.assertEqual(calls[0][0], BASE_URL + "/" + TABLE + "/$query")
        self.assertEqual(calls[0][1]["method"], "POST")
        self.assertTrue(calls[0][1]["body"].startswith(b"$filter="))

    def test_exports_keep_csv_schema_missingness_original_rows_and_hashes(self):
        self.selected_row()["VAL_DTHS_COUNT_NUMERIC"] = None
        result = self.client.get_data(**self.selection)
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "export"
            files = write_result(destination, result)
            self.assertTrue(Path(files["data.csv"]).read_bytes().startswith(b"\xef\xbb\xbf"))
            with Path(files["data.csv"]).open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                self.assertEqual(tuple(reader.fieldnames), DATA_FIELDS)
                self.assertEqual(next(row for row in reader if row["measure"] == "deaths")["value"], "")
            self.assertEqual(json.loads(Path(files["raw.json"]).read_text()), result["raw"])
            manifest = json.loads(Path(files["manifest.json"]).read_text())
            for name, digest in manifest["files"].items():
                self.assertEqual(hashlib.sha256((destination / name).read_bytes()).hexdigest(), digest)
            self.assert_code("output_exists", write_result, destination, result)

    def test_cli_failure_exports_diagnostics_without_fake_csv(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "failure"
            args = ["get", "--area", "PHL", "--year", "2023", "--sex", "TYPO",
                    "--age", "TOTAL", "--cause", "0", "--measure", "deaths", "--output-dir", str(destination)]
            with mock.patch("cli.GHEClient", return_value=self.client), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(args), 2)
            response = json.loads((destination / "response.json").read_text())
            self.assertEqual(response["error"]["code"], "invalid_query")
            self.assertFalse(response["provenance"]["complete"])
            self.assertFalse((destination / "data.csv").exists())

    def test_export_write_failures_never_leave_a_successful_partial_result(self):
        result = self.client.get_data(**self.selection)
        original_write = Path.write_text
        def fail_manifest(path, *args, **kwargs):
            if path.name == "manifest.json":
                raise OSError("synthetic manifest write failure")
            return original_write(path, *args, **kwargs)
        for failure in (mock.patch("cli.csv.DictWriter.writerows", side_effect=OSError("synthetic CSV failure")),
                        mock.patch.object(Path, "write_text", fail_manifest)):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as folder, failure:
                destination = Path(folder) / "export"
                with self.assertRaises(OSError):
                    write_result(destination, result)
                self.assertFalse(destination.exists())
                self.assertEqual(list(Path(folder).iterdir()), [])

    def test_cli_export_failure_saves_only_error_diagnostics(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "failure"
            args = ["get", "--area", "PHL", "--year", "2023", "--sex", "TOTAL",
                    "--age", "TOTAL", "--cause", "0", "--measure", "deaths", "--output-dir", str(destination)]
            output = io.StringIO()
            with mock.patch("cli.GHEClient", return_value=self.client), contextlib.redirect_stdout(output), \
                    mock.patch("cli.csv.DictWriter.writerows", side_effect=OSError("synthetic CSV failure")):
                self.assertEqual(main(args), 2)
            response = json.loads((destination / "response.json").read_text())
            self.assertEqual(response["status"], "error")
            self.assertFalse(response["provenance"]["complete"])
            self.assertEqual(set(path.name for path in destination.iterdir()), {"response.json", "manifest.json"})
            self.assertEqual(json.loads(output.getvalue())["status"], "error")

    def test_client_limits_reject_invalid_inputs(self):
        for options in ({"page_size": 0}, {"page_size": 120001}, {"max_rows": True},
                        {"timeout": float("nan")}, {"retries": 0}):
            with self.subTest(options=options):
                self.assert_code("invalid_query", Transport, **options)


if __name__ == "__main__":
    unittest.main()
