"""Synthetic failure and completeness tests; no internet or cached WHO data."""
import json
import http.client
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from functools import partial
from gho_client import GHOClient as BackendClient, GHOError, LEGACY_BASE_URL as BASE_URL, literal, validate_url as backend_url, validate_code

# The original transport contracts explicitly exercise the retained adapter.
GHOClient = partial(BackendClient, backend="legacy")
validate_url = partial(backend_url, backend="legacy")
from indicator_search import search_indicators, basic_metadata


CATALOGUE = [
    {"IndicatorCode": "UHC_TEST", "IndicatorName": "UHC Service Coverage Index test", "Language": "EN"},
    {"IndicatorCode": "RATE_TEST", "IndicatorName": "Incidence of tuberculosis (per 100 000 population per year)", "Language": "EN"},
    {"IndicatorCode": "COUNT_TEST", "IndicatorName": "Number of incident tuberculosis cases", "Language": "EN"},
    {"IndicatorCode": "MEASLES_TEST", "IndicatorName": "Measles - number of reported cases", "Language": "EN"},
]


class StaticCatalogue:
    def catalogue(self):
        return CATALOGUE


def row(identifier, indicator="UHC_TEST", year=2000):
    return {"Id": identifier, "IndicatorCode": indicator, "SpatialDim": "PHL",
            "SpatialDimType": "COUNTRY", "TimeDim": year, "NumericValue": 1}


