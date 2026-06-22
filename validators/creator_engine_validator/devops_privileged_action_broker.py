"""Slice-1 DevOps privileged-action broker skeleton.

The module is deliberately offline and fail-closed.  It validates a
``privileged_action_envelope`` wrapper, records a value-free decision in a
runtime-evidence hash chain, and dispatches accepted requests only to local
stub executors.  Live OpenBao, SSH, network, shell, and subprocess behavior are
reserved for later slices.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import re
from typing import Any

from .loader import LoaderError, load_yaml
from .reporting import ValidationError, make_error
from .runtime_evidence_spine import CHAIN_KIND, RECORD_KIND, append, verify_chain
from .schema import validate_with_schema

SCHEMA = "schemas/devops-privileged-action-broker.schema.yaml"
CONTRACT = "docs/contracts/devops-privileged-action-broker.md"

CODE_SCHEMA = "PAB-001"
CODE_CAPABILITY = "PAB-002"
CODE_SECRET = "PAB-003"
CODE_EXECUTION = "PAB-004"

RECORD_TYPE_DECISION = "devops_privileged_action_broker_decision"
RECORD_TYPE_ACTION = "devops_privileged_action_broker_action"
BROKER_COMPONENT = "devops-privileged-action-broker"
POLICY_SHA = hashlib.sha256(
    b"creator-engine:devops-privileged-action-broker:slice-1:policy:v1"
).hexdigest()

BROKER_PROXY_MODE = "broker-proxies"
CAPABILITY_HANDOFF_MODE = "capability-handoff"
SIDECAR_TMPFS_CUSTODY = "sidecar-templates-real-secret-into-tmpfs"


@dataclass(frozen=True)
class StubActionResult:
    """Value-free result from a Slice-1 stub executor."""

    executor: str
    status: str
    evidence_ref: str


@dataclass(frozen=True)
class BrokerResult:
    """Outcome of one broker request."""

    accepted: bool
    verdict: str
    errors: tuple[ValidationError, ...]
    decision_record: dict[str, Any]
    action_record: dict[str, Any] | None = None
    action_result: StubActionResult | None = None


Executor = Callable[[Mapping[str, Any]], StubActionResult]
Clock = Callable[[], datetime]


_ALLOWED_CAPABILITIES: frozenset[tuple[str, str, str, str]] = frozenset(
    {
        ("openbao_ssh", "ssh_sign_public_key", "signed_ssh_certificate", "ssh"),
        ("openbao_ssh", "ssh_issue_otp", "one_time_ssh_password", "ssh"),
        ("openbao_transit", "transit_encrypt", "transit_operation", "transit"),
        ("openbao_transit", "transit_decrypt", "transit_operation", "transit"),
        ("openbao_transit", "transit_sign", "transit_operation", "transit"),
        ("openbao_transit", "transit_verify", "transit_operation", "transit"),
        ("openbao_transit", "transit_hash_hmac_random", "transit_operation", "transit"),
        ("openbao_database", "database_dynamic_credentials", "dynamic_credential", "database"),
        (
            "openbao_kubernetes",
            "kubernetes_service_account_token",
            "service_account_token",
            "kubernetes",
        ),
        ("openbao_rabbitmq", "rabbitmq_dynamic_credentials", "dynamic_credential", "rabbitmq"),
        ("openbao_cubbyhole", "response_wrap", "response_wrapped_payload", "cubbyhole"),
        ("broker_internal", "broker_proxy_command", "broker_policy_only", "broker"),
        ("broker_internal", "sidecar_template_secret", "broker_policy_only", "broker"),
    }
)

_SECRET_KEY_PATTERN = re.compile(
    r"(password|passwd|client[_ -]?secret|secret[_ -]?key|\bsecret\b|"
    r"private[_ -]?key|wrapping[_ -]?token|openbao[_ -]?token|"
    r"\botp\b|one[_ -]?time[_ -]?password|dynamic[_ -]?credential|plaintext|"
    r"cookie|recovery[_ -]?code|provider[_ -]?api[_ -]?credential|api[_ -]?key)",
    re.IGNORECASE,
)
_SECRET_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", re.IGNORECASE),
    re.compile(
        r"\b(password|passwd|client[_ -]?secret|secret[_ -]?key|secret|token|"
        r"private[_ -]?key|wrapping[_ -]?token|"
        r"openbao[_ -]?token|\botp\b|one[_ -]?time[_ -]?password|"
        r"dynamic[_ -]?credential|plaintext|cookie|recovery[_ -]?code|"
        r"provider[_ -]?api[_ -]?credential|api[_ -]?key)\b\s*[:=]\s*\S+",
        re.IGNORECASE,
    ),
    re.compile(r"\b(sk-[A-Za-z0-9_-]{12,}|ghp_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\b"),
)


class BrokerLedgerError(RuntimeError):
    """Raised when the broker ledger cannot be safely extended."""


class BrokerLedger:
    """Small YAML-backed runtime-evidence chain for broker decisions/actions."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"kind": CHAIN_KIND, "records": []}
        try:
            document = load_yaml(self.path)
        except LoaderError as exc:
            raise BrokerLedgerError(str(exc)) from exc
        if not isinstance(document, dict):
            raise BrokerLedgerError("broker ledger must be a YAML mapping")
        if document.get("kind") != CHAIN_KIND:
            raise BrokerLedgerError(f"broker ledger kind must be {CHAIN_KIND!r}")
        records = document.get("records")
        if not isinstance(records, list):
            raise BrokerLedgerError("broker ledger records must be a list")
        return document

    def records(self) -> list[dict[str, Any]]:
        records = self.load()["records"]
        return [dict(record) for record in records if isinstance(record, dict)]

    def verify(self) -> list[Any]:
        return verify_chain(self.load()["records"])

    def append(self, record_body: Mapping[str, Any]) -> dict[str, Any]:
        document = self.load()
        records = document["records"]
        findings = verify_chain(records)
        if findings:
            summary = "; ".join(f"{f.kind}@{f.index}" for f in findings)
            raise BrokerLedgerError(f"broker ledger hash chain does not verify: {summary}")
        record = append(records, dict(record_body))
        document["records"] = [*records, record]
        self._write(document)
        return record

    def _write(self, document: Mapping[str, Any]) -> None:
        try:
            import yaml
        except ModuleNotFoundError as exc:  # pragma: no cover - environment guard
            raise BrokerLedgerError("PyYAML is required") from exc

        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(f".{self.path.name}.tmp")
        tmp.write_text(yaml.safe_dump(dict(document), sort_keys=False), encoding="utf-8")
        tmp.replace(self.path)


