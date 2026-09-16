"""Compare the skill with original DSIR source; R is development-only."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("source", "id", "indicator", "location", "iso3", "location_name",
          "year", "value", "value_num", "low", "high", "series", "dim1", "dim2", "dim3")
NUMERIC = {"value_num", "low", "high"}
STRINGS = set(FIELDS) - NUMERIC - {"year"}
R_TYPES = {field: "character" for field in STRINGS} | {field: "double" for field in NUMERIC} | {"year": "integer"}


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def null_counts(rows):
    return {field: sum(row.get(field) is None for row in rows) for field in FIELDS}


def groups(rows, fields):
    return dict(sorted(Counter(canonical([row.get(field) for field in fields]) for row in rows).items()))


def compare_clean(python_rows, r_result):
    if not r_result or r_result.get("status") != "ok":
        return {"passed": False, "reason": "R reference did not return an OK result", "r_result": r_result}
    r_rows = r_result.get("clean")
    if not isinstance(r_rows, list):
        return {"passed": False, "reason": "R output is not a JSON row array"}
    schema_ok = r_result.get("clean_columns") == list(FIELDS) and all(list(row) == list(FIELDS) for row in python_rows)
    r_types_ok = r_result.get("clean_types") == R_TYPES
    python_types_ok = all(
        value is None or (isinstance(value, str) if field in STRINGS else
                          isinstance(value, int) and not isinstance(value, bool) if field == "year" else
                          isinstance(value, (float, int)) and not isinstance(value, bool))
        for row in python_rows for field, value in row.items())
    # Compare in sequence as well as multiplicity: DSIR's location/year order is
    # part of the contract; stable ordering preserves meaningful duplicates.
    mismatch_count = abs(len(python_rows) - len(r_rows))
    examples, maximum_errors = [], {field: 0.0 for field in NUMERIC}
    for row_index, (left, right) in enumerate(zip(python_rows, r_rows)):
        for field in FIELDS:
            a, b = left.get(field), right.get(field)
            same = a == b
            if field in NUMERIC and a is not None and b is not None:
                maximum_errors[field] = max(maximum_errors[field], abs(a - b))
                same = math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-10)
            if not same:
                mismatch_count += 1
                if len(examples) < 20:
                    examples.append({"row": row_index, "field": field, "python": a, "r": b})
    keys = ("id", "location", "iso3", "year", "series", "dim1", "dim2", "dim3")
    key_counts_match = groups(python_rows, keys) == groups(r_rows, keys)
    missing_python, missing_r = null_counts(python_rows), null_counts(r_rows)
    passed = (schema_ok and r_types_ok and python_types_ok and key_counts_match
              and mismatch_count == 0 and missing_python == missing_r)
    return {"passed": passed, "python_rows": len(python_rows), "r_rows": len(r_rows),
            "schema_15_fields_and_order": schema_ok, "r_types_match": r_types_ok,
            "python_types_match": python_types_ok, "ordered_row_comparison": True,
            "indicator_location_year_series_dimension_multiplicity_match": key_counts_match,
            "missing_python": missing_python, "missing_r": missing_r,
            "numeric_tolerance": {"absolute": 1e-10, "relative": 1e-12},
            "numeric_max_absolute_error": maximum_errors,
            "mismatch_count": mismatch_count, "examples": examples}


def normalize_raw(value):
    # jsonlite adds null columns when nested structures differ. Dropping only
    # null object entries normalizes that serialization; array order remains.
    if isinstance(value, dict):
        return {key: normalize_raw(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [normalize_raw(item) for item in value]
    return value


def raw_dimension_counts(rows):
    return Counter(canonical(normalize_raw({key: row.get(key) for key in
                   ("geoAreaCode", "timePeriodStart", "series", "dimensions", "attributes")})) for row in rows)


def synthetic_cases():
    base = {"indicator": ["3.4.1"], "series": "SYNTHETIC_ONLY", "seriesDescription": "Synthetic test row",
            "geoAreaCode": "608", "geoAreaName": "Philippine Islands", "timePeriodStart": 2020, "value": "1"}
    cases = [
        ("synthetic_empty", []),
        ("synthetic_missing_columns", [{"geoAreaCode": "608", "timePeriodStart": 2020}]),
        ("synthetic_censored_and_missing", [dict(base, value="<0.1", lowerBound=None, upperBound="1.2"),
            dict(base, value=None, timePeriodStart=None), dict(base, value="", timePeriodStart="not a year")]),
        ("synthetic_members_and_aggregates", [dict(base, geoAreaCode="076"), dict(base, geoAreaCode="76"),
            dict(base, geoAreaCode="1", geoAreaName="World"),
            dict(base, geoAreaCode="99047", geoAreaName="WHO Western Pacific"),
            dict(base, geoAreaCode="772", geoAreaName="Tokelau")]),
        ("synthetic_indicator_links", [dict(base, indicator=["3.4.1", "3.4.2"]), dict(base, indicator=[])]),
        ("synthetic_atomic_indicator", [dict(base, indicator="3.4.1")]),
        ("synthetic_duplicate_dimensions", [dict(base, dimensions={"Sex": "FEMALE", "Age": "15Y"}),
            dict(base, dimensions={"Sex": "BOTHSEX"}), dict(base, dimensions={"Sex": "BOTHSEX"})]),
        ("synthetic_numeric_formats", [dict(base, value="1e-3", lowerBound="0", upperBound="2.5"),
            dict(base, value="1,000"), dict(base, value=".."), dict(base, value="-1.25", timePeriodStart="2020.9")])
    ]
    countries = json.loads((ROOT / "references/metadata/who_countries.json").read_text(encoding="utf-8"))
    cases.append(("synthetic_all_member_locations", [dict(base, geoAreaCode=country["m49_code"],
                   geoAreaName="Synthetic API label") for country in countries]))
    return [{"id": identifier, "records": rows, "synthetic": True,
             "purpose": "Transformation-only fixture, never a UN observation"} for identifier, rows in cases]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "reports/parity/common_raw_input.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/parity")
    parser.add_argument("--source-dir", type=Path, default=ROOT.parent.parent / "DSIR")
    parser.add_argument("--rscript", type=Path, default=Path("Rscript"))
    parser.add_argument("--live-r", action="store_true", help="Also retrieve each query independently through original DSIR; requires network")
    parser.add_argument("--reuse-evidence", action="store_true", help="Compare saved R output without executing R or accessing the network")
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / "scripts"))
    from clean import clean_records
    from locations import load_countries

    args.output_dir.mkdir(parents=True, exist_ok=True)
    source_names = ("clean_schema.R", "m49_to_iso3.R", "iso3_to_m49.R", "http.R", "sdg.R", "sdg_coverage.R")
    hashes = {name: hashlib.sha256((args.source_dir / "R" / name).read_bytes()).hexdigest() for name in source_names}
    source_md5 = {name: hashlib.md5((args.source_dir / "R" / name).read_bytes()).hexdigest() for name in source_names}
    hashes["data/who_countries.rda"] = hashlib.sha256((args.source_dir / "data/who_countries.rda").read_bytes()).hexdigest()
    revision = subprocess.run(["git", "-C", str(args.source_dir), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    common_path = args.output_dir / "parity_common_input.json"
    r_path, process_path = args.output_dir / "r_reference.json", args.output_dir / "r_process_status.json"
    if args.reuse_evidence:
        common = json.loads(common_path.read_text(encoding="utf-8"))
        run_id = json.loads((args.output_dir / "parity_spec.json").read_text(encoding="utf-8")).get("run_id")
    else:
        run_id = str(uuid.uuid4())
        common = json.loads(args.input.read_text(encoding="utf-8"))
        existing_ids = {query["id"] for query in common["queries"]}
        common["queries"].extend(query for query in synthetic_cases() if query["id"] not in existing_ids)
        save_json(common_path, common)
        spec_path = args.output_dir / "parity_spec.json"
        save_json(spec_path, {"source_dir": str(args.source_dir.resolve()), "source_revision": revision,
                              "common_raw_path": str(common_path.resolve()), "live_r": args.live_r, "run_id": run_id})
        # Reset status before launch so a failed start cannot reuse an earlier
        # successful child result or claim its reference rows belong to this run.
        save_json(process_path, {"child_ok": False, "message": "R reference not yet completed", "run_id": run_id})
        result = subprocess.run([str(args.rscript), "--vanilla", str(Path(__file__).with_name("parity.R")),
                                 str(spec_path.resolve()), str(r_path.resolve()), str(process_path.resolve())],
                                timeout=2500, check=False)
        save_json(args.output_dir / "r_launcher_status.json", {"returncode": result.returncode})
    process = json.loads(process_path.read_text(encoding="utf-8")) if process_path.exists() else {"child_ok": False, "message": "No R process status"}
    reference = json.loads(r_path.read_text(encoding="utf-8")) if r_path.exists() else {}
    common_reference = {query["id"]: query for query in reference.get("common_raw", [])}
    live_reference = {query["id"]: query for query in reference.get("live_queries", [])}
    common_results, live_results, evidence, live_indicators = [], [], [], set()
    for query in common["queries"]:
        cleaned = clean_records(query["records"])
        evidence.append({"id": query["id"], "clean": cleaned})
        comparison = compare_clean(cleaned, common_reference.get(query["id"]))
        comparison.update(id=query["id"], synthetic=bool(query.get("synthetic")))
        common_results.append(comparison)
        if not query.get("synthetic") and query["records"]:
            codes = query.get("indicator", (query.get("args") or {}).get("indicator"))
            if codes is None:
                codes = [code for row in query["records"] for code in (row.get("indicator") or [])]
            live_indicators.update([codes] if isinstance(codes, str) else codes)
        if query["id"] in live_reference:
            item = live_reference[query["id"]]
            live = compare_clean(cleaned, item)
            live.update(id=query["id"], raw_rows_python=len(query["records"]), raw_rows_r=item.get("raw_rows"))
            live["raw_dimensions_and_attributes_match"] = raw_dimension_counts(query["records"]) == raw_dimension_counts(item.get("raw", []))
            live["passed"] = live["passed"] and live["raw_dimensions_and_attributes_match"] and bool(query["records"])
            live_results.append(live)
        print(f"Common-input parity {query['id']}: {'PASS' if comparison['passed'] else 'FAIL'}", flush=True)
    save_json(args.output_dir / "python_reference.json", {"queries": evidence})
    live_required = args.live_r or bool(live_reference)
    expected_live = sum(not query.get("synthetic") for query in common["queries"])
    country_fields = ("iso3", "m49_code", "name_short", "who_region")
    countries_match = groups(load_countries(), country_fields) == groups(reference.get("who_countries", []), country_fields)
    reference_current = (bool(run_id) and reference.get("run_id") == run_id
                         and reference.get("source_revision") == revision
                         and reference.get("source_md5") == source_md5)
    passed = (process.get("child_ok") is True and reference.get("status") == "complete"
              and reference_current and countries_match and len(live_indicators) >= 10 and all(result["passed"] for result in common_results)
              and (not live_required or (len(live_results) == expected_live and all(item["passed"] for item in live_results))))
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "passed": passed,
              "mode": "independent_live_R_and_common_input" if live_required else "common_input_cleaning_only",
              "r_version": reference.get("r_version"), "dsir_source_version": reference.get("dsir_source_version"),
              "dsir_installed_version": reference.get("dsir_installed_version"), "source_revision": revision,
              "source_sha256": hashes, "source_matches_installed": reference.get("source_matches_installed"),
              "r_process": process, "distinct_live_snapshot_indicators": sorted(live_indicators),
              "reference_run_and_source_match": reference_current,
              "bundled_country_mapping_matches_source": countries_match,
              "common_input_passed": sum(item["passed"] for item in common_results),
              "common_input_failed": sum(not item["passed"] for item in common_results),
              "live_r_passed": sum(item["passed"] for item in live_results),
              "live_r_failed": sum(not item["passed"] for item in live_results),
              "common_input": common_results, "live_r": live_results,
              "interpretation": "Identical raw input isolates cleaning behavior. Independent live differences can reflect API revisions, ordering or filters and must be inspected. Synthetic rows are test fixtures, never source observations. DSIR's compact 15 deliberately omits SDG dimensions; independent live checks compare raw dimensions and attributes separately."}
    save_json(args.output_dir / "parity_results.json", report)
    lines = ["# DSIR SDG parity results", "", f"Generated: {report['generated_at']}", "",
             f"Overall: {'PASS' if passed else 'FAIL'}. Mode: `{report['mode']}`.",
             f"Original DSIR {report['dsir_source_version']}, commit `{revision}`; {report['r_version']}.",
             f"Distinct live-snapshot indicators: {len(live_indicators)}.",
             f"Bundled country mapping agrees with original source: {countries_match}.",
             f"Common-input checks: {report['common_input_passed']} passed; {report['common_input_failed']} failed.",
             f"Independent R live retrieval checks: {report['live_r_passed']} passed; {report['live_r_failed']} failed.", "",
             "Checks cover all 15 ordered fields, row sequence and multiplicity, scalar types, indicator, location, year, series, numeric values and bounds, and per-column missingness. Numeric tolerance: absolute 1e-10, relative 1e-12. The exact unmodified R source and its country asset are evaluated in an isolated environment. R is not bundled or needed by users.", "",
             "Common-input checks do not independently prove retrieval parity. Independent live checks, when enabled, also compare raw dimensions and attributes. DSIR's dim1/dim2/dim3 are always missing for SDG; enriched skill output must preserve SDG dimensions separately.", "",
             "| Case | Fixture | Common-input parity | Rows (Python/R) |", "| --- | --- | --- | --- |"]
    for item in common_results:
        lines.append(f"| {item['id']} | {'Synthetic' if item['synthetic'] else 'Live snapshot'} | {'PASS' if item['passed'] else 'FAIL'} | {item.get('python_rows', '?')}/{item.get('r_rows', '?')} |")
    if live_results:
        lines += ["", "| Independent R retrieval | Result | Raw dimensions and attributes |", "| --- | --- | --- |"]
        for item in live_results:
            lines.append(f"| {item['id']} | {'PASS' if item['passed'] else 'FAIL'} | {'PASS' if item['raw_dimensions_and_attributes_match'] else 'FAIL'} |")
    failures = [item for item in common_results + live_results if not item["passed"]]
    if failures:
        lines += ["", "## Differences requiring inspection", "", "See `parity_results.json` for the exact fields, missingness counts and example mismatches. No observation values were changed to make comparisons pass."]
    (args.output_dir / "parity_results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
