"""Check SDG catalogue/data contracts; this runner does not evaluate a language model."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from sdg_client import SDGClient, SDGError
from indicator_search import search_indicators, describe_indicator
from locations import resolve_locations
from clean import clean_records, observation_context, CORE_FIELDS
from qa import qa_records


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def validate_casebook(book):
    cases, ids = book.get("cases", []), set()
    mandatory = {"id", "user_question", "operation", "expected_series", "expected_locations",
                 "expected_year_logic", "should_clarify", "important_notes", "synthetic_input"}
    operations = {"data", "search", "describe", "resolve", "negative", "review"}
    for case in cases:
        require(isinstance(case, dict) and mandatory <= case.keys(), "Missing required case fields")
        name = case["id"]
        require(isinstance(name, str) and name and name not in ids, "Case IDs must be unique nonempty strings")
        ids.add(name)
        require(case["operation"] in operations, name + ": invalid operation")
        require(isinstance(case["user_question"], str) and len(case["user_question"]) >= 10, name + ": invalid user question")
        require(isinstance(case["should_clarify"], bool), name + ": clarification rule must be boolean")
        require(isinstance(case["synthetic_input"], bool), name + ": synthetic_input must be boolean")
        for field in ("expected_series", "expected_locations"):
            require(isinstance(case[field], list) and all(isinstance(v, str) and v for v in case[field]), name + ": invalid " + field)
        require("expected_indicator_code" in case or "expected_candidates" in case, name + ": indicator expectation required")
        require(isinstance(case["expected_year_logic"], str) and len(case["expected_year_logic"]) >= 20, name + ": year rule must be substantive")
        require(isinstance(case["important_notes"], list) and case["important_notes"] and
                all(isinstance(v, str) and len(v) >= 20 for v in case["important_notes"]), name + ": substantive notes required")
        if case["operation"] == "data":
            require(case["expected_series"] and case["expected_locations"] and case.get("expected_indicator_code"), name + ": retrieval must identify series, area and indicator")
    health_questions = sum(not c["synthetic_input"] and c["operation"] in {"data", "search", "describe", "review"} for c in cases)
    require(health_questions >= 25, "At least 25 real SDG health-data questions required")
    return {"total_cases": len(cases), "real_health_data_questions": health_questions,
            "synthetic_cases": sum(c["synthetic_input"] for c in cases), "required_fields_valid": True}


def catalogue_contract(case, client):
    indicators = {r["code"]: r for r in client.indicators()}
    series = {r["code"]: r for r in client.series()}
    areas = {str(int(r["geoAreaCode"])): r for r in client.areas()}
    expected_indicators = ([case["expected_indicator_code"]] if case.get("expected_indicator_code") else case.get("expected_candidates", []))
    for code in expected_indicators:
        require(code in indicators, f"{code} missing from current indicator catalogue")
    for code in case["expected_series"]:
        require(code in series, f"{code} missing from current series catalogue; investigate a release change")
        require(bool(set(series[code].get("indicator", [])) & set(expected_indicators)), f"{code} is not linked to expected indicator")
    for code in case["expected_locations"]:
        require(code in areas, f"{code} missing from current area catalogue")
    return {"indicator_codes": expected_indicators, "series_codes": case["expected_series"],
            "area_codes": case["expected_locations"],
            "releases": sorted({series[c].get("release", "not provided") for c in case["expected_series"]})}


def execute_case(case, client):
    operation = case["operation"]
    if operation == "search":
        result = search_indicators(case["query"], client=client, limit=50)
        actual = {r["series_code"] for r in result["matches"] if r["series_code"]}
        if case.get("selection_allowed") is False:
            require(result["status"] in {"ok", "no_matches"}, "Unexpected search status")
            require(any("not a substitute" in note for note in result["notes"]), "Missing warning about changed threshold and denominator")
        else:
            require(result["status"] == "ok", "Search returned no candidates")
            require(set(case["expected_series"]) <= actual, "Expected series candidates missing from search: " + str(sorted(actual)))
        catalogue = {r["code"]: r for r in client.series()}
        require(all(r["series_code"] in catalogue and r["name"] == catalogue[r["series_code"]]["description"]
                    for r in result["matches"] if r["series_code"]), "Search invented a series code or official name")
        return {"status": result["status"], "matches": result["matches"], "notes": result["notes"],
                "selection_allowed": case.get("selection_allowed", True)}
    if operation == "resolve":
        result = resolve_locations(case["inputs"], client=client)
        require(result["status"] == "ok", "Location resolver requires unexpected clarification")
        require(set(r["code"] for r in result["locations"]) == set(case["expected_locations"]), "Wrong resolved areas")
        return result
    if operation == "describe":
        result = describe_indicator(case["expected_indicator_code"], client=client)
        require(result["indicator"]["code"] == case["expected_indicator_code"], "Wrong described indicator")
        require(set(case["expected_series"]) <= {r["code"] for r in result["series"]}, "Missing described series")
        require(not result["metadata_errors"], "One or more metadata requests failed")
        require(all(r["definition"] is None for r in result["series"]), "Definition must not be invented from a label")
        return {"status": result["status"], "indicator": result["indicator"]["code"],
                "series": result["series"], "metadata_errors": result["metadata_errors"]}
    if operation == "review":
        return {"status": "manual_review_required", "retrieval_attempted": False,
                "reason": "A human must assess the assistant's clarification and membership explanation."}
    if operation == "negative":
        if case["id"] == "sdg_unknown_location":
            result = resolve_locations(case["locations"], client=client)
            require(result["status"] == "needs_clarification" and not result["locations"], "Unknown location must not trigger an all-area query")
            return result
        try:
            client.get_sdg_data(case.get("indicator", case.get("expected_indicator_code")),
                                locations=case["expected_locations"] or None, series=case.get("series"))
        except SDGError as error:
            require(error.code == case["expected_error"], "Wrong failure class: " + error.code)
            return error.as_dict()
        raise AssertionError("Invalid indicator or series was accepted")
    if operation == "data":
        start = len(client.trace)
        result = client.get_sdg_data(case["expected_indicator_code"], locations=case["expected_locations"],
                                     series=case["expected_series"], year_from=case.get("year_from"),
                                     year_to=case.get("year_to"), dimensions=case.get("requested_dimensions"))
        rows = result["records"]
        if case.get("expected_status"):
            require(result["status"] == case["expected_status"], "Retrieval status differs from the release-specific expectation")
        if "expected_row_count" in case:
            require(len(rows) == case["expected_row_count"], "Row count differs from the release-specific coverage expectation")
        if case.get("allow_empty"):
            require(result["status"] in {"ok", "filters_no_data", "indicator_no_data"}, "Unexpected retrieval status")
        else:
            require(result["status"] == "ok" and rows, "Expected observations were not retrieved")
        require(all(r["series"] in case["expected_series"] and str(r["geoAreaCode"]) in case["expected_locations"] for r in rows), "Wrong series or area in result")
        for row in rows:
            year = int(row["timePeriodStart"])
            require(case.get("year_from", 0) <= year <= case.get("year_to", 9999), "Out-of-scope year in result")
            for key, codes in case.get("requested_dimensions", {}).items():
                require(row["dimensions"].get(key) in codes, "Dimension filter was ignored")
        cleaned = clean_records(rows)
        contexts = observation_context(rows)
        require(len(rows) == len(cleaned) == len(contexts), "Cleaning lost rows or observation context")
        require(all(tuple(row) == CORE_FIELDS for row in cleaned), "DSIR core schema differs")
        qa = qa_records(rows, cleaned)
        require(qa["status"] != "fail", "QA found an error: " + str(qa["issues"]))
        years = sorted({r["year"] for r in cleaned if r["year"] is not None})
        output = {"status": result["status"], "rows": len(rows), "retrieved_rows": result["retrieved_row_count"],
                  "pages": result["pages"], "years": years, "qa": qa,
                  "requests": client.trace[start:],
                  "baseline_probe": result["baseline_probe"],
                  "returned_locations": sorted({r["location"] for r in cleaned})}
        if case.get("expectation_correction"):
            output["expectation_correction"] = case["expectation_correction"]
        if case.get("answer_selection") == "latest_available":
            output["latest_available_year"] = max(years) if years else None
        return output
    raise AssertionError("Unsupported case operation")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true", help="Validate the casebook locally without an API request")
    parser.add_argument("--catalogue-only", action="store_true", help="Check verified identities, search, location and negative contracts; skip data/metadata requests")
    parser.add_argument("--catalogue-dir", type=Path, help="Use an explicitly labelled previously downloaded catalogue for identity/search checks only")
    parser.add_argument("--case", action="append", help="Run selected case IDs; repeat for several cases")
    parser.add_argument("--merge-from", type=Path, help="Keep previous case evidence and replace explicitly rechecked cases")
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "eval_results.json")
    args = parser.parse_args()
    book = json.loads(Path(__file__).with_name("cases.json").read_text(encoding="utf-8"))
    validation = validate_casebook(book)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "model_evaluated": False,
              "validation": validation, "mode": "schema_only" if args.validate_only else "catalogue_contracts" if args.catalogue_only else "live_API_contracts",
              "catalogue_evidence": "previously downloaded snapshot" if args.catalogue_dir else "live UNSD API",
              "scope_note": "Cases use explicit expected arguments. Natural-language interpretation, clarification and response quality require a separate assistant review."}
    if args.validate_only:
        report["catalogue_evidence"] = "not checked"
        report.update({"passed": 0, "failed": 0, "cases": []})
    else:
        require(not args.catalogue_dir or args.catalogue_only, "Catalogue snapshots may only be used with --catalogue-only")
        client = SDGClient(page_size=args.page_size)
        if args.catalogue_dir:
            for kind in ("Indicator", "Series", "GeoArea"):
                client._cache[kind] = json.loads((args.catalogue_dir / (kind + "_List.json")).read_text(encoding="utf-8-sig"))
        cases = book["cases"]
        if args.case:
            require(set(args.case) <= {c["id"] for c in cases}, "Unknown case ID requested")
            cases = [c for c in cases if c["id"] in args.case]
        results = []
        for case in cases:
            started = time.monotonic()
            item = {"id": case["id"], "operation": case["operation"], "contract": "failed",
                    "natural_language_review": "pending", "should_clarify": case["should_clarify"],
                    "review_criteria": [case["expected_year_logic"], *case["important_notes"]]}
            try:
                item["catalogue"] = catalogue_contract(case, client)
                if args.catalogue_only and case["operation"] in {"data", "describe", "review"}:
                    item["execution"] = "not_run_in_catalogue_mode"
                else:
                    item["observed"] = execute_case(case, client)
                    item["execution"] = "manual_review_only" if case["operation"] == "review" else "executed"
                item["contract"] = "passed"
            except Exception as error:
                item["failure"] = error.as_dict() if isinstance(error, SDGError) else {"type": type(error).__name__, "message": str(error)}
            item["elapsed_seconds"] = round(time.monotonic() - started, 3)
            item["executed_at"] = datetime.now(timezone.utc).isoformat()
            results.append(item)
            print(case["id"] + ": " + item["contract"] + (" " + json.dumps(item["failure"]) if "failure" in item else ""), flush=True)
        if args.merge_from:
            previous = json.loads(args.merge_from.read_text(encoding="utf-8"))
            require(previous["mode"] == report["mode"], "Cannot merge evidence from different execution modes")
            updated = {r["id"]: r for r in results}
            merged = []
            for earlier in previous["cases"]:
                replacement = updated.pop(earlier["id"], None)
                if replacement:
                    replacement["previous_evidence"] = earlier
                    merged.append(replacement)
                else:
                    merged.append(earlier)
            results = merged + list(updated.values())
        report.update({"passed": sum(r["contract"] == "passed" for r in results),
                       "failed": sum(r["contract"] == "failed" for r in results), "cases": results,
                       "catalogue_requests": [r for r in client.trace if r["url"].split("?", 1)[0].endswith("/List")]})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    text = ["# SDG executable evaluation results", "", "Generated: " + report["generated_at"], "",
            "Mode: " + report["mode"], "", f"Contracts: {report['passed']} passed; {report['failed']} failed.", "",
            report["scope_note"], "", "No language model was called. Natural-language response reviews remain pending.", "",
            "| Case | Contract | Execution |", "| --- | --- | --- |"]
    text += [f"| {r['id']} | {r['contract']} | {r.get('execution', 'failed')} |" for r in report["cases"]]
    args.output.with_suffix(".md").write_text("\n".join(text) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "cases"}, ensure_ascii=False, indent=2))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
