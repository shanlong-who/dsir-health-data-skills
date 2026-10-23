"""Opt-in, small independent WHO checks. Saves fresh evidence; never supplies runtime data."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from gho_client import GHOClient, GHOError, utc_now
from cli import build_response, write_result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--suite", choices=["base", "extended", "all"], default="all")
    parser.add_argument("--case", help="Run one named case from the selected suite.")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    report = {"started_at": utc_now(), "mode": "live", "cases": [], "catalogues": {}}
    clients = {"legacy": GHOClient(timeout=25, retries=2),
               "xmart": GHOClient(backend="xmart", timeout=25, retries=2)}

    def save():
        (args.output_dir / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    for backend, client in clients.items():
        try:
            entries = client.catalogue()
            payload = json.dumps(entries, ensure_ascii=False, indent=2).encode("utf-8")
            (args.output_dir / (backend + "-catalogue.json")).write_bytes(payload)
            report["catalogues"][backend] = {"count": len(entries), "sha256": hashlib.sha256(payload).hexdigest(),
                                             "provenance": client.catalogue_provenance}
        except GHOError as exc:
            report["catalogues"][backend] = exc.as_dict()
        save()
    # Codes must still be verified against the live catalogue by each adapter.
    cases = [
        ("legacy-default-dtp", "legacy", "WHS4_100", {"locations": ["PHL", "CHN"], "year_from": 2020, "year_to": 2021}, "ok"),
        ("xmart-dtp", "xmart", "WHS4_100", {"locations": ["PHL", "CHN"], "year_from": 2020, "year_to": 2021}, "ok"),
        ("legacy-only-measles", "legacy", "WHS3_62", {"locations": ["PHL"], "year_from": 2020, "year_to": 2021}, "ok"),
        ("xmart-absent-measles", "xmart", "WHS3_62", {}, "indicator_not_found"),
        ("legacy-sex", "legacy", "WHOSIS_000001", {"locations": ["PHL"], "year_from": 2020, "year_to": 2021,
                                                    "dimensions": {"dim1": "SEX_FMLE"}}, "ok"),
        ("legacy-valid-empty", "legacy", "WHOSIS_000001", {"locations": ["PHL"], "year_from": 2099,
                                                            "dimensions": {"dim1": "SEX_FMLE"}}, "filters_no_data"),
        ("legacy-invalid-sex", "legacy", "WHOSIS_000001", {"dimensions": {"dim1": "SEX_TYP0"}}, "invalid_query"),
        ("xmart-sex", "xmart", "WHOSIS_000001", {"locations": ["PHL"], "year_from": 2020, "year_to": 2021,
                                                  "dimensions": {"dim1": "SEX_FMLE"}}, "ok"),
    ]
    extended = [
        ("legacy-age-sex", "legacy", "LIFE_0000000029", {"locations": ["PHL"], "year_from": 2020, "year_to": 2020,
                                                        "dimensions": {"dim1": "SEX_FMLE", "dim2": "AGEGROUP_YEARS15-19"}}, "ok"),
        ("xmart-age-sex", "xmart", "NCD_BMI_30A", {"locations": ["PHL"], "year_from": 2020, "year_to": 2020,
                                                   "dimensions": {"dim1": "SEX_FMLE", "dim2": "AGEGROUP_Y_GE18"}}, "ok"),
        ("xmart-only-tb", "xmart", "TB_mdr_prct", {"locations": ["PHL"], "year_from": 2020, "year_to": 2021}, "ok"),
        ("legacy-absent-tb", "legacy", "TB_mdr_prct", {}, "indicator_not_found"),
        ("xmart-dotted-code", "xmart", "2017_AH_6.3", {"locations": ["PHL"], "year_from": 2017, "year_to": 2017}, "ok"),
    ]
    cases = cases if args.suite == "base" else extended if args.suite == "extended" else cases + extended
    if args.case:
        cases = [case for case in cases if case[0] == args.case]
        if not cases:
            parser.error("Unknown case for the selected suite.")
    for name, backend, code, query, expected in cases:
        client = clients[backend]
        start = len(client.trace)
        record = {"case": name, "backend": backend, "indicator": code, "query": query, "expected": expected}
        try:
            result = client.get_gho_data(code, **query)
            response = build_response(result, client)
            write_result(args.output_dir / name, response, result["records"], result.get("source_records"))
            record.update(actual=response["status"], row_count=response["row_count"], qa=response["qa"]["status"])
        except GHOError as exc:
            record.update(actual=exc.code, error=exc.as_dict()["error"])
        record["requests"] = client.trace[start:]
        record["passed"] = record["actual"] == expected and record.get("qa") != "fail"
        report["cases"].append(record)
        print(name, record["actual"], "PASS" if record["passed"] else "FAIL", flush=True)
        save()
    report["completed_at"] = utc_now()
    report["passed"] = all(c["passed"] for c in report["cases"])
    save()
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
