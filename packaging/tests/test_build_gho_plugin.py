"""Regression checks for source-based, non-mutating GHO test packaging."""
import importlib.util
import json
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("gho_builder", Path(__file__).resolve().parents[1] / "build_gho_plugin.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "repo"
        self.output = self.base / "build"
        identity = {"name": "dsir-gho", "version": "0.1.3", "description": "test", "author": {"name": "test"},
                    "license": "MIT", "keywords": ["WHO"]}
        interface = {"displayName": "GHO", "longDescription": "legacy default"}
        files = {
            "dsir-gho/SKILL.md": b"current skill", "dsir-gho/LICENSE": b"MIT",
            "dsir-gho/scripts/cli.py": b"current repaired client",
            "dsir-gho/scripts/gho_client.py": b"legacy default", "dsir-gho/scripts/xmart.py": b"explicit xmart",
            "dsir-gho/agents/openai.yaml": b"current agent", "dsir-gho/references/output_schema.md": b"schema",
            "dsir-gho/packaging/install.ps1": b"safe installer", "dsir-gho/packaging/install.sh": b"safe installer",
            "plugins/dsir-gho/plugin.json": builder.json_bytes({**identity, "extensions": {"com.openai": {"interface": interface}}}),
            "plugins/dsir-gho/.codex-plugin/plugin.json": builder.json_bytes({**identity, "skills": "./skills/", "interface": interface}),
            "plugins/dsir-gho/assets/dsir-logo.jpg": b"logo", "plugins/dsir-gho/README.md": b"readme",
            "plugins/dsir-gho/skills/dsir-gho/scripts/cli.py": b"STALE EMBEDDED COPY",
            "packaging/GHO_TESTING.md": b"guide", "dist/dsir-gho-0.1.1.zip": b"STALE INVALID ZIP",
            "dsir-gho/tests/fixture.json": b"observations", "dsir-gho/reports/raw.json": b"observations",
            "dsir-gho/scripts/__pycache__/cli.pyc": b"cache", "dsir-gho/scripts/.env": b"not a runtime input",
        }
        for name, content in files.items():
            self.write(name, content)
        self.state = {"commit": "a" * 40, "dirty": False, "tracked": set(files)}
        self.addCleanup(patch.stopall)
        patch.object(builder, "repository_state", return_value=self.state).start()

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def build(self, **kwargs):
        return builder.build(self.output, root=self.root, **kwargs)

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_current_source_wins_and_source_is_unchanged(self):
        before = self.snapshot()
        report = self.build()
        self.assertEqual(before, self.snapshot())
        self.assertFalse(report["source_dirty"])
        with zipfile.ZipFile(self.output / report["artifacts"][0]["file"]) as archive:
            self.assertEqual(archive.read("dsir-gho/skills/dsir-gho/scripts/cli.py"), b"current repaired client")
            self.assertFalse(any("STALE" in archive.read(name).decode(errors="replace") for name in archive.namelist()))

    def test_standalone_and_marketplace_match_plugin(self):
        report = self.build()
        with zipfile.ZipFile(self.output / report["artifacts"][0]["file"]) as plugin, zipfile.ZipFile(self.output / report["artifacts"][1]["file"]) as skill:
            for name, digest in report["runtime_files"].items():
                content = plugin.read("dsir-gho/skills/dsir-gho/" + name)
                self.assertEqual(builder.sha256(content), digest)
                self.assertEqual(content, skill.read("dsir-gho/" + name))
            for name in plugin.namelist():
                self.assertEqual(plugin.read(name), (self.output / "local-marketplace/plugins" / name).read_bytes())
            portable = json.loads(plugin.read("dsir-gho/plugin.json"))
            compat = json.loads(plugin.read("dsir-gho/.codex-plugin/plugin.json"))
            self.assertEqual(portable["version"], builder.VERSION)
            self.assertEqual(compat["version"], builder.VERSION)
            self.assertEqual(portable["extensions"]["com.openai"]["interface"], compat["interface"])
            self.assertEqual(compat["interface"]["displayName"], "DSIR GHO Local Test")
        catalog = json.loads((self.output / "local-marketplace/.agents/plugins/marketplace.json").read_bytes())
        self.assertEqual(catalog["name"], builder.MARKETPLACE)
        self.assertEqual(catalog["plugins"][0]["source"]["path"], "./plugins/dsir-gho")

    def test_excludes_untracked_files_caches_and_evidence(self):
        self.write("dsir-gho/references/private-draft.md", b"untracked")
        report = self.build()
        for item in report["artifacts"]:
            with zipfile.ZipFile(self.output / item["file"]) as archive:
                for name in archive.namelist():
                    self.assertFalse(any(part in name for part in ("private-draft", "__pycache__", ".env", "tests/", "reports/", "evals/")))

    def test_repeat_builds_have_identical_archive_hashes(self):
        first = self.build()
        second = builder.build(self.base / "second", root=self.root)
        self.assertEqual(first["artifacts"], second["artifacts"])

    def test_refuses_existing_destination_without_overwrite(self):
        self.output.mkdir()
        sentinel = self.output / "keep.txt"
        sentinel.write_bytes(b"keep")
        with self.assertRaises(FileExistsError):
            self.build()
        self.assertEqual(sentinel.read_bytes(), b"keep")
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_refuses_output_in_source_or_repository_ancestor(self):
        for target in (self.root, self.root / "plugins/new-build", self.base):
            with self.subTest(target=target), self.assertRaises(ValueError):
                builder.build(target, root=self.root)

    def test_dirty_source_requires_explicit_development_option(self):
        self.state["dirty"] = True
        with self.assertRaisesRegex(ValueError, "Commit or review"):
            self.build()
        self.assertFalse(self.output.exists())
        self.assertTrue(self.build(allow_dirty=True)["source_dirty"])

    def test_missing_required_source_fails_before_creating_output(self):
        self.state["tracked"].remove("dsir-gho/scripts/gho_client.py")
        with self.assertRaisesRegex(ValueError, "Required runtime"):
            self.build()
        self.assertFalse(self.output.exists())

    def test_manifest_disagreement_fails_before_creating_output(self):
        path = self.root / "plugins/dsir-gho/.codex-plugin/plugin.json"
        manifest = json.loads(path.read_bytes())
        manifest["version"] = "unexpected"
        path.write_bytes(builder.json_bytes(manifest))
        with self.assertRaisesRegex(ValueError, "manifests disagree"):
            self.build()
        self.assertFalse(self.output.exists())

    def test_only_local_test_versions_are_accepted(self):
        for version in ("0.1.4", "../escape", "0.1.4-test.1/extra"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                self.build(version=version)
        self.assertFalse(self.output.exists())

    def test_archive_validator_rejects_modified_duplicate_and_unsafe_entries(self):
        for index, entries in enumerate(([("dsir-gho/a", b"wrong")],
                                         [("dsir-gho/a", b"a"), ("dsir-gho/a", b"a")],
                                         [("dsir-gho/../a", b"a")])):
            path = self.base / f"invalid-{index}.zip"
            with warnings.catch_warnings(), zipfile.ZipFile(path, "w") as archive:
                warnings.simplefilter("ignore", UserWarning)
                for name, content in entries:
                    archive.writestr(name, content)
            with self.subTest(index=index), self.assertRaises(ValueError):
                builder.validate_archive(path, {"../a" if index == 2 else "a": b"a"})


if __name__ == "__main__":
    unittest.main()
