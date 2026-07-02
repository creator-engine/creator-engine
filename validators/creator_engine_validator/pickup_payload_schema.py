"""Payload-as-data-only schema for conveyor pickup discovery."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

AuditSink = Callable[[Mapping[str, Any]], None]

ALLOWED_DISCOVERY_PAYLOAD_FIELDS = frozenset({"issue", "branch_name", "pr_title", "pr_body"})
REQUIRED_DISCOVERY_PAYLOAD_FIELDS = ALLOWED_DISCOVERY_PAYLOAD_FIELDS

MAX_DISCOVERY_PAYLOAD_FIELD_LENGTHS: Mapping[str, int] = {
    "issue": 128,
    "branch_name": 255,
    "pr_title": 512,
    "pr_body": 65_536,
}

BANNED_DISCOVERY_CONTROL_FIELDS = frozenset(
    {
        "approval_policy",
        "args",
        "argv",
        "base",
        "base_ref",
        "bundle",
        "bundle_path",
        "checkout_path",
        "command",
        "commands",
        "credentials",
        "env",
        "environment",
        "git_config",
        "git_options",
        "gh_options",
        "hook_path",
        "hook_paths",
        "hooks_path",
        "publish",
        "publish_policy",
        "pr_base",
        "remote",
        "remotes",
        "repo",
        "repo_path",
        "repository",
        "timeout",
        "timeouts",
        "validate_command",
        "validation_timeout",
        "worktree",
        "worktree_path",
    }
)


@dataclass(frozen=True)
class ConveyorDiscoveryPayload:
    """Validated four-field discovery payload.

    The fields remain untrusted text. This value proves only that the payload
    shape is data-only and bounded before a caller encodes it for a target API.
    """

    issue: str
    branch_name: str
    pr_title: str
    pr_body: str

    def to_dict(self) -> dict[str, str]:
        return {
            "issue": self.issue,
            "branch_name": self.branch_name,
            "pr_title": self.pr_title,
            "pr_body": self.pr_body,
        }


class DiscoveryPayloadRejected(ValueError):
    """Raised when a discovery payload fails closed."""

    def __init__(self, message: str, *, audit_records: tuple[Mapping[str, Any], ...]) -> None:
        super().__init__(message)
        self.audit_records = audit_records


def validate_discovery_payload(
    payload: Mapping[str, Any],
    *,
    audit_sink: AuditSink | None = None,
    source: str = "conveyor_pickup",
) -> ConveyorDiscoveryPayload:
    """Validate the ADR-0004 data-only discovery payload.

    Rejections are value-free: audit records name the rejected field and reason
    but never copy attacker-controlled payload values into logs.
    """

    if not isinstance(payload, Mapping):
        record = _audit_record(source, "schema_mismatch", field=None, detail="payload_not_mapping")
        _emit(audit_sink, record)
        raise DiscoveryPayloadRejected("discovery payload must be a mapping", audit_records=(record,))

    audit_records: list[Mapping[str, Any]] = []
    keys = set(payload.keys())
    unknown = sorted(str(key) for key in keys - ALLOWED_DISCOVERY_PAYLOAD_FIELDS)
    for field in unknown:
        reason = "banned_control_field" if field in BANNED_DISCOVERY_CONTROL_FIELDS else "unknown_field"
        audit_records.append(_audit_record(source, reason, field=field))

    missing = sorted(REQUIRED_DISCOVERY_PAYLOAD_FIELDS - keys)
    for field in missing:
        audit_records.append(_audit_record(source, "missing_required_field", field=field))

    values: dict[str, str] = {}
    for field in sorted(ALLOWED_DISCOVERY_PAYLOAD_FIELDS & keys):
        value = payload.get(field)
        if not isinstance(value, str):
            audit_records.append(_audit_record(source, "schema_mismatch", field=field, detail="field_not_string"))
            continue
        if len(value) > MAX_DISCOVERY_PAYLOAD_FIELD_LENGTHS[field]:
            audit_records.append(
                _audit_record(
                    source,
                    "field_oversized",
                    field=field,
                    detail=f"max_length={MAX_DISCOVERY_PAYLOAD_FIELD_LENGTHS[field]}",
                )
            )
            continue
        values[field] = value

    if audit_records:
        records = tuple(audit_records)
        for record in records:
            _emit(audit_sink, record)
        raise DiscoveryPayloadRejected("discovery payload rejected", audit_records=records)

    return ConveyorDiscoveryPayload(
        issue=values["issue"],
        branch_name=values["branch_name"],
        pr_title=values["pr_title"],
        pr_body=values["pr_body"],
    )


def _audit_record(
    source: str,
    reason: str,
    *,
    field: str | None,
    detail: str | None = None,
) -> Mapping[str, Any]:
    record: dict[str, Any] = {
        "action": "discovery_payload_rejected",
        "source": source,
        "reason": reason,
        "allowed_fields": sorted(ALLOWED_DISCOVERY_PAYLOAD_FIELDS),
    }
    if field is not None:
        record["field"] = field
    if detail is not None:
        record["detail"] = detail
    return record


def _emit(audit_sink: AuditSink | None, record: Mapping[str, Any]) -> None:
    if audit_sink is not None:
        audit_sink(record)


__all__ = [
    "ALLOWED_DISCOVERY_PAYLOAD_FIELDS",
    "BANNED_DISCOVERY_CONTROL_FIELDS",
    "ConveyorDiscoveryPayload",
    "DiscoveryPayloadRejected",
    "MAX_DISCOVERY_PAYLOAD_FIELD_LENGTHS",
    "validate_discovery_payload",
]
