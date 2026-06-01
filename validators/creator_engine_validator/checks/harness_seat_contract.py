"""G2.007.0 harness seat-contract substrate validator.

A shape-only, harness-agnostic record family that declares a Controller-seat contract:
the harness occupying the seat, the required launch posture, the genuinely
posture-defeating modes it must refuse, the full-permission mode (the efficient
Controller operating mode) and its harness-specific flag, the enforcement ring, and the
required hook-pack (a G2.006.0 ``extension_contract``).

CE does not privilege any harness — ``claude_code`` is the reference instance and
``codex``/``hermes``/``openclaw`` instantiate the same contract (promoted in G2.007.1).

Headline rule — **full-permission mode is the efficient Controller mode, not a refused
one.** A Controller needs full permissions to work without per-action human approval;
the validator enforces ``full_permission_mode: true`` => ``ring0_hook_pack_confirmed:
true`` (the Ring 0 hook-pack confirmation is the safety substitute for per-action
approval; hooks still fire under full permissions). Implementation varies by harness, so
``permission_mode_flag`` records the concrete flag and the validator binds it for known
harnesses (``claude_code`` => ``--dangerously-skip-permissions``; ``codex`` =>
``--yolo``); ``hermes``/``openclaw`` are bound by G2.007.1.

Substrate only: this formalizes — and does NOT replace — the CC-G-* runtime
(``.claude/**``, ``hook_check.py``, ``ce launch``). No runtime, no ``.claude/**``
mutation, no secret values.

Prose contract: ``docs/operations/HARNESS_SEAT_CONTRACT.md``.
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

CHECK_NAME = "harness_seat_contract"
CONTRACT = "specs/v2/007-harness-seat-contract/spec.ce.yml#seat_contract"
SCHEMA_PATH = "schemas/harness-seat-contract.schema.yaml"
KEY = "seat_contract"
SCOPE_TOKEN = "harness-seat-contract"
PROTOCOL_DOC = "HARNESS_SEAT_CONTRACT.md"
SPEC_FEATURE_DIR = "007-harness-seat-contract"

CODE_SCHEMA = "VAL-SEAT-SCHEMA"
CODE_HARNESS = "VAL-SEAT-HARNESS"
CODE_POSTURE = "VAL-SEAT-POSTURE"
CODE_PROHIBITED = "VAL-SEAT-PROHIBITED"
CODE_FULL_PERMISSION = "VAL-SEAT-FULL-PERMISSION"
CODE_PERMISSION_FLAG = "VAL-SEAT-PERMISSION-FLAG"
CODE_HOOKPACK = "VAL-SEAT-HOOKPACK"
CODE_ROLE = "VAL-SEAT-ROLE"
CODE_MODE = "VAL-SEAT-MODE"
CODE_SECRET = "VAL-SEAT-SECRET"
CODE_NO_INLINE = "VAL-SEAT-NO-INLINE"

HARNESSES = frozenset({"claude_code", "codex", "hermes", "openclaw"})
# The genuinely posture-DEFEATING modes a governed seat MUST refuse (CLAUDE_CODE_
# CONTROLLER_SEAT_CONTRACT.md §5). full_permission_mode is NOT here — it is sanctioned.
REQUIRED_REFUSED_MODES = frozenset({"bare", "print_headless", "background_agents", "remote_control", "settings_local_weakening"})
# Harness-specific full-permission flags CE knows today (extended per harness by G2.007.1).
HARNESS_FULL_PERMISSION_FLAGS = {"claude_code": "--dangerously-skip-permissions", "codex": "--yolo"}

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
            errors.append(make_error(CODE_NO_INLINE, path, _pointer(("line", line_no)), "harness-seat-contract metadata belongs in sidecars/examples, not Markdown bodies", CONTRACT))
    return errors


def _validate_required_hook_pack(rec: dict[str, Any], path: Path, pre: tuple[Any, ...]) -> list[ValidationError]:
    """The required hook-pack must be a ring_1 defeasible hook_pack (G2.006.0 vocabulary)."""
    errors: list[ValidationError] = []
    hp = rec.get("required_hook_pack")
    if not isinstance(hp, dict):
        errors.append(make_error(CODE_HOOKPACK, path, _pointer(pre + ("required_hook_pack",)), "seat_contract must declare a required_hook_pack (a ring_1 defeasible hook_pack extension_contract)", CONTRACT))
        return errors
    if _normalize_token(hp.get("extension_kind", "")) != "hook_pack":
        errors.append(make_error(CODE_HOOKPACK, path, _pointer(pre + ("required_hook_pack", "extension_kind")), "required_hook_pack.extension_kind must be hook_pack", CONTRACT))
    if _normalize_token(hp.get("ring", "")) != "ring_1":
        errors.append(make_error(CODE_HOOKPACK, path, _pointer(pre + ("required_hook_pack", "ring")), "required_hook_pack must occupy ring_1 (RUNTIME/DEFEASIBLE)", CONTRACT))
    hooks = hp.get("hooks") if isinstance(hp.get("hooks"), list) else []
    if not hooks:
        errors.append(make_error(CODE_HOOKPACK, path, _pointer(pre + ("required_hook_pack", "hooks")), "required_hook_pack must declare at least one hook", CONTRACT))
    for idx, hook in enumerate(hooks):
        if not isinstance(hook, dict):
            continue
        if hook.get("defeasible") is not True:
            errors.append(make_error(CODE_HOOKPACK, path, _pointer(pre + ("required_hook_pack", "hooks", idx, "defeasible")), "ring_1 hooks must be defeasible: true", CONTRACT))
        if _normalize_token(hook.get("failure_posture", "")) != "fail_open":
            errors.append(make_error(CODE_HOOKPACK, path, _pointer(pre + ("required_hook_pack", "hooks", idx, "failure_posture")), "ring_1 in-band hooks must fail_open", CONTRACT))
    return errors


def validate_seat_contract_file(path: Path) -> list[ValidationError]:
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
            errors.append(make_error(CODE_SCHEMA, path, "", "scoped YAML files must declare a seat_contract mapping", SCHEMA_PATH))
        return errors
    rec = data[KEY]
    pre = (KEY,)

    harness = _normalize_token(rec.get("harness", ""))
    if harness not in HARNESSES:
        errors.append(make_error(CODE_HARNESS, path, _pointer(pre + ("harness",)), "harness must be one of claude_code, codex, hermes, openclaw", CONTRACT))

    # --- required posture (§4) ---
    if _normalize_token(rec.get("enforcement_ring", "")) != "ring_0":
        errors.append(make_error(CODE_POSTURE, path, _pointer(pre + ("enforcement_ring",)), "a seat-contract is enforced at the HARD Ring 0 floor; enforcement_ring must be ring_0", CONTRACT))
    posture = rec.get("launch_posture") if isinstance(rec.get("launch_posture"), dict) else {}
    ppre = pre + ("launch_posture",)
    if posture.get("model_pin") is not True:
        errors.append(make_error(CODE_POSTURE, path, _pointer(ppre + ("model_pin",)), "launch_posture.model_pin must be true (explicit model pin; no implicit default)", CONTRACT))
    if posture.get("strict_mcp_config") is not True:
        errors.append(make_error(CODE_POSTURE, path, _pointer(ppre + ("strict_mcp_config",)), "launch_posture.strict_mcp_config must be true", CONTRACT))
    if _normalize_token(posture.get("terminal_visibility", "")) != "operator_visible":
        errors.append(make_error(CODE_POSTURE, path, _pointer(ppre + ("terminal_visibility",)), "launch_posture.terminal_visibility must be operator_visible (no hidden/headless seat)", CONTRACT))
    sources = posture.get("setting_sources") if isinstance(posture.get("setting_sources"), list) else []
    source_tokens = {_normalize_token(s) for s in sources}
    if "project" not in source_tokens or "local" in source_tokens:
        errors.append(make_error(CODE_POSTURE, path, _pointer(ppre + ("setting_sources",)), "launch_posture.setting_sources must include 'project' and exclude 'local' (settings.local.json must not weaken the posture)", CONTRACT))

    # --- refused-modes floor (§5; posture-defeating set) ---
    refused = {_normalize_token(m) for m in (rec.get("refused_modes") if isinstance(rec.get("refused_modes"), list) else [])}
    missing = REQUIRED_REFUSED_MODES - refused
    if missing:
        errors.append(make_error(CODE_PROHIBITED, path, _pointer(pre + ("refused_modes",)), f"refused_modes must refuse every posture-defeating mode; missing: {sorted(missing)}", CONTRACT))

    # --- full-permission-mode invariant (headline) + harness flag binding ---
    full_perm = posture.get("full_permission_mode")
    if full_perm is True and posture.get("ring0_hook_pack_confirmed") is not True:
        errors.append(make_error(CODE_FULL_PERMISSION, path, _pointer(ppre + ("full_permission_mode",)), "full_permission_mode requires ring0_hook_pack_confirmed: true (the Ring 0 hook-pack confirmation is the safety substitute for per-action approval)", CONTRACT))
    if full_perm is True and harness in HARNESS_FULL_PERMISSION_FLAGS:
        expected = HARNESS_FULL_PERMISSION_FLAGS[harness]
        if str(posture.get("permission_mode_flag", "")).strip() != expected:
            errors.append(make_error(CODE_PERMISSION_FLAG, path, _pointer(ppre + ("permission_mode_flag",)), f"for harness {harness!r}, full_permission_mode must declare permission_mode_flag {expected!r}", CONTRACT))

    # --- required hook-pack (reuse G2.006.0 vocabulary) ---
    errors.extend(_validate_required_hook_pack(rec, path, pre))

    # --- role / mode floors ---
    role = _normalize_token(rec.get("emitting_role", ""))
    if role not in EMITTING_ROLES or role in FORBIDDEN_ACTIVE_ROLES:
        errors.append(make_error(CODE_ROLE, path, _pointer(pre + ("emitting_role",)), "emitting_role must be a canonical non-ratifying role; agent_ratifier/source are reserved-inactive and may not emit", CONTRACT))
    if _normalize_token(rec.get("operating_mode", "")) not in OPERATING_MODES:
        errors.append(make_error(CODE_MODE, path, _pointer(pre + ("operating_mode",)), "operating_mode must be one of strict, auto, transcendence", CONTRACT))

    if _contains_secret(rec):
        errors.append(make_error(CODE_SECRET, path, _pointer(pre), "seat_contract must not carry secret/credential values; reference flags/validators by name only", CONTRACT))
    return errors


@register(
    CHECK_NAME,
    [CODE_SCHEMA, CODE_HARNESS, CODE_POSTURE, CODE_PROHIBITED, CODE_FULL_PERMISSION, CODE_PERMISSION_FLAG, CODE_HOOKPACK, CODE_ROLE, CODE_MODE, CODE_SECRET, CODE_NO_INLINE],
)
def run_harness_seat_contract(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for file_path in _iter_scanned_files(paths):
        errors.extend(validate_seat_contract_file(file_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