def validate_envelope(
    document: Mapping[str, Any],
    *,
    instance_path: str | Path = "<broker-request>",
) -> list[ValidationError]:
    """Run the Slice-1 envelope validation chain.

    Schema errors stop the chain so structurally invalid secret-bearing keys
    remain reported as ``PAB-001`` rather than being reclassified by later
    semantic checks.
    """

    schema_errors = list(
        validate_with_schema(
            document,
            SCHEMA,
            instance_path,
            code=CODE_SCHEMA,
            contract=CONTRACT,
        )
    )
    if schema_errors:
        return schema_errors

    envelope = document["privileged_action_envelope"]
    errors: list[ValidationError] = []
    errors.extend(_capability_coherence_errors(envelope, instance_path))
    errors.extend(_execution_policy_errors(envelope, instance_path))
    errors.extend(_semantic_secret_errors(envelope, instance_path))
    return errors


def dispatch(
    document: Mapping[str, Any],
    *,
    ledger: BrokerLedger,
    executors: Mapping[str, Executor] | None = None,
    now: Clock | None = None,
) -> BrokerResult:
    """Validate, attest, and dispatch one envelope to a Slice-1 stub executor."""

    clock = now or _utc_now
    recorded_at = _format_utc(clock())
    envelope = _maybe_envelope(document)
    envelope_hash = envelope_digest(document)
    errors = tuple(validate_envelope(document))
    verdict = "accepted" if not errors else "refused"

    decision_body = _decision_record_body(
        envelope=envelope,
        envelope_hash=envelope_hash,
        verdict=verdict,
        errors=errors,
        recorded_at=recorded_at,
    )
    decision_record = ledger.append(decision_body)
    if errors:
        return BrokerResult(
            accepted=False,
            verdict=verdict,
            errors=errors,
            decision_record=decision_record,
        )

    assert envelope is not None
    execution_mode = str(envelope["execution"]["execution_mode"])
    executor_map = dict(default_stub_executors())
    if executors is not None:
        executor_map.update(executors)
    executor = executor_map.get(execution_mode)
    if executor is None:
        err = make_error(
            CODE_EXECUTION,
            "<broker-request>",
            "privileged_action_envelope.execution.execution_mode",
            "execution_mode has no Slice-1 stub executor",
            CONTRACT,
        )
        return BrokerResult(
            accepted=False,
            verdict="refused",
            errors=(err,),
            decision_record=decision_record,
        )

    action_result = executor(envelope)
    action_record = ledger.append(
        _action_record_body(
            envelope=envelope,
            envelope_hash=envelope_hash,
            recorded_at=_format_utc(clock()),
            action_result=action_result,
        )
    )
    return BrokerResult(
        accepted=True,
        verdict=verdict,
        errors=(),
        decision_record=decision_record,
        action_record=action_record,
        action_result=action_result,
    )


