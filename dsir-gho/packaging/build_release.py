"""Build a compact installable skill and a separate source/validation archive."""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"
RUNTIME_DIRS = {"agents", "scripts", "references", "packaging"}
RUNTIME_ROOT = {"SKILL.md", "README.md", "DESIGN.md", "LICENSE"}


def files(source=False):
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if not path.is_file() or any(part in {"__pycache__", ".git", ".venv", "outputs"} for part in relative.parts) or path.suffix == ".pyc":
            continue
        if source or relative.parts[0] in RUNTIME_DIRS or str(relative) in RUNTIME_ROOT:
            yield path, relative


def build(destination):
    destination = destination.resolve()
    if destination == ROOT or ROOT in destination.parents:
        raise ValueError("Release output must be outside the source folder.")
    destination.mkdir(parents=True, exist_ok=True)
    outputs = []
    for source in (False, True):
        suffix = "-source" if source else ""
        output = destination / f"dsir-gho-{VERSION}{suffix}.zip"
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for path, relative in files(source):
                info = zipfile.ZipInfo("dsir-gho/" + relative.as_posix(), (2026, 9, 9, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                content = path.read_bytes()
                if not source and relative.as_posix() == "README.md":
                    text = content.decode("utf-8")
                    start = text.find("## Tests and evaluation")
                    end = text.find("\n## ", start + 4) if start >= 0 else -1
                    if start >= 0:
                        text = text[:start] + "## Tests and evaluation\n\nThe separate source archive contains the test scripts, 46 evaluation cases, and validation reports. These maintainer files and recorded observations are excluded from this runtime package. R is used only in that archive for parity checks.\n" + (text[end:] if end >= 0 else "")
                    text = re.sub(r"\[([^\]]+)\]\(((?:evals|reports)/[^)]+)\)",
                                  r"\1 (in the separate source archive: `\2`)", text)
                    content = text.encode("utf-8")
                archive.writestr(info, content)
        with zipfile.ZipFile(output) as archive:
            if archive.testzip() is not None:
                raise ValueError("Archive integrity check failed.")
        outputs.append({"file": output.name, "bytes": output.stat().st_size,
                        "sha256": hashlib.sha256(output.read_bytes()).hexdigest()})
    manifest = destination / f"dsir-gho-{VERSION}-checksums.json"
    manifest.write_text(json.dumps(outputs, indent=2) + "\n", encoding="utf-8")
    return outputs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    print(json.dumps(build(parser.parse_args().output_dir), indent=2))
