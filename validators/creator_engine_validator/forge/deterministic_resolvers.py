"""Deterministic, read-only conflict resolvers for known CE integrator conflicts.

These helpers model only the mechanical families observed in ce-ops#216's
Integrator MVP grounding set (#366/#367/#368/#373). They do not run git, push,
open PRs, read credentials, or choose among semantic edits. Unrecognized or
ambiguous conflicts return an unresolved result with evidence.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, replace
from pathlib import PurePosixPath
from typing import Any

_VERSIONS_PATH = "validators/creator_engine_validator/_versions.py"
_VERSION_BOUNDARY_TEST_PATH = "validators/tests/unit/test_version_boundary.py"
_REGISTRY_NAMES = ("V1_RUNTIME", "V3_RUNTIME")
_COUNT_ASSERT_RE = re.compile(r"(?m)^(\s*)assert len\(ver\.(V[13]_RUNTIME)\) == \d+\s*$")


@dataclass(frozen=True)
class ResolverResult:
    """Structured outcome for a deterministic resolver attempt."""

    resolver: str
    applicable: bool
    resolved: bool
    unresolved: bool
    changed_paths: tuple[str, ...]
    reason: str
    evidence: tuple[str, ...] = ()
    content: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolver": self.resolver,
            "applicable": self.applicable,
            "resolved": self.resolved,
            "unresolved": self.unresolved,
            "changed_paths": list(self.changed_paths),
            "reason": self.reason,
            "evidence": list(self.evidence),
            "content": self.content,
        }


@dataclass(frozen=True)
class _ConflictHunk:
    ours: tuple[str, ...]
    theirs: tuple[str, ...]


class _MalformedConflict(ValueError):
    pass


class _MalformedRegistry(ValueError):
    pass


def resolve_conflict(
    path: str,
    conflicted_text: str,
    *,
    context_files: dict[str, str] | None = None,
) -> ResolverResult:
    """Detect, apply, and verify one known deterministic conflict family."""

    if path == _VERSIONS_PATH:
        result = _resolve_versions_registry(path, conflicted_text)
    elif path == _VERSION_BOUNDARY_TEST_PATH:
        result = _resolve_version_boundary_counts(path, conflicted_text, context_files or {})
    elif _is_append_registry_path(path) or _is_lockfile_path(path):
        result = _resolve_append_only(path, conflicted_text)
    else:
        return _not_applicable("unrecognized_conflict_family")
    return verify_resolution(result, context_files=context_files or {})


def resolve_non_overlapping_additions(
    *,
    base_paths: set[str] | frozenset[str],
    ours_paths: set[str] | frozenset[str],
    theirs_paths: set[str] | frozenset[str],
) -> ResolverResult:
    """Resolve non-overlapping CE changelog/PR-manifest additions by unioning paths."""

    ours_added = set(ours_paths) - set(base_paths)
    theirs_added = set(theirs_paths) - set(base_paths)
    additions = ours_added | theirs_added
    if not additions or not all(_is_ce_carrier_path(p) for p in additions):
        return _not_applicable("not_ce_carrier_additions")
    overlap = sorted(ours_added & theirs_added)
    if overlap:
        return _unresolved(
            "ce_carrier_non_overlapping_additions",
            "overlapping additions require semantic review",
            changed_paths=tuple(overlap),
            evidence=tuple(f"overlap={p}" for p in overlap),
        )
    return ResolverResult(
        resolver="ce_carrier_non_overlapping_additions",
        applicable=True,
        resolved=True,
        unresolved=False,
        changed_paths=tuple(sorted(additions)),
        reason="non-overlapping CE changelog/manifest additions unioned",
        evidence=(f"additions={len(additions)}",),
    )


def verify_resolution(
    result: ResolverResult,
    *,
    context_files: dict[str, str] | None = None,
) -> ResolverResult:
    """Verify a produced resolution remains inside its deterministic contract."""

    if not result.resolved or result.content is None:
        return result
    if "<<<<<<<" in result.content or ">>>>>>>" in result.content or "=======" in result.content:
        return _unresolved(
            result.resolver,
            "resolution still contains conflict markers",
            changed_paths=result.changed_paths,
            evidence=result.evidence,
        )
    if result.resolver == "versions_module_registry_union":
        try:
            registries = _extract_registries(result.content)
        except _MalformedRegistry as exc:
            return _unresolved(
                result.resolver,
                f"verification failed: {exc}",
                changed_paths=result.changed_paths,
                evidence=result.evidence,
            )
        collision = sorted(registries["V1_RUNTIME"] & registries["V3_RUNTIME"])
        if collision:
            return _unresolved(
                result.resolver,
                "verification failed: module id collision across version registries",
                changed_paths=result.changed_paths,
                evidence=tuple(f"collision={c}" for c in collision),
            )
        evidence = tuple(
            sorted(
                set(result.evidence)
                | {f"V1_RUNTIME={len(registries['V1_RUNTIME'])}", f"V3_RUNTIME={len(registries['V3_RUNTIME'])}"}
            )
        )
        return replace(result, evidence=evidence)
    if result.resolver == "version_boundary_count_post_merge_total":
        try:
            ast.parse(result.content)
        except SyntaxError as exc:
            return _unresolved(
                result.resolver,
                f"verification failed: malformed Python after count resolution: {exc.msg}",
                changed_paths=result.changed_paths,
                evidence=result.evidence,
            )
    return result


def _resolve_versions_registry(path: str, conflicted_text: str) -> ResolverResult:
    try:
        ours_text, theirs_text = _split_conflict_variants(conflicted_text)
        ours = _extract_registries(ours_text)
        theirs = _extract_registries(theirs_text)
    except (_MalformedConflict, _MalformedRegistry) as exc:
        return _unresolved(
            "versions_module_registry_union",
            f"malformed _versions.py registry conflict: {exc}",
            changed_paths=(path,),
        )

    merged = {name: ours[name] | theirs[name] for name in _REGISTRY_NAMES}
    collision = sorted(merged["V1_RUNTIME"] & merged["V3_RUNTIME"])
    if collision:
        return _unresolved(
            "versions_module_registry_union",
            "module id collision across V1_RUNTIME and V3_RUNTIME",
            changed_paths=(path,),
            evidence=tuple(f"collision={c}" for c in collision),
        )
    try:
        content = _replace_registry_assignments(ours_text, merged)
    except (_MalformedRegistry, SyntaxError) as exc:
        return _unresolved(
            "versions_module_registry_union",
            f"malformed _versions.py registry conflict: {exc}",
            changed_paths=(path,),
        )
    return ResolverResult(
        resolver="versions_module_registry_union",
        applicable=True,
        resolved=True,
        unresolved=False,
        changed_paths=(path,),
        reason="unioned module registry entries from both sides",
        evidence=tuple(f"{name}_union={len(merged[name])}" for name in _REGISTRY_NAMES),
        content=content,
    )


def _resolve_version_boundary_counts(
    path: str,
    conflicted_text: str,
    context_files: dict[str, str],
) -> ResolverResult:
    versions_text = context_files.get(_VERSIONS_PATH)
    if not versions_text:
        return _unresolved(
            "version_boundary_count_post_merge_total",
            "requires resolved _versions.py context",
            changed_paths=(path,),
        )
    try:
        counts = {name: len(values) for name, values in _extract_registries(versions_text).items()}
        content, registries_seen = _replace_conflict_hunks(
            conflicted_text,
            lambda hunk: _version_count_replacement(hunk, counts),
        )
    except (_MalformedConflict, _MalformedRegistry, ValueError) as exc:
        return _unresolved(
            "version_boundary_count_post_merge_total",
            f"malformed version-boundary count conflict: {exc}",
            changed_paths=(path,),
        )
    return ResolverResult(
        resolver="version_boundary_count_post_merge_total",
        applicable=True,
        resolved=True,
        unresolved=False,
        changed_paths=(path,),
        reason="replaced expected module-count conflict with post-merge registry total",
        evidence=tuple(f"{name}={counts[name]}" for name in sorted(registries_seen)),
        content=content,
    )


def _version_count_replacement(hunk: _ConflictHunk, counts: dict[str, int]) -> tuple[list[str], set[str]]:
    ours = "".join(hunk.ours)
    theirs = "".join(hunk.theirs)
    ours_match = _COUNT_ASSERT_RE.findall(ours)
    theirs_match = _COUNT_ASSERT_RE.findall(theirs)
    if len(ours_match) != 1 or len(theirs_match) != 1:
        raise ValueError("count hunk must contain exactly one count assertion per side")
    (indent, ours_name), (theirs_indent, theirs_name) = ours_match[0], theirs_match[0]
    if ours_name != theirs_name:
        raise ValueError("count hunk sides reference different registries")
    if indent != theirs_indent:
        raise ValueError("count hunk sides use different indentation")
    if ours_name not in counts:
        raise ValueError(f"unknown registry {ours_name}")
    return [f"{indent}assert len(ver.{ours_name}) == {counts[ours_name]}\n"], {ours_name}


def _resolve_append_only(path: str, conflicted_text: str) -> ResolverResult:
    if _is_lockfile_path(path) and not _is_append_registry_path(path):
        return _unresolved(
            "append_only_union",
            "lockfile canonicalization is unclear; escalating as unresolved",
            changed_paths=(path,),
        )
    try:
        content, evidence = _replace_conflict_hunks(conflicted_text, _append_hunk_replacement)
    except (_MalformedConflict, ValueError) as exc:
        return _unresolved(
            "append_only_union",
            str(exc),
            changed_paths=(path,),
        )
    return ResolverResult(
        resolver="append_only_union",
        applicable=True,
        resolved=True,
        unresolved=False,
        changed_paths=(path,),
        reason="unioned non-overlapping append-only registry entries",
        evidence=tuple(sorted(evidence)),
        content=content,
    )


def _append_hunk_replacement(hunk: _ConflictHunk) -> tuple[list[str], set[str]]:
    ours = [line for line in hunk.ours if line.strip()]
    theirs = [line for line in hunk.theirs if line.strip()]
    ours_values = {line.rstrip("\n") for line in ours}
    theirs_values = {line.rstrip("\n") for line in theirs}
    overlap = sorted(ours_values & theirs_values)
    if overlap:
        raise ValueError("overlapping append entries require semantic review")
    if len(ours_values) != len(ours) or len(theirs_values) != len(theirs):
        raise ValueError("duplicate append entries require semantic review")
    merged = [f"{line}\n" for line in sorted(ours_values | theirs_values)]
    return merged, {f"append_lines={len(merged)}", "canonical_order=lexicographic"}


def _extract_registries(text: str) -> dict[str, set[str]]:
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        raise _MalformedRegistry(f"Python does not parse: {exc.msg}") from exc
    registries: dict[str, set[str]] = {}
    for node in tree.body:
        name = _assignment_name(node)
        if name in _REGISTRY_NAMES:
            registries[name] = _registry_entries(node)
    missing = [name for name in _REGISTRY_NAMES if name not in registries]
    if missing:
        raise _MalformedRegistry(f"missing registry assignment(s): {', '.join(missing)}")
    return registries


def _assignment_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    return None


def _assignment_value(node: ast.AST) -> ast.AST:
    if isinstance(node, ast.AnnAssign) and node.value is not None:
        return node.value
    if isinstance(node, ast.Assign):
        return node.value
    raise _MalformedRegistry("registry assignment has no value")


def _registry_entries(node: ast.AST) -> set[str]:
    value = _assignment_value(node)
    if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "frozenset"):
        raise _MalformedRegistry("registry value must be frozenset(...)")
    if len(value.args) != 1:
        raise _MalformedRegistry("registry frozenset must have one literal collection argument")
    literal = value.args[0]
    if not isinstance(literal, (ast.Set, ast.List, ast.Tuple)):
        raise _MalformedRegistry("registry frozenset argument must be a literal collection")
    entries: set[str] = set()
    for elt in literal.elts:
        if not isinstance(elt, ast.Constant) or not isinstance(elt.value, str) or not elt.value.strip():
            raise _MalformedRegistry("malformed registry entry; expected non-empty string literal")
        if elt.value in entries:
            raise _MalformedRegistry(f"duplicate registry entry {elt.value!r}")
        entries.add(elt.value)
    return entries


def _replace_registry_assignments(text: str, registries: dict[str, set[str]]) -> str:
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    replacements: list[tuple[int, int, list[str]]] = []
    for node in tree.body:
        name = _assignment_name(node)
        if name in registries:
            if getattr(node, "end_lineno", None) is None:
                raise _MalformedRegistry(f"cannot locate end of {name} assignment")
            annotated = isinstance(node, ast.AnnAssign)
            replacements.append(
                (node.lineno - 1, node.end_lineno, _format_registry_assignment(name, registries[name], annotated))
            )
    for start, end, replacement in sorted(replacements, reverse=True):
        lines[start:end] = replacement
    return "".join(lines)


def _format_registry_assignment(name: str, entries: set[str], annotated: bool) -> list[str]:
    prefix = f"{name}: frozenset[str]" if annotated else name
    lines = [f"{prefix} = frozenset(\n", "    {\n"]
    lines.extend(f'        "{entry}",\n' for entry in sorted(entries))
    lines.extend(["    }\n", ")\n"])
    return lines


def _split_conflict_variants(text: str) -> tuple[str, str]:
    parsed = _parse_conflict_stream(text)
    ours: list[str] = []
    theirs: list[str] = []
    for item in parsed:
        if isinstance(item, _ConflictHunk):
            ours.extend(item.ours)
            theirs.extend(item.theirs)
        else:
            ours.append(item)
            theirs.append(item)
    return "".join(ours), "".join(theirs)


def _replace_conflict_hunks(text: str, replacer) -> tuple[str, set[str]]:
    parsed = _parse_conflict_stream(text)
    out: list[str] = []
    evidence: set[str] = set()
    for item in parsed:
        if isinstance(item, _ConflictHunk):
            replacement, item_evidence = replacer(item)
            out.extend(replacement)
            evidence.update(item_evidence)
        else:
            out.append(item)
    return "".join(out), evidence


def _parse_conflict_stream(text: str) -> list[str | _ConflictHunk]:
    lines = text.splitlines(keepends=True)
    parsed: list[str | _ConflictHunk] = []
    ours: list[str] = []
    theirs: list[str] = []
    state = "normal"
    saw_hunk = False
    for line in lines:
        if line.startswith("<<<<<<<"):
            if state != "normal":
                raise _MalformedConflict("nested conflict marker")
            state = "ours"
            ours = []
            theirs = []
            saw_hunk = True
            continue
        if line.startswith("|||||||"):
            if state != "ours":
                raise _MalformedConflict("base marker outside ours side")
            state = "base"
            continue
        if line.startswith("======="):
            if state not in {"ours", "base"}:
                raise _MalformedConflict("separator marker outside conflict")
            state = "theirs"
            continue
        if line.startswith(">>>>>>>"):
            if state != "theirs":
                raise _MalformedConflict("end marker outside theirs side")
            parsed.append(_ConflictHunk(tuple(ours), tuple(theirs)))
            state = "normal"
            continue
        if state == "normal":
            parsed.append(line)
        elif state == "ours":
            ours.append(line)
        elif state == "theirs":
            theirs.append(line)
        elif state == "base":
            continue
    if state != "normal":
        raise _MalformedConflict("unterminated conflict marker")
    if not saw_hunk:
        raise _MalformedConflict("no conflict markers found")
    return parsed


def _is_ce_carrier_path(path: str) -> bool:
    return bool(re.fullmatch(r"\.ce/(changelog|pr-manifests)/[^/]+\.md", path))


def _is_append_registry_path(path: str) -> bool:
    p = PurePosixPath(path)
    return (
        path.startswith(".ce/registries/")
        or "/registries/" in path
        or p.name.endswith(".registry")
        or p.name.endswith(".registry.txt")
    )


def _is_lockfile_path(path: str) -> bool:
    name = PurePosixPath(path).name
    return name in {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock"} or name.endswith(".lock")


def _not_applicable(reason: str) -> ResolverResult:
    return ResolverResult(
        resolver="none",
        applicable=False,
        resolved=False,
        unresolved=False,
        changed_paths=(),
        reason=reason,
    )


def _unresolved(
    resolver: str,
    reason: str,
    *,
    changed_paths: tuple[str, ...],
    evidence: tuple[str, ...] = (),
) -> ResolverResult:
    return ResolverResult(
        resolver=resolver,
        applicable=True,
        resolved=False,
        unresolved=True,
        changed_paths=changed_paths,
        reason=reason,
        evidence=evidence,
    )
