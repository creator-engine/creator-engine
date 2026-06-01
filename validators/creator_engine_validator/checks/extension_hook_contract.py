"""G2.006.0 extension + hook contract substrate validator.

A shape-only record family that declares a CE **extension** (e.g. a Claude Code
hook-pack) and its **hook** bindings, as the declarative formalization of the
three-ring model:

* Ring 0 — the HARD, non-defeasible kernel floor (`ce launch` / `ce lane launch`).
* Ring 1 — the RUNTIME, launch-pinned, **DEFEASIBLE** in-band hook-pack; fails open.
* Ring 2 — the VALIDATOR bridge the Ring 1 hooks call (e.g. ``hook-check``).

The headline rule is the **enforcement_strength x ring coherence invariant**, which a
flat schema cannot express and which this check enforces: ``hard`` enforcement is valid
ONLY at ``ring_0``; a ``ring_1`` extension MUST be defeasible and its in-band hooks MUST
fail open. A hook that claims ``hard``/non-defeasible at Ring 1 is rejected.

Substrate only: this formalizes — and does NOT replace — the CC-G-C/D hook-pack runtime
(`.claude/**`, ``hook_check.py``). No runtime, no ``.claude/**`` mutation, and no
secret/credential value anywhere.

Prose contract: ``docs/operations/EXTENSION_HOOK_CONTRACT.md``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register
from .connector_substrate import (
    EMITTING_ROLES,
    FORBIDDEN_ACTIVE_ROLES,
    OPERATING_MODES,
    _contains_secret,
    _normalize_token,
    _pointer,
)

CHECK_NAME = "extension_hook_contract"
CONTRACT = "specs/v2/006-extension-hook-contract/spec.ce.yml#extension_contract"
SCHEMA_PATH = "schemas/extension-hook-contract.schema.yaml"
KEY = "extension_contract"
SCOPE_TOKEN = "extension-hook-contract"
PROTOCOL_DOC = "EXTENSION_HOOK_CONTRACT.md"
SPEC_FEATURE_DIR = "006-extension-hook-contract"

CODE_SCHEMA = "VAL-EXT-SCHEMA"
CODE_KIND = "VAL-EXT-KIND"
CODE_RING = "VAL-EXT-RING"
CODE_HOOK = "VAL-EXT-HOOK"
CODE_RING_COHERENCE = "VAL-EXT-RING-COHERENCE"
CODE_ROLE = "VAL-EXT-ROLE"
CODE_MODE = "VAL-EXT-MODE"
CODE_SECRET = "VAL-EXT-SECRET"
CODE_NO_INLINE = "VAL-EXT-NO-INLINE"

EXTENSION_KINDS = frozenset({"hook_pack", "connector", "directive_pack"})
RINGS = frozenset({"ring_0", "ring_1", "ring_2"})
ENFORCEMENT_STRENGTHS = frozenset({"hard", "runtime", "defeasible"})
HOOK_EVENTS = frozenset({"pretooluse", "posttooluse", "stop", "userpromptsubmit", "sessionstart"})
DECISION_PROTOCOLS = frozenset({"allow_deny", "allow_deny_block", "advisory"})
FAILURE_POSTURES = frozenset({"fail_open", "fail_closed"})

_YAML_SUFFIXES = {".yml", ".yaml"}
_MD_SUFFIXES = {".md", ".markdown"}


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _path_in_scope(path: Path) -> bool:
    parts = path.parts
    if SCOPE_TOKEN in parts:
        return True
    if path.name == PROTOCOL_DOC:
        return True
    for i in range(len(parts) - 2):
        if parts[i] == "specs" and parts[i + 1] == "v2" and parts[i + 2] == SPEC_FEATURE_DIR:
            return path.name == "spec.md"
    return False


def _iter_scanned_files(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    suffixes = _YAML_SUFFIXES | _MD_SUFFIXES
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            candidates = [path]
        elif path.is_dir():
            candidates = sorted(p for p in path.rglob("*") if p.is_file())
        else:
            candidates = []
        for candidate in candidates:
            if _is_tmp_artifact(candidate) or candidate.suffix.lower() not in suffixes or not _path_in_scope(candidate):
                continue
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            out.append(candidate)
    return out


def _validate_markdown(path: Path) -> list[ValidationError]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [make_error(CODE_NO_INLINE, path, "", f"failed to read markdown: {exc}", CONTRACT)]
    errors: list[ValidationError] = []
    in_fence = False
    fence_is_yaml = False
    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if line_no == 1 and stripped == "---":
            in_fence = True
            fence_is_yaml = True
            continue
        if in_fence and fence_is_yaml and stripped in {"---", "..."}:
            in_fence = False
            fence_is_yaml = False
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            if not in_fence:
                in_fence = True
                fence_is_yaml = stripped[3:].strip().lower() in {"yaml", "yml"}
            else:
                in_fence = False
                fence_is_yaml = False
            continue
        if not fence_is_yaml:
            continue
        if stripped.split(":", 1)[0].strip() == KEY:
            errors.append(make_error(CODE_NO_INLINE, path, _pointer(("line", line_no)), "extension-hook-contract metadata belongs in sidecars/examples, not Markdown bodies", CONTRACT))
    return errors


def validate_extension_contract_file(path: Path) -> list[ValidationError]:
    path = Path(path)
    if path.suffix.lower() in _MD_SUFFIXES:
        return _validate_markdown(path)
    try:
        data = load_yaml(path)
    except LoaderError as exc:
        return [make_error(CODE_SCHEMA, path, "", str(exc), SCHEMA_PATH)]
    errors: list[ValidationError] = []
    try:
        errors.extend(validate_with_schema(data, SCHEMA_PATH, path, code=CODE_SCHEMA, contract=SCHEMA_PATH))
    except Exception as exc:  # pragma: no cover - environment guard
        errors.append(make_error(CODE_SCHEMA, path, "", f"schema validation failed: {exc}", SCHEMA_PATH))
    if not isinstance(data, dict) or KEY not in data or not isinstance(data[KEY], dict):
        if not errors:
            errors.append(make_error(CODE_SCHEMA, path, "", "scoped YAML files must declare an extension_contract mapping", SCHEMA_PATH))
        return errors
    rec = data[KEY]
    pre = (KEY,)

    if _normalize_token(rec.get("extension_kind", "")) not in EXTENSION_KINDS:
        errors.append(make_error(CODE_KIND, path, _pointer(pre + ("extension_kind",)), "extension_kind must be one of hook_pack, connector, directive_pack", CONTRACT))

    ring = _normalize_token(rec.get("ring", ""))
    if ring not in RINGS:
        errors.append(make_error(CODE_RING, path, _pointer(pre + ("ring",)), "ring must be one of ring_0, ring_1, ring_2", CONTRACT))
    strength = _normalize_token(rec.get("enforcement_strength", ""))
    if strength not in ENFORCEMENT_STRENGTHS:
        errors.append(make_error(CODE_RING, path, _pointer(pre + ("enforcement_strength",)), "enforcement_strength must be one of hard, runtime, defeasible", CONTRACT))

    role = _normalize_token(rec.get("emitting_role", ""))
    if role not in EMITTING_ROLES or role in FORBIDDEN_ACTIVE_ROLES:
        errors.append(make_error(CODE_ROLE, path, _pointer(pre + ("emitting_role",)), "emitting_role must be a canonical non-ratifying role; agent_ratifier/source are reserved-inactive and may not emit", CONTRACT))
    if _normalize_token(rec.get("operating_mode", "")) not in OPERATING_MODES:
        errors.append(make_error(CODE_MODE, path, _pointer(pre + ("operating_mode",)), "operating_mode must be one of strict, auto, transcendence", CONTRACT))

    hooks = rec.get("hooks") if isinstance(rec.get("hooks"), list) else []
    for idx, hook in enumerate(hooks):
        if not isinstance(hook, dict):
            continue
        hpre = pre + ("hooks", idx)
        if _normalize_token(hook.get("event", "")) not in HOOK_EVENTS:
            errors.append(make_error(CODE_HOOK, path, _pointer(hpre + ("event",)), "hook event must be a supported Claude Code event (PreToolUse/PostToolUse/Stop/UserPromptSubmit/SessionStart)", CONTRACT))
        if _normalize_token(hook.get("decision_protocol", "")) not in DECISION_PROTOCOLS:
            errors.append(make_error(CODE_HOOK, path, _pointer(hpre + ("decision_protocol",)), "decision_protocol must be one of allow_deny, allow_deny_block, advisory", CONTRACT))
        if _normalize_token(hook.get("failure_posture", "")) not in FAILURE_POSTURES:
            errors.append(make_error(CODE_HOOK, path, _pointer(hpre + ("failure_posture",)), "failure_posture must be one of fail_open, fail_closed", CONTRACT))

    # --- the three-ring coherence invariant (cross-field; schema cannot express) ---
    if strength == "hard" and ring and ring != "ring_0":
        errors.append(make_error(CODE_RING_COHERENCE, path, _pointer(pre + ("enforcement_strength",)), "hard enforcement_strength is valid ONLY at ring_0; the HARD floor is the Ring 0 kernel", CONTRACT))
    if ring == "ring_1":
        if strength == "hard":
            errors.append(make_error(CODE_RING_COHERENCE, path, _pointer(pre + ("enforcement_strength",)), "a ring_1 extension is RUNTIME/DEFEASIBLE; it must not claim hard enforcement (use runtime or defeasible)", CONTRACT))
        for idx, hook in enumerate(hooks):
            if not isinstance(hook, dict):
                continue
            if hook.get("defeasible") is False:
                errors.append(make_error(CODE_RING_COHERENCE, path, _pointer(pre + ("hooks", idx, "defeasible")), "ring_1 hooks are DEFEASIBLE by contract; defeasible must not be false", CONTRACT))
            if _normalize_token(hook.get("failure_posture", "")) == "fail_closed":
                errors.append(make_error(CODE_RING_COHERENCE, path, _pointer(pre + ("hooks", idx, "failure_posture")), "ring_1 in-band hooks fail open by contract; failure_posture must not be fail_closed", CONTRACT))

    if _contains_secret(rec):
        errors.append(make_error(CODE_SECRET, path, _pointer(pre), "extension contract must not carry secret/credential values; reference validators/credentials by name only", CONTRACT))
    return errors


@register(
    CHECK_NAME,
    [CODE_SCHEMA, CODE_KIND, CODE_RING, CODE_HOOK, CODE_RING_COHERENCE, CODE_ROLE, CODE_MODE, CODE_SECRET, CODE_NO_INLINE],
)
def run_extension_hook_contract(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for file_path in _iter_scanned_files(paths):
        errors.extend(validate_extension_contract_file(file_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
