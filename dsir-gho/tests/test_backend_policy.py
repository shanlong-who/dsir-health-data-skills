"""Phase 1 contracts use synthetic records; no WHO values are assumed."""
import io
import json
import sys
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from gho_client import GHOClient, GHOError, LEGACY_BASE_URL, BASE_URL
from cli import main, parser, build_response
from indicator_search import search_indicators, describe_indicator, basic_metadata
from test_xmart import FixtureTransport, directory, wide, long


CATALOGUE = [{"IndicatorCode": "TEST", "IndicatorName": "Synthetic indicator"}]


class LegacyFixture:
    """Small OData fixture with distinct type/code/baseline probes."""
    def __init__(self, rows=None, types=None, empty=False):
        self.rows = rows if rows is not None else [{
            "Id": 1, "IndicatorCode": "TEST", "SpatialDim": "PHL",
            "SpatialDimType": "COUNTRY", "TimeDim": 2020,
            "Dim1Type": "SEX", "Dim1": "SEX_FMLE", "Dim2Type": "AGEGROUP",
            "Dim2": "AGEGROUP_Y40T44", "NumericValue": None, "Value": "Not available"}]
        self.types = types or {"Dim1Type": ["SEX"], "Dim2Type": ["AGEGROUP"]}
        self.empty = empty
        self.calls = []

    def __call__(self, url):
        self.calls.append(url)
        path = urlsplit(url).path
        query = parse_qs(urlsplit(url).query)
        if path.endswith("/Indicator"):
            rows = CATALOGUE
        elif "/DIMENSION/" in path:
            kind = path.split("/")[-2]
            rows = [{"Code": c, "Title": c} for c in {
                "SEX": ["SEX_FMLE", "SEX_MLE", "SEX_BTSX"],
                "AGEGROUP": ["AGEGROUP_Y40T44", "AGEGROUP_Y45T49"]}[kind]]
        elif "$select" in query and query["$select"][0].endswith("Type"):
            field = query["$select"][0]
            rows = [{field: t} for t in self.types.get(field, [])
                    if f"ne '{t}'" not in query.get("$filter", [""])[0]]
        elif query.get("$select") == ["Id"]:
            rows = [{"Id": r["Id"]} for r in self.rows]
        else:
            rows = [] if self.empty else self.rows
        size = int(query.get("$top", [1000])[0])
        return {"value": rows[:size], "@odata.count": len(rows)}


