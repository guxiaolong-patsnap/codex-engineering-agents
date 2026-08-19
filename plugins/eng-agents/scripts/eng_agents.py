#!/usr/bin/env python3
"""Engineering Agents Mac setup and lifecycle control plane."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
UI_DIR = PLUGIN_ROOT / "ui" / "setup"
DEFAULT_CATALOG_URL = "https://github.com/guxiaolong-patsnap/codex-engineering-agents.git"
DEFAULT_RUNTIME = pathlib.Path.home() / "Codex" / "engineering-agents" / "projects" / "issue-worker-prod"
API_VERSION = "eng-agents.patsnap.com/v1"
PLUGIN_VERSION = "1.0.0"
NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$")


class ControlPlaneError(RuntimeError):
    pass


def _run(argv: list[str], *, cwd: pathlib.Path | None = None) -> str:
    result = subprocess.run(argv, cwd=cwd, check=True, text=True, capture_output=True)
    return result.stdout.strip()


def _json(path: pathlib.Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ControlPlaneError(f"Cannot read JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ControlPlaneError(f"Expected JSON object: {path}")
    return data


def atomic_json(path: pathlib.Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def atomic_text(path: pathlib.Path, text_value: str, *, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text_value); handle.flush(); os.fsync(handle.fileno())
        if executable: os.chmod(tmp_name, 0o755)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name): os.unlink(tmp_name)


def resolve_runtime(path: str | pathlib.Path) -> pathlib.Path:
    value = pathlib.Path(path).expanduser()
    value.parent.mkdir(parents=True, exist_ok=True)
    return value.parent.resolve() / value.name


def safe_catalog_path(root: pathlib.Path, raw: str, *, kind: str) -> pathlib.Path:
    rel = pathlib.PurePosixPath(raw)
    if not raw or rel.is_absolute() or ".." in rel.parts:
        raise ControlPlaneError(f"Unsafe {kind} path: {raw!r}")
    candidate = root / pathlib.Path(*rel.parts)
    if candidate.is_symlink(): raise ControlPlaneError(f"Catalog {kind} payload must not be a symlink: {raw!r}")
    path = candidate.resolve()
    if root.resolve() != path and root.resolve() not in path.parents:
        raise ControlPlaneError(f"{kind} path escapes catalog: {raw!r}")
    return path


def _entry_id(entry: dict[str, Any], kind: str) -> str:
    value = entry.get("id") or entry.get("name")
    if not isinstance(value, str) or not NAME_RE.fullmatch(value):
        raise ControlPlaneError(f"Invalid {kind} id: {value!r}")
    return value


def _string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ControlPlaneError(f"{field} must be an array of ids")
    if len(value) != len(set(value)):
        raise ControlPlaneError(f"{field} contains duplicate ids")
    return value


def _exact_fields(entry: dict[str, Any], required: set[str], field: str) -> None:
    missing, extra = sorted(required - entry.keys()), sorted(entry.keys() - required)
    if missing:
        raise ControlPlaneError(f"{field} is missing fields: {', '.join(missing)}")
    if extra:
        raise ControlPlaneError(f"{field} has unknown fields: {', '.join(extra)}")


def _plugin_compatible(expression: Any) -> bool:
    if not isinstance(expression, str) or not expression.strip():
        return False
    tokens = expression.split()
    if not tokens or any(not re.fullmatch(r"(?:>=|<=|>|<|=)?\d+\.\d+\.\d+", token) for token in tokens):
        return False
    current = tuple(int(part) for part in PLUGIN_VERSION.split("."))
    matched = False
    for operator, raw in re.findall(r"(>=|<=|>|<|=)?\s*(\d+\.\d+\.\d+)", expression):
        matched = True
        wanted = tuple(int(part) for part in raw.split("."))
        if operator == ">=" and not current >= wanted: return False
        if operator == "<=" and not current <= wanted: return False
        if operator == ">" and not current > wanted: return False
        if operator == "<" and not current < wanted: return False
        if operator in ("", "=") and current != wanted: return False
    return matched


def _check_dependency_cycles(graph: dict[str, list[str]]) -> None:
    state: dict[str, int] = {}
    stack: list[str] = []
    def visit(node: str) -> None:
        if state.get(node) == 2: return
        if state.get(node) == 1:
            start = stack.index(node)
            raise ControlPlaneError("Dependency cycle: " + " -> ".join(stack[start:] + [node]))
        state[node] = 1; stack.append(node)
        for dependency in graph.get(node, []): visit(dependency)
        stack.pop(); state[node] = 2
    for node in sorted(graph): visit(node)


def validate_catalog(root: pathlib.Path) -> dict[str, Any]:
    root = root.resolve()
    manifest = _json(root / "catalog" / "manifest.json")
    allowed_manifest_fields = {"$schema", "apiVersion", "catalogVersion", "compatibility", "agents", "skills", "integrations", "entrypoints"}
    missing_manifest_fields = allowed_manifest_fields - {"$schema"} - manifest.keys()
    extra_manifest_fields = manifest.keys() - allowed_manifest_fields
    if missing_manifest_fields or extra_manifest_fields:
        raise ControlPlaneError(
            f"Invalid manifest fields; missing={sorted(missing_manifest_fields)}, extra={sorted(extra_manifest_fields)}"
        )
    if manifest.get("apiVersion") not in (API_VERSION, "v1"):
        raise ControlPlaneError("catalog apiVersion must be eng-agents.patsnap.com/v1")
    if not isinstance(manifest.get("catalogVersion"), str) or not SEMVER_RE.fullmatch(manifest["catalogVersion"]):
        raise ControlPlaneError("catalogVersion must be semantic version syntax")
    compatibility = manifest.get("compatibility")
    if not isinstance(compatibility, dict) or set(compatibility) != {"plugin"}:
        raise ControlPlaneError("compatibility must contain exactly plugin")
    if not _plugin_compatible(compatibility.get("plugin")):
        raise ControlPlaneError(f"Catalog is incompatible with eng-agents {PLUGIN_VERSION}")

    collections: dict[str, dict[str, dict[str, Any]]] = {}
    expected_fields = {
        "agents": {"id", "path", "owner", "skillDependencies", "integrationDependencies"},
        "skills": {"id", "path", "owner", "kind", "agentDependencies", "skillDependencies", "integrationDependencies"},
        "integrations": {"id", "path", "owner", "kind"},
    }
    global_ids: set[str] = set()
    for plural in ("agents", "skills", "integrations"):
        entries = manifest.get(plural, [])
        if not isinstance(entries, list):
            raise ControlPlaneError(f"{plural} must be an array")
        by_id: dict[str, dict[str, Any]] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                raise ControlPlaneError(f"{plural} entries must be objects")
            item_id = _entry_id(entry, plural[:-1])
            _exact_fields(entry, expected_fields[plural], f"{plural}.{item_id}")
            if item_id in by_id:
                raise ControlPlaneError(f"Duplicate {plural[:-1]} id: {item_id}")
            if item_id in global_ids:
                raise ControlPlaneError(f"Catalog id is not globally unique: {item_id}")
            global_ids.add(item_id)
            owner = entry.get("owner")
            if owner is not None and (not isinstance(owner, str) or not owner.strip()):
                raise ControlPlaneError(f"Invalid owner for {item_id}")
            raw_path = entry.get("path")
            if not isinstance(raw_path, str):
                raise ControlPlaneError(f"Missing path for {plural[:-1]} {item_id}")
            path = safe_catalog_path(root, raw_path, kind=plural[:-1])
            if plural == "agents":
                rel = pathlib.PurePosixPath(raw_path)
                if rel.parent != pathlib.PurePosixPath(".codex/agents") or rel.suffix != ".toml" or rel.stem != item_id or not path.is_file():
                    raise ControlPlaneError(f"Agent {item_id} must be a .codex/agents/*.toml file")
                name_match = re.search(r'(?m)^name\s*=\s*"([^"]+)"\s*$', path.read_text(encoding="utf-8"))
                if not name_match or name_match.group(1) != item_id:
                    raise ControlPlaneError(f"Agent {item_id} TOML name does not match")
            elif plural == "skills":
                rel = pathlib.PurePosixPath(raw_path)
                skill_file = path / "SKILL.md"
                if rel != pathlib.PurePosixPath(f".agents/skills/{item_id}") or not path.is_dir() or not skill_file.is_file():
                    raise ControlPlaneError(f"Skill {item_id} path must be .agents/skills/{item_id}")
                header = skill_file.read_text(encoding="utf-8")[:4096]
                match = re.search(r"(?m)^name:\s*([^\s]+)\s*$", header)
                if not match or match.group(1) != item_id:
                    raise ControlPlaneError(f"Skill {item_id} frontmatter name does not match")
                if entry.get("kind") not in (None, "dispatcher", "specialist"):
                    raise ControlPlaneError(f"Skill {item_id} kind must be dispatcher or specialist")
            elif not path.exists():
                raise ControlPlaneError(f"Integration path does not exist: {raw_path}")
            if plural == "integrations":
                if entry.get("kind") not in ("cli", "mcp"):
                    raise ControlPlaneError(f"Integration {item_id} kind must be cli or mcp")
                declaration_path = path / "integration.json" if path.is_dir() else path
                declaration = _json(declaration_path)
                if declaration.get("id") != item_id or declaration.get("kind") != entry.get("kind"):
                    raise ControlPlaneError(f"Integration {item_id} id/kind does not match its declaration")
            by_id[item_id] = entry
        collections[plural] = by_id

    dep_fields = {"skillDependencies": "skills", "agentDependencies": "agents", "integrationDependencies": "integrations"}
    graph: dict[str, list[str]] = {}
    for plural in collections:
        for item_id, entry in collections[plural].items():
            deps = entry.get("dependencies") or {}
            if not isinstance(deps, dict):
                raise ControlPlaneError(f"dependencies for {item_id} must be an object")
            merged = {
                "skillDependencies": entry.get("skillDependencies", deps.get("skills")),
                "agentDependencies": entry.get("agentDependencies", deps.get("agents")),
                "integrationDependencies": entry.get("integrationDependencies", deps.get("integrations")),
            }
            for field, target in dep_fields.items():
                for ref in _string_list(merged[field], f"{item_id}.{field}"):
                    if ref not in collections[target]:
                        raise ControlPlaneError(f"Unknown {target[:-1]} dependency {ref!r} in {item_id}")
            prefix = plural[:-1]
            graph[f"{prefix}:{item_id}"] = (
                [f"skill:{x}" for x in _string_list(merged["skillDependencies"], f"{item_id}.skillDependencies")]
                + [f"agent:{x}" for x in _string_list(merged["agentDependencies"], f"{item_id}.agentDependencies")]
                + [f"integration:{x}" for x in _string_list(merged["integrationDependencies"], f"{item_id}.integrationDependencies")]
            )
    _check_dependency_cycles(graph)

    entrypoints = manifest.get("entrypoints", {})
    if not isinstance(entrypoints, dict) or not entrypoints:
        raise ControlPlaneError("entrypoints must be a non-empty object")
    normalized: dict[str, str] = {}
    for name, spec in entrypoints.items():
        skill = spec if isinstance(spec, str) else spec.get("skill") if isinstance(spec, dict) else None
        if not isinstance(name, str) or not NAME_RE.fullmatch(name.replace("_", "-").lower()) or not isinstance(skill, str) or skill not in collections["skills"]:
            raise ControlPlaneError(f"Entrypoint {name!r} references unknown skill {skill!r}")
        normalized[name] = skill

    result = dict(manifest)
    result.update({"_catalogRoot": str(root), "_agentsById": collections["agents"], "_skillsById": collections["skills"], "_integrationsById": collections["integrations"], "_entrypoints": normalized})
    return result


def catalog_digest(root: pathlib.Path, manifest: dict[str, Any]) -> str:
    root = root.resolve()
    digest = hashlib.sha256()
    files: dict[str, pathlib.Path] = {"catalog/manifest.json": root / "catalog" / "manifest.json"}
    for plural in ("agents", "skills", "integrations"):
        for entry in manifest.get(plural, []):
            path = safe_catalog_path(root, entry["path"], kind=plural[:-1])
            logical = pathlib.PurePosixPath(entry["path"])
            if path.is_dir():
                for child in path.rglob("*"):
                    if child.is_symlink(): raise ControlPlaneError(f"Catalog payload must not contain symlinks: {child}")
                    if child.is_file(): files[(logical / child.relative_to(path).as_posix()).as_posix()] = child
            else:
                if path.is_symlink(): raise ControlPlaneError(f"Catalog payload must not contain symlinks: {path}")
                files[logical.as_posix()] = path
    for logical, path in sorted(files.items()):
        digest.update(logical.encode() + b"\0" + path.read_bytes() + b"\0")
    return "sha256:" + digest.hexdigest()


def verify_git_catalog(root: pathlib.Path, commit: str, manifest: dict[str, Any]) -> None:
    try:
        actual = _run(["git", "-C", str(root), "rev-parse", "HEAD"])
        status = _run(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all", "--ignored=matching"])
        tracked = set(_run(["git", "-C", str(root), "ls-files"]).splitlines())
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise ControlPlaneError(f"Catalog Git verification failed: {exc}") from exc
    if actual != commit: raise ControlPlaneError(f"Catalog checkout HEAD {actual} does not match resolved commit {commit}")
    if status: raise ControlPlaneError("Catalog checkout is dirty or contains untracked/ignored files; refusing mutable supply-chain input")
    required = {"catalog/manifest.json"}
    for plural in ("agents", "skills", "integrations"):
        for entry in manifest[plural]:
            logical = pathlib.PurePosixPath(entry["path"])
            path = safe_catalog_path(root, entry["path"], kind=plural[:-1])
            if path.is_dir():
                required.update((logical / child.relative_to(path).as_posix()).as_posix() for child in path.rglob("*") if child.is_file())
            else: required.add(logical.as_posix())
    missing = sorted(required - tracked)
    if missing: raise ControlPlaneError(f"Catalog payload contains files not tracked by commit {commit}: {missing}")


def resolve_catalog(source: str, ref: str, cache_root: pathlib.Path, *, allow_filesystem: bool = False) -> tuple[pathlib.Path, dict[str, Any]]:
    local = pathlib.Path(source).expanduser()
    if local.exists():
        root = local.resolve()
        try:
            commit = _run(["git", "-C", str(root), "rev-parse", "HEAD"])
        except (subprocess.CalledProcessError, FileNotFoundError):
            commit = "filesystem"
        manifest = validate_catalog(root)
        if commit != "filesystem": verify_git_catalog(root, commit, manifest)
        elif not allow_filesystem: raise ControlPlaneError("Non-Git catalog sources require explicit --allow-filesystem-catalog for local development")
        return root, {"source": str(root), "requestedRef": ref, "commit": commit, "digest": catalog_digest(root, manifest)}

    if "://" in source:
        parsed_source = urlparse(source)
        if parsed_source.query or parsed_source.fragment or (
            parsed_source.scheme in ("http", "https") and (parsed_source.username or parsed_source.password)
        ):
            raise ControlPlaneError("Catalog source must not contain credentials, query, or fragment; use SSH or a Git credential helper")

    source_key = hashlib.sha256(source.encode()).hexdigest()[:20]
    git_dir = cache_root / "sources" / source_key
    git_dir.parent.mkdir(parents=True, exist_ok=True)
    if not git_dir.exists():
        _run(["git", "clone", "--no-checkout", source, str(git_dir)])
    _run(["git", "-C", str(git_dir), "fetch", "--prune", "origin", ref])
    commit = _run(["git", "-C", str(git_dir), "rev-parse", "FETCH_HEAD"])
    checkout = cache_root / "catalogs" / commit
    if not checkout.exists():
        checkout.parent.mkdir(parents=True, exist_ok=True)
        _run(["git", "-C", str(git_dir), "worktree", "add", "--detach", str(checkout), commit])
    manifest = validate_catalog(checkout)
    verify_git_catalog(checkout, commit, manifest)
    return checkout, {"source": source, "requestedRef": ref, "commit": commit, "digest": catalog_digest(checkout, manifest)}


def _copy_declared_assets(catalog: pathlib.Path, staging: pathlib.Path, manifest: dict[str, Any]) -> None:
    agents_dir, skills_dir = staging / ".codex" / "agents", staging / ".agents" / "skills"
    agents_dir.mkdir(parents=True); skills_dir.mkdir(parents=True)
    for entry in manifest["agents"]:
        src = safe_catalog_path(catalog, entry["path"], kind="agent")
        shutil.copy2(src, agents_dir / src.name)
    for entry in manifest["skills"]:
        src = safe_catalog_path(catalog, entry["path"], kind="skill")
        shutil.copytree(src if src.is_dir() else src.parent, skills_dir / _entry_id(entry, "skill"))


def _runtime_agents_md(lock: dict[str, Any]) -> str:
    return f"""# Generated Engineering Agents runtime project

