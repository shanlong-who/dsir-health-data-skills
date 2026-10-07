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


def compare_context(left, right):
    """Compare retained source context using the same numeric tolerance."""
    if isinstance(left, dict) and isinstance(right, dict):
        return set(left) == set(right) and all(compare_context(left[k], right[k]) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(compare_context(a, b) for a, b in zip(left, right))
    if isinstance(left, (int, float)) and not isinstance(left, bool) and isinstance(right, (int, float)) and not isinstance(right, bool):
        return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-10)
    return type(left) is type(right) and left == right


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rscript", type=Path, default=Path("Rscript"))
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports" / "xmart-parity")
    parser.add_argument("--offline", action="store_true", help="Run synthetic common-input source parity without network calls")
    parser.add_argument("--reuse-evidence", action="store_true", help="Recompare the saved run; performs no new retrieval")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pinned = "885464b1fade2f8b6d02dde93f9080e4b3f4f2a5"
    revision = subprocess.run(["git", "-C", str(args.source_dir), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    if revision != pinned:
        parser.error("Reference checkout must be the exact DSIR 0.11.0 commit " + pinned)
    source_files = ["R/http.R", "R/clean_schema.R", "R/clean_metadata.R", "R/who_backend.R",
                    "R/who_gho.R", "R/who_legacy.R", "R/gho.R", "DESCRIPTION", "data/who_countries.rda"]
    subprocess.run(["git", "-C", str(args.source_dir), "diff", "--exit-code", "HEAD", "--", *source_files], check=True)
    source_hashes = {name: hashlib.sha256((args.source_dir / name).read_bytes()).hexdigest() for name in source_files}
    casebook = json.loads(Path(__file__).with_name("cases.json").read_text(encoding="utf-8"))
    cases = [c for c in casebook["cases"] if c.get("parity")]
    cases += [
        {"id": "xmart_named_sex", "args": {"indicator": "NCDMORT3070", "locations": ["PHL"], "year_from": 2020,
                                         "dimensions": {"DIM_SEX": ["TOTAL"]}}},
        {"id": "xmart_named_age", "args": {"indicator": "NCDMORT3070", "locations": ["PHL"], "year_from": 2020,
                                         "dimensions": {"DIM_AGE": ["YEARS30-69"]}}},
    ]
    evidence_path = args.output_dir / "python_reference.json"
    reference_path = args.output_dir / "r_reference.json"
    process_path = args.output_dir / "r_process_status.json"
    common_path = args.output_dir / "common_raw_input.json"
    if args.reuse_evidence:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        if evidence.get("source_hashes") != source_hashes:
            parser.error("Saved evidence belongs to a different source snapshot")
    else:
        from xmart_parity_inputs import common_inputs
        common = common_inputs()
        evidence = {"retrieved_at": datetime.now(timezone.utc).isoformat(), "source_revision": revision,
                    "source_hashes": source_hashes, "backend": "xmart", "offline": args.offline, "queries": [], "catalogue": []}
        client = GHOClient()
        if not args.offline:
            try:
                evidence["catalogue"] = client.catalogue()
                evidence["catalogue_status"] = "ok"
            except GHOError as exc:
                evidence["catalogue_status"] = "error"
                evidence["catalogue_error"] = exc.as_dict()
            for case in cases:
                print(f"Python live reference: {case['id']}", flush=True)
                if evidence["catalogue_status"] != "ok":
                    entry = {"id": case["id"], "args": case["args"], "status": "blocked",
                             "reason": "Fresh xMart directory retrieval failed"}
                else:
                    try:
                        result = client.get_gho_data(**case["args"])
                        raw = result["records"]
                        entry = {"id": case["id"], "args": case["args"], "status": result["status"], "raw": raw,
                                 "source_raw": result.get("source_records"), "clean": clean_records(raw, evidence["catalogue"]),
                                 "provenance": result["provenance"]}
                        common["queries"].append({"id": case["id"], "synthetic": False, "records": raw, "clean": entry["clean"]})
                    except GHOError as exc:
                        entry = {"id": case["id"], "args": case["args"], **exc.as_dict()}
                evidence["queries"].append(entry)
        evidence["requests"] = client.trace
        save_json(evidence_path, evidence)
        save_json(common_path, common)
        spec = {"source_dir": str(args.source_dir.resolve()), "source_revision": revision,
                "source_files": source_files, "source_hashes": source_hashes,
                "common_raw_path": str(common_path.resolve()), "offline": args.offline,
                "queries": [{"id": c["id"], "args": c["args"]} for c in cases] if not args.offline else []}
        spec_path = args.output_dir / "parity_spec.json"
        save_json(spec_path, spec)
        completed = subprocess.run([str(args.rscript), "--vanilla", str(Path(__file__).with_name("parity.R")),
                                    str(spec_path.resolve()), str(reference_path.resolve()), str(process_path.resolve())],
                                   timeout=1900, check=False)
        if completed.returncode != 0:
            save_json(process_path, {"child_ok": False, "parent_exit_code": completed.returncode})
    process = json.loads(process_path.read_text()) if process_path.exists() else {"child_ok": False}
    reference = json.loads(reference_path.read_text(encoding="utf-8")) if reference_path.exists() else {}
    r_queries = {q["id"]: q for q in reference.get("queries", [])}
    r_common = {q["id"]: q for q in reference.get("common_raw", [])}
    comparisons = []
    for query in evidence["queries"]:
        if query["status"] != "ok" or not query.get("raw"):
            comparison = {"passed": False, "status": query["status"], "reason": "No successful independent live comparison",
                          "r_status": r_queries.get(query["id"], {}).get("status")}
        else:
            comparison = compare_clean(query["clean"], r_queries.get(query["id"]))
            comparison["raw_row_counts_match"] = len(query["raw"]) == r_queries.get(query["id"], {}).get("raw_rows")
            comparison["passed"] &= comparison["raw_row_counts_match"]
        comparisons.append(comparison | {"id": query["id"], "query": query["args"]})
    common = json.loads(common_path.read_text(encoding="utf-8"))
    common_comparisons = []
    for query in common["queries"]:
        comparison = compare_clean(clean_records(query["records"], common["catalogue"], countries=reference.get("who_countries")),
                                   r_common.get(query["id"]))
        if "native" in query:
            r_normalized = r_common.get(query["id"], {}).get("normalized")
            comparison["normalized_context_matches"] = compare_context(query["records"], r_normalized)
            comparison["passed"] &= comparison["normalized_context_matches"]
        common_comparisons.append(comparison | {"id": query["id"], "synthetic": query["synthetic"]})
    source_verified = reference.get("source_hashes") == source_hashes and reference.get("dsir_version") == "0.11.0"
    offline_mode = evidence.get("offline", args.offline)
    offline_passed = process.get("child_ok") is True and source_verified and len(common_comparisons) >= 13 and all(c["passed"] for c in common_comparisons)
    live_passed = len(comparisons) >= 15 and all(c["passed"] for c in comparisons)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "mode": "saved_evidence_recomparison" if args.reuse_evidence else "synthetic_common_input" if args.offline else "fresh_live_and_common_input",
              "passed": offline_passed and (offline_mode or live_passed), "common_input_passed": offline_passed,
              "live_parity_passed": live_passed, "live_requested": not offline_mode,
              "source_revision": revision, "source_hashes": source_hashes, "source_verified": source_verified,
              "dsir_version": reference.get("dsir_version"), "r_version": reference.get("r_version"),
              "r_process": process, "catalogue_error": evidence.get("catalogue_error"),
              "live_queries": comparisons, "common_raw_queries": common_comparisons,
              "live_passed": sum(c["passed"] for c in comparisons), "live_unverified": sum(not c["passed"] for c in comparisons),
              "common_raw_passed": sum(c["passed"] for c in common_comparisons), "common_raw_failed": sum(not c["passed"] for c in common_comparisons)}
    save_json(args.output_dir / "parity_results.json", report)
    lines = ["# DSIR 0.11.0 xMart parity", "", f"Generated: {report['generated_at']}",
             f"Reference commit: `{revision}`.", "",
             f"Common-input source parity: {report['common_raw_passed']} passed; {report['common_raw_failed']} failed.",
             f"Independent live parity: {report['live_passed']} passed; {report['live_unverified']} unverified.",
             "Synthetic fixtures validate transformations only; they are never WHO data.",
             "The exact source files and bundled data are loaded without using the installed DSIR package.", "",
             "| Check | Result |", "| --- | --- |"]
    lines += [f"| {c['id']} | {'PASS' if c['passed'] else 'FAIL'} |" for c in common_comparisons]
    lines += [f"| live: {c['id']} | {'PASS' if c['passed'] else 'UNVERIFIED'} |" for c in comparisons]
    (args.output_dir / "parity_results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("passed", "source_verified", "live_passed", "live_unverified", "common_raw_passed", "common_raw_failed")}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