class BackendPolicyTests(unittest.TestCase):
    def error(self, expected, call):
        with self.assertRaises(GHOError) as caught:
            call()
        self.assertEqual(caught.exception.code, expected)
        return caught.exception

    def test_client_cli_and_page_defaults_agree(self):
        self.assertEqual((GHOClient().backend, GHOClient().page_size), ("legacy", 1000))
        self.assertEqual(GHOClient(backend="xmart").page_size, 5000)
        self.assertEqual(parser().parse_args(["doctor"]).backend, "legacy")
        stream = io.StringIO()
        with patch("cli.GHOClient", return_value=GHOClient(transport=LegacyFixture())) as factory, redirect_stdout(stream):
            self.assertEqual(main(["doctor"]), 0)
        factory.assert_called_once_with(backend="legacy", page_size=None)
        self.assertEqual(json.loads(stream.getvalue())["backend"], "legacy")

    def test_page_limits_rejected_before_network(self):
        for backend, limit in (("legacy", 1000), ("xmart", 120000)):
            self.error("invalid_query", lambda: GHOClient(backend=backend, page_size=limit + 1))
            for size in (0, -1, True, 2.5):
                self.error("invalid_query", lambda: GHOClient(backend=backend).collection("TEST", page_size=size))

    def test_default_legacy_observation_request_respects_cap(self):
        transport = LegacyFixture()
        result = GHOClient(transport=transport).get_gho_data("TEST")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(all(int(parse_qs(urlsplit(u).query).get("$top", [1])[0]) <= 1000 for u in transport.calls))

    def test_absence_is_scoped_and_never_falls_back(self):
        for backend, transport in (("legacy", LegacyFixture()), ("xmart", FixtureTransport())):
            client = GHOClient(backend=backend, transport=transport)
            exc = self.error("indicator_not_found", lambda: client.get_gho_data("ABSENT"))
            self.assertEqual(exc.details["backend"], backend)
            self.assertFalse(exc.details["fallback_performed"])
            self.assertTrue(exc.details["catalogue"]["complete"])
            self.assertTrue(all(t["backend"] == backend for t in client.trace))

    def test_exact_numeric_dotted_catalogue_code_is_retrievable(self):
        transport = FixtureTransport(entries=[directory(IND_CODE_GHO="2017_AH_6.3", IND_PER_CODE="2017_AH_6.3")])
        result = GHOClient(backend="xmart", transport=transport).get_gho_data("2017_AH_6.3")
        self.assertEqual(result["records"][0]["IndicatorCode"], "2017_AH_6.3")

    def test_search_and_metadata_use_actual_backend(self):
        for backend, transport, suffix in (("legacy", LegacyFixture(), "/Indicator"),
                                            ("xmart", FixtureTransport(), "/DATA_/IND_DIRECTORY_WIDE")):
            client = GHOClient(backend=backend, transport=transport)
            result = search_indicators("TEST", client)
            self.assertEqual(result["backend"], backend)
            self.assertEqual(result["catalogue_source"], client.base_url + suffix)
            self.assertTrue(result["provenance"]["complete"])
        self.assertTrue(basic_metadata(CATALOGUE[0])["metadata_source"].startswith(LEGACY_BASE_URL))

    def test_selected_route_supplies_matching_metadata(self):
        entries = [directory(IND_ID="OTHER", IND_PER_CODE="OTHER", DWNL_QUERY=None,
                             IND_UNIT="wrong unit", IND_NAME_FULL="Other variant"), directory()]
        client = GHOClient(backend="xmart", transport=FixtureTransport(entries=entries))
        result = client.get_gho_data("TEST")
        response = build_response(result, client)
        self.assertEqual(response["indicator"]["unit"], "test units")
        self.assertEqual(response["indicator"]["name"], "Synthetic xMart measure")
        description = describe_indicator("TEST", client)
        self.assertEqual(description["unit"], "test units")
        self.assertEqual(description["name"], response["indicator"]["name"])

    def test_route_absence_is_not_indicator_absence(self):
        client = GHOClient(backend="xmart", transport=FixtureTransport(entries=[directory(DWNL_QUERY=None)]))
        exc = self.error("unsupported_indicator_route", lambda: client.get_gho_data("TEST"))
        self.assertFalse(exc.details["fallback_performed"])

    def test_http_failures_have_distinct_reasons_and_no_fallback(self):
        for backend in ("legacy", "xmart"):
            for status, kind in ((400, "invalid_request"), (404, "http_error"),
                                 (429, "temporarily_unavailable"), (503, "temporarily_unavailable")):
                def transport(url):
                    raise urllib.error.HTTPError(url, status, "synthetic failure", {}, None)
                client = GHOClient(backend=backend, transport=transport, retries=1)
                exc = self.error("who_api_request_failed", client.catalogue)
                self.assertEqual(exc.details["failure_kind"], kind)
                self.assertEqual(client.trace[-1]["http_status"], status)
                self.assertTrue(all(r["backend"] == backend for r in client.trace))

    def test_network_failure_is_not_empty_or_absent(self):
        def transport(url):
            raise urllib.error.URLError("synthetic network denial")
        client = GHOClient(transport=transport, retries=1)
        exc = self.error("who_api_request_failed", client.catalogue)
        self.assertEqual(exc.details["failure_kind"], "network_error")

    def test_invalid_json_is_not_empty(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def geturl(self): return LEGACY_BASE_URL + "/TEST"
            def read(self, size): return b'{"value":'
        client = GHOClient(retries=1)
        with patch.object(client._opener, "open", return_value=Response()):
            self.error("invalid_response", lambda: client.collection("TEST"))

    def test_legacy_sex_and_age_codes_keep_missing_values(self):
        client = GHOClient(transport=LegacyFixture())
        result = client.get_gho_data("TEST", locations=["PHL"], year_from=2020, year_to=2020,
                                     dimensions={"dim1": ["SEX_FMLE"], "dim2": ["AGEGROUP_Y40T44"]})
        response = build_response(result, client)
        self.assertIsNone(response["data"][0]["value_num"])
        self.assertEqual(response["data"][0]["dim2"], "AGEGROUP_Y40T44")
        self.assertEqual(response["qa"]["status"], "warning")

    def test_legacy_invalid_sibling_and_wrong_position_are_errors(self):
        for dimensions in ({"dim1": ["SEX_FMLE", "TYPO"]}, {"dim2": ["SEX_FMLE"]}, {"dim3": ["SEX_FMLE"]}):
            client = GHOClient(transport=LegacyFixture())
            self.error("invalid_query", lambda: client.get_gho_data("TEST", dimensions=dimensions))

    def test_legacy_valid_unobserved_code_is_empty_selection(self):
        client = GHOClient(transport=LegacyFixture(empty=True))
        result = client.get_gho_data("TEST", year_from=2099, dimensions={"dim1": "SEX_MLE"})
        self.assertEqual(result["status"], "filters_no_data")
        self.assertEqual(result["records"], [])

    def test_empty_baseline_requires_consistent_count(self):
        for payload in ({"value": []}, {"value": [], "@odata.count": 2}):
            fixture = LegacyFixture(empty=True)
            def transport(url):
                return payload if parse_qs(urlsplit(url).query).get("$select") == ["Id"] else fixture(url)
            self.error("incomplete_data", lambda: GHOClient(transport=transport).get_gho_data("TEST", year_from=2099))

    def test_empty_indicator_remains_distinct(self):
        result = GHOClient(transport=LegacyFixture(rows=[], empty=True)).get_gho_data("TEST", year_from=2099)
        self.assertEqual(result["status"], "indicator_no_data")

    def test_missing_observation_identifier_is_incomplete(self):
        row = LegacyFixture().rows[0] | {"Id": None}
        self.error("incomplete_data", lambda: GHOClient(transport=LegacyFixture(rows=[row])).get_gho_data("TEST"))

    def test_xmart_named_and_positional_invalid_codes(self):
        for dimensions in ({"DIM_SEX": ["FEMALE", "TYPO"]}, {"DIM_SEX": "SEX_FMLE"},
                           {"dim1": "TYPO"}, {"DIM_AGE": "BAD_AGE"}):
            client = GHOClient(backend="xmart", transport=FixtureTransport())
            self.error("invalid_query", lambda: client.get_gho_data("TEST", dimensions=dimensions))

    def test_xmart_unverifiable_codes_do_not_claim_empty_data(self):
        client = GHOClient(backend="xmart", transport=FixtureTransport())
        self.error("unverified_dimension", lambda: client.get_gho_data("TEST", dimensions={"DIM_OTHER": "UNKNOWN"}))

    def test_xmart_age_and_sex_are_not_dropped(self):
        client = GHOClient(backend="xmart", transport=FixtureTransport())
        result = client.get_gho_data("TEST", dimensions={"DIM_SEX": "FEMALE", "DIM_AGE": "Y40T44"})
        self.assertEqual(result["records"][0]["Dim2"], "AGEGROUP_Y40T44")
        self.assertEqual(result["source_records"][0]["DIM_SEX"], "FEMALE")


if __name__ == "__main__":
    unittest.main()
