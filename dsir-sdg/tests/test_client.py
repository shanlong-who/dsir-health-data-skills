"""Synthetic API contracts: pagination, filters and explicit failure classes."""
import http.client
import socket
import sys
import unittest
import urllib.error
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from sdg_client import SDGClient, SDGError, validate_url


INDICATORS = [{"code": "3.2.1", "description": "Under-five mortality rate"},
              {"code": "3.8.1", "description": "UHC service coverage"}]
SERIES = [{"code": "RATE_TEST", "description": "Synthetic rate", "indicator": ["3.2.1"]},
          {"code": "COUNT_TEST", "description": "Synthetic count", "indicator": ["3.2.1"]},
          {"code": "UHC_TEST", "description": "Synthetic index", "indicator": ["3.8.1"]}]
AREAS = [{"geoAreaCode": "608", "geoAreaName": "Philippines"},
         {"geoAreaCode": "156", "geoAreaName": "China"},
         {"geoAreaCode": "1", "geoAreaName": "World"}]


def observation(year=2020, **overrides):
    record = {"indicator": ["3.2.1"], "series": "RATE_TEST", "geoAreaCode": "608",
              "timePeriodStart": year, "value": "10.5", "dimensions": {"Sex": "BOTHSEX"},
              "attributes": {"Units": "PER_1000_LIVE_BIRTHS"}}
    record.update(overrides)
    return record


def page(records, *, number=1, total=None, pages=1, **metadata):
    return {"data": records, "pageNumber": number,
            "totalElements": len(records) if total is None else total,
            "totalPages": pages, **metadata}


def client(transport, **kwargs):
    output = SDGClient(transport=transport, sleep=lambda _: None, **kwargs)
    output._cache = {"Indicator": INDICATORS, "Series": SERIES, "GeoArea": AREAS}
    return output


