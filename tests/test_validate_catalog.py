from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_catalog", REPO_ROOT / "scripts/validate_catalog.py"
)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class CatalogValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / "catalog"
        shutil.copytree(
            REPO_ROOT,
            self.root,
            ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"),
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def validate(self) -> list[str]:
        return VALIDATOR.validate_catalog(self.root)

    def manifest(self) -> dict:
        return json.loads((self.root / "catalog/manifest.json").read_text())

    def write_manifest(self, data: dict) -> None:
        (self.root / "catalog/manifest.json").write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )

    def assert_error_contains(self, fragment: str) -> None:
        errors = self.validate()
        self.assertTrue(
            any(fragment in error for error in errors),
            f"expected {fragment!r} in:\n" + "\n".join(errors),
        )

    def test_repository_catalog_is_valid(self) -> None:
        self.assertEqual([], self.validate())

    def test_invalid_json_is_reported(self) -> None:
        (self.root / "integrations/cli/company-gitlab/integration.json").write_text("{")
        self.assert_error_contains("invalid JSON")

    def test_invalid_toml_is_reported(self) -> None:
        (self.root / ".codex/agents/coding.toml").write_text('name = "unterminated')
        self.assert_error_contains("invalid TOML")

    def test_invalid_frontmatter_is_reported(self) -> None:
        path = self.root / ".agents/skills/security-review/SKILL.md"
        path.write_text(path.read_text().replace("name: security-review", "name: wrong-name"))
        self.assert_error_contains("frontmatter name")

    def test_escaping_path_is_reported(self) -> None:
        manifest = self.manifest()
        manifest["agents"][0]["path"] = "../coding.toml"
        self.write_manifest(manifest)
        self.assert_error_contains("path must stay relative")

    def test_agent_name_mismatch_is_reported(self) -> None:
        path = self.root / ".codex/agents/coding.toml"
        path.write_text(path.read_text().replace('name = "coding"', 'name = "other"'))
        self.assert_error_contains("TOML name")

    def test_dangling_dependency_is_reported(self) -> None:
        manifest = self.manifest()
        manifest["skills"][0]["agentDependencies"].append("missing-agent")
        self.write_manifest(manifest)
        self.assert_error_contains("dangling dependency agent:missing-agent")

    def test_dependency_cycle_is_reported(self) -> None:
        manifest = self.manifest()
        manifest["agents"][1]["skillDependencies"].append("security-review")
        self.write_manifest(manifest)
        self.assert_error_contains("dependency cycle")

    def test_embedded_secret_is_reported(self) -> None:
        path = self.root / ".agents/skills/security-review/SKILL.md"
        path.write_text(path.read_text() + "\nExample: glpat-abcdefghijklmnop\n")
        self.assert_error_contains("possible embedded secret")

    def test_skill_resource_is_secret_scanned(self) -> None:
        path = self.root / ".agents/skills/security-review/scripts/helper.txt"
        path.parent.mkdir()
        path.write_text("glpat-abcdefghijklmnop\n")
        self.assert_error_contains("possible embedded secret")

    def test_unknown_entry_field_is_reported(self) -> None:
        manifest = self.manifest()
        manifest["skills"][0]["runtimePath"] = "/tmp/not-owned-here"
        self.write_manifest(manifest)
        self.assert_error_contains("unknown fields")

    def test_skill_symlink_is_rejected(self) -> None:
        outside = self.root.parent / "outside.txt"
        outside.write_text("host-local data\n")
        link = self.root / ".agents/skills/security-review/linked.txt"
        link.symlink_to(outside)
        self.assert_error_contains("must not contain symlinks")


if __name__ == "__main__":
    unittest.main()
