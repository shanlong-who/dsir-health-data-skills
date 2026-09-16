"""Run API/data contracts. Natural-language response criteria remain manual."""
from __future__ import annotations

import argparse
import json
import socket
import sys
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from gho_client import GHOClient, GHOError, BASE_URL
from indicator_search import search_indicators, describe_indicator
from locations import resolve_locations
from clean import clean_records, CORE_FIELDS


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def validate_casebook(book):
    """Validate question-level expectations before any WHO request is made."""
    require(isinstance(book, dict) and isinstance(book.get("cases"), list), "Casebook must contain a cases array")
    cases = book["cases"]
    ids = set()
    mandatory = {"id", "user_question", "expected_locations", "expected_year_logic",
                 "should_clarify", "important_notes", "operation", "expect", "synthetic_input"}
    operations = {"data", "pagination", "search", "resolve", "describe", "fixture"}
    for case in cases:
        require(isinstance(case, dict) and mandatory.issubset(case), "Case is missing required question-level fields")
        label = case["id"]
        require(isinstance(label, str) and bool(label) and label not in ids, "Case IDs must be nonempty and unique")
        ids.add(label)
        require(case["operation"] in operations, f"{label}: unknown operation")
        require(isinstance(case["user_question"], str) and len(case["user_question"].strip()) >= 10,
                f"{label}: user_question must be a natural-language question")
        require(case.get("prompt") == case["user_question"], f"{label}: prompt compatibility differs from user_question")
        require(isinstance(case["should_clarify"], bool), f"{label}: should_clarify must be boolean")
        require(isinstance(case["synthetic_input"], bool), f"{label}: synthetic_input must be boolean")
        require(isinstance(case["expected_locations"], list) and
                all(isinstance(code, str) and bool(code) for code in case["expected_locations"]),
                f"{label}: expected_locations must be a code array")
        require(isinstance(case["expected_year_logic"], str) and len(case["expected_year_logic"].strip()) >= 20,
                f"{label}: expected_year_logic must state the selection rule")
        require(isinstance(case["important_notes"], list) and bool(case["important_notes"]) and
                all(isinstance(note, str) and bool(note.strip()) for note in case["important_notes"]),
                f"{label}: important_notes must contain substantive notes")
        require("expected_indicator_code" in case or "expected_candidates" in case,
                f"{label}: an expected indicator or candidates is required")
        if "expected_indicator_code" in case:
            require(isinstance(case["expected_indicator_code"], str) and bool(case["expected_indicator_code"]),
                    f"{label}: expected_indicator_code must be a nonempty string")
        if "expected_candidates" in case:
            require(isinstance(case["expected_candidates"], list) and
                    all(isinstance(code, str) and bool(code) for code in case["expected_candidates"]),
                    f"{label}: expected_candidates must be a code array")
        if case["operation"] in {"data", "pagination"}:
            require(case["expected_indicator_code"] == case["args"]["indicator"], f"{label}: indicator expectation conflicts with executable args")
            require(case["expected_locations"] == case["args"].get("locations", []), f"{label}: location expectation conflicts with executable args")
        if case["operation"] == "describe":
            require(case["expected_indicator_code"] == case["code"], f"{label}: metadata indicator expectations differ")
        if case["operation"] == "search":
            required = set(case["expect"].get("required_candidates", []))
            if case["expect"].get("top_candidate"):
                required.add(case["expect"]["top_candidate"])
            require(required.issubset(case["expected_candidates"]), f"{label}: candidate expectation conflicts with executable contract")
        if case["operation"] == "fixture":
            require(case["synthetic_input"] is True and
                    any("synthetic" in note.lower() for note in case["important_notes"]),
                    f"{label}: injected failure/cleaner cases must be labelled synthetic")
    real_questions = sum(not case["synthetic_input"] for case in cases)
    health_data_questions = sum(not case["synthetic_input"] and case["operation"] in
                                {"data", "pagination", "search", "describe"} for case in cases)
    require(health_data_questions >= 20, "At least 20 nonsynthetic natural-language health-data questions are required")
    return {"total_cases": len(cases), "non_synthetic_questions": real_questions,
            "non_synthetic_health_data_questions": health_data_questions,
            "synthetic_cases": len(cases) - real_questions, "required_fields_valid": True}


