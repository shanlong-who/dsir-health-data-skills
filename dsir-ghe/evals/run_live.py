"""Explicitly opted-in, bounded official GHE acceptance queries."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from ghe_client import GHEClient
from transport import GHEError, utc_now
from cli import write_result


def run(output_dir):
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=False)
    client = GHEClient(max_rows=5000)
    catalogues = {name: client.dimensions(name) for name in ("measure", "year", "area", "sex", "age")}
    catalogues["cause"] = client.causes()
    (root / "catalogues.json").write_text(json.dumps({
        "retrieved_at": utc_now(), "catalogues": catalogues, "requests": client.http.trace,
        "scope": "Live reference catalogues, not full observation coverage."}, indent=2, ensure_ascii=False), encoding="utf-8")
    latest = max(int(row["code"]) for row in catalogues["year"])
    base = dict(area=["PHL"], year=[latest], sex=["TOTAL"], age=["TOTAL"], cause=["0"])
    specifications = [
        ("all-measures", "get", {**base, "measure": [row["code"] for row in catalogues["measure"]]}),
        ("sex-age-paging", "get", {**base, "year": None, "year_from": latest - 1, "year_to": latest,
                                 "sex": ["FEMALE", "MALE"], "age": ["Y40T44"], "measure": ["deaths", "death_rate"]}),
        ("verified-empty", "get", {**base, "year": None, "year_from": 2099, "year_to": 2099, "measure": ["deaths"]}),
        ("coverage", "coverage", {**base, "year": None}),
        ("invalid-sex", "get", {**base, "sex": ["TYPO"], "measure": ["deaths"]})]
    diabetes = [row for row in catalogues["cause"] if (row["cause_name"] or "").casefold() == "diabetes mellitus"]
    if len(diabetes) == 1:
        specifications.insert(2, ("diabetes", "get", {**base, "cause": [diabetes[0]["cause_code"]],
                                                     "measure": ["deaths", "death_rate"]}))
    outcomes = []
    for name, command, selection in specifications:
        try:
            client.http.page_size = 2 if name == "sex-age-paging" else 5000
            result = client.get_data(**selection) if command == "get" else client.coverage(**selection)
            expected = "filters_no_data" if name == "verified-empty" else "ok"
            passed = result["status"] == expected and result["provenance"]["complete"]
            if name == "sex-age-paging":
                passed = passed and result["provenance"]["pages"] >= 2
        except GHEError as exc:
            result = {**exc.as_dict(), "query": selection, "provenance": {
                "source": "WHO GHE", "backend": "xmart", "complete": False, "requests": client.http.trace}}
            passed = name == "invalid-sex" and exc.code == "invalid_query"
        write_result(root / name, result)
        outcomes.append({"case": name, "status": result["status"], "passed": passed,
                         "rows": result.get("row_count"), "selection": selection})
        print(json.dumps(outcomes[-1]), flush=True)
    report = {"live": True, "created_at": utc_now(), "cases": outcomes,
              "diabetes_exact_match_count": len(diabetes),
              "requests": len(client.http.trace), "passed": all(row["passed"] for row in outcomes)}
    (root / "results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.output_dir))
