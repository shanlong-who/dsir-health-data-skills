"""Build standalone, source and skills-only plugin releases without R."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"
RUNTIME_DIRS = {"scripts", "references", "agents", "assets"}
RUNTIME_FILES = {"SKILL.md", "LICENSE", "README.md", "DESIGN.md"}


def entries(root):
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if "preflight" in relative.parts:
            continue
        if path.is_file() and not any(part.startswith(".") and part != ".codex-plugin" or part == "__pycache__" for part in relative.parts) and path.suffix != ".pyc":
            yield path, relative


def archive(destination, files):
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as package:
        for path, name in files:
            info = zipfile.ZipInfo(name, (2026, 9, 16, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            package.writestr(info, path.read_bytes())
    with zipfile.ZipFile(destination) as package:
        assert package.testzip() is None
    return {"file": destination.name, "bytes": destination.stat().st_size,
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}


def build(output=None, plugin=None):
    output = Path(output or ROOT.parent / "dist").resolve()
    plugin = Path(plugin or ROOT.parent / "plugins/dsir-sdg").resolve()
    if ROOT == output or ROOT in output.parents or ROOT == plugin or ROOT in plugin.parents:
        raise ValueError("Build artifacts must be outside the source skill directory.")
    output.mkdir(parents=True, exist_ok=True)
    plugin.mkdir(parents=True, exist_ok=True)
    identity = {"name": "dsir-sdg", "version": VERSION,
                "description": "Discover UN SDG indicators and series, retrieve complete observations, and preserve DSIR cleaning semantics with dimensions and provenance.",
                "author": {"name": "Shanlong Ding"}, "license": "MIT",
                "keywords": ["DSIR", "SDG", "UN", "health-data", "sustainable-development"]}
    interface = {"displayName": "DSIR SDG Data Skill", "shortDescription": "Find UN SDG data with verified series and scope.",
                 "longDescription": "Query public UN SDG data using natural language. Confirm indicators, series, locations, units and population dimensions; export complete CSV and JSON. Requires Python 3.10+ and script HTTPS access, with no R or hosted service.",
                 "developerName": "Shanlong Ding", "category": "Productivity", "capabilities": ["Read", "Write"],
                 "composerIcon": "./assets/dsir-logo.jpg", "logo": "./assets/dsir-logo.jpg",
                 "defaultPrompt": ["Compare UHC service coverage in China, Japan and the Philippines.",
                                   "Get Philippine TB incidence since 2015 from UN SDG.",
                                   "Find the current SDG financial protection measure."]}
    (plugin / ".codex-plugin").mkdir(exist_ok=True)
    (plugin / "plugin.json").write_text(json.dumps({"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json", **identity,
                                                  "extensions": {"com.openai": {"interface": interface}}}, indent=2) + "\n", encoding="utf-8")
    (plugin / ".codex-plugin/plugin.json").write_text(json.dumps({**identity, "skills": "./skills/", "interface": interface}, indent=2) + "\n", encoding="utf-8")
    runtime = []
    for path, relative in entries(ROOT):
        if relative.parts[0] in RUNTIME_DIRS or relative.as_posix() in RUNTIME_FILES:
            runtime.append((path, "dsir-sdg/" + relative.as_posix()))
            if relative.parts[0] in RUNTIME_DIRS or relative.name in {"SKILL.md", "LICENSE"}:
                target = plugin / "skills/dsir-sdg" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
    (plugin / "assets").mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "assets/dsir-logo.jpg", plugin / "assets/dsir-logo.jpg")
    for name in ("LICENSE", "README.md"):
        shutil.copyfile(ROOT / name, plugin / name)
    result = [archive(output / f"dsir-sdg-{VERSION}.zip", runtime),
              archive(output / f"dsir-sdg-{VERSION}-source.zip", [(p, "dsir-sdg/" + r.as_posix()) for p, r in entries(ROOT)]),
              archive(output / f"dsir-sdg-plugin-{VERSION}.zip", [(p, "dsir-sdg/" + r.as_posix()) for p, r in entries(plugin)])]
    (output / f"dsir-sdg-{VERSION}-checksums.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    build()
