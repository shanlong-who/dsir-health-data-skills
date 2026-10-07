"""Synthetic xMart contracts. These fixtures are never WHO observations."""
import copy
import json
import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from gho_client import GHOClient, GHOError, BASE_URL, validate_url
from xmart import dimension_fields, numeric_display
from clean import clean_records, CORE_FIELDS
from cli import build_response
from indicator_search import describe_indicator


def directory(**changes):
    row = {"IND_ID": "SYNTHETIC_ID", "IND_PER_CODE": "TEST", "IND_CODE_GHO": "TEST",
           "IND_NAME_FULL": "Synthetic xMart measure", "IND_NAME": "Synthetic measure",
           "TERM_LANG": "en", "IND_UNIT": "test units", "IND_PUBLISH_TABLE": None,
           "DWNL_QUERY": "https://private-uat.example/DATA_/data/RELAY_TEST?$select=DIM_AGE,DIM_SEX"}
    return row | changes


GEO = [
    {"Sys_PK": 1, "GEO_CODE_M49": "608", "GEO_CODE_ISO_3": "PHL", "GEO_TYPE": "COUNTRY", "GEO_NAME_SHORT": "Philippines"},
    {"Sys_PK": 2, "GEO_CODE_M49": "958", "GEO_CODE_ISO_3": None, "GEO_TYPE": "WHOREGION", "GEO_NAME_SHORT": "Western Pacific"},
    {"Sys_PK": 3, "GEO_CODE_M49": "953", "GEO_CODE_ISO_3": None, "GEO_TYPE": "WHOREGION", "GEO_NAME_SHORT": "Africa"},
    {"Sys_PK": 4, "GEO_CODE_M49": "002", "GEO_CODE_ISO_3": None, "GEO_TYPE": "REGION", "GEO_NAME_SHORT": "Africa"},
    {"Sys_PK": 5, "GEO_CODE_M49": "001", "GEO_CODE_ISO_3": None, "GEO_TYPE": "GLOBAL", "GEO_NAME_SHORT": "World"},
    {"Sys_PK": 6, "GEO_CODE_M49": "772", "GEO_CODE_ISO_3": "TKL", "GEO_TYPE": "TERRITORY", "GEO_NAME_SHORT": "Tokelau"},
]


def wide(**changes):
    row = {"Sys_PK": 1, "_RecordID": "source-test-1", "IND_ID": "SYNTHETIC_ID",
           "DIM_TIME": "2023", "DIM_TIME_TYPE": "YEAR", "DIM_GEO_CODE_M49": "608",
           "DIM_GEO_CODE_TYPE": "COUNTRY", "GEO_NAME_SHORT": "Philippines",
           "DIM_AGE": "Y40T44", "DIM_SEX": "FEMALE", "DIM_CURRENCY": "USD", "DIM_OTHER": "extra",
           "VALUE_LABEL": "<10", "AMOUNT_N": 10, "AMOUNT_NL": 9, "AMOUNT_NU": 11,
           "Sys_CommitDateUtc": "2026-10-07", "VALUE_PROVENANCE": "synthetic source", "VALUE_COMMENTS": None}
    return row | changes


def long(**changes):
    row = {"Sys_PK": 1, "_RecordID": "source-test-1", "IND_ID": "SYNTHETIC_ID",
           "DIM_TIME": "2023", "DIM_TIME_TYPE": "YEAR", "DIM_GEO_CODE_M49": "608", "DIM_GEO_CODE_TYPE": "COUNTRY",
           "VALUE_LABEL": "10", "VALUE_NUMERIC": 10, "VALUE_NUMERIC_LOWER": 9, "VALUE_NUMERIC_UPPER": 11,
           "DIM_1_CODE": "DIM_POP_SEX", "DIM_MEMBER_1_CODE": "FMLE",
           "DIM_2_CODE": "DIM_POP_AGE_GRP", "DIM_MEMBER_2_CODE": "YEARS18-PLUS",
           "DIM_3_CODE": None, "DIM_MEMBER_3_CODE": None,
           "DIM_4_CODE": "DIM_OTHER", "DIM_MEMBER_4_CODE": "retained"}
    return row | changes