def fixture_case(name):
    """Test transport failures with injected responses, never live fake data."""
    calls = []
    sample = {"Id": 1, "IndicatorCode": "WHS3_62", "SpatialDimType": "COUNTRY",
              "SpatialDim": "PHL", "TimeDim": 2021, "NumericValue": 0, "Value": "0"}
    def transport(url):
        calls.append(url)
        if name == "network_failure":
            raise socket.timeout("Injected timeout for a failure-path test")
        if name in {"http_503", "retry_success"}:
            if name == "http_503" or len(calls) == 1:
                raise urllib.error.HTTPError(url, 503, "Injected unavailable response", {}, None)
        if name == "invalid_schema":
            return {"unexpected": []}
        if name == "paging_cycle":
            return {"value": [sample], "@odata.count": 3,
                    "@odata.nextLink": BASE_URL + "/WHS3_62?repeat=1"}
        if name == "count_changes":
            return {"value": [dict(sample, Id=len(calls))], "@odata.count": 2 if len(calls) == 1 else 3}
        if name == "missing_page":
            return {"value": [sample] if len(calls) == 1 else [], "@odata.count": 2}
        if name == "unsafe_next_link":
            return {"value": [sample], "@odata.count": 2,
                    "@odata.nextLink": "https://example.com/untrusted-page"}
        if name == "indicator_no_data":
            return {"value": [], "@odata.count": 0}
        return {"value": [sample], "@odata.count": 1}

    client = GHOClient(transport=transport, retries=3, page_size=1, sleep=lambda _: None)
    # A real catalogue identity; test responses are explicitly synthetic.
    client._catalogue = [{"IndicatorCode": "WHS3_62",
                          "IndicatorName": "Measles - number of reported cases", "Language": "EN"}]
    if name == "clean_missingness":
        records = [{"IndicatorCode": "WHS3_62", "SpatialDim": "WPR_WO_IDN", "TimeDim": 2021,
                    "Value": "<0.1", "NumericValue": None, "Dim1": "SEX_BTSX"}]
        records.append(dict(records[0]))
        cleaned = clean_records(records, client._catalogue)
        require(len(cleaned) == 2, "Cleaner changed duplicate row count")
        require(tuple(cleaned[0]) == tuple(CORE_FIELDS), "Cleaner schema/order differs")
        for row in cleaned:
            require(row["value"] == "<0.1" and row["value_num"] is None, "Missing numeric value was guessed")
            require(row["iso3"] is None and row["location_name"] is None, "Unknown DSIR location was silently enriched")
            require(row["dim1"] == "SEX_BTSX" and row["dim2"] is None, "Dimension missingness changed")
            require(row["low"] is None and row["high"] is None and row["series"] is None, "Missing fields changed")
        return {"status": "ok", "rows": 2, "attempts": 0}
    try:
        if name == "indicator_no_data":
            result = client.get_gho_data("WHS3_62", locations=["PHL"], spatial_type="COUNTRY")
        else:
            result = client.collection("WHS3_62", paged=True)
            result["status"] = "ok"
        return {"status": result["status"], "rows": len(result["records"]), "attempts": len(calls)}
    except GHOError as exc:
        result = exc.as_dict()
        result["attempts"] = len(calls)
        return result