This directory is generated and managed by the `eng-agents` plugin.

- Catalog commit: `{lock['commit']}`
- Catalog digest: `{lock['digest']}`
- Runtime configuration: `.eng-agents/instance.json`
- Repository bindings: `.eng-agents/bindings.json`

Treat `.codex/agents/` and `.agents/skills/` as generated files. Update them
through `$eng-agents-update`; make source changes in the catalog repository.
Operate only on repositories explicitly listed in bindings. Never store
credentials here; bindings contain environment-variable names only.
"""


RUNTIME_STATE_SOURCE = r'''#!/usr/bin/env python3
"""Atomic lease and issue-claim helper generated by eng-agents."""
import argparse, fcntl, hashlib, json, os, pathlib, secrets, shutil, socket, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parent
STATE = ROOT / "state"

def safe_id(value): return hashlib.sha256(value.encode()).hexdigest()
def metadata_path(kind, key): return STATE / ("lease" if kind == "lease" else "claims") / safe_id(key)
def write_json(path, data):
    path.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".metadata.", dir=path)
    with os.fdopen(fd, "w") as handle:
        json.dump(data, handle, sort_keys=True); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
    os.replace(tmp, path / "metadata.json")
def read_json(path):
    try: return json.loads((path / "metadata.json").read_text())
    except Exception: return {}
def synchronized(operation):
    def wrapped(kind, key, *args, **kwargs):
        lock_path = STATE / "locks" / (kind + "-" + safe_id(key) + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try: return operation(kind, key, *args, **kwargs)
            finally: fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return wrapped
@synchronized
def acquire(kind, key, owner, ttl):
    path = metadata_path(kind, key); path.parent.mkdir(parents=True, exist_ok=True); now = int(time.time())
    if kind == "claim" and (STATE / "completed" / (safe_id(key) + ".json")).is_file():
        return {"ok": False, "status": "ALREADY_COMPLETED", "key": key}
    try: path.mkdir()
    except FileExistsError:
        current = read_json(path)
        if not current:
            try: corrupt_age = now - int(path.stat().st_mtime)
            except OSError: return {"ok": False, "status": "BUSY"}
            if corrupt_age < 5: return {"ok": False, "status": "BUSY_RECOVERING", "retryAfter": 5 - corrupt_age}
        elif int(current.get("expiresAt", now + 1)) >= now:
            return {"ok": False, "status": "BUSY", "holder": current.get("owner"), "expiresAt": current.get("expiresAt")}
        stale = path.with_name(path.name + ".stale-" + str(now))
        try: os.replace(path, stale); path.mkdir(); shutil.rmtree(stale, ignore_errors=True)
        except (FileExistsError, FileNotFoundError): return {"ok": False, "status": "BUSY"}
    record = {"kind": kind, "key": key, "owner": owner, "token": secrets.token_hex(16), "acquiredAt": now, "expiresAt": now + ttl}
    write_json(path, record); return {"ok": True, "status": "ACQUIRED", **record}
@synchronized
def renew(kind, key, owner, token, ttl):
    path = metadata_path(kind, key); current = read_json(path); now = int(time.time())
    if not current: return {"ok": False, "status": "ABSENT_OR_CORRUPT"}
    if current.get("owner") != owner or not secrets.compare_digest(str(current.get("token", "")), token): return {"ok": False, "status": "NOT_OWNER", "holder": current.get("owner")}
    if int(current.get("expiresAt", 0)) < now: return {"ok": False, "status": "EXPIRED"}
    current["expiresAt"] = now + ttl; current["renewedAt"] = now; write_json(path, current)
    return {"ok": True, "status": "RENEWED", **current}
@synchronized
def release(kind, key, owner, token, complete=False):
    path = metadata_path(kind, key); current = read_json(path)
    if not path.exists(): return {"ok": True, "status": "ABSENT"}
    if current.get("owner") != owner or not secrets.compare_digest(str(current.get("token", "")), token): return {"ok": False, "status": "NOT_OWNER", "holder": current.get("owner")}
    if complete and kind == "claim":
        completed = STATE / "completed" / (safe_id(key) + ".json")
        completed.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".completed.", dir=completed.parent)
        with os.fdopen(fd, "w") as handle:
            json.dump({**current, "completedAt": int(time.time())}, handle, sort_keys=True); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp, completed)
    shutil.rmtree(path); return {"ok": True, "status": "COMPLETED" if complete else "RELEASED"}
def main():
    parser = argparse.ArgumentParser(); parser.add_argument("action", choices=["lease-acquire","lease-renew","lease-release","claim-acquire","claim-renew","claim-release","claim-complete"])
    parser.add_argument("--issue", default="scheduler"); parser.add_argument("--owner", default=os.environ.get("CODEX_RUN_ID") or f"{socket.gethostname()}:{os.getpid()}"); parser.add_argument("--token", default=""); parser.add_argument("--ttl", type=int, default=7200)
    args = parser.parse_args(); kind = "lease" if args.action.startswith("lease-") else "claim"; key = "scheduler" if kind == "lease" else args.issue
    result = acquire(kind, key, args.owner, args.ttl) if args.action.endswith("acquire") else renew(kind, key, args.owner, args.token, args.ttl) if args.action.endswith("renew") else release(kind, key, args.owner, args.token, args.action == "claim-complete")
    print(json.dumps(result, sort_keys=True)); raise SystemExit(0 if result.get("ok") else 3)
if __name__ == "__main__": main()
'''


def _copy_catalog_payload(catalog: pathlib.Path, staging: pathlib.Path, manifest: dict[str, Any]) -> None:
    _copy_declared_assets(catalog, staging, manifest)
    (staging / "catalog").mkdir(parents=True, exist_ok=True)
    for name in ("manifest.json", "manifest.schema.json"):
        source = catalog / "catalog" / name
        if source.is_file(): shutil.copy2(source, staging / "catalog" / name)
    for entry in manifest["integrations"]:
        source = safe_catalog_path(catalog, entry["path"], kind="integration")
        target = staging / pathlib.Path(*pathlib.PurePosixPath(entry["path"]).parts)
        if source.is_dir(): shutil.copytree(source, target)
        else: target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)


def _managed_link(runtime: pathlib.Path, path: pathlib.Path, target: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() and os.readlink(path) == target: return
    if path.exists() or path.is_symlink():
        legacy = runtime / ".eng-agents" / "legacy" / f"{path.name}-{int(time.time())}-{secrets.token_hex(3)}"
        legacy.parent.mkdir(parents=True, exist_ok=True); shutil.move(str(path), str(legacy))
    temporary = path.with_name(f".{path.name}.eng-agents-{secrets.token_hex(4)}")
    os.symlink(target, temporary); os.replace(temporary, path)


def materialize_runtime(runtime: pathlib.Path, catalog: pathlib.Path, lock: dict[str, Any], manifest: dict[str, Any]) -> None:
    runtime.mkdir(parents=True, exist_ok=True)
    control = runtime / ".eng-agents"
    generations = control / "generations"; generations.mkdir(parents=True, exist_ok=True)
    helper_digest = hashlib.sha256(RUNTIME_STATE_SOURCE.encode()).hexdigest()
    lock_data = {
        "apiVersion": API_VERSION,
        "kind": "CatalogLock",
        "controllerVersion": PLUGIN_VERSION,
        "catalogApiVersion": manifest["apiVersion"],
        "catalogVersion": manifest["catalogVersion"],
        "compatibility": manifest["compatibility"],
        "selected": {
            "agents": sorted(manifest["_agentsById"]),
            "skills": sorted(manifest["_skillsById"]),
            "integrations": sorted(manifest["_integrationsById"]),
            "entrypoints": manifest["_entrypoints"],
        },
        "effectivePolicy": {"model": "inherit-host-policy", "reasoning": "inherit-host-policy"},
        "runtimeStateHelperDigest": "sha256:" + helper_digest,
        **lock,
    }
    generation_id = f"{manifest['catalogVersion']}-{lock['commit'][:12]}-{lock['digest'].split(':', 1)[-1][:12]}-p{PLUGIN_VERSION}-{helper_digest[:8]}"
    generation = generations / generation_id
    if generation.parent != generations or not generation.name or generation.name in (".", ".."):
        raise ControlPlaneError("Resolved generation path escapes the managed generations directory")
    if generation.is_symlink(): raise ControlPlaneError("Managed generation must not be a symlink")
    if not generation.exists():
        staging = pathlib.Path(tempfile.mkdtemp(prefix=".stage-", dir=generations))
        try:
            _copy_catalog_payload(catalog, staging, manifest)
            (staging / ".codex" / "config.toml").write_text("[features]\nmulti_agent_v2 = true\n\n[agents]\nenabled = true\n", encoding="utf-8")
            (staging / "AGENTS.md").write_text(_runtime_agents_md(lock_data), encoding="utf-8")
            atomic_text(staging / "runtime_state.py", RUNTIME_STATE_SOURCE, executable=True)
            atomic_json(staging / "catalog.lock.json", lock_data)
            runtime_manifest = validate_catalog(staging)
            if catalog_digest(staging, runtime_manifest) != lock["digest"]:
                raise ControlPlaneError("Staged runtime digest does not match the resolved catalog")
            os.replace(staging, generation)
        finally:
            if staging.exists(): shutil.rmtree(staging)
    generation_manifest = validate_catalog(generation)
    if catalog_digest(generation, generation_manifest) != lock["digest"]:
        raise ControlPlaneError(f"Generation {generation_id} failed digest verification")
    generation_lock = _json(generation / "catalog.lock.json")
    if generation_lock.get("runtimeStateHelperDigest") != "sha256:" + helper_digest:
        raise ControlPlaneError(f"Generation {generation_id} has an incompatible runtime helper")
    bindings_path = control / "bindings.json"
    if bindings_path.exists():
        existing_bindings = _json(bindings_path)
        if existing_bindings.get("projects"): validate_bindings(existing_bindings, runtime, generation_manifest)
    else:
        atomic_json(bindings_path, {"apiVersion": API_VERSION, "kind": "Bindings", "projects": [], "routing": [], "credentials": {"gitlabTokenEnv": "GITLAB_TOKEN", "githubTokenEnv": "GITHUB_TOKEN"}, "automation": {"enabled": True, "intervalMinutes": 10, "entrypoint": next(iter(manifest["_entrypoints"]))}})
    for rel in ("state/claims", "state/completed", "state/locks", "logs"): (control / rel).mkdir(parents=True, exist_ok=True)
    instance_path = control / "instance.json"
    existing_instance = _json(instance_path) if instance_path.exists() else {}
    instance = {"apiVersion": API_VERSION, "kind": "Instance", "metadata": {"id": existing_instance.get("metadata", {}).get("id", runtime.name)}, "spec": {"runtimePath": str(runtime.resolve()), "controllerVersion": PLUGIN_VERSION}}
    atomic_json(instance_path, instance)
    _managed_link(runtime, runtime / ".codex/agents", "../.eng-agents/current/.codex/agents")
    _managed_link(runtime, runtime / ".codex/config.toml", "../.eng-agents/current/.codex/config.toml")
    _managed_link(runtime, runtime / ".agents/skills", "../.eng-agents/current/.agents/skills")
    _managed_link(runtime, runtime / "catalog", ".eng-agents/current/catalog")
    _managed_link(runtime, runtime / "integrations", ".eng-agents/current/integrations")
    _managed_link(runtime, runtime / "AGENTS.md", ".eng-agents/current/AGENTS.md")
    _managed_link(runtime, control / "catalog.lock.json", "current/catalog.lock.json")
    _managed_link(runtime, control / "runtime_state.py", "current/runtime_state.py")
    current_tmp = control / f".current-{secrets.token_hex(4)}"
    os.symlink(f"generations/{generation_id}", current_tmp); os.replace(current_tmp, control / "current")


def rollback_runtime(runtime: pathlib.Path, requested: str | None = None) -> str:
    control, current = runtime / ".eng-agents", runtime / ".eng-agents/current"
    generations = control / "generations"
    if not current.is_symlink() or not generations.is_dir():
        raise ControlPlaneError("Runtime has no managed generations")
    current_name = pathlib.Path(os.readlink(current)).name
    candidates = sorted((p for p in generations.iterdir() if p.is_dir() and not p.is_symlink() and p.name != current_name), key=lambda p: p.stat().st_mtime, reverse=True)
    target = generations / requested if requested else (candidates[0] if candidates else None)
    if target is None or target.is_symlink() or not target.is_dir() or target.parent != generations:
        raise ControlPlaneError("Requested rollback generation is unavailable")
    lock = _json(target / "catalog.lock.json")
    manifest = validate_catalog(target)
    if catalog_digest(target, manifest) != lock.get("digest"):
        raise ControlPlaneError("Rollback generation failed digest verification")
    if "sha256:" + hashlib.sha256((target / "runtime_state.py").read_bytes()).hexdigest() != lock.get("runtimeStateHelperDigest"):
        raise ControlPlaneError("Rollback generation runtime helper failed digest verification")
    existing_bindings = _json(control / "bindings.json")
    if existing_bindings.get("projects"): validate_bindings(existing_bindings, runtime, manifest)
    temporary = control / f".current-{secrets.token_hex(4)}"
    os.symlink(f"generations/{target.name}", temporary); os.replace(temporary, current)
    return target.name


def catalog_public(manifest: dict[str, Any]) -> dict[str, Any]:
    return {"catalogVersion": manifest["catalogVersion"], "agents": [{"id": _entry_id(x, "agent"), "owner": x.get("owner", "")} for x in manifest["agents"]], "skills": [{"id": _entry_id(x, "skill"), "kind": x.get("kind", "")} for x in manifest["skills"]], "entrypoints": manifest["_entrypoints"]}


def validate_bindings(data: dict[str, Any], runtime: pathlib.Path, manifest: dict[str, Any]) -> dict[str, Any]:
    if data.get("apiVersion") != API_VERSION or data.get("kind") != "Bindings":
        raise ControlPlaneError("Bindings apiVersion/kind is invalid")
    allowed_root = {"apiVersion", "kind", "projects", "routing", "credentials", "automation"}
    if set(data) - allowed_root: raise ControlPlaneError(f"Unknown Bindings fields: {sorted(set(data) - allowed_root)}")
    projects = data.get("projects")
    if not isinstance(projects, list) or not projects:
        raise ControlPlaneError("Add at least one Git repository")
    project_ids: set[str] = set()
    for project in projects:
        if not isinstance(project, dict): raise ControlPlaneError("Project entries must be objects")
        allowed_project = {"id", "provider", "remote", "path", "defaultBranch", "enabled"}
        if set(project) - allowed_project: raise ControlPlaneError(f"Unknown project fields: {sorted(set(project) - allowed_project)}")
        item_id = project.get("id")
        if not isinstance(item_id, str) or not NAME_RE.fullmatch(item_id) or item_id in project_ids: raise ControlPlaneError(f"Invalid or duplicate project id: {item_id!r}")
        project_ids.add(item_id)
        if project.get("provider") not in ("gitlab", "github"): raise ControlPlaneError(f"Invalid provider for {item_id}")
        if not isinstance(project.get("remote"), str) or not project["remote"].strip(): raise ControlPlaneError(f"Missing remote for {item_id}")
        if "://" in project["remote"]:
            parsed_remote = urlparse(project["remote"])
            if parsed_remote.query or parsed_remote.fragment or (
                parsed_remote.scheme in ("http", "https") and (parsed_remote.username or parsed_remote.password)
            ):
                raise ControlPlaneError(f"Remote for {item_id} must not contain credentials, query, or fragment")
        if not isinstance(project.get("enabled", True), bool): raise ControlPlaneError(f"enabled must be boolean for {item_id}")
        if project.get("defaultBranch") is not None and not isinstance(project["defaultBranch"], str): raise ControlPlaneError(f"defaultBranch must be a string for {item_id}")
        if not project.get("path"):
            raise ControlPlaneError(f"Project {item_id} requires a local checkout path")
        if project.get("path"):
            path = pathlib.Path(project["path"]).expanduser()
            if not path.is_absolute(): raise ControlPlaneError(f"Project path must be absolute: {project['path']}")
            project["path"] = str(path.resolve())
    agent_ids, entrypoints = set(manifest["_agentsById"]), set(manifest["_entrypoints"])
    routing = data.get("routing", [])
    if not isinstance(routing, list): raise ControlPlaneError("routing must be an array")
    for rule in routing:
        if not isinstance(rule, dict): raise ControlPlaneError("Routing rules must be objects")
        allowed_rule = {"labels", "keywords", "agents", "entrypoint"}
        if set(rule) - allowed_rule: raise ControlPlaneError(f"Unknown routing fields: {sorted(set(rule) - allowed_rule)}")
        _string_list(rule.get("labels"), "routing.labels")
        _string_list(rule.get("keywords"), "routing.keywords")
        for agent in _string_list(rule.get("agents"), "routing.agents"):
            if agent not in agent_ids: raise ControlPlaneError(f"Unknown routing agent: {agent}")
        if rule.get("entrypoint") and rule["entrypoint"] not in entrypoints: raise ControlPlaneError(f"Unknown routing entrypoint: {rule['entrypoint']}")
    automation = data.get("automation", {})
    if not isinstance(automation, dict): raise ControlPlaneError("automation must be an object")
    if set(automation) - {"enabled", "intervalMinutes", "entrypoint", "name"}: raise ControlPlaneError("automation has unknown fields")
    if not isinstance(automation.get("enabled", True), bool): raise ControlPlaneError("automation.enabled must be boolean")
    if automation.get("name") is not None and not isinstance(automation["name"], str): raise ControlPlaneError("automation.name must be a string")
    interval = automation.get("intervalMinutes", 10)
    if not isinstance(interval, int) or isinstance(interval, bool) or not 5 <= interval <= 1440: raise ControlPlaneError("intervalMinutes must be an integer from 5 to 1440")
    selected = automation.get("entrypoint") or next(iter(entrypoints))
    if selected not in entrypoints: raise ControlPlaneError(f"Unknown automation entrypoint: {selected}")
    automation["entrypoint"] = selected
    credentials = data.get("credentials", {})
    if not isinstance(credentials, dict) or set(credentials) - {"gitlabTokenEnv", "githubTokenEnv"}:
        raise ControlPlaneError("credentials may contain only token environment-variable references")
    env_name = re.compile(r"^[A-Z][A-Z0-9_]*$")
    if any(not isinstance(value, str) or not env_name.fullmatch(value) for value in credentials.values()):
        raise ControlPlaneError("credential references must be environment-variable names, never secret values")
    data.update({"projects": projects, "automation": automation})
    return data


def _remote_identity(value: str, provider: str) -> tuple[str, str]:
    cleaned = value.strip().removesuffix(".git")
    if "://" in cleaned:
        parsed = urlparse(cleaned)
        return (parsed.hostname or "").lower(), parsed.path.strip("/")
    if "@" in cleaned and ":" in cleaned:
        authority, path = cleaned.split(":", 1)
        return authority.rsplit("@", 1)[-1].lower(), path.strip("/")
    default_host = "git.patsnap.com" if provider == "gitlab" else "github.com"
    return default_host, cleaned.strip("/")


def project_readiness(project: dict[str, Any], *, write_probe: bool = False) -> tuple[bool, str]:
    raw_path = project.get("path")
    if not raw_path: return False, "local checkout path is missing"
    path = pathlib.Path(raw_path)
    if not path.is_dir(): return False, f"checkout does not exist: {path}"
    try:
        top = pathlib.Path(_run(["git", "-C", str(path), "rev-parse", "--show-toplevel"])).resolve()
        origin = _run(["git", "-C", str(path), "remote", "get-url", "origin"])
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False, f"not a Git checkout with an origin remote: {path}"
    if path.resolve() != top:
        return False, f"configured path must be the Git checkout root: {top}"
    expected, actual = _remote_identity(str(project["remote"]), project["provider"]), _remote_identity(origin, project["provider"])
    if expected != actual:
        return False, f"origin mismatch: expected {expected[0]}/{expected[1]}, got {actual[0]}/{actual[1]}"
    if write_probe:
        try:
            fd, probe = tempfile.mkstemp(prefix=".eng-agents-write-probe-", dir=top)
            os.close(fd); os.unlink(probe)
        except OSError as exc:
            return False, f"checkout is not writable by the scheduled identity: {exc}"
    return True, f"ready: {top} ({actual[0]}/{actual[1]})"


def build_schedule_intent(runtime: pathlib.Path, bindings: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    auto = bindings.get("automation", {})
    entrypoint = auto.get("entrypoint") or next(iter(manifest["_entrypoints"]))
    skill, interval = manifest["_entrypoints"][entrypoint], int(auto.get("intervalMinutes", 10))
    paths = [str(runtime.resolve())]
    for item_id, entry in manifest["_integrationsById"].items():
        declaration_path = safe_catalog_path(runtime, entry["path"], kind="integration")
        declaration = _json(declaration_path / "integration.json" if declaration_path.is_dir() else declaration_path)
        ready, detail = integration_readiness(declaration, deep=False)
        if not ready: raise ControlPlaneError(f"Integration {item_id} is not ready: {detail}")
    for project in bindings["projects"]:
        if project.get("enabled", True):
            ready, detail = project_readiness(project)
            if not ready: raise ControlPlaneError(f"Project {project['id']} is not ready: {detail}")
            resolved = str(pathlib.Path(project["path"]).expanduser().resolve())
            if resolved not in paths: paths.append(resolved)
    instance_path = str((runtime / ".eng-agents/instance.json").resolve())
    helper_path = str((runtime / ".eng-agents/runtime_state.py").resolve())
    prompt = (
        f"Create a unique owner ID for this run. Acquire the scheduler lease with `python3 {helper_path} "
        f"lease-acquire --owner <owner-id>` and retain its returned fencing token; stop with NO_WORK if busy. Then use ${skill} and read runtime "
        f"configuration from `{instance_path}`. Pass the same owner ID and the corresponding `--token` to renew/release/complete commands, renew the lease and active claim before their TTL expires, and always release "
        "the scheduler lease in a finally step. Operate only on the projects attached to this Scheduled Task."
    )
    return {"apiVersion": API_VERSION, "kind": "ScheduleIntent", "metadata": {"id": f"eng-agents-{runtime.name}", "name": auto.get("name") or f"Engineering Agents — {entrypoint}"}, "spec": {"enabled": auto.get("enabled", True), "entrypoint": {"name": entrypoint, "skill": skill}, "prompt": prompt, "schedule": {"intervalMinutes": interval, "rrule": f"RRULE:FREQ=MINUTELY;INTERVAL={interval}"}, "execution": {"environment": "local", "instancePath": instance_path, "runtimeStateHelper": helper_path, "projectPaths": paths}}}


def load_runtime(runtime: pathlib.Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    lock = _json(runtime / ".eng-agents/catalog.lock.json")
    required_lock = {"apiVersion", "kind", "controllerVersion", "catalogApiVersion", "catalogVersion", "compatibility", "selected", "effectivePolicy", "runtimeStateHelperDigest", "source", "requestedRef", "commit", "digest", "materializedFrom"}
    if lock.get("apiVersion") != API_VERSION or lock.get("kind") != "CatalogLock" or not required_lock <= lock.keys():
        raise ControlPlaneError("catalog.lock.json does not satisfy the v1 runtime contract")
    instance = _json(runtime / ".eng-agents/instance.json")
    spec = instance.get("spec") if isinstance(instance.get("spec"), dict) else {}
    if instance.get("apiVersion") != API_VERSION or instance.get("kind") != "Instance" or spec != {"runtimePath": str(runtime.resolve()), "controllerVersion": PLUGIN_VERSION}:
        raise ControlPlaneError("instance.json does not satisfy the v1 runtime contract")
    manifest = validate_catalog(runtime)
    if catalog_digest(runtime, manifest) != lock.get("digest"):
        raise ControlPlaneError("Materialized runtime digest does not match catalog.lock.json")
    bindings = validate_bindings(_json(runtime / ".eng-agents/bindings.json"), runtime, manifest)
    return lock, manifest, bindings


def _resolve_skill_root(provider: str) -> pathlib.Path | None:
    candidates = [pathlib.Path.home() / ".codex/skills" / provider, pathlib.Path.home() / ".agents/skills" / provider]
    for candidate in candidates:
        if (candidate / "SKILL.md").is_file(): return candidate.resolve()
    cache = pathlib.Path.home() / ".codex/plugins/cache"
    if cache.is_dir():
        for candidate in cache.rglob(provider):
            if candidate.parent.name == "skills" and (candidate / "SKILL.md").is_file(): return candidate.resolve()
    return None


def integration_readiness(declaration: dict[str, Any], *, deep: bool) -> tuple[bool, str]:
    executable = declaration.get("executable")
    if not isinstance(executable, str) or not shutil.which(executable): return False, "declared executable is unavailable"
    provider = declaration.get("provider")
    skill_root = _resolve_skill_root(provider) if isinstance(provider, str) else None
    arguments = declaration.get("arguments", [])
    if not isinstance(arguments, list) or not all(isinstance(item, str) for item in arguments): return False, "arguments must be strings"
    resolved_arguments: list[str] = []
    for argument in arguments:
        match = re.fullmatch(r"\{skill:([^}]+)\}(/.*)?", argument)
        if match:
            if match.group(1) != provider or skill_root is None: return False, f"provider skill is not installed: {match.group(1)}"
            resolved = skill_root / (match.group(2) or "").lstrip("/")
            if not resolved.is_file(): return False, f"provider argument path is missing: {resolved}"
            resolved_arguments.append(str(resolved))
        else: resolved_arguments.append(argument)
    health = declaration.get("healthCheck", {})
    health_arguments = health.get("arguments", []) if isinstance(health, dict) else []
    if not isinstance(health_arguments, list) or not all(isinstance(item, str) for item in health_arguments): return False, "healthCheck.arguments must be strings"
    if deep and health_arguments:
        environment = dict(os.environ); environment.setdefault("GITLAB_SKILL_AUTO_UPDATE", "0")
        try:
            result = subprocess.run([executable, *resolved_arguments, *health_arguments], text=True, capture_output=True, timeout=20, env=environment)
        except (OSError, subprocess.TimeoutExpired) as exc: return False, f"health check failed: {type(exc).__name__}"
        if result.returncode != 0: return False, f"health check exited {result.returncode}"
    return True, "wiring and health check passed" if deep and health_arguments else "wiring resolved"


def doctor(runtime: pathlib.Path, *, deep: bool = False) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    def record(name: str, ok: bool, detail: str) -> None: checks.append({"name": name, "ok": ok, "detail": detail})
    try:
        lock, manifest, bindings = load_runtime(runtime)
        record("runtime-contracts", True, "instance, lock, bindings and catalog are readable")
        actual = catalog_digest(runtime, manifest)
        record("catalog-digest", actual == lock.get("digest"), f"expected {lock.get('digest')}, got {actual}")
        missing_agents = [item for item, entry in manifest["_agentsById"].items() if not (runtime / ".codex/agents" / pathlib.Path(entry["path"]).name).is_file()]
        missing_skills = [item for item in manifest["_skillsById"] if not (runtime / ".agents/skills" / item / "SKILL.md").is_file()]
        record("materialized-assets", not missing_agents and not missing_skills, f"missing agents={missing_agents}, skills={missing_skills}")
        project_failures = []
        for project in bindings["projects"]:
            if project.get("enabled", True):
                ready, detail = project_readiness(project, write_probe=True)
                if not ready: project_failures.append(f"{project['id']}: {detail}")
        record("project-checkouts", not project_failures, "; ".join(project_failures) or "all enabled checkouts match their origin and are writable")
        integration_failures = []
        for item_id, entry in manifest["_integrationsById"].items():
            declaration_path = safe_catalog_path(runtime, entry["path"], kind="integration")
            declaration = _json(declaration_path / "integration.json" if declaration_path.is_dir() else declaration_path)
            ready, detail = integration_readiness(declaration, deep=deep)
            if not ready: integration_failures.append(f"{item_id}: {detail}")
        record("integrations", not integration_failures, "; ".join(integration_failures) or "declared integration executables are available")
        helper = runtime / ".eng-agents/runtime_state.py"
        helper_digest = "sha256:" + hashlib.sha256(helper.read_bytes()).hexdigest() if helper.is_file() else "missing"
        record("runtime-state-helper", helper_digest == lock.get("runtimeStateHelperDigest"), f"expected {lock.get('runtimeStateHelperDigest')}, got {helper_digest}")
        record("schedule-intent", bool(build_schedule_intent(runtime, bindings, manifest)["spec"]["entrypoint"]["skill"]), "selected entrypoint resolves")
    except ControlPlaneError as exc:
        record("runtime-contracts", False, str(exc))
    return {"ok": all(check["ok"] for check in checks), "checks": checks}


class SetupHandler(BaseHTTPRequestHandler):
    runtime: pathlib.Path
    manifest: dict[str, Any]
    csrf_token: str
    allowed_origin: str
    allowed_host: str
    csrf_used = False
    csrf_lock = threading.Lock()

    def log_message(self, fmt: str, *args: Any) -> None: sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))
    def _send_json(self, code: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store"); self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'"); self.end_headers(); self.wfile.write(body)
    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 0 or length > 1024 * 1024: raise ControlPlaneError("Request body is too large")
        try: value = json.loads(self.rfile.read(length) if length else b"{}")
        except json.JSONDecodeError as exc: raise ControlPlaneError("Invalid JSON body") from exc
        if not isinstance(value, dict): raise ControlPlaneError("JSON body must be an object")
        return value
    def do_GET(self) -> None:
        if self.headers.get("Host") != self.allowed_host:
            self._send_json(403, {"ok": False, "error": "Host rejected"}); return
        path = urlparse(self.path).path
        if path == "/api/catalog": self._send_json(200, catalog_public(self.manifest)); return
        if path == "/api/config": self._send_json(200, _json(self.runtime / ".eng-agents/bindings.json")); return
        if path == "/api/meta": self._send_json(200, {"runtime_path": str(self.runtime), "csrf_token": self.csrf_token}); return
        rel = path.lstrip("/") or "index.html"; file_path = (UI_DIR / rel).resolve()
        if not file_path.is_file() or UI_DIR.resolve() not in file_path.parents: self.send_error(404); return
        content = file_path.read_bytes(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(content))); self.send_header("Cache-Control", "no-store"); self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'"); self.end_headers(); self.wfile.write(content)
    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/complete": self.send_error(404); return
        if self.headers.get("Host") != self.allowed_host or self.headers.get("Origin") != self.allowed_origin:
            self._send_json(403, {"ok": False, "error": "Cross-origin request rejected"}); return
        try:
            data = self._body()
            if not secrets.compare_digest(str(data.pop("csrf_token", "")), self.csrf_token): raise ControlPlaneError("Setup page expired")
            validated = validate_bindings(data, self.runtime, self.manifest)
            with self.csrf_lock:
                if self.csrf_used: raise ControlPlaneError("Setup page expired")
                type(self).csrf_used = True
            atomic_json(self.runtime / ".eng-agents/bindings.json", validated)
        except ControlPlaneError as exc: self._send_json(400, {"ok": False, "error": str(exc)}); return
        self._send_json(200, {"ok": True}); setattr(self.server, "setup_completed", True); threading.Timer(0.3, self.server.shutdown).start()


def run_ui(runtime: pathlib.Path, manifest: dict[str, Any], host: str, port: int, open_browser: bool, timeout: int) -> int:
    SetupHandler.runtime, SetupHandler.manifest, SetupHandler.csrf_token, SetupHandler.csrf_used = runtime, manifest, secrets.token_urlsafe(24), False
    server = ThreadingHTTPServer((host, port), SetupHandler); SetupHandler.allowed_host = f"{host}:{server.server_port}"; SetupHandler.allowed_origin = f"http://{SetupHandler.allowed_host}"; setattr(server, "setup_completed", False)
    print(f"Engineering Agents setup: {SetupHandler.allowed_origin}/", flush=True)
    if open_browser: threading.Timer(0.2, lambda: webbrowser.open(SetupHandler.allowed_origin + "/")).start()
    timer = threading.Timer(timeout, server.shutdown) if timeout > 0 else None
    if timer: timer.daemon = True; timer.start()
    try: server.serve_forever()
    finally:
        if timer: timer.cancel()
        server.server_close()
    return 0 if getattr(server, "setup_completed", False) else 124


def print_schedule(runtime: pathlib.Path, *, run_now: bool = False, verified: bool = False) -> int:
    if not verified:
        readiness = doctor(runtime, deep=True)
        if not readiness["ok"]: raise ControlPlaneError("Deep runtime readiness failed: " + json.dumps(readiness, ensure_ascii=False))
    lock, manifest, bindings = load_runtime(runtime)
    if lock.get("commit") == "filesystem": raise ControlPlaneError("Unversioned filesystem catalogs cannot create or run Scheduled Tasks")
    intent = build_schedule_intent(runtime, bindings, manifest)
    if run_now: intent = {"action": "run-now", "scheduleIntent": intent, "instruction": "Run the selected entrypoint now in this Codex conversation; do not write private automation state."}
    print(json.dumps(intent, ensure_ascii=False, indent=2)); return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Engineering Agents Mac setup and lifecycle control plane")
    parser.add_argument("command", nargs="?", choices=["run", "clone", "ui", "apply", "materialize", "schedule", "doctor", "update", "rollback", "run-now"], default="run")
    parser.add_argument("--into", "--project", dest="runtime", default=str(DEFAULT_RUNTIME), help="Generated runtime project directory")
    parser.add_argument("--catalog-source", "--repo-url", dest="catalog_source", default=os.environ.get("ENG_AGENTS_CATALOG_URL", os.environ.get("ENG_AGENTS_REPO_URL", DEFAULT_CATALOG_URL)))
    parser.add_argument("--ref", default=os.environ.get("ENG_AGENTS_CATALOG_REF", os.environ.get("ENG_AGENTS_REPO_REF", "v1.0.0")))
    parser.add_argument("--expected-digest", default=os.environ.get("ENG_AGENTS_CATALOG_DIGEST"), help="Optional trusted sha256:<hex> release digest")
    parser.add_argument("--allow-filesystem-catalog", action="store_true", help="Development only: allow an unversioned local non-Git catalog")
    parser.add_argument("--cache-root", help="Catalog cache (default: two levels above runtime, under cache)")
    parser.add_argument("--host", default="127.0.0.1"); parser.add_argument("--port", type=int, default=int(os.environ.get("ENG_AGENTS_SETUP_PORT", "0"))); parser.add_argument("--timeout", type=int, default=int(os.environ.get("ENG_AGENTS_SETUP_TIMEOUT", "900"))); parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--skip-clone", action="store_true", help="Compatibility: reuse the catalog recorded in catalog.lock.json")
    parser.add_argument("--generation", help="Exact retained generation to activate during rollback")
    parser.add_argument("--deep", action="store_true", help="Run declared integration health checks (may require interactive login)")
    parser.add_argument("--codex-home", help="Deprecated compatibility option; ignored"); parser.add_argument("--skip-codex-sync", action="store_true", help="Deprecated compatibility option; ignored")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv); runtime = resolve_runtime(args.runtime); cache_root = pathlib.Path(args.cache_root).expanduser().resolve() if args.cache_root else runtime.parent.parent / "cache"
    try:
        if args.command == "rollback":
            print(json.dumps({"ok": True, "generation": rollback_runtime(runtime, args.generation)}, indent=2)); return 0
        if args.command in ("apply", "schedule"): return print_schedule(runtime)
        if args.command == "run-now": return print_schedule(runtime, run_now=True)
        if args.command == "doctor":
            report = doctor(runtime, deep=args.deep); print(json.dumps(report, ensure_ascii=False, indent=2)); return 0 if report["ok"] else 1
        if args.command == "ui" and (runtime / ".eng-agents/catalog.lock.json").is_file():
            active_lock = _json(runtime / ".eng-agents/catalog.lock.json")
            active_manifest = validate_catalog(runtime)
            if catalog_digest(runtime, active_manifest) != active_lock.get("digest"):
                raise ControlPlaneError("Active runtime failed digest verification")
            rc = run_ui(runtime, active_manifest, args.host, args.port, not args.no_browser, args.timeout)
            if rc: return rc
            readiness = doctor(runtime, deep=True)
            if not readiness["ok"]: print(json.dumps(readiness, ensure_ascii=False, indent=2)); return 1
            return print_schedule(runtime, verified=True)
        if args.skip_clone and (runtime / ".eng-agents/catalog.lock.json").is_file():
            lock = _json(runtime / ".eng-agents/catalog.lock.json")
            catalog = runtime; manifest = validate_catalog(catalog)
            if catalog_digest(catalog, manifest) != lock.get("digest"):
                raise ControlPlaneError("Materialized runtime failed digest verification")
        else:
            catalog, lock = resolve_catalog(args.catalog_source, args.ref, cache_root, allow_filesystem=args.allow_filesystem_catalog); manifest = validate_catalog(catalog); lock["materializedFrom"] = str(catalog)
            if args.expected_digest and not secrets.compare_digest(args.expected_digest, lock["digest"]):
                raise ControlPlaneError(f"Catalog digest mismatch: expected {args.expected_digest}, got {lock['digest']}")
        if lock.get("commit") == "filesystem" and args.command == "run":
            raise ControlPlaneError("Development filesystem catalogs may be materialized but cannot enter the setup/scheduling flow")
        if args.command == "clone": print(json.dumps({"catalogPath": str(catalog), **lock}, indent=2)); return 0
        if args.command in ("run", "materialize", "update"):
            materialize_runtime(runtime, catalog, lock, manifest); print(f"Runtime materialized at {runtime} from commit {lock['commit']}", flush=True)
            if args.command in ("materialize", "update"): return 0
        if args.command in ("run", "ui"):
            if args.command == "ui" and not (runtime / ".eng-agents/catalog.lock.json").is_file(): materialize_runtime(runtime, catalog, lock, manifest)
            rc = run_ui(runtime, manifest, args.host, args.port, not args.no_browser, args.timeout)
            if rc: return rc
            readiness = doctor(runtime, deep=True)
            if not readiness["ok"]: print(json.dumps(readiness, ensure_ascii=False, indent=2)); return 1
            return print_schedule(runtime, verified=True)
        return 0
    except (ControlPlaneError, subprocess.CalledProcessError) as exc:
        print(f"eng-agents: {exc}", file=sys.stderr); return 2


if __name__ == "__main__": raise SystemExit(main())