class FixtureTransport:
    def __init__(self, observations=None, entries=None):
        self.observations = observations or [wide()]
        self.entries = entries or [directory()]
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        query = parse_qs(kwargs["body"].decode() if kwargs.get("body") else urlsplit(url).query)
        path = urlsplit(url).path.removesuffix("/$query")
        if path.endswith("IND_DIRECTORY_WIDE"):
            rows = self.entries
        elif path.endswith("REF_GEO"):
            rows = GEO
        elif path.endswith("REF_DISAGGREGATIONS"):
            rows = [{"TERM_SET": "DIM_SEX", "TERM_KEY": "FEMALE", "TERM_NAME_MAIN": "Female"}]
        else:
            rows = self.observations
        if "$apply" in query:
            fields = query["$orderby"][0].split(",")
            unique = {json.dumps({f: r.get(f) for f in fields}, sort_keys=True): {f: r.get(f) for f in fields} for r in rows}
            rows = list(unique.values())
            count = 99999999  # Grouped count describes facts, never groups.
        else:
            count = len(rows)
        offset, size = int(query.get("$skip", [0])[0]), int(query.get("$top", [5000])[0])
        return {"value": copy.deepcopy(rows[offset:offset + size]), "@odata.count": count}


class XMartTests(unittest.TestCase):
    def client(self, observations=None, entries=None, **kwargs):
        transport = FixtureTransport(observations, entries)
        return GHOClient(transport=transport, **kwargs), transport

    def assert_error(self, expected, function):
        with self.assertRaises(GHOError) as caught:
            function()
        self.assertEqual(caught.exception.code, expected)

    def test_default_and_explicit_backend_selection(self):
        self.assertEqual(GHOClient().backend, "xmart")
        self.assertEqual(GHOClient(backend="legacy").backend, "legacy")
        self.assert_error("invalid_query", lambda: GHOClient(backend="auto"))
        self.assert_error("invalid_query", lambda: GHOClient(page_size=120001))

    def test_urls_reject_legacy_uat_private_or_other_marts(self):
        for url in ("http://xmart-api-public.who.int/DATA_/RELAY_TEST", "https://xmart-api-public-uat.who.int/DATA_/RELAY_TEST",
                    "https://ghoapi.azureedge.net/api/TEST", BASE_URL + "/DEX_CMS/GHE_FULL",
                    BASE_URL + "/DATA_/data/RELAY_TEST", BASE_URL + "/DATA_/../RELAY_TEST",
                    "https://user@xmart-api-public.who.int/DATA_/RELAY_TEST"):
            self.assert_error("unsafe_api_link", lambda: validate_url(url))

    def test_query_encoding_preserves_odata_parameter_names(self):
        url = GHOClient().url("DATA_/RELAY_TEST", {"$top": 1, "$filter": "DIM_SEX eq 'TOTAL'"})
        self.assertIn("$top=1", url)
        self.assertIn("$filter=DIM_SEX%20eq%20%27TOTAL%27", url)
        self.assertNotIn("%24", url)

    def test_directory_routing_extracts_object_never_follows_hostname(self):
        client, transport = self.client()
        result = client.get_gho_data("TEST")
        self.assertEqual(result["provenance"]["table"], "DATA_/RELAY_TEST")
        self.assertTrue(all(urlsplit(url).hostname == "xmart-api-public.who.int" for url, _ in transport.calls))
        self.assertEqual(result["indicator"]["Unit"], "test units")

    def test_directory_deduplicates_catalogue_but_prefers_downloadable_route(self):
        client, _ = self.client(entries=[directory(DWNL_QUERY=None, IND_PER_CODE="OTHER"), directory()])
        self.assertEqual(len(client.catalogue()), 1)
        self.assertEqual(client._xmart.route("TEST")["path"], "DATA_/RELAY_TEST")

    def test_directory_name_fallback_is_catalogue_only(self):
        client, _ = self.client(entries=[directory(IND_NAME_FULL=None)])
        self.assertEqual(client.catalogue()[0]["IndicatorName"], "Synthetic measure")
        self.assertIsNone(client.get_gho_data("TEST")["records"][0]["IndicatorName"])

    def test_no_route_or_unknown_code_never_falls_back(self):
        client, transport = self.client(entries=[directory(DWNL_QUERY="https://example.org/DEX_CMS/GHE_FULL")])
        self.assert_error("unsupported_indicator_route", lambda: client.get_gho_data("TEST"))
        self.assert_error("indicator_not_found", lambda: client.get_gho_data("INVENTED"))
        self.assertTrue(all("ghoapi" not in url for url, _ in transport.calls))

    def test_failed_directory_is_not_cached(self):
        replies = iter([{"value": [], "@odata.count": 0}, {"value": [directory()], "@odata.count": 1}])
        client = GHOClient(transport=lambda _: next(replies))
        self.assert_error("invalid_catalogue", client.catalogue)
        self.assertEqual(client.catalogue()[0]["IndicatorCode"], "TEST")
        self.assertEqual(client.catalogue()[0]["IndicatorCode"], "TEST")

    def test_duplicate_directory_identity_fails(self):
        client, _ = self.client(entries=[directory(), directory()])
        self.assert_error("invalid_catalogue", client.catalogue)

    def test_wide_normalization_preserves_core_bounds_and_extra_dimensions(self):
        client, _ = self.client()
        result = client.get_gho_data("TEST")
        row = result["records"][0]
        self.assertEqual((row["Dim1"], row["Dim2"], row["Dim3"]), ("SEX_FMLE", "AGEGROUP_Y40T44", "USD"))
        self.assertEqual((row["NumericValue"], row["Low"], row["High"]), (10, 9, 11))
        self.assertEqual(row["Value"], "<10")
        self.assertEqual(row["DIM_OTHER"], "extra")
        self.assertEqual(result["source_records"][0], wide())
        self.assertEqual(tuple(clean_records(result["records"], client.catalogue())[0]), CORE_FIELDS)

    def test_dimension_order_comes_from_schema_even_all_null(self):
        self.assertEqual(dimension_fields(["DIM_Z", "DIM_AGE", "DIM_SEX", "DIM_TIME", "DIM_4_CODE"]), ["DIM_SEX", "DIM_AGE", "DIM_Z"])
        client, _ = self.client([wide(DIM_SEX=None)])
        row = client.get_gho_data("TEST")["records"][0]
        self.assertIsNone(row["Dim1"])
        self.assertIsNone(row["Dim1Type"])
        self.assertEqual(row["Dim2"], "AGEGROUP_Y40T44")

    def test_long_normalization_retains_row_types_and_beyond_core_positions(self):
        client, _ = self.client([long(), long(Sys_PK=2, DIM_1_CODE="DIM_AGE", DIM_MEMBER_1_CODE="Y40T44")])
        rows = client.get_gho_data("TEST")["records"]
        self.assertEqual(rows[0]["Dim1"], "SEX_FMLE")
        self.assertEqual(rows[1]["Dim1"], "AGEGROUP_Y40T44")
        self.assertEqual(rows[0]["DIM_POP_SEX"], "FMLE")
        self.assertIsNone(rows[1]["DIM_POP_SEX"])
        self.assertEqual(rows[0]["DIM_MEMBER_4_CODE"], "retained")

    def test_named_wide_filters_use_exact_native_codes(self):
        client, _ = self.client()
        context = client._xmart.context("TEST", dimensions={"DIM_SEX": "TOTAL", "DIM_AGE": "Y40T44"})
        self.assertIn("DIM_SEX eq 'TOTAL'", context["filter"])
        self.assertIn("DIM_AGE eq 'Y40T44'", context["filter"])
        self.assert_error("invalid_query", lambda: client.get_gho_data("TEST", dimensions={"DIM_MADE_UP": "X"}))

    def test_describe_exposes_native_named_values(self):
        client, _ = self.client()
        result = describe_indicator("TEST", client)
        self.assertEqual(result["observed_named_dimension_values"]["DIM_SEX"], ["FEMALE"])
        self.assertEqual(result["observed_named_dimension_values"]["DIM_OTHER"], ["extra"])
        self.assertEqual(result["observed_dimension_values"]["dim1"][0]["code"], "SEX_FMLE")

    def test_named_long_filters_discover_actual_type_positions(self):
        client, _ = self.client([long()])
        context = client._xmart.context("TEST", dimensions={"DIM_POP_SEX": "FMLE"})
        self.assertIn("DIM_1_CODE eq 'DIM_POP_SEX'", context["filter"])
        self.assertIn("DIM_MEMBER_1_CODE eq 'FMLE'", context["filter"])
        self.assertNotIn("DIM_MEMBER_2_CODE", context["filter"])
        self.assert_error("invalid_query", lambda: client.get_gho_data("TEST", dimensions={"DIM_UNKNOWN": "X"}))

    def test_long_type_discovery_batches_at_most_six_order_fields(self):
        row = long()
        row.update({f"DIM_{i}_CODE": f"DIM_TEST_{i}" for i in range(5, 13)})
        client, transport = self.client([row])
        client.indicator_dimensions("TEST")
        grouped = [parse_qs(urlsplit(url).query) for url, _ in transport.calls if "$apply" in parse_qs(urlsplit(url).query)]
        self.assertEqual(len(grouped), 2)
        self.assertTrue(all(len(q["$orderby"][0].split(",")) <= 6 for q in grouped))

    def test_positional_wide_translates_canonical_sex_and_age_only(self):
        client, _ = self.client()
        context = client._xmart.context("TEST", dimensions={"dim1": "SEX_BTSX", "dim2": "AGEGROUP_Y40T44"})
        self.assertIn("DIM_SEX eq 'TOTAL'", context["filter"])
        self.assertIn("DIM_AGE eq 'Y40T44'", context["filter"])

    def test_positional_long_supports_population_sex_and_age(self):
        client, _ = self.client([long()])
        context = client._xmart.context("TEST", dimensions={"dim1": "SEX_FMLE", "dim2": "AGEGROUP_YEARS18-PLUS"})
        self.assertIn("'DIM_POP_SEX'", context["filter"])
        self.assertIn("DIM_MEMBER_1_CODE eq 'FMLE'", context["filter"])
        self.assertIn("DIM_MEMBER_2_CODE eq 'YEARS18-PLUS'", context["filter"])

    def test_geography_converts_m49_and_distinguishes_who_and_un_regions(self):
        client, _ = self.client()
        self.assertEqual(client._xmart.geo_code("WPR"), "958")
        self.assertEqual(client._xmart.geo_code("AFR"), "953")
        self.assertEqual(client._xmart.geo_code("002", inverse=True), "002")
        self.assertEqual(client._xmart.geo_code("PHL"), "608")
        self.assertEqual(client._xmart.geo_code("958", inverse=True), "WPR")

    def test_country_and_year_filters_use_source_fields(self):
        client, _ = self.client()
        context = client._xmart.context("TEST", locations=["PHL"], year_from=2015, year_to=2023)
        self.assertIn("DIM_GEO_CODE_M49 eq '608'", context["filter"])
        self.assertIn("DIM_TIME ge '2015'", context["filter"])
        self.assertEqual(context["query"]["spatial_type"], "COUNTRY")

    def test_nonannual_time_retains_detail_without_invented_year(self):
        client, _ = self.client([wide(DIM_TIME="2023-Q1", DIM_TIME_TYPE="QUARTER")])
        row = client.get_gho_data("TEST")["records"][0]
        self.assertIsNone(row["TimeDim"])
        self.assertEqual(row["TimeDimensionValue"], "2023-Q1")

    def test_multiple_measure_families_are_failure_not_arbitrary_choice(self):
        client, _ = self.client([wide(PERCENT_N=8)])
        self.assert_error("ambiguous_measure", lambda: client.get_gho_data("TEST"))

    def test_missing_numeric_preserves_literal_thresholds(self):
        client, _ = self.client([wide(AMOUNT_N=None, VALUE_LABEL="NA")])
        row = client.get_gho_data("TEST")["records"][0]
        self.assertIsNone(row["NumericValue"])
        self.assertIsNone(row["MeasureField"])
        self.assertIsNone(row["Low"])
        self.assertEqual(row["Value"], "NA")

    def test_missing_display_uses_dsir_numeric_formatting(self):
        self.assertEqual([numeric_display(x) for x in (10000, 100000, 0.00001, 123.12345678912345, None)],
                         ["10000", "1e+05", "1e-05", "123.123456789123", None])

    def test_source_name_and_nonmember_spatial_name_match_dsir_0110(self):
        client, _ = self.client([wide(DIM_GEO_CODE_M49="772", GEO_NAME_SHORT="Tokelau")])
        row = clean_records(client.get_gho_data("TEST")["records"], client.catalogue())[0]
        self.assertEqual(row["location_name"], "Tokelau")
        self.assertIsNone(row["iso3"])

    def test_long_queries_use_read_only_post_query(self):
        client, transport = self.client()
        client.collection("DATA_/RELAY_TEST", {"$filter": in_filter_for_test()}, paged=True)
        url, kwargs = transport.calls[-1]
        self.assertTrue(url.endswith("/$query"))
        self.assertEqual(kwargs["method"], "POST")
        self.assertIn(b"$filter=", kwargs["body"])
        self.assertEqual(client.trace[-1]["method"], "POST")
        self.assertTrue(client.trace[-1]["query_body_sha256"])

    def test_groupby_uses_short_pages_and_ignores_underlying_fact_count(self):
        client, _ = self.client([long()], page_size=1)
        result = client.collection("DATA_/RELAY_TEST", group=["DIM_1_CODE"])
        self.assertEqual(len(result["records"]), 1)
        self.assertEqual(result["provenance"]["pages"], 2)
        self.assertTrue(result["provenance"]["complete"])

    def test_count_changes_missing_pages_and_overlap_are_failures(self):
        for second in ({"value": [wide(Sys_PK=3)], "@odata.count": 4}, {"value": [], "@odata.count": 3},
                       {"value": [wide(Sys_PK=2)], "@odata.count": 3}):
            replies = iter([{"value": [wide(Sys_PK=1), wide(Sys_PK=2)], "@odata.count": 3}, second])
            client = GHOClient(transport=lambda _: next(replies), page_size=2)
            self.assert_error("incomplete_data", lambda: client.collection("DATA_/RELAY_TEST", {"$orderby": "Sys_PK"}, paged=True))

    def test_schema_and_type_drift_are_failures(self):
        for second in (wide(Sys_PK=2, NEW_FIELD="x"), wide(Sys_PK=2, AMOUNT_N="10")):
            replies = iter([{"value": [wide()], "@odata.count": 2}, {"value": [second], "@odata.count": 2}])
            client = GHOClient(transport=lambda _: next(replies), page_size=1)
            self.assert_error("incomplete_data", lambda: client.collection("DATA_/RELAY_TEST", {"$orderby": "Sys_PK"}, paged=True))

    def test_missing_count_and_identifiers_are_failures(self):
        client = GHOClient(transport=lambda _: {"value": [wide()]})
        self.assert_error("incomplete_data", lambda: client.collection("DATA_/RELAY_TEST", paged=True))
        client = GHOClient(transport=lambda _: {"value": [wide(Sys_PK=None)], "@odata.count": 1})
        self.assert_error("incomplete_data", lambda: client.collection("DATA_/RELAY_TEST", {"$orderby": "Sys_PK"}, paged=True))

    def test_wrong_indicator_and_nested_fields_are_not_results(self):
        for observation in (wide(IND_ID="WRONG"), wide(AMOUNT_N={"fake": 1})):
            client, _ = self.client([observation])
            self.assert_error("invalid_response", lambda: client.get_gho_data("TEST"))

    def test_response_provenance_context_and_named_filter_qa(self):
        client, _ = self.client()
        result = client.get_gho_data("TEST", dimensions={"DIM_SEX": "TOTAL"})
        response = build_response(result, client)
        self.assertEqual(response["status"], "qa_failed")  # Injected source ignores the filter.
        self.assertEqual(response["provenance"]["reference_dsir_version"], "0.11.0")
        self.assertEqual(response["observation_context"][0]["DIM_OTHER"], "extra")
        self.assertEqual(response["row_count"], 1)

    def test_named_long_qa_uses_native_fields_beyond_core_positions(self):
        client, _ = self.client([long(DIM_4_CODE="DIM_TEST_12")])
        result = client.get_gho_data("TEST", dimensions={"DIM_TEST_12": "retained"})
        response = build_response(result, client)
        self.assertNotIn("named_dimension_filter_mismatch", [issue["code"] for issue in response["qa"]["issues"]])

    def test_named_long_qa_checks_types_without_dim_prefix(self):
        client, _ = self.client([long(DIM_1_CODE="SEX", DIM_MEMBER_1_CODE="FMLE")])
        result = client.get_gho_data("TEST", dimensions={"SEX": "MLE"})
        response = build_response(result, client)
        self.assertEqual(response["status"], "qa_failed")
        self.assertIn("named_dimension_filter_mismatch", [issue["code"] for issue in response["qa"]["issues"]])

    def test_verified_empty_classification_uses_counted_baseline(self):
        for baseline_exists, expected in ((True, "filters_no_data"), (False, "indicator_no_data")):
            fixture = FixtureTransport()
            def transport(url):
                query = parse_qs(urlsplit(url).query)
                if urlsplit(url).path.endswith("RELAY_TEST") and "$filter" in query:
                    baseline = "DIM_TIME" not in query["$filter"][0]
                    rows = [wide()] if baseline and baseline_exists else []
                    return {"value": rows, "@odata.count": len(rows)}
                return fixture(url)
            client = GHOClient(transport=transport)
            result = client.get_gho_data("TEST", year_from=2099)
            self.assertEqual(result["status"], expected)
            self.assertEqual(result["records"], [])
            self.assertTrue(result["provenance"]["complete"])

    def test_empty_baseline_without_valid_count_is_a_failure(self):
        fixture = FixtureTransport()
        def transport(url):
            query = parse_qs(urlsplit(url).query)
            if urlsplit(url).path.endswith("RELAY_TEST") and "$filter" in query:
                return {"value": [], "@odata.count": 0} if "DIM_TIME" in query["$filter"][0] else {"value": []}
            return fixture(url)
        client = GHOClient(transport=transport)
        self.assert_error("incomplete_data", lambda: client.get_gho_data("TEST", year_from=2099))

    def test_declared_row_limit_is_enforced_before_more_pages(self):
        calls = []
        def transport(url):
            calls.append(url)
            return {"value": [wide()], "@odata.count": 100}
        client = GHOClient(transport=transport, max_rows=10)
        self.assert_error("incomplete_data", lambda: client.collection("DATA_/RELAY_TEST", paged=True))
        self.assertEqual(len(calls), 1)


def in_filter_for_test():
    return "DIM_OTHER in (" + ",".join("'" + "synthetic" * 10 + str(i) + "'" for i in range(50)) + ")"


if __name__ == "__main__":
    unittest.main()