def check_case(case, client, catalogue):
    operation, expected = case["operation"], case["expect"]
    if operation == "fixture":
        result = fixture_case(case["fixture"])
    elif operation == "search":
        result = search_indicators(case["query"], client=client, limit=30)
    elif operation == "resolve":
        result = resolve_locations(case["inputs"], client=client)
    elif operation == "describe":
        result = describe_indicator(case["code"], client=client)
    elif operation in {"data", "pagination"}:
        use_client = client
        if operation == "pagination":
            use_client = GHOClient(page_size=7)
            use_client._catalogue = catalogue
        result = use_client.get_gho_data(**case["args"])
    else:
        raise AssertionError(f"Unknown operation: {operation}")
    if "error" in expected:
        require(result.get("status") == "error", f"Expected error {expected['error']}, got {result.get('status')}")
        require(result.get("error", {}).get("code") == expected["error"], "Wrong failure classification")
    else:
        require(result.get("status") == expected["status"], f"Expected {expected['status']}, got {result.get('status')}")
    if "attempts" in expected:
        require(result.get("attempts") == expected["attempts"], "Wrong retry count")
    summary = {"status": result.get("status")}
    if "error" in result:
        summary["error"] = result["error"]
    if operation == "search":
        candidates = result.get("candidates", [])
        codes = [row["code"] for row in candidates]
        catalogue_map = {row["IndicatorCode"]: row["IndicatorName"] for row in catalogue}
        require(all(row["code"] in catalogue_map and row["name"] == catalogue_map[row["code"]]
                    for row in candidates), "Candidate code/name is not verified in the live catalogue")
        require(set(expected.get("required_candidates", [])).issubset(codes), f"Missing expected candidates: {codes}")
        if "top_candidate" in expected:
            require(bool(codes) and codes[0] == expected["top_candidate"], f"Wrong leading candidate: {codes[:1]}")
        require(len(codes) >= expected.get("minimum_candidates", 0), "Too few candidates")
        require(len(codes) <= expected.get("maximum_candidates", 100000), "Too many candidates")
        summary["candidates"] = [{"code": row["code"], "name": row["name"]} for row in candidates]
    elif operation == "resolve" and result["status"] == "ok":
        rows = result["locations"]
        require([r["code"] for r in rows] == expected["codes"], "Resolved location differs")
        if "spatial_types" in expected:
            require([r["spatial_type"].upper() for r in rows] == [v.upper() for v in expected["spatial_types"]], "Wrong spatial type")
        summary["locations"] = rows
    elif operation == "describe":
        require(result.get("code") == case["code"], "Wrong metadata indicator")
        require(len(result.get("available_years", [])) >= expected.get("minimum_years", 0), "Missing coverage years")
        dimensions = {r["Dimension"] for r in result.get("available_dimensions", [])}
        require(set(expected.get("declared_dimensions", [])).issubset(dimensions), "Missing declared dimensions")
        summary.update({"available_years": result.get("available_years"),
                        "dimensions": sorted(dimensions), "provenance": result.get("provenance")})
    elif operation in {"data", "pagination"}:
        rows, query = result["records"], case["args"]
        require(len(rows) >= expected.get("minimum_rows", 0), "Too few observations")
        require(len(rows) <= expected.get("maximum_rows", 10000000), "Too many observations")
        require(all(r.get("IndicatorCode") == query["indicator"] for r in rows), "Wrong indicator returned")
        if query.get("locations"):
            require(all(r.get("SpatialDim") in query["locations"] for r in rows), "WHO ignored location filter")
        for key, comparison in (("year_from", lambda y, bound: y >= bound), ("year_to", lambda y, bound: y <= bound)):
            if key in query:
                require(all(comparison(r["TimeDim"], query[key]) for r in rows), "WHO ignored year filter")
        if query.get("spatial_type"):
            require(all(r.get("SpatialDimType") == query["spatial_type"] for r in rows), "WHO ignored spatial type")
        for key, values in query.get("dimensions", {}).items():
            require(all(r.get(key.capitalize()) in values for r in rows), "WHO ignored dimension filter")
        for key in ("dim1", "dim2", "dim3"):
            require(set(expected.get(key + "_contains", [])).issubset({r.get(key.capitalize()) for r in rows}), "Expected stratum is missing")
        if expected.get("null_dimensions"):
            require(all(r.get(key) is None for r in rows for key in ("Dim1", "Dim2", "Dim3")), "Unexpected strata")
        if expected.get("some_dimensions"):
            require(any(r.get(key) is not None for r in rows for key in ("Dim1", "Dim2", "Dim3")), "Expected dimensions lost")
        require(set(expected.get("required_locations", [])).issubset({r["SpatialDim"] for r in rows}), "Expected location has no rows")
        provenance = result.get("provenance", {})
        require(provenance.get("complete") is True and bool(provenance.get("urls")), "Missing complete provenance")
        require(provenance.get("pages", 0) >= expected.get("minimum_pages", 1), "Forced pagination not exercised")
        summary.update({"rows": len(rows), "locations": sorted({r["SpatialDim"] for r in rows}),
                        "years": sorted({r["TimeDim"] for r in rows}), "provenance": provenance})
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true", help="Validate all question-level case fields locally; make no WHO requests")
    parser.add_argument("--offline", action="store_true", help="Run injected transport and cleaner contracts only")
    parser.add_argument("--case", action="append", help="Run named cases only; repeat for multiple IDs")
    parser.add_argument("--merge-from", type=Path, help="Retain earlier case evidence and replace only the selected rechecked cases")
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "eval_results.json")
    args = parser.parse_args()
    previous = json.loads(args.merge_from.read_text(encoding="utf-8")) if args.merge_from else None
    casebook = json.loads((Path(__file__).with_name("cases.json")).read_text(encoding="utf-8"))
    validation = validate_casebook(casebook)
    if args.validate_only:
        report = {"kind": "local_casebook_schema_validation", "model_evaluated": False,
                  "generated_at": datetime.now(timezone.utc).isoformat(), **validation}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0
    cases = casebook["cases"]
    if args.offline:
        cases = [case for case in cases if case["operation"] == "fixture"]
    if args.case:
        cases = [case for case in cases if case["id"] in args.case]
    client = GHOClient()
    catalogue = []
    if any(c["operation"] != "fixture" for c in cases):
        catalogue = client.catalogue()
    results = []
    for case in cases:
        started = time.monotonic()
        item = {"id": case["id"], "operation": case["operation"], "contract": "failed",
                "review_status": "manual_review_pending" if case.get("review") else "not_applicable",
                "review_criteria": case.get("review", [])}
        try:
            try:
                item["observed"] = check_case(case, client, catalogue)
                item["contract"] = "passed"
            except GHOError as exc:
                item["observed"] = exc.as_dict()
                if case["expect"].get("error") == exc.code:
                    item["contract"] = "passed"
                else:
                    item["failure"] = str(exc)
        except Exception as exc:
            item["failure"] = f"{type(exc).__name__}: {exc}"
        item["elapsed_seconds"] = round(time.monotonic() - started, 3)
        item["executed_at"] = datetime.now(timezone.utc).isoformat()
        results.append(item)
        print(f"{case['id']}: {item['contract']}" + (f" ({item['failure']})" if item.get("failure") else ""), flush=True)
    rechecked = [item["id"] for item in results]
    if previous:
        updates = {item["id"]: item for item in results}
        merged = []
        for earlier in previous["cases"]:
            if earlier["id"] in updates:
                replacement = updates.pop(earlier["id"])
                replacement["previous_evidence"] = earlier
                merged.append(replacement)
            else:
                earlier.setdefault("executed_at", previous["generated_at"])
                merged.append(earlier)
        results = merged + list(updates.values())
    report = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
              "kind": "executable_api_contracts", "model_evaluated": False,
              "casebook_validation": validation,
              "rechecked_cases": rechecked if previous else [],
              "earlier_report_generated_at": previous["generated_at"] if previous else None,
              "scope": "offline injected fixtures" if args.offline else "live WHO API plus injected failure fixtures",
              "passed": sum(r["contract"] == "passed" for r in results),
              "failed": sum(r["contract"] == "failed" for r in results),
              "manual_review_pending": sum(r["review_status"] == "manual_review_pending" for r in results),
              "cases": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = ["# Executable evaluation results", "", f"Generated: {report['generated_at']}", "",
                f"API/data contracts: {report['passed']} passed; {report['failed']} failed.",
                f"Natural-language response reviews pending: {report['manual_review_pending']}.", "",
                "No model was called by this runner. Contract passes do not establish that an assistant followed the skill's instructions.", "",
                "| Case | Contract | Response review |", "| --- | --- | --- |"]
    markdown += [f"| {r['id']} | {r['contract']} | {r['review_status']} |" for r in results]
    args.output.with_suffix(".md").write_text("\n".join(markdown) + "\n", encoding="utf-8")
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
