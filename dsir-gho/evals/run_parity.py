"""Compare live Python retrieval/cleaning with unmodified original DSIR R code."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from gho_client import GHOClient, GHOError
from clean import clean_records, CORE_FIELDS

NUMERIC = {"value_num", "low", "high"}
STRING_FIELDS = set(CORE_FIELDS) - NUMERIC - {"year"}
KEY_FIELDS = ("source", "id", "location", "iso3", "location_name", "year", "series", "dim1", "dim2", "dim3", "value")
R_TYPES = {field: "character" for field in STRING_FIELDS} | {field: "double" for field in NUMERIC} | {"year": "integer"}


def save_json(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def null_counts(rows):
    return {field: sum(row.get(field) is None for row in rows) for field in CORE_FIELDS}


def row_key(row):
    return tuple(row.get(field) for field in KEY_FIELDS)


def dimension_counts(rows):
    counts = Counter((row.get("dim1"), row.get("dim2"), row.get("dim3")) for row in rows)
    return [{"dim1": key[0], "dim2": key[1], "dim3": key[2], "rows": value}
            for key, value in sorted(counts.items(), key=lambda item: repr(item[0]))]


def compare_clean(python_rows, r_result):
    if r_result is None or r_result.get("status") != "ok":
        return {"passed": False, "reason": "R reference did not produce an OK result", "r_result": r_result}
    r_rows = r_result.get("clean", [])
    if not isinstance(r_rows, list):
        return {"passed": False, "reason": "R clean output is not a row array"}
    schema_ok = r_result.get("clean_columns") == list(CORE_FIELDS) and all(list(row) == list(CORE_FIELDS) for row in python_rows)
    r_types_ok = r_result.get("clean_types") == R_TYPES
    python_types_ok = all(
        (value is None or (isinstance(value, str) if field in STRING_FIELDS else
         isinstance(value, int) and not isinstance(value, bool) if field == "year" else
         isinstance(value, (float, int)) and not isinstance(value, bool)))
        for row in python_rows for field, value in row.items())
    left, right = defaultdict(list), defaultdict(list)
    for row in python_rows:
        left[row_key(row)].append(row)
    for row in r_rows:
        right[row_key(row)].append(row)
    key_counts_match = {k: len(v) for k, v in left.items()} == {k: len(v) for k, v in right.items()}
    mismatch_count, examples = 0, []
    max_absolute_error = {field: 0.0 for field in NUMERIC}
    for key in sorted(left.keys() | right.keys(), key=repr):
        python_group = sorted(left[key], key=lambda row: repr(tuple(row.get(f) for f in CORE_FIELDS)))
        r_group = sorted(right[key], key=lambda row: repr(tuple(row.get(f) for f in CORE_FIELDS)))
        if len(python_group) != len(r_group):
            mismatch_count += abs(len(python_group) - len(r_group))
            if len(examples) < 12:
                examples.append({"key": list(key), "python_rows": len(python_group), "r_rows": len(r_group)})
        for python_row, r_row in zip(python_group, r_group):
            for field in CORE_FIELDS:
                a, b = python_row.get(field), r_row.get(field)
                same = a == b
                if field in NUMERIC and a is not None and b is not None:
                    error = abs(a - b)
                    max_absolute_error[field] = max(error, max_absolute_error[field])
                    same = math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-10)
                if not same:
                    mismatch_count += 1
                    if len(examples) < 12:
                        examples.append({"key": list(key), "field": field, "python": a, "r": b})
    missing_python, missing_r = null_counts(python_rows), null_counts(r_rows)
    dimensions_python, dimensions_r = dimension_counts(python_rows), dimension_counts(r_rows)
    passed = (schema_ok and r_types_ok and python_types_ok and key_counts_match and
              len(python_rows) == len(r_rows) and mismatch_count == 0 and
              missing_python == missing_r and dimensions_python == dimensions_r)
    return {"passed": passed, "python_rows": len(python_rows), "r_rows": len(r_rows),
            "schema_15_fields_and_order": schema_ok, "r_types_match": r_types_ok,
            "python_types_match": python_types_ok, "row_keys_and_multiplicity_match": key_counts_match,
            "compared_fields": list(CORE_FIELDS), "numeric_tolerance": {"absolute": 1e-10, "relative": 1e-12},
            "numeric_max_absolute_error": max_absolute_error, "mismatch_count": mismatch_count,
            "missing_python": missing_python, "missing_r": missing_r,
            "dimensions_python": dimensions_python, "dimensions_r": dimensions_r,
            "examples": examples}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rscript", type=Path, default=Path("Rscript"))
    parser.add_argument("--source-dir", type=Path, default=ROOT.parent.parent / "DSIR")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports" / "parity")
    parser.add_argument("--reuse-evidence", action="store_true", help="Recompare previously saved test evidence; performs no new retrieval")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    casebook = json.loads(Path(__file__).with_name("cases.json").read_text(encoding="utf-8"))
    cases = [case for case in casebook["cases"] if case.get("parity")]
    source_file = args.source_dir / "R" / "gho.R"
    source_sha = hashlib.sha256(source_file.read_bytes()).hexdigest()
    revision = subprocess.run(["git", "-C", str(args.source_dir), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    evidence_path = args.output_dir / "python_reference.json"
    reference_path = args.output_dir / "r_reference.json"
    process_path = args.output_dir / "r_process_status.json"
    common_path = args.output_dir / "common_raw_input.json"
    if args.reuse_evidence:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    else:
        client = GHOClient()
        catalogue = client.catalogue()
        evidence = {"retrieved_at": datetime.now(timezone.utc).isoformat(), "catalogue": catalogue,
                    "source_revision": revision, "source_sha256": source_sha, "queries": []}
        common = {"catalogue": catalogue, "queries": []}
        for case in cases:
            print(f"Python live reference: {case['id']}", flush=True)
            try:
                result = client.get_gho_data(**case["args"])
                raw = result["records"]
                entry = {"id": case["id"], "args": case["args"], "status": result["status"],
                         "raw": raw, "clean": clean_records(raw, catalogue), "provenance": result["provenance"]}
                common["queries"].append({"id": case["id"], "records": raw})
            except GHOError as exc:
                entry = {"id": case["id"], "args": case["args"], **exc.as_dict()}
            evidence["queries"].append(entry)
            save_json(evidence_path, evidence)
        scalar_rows = [
            {"IndicatorCode": "WHS3_62", "SpatialDim": "WPR_WO_IDN", "TimeDim": "2020.9", "Value": "<0.1", "NumericValue": None, "Dim1": "SEX_BTSX"},
            {"IndicatorCode": "WHS3_62", "SpatialDim": "PHL", "TimeDim": None, "Value": "NA", "NumericValue": "not available", "Low": None, "High": None},
            {"IndicatorCode": "UHC_INDEX_REPORTED", "SpatialDim": "WPR", "TimeDim": 2020, "Value": "", "NumericValue": None}
        ]
        scalar_rows.append(dict(scalar_rows[0]))
        common["queries"].append({"id": "common_scalar_missingness_duplicates", "records": scalar_rows,
                                  "synthetic": True, "purpose": "Transformation-only edge cases; never reported as WHO values"})
        save_json(common_path, common)
        spec = {"source_dir": str(args.source_dir.resolve()), "source_revision": revision,
                "common_raw_path": str(common_path.resolve()),
                "queries": [{"id": c["id"], "args": c["args"]} for c in cases]}
        spec_path = args.output_dir / "parity_spec.json"
        save_json(spec_path, spec)
        command = [str(args.rscript), "--vanilla", str(Path(__file__).with_name("parity.R")),
                   str(spec_path.resolve()), str(reference_path.resolve()), str(process_path.resolve())]
        completed = subprocess.run(command, timeout=1900, check=False)
        print(f"R parent exit: {completed.returncode}", flush=True)
        if completed.returncode != 0:
            save_json(process_path, {"child_ok": False, "parent_exit_code": completed.returncode})
    process = json.loads(process_path.read_text(encoding="utf-8")) if process_path.exists() else {"child_ok": False, "message": "Missing R process result"}
    reference = json.loads(reference_path.read_text(encoding="utf-8")) if reference_path.exists() else {"queries": [], "common_raw": []}
    r_queries = {query["id"]: query for query in reference.get("queries", [])}
    r_common = {query["id"]: query for query in reference.get("common_raw", [])}
    comparisons = []
    for query in evidence["queries"]:
        reference_query = r_queries.get(query["id"])
        if query.get("status") != "ok" or not query.get("raw"):
            comparison = {"passed": False, "reason": "Python live retrieval failed or returned no rows", "status": query.get("status")}
        else:
            comparison = compare_clean(query["clean"], reference_query)
            comparison["raw_row_counts_match"] = len(query["raw"]) == (reference_query or {}).get("raw_rows")
            comparison["passed"] &= comparison["raw_row_counts_match"]
        comparison["id"] = query["id"]
        comparison["query"] = query["args"]
        comparisons.append(comparison)
        print(f"Live parity {query['id']}: {'passed' if comparison['passed'] else 'FAILED'}", flush=True)
    common_input = json.loads(common_path.read_text(encoding="utf-8"))
    common_comparisons = []
    for query in common_input["queries"]:
        cleaned = clean_records(query["records"], common_input["catalogue"], countries=reference.get("who_countries"))
        comparison = compare_clean(cleaned, r_common.get(query["id"]))
        comparison["id"] = query["id"]
        comparison["synthetic"] = bool(query.get("synthetic"))
        common_comparisons.append(comparison)
    source_match = all(reference.get("source_matches_installed", {}).values()) and bool(reference.get("source_matches_installed"))
    passed = (process.get("child_ok") is True and reference.get("status") == "complete" and source_match
              and all(row["passed"] for row in comparisons + common_comparisons)
              and len(comparisons) >= 10)
    report = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
              "mode": "saved_evidence_recomparison" if args.reuse_evidence else "live_paired_retrieval_and_common_raw_cleaning",
              "passed": passed, "r_process": process, "r_version": reference.get("r_version"),
              "dsir_version": reference.get("dsir_version"), "source_revision": revision, "source_sha256": source_sha,
              "source_matches_installed": reference.get("source_matches_installed"),
              "live_queries": comparisons, "common_raw_queries": common_comparisons,
              "live_passed": sum(row["passed"] for row in comparisons),
              "live_failed": sum(not row["passed"] for row in comparisons),
              "common_raw_passed": sum(row["passed"] for row in common_comparisons),
              "common_raw_failed": sum(not row["passed"] for row in common_comparisons),
              "interpretation": "Live parity failures with common-raw passes can indicate upstream revisions, ordering or retrieval differences; inspect saved evidence before attributing a cleaner defect."}
    save_json(args.output_dir / "parity_results.json", report)
    lines = ["# Original DSIR versus Python parity", "", f"Generated: {report['generated_at']}", "",
             f"Overall: {'PASS' if passed else 'FAIL'}.",
             f"Live queries: {report['live_passed']} passed, {report['live_failed']} failed.",
             f"Common-raw cleaning checks: {report['common_raw_passed']} passed, {report['common_raw_failed']} failed.", "",
             f"Reference: DSIR {report['dsir_version']}; {report['r_version']}; original commit `{revision}`.", "",
             "Each comparison checks the 15 ordered fields, R/Python scalar types, row counts and multiplicity, dimensions, per-column missingness, raw display values, indicator/location labels, and numeric values with absolute tolerance 1e-10 and relative tolerance 1e-12.", "",
             "R executes the original source without editing the original repository or installed package. The R child result is checked independently of the successful parent exit. Test evidence is not runtime data.", "",
             "| Query | Live parity | Common-raw parity | Rows (Python/R) |", "| --- | --- | --- | --- |"]
    common_map = {row["id"]: row for row in common_comparisons}
    for row in comparisons:
        common_result = common_map.get(row["id"], {})
        lines.append(f"| {row['id']} | {'PASS' if row['passed'] else 'FAIL'} | {'PASS' if common_result.get('passed') else 'FAIL'} | {row.get('python_rows', '?')}/{row.get('r_rows', '?')} |")
    (args.output_dir / "parity_results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
