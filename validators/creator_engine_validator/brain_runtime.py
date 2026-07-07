"""Knowledge-SSOT assertion ledger runtime.

The versioned authoritative assertion ledger lives in the repo and is copied
deterministically into the local runtime ledger under ``.ce/state`` at
bootstrap. It deliberately stops at the SSOT layer: no datastore, no MCP server,
no recall/vector path, and no MEMORY migration shim.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import yaml

from ._versions import V3_LOCAL_STATE_ROOT
from .loader import LoaderError, load_yaml
from .reporting import ValidationError, make_error
from .runtime_evidence_spine import (
    CONTENT_HASH_FIELD,
    GENESIS_PREV_HASH,
    canonical_content_hash,
)
from .schema import validate_with_schema

SCHEMA_PATH = "schemas/brain-assertion.schema.yaml"
CONTRACT = "schemas/brain-assertion.schema.yaml"
LEDGER_KIND = "brain-assertion-ledger"
LEDGER_RECORD_TYPE = "brain_assertion_ledger"
ASSERTION_KIND = "brain-assertion"
ASSERTION_RECORD_TYPE = "brain_assertion"
DECISION_KIND = "brain-decision"
DECISION_RECORD_TYPE = "brain_decision"
LESSON_KIND = "brain-lesson"
LESSON_RECORD_TYPE = "brain_lesson"
HYDRATION_KIND = "ce-brain-hydration-contract"
SCHEMA_VERSION = "1"
LEDGER_RELATIVE_PATH = Path("brain") / "assertions.yaml"
AUTHORITATIVE_LEDGER_RELATIVE_PATH = Path(".ce") / "brain" / "assertions.yaml"
ASSERTION_TYPES = frozenset({"capability", "convention", "decision", "gotcha"})
VERIFICATION_METHOD_TYPES = frozenset({"probe", "static", "manual-attested"})
DEFAULT_ASSERTION_TYPE = "decision"

CODE_SCHEMA = "brain_assertion_schema_violation"
CODE_CONTENT_ADDRESS = "brain_assertion_content_address"
CODE_CHAIN_LINK = "brain_assertion_chain_link"
CODE_SEQUENCE = "brain_assertion_sequence_break"
CODE_FORBIDDEN_IDENTIFIER = "brain_assertion_forbidden_identifier"
CODE_SUPERSEDE_TARGET = "brain_assertion_supersede_target"
CODE_DUPLICATE_ACTIVE = "brain_assertion_duplicate_active"
CODE_UNKNOWN = "brain_assertion_unknown"

_ID_RE = re.compile(r"^brain-assertion-[a-z0-9][a-z0-9-]{3,96}$")
_DECISION_ID_RE = re.compile(r"^brain-decision-[a-z0-9][a-z0-9-]{3,96}$")
_LESSON_ID_RE = re.compile(r"^brain-lesson-[a-z0-9][a-z0-9-]{3,96}$")
_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_FORBIDDEN_KEYS = {
    "account",
    "account_id",
    "credential",
    "credentials",
    "host",
    "host_id",
    "hostname",
    "installation_id",
    "password",
    "port",
    "secret",
    "token",
}
_PROBE_EVIDENCE_PREFIX = "probe:"

Writer = Callable[[Path, str], None]


class BrainRuntimeError(Exception):
    code = "CE-BRAIN-ERROR"


class BrainLedgerInvalid(BrainRuntimeError):
    code = "CE-BRAIN-LEDGER-INVALID"

    def __init__(self, errors: Iterable[ValidationError] | str):
        if isinstance(errors, str):
            self.errors: tuple[ValidationError, ...] = ()
            super().__init__(errors)
            return
        self.errors = tuple(errors)
        super().__init__("brain assertion ledger failed validation")


class BrainAssertionRefused(BrainLedgerInvalid):
    code = "CE-BRAIN-ASSERTION-REFUSED"


@dataclass(frozen=True)
class AssertResult:
    ledger_path: Path
    record: dict[str, Any]
    sequence: int
    content_hash: str
    prev_hash: str
    ledger_text: str


@dataclass(frozen=True)
class CorrectResult:
    ledger_path: Path
    superseded_record: dict[str, Any]
    record: dict[str, Any]
    ledger_text: str


@dataclass(frozen=True)
class MemoryAppendResult:
    ledger_path: Path
    record: dict[str, Any]
    sequence: int
    content_hash: str
    prev_hash: str
    ledger_text: str


@dataclass(frozen=True)
class CheckResult:
    status: str
    record: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "record": self.record}


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    ledger_path: Path
    summary: dict[str, Any]
    errors: tuple[str, ...]


@dataclass(frozen=True)
class SyncResult:
    authoritative_path: Path
    ledger_path: Path
    record_count: int
    active_count: int
    head_content_hash: str | None
    updated: bool
    authoritative_exists: bool


class _NoAliasSafeDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):  # type: ignore[override]
        return True


def ledger_path(state_root: Path | str = V3_LOCAL_STATE_ROOT) -> Path:
    return Path(state_root) / LEDGER_RELATIVE_PATH


def repo_root_from_state_root(state_root: Path | str = V3_LOCAL_STATE_ROOT) -> Path:
    root = Path(state_root)
    if root.name == "state" and root.parent.name == ".ce":
        return root.parent.parent
    return Path(".")


def authoritative_ledger_path(repo_root: Path | str = Path(".")) -> Path:
    return Path(repo_root) / AUTHORITATIVE_LEDGER_RELATIVE_PATH


def _default_write(path: Path, text: str) -> None:  # pragma: no cover - live writer
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f"{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}"
    tmp.write_text(text, encoding="utf-8")
    tmp.rename(path)


def _stable_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise BrainAssertionRefused("brain assertion values must be JSON-compatible") from exc


def _stable_copy(value: Any) -> Any:
    return json.loads(_stable_json(value))


def _normalize_claim(claim: Any) -> dict[str, Any]:
    if not isinstance(claim, dict) or not claim:
        raise BrainAssertionRefused("claim must be a non-empty mapping")
    return _stable_copy(claim)


def _normalize_scope(scope: Any) -> str | dict[str, Any]:
    if isinstance(scope, str) and scope:
        return scope
    if isinstance(scope, dict) and scope:
        return _stable_copy(scope)
    raise BrainAssertionRefused("scope must be a non-empty string or mapping")


def _statement_from_claim(claim: dict[str, Any]) -> str:
    subject = claim.get("subject")
    predicate = claim.get("predicate")
    obj = claim.get("object")
    if all(isinstance(part, str) and part for part in (subject, predicate, obj)):
        return f"{subject} {predicate} {obj}"
    fact = claim.get("fact")
    if isinstance(fact, str) and fact:
        return fact
    return _stable_json(claim)


def _normalize_statement(statement: str | None, claim: dict[str, Any]) -> str:
    normalized = _statement_from_claim(claim) if statement is None else statement
    if not isinstance(normalized, str) or not normalized.strip():
        raise BrainAssertionRefused("statement must be a non-empty string")
    normalized = normalized.strip()
    if len(normalized) > 1024:
        raise BrainAssertionRefused("statement must be 1024 characters or fewer")
    return normalized


def _normalize_memory_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BrainAssertionRefused(f"{field} must be a non-empty string")
    normalized = value.strip()
    if len(normalized) > 2048:
        raise BrainAssertionRefused(f"{field} must be 2048 characters or fewer")
    return normalized


def _normalize_authority(value: str) -> str:
    normalized = _normalize_memory_text(value, "authority")
    if len(normalized) > 256:
        raise BrainAssertionRefused("authority must be 256 characters or fewer")
    return normalized


def _normalize_date(value: str) -> str:
    if not isinstance(value, str) or not _DATE_RE.match(value):
        raise BrainAssertionRefused("date must use YYYY-MM-DD")
    return value


def _normalize_assertion_type(assertion_type: str | None) -> str:
    normalized = DEFAULT_ASSERTION_TYPE if assertion_type is None else assertion_type
    if normalized not in ASSERTION_TYPES:
        raise BrainAssertionRefused(
            "assertion type must be one of capability, convention, decision, or gotcha"
        )
    return normalized


def _normalize_verification_method(value: Any, evidence_ref: str) -> dict[str, Any]:
    if value is None:
        if evidence_ref.startswith(_PROBE_EVIDENCE_PREFIX):
            probe_name = evidence_ref.removeprefix(_PROBE_EVIDENCE_PREFIX)
            if not probe_name:
                raise BrainAssertionRefused("probe evidence_ref must include a probe name")
            return {"evidence_ref": evidence_ref, "probe": probe_name, "type": "probe"}
        return {"evidence_ref": evidence_ref, "type": "static"}
    if isinstance(value, str):
        value = {"type": value}
    if not isinstance(value, dict):
        raise BrainAssertionRefused("verification_method must be a mapping or method name")
    normalized = _stable_copy(value)
    method_type = normalized.get("type")
    if method_type not in VERIFICATION_METHOD_TYPES:
        raise BrainAssertionRefused("verification_method.type must be probe, static, or manual-attested")
    method_evidence = normalized.get("evidence_ref", evidence_ref)
    if not isinstance(method_evidence, str) or not method_evidence or "://" in method_evidence:
        raise BrainAssertionRefused("verification_method.evidence_ref must be a non-empty local or opaque reference")
    if method_type == "probe":
        probe_name = normalized.get("probe")
        if probe_name is None and method_evidence.startswith(_PROBE_EVIDENCE_PREFIX):
            probe_name = method_evidence.removeprefix(_PROBE_EVIDENCE_PREFIX)
        if not isinstance(probe_name, str) or not probe_name:
            raise BrainAssertionRefused("probe verification_method requires a non-empty probe")
        normalized["probe"] = probe_name
        normalized["evidence_ref"] = method_evidence
    else:
        normalized.pop("probe", None)
        normalized["evidence_ref"] = method_evidence
    return normalized


def _assertion_id(seed: dict[str, Any]) -> str:
    digest = hashlib.sha256(_stable_json(seed).encode("utf-8")).hexdigest()
    return f"brain-assertion-{digest[:24]}"


def _decision_id(seed: dict[str, Any]) -> str:
    digest = hashlib.sha256(_stable_json(seed).encode("utf-8")).hexdigest()
    return f"brain-decision-{digest[:24]}"


def _lesson_id(seed: dict[str, Any]) -> str:
    digest = hashlib.sha256(_stable_json(seed).encode("utf-8")).hexdigest()
    return f"brain-lesson-{digest[:24]}"


def _validate_id(value: str) -> None:
    if not isinstance(value, str) or not _ID_RE.match(value):
        raise BrainAssertionRefused("assertion id does not match the brain-assertion id shape")


def _validate_decision_id(value: str) -> None:
    if not isinstance(value, str) or not _DECISION_ID_RE.match(value):
        raise BrainAssertionRefused("decision id does not match the brain-decision id shape")


def _validate_lesson_id(value: str) -> None:
    if not isinstance(value, str) or not _LESSON_ID_RE.match(value):
        raise BrainAssertionRefused("lesson id does not match the brain-lesson id shape")


def _claim_key(scope: Any, claim: dict[str, Any]) -> str:
    return hashlib.sha256(_stable_json({"scope": scope, "claim": claim}).encode("utf-8")).hexdigest()


def _ledger_doc(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "kind": LEDGER_KIND,
        "record_type": LEDGER_RECORD_TYPE,
        "schema_version": SCHEMA_VERSION,
        "records": [copy.deepcopy(record) for record in records],
    }


def serialize_ledger(records: Sequence[dict[str, Any]]) -> str:
    return yaml.dump(
        _ledger_doc(records),
        Dumper=_NoAliasSafeDumper,
        sort_keys=True,
        allow_unicode=False,
        default_flow_style=False,
    )


def _copy_mapping_records(records: Sequence[Any], path: Path | str) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    errors: list[ValidationError] = []
    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(_err(CODE_SCHEMA, path, ("records", idx), "brain assertion ledger records must be mappings"))
        else:
            copied.append(copy.deepcopy(record))
    if errors:
        raise BrainLedgerInvalid(errors)
    return copied


def _records_from_doc(data: Any, path: Path | str) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        raise BrainLedgerInvalid("brain assertion ledger must be a YAML mapping")
    records = data.get("records")
    if not isinstance(records, list):
        raise BrainLedgerInvalid("brain assertion ledger records must be a list")
    errors = validate_ledger_doc(data, path)
    if errors:
        raise BrainLedgerInvalid(errors)
    return _copy_mapping_records(records, path)


def load_ledger_text(text: str) -> list[dict[str, Any]]:
    data = yaml.safe_load(text)
    return _records_from_doc(data, "<brain-ledger-text>")


def load_records_from_path(path: Path | str) -> list[dict[str, Any]]:
    source = Path(path)
    try:
        data = load_yaml(source)
    except LoaderError as exc:
        raise BrainLedgerInvalid(str(exc)) from exc
    return _records_from_doc(data, source)


def load_records(state_root: Path | str = V3_LOCAL_STATE_ROOT) -> list[dict[str, Any]]:
    path = ledger_path(state_root)
    if not path.is_file():
        return []
    return load_records_from_path(path)


def load_authoritative_records(repo_root: Path | str = Path(".")) -> list[dict[str, Any]]:
    return load_records_from_path(authoritative_ledger_path(repo_root))


def authoritative_ledger_exists(repo_root: Path | str = Path(".")) -> bool:
    return authoritative_ledger_path(repo_root).is_file()


def sync_authoritative_ledger(
    *,
    state_root: Path | str = V3_LOCAL_STATE_ROOT,
    repo_root: Path | str | None = None,
    write: Writer | None = None,
) -> SyncResult:
    """Copy the repo-versioned assertion ledger into local runtime state.

    If the authoritative ledger is absent, the function is a no-op so tests and
    older checkouts that only provide a local ledger keep the prior behavior.
    When present, the authoritative ledger is schema/hash-chain validated before
    any runtime file is touched.
    """

    resolved_repo_root = repo_root_from_state_root(state_root) if repo_root is None else Path(repo_root)
    source = authoritative_ledger_path(resolved_repo_root)
    target = ledger_path(state_root)
    if not source.is_file():
        return SyncResult(
            authoritative_path=source,
            ledger_path=target,
            record_count=0,
            active_count=0,
            head_content_hash=None,
            updated=False,
            authoritative_exists=False,
        )

    records = load_records_from_path(source)
    _require_valid_records(records, source)
    source_text = source.read_text(encoding="utf-8")
    current_text = target.read_text(encoding="utf-8") if target.is_file() else None
    updated = current_text != source_text
    if updated:
        (write or _default_write)(target, source_text)
    latest, _indexes = _latest_by_id(records)
    active = [record for record in latest.values() if record.get("status") == "active"]
    return SyncResult(
        authoritative_path=source,
        ledger_path=target,
        record_count=len(records),
        active_count=len(active),
        head_content_hash=str(records[-1][CONTENT_HASH_FIELD]) if records else None,
        updated=updated,
        authoritative_exists=True,
    )


def records_equal_authoritative(
    *,
    state_root: Path | str = V3_LOCAL_STATE_ROOT,
    repo_root: Path | str | None = None,
) -> bool:
    resolved_repo_root = repo_root_from_state_root(state_root) if repo_root is None else Path(repo_root)
    source = authoritative_ledger_path(resolved_repo_root)
    target = ledger_path(state_root)
    if not source.is_file() or not target.is_file():
        return True
    return load_records_from_path(target) == load_records_from_path(source)


def _pointer(parts: tuple[Any, ...]) -> str:
    rendered = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(rendered) if rendered else "/"


def _err(code: str, path: Path | str, parts: tuple[Any, ...], message: str) -> ValidationError:
    return make_error(code, path, _pointer(parts), message, CONTRACT)


def _key_is_forbidden(key: Any) -> bool:
    token = str(key).strip().lower().replace("-", "_")
    parts = [p for p in re.split(r"[^a-z0-9]+", token) if p]
    if token in _FORBIDDEN_KEYS:
        return True
    return any(part in _FORBIDDEN_KEYS for part in parts)


def _forbidden_identifier_errors(value: Any, path: Path | str, prefix: tuple[Any, ...]) -> list[ValidationError]:
    errors: list[ValidationError] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_prefix = prefix + (key,)
            if _key_is_forbidden(key):
                errors.append(
                    _err(
                        CODE_FORBIDDEN_IDENTIFIER,
                        path,
                        key_prefix,
                        "brain assertion records must not carry host, port, credential, account, token, or secret identifiers",
                    )
                )
            errors.extend(_forbidden_identifier_errors(child, path, key_prefix))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            errors.extend(_forbidden_identifier_errors(child, path, prefix + (idx,)))
    return errors


def _validate_chain(records: Sequence[Any], path: Path | str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for idx, record in enumerate(records):
        prefix = ("records", idx)
        if not isinstance(record, dict):
            continue
        expected = canonical_content_hash(record)
        actual = record.get(CONTENT_HASH_FIELD)
        if actual != expected:
            errors.append(
                _err(
                    CODE_CONTENT_ADDRESS,
                    path,
                    prefix + (CONTENT_HASH_FIELD,),
                    "content_hash must equal SHA256 of canonical record material excluding content_hash",
                )
            )
        if record.get("sequence") != idx:
            errors.append(
                _err(CODE_SEQUENCE, path, prefix + ("sequence",), "sequence must be contiguous from 0")
            )
        prev_hash = record.get("prev_hash")
        if idx == 0:
            if prev_hash != GENESIS_PREV_HASH:
                errors.append(
                    _err(
                        CODE_CHAIN_LINK,
                        path,
                        prefix + ("prev_hash",),
                        "genesis prev_hash must be the all-zero SHA256 sentinel",
                    )
                )
        else:
            prior = records[idx - 1]
            expected_prev = prior.get(CONTENT_HASH_FIELD) if isinstance(prior, dict) else None
            if prev_hash != expected_prev:
                errors.append(
                    _err(
                        CODE_CHAIN_LINK,
                        path,
                        prefix + ("prev_hash",),
                        "non-genesis prev_hash must match the prior record content_hash",
                    )
                )
    return errors


def _latest_by_id(records: Sequence[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    latest: dict[str, dict[str, Any]] = {}
    indexes: dict[str, int] = {}
    for idx, record in enumerate(records):
        rid = record.get("id")
        if isinstance(rid, str):
            latest[rid] = record
            indexes[rid] = idx
    return latest, indexes


def _validate_current_view(records: Sequence[dict[str, Any]], path: Path | str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    latest, indexes = _latest_by_id(records)
    for idx, record in enumerate(records):
        if record.get("status") != "superseded":
            continue
        target_id = record.get("superseded_by")
        target = latest.get(str(target_id))
        if target is None:
            errors.append(
                _err(
                    CODE_SUPERSEDE_TARGET,
                    path,
                    ("records", idx, "superseded_by"),
                    "superseded assertion must point at an existing assertion id",
                )
            )
            continue

        seen = {str(record.get("id"))}
        current_id = str(target_id)
        current = target
        cycle_detected = False
        while current.get("status") == "superseded":
            if current_id in seen:
                errors.append(
                    _err(
                        CODE_SUPERSEDE_TARGET,
                        path,
                        ("records", idx, "superseded_by"),
                        "superseded assertion chain contains a cycle before reaching a currently active assertion",
                    )
                )
                cycle_detected = True
                break
            seen.add(current_id)
            next_id = current.get("superseded_by")
            current_id = str(next_id)
            next_record = latest.get(current_id)
            if next_record is None:
                break
            current = next_record

        if cycle_detected:
            continue
        if current.get("status") != "active":
            errors.append(
                _err(
                    CODE_SUPERSEDE_TARGET,
                    path,
                    ("records", idx, "superseded_by"),
                    "superseded assertion must point at a currently active assertion",
                )
            )

    active_claims: dict[str, str] = {}
    for rid, record in latest.items():
        if record.get("kind") != ASSERTION_KIND or record.get("status") != "active":
            continue
        key = _claim_key(record.get("scope"), record.get("claim"))
        other = active_claims.get(key)
        if other is not None and other != rid:
            errors.append(
                _err(
                    CODE_DUPLICATE_ACTIVE,
                    path,
                    ("records", indexes[rid], "claim"),
                    "current brain assertion view has more than one active assertion for the same scope and claim",
                )
            )
        active_claims[key] = rid
    seen_memory: dict[str, dict[str, Any]] = {}
    for idx, record in enumerate(records):
        kind = record.get("kind")
        if kind not in {DECISION_KIND, LESSON_KIND}:
            continue
        rid = record.get("id")
        if not isinstance(rid, str):
            continue
        if rid in seen_memory:
            errors.append(
                _err(
                    CODE_DUPLICATE_ACTIVE,
                    path,
                    ("records", idx, "id"),
                    "brain memory record id must be unique",
                )
            )
        supersedes_ref = record.get("supersedes_ref")
        if supersedes_ref is not None:
            target = seen_memory.get(str(supersedes_ref))
            if target is None:
                errors.append(
                    _err(
                        CODE_SUPERSEDE_TARGET,
                        path,
                        ("records", idx, "supersedes_ref"),
                        "brain memory supersedes_ref must point at an earlier record",
                    )
                )
            elif target.get("kind") != kind:
                errors.append(
                    _err(
                        CODE_SUPERSEDE_TARGET,
                        path,
                        ("records", idx, "supersedes_ref"),
                        "brain memory supersedes_ref must point at a record of the same kind",
                    )
                )
        seen_memory[rid] = record
    return errors


def validate_ledger_doc(doc: dict[str, Any], path: Path | str) -> list[ValidationError]:
    errors: list[ValidationError] = []
    errors.extend(validate_with_schema(doc, SCHEMA_PATH, path, code=CODE_SCHEMA, contract=CONTRACT))
    records = doc.get("records")
    if not isinstance(records, list):
        return errors
    for idx, record in enumerate(records):
        if isinstance(record, dict):
            errors.extend(_forbidden_identifier_errors(record.get("claim"), path, ("records", idx, "claim")))
            errors.extend(_forbidden_identifier_errors(record.get("scope"), path, ("records", idx, "scope")))
    errors.extend(_validate_chain(records, path))
    usable_records = [record for record in records if isinstance(record, dict)]
    errors.extend(_validate_current_view(usable_records, path))
    return errors


def validate_records(records: Sequence[dict[str, Any]], path: Path | str = "<brain-runtime>") -> list[ValidationError]:
    if not records:
        return []
    return validate_ledger_doc(_ledger_doc(records), path)


def _require_valid_records(records: Sequence[dict[str, Any]], path: Path | str = "<brain-runtime>") -> None:
    errors = validate_records(records, path)
    if errors:
        raise BrainLedgerInvalid(errors)


def _append_record(records: Sequence[dict[str, Any]], body: dict[str, Any]) -> dict[str, Any]:
    record = copy.deepcopy(body)
    record.pop(CONTENT_HASH_FIELD, None)
    record["sequence"] = len(records)
    record["prev_hash"] = str(records[-1][CONTENT_HASH_FIELD]) if records else GENESIS_PREV_HASH
    record[CONTENT_HASH_FIELD] = canonical_content_hash(record)
    return record


def _write_ledger(path: Path, records: Sequence[dict[str, Any]], writer: Writer) -> str:
    text = serialize_ledger(records)
    writer(path, text)
    return text


def _active_match(records: Sequence[dict[str, Any]], scope: Any, claim: dict[str, Any]) -> dict[str, Any] | None:
    latest, _indexes = _latest_by_id(records)
    key = _claim_key(scope, claim)
    matches = [
        record
        for record in latest.values()
        if record.get("status") == "active" and _claim_key(record.get("scope"), record.get("claim")) == key
    ]
    if not matches:
        return None
    return sorted(matches, key=lambda r: int(r.get("sequence", 0)))[-1]


def assert_claim(
    *,
    claim: dict[str, Any],
    scope: str | dict[str, Any],
    evidence_ref: str,
    statement: str | None = None,
    assertion_type: str | None = None,
    verification_method: dict[str, Any] | str | None = None,
    state_root: Path | str = V3_LOCAL_STATE_ROOT,
    assertion_id: str | None = None,
    records: Sequence[dict[str, Any]] | None = None,
    write: Writer | None = None,
) -> AssertResult:
    path = ledger_path(state_root)
    current = load_records(state_root) if records is None else _copy_mapping_records(records, path)
    _require_valid_records(current, ledger_path(state_root))
    normalized_claim = _normalize_claim(claim)
    normalized_scope = _normalize_scope(scope)
    if not isinstance(evidence_ref, str) or not evidence_ref or "://" in evidence_ref:
        raise BrainAssertionRefused("evidence_ref must be a non-empty local or opaque reference")
    normalized_statement = _normalize_statement(statement, normalized_claim)
    normalized_type = _normalize_assertion_type(assertion_type)
    normalized_verification = _normalize_verification_method(verification_method, evidence_ref)
    rid = assertion_id or _assertion_id(
        {
            "op": "assert",
            "scope": normalized_scope,
            "statement": normalized_statement,
            "type": normalized_type,
            "claim": normalized_claim,
            "verification_method": normalized_verification,
            "evidence_ref": evidence_ref,
        }
    )
    _validate_id(rid)
    latest, _indexes = _latest_by_id(current)
    if rid in latest and latest[rid].get("status") == "active":
        raise BrainAssertionRefused("active assertion id already exists")
    if _active_match(current, normalized_scope, normalized_claim) is not None:
        raise BrainAssertionRefused("active assertion already exists for scope and claim")

    body = {
        "kind": ASSERTION_KIND,
        "record_type": ASSERTION_RECORD_TYPE,
        "schema_version": SCHEMA_VERSION,
        "id": rid,
        "statement": normalized_statement,
        "type": normalized_type,
        "verification_method": normalized_verification,
        "claim": normalized_claim,
        "scope": normalized_scope,
        "evidence_ref": evidence_ref,
        "status": "active",
        "superseded_by": None,
    }
    record = _append_record(current, body)
    updated = [*current, record]
    errors = validate_records(updated, ledger_path(state_root))
    if errors:
        raise BrainAssertionRefused(errors)
    text = _write_ledger(path, updated, write or _default_write)
    return AssertResult(
        ledger_path=path,
        record=record,
        sequence=int(record["sequence"]),
        content_hash=str(record[CONTENT_HASH_FIELD]),
        prev_hash=str(record["prev_hash"]),
        ledger_text=text,
    )


def correct_claim(
    *,
    assertion_id: str,
    claim: dict[str, Any],
    evidence_ref: str,
    statement: str | None = None,
    assertion_type: str | None = None,
    verification_method: dict[str, Any] | str | None = None,
    state_root: Path | str = V3_LOCAL_STATE_ROOT,
    new_assertion_id: str | None = None,
    scope: str | dict[str, Any] | None = None,
    records: Sequence[dict[str, Any]] | None = None,
    write: Writer | None = None,
) -> CorrectResult:
    _validate_id(assertion_id)
    path = ledger_path(state_root)
    current = load_records(state_root) if records is None else _copy_mapping_records(records, path)
    _require_valid_records(current, ledger_path(state_root))
    latest, _indexes = _latest_by_id(current)
    old = latest.get(assertion_id)
    if old is None or old.get("status") != "active":
        raise BrainAssertionRefused("assertion id is not currently active")
    normalized_claim = _normalize_claim(claim)
    normalized_scope = _normalize_scope(scope if scope is not None else old.get("scope"))
    if not isinstance(evidence_ref, str) or not evidence_ref or "://" in evidence_ref:
        raise BrainAssertionRefused("evidence_ref must be a non-empty local or opaque reference")
    normalized_statement = _normalize_statement(statement, normalized_claim)
    normalized_type = _normalize_assertion_type(assertion_type or old.get("type"))
    normalized_verification = _normalize_verification_method(verification_method, evidence_ref)
    new_id = new_assertion_id or _assertion_id(
        {
            "op": "correct",
            "supersedes": assertion_id,
            "scope": normalized_scope,
            "statement": normalized_statement,
            "type": normalized_type,
            "claim": normalized_claim,
            "verification_method": normalized_verification,
            "evidence_ref": evidence_ref,
        }
    )
    _validate_id(new_id)
    if new_id == assertion_id:
        raise BrainAssertionRefused("new assertion id must differ from superseded assertion id")
    existing_new = _active_match(current, normalized_scope, normalized_claim)
    if existing_new is not None and existing_new.get("id") != assertion_id:
        raise BrainAssertionRefused("another active assertion already exists for the corrected scope and claim")

    supersede_body = {
        "kind": ASSERTION_KIND,
        "record_type": ASSERTION_RECORD_TYPE,
        "schema_version": SCHEMA_VERSION,
        "id": assertion_id,
        "statement": str(old["statement"]),
        "type": str(old["type"]),
        "verification_method": copy.deepcopy(old["verification_method"]),
        "claim": copy.deepcopy(old["claim"]),
        "scope": copy.deepcopy(old["scope"]),
        "evidence_ref": evidence_ref,
        "status": "superseded",
        "superseded_by": new_id,
    }
    superseded = _append_record(current, supersede_body)
    active_body = {
        "kind": ASSERTION_KIND,
        "record_type": ASSERTION_RECORD_TYPE,
        "schema_version": SCHEMA_VERSION,
        "id": new_id,
        "statement": normalized_statement,
        "type": normalized_type,
        "verification_method": normalized_verification,
        "claim": normalized_claim,
        "scope": normalized_scope,
        "evidence_ref": evidence_ref,
        "status": "active",
        "superseded_by": None,
    }
    active = _append_record([*current, superseded], active_body)
    updated = [*current, superseded, active]
    errors = validate_records(updated, ledger_path(state_root))
    if errors:
        raise BrainAssertionRefused(errors)
    text = _write_ledger(path, updated, write or _default_write)
    return CorrectResult(ledger_path=path, superseded_record=superseded, record=active, ledger_text=text)


def _append_decision(
    *,
    date: str,
    scope: str | dict[str, Any],
    statement: str,
    authority: str,
    supersedes_ref: str | None = None,
    state_root: Path | str = V3_LOCAL_STATE_ROOT,
    decision_id: str | None = None,
    records: Sequence[dict[str, Any]] | None = None,
    write: Writer | None = None,
) -> MemoryAppendResult:
    path = ledger_path(state_root)
    current = load_records(state_root) if records is None else _copy_mapping_records(records, path)
    _require_valid_records(current, ledger_path(state_root))
    normalized_date = _normalize_date(date)
    normalized_scope = _normalize_scope(scope)
    normalized_statement = _normalize_memory_text(statement, "statement")
    normalized_authority = _normalize_authority(authority)
    if supersedes_ref is not None:
        _validate_decision_id(supersedes_ref)
    rid = decision_id or _decision_id(
        {
            "op": "decision",
            "date": normalized_date,
            "scope": normalized_scope,
            "statement": normalized_statement,
            "authority": normalized_authority,
            "supersedes_ref": supersedes_ref,
        }
    )
    _validate_decision_id(rid)

    body = {
        "kind": DECISION_KIND,
        "record_type": DECISION_RECORD_TYPE,
        "schema_version": SCHEMA_VERSION,
        "id": rid,
        "date": normalized_date,
        "scope": normalized_scope,
        "statement": normalized_statement,
        "authority": normalized_authority,
        "supersedes_ref": supersedes_ref,
        "status": "active",
    }
    record = _append_record(current, body)
    updated = [*current, record]
    errors = validate_records(updated, ledger_path(state_root))
    if errors:
        raise BrainAssertionRefused(errors)
    text = _write_ledger(path, updated, write or _default_write)
    return MemoryAppendResult(
        ledger_path=path,
        record=record,
        sequence=int(record["sequence"]),
        content_hash=str(record[CONTENT_HASH_FIELD]),
        prev_hash=str(record["prev_hash"]),
        ledger_text=text,
    )


def _append_lesson(
    *,
    date: str,
    scope: str | dict[str, Any],
    source: str,
    feedback: str,
    correction: str,
    why: str,
    how_to_apply: str,
    supersedes_ref: str | None = None,
    state_root: Path | str = V3_LOCAL_STATE_ROOT,
    lesson_id: str | None = None,
    records: Sequence[dict[str, Any]] | None = None,
    write: Writer | None = None,
) -> MemoryAppendResult:
    path = ledger_path(state_root)
    current = load_records(state_root) if records is None else _copy_mapping_records(records, path)
    _require_valid_records(current, ledger_path(state_root))
    normalized_date = _normalize_date(date)
    normalized_scope = _normalize_scope(scope)
    normalized_source = _normalize_memory_text(source, "source")
    normalized_feedback = _normalize_memory_text(feedback, "feedback")
    normalized_correction = _normalize_memory_text(correction, "correction")
    normalized_why = _normalize_memory_text(why, "why")
    normalized_how = _normalize_memory_text(how_to_apply, "how_to_apply")
    if supersedes_ref is not None:
        _validate_lesson_id(supersedes_ref)
    rid = lesson_id or _lesson_id(
        {
            "op": "lesson",
            "date": normalized_date,
            "scope": normalized_scope,
            "source": normalized_source,
            "feedback": normalized_feedback,
            "correction": normalized_correction,
            "why": normalized_why,
            "how_to_apply": normalized_how,
            "supersedes_ref": supersedes_ref,
        }
    )
    _validate_lesson_id(rid)

    body = {
        "kind": LESSON_KIND,
        "record_type": LESSON_RECORD_TYPE,
        "schema_version": SCHEMA_VERSION,
        "id": rid,
        "date": normalized_date,
        "scope": normalized_scope,
        "source": normalized_source,
        "feedback": normalized_feedback,
        "correction": normalized_correction,
        "why": normalized_why,
        "how_to_apply": normalized_how,
        "supersedes_ref": supersedes_ref,
        "status": "active",
    }
    record = _append_record(current, body)
    updated = [*current, record]
    errors = validate_records(updated, ledger_path(state_root))
    if errors:
        raise BrainAssertionRefused(errors)
    text = _write_ledger(path, updated, write or _default_write)
    return MemoryAppendResult(
        ledger_path=path,
        record=record,
        sequence=int(record["sequence"]),
        content_hash=str(record[CONTENT_HASH_FIELD]),
        prev_hash=str(record["prev_hash"]),
        ledger_text=text,
    )


def check_claim(
    *,
    claim: dict[str, Any],
    scope: str | dict[str, Any],
    state_root: Path | str = V3_LOCAL_STATE_ROOT,
    records: Sequence[dict[str, Any]] | None = None,
) -> CheckResult:
    current = load_records(state_root) if records is None else _copy_mapping_records(records, ledger_path(state_root))
    if not current:
        return CheckResult(status="unknown", record=None)
    _require_valid_records(current, ledger_path(state_root))
    normalized_claim = _normalize_claim(claim)
    normalized_scope = _normalize_scope(scope)
    match = _active_match(current, normalized_scope, normalized_claim)
    if match is None:
        return CheckResult(status="unknown", record=None)
    return CheckResult(status="active", record=copy.deepcopy(match))


def _load_records_for_hydration(state_root: Path | str) -> list[dict[str, Any]]:
    path = ledger_path(state_root)
    if not path.is_file():
        return []
    try:
        data = load_yaml(path)
    except LoaderError as exc:
        raise BrainLedgerInvalid(str(exc)) from exc
    if isinstance(data, dict) and data.get("records") == []:
        # Hydration is read-only startup context: tolerate a bootstrap-empty ledger here while mutating ledger APIs fail closed.
        return []
    return _records_from_doc(data, path)


def _active_memory_records(records: Sequence[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    superseded = {
        str(record["supersedes_ref"])
        for record in records
        if record.get("kind") == kind and record.get("supersedes_ref") is not None
    }
    active = [
        copy.deepcopy(record)
        for record in records
        if record.get("kind") == kind and isinstance(record.get("id"), str) and record["id"] not in superseded
    ]
    active.sort(key=lambda record: (str(record.get("date", "")), int(record.get("sequence", 0)), str(record.get("id", ""))))
    return active


def _resume_state_pointer(state_root: Path | str) -> dict[str, Any] | None:
    root = Path(state_root)
    if not root.exists():
        return None
    paths: set[Path] = set()
    for pattern in ("**/*resume*", "**/*session*"):
        paths.update(path for path in root.glob(pattern) if path.is_file())
    candidates: list[tuple[str, str, Path]] = []
    for path in paths:
        try:
            content_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue
        candidates.append((str(path), content_sha256, path))
    if not candidates:
        return None
    # Resume-state filenames encode timestamps, so lexicographic path order is chronological.
    _name, _digest, newest = sorted(candidates, key=lambda item: (item[0], item[1]))[-1]
    stat = newest.stat()
    return {
        "path": str(newest),
        "content_sha256": hashlib.sha256(newest.read_bytes()).hexdigest(),
        "size_bytes": stat.st_size,
    }


def hydrate_contract(state_root: Path | str = V3_LOCAL_STATE_ROOT) -> dict[str, Any]:
    path = ledger_path(state_root)
    records = _load_records_for_hydration(state_root)
    if records:
        _require_valid_records(records, path)
    decisions = _active_memory_records(records, DECISION_KIND)
    lessons = _active_memory_records(records, LESSON_KIND)
    resume_state = _resume_state_pointer(state_root)
    return {
        "kind": HYDRATION_KIND,
        "schema_version": SCHEMA_VERSION,
        "ledger_path": str(path),
        "ledger_present": path.is_file(),
        "record_count": len(records),
        "head_content_hash": str(records[-1][CONTENT_HASH_FIELD]) if records else None,
        "active_decisions": decisions,
        "active_lessons": lessons,
        "newest_resume_state": resume_state,
        "summary": {
            "active_decision_count": len(decisions),
            "active_lesson_count": len(lessons),
            "newest_resume_state_present": resume_state is not None,
        },
    }


def verify_ledger(state_root: Path | str = V3_LOCAL_STATE_ROOT) -> VerifyResult:
    path = ledger_path(state_root)
    if not path.is_file():
        return VerifyResult(
            ok=False,
            ledger_path=path,
            summary={"record_count": 0, "active_count": 0, "head_content_hash": None},
            errors=(f"no brain assertion ledger at {path}",),
        )
    try:
        data = load_yaml(path)
    except LoaderError as exc:
        return VerifyResult(
            ok=False,
            ledger_path=path,
            summary={"record_count": 0, "active_count": 0, "head_content_hash": None},
            errors=(str(exc),),
        )
    if not isinstance(data, dict):
        errors = ["brain assertion ledger must be a YAML mapping"]
        return VerifyResult(ok=False, ledger_path=path, summary={"record_count": 0}, errors=tuple(errors))
    errors = validate_ledger_doc(data, path)
    records = data.get("records") if isinstance(data.get("records"), list) else []
    latest, _indexes = _latest_by_id([r for r in records if isinstance(r, dict)])
    active = [r for r in latest.values() if r.get("status") == "active"]
    summary = {
        "record_count": len(records),
        "active_count": len(active),
        "head_content_hash": records[-1].get(CONTENT_HASH_FIELD) if records else None,
        "errors": [e.format() for e in errors],
    }
    return VerifyResult(
        ok=not errors,
        ledger_path=path,
        summary=summary,
        errors=tuple(e.format() for e in errors),
    )