class ClientTests(unittest.TestCase):
    def assert_code(self, expected, fn):
        with self.assertRaises(SDGError) as caught:
            fn()
        self.assertEqual(caught.exception.code, expected)

    def test_complete_pagination_and_union_of_dimension_metadata(self):
        responses = iter([
            page([observation(2020), observation(2021)], total=3, pages=2,
                 dimensions=[{"id": "Sex", "codes": [{"code": "BOTHSEX"}]}]),
            page([observation(2022)], number=2, total=3, pages=2,
                 dimensions=[{"id": "Age", "codes": [{"code": "ALLAGE"}]}])])
        result = client(lambda _: next(responses), page_size=2).get_sdg_data("3.2.1")
        self.assertEqual([r["timePeriodStart"] for r in result["records"]], [2020, 2021, 2022])
        self.assertEqual(result["pages"], 2)
        self.assertEqual({m["id"] for m in result["metadata"]["dimensions"]}, {"Sex", "Age"})

    def test_repeated_keys_and_local_year_filter(self):
        urls = []
        def transport(url):
            urls.append(url)
            return page([observation(2014), observation(2015), observation(2020), observation(2021)])
        result = client(transport).get_sdg_data("3.2.1", ["608", "156"], year_from=2015, year_to=2020)
        query = parse_qs(urlsplit(urls[0]).query)
        self.assertEqual(query["areaCode"], ["608", "156"])
        self.assertNotIn("timePeriodStart", query)
        self.assertNotIn("timePeriodEnd", query)
        self.assertEqual([r["timePeriodStart"] for r in result["records"]], [2015, 2020])

    def test_page_count_change_is_failure(self):
        responses = iter([page([observation()], total=2, pages=2),
                          page([observation(2021)], number=2, total=3, pages=2)])
        self.assert_code("incomplete_data", lambda: client(lambda _: next(responses)).get_sdg_data("3.2.1"))

    def test_repeated_page_is_failure(self):
        responses = iter([page([observation()], total=2, pages=2),
                          page([observation()], number=2, total=2, pages=2)])
        self.assert_code("incomplete_data", lambda: client(lambda _: next(responses)).get_sdg_data("3.2.1"))

    def test_missing_intermediate_page_is_failure(self):
        self.assert_code("incomplete_data", lambda: client(lambda _: page([], total=2, pages=2)).get_sdg_data("3.2.1"))

    def test_final_count_mismatch_is_failure(self):
        self.assert_code("incomplete_data", lambda: client(lambda _: page([observation()], total=2)).get_sdg_data("3.2.1"))

    def test_missing_or_wrong_pagination_counter_is_failure(self):
        for override in ({"pageNumber": 0}, {"pageNumber": 2}, {"totalElements": "1"}, {"totalPages": None}):
            body = page([observation()])
            body.update(override)
            with self.subTest(override=override):
                self.assert_code("incomplete_data", lambda: client(lambda _: body).get_sdg_data("3.2.1"))

    def test_contradictory_total_and_page_counters_fail(self):
        for body in (page([observation()], total=1, pages=0), page([], total=0, pages=2)):
            self.assert_code("incomplete_data", lambda: client(lambda _: body).get_sdg_data("3.2.1"))

    def test_row_and_page_limits_fail_without_partial_success(self):
        for limits in ({"max_rows": 1}, {"max_pages": 1}):
            self.assert_code("incomplete_data", lambda: client(lambda _: page([observation()], total=2, pages=2), **limits).get_sdg_data("3.2.1"))

    def test_server_ignoring_area_or_indicator_filter_is_failure(self):
        for record in (observation(geoAreaCode="156"), observation(indicator=["3.8.1"])):
            self.assert_code("invalid_response", lambda: client(lambda _: page([record])).get_sdg_data("3.2.1", ["608"]))

    def test_scalar_indicator_in_response_is_allowed(self):
        result = client(lambda _: page([observation(indicator="3.2.1")])).get_sdg_data("3.2.1")
        self.assertEqual(result["status"], "ok")

    def test_invalid_shape_not_treated_as_no_data(self):
        for body in ({}, [], {"data": None}, page([1])):
            with self.subTest(body=body):
                self.assert_code("invalid_response", lambda: client(lambda _: body).get_sdg_data("3.2.1"))

    def test_series_and_dimension_and_attribute_filters(self):
        rows = [observation(dimensions={"Sex": "F"}), observation(dimensions={"Sex": "M"}),
                observation(series="COUNT_TEST", dimensions={"Sex": "F"})]
        result = client(lambda _: page(rows)).get_sdg_data(
            "3.2.1", series="RATE_TEST", dimensions={"Sex": ["F"]},
            attributes={"Units": "PER_1000_LIVE_BIRTHS"})
        self.assertEqual(result["records"], rows[:1])
        self.assertEqual(result["retrieved_row_count"], 3)

    def test_unknown_dimension_is_invalid_filter(self):
        self.assert_code("invalid_filter", lambda: client(lambda _: page([observation()])).get_sdg_data("3.2.1", dimensions={"Wrong": "F"}))

    def test_nonexistent_dimension_value_gives_filtered_empty(self):
        result = client(lambda _: page([observation()])).get_sdg_data("3.2.1", dimensions={"Sex": "NOT_PRESENT"})
        self.assertEqual(result["status"], "filters_no_data")

    def test_unknown_indicator_never_fetches_data(self):
        calls = []
        self.assert_code("indicator_not_found", lambda: client(lambda u: calls.append(u)).get_sdg_data("99.99.99"))
        self.assertEqual(calls, [])

    def test_foreign_series_never_fetches_data(self):
        calls = []
        self.assert_code("series_not_found", lambda: client(lambda u: calls.append(u)).get_sdg_data("3.2.1", series="UHC_TEST"))
        self.assertEqual(calls, [])

    def test_invalid_year_filters(self):
        for query in ({"year_from": True}, {"year_from": "2020"}, {"year_to": 2020.5},
                      {"year_from": 2022, "year_to": 2020}, {"year_from": -1}):
            self.assert_code("invalid_query", lambda: client(lambda _: None).get_sdg_data("3.2.1", **query))

    def test_invalid_filter_shapes_including_falsy_values(self):
        for key in ("dimensions", "attributes"):
            for value in ([], "", 0, False, {"Sex": []}, {"Sex": 5}, {"Sex": [None]}):
                with self.subTest(key=key, value=value):
                    self.assert_code("invalid_query", lambda: client(lambda _: page([observation()])).get_sdg_data("3.2.1", **{key: value}))

    def test_invalid_and_unknown_resolved_area_codes(self):
        for areas in ([], ["PHL"], "608", [608]):
            self.assert_code("invalid_query", lambda: client(lambda _: None).get_sdg_data("3.2.1", areas))
        self.assert_code("location_not_found", lambda: client(lambda _: None).get_sdg_data("3.2.1", ["999999"]))

    def test_year_filter_cannot_succeed_if_year_column_is_missing(self):
        record = observation()
        del record["timePeriodStart"]
        self.assert_code("invalid_response", lambda: client(lambda _: page([record])).get_sdg_data("3.2.1", year_from=2015))

    def test_non_numeric_year_is_excluded_by_filter(self):
        result = client(lambda _: page([observation(None), observation(2020)])).get_sdg_data("3.2.1", year_from=2015)
        self.assertEqual(len(result["records"]), 1)

    def test_globally_empty_indicator_is_distinct(self):
        result = client(lambda _: page([], total=0, pages=0)).get_sdg_data("3.2.1")
        self.assertEqual(result["status"], "indicator_no_data")

    def test_empty_area_with_global_data_is_filtered_empty(self):
        def transport(url):
            return page([], pages=0) if "areaCode" in parse_qs(urlsplit(url).query) else page([observation()], total=10, pages=10)
        result = client(transport).get_sdg_data("3.2.1", ["608"])
        self.assertEqual(result["status"], "filters_no_data")
        self.assertEqual(result["baseline_probe"]["global_indicator_rows"], 10)

    def test_failed_baseline_probe_is_api_failure(self):
        def transport(url):
            if "areaCode" in parse_qs(urlsplit(url).query):
                return page([], pages=0)
            raise urllib.error.HTTPError(url, 503, "Synthetic outage", {}, None)
        self.assert_code("un_api_request_failed", lambda: client(transport, retries=1).get_sdg_data("3.2.1", ["608"]))

    def test_retry_after_honored_then_success(self):
        attempts, delays = [], []
        def transport(url):
            attempts.append(url)
            if len(attempts) == 1:
                raise urllib.error.HTTPError(url, 429, "Synthetic rate limit", {"Retry-After": "3"}, None)
            return INDICATORS
        instance = SDGClient(transport=transport, sleep=delays.append)
        self.assertEqual(instance.indicators(), INDICATORS)
        self.assertEqual(delays, [3])

    def test_http404_is_not_catalogue_absence(self):
        def transport(url):
            raise urllib.error.HTTPError(url, 404, "Synthetic failure", {}, None)
        self.assert_code("un_api_request_failed", lambda: client(transport).get_sdg_data("3.2.1"))

    def test_truncated_network_and_timeout_errors_are_structured(self):
        for error in (http.client.IncompleteRead(b"partial", 50), socket.timeout("Synthetic timeout"), urllib.error.URLError("Synthetic blocked network")):
            def transport(_):
                raise error
            self.assert_code("un_api_request_failed", lambda: client(transport, retries=1).get_sdg_data("3.2.1"))

    def test_failed_catalogue_is_not_cached(self):
        responses = iter([[], INDICATORS])
        instance = SDGClient(transport=lambda _: next(responses))
        self.assert_code("invalid_response", instance.indicators)
        self.assertEqual(instance.indicators(), INDICATORS)
        self.assertEqual(instance.indicators(), INDICATORS)

    def test_foreign_or_malformed_api_urls_rejected(self):
        for url in ("https://example.com/sdgs/UNSDGAPIV5/v1/sdg/Indicator/List",
                    "https://unstats.un.org:invalid/sdgs/UNSDGAPIV5/v1/sdg/Indicator/List",
                    "http://unstats.un.org/sdgs/UNSDGAPIV5/v1/sdg/Indicator/List",
                    "https://unstats.un.org/sdgs/UNSDGAPIV5/v1/sdg/%2E%2E/other"):
            self.assert_code("unsafe_api_link", lambda: validate_url(url))

    def test_client_limits_are_validated(self):
        for limits in ({"retries": 0}, {"page_size": 10001}, {"page_size": True}, {"timeout": float("inf")}):
            self.assert_code("invalid_query", lambda: SDGClient(**limits))


if __name__ == "__main__":
    unittest.main()
