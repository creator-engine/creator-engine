"""OpenBao production go-live artifact checks (ce-ops#113).

The go-live work ships deployable artifacts, not live production actions. These
helpers keep the test assertions small and value-free: they inspect committed
templates/scripts for the hardening properties required before Operator bringup.
"""

from __future__ import annotations

from pathlib import Path


GO_LIVE_ARTIFACTS = (
    "docs/devops/openbao/openbao.hcl.tmpl",
    "docs/devops/openbao/openbao.service",
    "docs/devops/openbao/provision-openbao.sh",
    "docs/devops/openbao/snapshot-openbao.sh",
    "docs/devops/openbao/restore-drill-openbao.sh",
    "docs/devops/openbao/emergency-revoke-openbao.sh",
    "docs/devops/openbao/ce-broker-policy.hcl",
    "docs/devops/openbao-production-golive.md",
    "docs/devops/openbao-operator-bringup.md",
)

PUBLIC_BIND_MARKERS = (
    'address = "0.0.0.0:',
    'address = "[::]:',
    'address = ":::',
    'OPENBAO_TAILNET_BIND_ADDR:-0.0.0.0',
)


def read_go_live_artifact(repo_root: Path, relative_path: str) -> str:
    """Read a go-live artifact by repo-relative path."""

    return (repo_root / relative_path).read_text(encoding="utf-8")


def validate_tailnet_tls_hcl(hcl: str) -> list[str]:
    """Return hardening violations for the committed OpenBao HCL template."""

    violations: list[str] = []
    required_snippets = {
        'storage "raft"': "missing integrated raft storage",
        'listener "tcp"': "missing tcp listener",
        'address         = "${OPENBAO_TAILNET_BIND_ADDR}:8200"': "listener is not parameterized to the tailnet bind address",
        'cluster_address = "${OPENBAO_TAILNET_BIND_ADDR}:8201"': "cluster listener is not tailnet-bound",
        "tls_disable      = false": "TLS is not enforced",
        'tls_cert_file    = "${OPENBAO_TLS_CERT_FILE}"': "TLS certificate path is not parameterized",
        'tls_key_file     = "${OPENBAO_TLS_KEY_FILE}"': "TLS key path is not parameterized",
        'audit "file" "ce_audit"': "file audit device is not configured",
        'file_path = "${OPENBAO_AUDIT_LOG}"': "audit sink path is not parameterized",
    }
    for snippet, message in required_snippets.items():
        if snippet not in hcl:
            violations.append(message)
    for marker in PUBLIC_BIND_MARKERS:
        if marker in hcl:
            violations.append(f"public listener marker present: {marker}")
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
        "CapabilityBoundingSet=CAP_IPC_LOCK": "capabilities must be bounded to IPC lock",
        "ReadWritePaths=/var/lib/openbao /var/log/openbao /run/openbao": "write paths must be explicitly scoped",
    }
    for snippet, message in required_snippets.items():
        if snippet not in unit:
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
        "systemctl daemon-reload": "script must reload systemd on apply",
    }
    for snippet, message in required_snippets.items():
        if snippet not in script:
            violations.append(message)
    forbidden = ("operator init", "operator unseal", "root_token")
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
        "seal)": "script must support emergency seal",
        "operator seal": "script must wire the emergency seal command",
        "--execute": "script must require explicit execution",
    }
    for snippet, message in required_snippets.items():
        if snippet not in script:
            violations.append(message)
    return violations