class ClientTests(unittest.TestCase):
    def assert_error(self, code, function):
        with self.assertRaises(GHOError) as caught:
            function()
        self.assertEqual(caught.exception.code, code)

    def test_manual_skip_without_nextlink(self):
        data = [row(i) for i in range(5)]
        def transport(url):
            query = parse_qs(urlsplit(url).query)
            start = int(query.get("$skip", [0])[0])
            return {"value": data[start:start + 2], "@odata.count": len(data)}
        result = GHOClient(transport=transport, page_size=2).collection("UHC_TEST", {"$orderby": "Id"}, paged=True)
        self.assertEqual(result["records"], data)
        self.assertEqual(result["provenance"]["pages"], 3)
        self.assertTrue(result["provenance"]["complete"])

    def test_nextlink_and_empty_page(self):
        responses = iter([{"value": [], "@odata.nextLink": BASE_URL + "/X?$skip=1"}, {"value": [row(1)]}])
        self.assertEqual(len(GHOClient(transport=lambda _: next(responses)).collection("X")["records"]), 1)

    def test_cycle_is_failure(self):
        self.assert_error("incomplete_data", lambda: GHOClient(transport=lambda url: {"value": [], "@odata.nextLink": url}).collection("X"))

    def test_foreign_nextlink_is_failure(self):
        self.assert_error("unsafe_api_link", lambda: GHOClient(transport=lambda _: {"value": [], "@odata.nextLink": "https://example.org/api/X"}).collection("X"))

    def test_changed_entity_is_failure(self):
        self.assert_error("unsafe_api_link", lambda: GHOClient(transport=lambda _: {"value": [], "@odata.nextLink": BASE_URL + "/Y"}).collection("X"))

    def test_invalid_shape_not_empty(self):
        for value in ({}, {"value": None}, {"value": [1]}, [], "maintenance"):
            with self.subTest(value=value):
                self.assert_error("invalid_response", lambda: GHOClient(transport=lambda _: value).collection("X"))

    def test_missing_count_managed_paging_fails(self):
        self.assert_error("incomplete_data", lambda: GHOClient(transport=lambda _: {"value": []}).collection("X", paged=True))

    def test_empty_array_stays_zero_rows(self):
        output = GHOClient(transport=lambda _: {"value": [], "@odata.count": 0}).collection("X", paged=True)
        self.assertEqual(output["records"], [])

    def test_premature_end_not_success(self):
        self.assert_error("incomplete_data", lambda: GHOClient(transport=lambda _: {"value": [], "@odata.count": 10}).collection("X", paged=True))

    def test_count_changed_fails(self):
        responses = iter([{"value": [row(1)], "@odata.count": 2}, {"value": [row(2)], "@odata.count": 3}])
        self.assert_error("incomplete_data", lambda: GHOClient(transport=lambda _: next(responses), page_size=1).collection("X", paged=True))

    def test_page_limit_fails(self):
        self.assert_error("incomplete_data", lambda: GHOClient(transport=lambda _: {"value": [row(1)], "@odata.count": 2}, page_size=1, max_pages=1).collection("X", paged=True))

    def test_top_probe_is_marked_incomplete(self):
        result = GHOClient(transport=lambda _: {"value": [row(1)], "@odata.count": 10}).collection("X", {"$top": 1})
        self.assertFalse(result["provenance"]["complete"])

    def test_http_retry_then_success(self):
        attempts, waits = [], []
        def transport(url):
            attempts.append(url)
            if len(attempts) < 3:
                raise urllib.error.HTTPError(url, 503, "unavailable", None, None)
            return {"value": []}
        GHOClient(transport=transport, sleep=waits.append).collection("X")
        self.assertEqual(len(attempts), 3)
        self.assertEqual(waits, [2, 4])

    def test_http_404_not_indicator_absence(self):
        def transport(url):
            raise urllib.error.HTTPError(url, 404, "missing", None, None)
        self.assert_error("who_api_request_failed", lambda: GHOClient(transport=transport).collection("X"))

    def test_network_error_not_absence(self):
        def transport(url):
            raise urllib.error.URLError("network not permitted")
        self.assert_error("who_api_request_failed", lambda: GHOClient(transport=transport, sleep=lambda _: None).collection("X"))

    def test_truncated_http_read_is_structured_failure(self):
        def transport(url):
            raise http.client.IncompleteRead(b"partial", 50)
        self.assert_error("who_api_request_failed", lambda: GHOClient(transport=transport, retries=2, sleep=lambda _: None).collection("X"))

    def test_malformed_nextlink_port_is_structured_failure(self):
        self.assert_error("unsafe_api_link", lambda: validate_url("https://ghoapi.azureedge.net:invalid/api/X"))

    def test_successful_catalogue_cache_only(self):
        attempts = []
        def transport(url):
            attempts.append(url)
            return {"value": CATALOGUE if len(attempts) > 1 else [], "@odata.count": len(CATALOGUE) if len(attempts) > 1 else 0}
        client = GHOClient(transport=transport)
        self.assert_error("invalid_catalogue", client.catalogue)
        self.assertEqual(client.catalogue(), CATALOGUE)
        self.assertEqual(client.catalogue(), CATALOGUE)
        self.assertEqual(len(attempts), 2)

    def test_no_fabricated_indicator(self):
        client = GHOClient()
        client._catalogue = CATALOGUE
        self.assert_error("indicator_not_found", lambda: client.get_gho_data("MADE_UP_INDICATOR"))
        for value in (None, "", "NA;drop", "../Indicator", "x?$filter=a"):
            self.assert_error("invalid_query", lambda: client.get_gho_data(value))

    def test_hyphens_are_valid_but_catalogue_confirmation_still_required(self):
        self.assertEqual(validate_code("GHED_GGHE-DGDP_SHA2011"), "GHED_GGHE-DGDP_SHA2011")
        client = GHOClient()
        client._catalogue = CATALOGUE
        self.assert_error("indicator_not_found", lambda: client.confirm_indicator("SYNTHETIC-NOT-PRESENT"))

    def test_validated_years(self):
        client = GHOClient()
        client._catalogue = CATALOGUE
        for kwargs in ({"year_from": 2025, "year_to": 2000}, {"year_from": True}, {"year_to": 2020.5}, {"year_from": "2020"}):
            self.assert_error("invalid_query", lambda: client.get_gho_data("UHC_TEST", **kwargs))

    def test_filter_escaping(self):
        urls = []
        def transport(url):
            urls.append(url)
            return {"value": [], "@odata.count": 0}
        client = GHOClient(transport=transport)
        client._catalogue = CATALOGUE
        resolved = {"status": "ok", "locations": [{"code": "O'NEIL", "spatial_type": "country"}]}
        with patch("locations.resolve_locations", return_value=resolved):
            client.get_gho_data("UHC_TEST", ["O'NEIL"], dimensions={"dim1": ["A'B"]}, spatial_type="COUNTRY")
        query = parse_qs(urlsplit(urls[0]).query)["$filter"][0]
        self.assertIn("'O''NEIL'", query)
        self.assertIn("'A''B'", query)

    def test_explicit_type_cannot_bypass_location_validation(self):
        client = GHOClient(transport=lambda _: {"value": [], "@odata.count": 0})
        client._catalogue = CATALOGUE
        self.assert_error("unknown_location", lambda: client.get_gho_data("UHC_TEST", ["Atlantis"], spatial_type="COUNTRY"))
        self.assert_error("invalid_query", lambda: client.get_gho_data("UHC_TEST", ["PHL"], spatial_type="REGION"))

    def test_invalid_filter_shapes(self):
        client = GHOClient()
        client._catalogue = CATALOGUE
        for kwargs in ({"locations": 15}, {"dimensions": ["x"]}, {"dimensions": {"dim1": 5}}):
            self.assert_error("invalid_query", lambda: client.get_gho_data("UHC_TEST", **kwargs))

    def test_empty_result_classification(self):
        for baseline, expected in (([], "indicator_no_data"), ([{"Id": 99}], "filters_no_data")):
            def transport(url):
                query = parse_qs(urlsplit(url).query)
                return {"value": baseline} if "$select" in query else {"value": [], "@odata.count": 0}
            client = GHOClient(transport=transport)
            client._catalogue = CATALOGUE
            self.assertEqual(client.get_gho_data("UHC_TEST", year_from=2099)["status"], expected)

    def test_baseline_probe_failure_not_no_data(self):
        def transport(url):
            if "$select" in parse_qs(urlsplit(url).query):
                raise urllib.error.HTTPError(url, 500, "bad", None, None)
            return {"value": [], "@odata.count": 0}
        client = GHOClient(transport=transport, retries=1)
        client._catalogue = CATALOGUE
        self.assert_error("who_api_request_failed", lambda: client.get_gho_data("UHC_TEST", year_from=2099))

    def test_repeated_ids_fail_without_dropping(self):
        client = GHOClient(transport=lambda _: {"value": [row(1), row(1)], "@odata.count": 2})
        client._catalogue = CATALOGUE
        self.assert_error("incomplete_data", lambda: client.get_gho_data("UHC_TEST"))


