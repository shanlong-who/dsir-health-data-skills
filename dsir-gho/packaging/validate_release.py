"""Check ZIP integrity, packaged links, and an optional live run with an empty PATH."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def validate(archive_path, work_dir, live=False):
    workspace = work_dir.resolve() / ("release-check-" + uuid.uuid4().hex[:12])
    workspace.mkdir(parents=True)
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None, "Corrupt ZIP entry"
        entries = archive.namelist()
        for name in entries:
            target = (workspace / name).resolve()
            assert workspace in target.parents, "Unsafe archive path"
        archive.extractall(workspace)
    skill = workspace / "dsir-gho"
    assert (skill / "SKILL.md").is_file()
    assert not (skill / "reports").exists(), "Runtime package must exclude recorded observations"
    assert not (skill / "evals").exists(), "Reference R checks belong in the source archive"
    for path in skill.rglob("*.md"):
        content = path.read_text(encoding="utf-8")
        for link in re.findall(r"\]\(([^)]+)\)", content):
            if "://" not in link and not link.startswith("#"):
                assert (path.parent / link.split("#")[0]).exists(), f"Broken packaged link: {path}: {link}"
    header = (skill / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1]
    assert re.search(r"^name: dsir-gho$", header, re.M)
    assert re.search(r"^description: .+", header, re.M)
    config = (skill / "agents/openai.yaml").read_text(encoding="utf-8")
    assert "$dsir-gho" in config
    assert "allow_implicit_invocation: false" not in config
    environment = dict(os.environ, PATH="", R_HOME=str(workspace / "no-r-installed"))
    base_command = [sys.executable, str(skill / "scripts/cli.py")]
    check = subprocess.run(base_command + ["--help"], env=environment, capture_output=True, text=True, encoding="utf-8")
    assert check.returncode == 0, check.stderr
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "archive": str(archive_path.resolve()),
              "archive_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(), "entries": len(entries),
              "static_checks": "pass", "python": sys.version.split()[0], "path_empty": True,
              "r_home_unavailable": True, "import_and_help": "pass", "live_checked": live}
    if live:
        result = subprocess.run(base_command + ["doctor"], env=environment, capture_output=True, text=True, encoding="utf-8", timeout=180)
        doctor = json.loads(result.stdout)
        assert result.returncode == 0 and doctor["status"] == "ok", doctor
        output_dir = workspace / "live-wpr"
        result = subprocess.run(base_command + ["--page-size", "7", "get", "UHC_INDEX_REPORTED", "--locations", "WPRO",
                                                "--output-dir", str(output_dir)], env=environment,
                                capture_output=True, text=True, encoding="utf-8", timeout=240)
        summary = json.loads(result.stdout)
        assert result.returncode == 0 and summary["status"] == "ok", summary
        response = json.loads((output_dir / "response.json").read_text(encoding="utf-8"))
        assert response["provenance"]["complete"] and response["qa"]["status"] == "pass"
        report.update(doctor=doctor, live_status=response["status"], live_rows=response["row_count"],
                      live_years=response["available_years_in_result"], live_pages=response["provenance"]["pages"],
                      live_qa=response["qa"]["status"], live_evidence=str(output_dir))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    report = validate(args.archive, args.work_dir, args.live)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