def default_stub_executors() -> dict[str, Executor]:
    return {
        BROKER_PROXY_MODE: broker_proxies_stub_executor,
        CAPABILITY_HANDOFF_MODE: capability_handoff_stub_executor,
    }


def broker_proxies_stub_executor(envelope: Mapping[str, Any]) -> StubActionResult:
    return _stub_result(envelope, BROKER_PROXY_MODE)


def capability_handoff_stub_executor(envelope: Mapping[str, Any]) -> StubActionResult:
    return _stub_result(envelope, CAPABILITY_HANDOFF_MODE)


def envelope_digest(document: Mapping[str, Any]) -> str:
    raw = json.dumps(
        _json_safe(document),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _capability_coherence_errors(
    envelope: Mapping[str, Any], instance_path: str | Path
) -> list[ValidationError]:
    cap = envelope["capability"]
    engine = str(cap["engine"])
    operation = str(cap["operation"])
    mode = str(cap["mode"])
    mount = str(cap["openbao_mount"])
    if engine == "external_plugin":
        return [
            make_error(
                CODE_CAPABILITY,
                instance_path,
                "privileged_action_envelope.capability.engine",
                "external_plugin capabilities are denied by default in Slice-1",
                CONTRACT,
            )
        ]
    if (engine, operation, mode, mount) in _ALLOWED_CAPABILITIES:
        return []
    return [
        make_error(
            CODE_CAPABILITY,
            instance_path,
            "privileged_action_envelope.capability",
            "capability engine, operation, mode, and OpenBao mount are not a Slice-1 allowed tuple",
            CONTRACT,
        )
    ]


def _execution_policy_errors(
    envelope: Mapping[str, Any], instance_path: str | Path
) -> list[ValidationError]:
    cap = envelope["capability"]
    execution = envelope["execution"]
    operation = str(cap["operation"])
    execution_mode = str(execution["execution_mode"])
    custody_mode = str(execution["custody_mode"])
    errors: list[ValidationError] = []
    if operation == "transit_decrypt" and execution_mode != BROKER_PROXY_MODE:
        errors.append(
            make_error(
                CODE_EXECUTION,
                instance_path,
                "privileged_action_envelope.execution.execution_mode",
                "transit_decrypt must use execution_mode: broker-proxies",
                CONTRACT,
            )
        )
    if operation == "sidecar_template_secret":
        if custody_mode != SIDECAR_TMPFS_CUSTODY:
            errors.append(
                make_error(
                    CODE_EXECUTION,
                    instance_path,
                    "privileged_action_envelope.execution.custody_mode",
                    "sidecar_template_secret must use tmpfs sidecar custody",
                    CONTRACT,
                )
            )
        if execution_mode != BROKER_PROXY_MODE:
            errors.append(
                make_error(
                    CODE_EXECUTION,
                    instance_path,
                    "privileged_action_envelope.execution.execution_mode",
                    "sidecar_template_secret must use execution_mode: broker-proxies",
                    CONTRACT,
                )
            )
    return errors


def _semantic_secret_errors(
    envelope: Mapping[str, Any], instance_path: str | Path
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    for path, kind in _secret_findings(envelope):
        errors.append(
            make_error(
                CODE_SECRET,
                instance_path,
                f"privileged_action_envelope.{path}",
                f"envelope contains a secret-shaped {kind}; broker evidence stays value-free",
                CONTRACT,
            )
        )
    return errors


def _secret_findings(value: Any, path: str = "") -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if _SECRET_KEY_PATTERN.search(key_text):
                findings.append((child_path, "key"))
            findings.extend(_secret_findings(child, child_path))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            findings.extend(_secret_findings(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        for pattern in _SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                findings.append((path, "value"))
                break
    return findings


def _decision_record_body(
    *,
    envelope: Mapping[str, Any] | None,
    envelope_hash: str,
    verdict: str,
    errors: Sequence[ValidationError],
    recorded_at: str,
) -> dict[str, Any]:
    requester = envelope.get("requester", {}) if isinstance(envelope, Mapping) else {}
    execution = envelope.get("execution", {}) if isinstance(envelope, Mapping) else {}
    return {
        "kind": RECORD_KIND,
        "record_type": RECORD_TYPE_DECISION,
        "schema_version": "1",
        "policy_sha": POLICY_SHA,
        "broker_component": BROKER_COMPONENT,
        "recorded_at": recorded_at,
        "who": {
            "seat_id": requester.get("seat_id"),
            "role": requester.get("role"),
            "actor_ref": requester.get("actor_ref"),
        },
        "what": {
            "envelope_id": envelope.get("envelope_id") if isinstance(envelope, Mapping) else None,
            "task_id": envelope.get("task_id") if isinstance(envelope, Mapping) else None,
            "execution_mode": execution.get("execution_mode"),
        },
        "envelope_hash": envelope_hash,
        "verdict": verdict,
        "reasons": [
            {
                "code": error.code,
                "path": error.path,
                "contract": error.contract,
            }
            for error in errors
        ],
    }


def _action_record_body(
    *,
    envelope: Mapping[str, Any],
    envelope_hash: str,
    recorded_at: str,
    action_result: StubActionResult,
) -> dict[str, Any]:
    cap = envelope["capability"]
    execution = envelope["execution"]
    target = envelope["target"]
    return {
        "kind": RECORD_KIND,
        "record_type": RECORD_TYPE_ACTION,
        "schema_version": "1",
        "policy_sha": POLICY_SHA,
        "broker_component": BROKER_COMPONENT,
        "recorded_at": recorded_at,
        "envelope_hash": envelope_hash,
        "envelope_id": envelope["envelope_id"],
        "task_id": envelope["task_id"],
        "execution_mode": execution["execution_mode"],
        "executor": action_result.executor,
        "status": action_result.status,
        "evidence_ref": action_result.evidence_ref,
        "capability": {
            "engine": cap["engine"],
            "operation": cap["operation"],
            "mode": cap["mode"],
            "openbao_mount": cap["openbao_mount"],
        },
        "target": {
            "target_type": target["target_type"],
            "target_ref": target["target_ref"],
        },
    }


def _stub_result(envelope: Mapping[str, Any], executor: str) -> StubActionResult:
    return StubActionResult(
        executor=executor,
        status="stubbed",
        evidence_ref=f"broker-stub:{envelope['envelope_id']}:{executor}",
    )


def _maybe_envelope(document: Mapping[str, Any]) -> Mapping[str, Any] | None:
    value = document.get("privileged_action_envelope")
    return value if isinstance(value, Mapping) else None


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    value = value.astimezone(UTC).replace(microsecond=0)
    return value.isoformat().replace("+00:00", "Z")
