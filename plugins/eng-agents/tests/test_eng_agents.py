import importlib.util
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile
import time
import unittest
from unittest import mock

MODULE = pathlib.Path(__file__).parents[1] / "scripts" / "eng_agents.py"
spec = importlib.util.spec_from_file_location("eng_agents", MODULE)
eng = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eng)


class EngAgentsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.catalog = self.root / "catalog-source"
        (self.catalog / "agents").mkdir(parents=True)
        (self.catalog / "agents/skills/poll").mkdir(parents=True)
        (self.catalog / "integrations/cli/tool").mkdir(parents=True)
        (self.catalog / "catalog").mkdir()
        (self.catalog / "agents/worker.toml").write_text('name="worker"\n')
        (self.catalog / "agents/skills/poll/SKILL.md").write_text("---\nname: poll\ndescription: test\n---\n# Poll\n")
        (self.catalog / "integrations/cli/tool/integration.json").write_text(json.dumps({"id": "tool", "kind": "cli", "executable": "python3", "healthCheck": {"arguments": ["--version"]}}) + "\n")
        self.manifest_data = {
            "apiVersion": eng.API_VERSION,
            "catalogVersion": "1.0.0",
            "compatibility": {"plugin": ">=1.0.0 <2.0.0"},
            "agents": [{"id": "worker", "path": "agents/worker.toml", "owner": "team", "skillDependencies": [], "integrationDependencies": ["tool"]}],
            "skills": [{"id": "poll", "path": "agents/skills/poll", "owner": "team", "kind": "dispatcher", "agentDependencies": ["worker"], "skillDependencies": [], "integrationDependencies": ["tool"]}],
            "integrations": [{"id": "tool", "path": "integrations/cli/tool", "owner": "team", "kind": "cli"}],
            "entrypoints": {"scheduledPoll": {"skill": "poll"}},
        }
        (self.catalog / "catalog/manifest.json").write_text(json.dumps(self.manifest_data))

    def tearDown(self): self.tmp.cleanup()

    def bindings(self, project):
        return {"apiVersion": eng.API_VERSION, "kind": "Bindings", "projects": [{"id": "repo", "provider": "github", "remote": "o/r", "path": str(project), "enabled": True}], "routing": [{"agents": ["worker"], "entrypoint": "scheduledPoll"}], "credentials": {}, "automation": {"enabled": True, "intervalMinutes": 15, "entrypoint": "scheduledPoll"}}

    def test_catalog_validation_and_bad_dependency(self):
        manifest = eng.validate_catalog(self.catalog)
        self.assertEqual(manifest["_entrypoints"]["scheduledPoll"], "poll")
        self.manifest_data["agents"][0]["skillDependencies"] = ["missing"]
        (self.catalog / "catalog/manifest.json").write_text(json.dumps(self.manifest_data))
        with self.assertRaises(eng.ControlPlaneError): eng.validate_catalog(self.catalog)

    def test_materialize_lock_schedule_and_doctor(self):
        manifest = eng.validate_catalog(self.catalog)
        digest = eng.catalog_digest(self.catalog, manifest)
        runtime = self.root / "runtime"
        lock = {"source": str(self.catalog), "requestedRef": "main", "commit": "abc123", "digest": digest, "materializedFrom": str(self.catalog)}
        eng.materialize_runtime(runtime, self.catalog, lock, manifest)
        project = self.root / "repo"; project.mkdir()
        subprocess.run(["git", "init", "-q", str(project)], check=True)
        subprocess.run(["git", "-C", str(project), "remote", "add", "origin", "https://github.com/o/r.git"], check=True)
        eng.atomic_json(runtime / ".eng-agents/bindings.json", self.bindings(project))
        self.assertTrue((runtime / ".codex/agents/worker.toml").is_file())
        self.assertTrue((runtime / ".agents/skills/poll/SKILL.md").is_file())
        _, loaded_manifest, bindings = eng.load_runtime(runtime)
        intent = eng.build_schedule_intent(runtime, bindings, loaded_manifest)
        self.assertEqual(intent["spec"]["entrypoint"]["skill"], "poll")
        self.assertNotIn("model", json.dumps(intent))
        self.assertEqual(intent["spec"]["execution"]["projectPaths"], [str(runtime.resolve()), str(project.resolve())])
        self.assertTrue(eng.doctor(runtime)["ok"])
        self.assertTrue(eng.doctor(runtime, deep=True)["ok"])
        helper = runtime / ".eng-agents/runtime_state.py"
        first = subprocess.run(["python3", str(helper), "claim-acquire", "--issue", "o/r#1", "--owner", "run-a"], text=True, capture_output=True)
        first_token = json.loads(first.stdout)["token"]
        renewed = subprocess.run(["python3", str(helper), "claim-renew", "--issue", "o/r#1", "--owner", "run-a", "--token", first_token], text=True, capture_output=True)
        second = subprocess.run(["python3", str(helper), "claim-acquire", "--issue", "o/r#1", "--owner", "run-b"], text=True, capture_output=True)
        released = subprocess.run(["python3", str(helper), "claim-release", "--issue", "o/r#1", "--owner", "run-a", "--token", first_token], text=True, capture_output=True)
        self.assertEqual((first.returncode, renewed.returncode, second.returncode, released.returncode), (0, 0, 3, 0))
        crash_key = "o/r#crash@v1"
        corrupt = runtime / ".eng-agents/state/claims" / hashlib.sha256(crash_key.encode()).hexdigest()
        corrupt.mkdir(); old = time.time() - 10; os.utime(corrupt, (old, old))
        recovered = subprocess.run(["python3", str(helper), "claim-acquire", "--issue", crash_key, "--owner", "run-a"], text=True, capture_output=True)
        self.assertEqual(recovered.returncode, 0)
        fenced_issue = "o/r#fenced@v1"
        owner_a = subprocess.run(["python3", str(helper), "claim-acquire", "--issue", fenced_issue, "--owner", "run-a", "--ttl", "1"], check=True, text=True, capture_output=True)
        owner_a_token = json.loads(owner_a.stdout)["token"]
        time.sleep(2)
        owner_b = subprocess.run(["python3", str(helper), "claim-acquire", "--issue", fenced_issue, "--owner", "run-b"], check=True, text=True, capture_output=True)
        owner_b_token = json.loads(owner_b.stdout)["token"]
        stale_complete = subprocess.run(["python3", str(helper), "claim-complete", "--issue", fenced_issue, "--owner", "run-a", "--token", owner_a_token], text=True, capture_output=True)
        competing = subprocess.run(["python3", str(helper), "claim-acquire", "--issue", fenced_issue, "--owner", "run-c"], text=True, capture_output=True)
        self.assertEqual((stale_complete.returncode, competing.returncode), (3, 3))
        subprocess.run(["python3", str(helper), "claim-release", "--issue", fenced_issue, "--owner", "run-b", "--token", owner_b_token], check=True, capture_output=True)
        v1_acquire = subprocess.run(["python3", str(helper), "claim-acquire", "--issue", "o/r#2@v1", "--owner", "run-a"], check=True, text=True, capture_output=True)
        v1_token = json.loads(v1_acquire.stdout)["token"]
        subprocess.run(["python3", str(helper), "claim-complete", "--issue", "o/r#2@v1", "--owner", "run-a", "--token", v1_token], check=True, capture_output=True)
        completed_again = subprocess.run(["python3", str(helper), "claim-acquire", "--issue", "o/r#2@v1", "--owner", "run-b"], text=True, capture_output=True)
        new_revision = subprocess.run(["python3", str(helper), "claim-acquire", "--issue", "o/r#2@v2", "--owner", "run-b"], text=True, capture_output=True)
        self.assertEqual((completed_again.returncode, new_revision.returncode), (3, 0))
        helper_source = helper.read_text()
        helper.write_text(helper_source + "\n# tampered\n")
        self.assertFalse(eng.doctor(runtime)["ok"])
        helper.write_text(helper_source)
        (runtime / ".codex/agents/worker.toml").write_text('name="changed"\n')
        self.assertFalse(eng.doctor(runtime)["ok"])

    def test_rejects_cycle_duplicate_dependency_and_incompatible_catalog(self):
        self.manifest_data["agents"][0]["skillDependencies"] = ["poll"]
        (self.catalog / "catalog/manifest.json").write_text(json.dumps(self.manifest_data))
        with self.assertRaises(eng.ControlPlaneError): eng.validate_catalog(self.catalog)
        self.manifest_data["agents"][0]["skillDependencies"] = []
        self.manifest_data["skills"][0]["integrationDependencies"] = ["tool", "tool"]
        (self.catalog / "catalog/manifest.json").write_text(json.dumps(self.manifest_data))
        with self.assertRaises(eng.ControlPlaneError): eng.validate_catalog(self.catalog)
        self.manifest_data["skills"][0]["integrationDependencies"] = ["tool"]
        self.manifest_data["compatibility"]["plugin"] = ">=99.0.0"
        (self.catalog / "catalog/manifest.json").write_text(json.dumps(self.manifest_data))
        with self.assertRaises(eng.ControlPlaneError): eng.validate_catalog(self.catalog)

    def test_rejects_catalog_version_path_injection(self):
        self.manifest_data["catalogVersion"] = "/tmp/escaped-generation"
        (self.catalog / "catalog/manifest.json").write_text(json.dumps(self.manifest_data))
        with self.assertRaises(eng.ControlPlaneError): eng.validate_catalog(self.catalog)

    def test_schedule_rejects_missing_checkout(self):
        manifest = eng.validate_catalog(self.catalog)
        bindings = self.bindings(self.root / "missing")
        with self.assertRaises(eng.ControlPlaneError):
            eng.build_schedule_intent(self.root / "runtime", bindings, manifest)

    def test_rejects_remote_credentials_and_wrong_host(self):
        manifest = eng.validate_catalog(self.catalog)
        project = self.root / "repo"; project.mkdir()
        subprocess.run(["git", "init", "-q", str(project)], check=True)
        subprocess.run(["git", "-C", str(project), "remote", "add", "origin", "https://evil.example/o/r.git"], check=True)
        bindings = self.bindings(project)
        bindings["projects"][0]["remote"] = "https://embedded-user@github.com/o/r.git"
        with self.assertRaises(eng.ControlPlaneError): eng.validate_bindings(bindings, self.root / "runtime", manifest)
        bindings["projects"][0]["remote"] = "https://github.com/o/r.git"
        validated = eng.validate_bindings(bindings, self.root / "runtime", manifest)
        self.assertFalse(eng.project_readiness(validated["projects"][0])[0])
        subprocess.run(["git", "-C", str(project), "remote", "set-url", "origin", "https://github.com/o/r.git"], check=True)
        subdirectory = project / "src"; subdirectory.mkdir()
        validated["projects"][0]["path"] = str(subdirectory)
        self.assertFalse(eng.project_readiness(validated["projects"][0])[0])

    def test_catalog_digest_rejects_nested_symlink(self):
        manifest = eng.validate_catalog(self.catalog)
        outside = self.root / "host-local.txt"; outside.write_text("local data\n")
        (self.catalog / "agents/skills/poll/linked.txt").symlink_to(outside)
        with self.assertRaises(eng.ControlPlaneError): eng.catalog_digest(self.catalog, manifest)

    def test_resolve_rejects_dirty_git_catalog(self):
        subprocess.run(["git", "init", "-q", str(self.catalog)], check=True)
        subprocess.run(["git", "-C", str(self.catalog), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.catalog), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "catalog"], check=True)
        _, lock = eng.resolve_catalog(str(self.catalog), "HEAD", self.root / "cache")
        self.assertRegex(lock["commit"], r"^[0-9a-f]{40}$")
        (self.catalog / "agents/worker.toml").write_text('name="worker"\ndescription="dirty"\n')
        with self.assertRaises(eng.ControlPlaneError): eng.resolve_catalog(str(self.catalog), "HEAD", self.root / "cache")

    def test_rejects_catalog_url_credentials(self):
        with self.assertRaises(eng.ControlPlaneError):
            eng.resolve_catalog("https://embedded-user@example.invalid/catalog.git", "v1.0.0", self.root / "cache")

    def test_filesystem_catalog_cannot_schedule(self):
        runtime = self.root / "runtime"
        manifest = eng.validate_catalog(self.catalog)
        lock = {"source": str(self.catalog), "requestedRef": "dev", "commit": "filesystem", "digest": eng.catalog_digest(self.catalog, manifest), "materializedFrom": str(self.catalog)}
        eng.materialize_runtime(runtime, self.catalog, lock, manifest)
        project = self.root / "repo"; project.mkdir()
        subprocess.run(["git", "init", "-q", str(project)], check=True)
        subprocess.run(["git", "-C", str(project), "remote", "add", "origin", "https://github.com/o/r.git"], check=True)
        eng.atomic_json(runtime / ".eng-agents/bindings.json", self.bindings(project))
        with self.assertRaises(eng.ControlPlaneError): eng.print_schedule(runtime)

    def test_update_keeps_generation_and_rolls_back(self):
        runtime = self.root / "runtime"
        first_manifest = eng.validate_catalog(self.catalog)
        first_lock = {"source": str(self.catalog), "requestedRef": "v1", "commit": "1111111111111", "digest": eng.catalog_digest(self.catalog, first_manifest), "materializedFrom": str(self.catalog)}
        eng.materialize_runtime(runtime, self.catalog, first_lock, first_manifest)
        first_generation = (runtime / ".eng-agents/current").resolve().name
        (self.catalog / "agents/worker.toml").write_text('name="worker"\ndescription="v2"\n')
        second_manifest = eng.validate_catalog(self.catalog)
        second_lock = {"source": str(self.catalog), "requestedRef": "v2", "commit": "2222222222222", "digest": eng.catalog_digest(self.catalog, second_manifest), "materializedFrom": str(self.catalog)}
        eng.materialize_runtime(runtime, self.catalog, second_lock, second_manifest)
        self.assertIn('description="v2"', (runtime / ".codex/agents/worker.toml").read_text())
        self.assertEqual(eng.rollback_runtime(runtime), first_generation)
        self.assertNotIn("description", (runtime / ".codex/agents/worker.toml").read_text())

    def test_failed_update_does_not_switch_current(self):
        runtime = self.root / "runtime"
        first_manifest = eng.validate_catalog(self.catalog)
        first_lock = {"source": str(self.catalog), "requestedRef": "v1", "commit": "1111111111111", "digest": eng.catalog_digest(self.catalog, first_manifest), "materializedFrom": str(self.catalog)}
        eng.materialize_runtime(runtime, self.catalog, first_lock, first_manifest)
        original_current = os.readlink(runtime / ".eng-agents/current")
        (self.catalog / "agents/worker.toml").write_text('name="worker"\ndescription="v2"\n')
        second_manifest = eng.validate_catalog(self.catalog)
        second_lock = {"source": str(self.catalog), "requestedRef": "v2", "commit": "2222222222222", "digest": eng.catalog_digest(self.catalog, second_manifest), "materializedFrom": str(self.catalog)}
        with mock.patch.object(eng, "_managed_link", side_effect=OSError("injected failure")):
            with self.assertRaises(OSError): eng.materialize_runtime(runtime, self.catalog, second_lock, second_manifest)
        self.assertEqual(os.readlink(runtime / ".eng-agents/current"), original_current)
        self.assertNotIn("description", (runtime / ".codex/agents/worker.toml").read_text())

    def test_rejects_path_escape_and_unknown_ui_choice(self):
        self.manifest_data["agents"][0]["path"] = "../outside.toml"
        (self.catalog / "catalog/manifest.json").write_text(json.dumps(self.manifest_data))
        with self.assertRaises(eng.ControlPlaneError): eng.validate_catalog(self.catalog)


if __name__ == "__main__": unittest.main()
