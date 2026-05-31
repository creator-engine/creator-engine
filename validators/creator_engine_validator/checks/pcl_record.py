"""G2.004.0 PCL (Project Coordination Ledger) record substrate validator.

PCL is the per-repo authoritative coordination ledger. This check validates the
shape-only substrate: content-addressed, hash-chained records discriminated by
``record_kind``. PCL records never ratify; ``agent_ratifier`` stays
reserved-inactive. ``event_block_pointer`` records reference a CE-event block by
an opaque 64-hex ``content_hash`` value only — no CE-event code/schema import,
no runtime dependency. Live ``ce pcl`` append/verify runtime and ``.ce/pcl/``
live writes remain deferred to G2.004.1.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "pcl_record"
CONTRACT = "specs/v2/004-pcl-substrate/spec.ce.yml#pcl_record"
SCHEMA_PATH = "schemas/pcl-record.schema.yaml"

CODE_SCHEMA = "VAL-PCL-SCHEMA"
CODE_CONTENT_ADDRESS = "VAL-PCL-CONTENT-ADDRESS"
CODE_CHAIN_LINK = "VAL-PCL-CHAIN-LINK"
CODE_RECORD_KIND = "VAL-PCL-RECORD-KIND"
CODE_ROLE_FLOOR = "VAL-PCL-ROLE-FLOOR"
CODE_MODE_ENUM = "VAL-PCL-MODE-ENUM"
CODE_POINTER_SHAPE = "VAL-PCL-POINTER-SHAPE"
CODE_SIGNATURE_SHAPE = "VAL-PCL-SIGNATURE-SHAPE"
CODE_NO_INLINE = "VAL-PCL-NO-INLINE"
CODE_WRITE_FREEZE = "VAL-PCL-WRITE-FREEZE"

OPERATING_MODES = frozenset({"strict", "auto", "transcendence"})
EMITTING_ROLES = frozenset({"operator", "controller", "architect", "implementer", "reviewer", "verification", "agent_reviewer"})
FORBIDDEN_ACTIVE_ROLES = frozenset({"agent_ratifier", "source"})
RECORD_KINDS = frozenset(
    {
        "lane_claim",
        "lane_release",
        "gate_opened",
        "gate_closed",
        "completion_report_pointer",
        "event_block_pointer",
        "directive_pack_published",
        "identity_assertion",
    }
)
EVENT_BLOCK_POINTER_KIND = "event_block_pointer"
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
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
    if "pcl-record" in parts:
        return True
    if path.name == "PCL_PROTOCOL.md":
        return True
    for i in range(len(parts) - 2):
        if parts[i] == "specs" and parts[i + 1] == "v2" and parts[i + 2] == "004-pcl-substrate":
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


def _canonical_hash(record: dict[str, Any]) -> str:
    material = {k: v for k, v in record.items() if k not in {"content_hash", "signature"}}
    raw = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _records_from_data(data: Any, path: Path) -> tuple[list[dict[str, Any]], list[ValidationError]]:
    if not isinstance(data, dict):
        return [], [_err(CODE_SCHEMA, path, (), "PCL files must be YAML mappings", SCHEMA_PATH)]
    if "pcl_record" in data:
        record = data["pcl_record"]
        if isinstance(record, dict):
            return [record], []
        return [], [_err(CODE_SCHEMA, path, ("pcl_record",), "pcl_record must be a mapping", SCHEMA_PATH)]
    if "pcl_chain" in data:
        chain = data["pcl_chain"]
        if not isinstance(chain, list):
            return [], [_err(CODE_SCHEMA, path, ("pcl_chain",), "pcl_chain must be a list", SCHEMA_PATH)]
        errors = []
        records = []
        for idx, item in enumerate(chain):
            if not isinstance(item, dict):
                errors.append(_err(CODE_SCHEMA, path, ("pcl_chain", idx), "PCL chain entries must be mappings", SCHEMA_PATH))
            else:
                records.append(item)
        return records, errors
    return [], [_err(CODE_SCHEMA, path, (), "scoped PCL YAML files must declare pcl_record or pcl_chain", SCHEMA_PATH)]


def _validate_signature(record: dict[str, Any], path: Path, prefix: tuple[Any, ...]) -> list[ValidationError]:
    sig = record.get("signature")
    if not isinstance(sig, dict):
        return [_err(CODE_SIGNATURE_SHAPE, path, prefix + ("signature",), "signature must be a shape-only mapping")]
    required = {"scheme", "key_id", "value"}
    missing = sorted(required - set(sig))
    errors: list[ValidationError] = []
    if missing:
        errors.append(_err(CODE_SIGNATURE_SHAPE, path, prefix + ("signature",), f"signature missing required shape fields: {', '.join(missing)}"))
    if _normalize_token(sig.get("value", "")) not in {"reserved_inactive", "reserved_inactive".replace("_", "-")}:
        errors.append(_err(CODE_SIGNATURE_SHAPE, path, prefix + ("signature", "value"), "signature value must remain reserved-inactive in G2.004.0"))
    return errors


def _subtree_contains_hermes_pcl_write(value: Any) -> bool:
    if isinstance(value, str):
        text = value.strip()
        return text.startswith(".hermes/pcl") or "/.hermes/pcl" in text or (text.startswith(".hermes/") and "pcl" in text)
    if isinstance(value, dict):
        return any(_subtree_contains_hermes_pcl_write(k) or _subtree_contains_hermes_pcl_write(v) for k, v in value.items())
    if isinstance(value, list):
        return any(_subtree_contains_hermes_pcl_write(v) for v in value)
    return False


def _validate_pointer(record: dict[str, Any], path: Path, prefix: tuple[Any, ...]) -> list[ValidationError]:
    body = record.get("body")
    if not isinstance(body, dict):
        return [_err(CODE_POINTER_SHAPE, path, prefix + ("body",), "event_block_pointer records must carry a body mapping")]
    pointer = body.get("ce_event_content_hash")
    if not isinstance(pointer, str) or not _HASH_RE.match(pointer):
        return [
            _err(
                CODE_POINTER_SHAPE,
                path,
                prefix + ("body", "ce_event_content_hash"),
                "event_block_pointer body must reference a CE-event block by an opaque 64-hex ce_event_content_hash",
            )
        ]
    return []


def _validate_records(records: list[dict[str, Any]], path: Path, *, root_key: str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    previous_hash: str | None = None
    for idx, record in enumerate(records):
        prefix = (root_key, idx) if root_key == "pcl_chain" else (root_key,)
        kind = _normalize_token(record.get("record_kind", ""))
        if kind not in RECORD_KINDS:
            errors.append(_err(CODE_RECORD_KIND, path, prefix + ("record_kind",), "record_kind must be one of the canonical PCL record kinds"))
        role = _normalize_token(record.get("emitting_role", ""))
        if role not in EMITTING_ROLES or role in FORBIDDEN_ACTIVE_ROLES:
            errors.append(_err(CODE_ROLE_FLOOR, path, prefix + ("emitting_role",), "emitting_role must be a canonical non-ratifying role; agent_ratifier is reserved-inactive and PCL records never ratify"))
        mode = _normalize_token(record.get("operating_mode", ""))
        if mode not in OPERATING_MODES:
            errors.append(_err(CODE_MODE_ENUM, path, prefix + ("operating_mode",), "operating_mode must be one of strict, auto, transcendence"))
        expected = _canonical_hash(record)
        if record.get("content_hash") != expected:
            errors.append(_err(CODE_CONTENT_ADDRESS, path, prefix + ("content_hash",), "content_hash must equal SHA256 of canonical record material excluding content_hash and signature"))
        parent = record.get("parent_hash")
        if idx == 0:
            if parent is not None:
                errors.append(_err(CODE_CHAIN_LINK, path, prefix + ("parent_hash",), "genesis record parent_hash must be null"))
        elif parent != previous_hash:
            errors.append(_err(CODE_CHAIN_LINK, path, prefix + ("parent_hash",), "non-genesis parent_hash must match prior record content_hash"))
        previous_hash = str(record.get("content_hash") or "")
        errors.extend(_validate_signature(record, path, prefix))
        if kind == EVENT_BLOCK_POINTER_KIND:
            errors.extend(_validate_pointer(record, path, prefix))
        if _subtree_contains_hermes_pcl_write(record.get("body")):
            errors.append(_err(CODE_WRITE_FREEZE, path, prefix + ("body",), "G2.004.0 PCL records must not target .hermes/pcl as active v2 state"))
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
        if key in {"pcl_record", "pcl_chain"}:
            errors.append(_err(CODE_NO_INLINE, path, ("line", line_no), "PCL record metadata belongs in sidecars/examples, not Markdown bodies"))
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
    records, record_errors = _records_from_data(data, path)
    errors.extend(record_errors)
    root_key = "pcl_chain" if isinstance(data, dict) and "pcl_chain" in data else "pcl_record"
    if records:
        errors.extend(_validate_records(records, path, root_key=root_key))
    return errors


@register(
    CHECK_NAME,
    [
        CODE_SCHEMA,
        CODE_CONTENT_ADDRESS,
        CODE_CHAIN_LINK,
        CODE_RECORD_KIND,
        CODE_ROLE_FLOOR,
        CODE_MODE_ENUM,
        CODE_POINTER_SHAPE,
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
