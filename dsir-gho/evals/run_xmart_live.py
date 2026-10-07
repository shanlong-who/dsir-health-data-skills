"""Small fresh xMart checks; errors and blocked checks remain explicit."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from gho_client import GHOClient, GHOError, utc_now
from indicator_search import describe_indicator, search_indicators
from cli import build_response


def run(output):
    client = GHOClient(retries=2, timeout=30)
    checks = []

    def check(label, fn):
        try:
            details = fn()
            item = {"id": label, "status": "pass", "details": details}
        except GHOError as exc:
            item = {"id": label, "status": "fail", **exc.as_dict()}
            item["status"] = "fail"
        except AssertionError as exc:
            item = {"id": label, "status": "fail", "error": {"code": "contract_failed", "message": str(exc)}}
        checks.append(item)
        print(f"{label}: {item['status']}", flush=True)
        return item

    def catalogue():
        rows = client.catalogue()
        assert rows
        return {"rows": len(rows), "backend": client.backend}

    def reference(path, required, order="Sys_PK"):
        result = client.collection(path, {"$orderby": order}, paged=True)
        assert result["provenance"]["complete"] and result["records"]
        assert all(set(required).issubset(row) for row in result["records"])
        return result["provenance"]

    def probe(path, required):
        result = client.collection(path, {"$top": 1})
        assert result["records"] and set(required).issubset(result["records"][0])
        assert result["provenance"]["complete"] is False
        return {"scope": "One-row connectivity/schema probe; not a complete catalogue or observation retrieval.",
                "provenance": result["provenance"]}

    check("geography_probe", lambda: probe("DATA_/REF_GEO", ["GEO_CODE_M49", "GEO_CODE_ISO_3"]))
    check("disaggregation_probe", lambda: probe("DATA_/REF_DISAGGREGATIONS", ["TERM_SET", "TERM_KEY"]))
    check("relay_probe", lambda: probe("DATA_/RELAY_GHO", ["IND_ID", "DIM_TIME", "VALUE_NUMERIC"]))

    check("geography_reference", lambda: reference("DATA_/REF_GEO", ["GEO_CODE_M49", "GEO_CODE_ISO_3", "GEO_TYPE", "GEO_NAME_SHORT"]))
    check("disaggregation_reference", lambda: reference("DATA_/REF_DISAGGREGATIONS", ["TERM_SET", "TERM_KEY", "TERM_NAME_MAIN"], "TERM_SET,TERM_KEY"))
    # Probe a published table to derive a small fact selection, never a GHO code.
    # This validates transport completeness and does not bypass directory routing.
    def relay_paging():
        probe = client.collection("DATA_/RELAY_GHO", {"$top": 1, "$orderby": "Sys_PK"})
        assert probe["records"] and "IND_ID" in probe["records"][0]
        seed = probe["records"][0]
        from xmart import in_filter
        filters = [in_filter("IND_ID", [seed["IND_ID"]])]
        for field in ("DIM_GEO_CODE_M49", "DIM_TIME"):
            if seed.get(field) is not None:
                filters.append(in_filter(field, [str(seed[field])]))
        params = {"$filter": " and ".join(filters), "$orderby": "Sys_PK"}
        ordinary = client.collection("DATA_/RELAY_GHO", params, paged=True)
        forced = client.collection("DATA_/RELAY_GHO", params, paged=True, page_size=1)
        assert ordinary["records"] == forced["records"] and forced["provenance"]["complete"]
        return {"ordinary": ordinary["provenance"], "forced": forced["provenance"],
                "scope": "Raw xMart transport check; no indicator identity inferred without the directory."}

    check("raw_relay_forced_paging", relay_paging)
    available = check("indicator_directory", catalogue)["status"] == "pass"
    cases = [
        ("measles_phl", {"indicator": "WHS3_62", "locations": ["PHL"], "year_from": 2015}),
        ("uhc_wpr", {"indicator": "UHC_INDEX_REPORTED", "locations": ["WPR"], "spatial_type": "REGION"}),
        ("named_sex", {"indicator": "NCDMORT3070", "locations": ["PHL"], "year_from": 2020, "dimensions": {"DIM_SEX": "TOTAL"}}),
        ("verified_empty_filter", {"indicator": "NCDMORT3070", "locations": ["PHL"], "year_from": 2099}),
    ]
    for label, args in cases:
        if not available:
            checks.append({"id": label, "status": "blocked", "reason": "Live indicator directory failed; no cached routes, legacy fallback or code substitution used."})
            continue
        def retrieve(args=args):
            result = client.get_gho_data(**args)
            response = build_response(result, client)
            assert result["provenance"]["complete"] and response["qa"]["status"] != "fail"
            return {"status": response["status"], "rows": response["row_count"], "provenance": response["provenance"]}
        check(label, retrieve)
    if available:
        check("live_search", lambda: search_indicators("tuberculosis", client))
        check("live_describe", lambda: describe_indicator("NCDMORT3070", client))
    else:
        checks.extend({"id": label, "status": "blocked", "reason": "Live directory unavailable."} for label in ("live_search", "live_describe"))
    report = {"generated_at": utc_now(), "mode": "fresh_live_requests", "backend": "xmart",
              "reference_dsir_version": "0.11.0", "reference_dsir_commit": "885464b1fade2f8b6d02dde93f9080e4b3f4f2a5",
              "passed": all(row["status"] == "pass" for row in checks), "checks": checks, "requests": client.trace}
    report["counts"] = {status: sum(row["status"] == status for row in checks) for status in ("pass", "fail", "blocked")}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    raise SystemExit(run(parser.parse_args().output))
