"""OpenBao production go-live artifact checks (ce-ops#113).

The go-live work ships deployable artifacts, not live production actions. These
helpers keep the test assertions small and value-free: they inspect committed
templates/scripts for the hardening properties required before Operator bringup.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any


GO_LIVE_ARTIFACTS = (
    "docs/devops/openbao/openbao.hcl.tmpl",
    "docs/devops/openbao/openbao.service",
    "docs/devops/openbao/provision-openbao.sh",
    "docs/devops/openbao/snapshot-openbao.sh",
    "docs/devops/openbao/restore-drill-openbao.sh",
    "docs/devops/openbao/emergency-revoke-openbao.sh",
    "docs/devops/openbao/ce-dev-policy.hcl.tmpl",
    "docs/devops/openbao/render-dev-policy.sh",
    "docs/devops/openbao/verify-production-config-openbao-2.5.5.sh",
    "docs/devops/openbao-production-golive.md",
    "docs/devops/openbao-operator-bringup.md",
)

PUBLIC_BIND_MARKERS = (
    'address = "0.0.0.0:',
    'address = "[::]:',
    'address = ":::',
    'OPENBAO_TAILNET_BIND_ADDR:-0.0.0.0',
)
SECRET_EXPORT_NAMES = frozenset(
    {
        "BAO_TOKEN",
        "OPENBAO_RESTORE_TOKEN",
        "OPENBAO_VERIFY_TOKEN",
        "OPENBAO_SECRET_ID_ACCESSOR",
        "OPENBAO_TOKEN_ACCESSOR",
        "OPENBAO_ROLE_ID",
        "OPENBAO_WRAPPING_TOKEN",
    }
)
_EXPORT_RE = re.compile(r"^\s*export\s+([A-Za-z_][A-Za-z0-9_]*)=(.+?)\s*$", re.MULTILINE)
_INLINE_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\b(?:hvs|hvb|bao)\.[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bage-secret-key-[A-Za-z0-9_-]{12,}\b", re.IGNORECASE),
    re.compile(
        r"\b(?:password|passwd|secret_value|token_value|private_key)\s*[=:]\s*\S{4,}",
        re.IGNORECASE,
    ),
)
_VALUE_FREE_EVIDENCE_REF_RE = re.compile(
    r"^(?:restore-proof|snapshot-ref|evidence-ref|audit-ref|rollback-ref|runbook-ref|"
    r"inventory-ref|mapping-ref|operator-attestation):"
    r"[A-Za-z0-9][A-Za-z0-9._:/@#-]{0,191}$"
)
_MIGRATION_INVENTORY_HEADER = (
    "record_id",
    "secret_class",
    "source_ref",
    "target_ref",
    "owner_ref",
    "rotation_ref",
    "rollback_ref",
    "evidence_ref",
    "status",
    "notes",
)
_MIGRATION_INVENTORY_SECRET_CLASSES = frozenset(
    {
        "github_app_pem",
        "model_provider_key",
        "bootstrap_token",
        "reviewer_token",
        "signing_key",
        "runtime_secret",
        "other",
    }
)
_MIGRATION_INVENTORY_STATUSES = frozenset(
    {
        "planned",
        "imported",
        "verified",
        "cutover",
        "rolled-back",
        "decommissioned",
    }
)
_MIGRATION_INVENTORY_REF_PATTERNS = {
    "record_id": re.compile(r"^[a-z0-9][a-z0-9._-]*$"),
    "source_ref": re.compile(r"^source-ref:[A-Za-z0-9._/:-]+$"),
    "target_ref": re.compile(r"^openbao-ref:ce-(?:kv|transit)/[A-Za-z0-9._/:-]+$"),
    "owner_ref": re.compile(r"^owner-ref:[A-Za-z0-9._/:-]+$"),
    "rotation_ref": re.compile(r"^rotation-ref:[A-Za-z0-9._/:-]+$"),
    "rollback_ref": re.compile(r"^rollback-ref:[A-Za-z0-9._/:-]+$"),
    "evidence_ref": re.compile(r"^evidence-ref:[A-Za-z0-9._/:-]+$"),
}


def read_go_live_artifact(repo_root: Path, relative_path: str) -> str:
    """Read a go-live artifact by repo-relative path."""

    return (repo_root / relative_path).read_text(encoding="utf-8")


def _strip_shell_value(raw: str) -> str:
    value = raw.strip()
    if value and value[-1] == ";":
        value = value[:-1].rstrip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value


def _is_placeholder_or_ref(value: str) -> bool:
    return (
        (value.startswith("<") and value.endswith(">"))
        or value.startswith("${")
        or value.startswith("$")
        or value.startswith("secret-ref:")
        or value.endswith("...")
        or "..." in value
    )


def _contains_inline_secret_value(value: str) -> bool:
    return any(pattern.search(value) for pattern in _INLINE_SECRET_PATTERNS)


def validate_secret_placeholders_in_runbook(runbook: str) -> list[str]:
    """Return violations when runbook secret exports use concrete values."""

    violations: list[str] = []
    for name, raw_value in _EXPORT_RE.findall(runbook):
        if name not in SECRET_EXPORT_NAMES:
            continue
        value = _strip_shell_value(raw_value)
        if _contains_inline_secret_value(value) or not _is_placeholder_or_ref(value):
            violations.append(f"{name} must be documented as a placeholder or SecretRef, not an inline value")
    return violations


def validate_restore_drill_proof(proof: Mapping[str, Any]) -> list[str]:
    """Return violations for value-free restore proof evidence."""

    violations: list[str] = []
    if proof.get("ok") is not True:
        violations.append("restore proof must record ok=true")
    for key in ("checked_at", "canary_field"):
        value = proof.get(key)
        if not isinstance(value, str) or not value.strip():
            violations.append(f"restore proof must include non-empty {key}")
    for key in ("token", "root_token", "secret", "secret_value", "unseal_key", "wrapping_token"):
        if key in proof:
            violations.append(f"restore proof must not include secret-bearing field {key}")
    for key, value in proof.items():
        if isinstance(value, str) and _contains_inline_secret_value(value):
            violations.append(f"restore proof field {key} contains inline secret-shaped material")
    return violations


def validate_migration_gate_evidence(record: Mapping[str, Any]) -> list[str]:
    """Return violations for the value-free live secret migration gate."""

    violations: list[str] = []
    required_refs = {
        "source_inventory_ref": "source inventory evidence is required before migration",
        "path_mapping_ref": "path mapping evidence is required before migration",
        "restore_drill_proof_ref": "restore proof evidence is required before migration",
        "encrypted_snapshot_ref": "encrypted snapshot evidence is required before migration",
        "audit_fail_closed_evidence_ref": "audit fail-closed evidence is required before migration",
        "rollback_plan_ref": "rollback plan evidence is required before migration",
        "operator_ratification_ref": "operator ratification evidence ref is required before migration",
    }
    for key, message in required_refs.items():
        value = record.get(key)
        if not isinstance(value, str) or not _VALUE_FREE_EVIDENCE_REF_RE.fullmatch(value):
            violations.append(message)
    for key, value in record.items():
        if isinstance(value, str) and _contains_inline_secret_value(value):
            violations.append(f"migration gate field {key} contains inline secret-shaped material")
    if record.get("live_secret_migration_enabled") is True:
        violations.append("readiness evidence must not enable live secret migration")
    if record.get("operator_ratified") is not True:
        violations.append("operator ratification evidence is required before migration")
    secret_refs = record.get("secret_refs")
    if not isinstance(secret_refs, list) or not secret_refs:
        violations.append("migration gate must enumerate destination secret refs")
    else:
        for item in secret_refs:
            if (
                not isinstance(item, str)
                or not item.startswith("secret-ref:")
                or _contains_inline_secret_value(item)
            ):
                violations.append("migration gate secret_refs must be SecretRef placeholders only")
                break
    return violations


def validate_secret_migration_inventory_tsv(inventory: str) -> list[str]:
    """Return violations for the value-free OpenBao migration inventory TSV."""

    violations: list[str] = []
    lines = inventory.splitlines()
    if not lines:
        return ["migration inventory must include the expected header"]
    header = tuple(lines[0].split("\t"))
    if header != _MIGRATION_INVENTORY_HEADER:
        violations.append("migration inventory header does not match the expected value-free template")
    data_rows = 0
    for line_number, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        data_rows += 1
        fields = line.split("\t")
        if len(fields) != len(_MIGRATION_INVENTORY_HEADER):
            violations.append(f"line {line_number}: expected 10 tab-separated fields")
            continue
        row = dict(zip(_MIGRATION_INVENTORY_HEADER, fields, strict=True))
        for field_name, pattern in _MIGRATION_INVENTORY_REF_PATTERNS.items():
            if not pattern.fullmatch(row[field_name]):
                violations.append(f"line {line_number}: invalid {field_name}")
        if row["secret_class"] not in _MIGRATION_INVENTORY_SECRET_CLASSES:
            violations.append(f"line {line_number}: invalid secret_class")
        if row["status"] not in _MIGRATION_INVENTORY_STATUSES:
            violations.append(f"line {line_number}: invalid status")
        for field_name, value in row.items():
            if _contains_inline_secret_value(value):
                violations.append(
                    f"line {line_number}: {field_name} contains inline secret-shaped material"
                )
    if data_rows == 0:
        violations.append("migration inventory must include at least one value-free data row")
    return violations


def validate_tailnet_tls_hcl(hcl: str) -> list[str]:
    """Return hardening violations for the committed OpenBao HCL template."""

    violations: list[str] = []
    required_snippets = {
        'storage "raft"': "missing integrated raft storage",
        'listener "tcp"': "missing tcp listener",
        'address         = "${OPENBAO_TAILNET_BIND_ADDR}:${OPENBAO_API_PORT}"': "listener is not parameterized to the tailnet bind address",
        'cluster_address = "${OPENBAO_TAILNET_BIND_ADDR}:${OPENBAO_CLUSTER_PORT}"': "cluster listener is not tailnet-bound",
        "tls_disable      = false": "TLS is not enforced",
        'tls_cert_file    = "${OPENBAO_TLS_CERT_FILE}"': "TLS certificate path is not parameterized",
        'tls_key_file     = "${OPENBAO_TLS_KEY_FILE}"': "TLS key path is not parameterized",
        'audit "file" "ce_audit"': "file audit device is not configured",
        "options = {": "audit options must use OpenBao 2.5.x map syntax",
        'file_path = "${OPENBAO_AUDIT_LOG}"': "audit sink path is not parameterized",
    }
    for snippet, message in required_snippets.items():
        if snippet not in hcl:
            violations.append(message)
    for marker in PUBLIC_BIND_MARKERS:
        if marker in hcl:
            violations.append(f"public listener marker present: {marker}")
    if "disable_mlock" in hcl:
        violations.append("OpenBao 2.5.5 no longer accepts disable_mlock in server config")
    if "options {" in hcl:
        violations.append("OpenBao 2.5.5 audit options must be a map, not a block")
    return violations


def validate_systemd_unit(unit: str) -> list[str]:
    """Return hardening violations for the OpenBao systemd unit."""

    violations: list[str] = []
    required_snippets = {
        "User=openbao": "service must run as the dedicated openbao user",
        "Group=openbao": "service must run as the dedicated openbao group",
        "NoNewPrivileges=true": "NoNewPrivileges must be enabled",
        "ProtectSystem=strict": "ProtectSystem=strict must be enabled",
        "ProtectHome=true": "ProtectHome=true must be enabled",
        "PrivateTmp=true": "PrivateTmp must be enabled",
        "MemoryDenyWriteExecute=true": "MemoryDenyWriteExecute must remain enabled",
        "ReadWritePaths=/var/lib/openbao /var/log/openbao /run/openbao": "write paths must be explicitly scoped",
    }
    for snippet, message in required_snippets.items():
        if snippet not in unit:
            violations.append(message)
    forbidden_snippets = {
        "AmbientCapabilities=CAP_IPC_LOCK": "OpenBao 2.5.5 removed mlock support; CAP_IPC_LOCK must not be granted",
        "CapabilityBoundingSet=CAP_IPC_LOCK": "OpenBao 2.5.5 removed mlock support; CAP_IPC_LOCK must not be granted",
        "LimitMEMLOCK=": "OpenBao 2.5.5 removed mlock support; memlock limits are moot",
    }
    for snippet, message in forbidden_snippets.items():
        if snippet in unit:
            violations.append(message)
    if "User=root" in unit:
        violations.append("service must not run as root")
    return violations


def validate_provision_script(script: str) -> list[str]:
    """Return violations for the idempotent host provision script."""

    violations: list[str] = []
    required_snippets = {
        "id -u \"$OPENBAO_USER\"": "dedicated user creation must be idempotent",
        "useradd --system": "script must create a system user when absent",
        "install -d -o \"$OPENBAO_USER\" -g \"$OPENBAO_GROUP\" -m 0700": "data directories must be owner-scoped 0700",
        "require_tailnet_bind": "script must reject non-tailnet bind addresses",
        "--apply": "script must separate planning from privileged apply",
        "--render-config": "script must expose a pure rendered-config mode for live config validation",
        "systemctl daemon-reload": "script must reload systemd on apply",
        "systemctl restart openbao.service": "script must start/restart OpenBao on apply",
        "systemctl reload openbao.service": "script must issue the audit-activation reload on apply",
    }
    for snippet, message in required_snippets.items():
        if snippet not in script:
            violations.append(message)
    forbidden = ("operator init", "operator unseal", "root_token", "disable_mlock", "options {")
    for snippet in forbidden:
        if snippet in script:
            violations.append(f"provision script must not perform Operator trust-root action: {snippet}")
    return violations


def validate_snapshot_restore_scripts(snapshot: str, restore: str) -> list[str]:
    """Return violations for encrypted snapshot and restore-drill scripts."""

    violations: list[str] = []
    snapshot_required = {
        "operator raft snapshot save": "snapshot script must save a raft snapshot",
        "OPENBAO_AGE_RECIPIENT": "snapshot script must require an encryption recipient",
        "age -r": "snapshot script must encrypt snapshots",
        "OPENBAO_SNAPSHOT_REMOTE_URI": "snapshot script must require an off-host destination",
        "copy_offhost": "snapshot script must copy encrypted artifacts off-host",
    }
    restore_required = {
        "age -d": "restore drill must decrypt the encrypted snapshot",
        "operator raft snapshot restore -force": "restore drill must restore into a throwaway raft instance",
        "OPENBAO_RESTORE_DRILL_ADDR": "restore drill must target an explicit throwaway address",
        "OPENBAO_RESTORE_TOKEN": "restore drill must separate the target restore token",
        "OPENBAO_VERIFY_TOKEN": "restore drill must separate the restored-state verification token",
        "OPENBAO_RESTORE_CANARY_PATH": "restore drill must verify a canary path",
        "RESTORE_DRILL_PROOF": "restore drill must emit proof for the gate",
    }
    for snippet, message in snapshot_required.items():
        if snippet not in snapshot:
            violations.append(message)
    for snippet, message in restore_required.items():
        if snippet not in restore:
            violations.append(message)
    return violations


def validate_emergency_revoke_script(script: str) -> list[str]:
    """Return violations for the emergency revocation runbook script."""

    violations: list[str] = []
    required_snippets = {
        "CE_DEV_ID": "script must bind actions to a per-dev identity",
        "lease)": "script must support lease revocation",
        "lease-prefix)": "script must support lease-prefix revocation",
        "approle)": "script must support AppRole accessor destruction",
        "OPENBAO_APPROLE_POLICY": "script must name the per-dev AppRole policy",
        "seal)": "script must support emergency seal",
        "operator seal": "script must wire the emergency seal command",
        "--execute": "script must require explicit execution",
    }
    for snippet, message in required_snippets.items():
        if snippet not in script:
            violations.append(message)
    return violations


def validate_per_dev_policy_template(policy: str) -> list[str]:
    """Return violations for the per-dev OpenBao policy template."""

    violations: list[str] = []
    required_snippets = {
        "ce-kv/data/devs/__CE_DEV_ID__/runtime/*": "data path must be scoped to the rendered dev id",
        "ce-kv/metadata/devs/__CE_DEV_ID__/runtime/*": "metadata path must be scoped to the rendered dev id",
        'capabilities = ["read"]': "data path must be read-only",
        'capabilities = ["read", "list"]': "metadata path must allow read/list only",
    }
    for snippet, message in required_snippets.items():
        if snippet not in policy:
            violations.append(message)
    forbidden = ("devs/+/runtime", "devs/*/runtime")
    for snippet in forbidden:
        if snippet in policy:
            violations.append(f"cross-dev wildcard present: {snippet}")
    return violations


def validate_policy_renderer(script: str) -> list[str]:
    """Return violations for the per-dev policy renderer script."""

    violations: list[str] = []
    required_snippets = {
        "CE_DEV_ID": "renderer must require a dev id",
        "^dev-[A-Za-z0-9_-]+$": "renderer must constrain dev id shape",
        "__CE_DEV_ID__": "renderer must substitute the dev id placeholder",
        "refusing unsafe CE_DEV_ID path component": "renderer must reject unsafe path components",
    }
    for snippet, message in required_snippets.items():
        if snippet not in script:
            violations.append(message)
    return violations