class SearchTests(unittest.TestCase):
    def test_aliases_select_only_real_catalogue_candidates(self):
        result = search_indicators("UHC SCI", StaticCatalogue())
        self.assertEqual(result["candidates"][0]["code"], "UHC_TEST")
        self.assertTrue(all(r["code"] in {x["IndicatorCode"] for x in CATALOGUE} for r in result["candidates"]))

    def test_tb_incidence_preserves_ambiguity(self):
        result = search_indicators("TB incidence", StaticCatalogue())
        self.assertEqual({r["code"] for r in result["candidates"]}, {"RATE_TEST", "COUNT_TEST"})
        self.assertTrue(result["selection_notes"])

    def test_typo_fuzzy(self):
        result = search_indicators("measels reported", StaticCatalogue())
        self.assertEqual(result["candidates"][0]["code"], "MEASLES_TEST")

    def test_no_matches_not_api_failure(self):
        self.assertEqual(search_indicators("zzzzzzqqqq", StaticCatalogue())["status"], "no_matches")

    def test_exact_code_case_insensitive(self):
        self.assertEqual(search_indicators("rate_test", StaticCatalogue())["candidates"][0]["score"], 1000)

    def test_unknown_unit_remains_null(self):
        meta = basic_metadata({"IndicatorCode": "ABC", "IndicatorName": "Health indicator"})
        self.assertIsNone(meta["unit"])
        self.assertIsNone(meta["definition"])

    def test_explicit_unit_extraction(self):
        self.assertEqual(basic_metadata(CATALOGUE[1])["unit"], "per 100 000 population per year")


if __name__ == "__main__":
    unittest.main()
