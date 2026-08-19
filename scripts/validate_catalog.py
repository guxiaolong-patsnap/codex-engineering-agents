#!/usr/bin/env python3
"""Validate the Engineering Agents authoring catalog using only Python stdlib."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

try:
    import tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:  # Python 3.9/3.10 on managed Mac minis.
    tomllib = None  # type: ignore[assignment]


ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$")
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bglpat-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|password|secret|token)\b\s*[:=]\s*"
        r"[\"'][A-Za-z0-9+/=_-]{12,}[\"']"
    ),
)


def _is_id(value: Any) -> bool:
    return isinstance(value, str) and bool(ID_RE.fullmatch(value))


def _load_json(path: Path, errors: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: invalid JSON: {exc}")
        return None


def _parse_simple_toml(text: str) -> dict[str, Any]:
    """Parse the flat TOML subset used by agent definitions on Python < 3.11."""
    result: dict[str, Any] = {}
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        raw = lines[index]
        index += 1
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_-]+)\s*=\s*(.*)$", line)
        if not match:
            raise ValueError(f"line {index}: expected key = value")
        key, value_text = match.groups()
        if key in result:
            raise ValueError(f"line {index}: duplicate key {key}")
        if value_text.startswith('"""'):
            value_text = value_text[3:]
            chunks: list[str] = []
            if value_text.endswith('"""'):
                chunks.append(value_text[:-3])
            else:
                chunks.append(value_text)
                while index < len(lines) and not lines[index].endswith('"""'):
                    chunks.append(lines[index])
                    index += 1
                if index >= len(lines):
                    raise ValueError(f"line {index}: unterminated multiline string")
                chunks.append(lines[index][:-3])
                index += 1
            result[key] = "\n".join(chunks)
            continue
        try:
            value = ast.literal_eval(value_text)
        except (SyntaxError, ValueError) as exc:
            if value_text in {"true", "false"}:
                value = value_text == "true"
            else:
                raise ValueError(f"line {index}: invalid value for {key}: {exc}") from exc
        if not isinstance(value, (str, int, float, bool, list)):
            raise ValueError(f"line {index}: unsupported value for {key}")
        result[key] = value
    return result


