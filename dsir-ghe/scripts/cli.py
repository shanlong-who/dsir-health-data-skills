"""GHE command-line tools for an agent-supplied Python runtime."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
import tempfile
from pathlib import Path

from ghe_client import DATA_FIELDS, GHEClient, METHODS_URL
from transport import BASE_URL, TABLE, GHEError, utc_now


def write_result(output_dir, response):
    """Expose a result directory only after every file and hash is written."""
    destination = Path(output_dir).expanduser().resolve()
    if destination.exists():
        raise GHEError("output_exists", "Choose a new directory; previous results are not overwritten.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".ghe-export-", dir=destination.parent) as folder:
        stage = Path(folder) / "result"
        files = write_files(stage, response)
        if destination.exists():
            raise GHEError("output_exists", "The output directory appeared during export; choose a new directory.")
        stage.rename(destination)
    return {name: str(destination / name) for name in files}


def write_files(destination, response):
    try:
        destination.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise GHEError("output_exists", "Choose a new directory; previous results are not overwritten.") from exc
    files = {}
    objects = {"response.json": {key: value for key, value in response.items() if key != "raw"}}
    if "raw" in response:
        objects["raw.json"] = response["raw"]
    for name, value in objects.items():
        path = destination / name
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        files[name] = str(path)
    if "data" in response:
        path = destination / "data.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=DATA_FIELDS)
            writer.writeheader()
            writer.writerows(response["data"])
        files[path.name] = str(path)
    manifest = {"created_at": utc_now(), "files": {
        name: hashlib.sha256(Path(path).read_bytes()).hexdigest() for name, path in files.items()}}
    path = destination / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    files[path.name] = str(path)
    return files


def parser():
    root = argparse.ArgumentParser(description="Retrieve WHO GHE estimates using the host's Python; no R or API key.")
    root.add_argument("--page-size", type=int, default=5000)
    root.add_argument("--max-rows", type=int, default=100000)
    root.add_argument("--timeout", type=float, default=30)
    commands = root.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor")
    doctor.add_argument("--live", action="store_true")
    dimensions = commands.add_parser("dimensions")
    dimensions.add_argument("dimension", choices=("measure", "area", "year", "sex", "age", "cause"))
    causes = commands.add_parser("causes")
    causes.add_argument("--search")
    locations = commands.add_parser("locations")
    locations.add_argument("names", nargs="+")
    for command in ("get", "coverage"):
        selection = commands.add_parser(command)
        selection.add_argument("--area", nargs="+", required=True)
        selection.add_argument("--year", nargs="+", type=int)
        selection.add_argument("--year-from", type=int)
        selection.add_argument("--year-to", type=int)
        selection.add_argument("--sex", nargs="+", required=True)
        selection.add_argument("--age", nargs="+", required=True)
        selection.add_argument("--cause", nargs="+", required=True)
        if command == "get":
            selection.add_argument("--measure", nargs="+", required=True)
        selection.add_argument("--output-dir", required=True)
    for command in (doctor, dimensions, causes, locations):
        command.add_argument("--output-dir")
    return root


def run_command(args, client):
    if args.command == "doctor":
        result = {"status": "ok", "python": platform.python_version(), "r_required": False,
                  "third_party_packages_required": False, "api_key_required": False,
                  "country_mapping_rows": len(client.countries), "network_tested": args.live}
        if args.live:
            result["measures"] = client.dimensions("measure")
            result["years"] = client.dimensions("year")
        return result
    if args.command == "dimensions":
        return {"status": "ok", "dimension": args.dimension, "catalogue": client.dimensions(args.dimension)}
    if args.command == "causes":
        rows = client.causes(args.search)
        return {"status": "ok" if rows else "no_matches", "search": args.search, "causes": rows}
    if args.command == "locations":
        return client.locations(args.names)
    selection = {key: getattr(args, key, None) for key in
                 ("area", "year", "year_from", "year_to", "sex", "age", "cause")}
    if args.command == "get":
        return client.get_data(**selection, measure=args.measure)
    return client.coverage(**selection)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    client = None
    try:
        if sys.version_info < (3, 10):
            raise GHEError("unsupported_runtime", "The AI host must supply Python 3.10 or later.")
        client = GHEClient(page_size=args.page_size, max_rows=args.max_rows, timeout=args.timeout)
        result = run_command(args, client)
        if "provenance" not in result:
            result["provenance"] = {
                "source": "WHO Global Health Estimates", "backend": "xmart", "base_url": BASE_URL,
                "table": TABLE, "requests": list(client.http.trace), "generated_at": utc_now(),
                "dsir_reference": client.reference_provenance, "release": None,
                "catalogue_scope": "Area, age and cause discovery uses a latest-year reference slice; this is not full observation coverage.",
                "method_context_url": METHODS_URL}
        files = write_result(args.output_dir, result) if args.output_dir else None
        preview = {key: value for key, value in result.items() if key not in {"data", "raw", "observation_context"}}
        if "data" in result:
            preview.update(preview=result["data"][:8], preview_is_complete=len(result["data"]) <= 8,
                           instruction="Read response.json and data.csv for the complete estimates, units and strata.")
        if files:
            preview["files"] = files
        print(json.dumps(preview, ensure_ascii=False, indent=2, allow_nan=False))
        return 0 if result["status"] in {"ok", "filters_no_data", "no_matches"} else 2
    except (GHEError, OSError, ValueError, TypeError) as exc:
        result = exc.as_dict() if isinstance(exc, GHEError) else {
            "status": "error", "error": {"code": "local_processing_failed", "message": str(exc)}}
        result["provenance"] = {"source": "WHO Global Health Estimates", "backend": "xmart",
                                "base_url": BASE_URL, "table": TABLE, "complete": False,
                                "requests": list(client.http.trace) if client else [],
                                "fallback_performed": False}
        if args.output_dir and not Path(args.output_dir).expanduser().exists():
            try:
                result["files"] = write_result(args.output_dir, result)
            except (OSError, GHEError) as export_error:
                result["export_error"] = str(export_error)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
