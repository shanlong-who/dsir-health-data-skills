"""Package the verified standalone GHO release as a skills-only plugin."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "dist/dsir-gho-0.1.1.zip"
VERSION = "0.1.3"
LOGO = ROOT / "packaging/assets/dsir-logo.jpg"
PLUGIN = ROOT / "plugins/dsir-gho"
OUTPUT = ROOT / f"dist/dsir-gho-plugin-{VERSION}.zip"


def main():
    identity = {
        "name": "dsir-gho", "version": VERSION,
        "description": "Discover and retrieve public WHO GHO health data with verified indicators and DSIR-compatible cleaning.",
        "author": {"name": "Shanlong Ding"}, "license": "MIT",
        "keywords": ["WHO", "GHO", "health-data", "DSIR"]}
    interface = {
        "displayName": "DSIR GHO Health Data Skill",
        "shortDescription": "Find and download WHO GHO data",
        "longDescription": "Find WHO Global Health Observatory indicators and retrieve public health statistics by country, region, year and named dimensions. Export CSV and JSON with source details and completeness checks. Intended for analysts and researchers; it does not provide clinical advice. Uses WHO public xMart, with an explicit legacy adapter. Requires Python 3.10+ and permitted HTTPS access in the agent runtime. No R or maintainer-hosted server is required. Maintenance candidate: offline checks and common-input parity passed, but complete live retrieval and independent live parity remain unverified after WHO requests redirected on 7 October 2026. Failed requests are reported; observations are not invented.",
        "developerName": "Shanlong Ding", "category": "Data & Analytics",
        "websiteURL": "https://shanlong-who.github.io/dsir-health-data-skills/",
        "privacyPolicyURL": "https://shanlong-who.github.io/dsir-health-data-skills/privacy.html",
        "supportURL": "https://github.com/shanlong-who/dsir-health-data-skills/issues",
        "composerIcon": "./assets/dsir-logo.jpg",
        "logo": "./assets/dsir-logo.jpg",
        "capabilities": ["Read", "Write"],
        "defaultPrompt": ["Show historical UHC service coverage for the Western Pacific Region.",
                          "Get measles reported cases in the Philippines since 2015.",
                          "Find WHO indicators for catastrophic health expenditure above 10%."]}
    portable = {"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                **identity, "extensions": {"com.openai": {"interface": interface}}}
    compatibility = {**identity, "skills": "./skills/", "interface": interface}
    if not LOGO.is_file():
        raise RuntimeError("The DSIR branding asset is missing.")
    (PLUGIN / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(LOGO, PLUGIN / "assets/dsir-logo.jpg")
    (PLUGIN / ".codex-plugin").mkdir(parents=True, exist_ok=True)
    (PLUGIN / "plugin.json").write_bytes((json.dumps(portable, indent=2) + "\n").encode("utf-8"))
    (PLUGIN / ".codex-plugin/plugin.json").write_bytes((json.dumps(compatibility, indent=2) + "\n").encode("utf-8"))
    copied = []
    with zipfile.ZipFile(SOURCE) as archive:
        assert archive.testzip() is None
        for name in archive.namelist():
            relative = Path(name).relative_to("dsir-gho")
            if relative.parts[0] not in {"scripts", "references", "agents", "SKILL.md", "LICENSE"}:
                continue
            target = (PLUGIN / "skills/dsir-gho" / relative).resolve()
            assert PLUGIN.resolve() in target.parents
            target.parent.mkdir(parents=True, exist_ok=True)
            content = archive.read(name)
            target.write_bytes(content)
            copied.append({"path": "skills/dsir-gho/" + relative.as_posix(), "sha256": hashlib.sha256(content).hexdigest()})
        (PLUGIN / "LICENSE").write_bytes(archive.read("dsir-gho/LICENSE"))
    if not (PLUGIN / "README.md").is_file():
        raise RuntimeError("Write the plugin installation README before building the release.")
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PLUGIN.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                info = zipfile.ZipInfo("dsir-gho/" + path.relative_to(PLUGIN).as_posix(), (2026, 10, 7, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes())
    with zipfile.ZipFile(OUTPUT) as archive:
        assert archive.testzip() is None
    report = {"artifact": OUTPUT.name, "bytes": OUTPUT.stat().st_size,
              "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
              "source_skill_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                "plugin_version": VERSION, "skill_runtime_version": "0.1.1",
              "branding_asset_sha256": hashlib.sha256(LOGO.read_bytes()).hexdigest(),
              "validation_status": "maintenance_candidate_pending_live_retrieval_and_independent_parity",
              "packaged_files": copied, "runtime_files_identical_to_verified_skill": True,
        "published": False, "marketplace_registered": False,
              "mcp_server": False, "r_runtime_required": False}
    (ROOT / f"dist/dsir-gho-plugin-{VERSION}-checksums.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "packaged_files"}, indent=2))


if __name__ == "__main__":
    main()
