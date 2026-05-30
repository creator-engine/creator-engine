"""G2.003.0 CE-event signed-block substrate validator."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "ce_event_block"
CONTRACT = "specs/v2/003-ce-event-protocol/spec.ce.yml#ce_event_block"
SCHEMA_PATH = "schemas/ce-event-block.schema.yaml"

CODE_SCHEMA = "VAL-CE-EVENT-SCHEMA"
CODE_CONTENT_ADDRESS = "VAL-CE-EVENT-CONTENT-ADDRESS"
CODE_CHAIN_LINK = "VAL-CE-EVENT-CHAIN-LINK"
CODE_ROLE_FLOOR = "VAL-CE-EVENT-ROLE-FLOOR"
CODE_MODE_ENUM = "VAL-CE-EVENT-MODE-ENUM"
CODE_SIGNATURE_SHAPE = "VAL-CE-EVENT-SIGNATURE-SHAPE"
CODE_NO_INLINE = "VAL-CE-EVENT-NO-INLINE"
CODE_WRITE_FREEZE = "VAL-CE-EVENT-WRITE-FREEZE"

OPERATING_MODES = frozenset({"strict", "auto", "transcendence"})
EMITTING_ROLES = frozenset({"operator", "controller", "architect", "implementer", "reviewer", "verification", "agent_reviewer"})
FORBIDDEN_ACTIVE_ROLES = frozenset({"agent_ratifier", "source"})
_SCANNED_YAML_SUFFIXES = {".yml", ".yaml"}
_SCANNED_MARKDOWN_SUFFIXES = {".md", ".markdown"}


def _normalize_token(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_")


def _pointer(parts: tuple[Any, ...]) -> str:
    rendered = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(rendered) if rendered else "/"


def _err(code: str, path: Path, parts: tuple[Any, ...], message: str, contract: str = CONTRACT) -> ValidationError:
    return make_error(code, path, _pointer(parts), message, contract)


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _path_in_scope(path: Path) -> bool:
    parts = path.parts
    if "ce-event-block" in parts:
        return True
    if path.name == "CE_EVENT_PROTOCOL.md":
        return True
    for i in range(len(parts) - 2):
        if parts[i] == "specs" and parts[i + 1] == "v2" and parts[i + 2] == "003-ce-event-protocol":
            return path.name == "spec.md"
    return False


def iter_scanned_files(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    suffixes = _SCANNED_YAML_SUFFIXES | _SCANNED_MARKDOWN_SUFFIXES
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


def _canonical_hash(block: dict[str, Any]) -> str:
    material = {k: v for k, v in block.items() if k not in {"content_hash", "signature"}}
    raw = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _blocks_from_data(data: Any, path: Path) -> tuple[list[dict[str, Any]], list[ValidationError]]:
    if not isinstance(data, dict):
        return [], [_err(CODE_SCHEMA, path, (), "CE-event files must be YAML mappings", SCHEMA_PATH)]
    if "ce_event_block" in data:
        block = data["ce_event_block"]
        if isinstance(block, dict):
            return [block], []
        return [], [_err(CODE_SCHEMA, path, ("ce_event_block",), "ce_event_block must be a mapping", SCHEMA_PATH)]
    if "ce_event_chain" in data:
        chain = data["ce_event_chain"]
        if not isinstance(chain, list):
            return [], [_err(CODE_SCHEMA, path, ("ce_event_chain",), "ce_event_chain must be a list", SCHEMA_PATH)]
        errors = []
        blocks = []
        for idx, item in enumerate(chain):
            if not isinstance(item, dict):
                errors.append(_err(CODE_SCHEMA, path, ("ce_event_chain", idx), "CE-event chain entries must be mappings", SCHEMA_PATH))
            else:
                blocks.append(item)
        return blocks, errors
    return [], [_err(CODE_SCHEMA, path, (), "scoped CE-event YAML files must declare ce_event_block or ce_event_chain", SCHEMA_PATH)]


def _validate_signature(block: dict[str, Any], path: Path, prefix: tuple[Any, ...]) -> list[ValidationError]:
    sig = block.get("signature")
    if not isinstance(sig, dict):
        return [_err(CODE_SIGNATURE_SHAPE, path, prefix + ("signature",), "signature must be a shape-only mapping")]
    required = {"scheme", "key_id", "value"}
    missing = sorted(required - set(sig))
    errors: list[ValidationError] = []
    if missing:
        errors.append(_err(CODE_SIGNATURE_SHAPE, path, prefix + ("signature",), f"signature missing required shape fields: {', '.join(missing)}"))
    if _normalize_token(sig.get("value", "")) not in {"reserved_inactive", "reserved_inactive".replace("_", "-")}:
        errors.append(_err(CODE_SIGNATURE_SHAPE, path, prefix + ("signature", "value"), "signature value must remain reserved-inactive in G2.003.0"))
    return errors


def _subtree_contains_hermes_event_write(value: Any) -> bool:
    if isinstance(value, str):
        text = value.strip()
        return text.startswith(".hermes/ce-events") or "/.hermes/ce-events" in text or text.startswith(".hermes/") and "ce-events" in text
    if isinstance(value, dict):
        return any(_subtree_contains_hermes_event_write(k) or _subtree_contains_hermes_event_write(v) for k, v in value.items())
    if isinstance(value, list):
        return any(_subtree_contains_hermes_event_write(v) for v in value)
    return False


def _validate_blocks(blocks: list[dict[str, Any]], path: Path, *, root_key: str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    previous_hash: str | None = None
    for idx, block in enumerate(blocks):
        prefix = (root_key, idx) if root_key == "ce_event_chain" else (root_key,)
        role = _normalize_token(block.get("emitting_role", ""))
        if role not in EMITTING_ROLES or role in FORBIDDEN_ACTIVE_ROLES:
            errors.append(_err(CODE_ROLE_FLOOR, path, prefix + ("emitting_role",), "emitting_role must be a canonical non-ratifying role; agent_ratifier is reserved-inactive"))
        mode = _normalize_token(block.get("operating_mode", ""))
        if mode not in OPERATING_MODES:
            errors.append(_err(CODE_MODE_ENUM, path, prefix + ("operating_mode",), "operating_mode must be one of strict, auto, transcendence"))
        expected = _canonical_hash(block)
        if block.get("content_hash") != expected:
            errors.append(_err(CODE_CONTENT_ADDRESS, path, prefix + ("content_hash",), "content_hash must equal SHA256 of canonical block material excluding content_hash and signature"))
        parent = block.get("parent_hash")
        if idx == 0:
            if parent is not None:
                errors.append(_err(CODE_CHAIN_LINK, path, prefix + ("parent_hash",), "genesis block parent_hash must be null"))
        elif parent != previous_hash:
            errors.append(_err(CODE_CHAIN_LINK, path, prefix + ("parent_hash",), "non-genesis parent_hash must match prior block content_hash"))
        previous_hash = str(block.get("content_hash") or "")
        errors.extend(_validate_signature(block, path, prefix))
        if _subtree_contains_hermes_event_write(block.get("event")):
            errors.append(_err(CODE_WRITE_FREEZE, path, prefix + ("event",), "G2.003.0 CE-event blocks must not target .hermes/ce-events as active v2 state"))
    return errors


def validate_markdown_file(path: Path) -> list[ValidationError]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [_err(CODE_NO_INLINE, path, (), f"failed to read markdown: {exc}")]
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
                marker = stripped[3:].strip().lower()
                in_fence = True
                fence_is_yaml = marker in {"yaml", "yml"}
            else:
                in_fence = False
                fence_is_yaml = False
            continue
        if not fence_is_yaml:
            continue
        key = stripped.split(":", 1)[0].strip()
        if key in {"ce_event_block", "ce_event_chain"}:
            errors.append(_err(CODE_NO_INLINE, path, ("line", line_no), "CE-event block metadata belongs in sidecars/examples, not Markdown bodies"))
    return errors


def validate_file(path: Path) -> list[ValidationError]:
    if path.suffix.lower() in _SCANNED_MARKDOWN_SUFFIXES:
        return validate_markdown_file(path)
    try:
        data = load_yaml(path)
    except LoaderError as exc:
        return [_err(CODE_SCHEMA, path, (), str(exc), SCHEMA_PATH)]
    errors: list[ValidationError] = []
    try:
        errors.extend(validate_with_schema(data, SCHEMA_PATH, path, code=CODE_SCHEMA, contract=SCHEMA_PATH))
    except Exception as exc:
        errors.append(_err(CODE_SCHEMA, path, (), f"schema validation failed: {exc}", SCHEMA_PATH))
    blocks, block_errors = _blocks_from_data(data, path)
    errors.extend(block_errors)
    root_key = "ce_event_chain" if isinstance(data, dict) and "ce_event_chain" in data else "ce_event_block"
    if blocks:
        errors.extend(_validate_blocks(blocks, path, root_key=root_key))
    return errors


@register(
    CHECK_NAME,
    [
        CODE_SCHEMA,
        CODE_CONTENT_ADDRESS,
        CODE_CHAIN_LINK,
        CODE_ROLE_FLOOR,
        CODE_MODE_ENUM,
        CODE_SIGNATURE_SHAPE,
        CODE_NO_INLINE,
        CODE_WRITE_FREEZE,
    ],
)
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for file_path in iter_scanned_files(paths):
        errors.extend(validate_file(file_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
