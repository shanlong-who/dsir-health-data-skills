"""Build local GHO test packages from tracked source, without editing that source."""
import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.4-test.1"
MARKETPLACE = "dsir-gho-local-test"
RUNTIME_DIRS = {"scripts", "references", "agents"}
SKIP_PARTS = {"__pycache__", ".venv", "outputs"}


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def repository_state(root):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args])

    return {
        "commit": git("rev-parse", "HEAD").decode().strip(),
        "dirty": bool(git("status", "--porcelain", "--untracked-files=all")),
        "tracked": set(git("ls-files", "-z").decode("utf-8").split("\0")) - {""},
    }


def read_source(root, relative, tracked):
    path = root / relative
    if relative not in tracked or not path.is_file():
        raise ValueError(f"Required tracked source is missing: {relative}")
    if root not in path.resolve().parents or any(
        item.is_symlink() for item in (path, *path.parents) if item != root and root in item.parents
    ):
        raise ValueError(f"Source must not use symlinks or leave the repository: {relative}")
    return path.read_bytes()


def runtime_files(root, tracked):
    selected = {"dsir-gho/SKILL.md", "dsir-gho/LICENSE"}
    for name in tracked:
        parts = PurePosixPath(name).parts
        if (len(parts) >= 3 and parts[0] == "dsir-gho" and parts[1] in RUNTIME_DIRS
                and not any(part.startswith(".") or part in SKIP_PARTS for part in parts)
                and PurePosixPath(name).suffix in {".py", ".md", ".json", ".yaml", ".yml"}):
            selected.add(name)
    for required in ("scripts/cli.py", "scripts/gho_client.py", "scripts/xmart.py", "agents/openai.yaml"):
        if "dsir-gho/" + required not in selected:
            raise ValueError(f"Required runtime file is not tracked: {required}")
    return {name.removeprefix("dsir-gho/"): read_source(root, name, tracked) for name in sorted(selected)}


