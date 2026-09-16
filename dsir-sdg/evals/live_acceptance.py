"""Maintainer live checks; recorded observations are never runtime defaults."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from sdg_client import SDGClient, SDGError, utc_now
from cli import build_response, write_result
from indicator_search import search_indicators
from locations import resolve_locations


def main():
    output = ROOT / "reports/live"
    output.mkdir(parents=True, exist_ok=True)
    client = SDGClient()
    catalogue = {"Indicator": client.indicators(), "Series": client.series(), "GeoArea": client.areas()}
    (output / "catalogues.json").write_text(json.dumps({"retrieved_at": utc_now(), "catalogues": catalogue, "requests": client.trace}, indent=2), encoding="utf-8")
    queries = [("3.8.1", ["99047", "608", "156", "392"], None),
               ("3.1.1", ["608"], 2015), ("3.1.2", ["608"], 2015), ("3.2.1", ["608"], 2015),
               ("3.2.2", ["608"], 2015), ("3.3.1", ["608"], 2015), ("3.3.2", ["608"], 2015),
               ("3.3.3", ["608"], 2015), ("3.4.1", ["608"], 2015), ("3.4.2", ["608"], 2015),
               ("3.8.2", ["608"], 2015), ("2.2.1", ["608"], 2015), ("6.1.1", ["608"], 2015)]
    def fetch(spec):
        indicator, areas, year = spec
        api = SDGClient(page_size=7 if indicator == "3.8.1" else 1000)
        api._cache.update(catalogue)
        args = {"indicator": indicator, "locations": areas, "year_from": year}
        try:
            result = api.get_sdg_data(**args)
            response = build_response(result, api)
            write_result(output / ("indicator-" + indicator), response, result["records"])
            print(json.dumps({"indicator": indicator, "status": response["status"], "rows": len(result['records']), "pages": result['pages'], "qa": response['qa']['status']}), flush=True)
            return {"id": "live-" + indicator, "indicator": indicator, "args": args,
                    "synthetic": False, "records": result["records"], "status": response["status"], "requests": api.trace}
        except SDGError as exc:
            print(json.dumps({"indicator": indicator, **exc.as_dict()}), flush=True)
            return {"id": "live-" + indicator, "indicator": indicator, "args": args, "synthetic": False, "records": [], **exc.as_dict()}
    results = list(ThreadPoolExecutor(max_workers=3).map(fetch, queries))
    parity = ROOT / "reports/parity"
    parity.mkdir(parents=True, exist_ok=True)
    (parity / "common_raw_input.json").write_text(json.dumps({"retrieved_at": utc_now(), "queries": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    searches = [search_indicators(q, client=client) for q in ("UHC SCI", "maternal mortality", "TB incidence", "catastrophic health expenditure above 10%")]
    resolutions = [resolve_locations(names, client=client) for names in (["WPRO"], ["PHL", "China", "Japan"], ["Congo"])]
    (output / "discovery.json").write_text(json.dumps({"searches": searches, "locations": resolutions}, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if all(r['status'] == 'ok' and r['records'] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
