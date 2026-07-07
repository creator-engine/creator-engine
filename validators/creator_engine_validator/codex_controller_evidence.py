"""Codex controller-promotion evidence packet.

The packet is deliberately a data carrier over existing launch facts: CDX-D
evaluation, managed hook-pack confirmation, lifecycle sentinel refs, and the
controller posture. It does not mint authority by itself; callers use
``validate_packet`` to decide whether a Codex controller may run as foreman or
must fail closed to a read-only posture.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import socket
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import hook_pack_confirm

PACKET_KIND = "ce-codex-controller-promotion-evidence-packet"
SCHEMA_VERSION = 1
STATE_DIR = Path(".ce/state/controller-evidence")
PACKET_PREFIX = "codex-controller-promotion"
STOP_HOOK_PATH = Path(".codex/hooks/ce-stop-codex.py")

REMOTE_CONTROL_ALLOWED = frozenset({"disabled", "brokered", "explicit-posture"})
REMOTE_CONTROL_ENV = ("CE_REMOTE_CONTROL_STATUS", "CE_POSTURE_REMOTE_CONTROL_STATUS")
REQUIRED_FIELD_CLASSES = (
    "argv_after_rewrite",
    "managed_hook_confirmed",
    "cdxd_result",
    "bypass_mode_source",
    "remote_control_status",
    "hook_requirements_sha",
    "hook_script_sha",
    "lifecycle_sentinel_refs",
    "ring1_smoke_result",
)
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_TOKEN_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


@dataclass(frozen=True)
class PacketValidation:
    path: Path
    status: str
    missing_field_classes: tuple[str, ...] = ()
    detail: str = ""
    payload: dict[str, Any] | None = None

    @property
    def ok(self) -> bool:
        return self.status == "valid"

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "path": str(self.path),
            "ok": self.ok,
            "missing_field_classes": list(self.missing_field_classes),
        }
        if self.detail:
            payload["detail"] = self.detail
        return payload


def default_host_id() -> str:
    return os.environ.get("CE_HOST_ID") or os.environ.get("CE_CONTROLLER_HOST_ID") or socket.gethostname()


def resolve_host_id(host_id: str | None = None) -> str:
    return str(host_id or default_host_id()).strip() or "unknown-host"


def _slug(value: str) -> str:
    cleaned = _TOKEN_RE.sub("-", value).strip("-._").lower()
    return cleaned or "unknown-host"


def evidence_dir(repo_root: Path | str | None) -> Path:
    return Path(repo_root or ".") / STATE_DIR


def packet_path(repo_root: Path | str | None, *, host_id: str | None = None) -> Path:
    return evidence_dir(repo_root) / f"{PACKET_PREFIX}.{_slug(resolve_host_id(host_id))}.json"


def sha256_file(path: Path) -> str | None:
    try:
        if not path.is_file():
            return None
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def combined_hook_sha(requirements_sha: str | None, script_sha: str | None) -> str | None:
    if not (_is_sha(requirements_sha) and _is_sha(script_sha)):
        return None
    return hashlib.sha256(f"{requirements_sha}\n{script_sha}\n".encode("utf-8")).hexdigest()


def hook_hashes(repo_root: Path | str | None) -> dict[str, str | None]:
    root = Path(repo_root or ".")
    requirements_sha = sha256_file(root / hook_pack_confirm.CODEX_REQUIREMENTS_PATH)
    script_sha = sha256_file(root / hook_pack_confirm.CODEX_HOOK_SCRIPT)
    return {
        "requirements": requirements_sha,
        "script": script_sha,
        "combined": combined_hook_sha(requirements_sha, script_sha),
    }


def normalize_remote_control_status(
    value: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> str:
    raw = value
    if raw is None:
        env = environ if environ is not None else os.environ
        for name in REMOTE_CONTROL_ENV:
            candidate = env.get(name)
            if candidate and candidate.strip():
                raw = candidate
                break
    token = (raw or "disabled").strip().lower().replace("_", "-").replace(" ", "-")
    if token in {"enabled-supervisory-only", "supervisory-only", "explicit", "explicit-posture"}:
        return "explicit-posture"
    if token in REMOTE_CONTROL_ALLOWED:
        return token
    return "disabled"


def known_gaps(repo_root: Path | str | None) -> list[dict[str, str]]:
    stop_hook = Path(repo_root or ".") / STOP_HOOK_PATH
    if stop_hook.exists():
        return []
    return [
        {
            "id": "codex-closeout-hook-gap",
            "path": str(STOP_HOOK_PATH),
            "status": "missing",
            "detail": "Codex closeout hook ce-stop-codex.py is not present",
        }
    ]


def build_packet(
    *,
    repo_root: Path | str | None,
    host_id: str | None,
    argv_after_rewrite: Sequence[str],
    managed_hook_confirmed: bool,
    cdxd_result: Mapping[str, Any],
    bypass_mode_source: str | None,
    remote_control_status: str,
    lifecycle_sentinel_refs: Sequence[str],
    ring1_smoke_result: Mapping[str, Any],
) -> dict[str, Any]:
    hashes = hook_hashes(repo_root)
    return {
        "kind": PACKET_KIND,
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "host_id": resolve_host_id(host_id),
        "harness": "codex",
        "argv_after_rewrite": [str(part) for part in argv_after_rewrite],
        "managed_hook_confirmed": {
            "confirmed": bool(managed_hook_confirmed),
            "sha": hashes["combined"],
        },
        "cdxd_result": dict(cdxd_result),
        "bypass_mode_source": bypass_mode_source or "none",
        "remote_control_status": normalize_remote_control_status(remote_control_status),
        "hook_requirements_sha": hashes["requirements"],
        "hook_script_sha": hashes["script"],
        "lifecycle_sentinel_refs": [str(ref) for ref in lifecycle_sentinel_refs],
        "ring1_smoke_result": dict(ring1_smoke_result),
        "known_gaps": known_gaps(repo_root),
    }


def write_packet(repo_root: Path | str | None, packet: Mapping[str, Any]) -> Path:
    path = packet_path(repo_root, host_id=str(packet.get("host_id") or "unknown-host"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(packet), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def read_packet(repo_root: Path | str | None, *, host_id: str | None = None) -> PacketValidation:
    path = packet_path(repo_root, host_id=host_id)
    if not path.is_file():
        return PacketValidation(path=path, status="absent", detail="promotion evidence packet is absent")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return PacketValidation(path=path, status="incomplete", detail=f"packet unreadable: {exc}")
    if not isinstance(payload, dict):
        return PacketValidation(path=path, status="incomplete", detail="packet is not a JSON object")
    return validate_packet(payload, path=path, host_id=host_id)


def validate_packet(
    payload: Mapping[str, Any],
    *,
    path: Path | None = None,
    host_id: str | None = None,
) -> PacketValidation:
    expected_host = resolve_host_id(host_id) if host_id is not None else None
    missing: list[str] = []

    if payload.get("kind") != PACKET_KIND:
        missing.append("kind")
    if payload.get("schema_version") != SCHEMA_VERSION:
        missing.append("schema_version")
    if not _non_empty_str(payload.get("generated_at")):
        missing.append("generated_at")
    if not _non_empty_str(payload.get("host_id")):
        missing.append("host_id")
    elif expected_host is not None and payload.get("host_id") != expected_host:
        missing.append("host_id")

    if not _str_list(payload.get("argv_after_rewrite")):
        missing.append("argv_after_rewrite")
    managed = payload.get("managed_hook_confirmed")
    if (
        not isinstance(managed, Mapping)
        or managed.get("confirmed") is not True
        or not _is_sha(managed.get("sha"))
    ):
        missing.append("managed_hook_confirmed")
    cdxd = payload.get("cdxd_result")
    if not isinstance(cdxd, Mapping) or cdxd.get("ok") is not True:
        missing.append("cdxd_result")
    if payload.get("bypass_mode_source") not in {"argv", "config", "none"}:
        missing.append("bypass_mode_source")
    if payload.get("remote_control_status") not in REMOTE_CONTROL_ALLOWED:
        missing.append("remote_control_status")
    if not _is_sha(payload.get("hook_requirements_sha")):
        missing.append("hook_requirements_sha")
    if not _is_sha(payload.get("hook_script_sha")):
        missing.append("hook_script_sha")
    if not _str_list(payload.get("lifecycle_sentinel_refs")):
        missing.append("lifecycle_sentinel_refs")
    smoke = payload.get("ring1_smoke_result")
    if not isinstance(smoke, Mapping) or smoke.get("status") != "pass":
        missing.append("ring1_smoke_result")

    status = "valid" if not missing else "incomplete"
    detail = "" if not missing else "missing or invalid field class(es): " + ", ".join(missing)
    return PacketValidation(
        path=path or Path("<memory>"),
        status=status,
        missing_field_classes=tuple(dict.fromkeys(missing)),
        detail=detail,
        payload=dict(payload),
    )


def _non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _str_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(_non_empty_str(item) for item in value)


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and _SHA_RE.fullmatch(value) is not None