def _load_toml(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        text = path.read_text(encoding="utf-8")
        data = tomllib.loads(text) if tomllib is not None else _parse_simple_toml(text)
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(f"{path}: invalid TOML: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{path}: TOML root must be a table")
        return None
    return data


def _frontmatter(path: Path, errors: list[str]) -> dict[str, str] | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        errors.append(f"{path}: cannot read skill: {exc}")
        return None
    if not lines or lines[0].strip() != "---":
        errors.append(f"{path}: SKILL.md must start with YAML frontmatter")
        return None
    try:
        end = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        errors.append(f"{path}: YAML frontmatter is not closed")
        return None
    result: dict[str, str] = {}
    for line_number, line in enumerate(lines[1:end], 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            errors.append(f"{path}:{line_number}: unsupported frontmatter line")
            continue
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if not key or not value:
            errors.append(f"{path}:{line_number}: frontmatter key and value are required")
            continue
        if value[:1] in {'"', "'"} and value[-1:] == value[:1]:
            value = value[1:-1]
        result[key] = value
    for required in ("name", "description"):
        if not result.get(required):
            errors.append(f"{path}: frontmatter requires {required!r}")
    return result


def _check_string_list(
    entry: dict[str, Any], key: str, location: str, errors: list[str]
) -> list[str]:
    value = entry.get(key)
    if not isinstance(value, list):
        errors.append(f"{location}: {key} must be an array")
        return []
    if any(not _is_id(item) for item in value):
        errors.append(f"{location}: {key} contains an invalid id")
    if len(value) != len(set(item for item in value if isinstance(item, str))):
        errors.append(f"{location}: {key} contains duplicates")
    return [item for item in value if isinstance(item, str)]


def _check_path(root: Path, value: Any, suffix: str, location: str, errors: list[str]) -> Path | None:
    if not isinstance(value, str) or not value:
        errors.append(f"{location}: path must be a non-empty string")
        return None
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        errors.append(f"{location}: path must stay relative to the catalog root")
        return None
    target = root / relative
    try:
        target.resolve().relative_to(root.resolve())
    except ValueError:
        errors.append(f"{location}: path escapes the catalog root")
        return None
    if not value.endswith(suffix):
        errors.append(f"{location}: path must end in {suffix}")
    if target.is_symlink():
        errors.append(f"{location}: declared payload must not be a symlink")
    if not target.is_file():
        errors.append(f"{location}: path does not exist: {value}")
    return target


def _check_skill_path(
    root: Path, value: Any, identifier: str, location: str, errors: list[str]
) -> tuple[Path, Path] | None:
    if not isinstance(value, str) or not value:
        errors.append(f"{location}: path must be a non-empty string")
        return None
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        errors.append(f"{location}: path must stay relative to the catalog root")
        return None
    directory = root / relative
    try:
        directory.resolve().relative_to(root.resolve())
    except ValueError:
        errors.append(f"{location}: path escapes the catalog root")
        return None
    if directory != root / ".agents/skills" / identifier:
        errors.append(f"{location}: skill must use .agents/skills/<id>")
    skill_file = directory / "SKILL.md"
    if not directory.is_dir() or not skill_file.is_file():
        errors.append(f"{location}: path must be a skill directory containing SKILL.md")
    if directory.is_symlink() or any(path.is_symlink() for path in directory.rglob("*")):
        errors.append(f"{location}: skill payload must not contain symlinks")
    return directory, skill_file


def _check_exact_fields(
    entry: dict[str, Any], required: set[str], location: str, errors: list[str]
) -> None:
    missing = sorted(required - entry.keys())
    extra = sorted(entry.keys() - required)
    if missing:
        errors.append(f"{location}: missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"{location}: unknown fields: {', '.join(extra)}")


def _validate_manifest_shape(manifest: Any, errors: list[str]) -> dict[str, Any] | None:
    if not isinstance(manifest, dict):
        errors.append("catalog/manifest.json: root must be an object")
        return None
    required = {
        "apiVersion",
        "catalogVersion",
        "compatibility",
        "agents",
        "skills",
        "integrations",
        "entrypoints",
    }
    missing = sorted(required - manifest.keys())
    if missing:
        errors.append(f"catalog/manifest.json: missing fields: {', '.join(missing)}")
    allowed = required | {"$schema"}
    extra = sorted(manifest.keys() - allowed)
    if extra:
        errors.append(f"catalog/manifest.json: unknown fields: {', '.join(extra)}")
    if manifest.get("apiVersion") != "eng-agents.patsnap.com/v1":
        errors.append("catalog/manifest.json: unsupported apiVersion")
    if not isinstance(manifest.get("catalogVersion"), str) or not SEMVER_RE.fullmatch(
        manifest.get("catalogVersion", "")
    ):
        errors.append("catalog/manifest.json: catalogVersion must be semantic version syntax")
    compatibility = manifest.get("compatibility")
    if not isinstance(compatibility, dict) or not isinstance(compatibility.get("plugin"), str) or not compatibility.get("plugin"):
        errors.append("catalog/manifest.json: compatibility.plugin is required")
    for collection in ("agents", "skills", "integrations"):
        if not isinstance(manifest.get(collection), list):
            errors.append(f"catalog/manifest.json: {collection} must be an array")
    if not isinstance(manifest.get("entrypoints"), dict):
        errors.append("catalog/manifest.json: entrypoints must be an object")
    return manifest


def _validate_discovery_coverage(
    root: Path,
    declared_agents: set[Path],
    declared_skills: set[Path],
    declared_integrations: set[Path],
    errors: list[str],
) -> None:
    actual_agents = set((root / ".codex/agents").glob("*.toml"))
    actual_skills = set((root / ".agents/skills").glob("*/SKILL.md"))
    actual_integrations = set((root / "integrations").glob("*/*/integration.json"))
    for label, actual, declared in (
        ("agent", actual_agents, declared_agents),
        ("skill", actual_skills, declared_skills),
        ("integration", actual_integrations, declared_integrations),
    ):
        for path in sorted(actual - declared):
            errors.append(f"{path}: {label} is not declared in catalog/manifest.json")


def _check_cycles(graph: dict[str, list[str]], errors: list[str]) -> None:
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> None:
        current = state.get(node, 0)
        if current == 2:
            return
        if current == 1:
            start = stack.index(node)
            errors.append("dependency cycle: " + " -> ".join(stack[start:] + [node]))
            return
        state[node] = 1
        stack.append(node)
        for neighbor in graph.get(node, []):
            visit(neighbor)
        stack.pop()
        state[node] = 2

    for node in sorted(graph):
        if state.get(node, 0) == 0:
            visit(node)


def _scan_secrets(paths: Iterable[Path], errors: list[str]) -> None:
    for path in sorted(set(paths)):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"{path}: possible embedded secret ({pattern.pattern})")
                break


def validate_catalog(root: Path) -> list[str]:
    """Return deterministic validation errors for a catalog checkout."""
    root = root.resolve()
    errors: list[str] = []
    manifest_path = root / "catalog/manifest.json"
    schema_path = root / "catalog/manifest.schema.json"

    # Parse every JSON authoring artifact, including the canonical schema.
    json_paths = sorted((root / "catalog").glob("*.json")) + sorted(
        (root / "integrations").glob("*/*/*.json")
    )
    parsed_json = {path: _load_json(path, errors) for path in json_paths}
    if schema_path not in parsed_json:
        errors.append("catalog/manifest.schema.json: canonical schema is missing")
    manifest = _validate_manifest_shape(parsed_json.get(manifest_path), errors)
    if manifest is None:
        return sorted(set(errors))

    agents = manifest.get("agents") if isinstance(manifest.get("agents"), list) else []
    skills = manifest.get("skills") if isinstance(manifest.get("skills"), list) else []
    integrations = manifest.get("integrations") if isinstance(manifest.get("integrations"), list) else []
    id_sets: dict[str, set[str]] = {"agent": set(), "skill": set(), "integration": set()}
    graph: dict[str, list[str]] = {}
    declared_agents: set[Path] = set()
    declared_skills: set[Path] = set()
    declared_integrations: set[Path] = set()
    source_paths: list[Path] = [manifest_path, schema_path]

    for index, entry in enumerate(agents):
        location = f"agents[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{location}: entry must be an object")
            continue
        _check_exact_fields(
            entry,
            {"id", "path", "owner", "skillDependencies", "integrationDependencies"},
            location,
            errors,
        )
        identifier = entry.get("id")
        if not _is_id(identifier):
            errors.append(f"{location}: invalid id")
            continue
        if identifier in id_sets["agent"]:
            errors.append(f"{location}: duplicate agent id {identifier}")
        id_sets["agent"].add(identifier)
        if not _is_id(entry.get("owner")):
            errors.append(f"{location}: invalid owner")
        skill_deps = _check_string_list(entry, "skillDependencies", location, errors)
        integration_deps = _check_string_list(entry, "integrationDependencies", location, errors)
        target = _check_path(root, entry.get("path"), ".toml", location, errors)
        if target:
            declared_agents.add(target)
            source_paths.append(target)
            if target.parent != root / ".codex/agents":
                errors.append(f"{location}: agent TOML must be directly under .codex/agents")
            data = _load_toml(target, errors) if target.is_file() else None
            if data is not None:
                if data.get("name") != identifier or target.stem != identifier:
                    errors.append(f"{location}: id, TOML name, and filename must match")
                if "model" in data or "model_reasoning_effort" in data:
                    errors.append(f"{location}: model policy belongs to the runtime control plane")
        graph[f"agent:{identifier}"] = [f"skill:{item}" for item in skill_deps] + [
            f"integration:{item}" for item in integration_deps
        ]

    for index, entry in enumerate(skills):
        location = f"skills[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{location}: entry must be an object")
            continue
        _check_exact_fields(
            entry,
            {
                "id",
                "path",
                "owner",
                "kind",
                "agentDependencies",
                "skillDependencies",
                "integrationDependencies",
            },
            location,
            errors,
        )
        identifier = entry.get("id")
        if not _is_id(identifier):
            errors.append(f"{location}: invalid id")
            continue
        if identifier in id_sets["skill"]:
            errors.append(f"{location}: duplicate skill id {identifier}")
        id_sets["skill"].add(identifier)
        if not _is_id(entry.get("owner")):
            errors.append(f"{location}: invalid owner")
        if entry.get("kind") not in {"dispatcher", "specialist"}:
            errors.append(f"{location}: kind must be dispatcher or specialist")
        agent_deps = _check_string_list(entry, "agentDependencies", location, errors)
        skill_deps = _check_string_list(entry, "skillDependencies", location, errors)
        integration_deps = _check_string_list(entry, "integrationDependencies", location, errors)
        skill_target = _check_skill_path(
            root, entry.get("path"), identifier, location, errors
        )
        if skill_target:
            directory, target = skill_target
            declared_skills.add(target)
            source_paths.extend(path for path in directory.rglob("*") if path.is_file())
            metadata = _frontmatter(target, errors) if target.is_file() else None
            if metadata is not None and metadata.get("name") != identifier:
                errors.append(f"{location}: id, frontmatter name, and directory must match")
        graph[f"skill:{identifier}"] = [f"agent:{item}" for item in agent_deps] + [
            f"skill:{item}" for item in skill_deps
        ] + [f"integration:{item}" for item in integration_deps]

    for index, entry in enumerate(integrations):
        location = f"integrations[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{location}: entry must be an object")
            continue
        _check_exact_fields(entry, {"id", "path", "owner", "kind"}, location, errors)
        identifier = entry.get("id")
        if not _is_id(identifier):
            errors.append(f"{location}: invalid id")
            continue
        if identifier in id_sets["integration"]:
            errors.append(f"{location}: duplicate integration id {identifier}")
        id_sets["integration"].add(identifier)
        if not _is_id(entry.get("owner")):
            errors.append(f"{location}: invalid owner")
        kind = entry.get("kind")
        if kind not in {"cli", "mcp"}:
            errors.append(f"{location}: kind must be cli or mcp")
        target = _check_path(root, entry.get("path"), "integration.json", location, errors)
        if target:
            declared_integrations.add(target)
            source_paths.append(target)
            data = parsed_json.get(target)
            if isinstance(data, dict):
                if data.get("id") != identifier or data.get("kind") != kind:
                    errors.append(f"{location}: id and kind must match the integration declaration")
                if data.get("access") not in {"read-only", "read-write"}:
                    errors.append(f"{location}: integration access must be explicit")
        graph[f"integration:{identifier}"] = []

    for node, dependencies in graph.items():
        for dependency in dependencies:
            kind, identifier = dependency.split(":", 1)
            if identifier not in id_sets[kind]:
                errors.append(f"{node}: dangling dependency {dependency}")

    entrypoints = manifest.get("entrypoints")
    if isinstance(entrypoints, dict):
        for name, entry in sorted(entrypoints.items()):
            if not isinstance(entry, dict) or set(entry) != {"skill"}:
                errors.append(f"entrypoints.{name}: must contain exactly one skill field")
                continue
            if entry["skill"] not in id_sets["skill"]:
                errors.append(f"entrypoints.{name}: dangling skill {entry['skill']}")

    _validate_discovery_coverage(
        root, declared_agents, declared_skills, declared_integrations, errors
    )
    _check_cycles(graph, errors)
    _scan_secrets(source_paths, errors)
    return sorted(set(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="catalog repository root",
    )
    args = parser.parse_args(argv)
    errors = validate_catalog(args.root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Catalog validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