def validate_archive(path, expected):
    """Check every byte, duplicate names, paths and CRC before a package is offered."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != {"dsir-gho/" + name for name in expected}:
            raise ValueError("Archive entries differ from the build inputs")
        if archive.testzip() is not None:
            raise ValueError("Archive CRC failed")
        for name, content in expected.items():
            parts = PurePosixPath(name).parts
            if not parts or ".." in parts or "\\" in name or ":" in name or name.startswith("/"):
                raise ValueError(f"Unsafe package path: {name}")
            if archive.read("dsir-gho/" + name) != content:
                raise ValueError(f"Packaged bytes differ from source: {name}")


def write_archive(path, files):
    with zipfile.ZipFile(path, "x", zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo("dsir-gho/" + name, (2026, 10, 23, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if name.endswith(".sh") else 0o100644) << 16
            archive.writestr(info, content)
    validate_archive(path, files)
    return {"file": path.name, "bytes": path.stat().st_size, "sha256": sha256(path.read_bytes())}


def build(destination, version=VERSION, *, root=ROOT, allow_dirty=False):
    root, destination = root.resolve(), Path(destination).resolve()
    if not re.fullmatch(r"\d+\.\d+\.\d+-test\.\d+", version):
        raise ValueError("This builder only produces local test versions, for example 0.1.4-test.1")
    if destination == root or destination in root.parents or (
        root in destination.parents and destination.relative_to(root).parts[0] != "dist"
    ):
        raise ValueError("Output must be outside the repository or in its ignored dist directory")
    state = repository_state(root)
    if state["dirty"] and not allow_dirty:
        raise ValueError("Commit or review source changes first; --allow-dirty is for development checks only")
    tracked = state["tracked"]
    runtime = runtime_files(root, tracked)
    portable = json.loads(read_source(root, "plugins/dsir-gho/plugin.json", tracked))
    compatibility = json.loads(read_source(root, "plugins/dsir-gho/.codex-plugin/plugin.json", tracked))
    interface = portable["extensions"]["com.openai"]["interface"]
    for key in ("name", "version", "description", "author", "license", "keywords"):
        if portable[key] != compatibility[key]:
            raise ValueError(f"Plugin manifests disagree: {key}")
    if portable["name"] != "dsir-gho" or compatibility["skills"] != "./skills/" or interface != compatibility["interface"]:
        raise ValueError("Plugin identity, skill path or interfaces disagree")
    for manifest in (portable, compatibility):
        manifest["version"] = version
    interface["displayName"] = "DSIR GHO Local Test"
    compatibility["interface"] = interface
    guide = read_source(root, "packaging/GHO_TESTING.md", tracked)
    metadata = {
        "package_version": version, "mode": "local_test",
        "source_commit": state["commit"], "source_dirty": state["dirty"],
        "runtime_source": "dsir-gho/", "default_backend": "legacy", "automatic_fallback": False,
        "runtime_files": {name: sha256(content) for name, content in sorted(runtime.items())},
        "published": False, "marketplace_registered": False,
    }
    build_info = json_bytes(metadata)
    plugin = {"skills/dsir-gho/" + name: content for name, content in runtime.items()}
    plugin.update({
        "plugin.json": json_bytes(portable), ".codex-plugin/plugin.json": json_bytes(compatibility),
        "assets/dsir-logo.jpg": read_source(root, "plugins/dsir-gho/assets/dsir-logo.jpg", tracked),
        "LICENSE": runtime["LICENSE"],
        "README.md": read_source(root, "plugins/dsir-gho/README.md", tracked),
        "TESTING.md": guide, "BUILD.json": build_info,
    })
    standalone = dict(runtime)
    standalone.update({
        "README.md": (f"# DSIR GHO local test skill {version}\n\n"
                      "This standalone skill contains the same runtime as the local test plugin.\n"
                      "Use one installation method at a time. See [TESTING.md](TESTING.md)\n"
                      "for installation, acceptance checks and limitations. Source identity and\n"
                      "runtime file hashes are in BUILD.json. No publication is performed.\n").encode(),
        "TESTING.md": guide, "BUILD.json": build_info,
    })
    for name in ("install.ps1", "install.sh"):
        standalone["packaging/" + name] = read_source(root, "dsir-gho/packaging/" + name, tracked)
    # All source checks precede output creation. Never reuse a previous build directory.
    destination.mkdir(parents=True, exist_ok=False)
    artifacts = [write_archive(destination / f"dsir-gho-plugin-{version}.zip", plugin),
                 write_archive(destination / f"dsir-gho-skill-{version}.zip", standalone)]
    marketplace_root = destination / "local-marketplace"
    for name, content in plugin.items():
        target = marketplace_root / "plugins/dsir-gho" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    catalog = {
        "name": MARKETPLACE, "interface": {"displayName": "DSIR GHO Local Test"},
        "plugins": [{"name": "dsir-gho", "source": {"source": "local", "path": "./plugins/dsir-gho"},
                     "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                     "category": "Data & Analytics"}],
    }
    catalog_path = marketplace_root / ".agents/plugins/marketplace.json"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_bytes(json_bytes(catalog))
    report = {**metadata, "artifacts": artifacts, "archive_validation": "all_entries_match_build_inputs",
              "local_marketplace": "local-marketplace", "marketplace_name": MARKETPLACE}
    (destination / "build-manifest.json").write_bytes(json_bytes(report))
    (destination / "SHA256SUMS.txt").write_bytes("".join(
        f"{item['sha256']}  {item['file']}\n" for item in artifacts).encode())
    (destination / "TESTING.md").write_bytes(guide)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory; existing outputs are never overwritten")
    parser.add_argument("--version", default=VERSION)
    parser.add_argument("--allow-dirty", action="store_true", help="Development checks only; records dirty source in BUILD.json")
    args = parser.parse_args()
    print(json.dumps(build(args.output_dir, args.version, allow_dirty=args.allow_dirty), indent=2))


if __name__ == "__main__":
    main()
