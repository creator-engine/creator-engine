"""Strict typed parameter schemas for every host-ops broker v1 verb."""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

COMMAND_LIKE_FIELDS = frozenset(
    {"command", "argv", "script", "shell", "environment", "mount", "socket", "exec", "pipe"}
)

VERBS = (
    "status",
    "restart-daemon",
    "prepare-owned-state-root",
    "rotate-attempt-log",
    "repair-systemd-unit",
    "run-ephemeral-container",
    "prune-stopped-owned-containers",
    "snapshot-openbao",
    "restore-drill-openbao",
)
MUTATING_VERBS = frozenset(v for v in VERBS if v != "status")

STATUS_CLASSES = ("daemons", "systemd", "containers", "state_roots", "openbao")
_SAFE_TEXT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+=,\- ]{0,255}$")
_OCTAL_MODE = re.compile(r"^0[0-7]{3}$")
_DIGEST_IMAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/\-]+@sha256:[A-Fa-f0-9]{64}$")


class VerbSchemaError(ValueError):
    """A verb parameter object is malformed."""


def reject_command_like_keys(value: object, *, where: str = "request") -> None:
    """Reject forbidden command-smuggling key names recursively."""
    if isinstance(value, Mapping):
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            if key in COMMAND_LIKE_FIELDS:
                raise VerbSchemaError(f"{where} contains forbidden command-like field {key!r}")
            reject_command_like_keys(raw_value, where=f"{where}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            reject_command_like_keys(item, where=f"{where}[{index}]")


def validate_params(verb: str, params: object) -> dict[str, Any]:
    if verb not in VERBS:
        raise VerbSchemaError(f"unknown verb {verb!r}")
    raw = _mapping(params, "params")
    reject_command_like_keys(raw, where=f"{verb}.params")
    return _VALIDATORS[verb](raw)


def target_value(verb: str, params: Mapping[str, Any]) -> str:
    """Return the rate-limit target component for a normalized params object."""
    if verb == "status":
        return str(params.get("target") or "global")
    if verb == "restart-daemon":
        return str(params["daemon"])
    if verb == "prepare-owned-state-root":
        return str(params["root_name"])
    if verb == "rotate-attempt-log":
        return str(params["subsystem"])
    if verb == "repair-systemd-unit":
        return str(params["unit"])
    if verb == "run-ephemeral-container":
        return str(params["image"])
    if verb == "prune-stopped-owned-containers":
        return str(params["namespace"])
    if verb == "snapshot-openbao":
        return str(params["profile"])
    if verb == "restore-drill-openbao":
        return f"{params['profile']}:{params['snapshot_ref']}"
    raise VerbSchemaError(f"unknown verb {verb!r}")


def _mapping(value: object, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise VerbSchemaError(f"{where} must be an object")
    return value


def _reject_extra(raw: Mapping[str, Any], allowed: set[str], where: str) -> None:
    extra = sorted(set(str(k) for k in raw) - allowed)
    if extra:
        raise VerbSchemaError(f"{where} has unsupported field(s): {', '.join(extra)}")


def _str(raw: Mapping[str, Any], key: str, *, required: bool = False, default: str | None = None) -> str | None:
    if key not in raw:
        if required:
            raise VerbSchemaError(f"{key} is required")
        return default
    value = raw[key]
    if not isinstance(value, str) or not value.strip():
        raise VerbSchemaError(f"{key} must be a non-empty string")
    if not _SAFE_TEXT.match(value):
        raise VerbSchemaError(f"{key} contains unsupported characters")
    return value


def _bool(raw: Mapping[str, Any], key: str, default: bool) -> bool:
    if key not in raw:
        return default
    if not isinstance(raw[key], bool):
        raise VerbSchemaError(f"{key} must be a boolean")
    return bool(raw[key])


def _int(raw: Mapping[str, Any], key: str, default: int | None = None, *, required: bool = False, min_value: int | None = None, max_value: int | None = None) -> int:
    if key not in raw:
        if required:
            raise VerbSchemaError(f"{key} is required")
        if default is None:
            raise VerbSchemaError(f"{key} has no default")
        value = default
    else:
        value = raw[key]
    if not isinstance(value, int) or isinstance(value, bool):
        raise VerbSchemaError(f"{key} must be an integer")
    if min_value is not None and value < min_value:
        raise VerbSchemaError(f"{key} must be >= {min_value}")
    if max_value is not None and value > max_value:
        raise VerbSchemaError(f"{key} must be <= {max_value}")
    return value


def _enum(raw: Mapping[str, Any], key: str, allowed: set[str], default: str | None = None, *, required: bool = False) -> str:
    value = _str(raw, key, required=required, default=default)
    if value not in allowed:
        raise VerbSchemaError(f"{key} must be one of {sorted(allowed)}")
    return value


def _validate_status(raw: Mapping[str, Any]) -> dict[str, Any]:
    _reject_extra(raw, {"include", "target", "detail"}, "status params")
    include_raw = raw.get("include", list(STATUS_CLASSES))
    if not isinstance(include_raw, Sequence) or isinstance(include_raw, (str, bytes)):
        raise VerbSchemaError("include must be a list of status classes")
    include: list[str] = []
    for item in include_raw:
        if item not in STATUS_CLASSES:
            raise VerbSchemaError(f"include item {item!r} is not supported")
        if item not in include:
            include.append(str(item))
    if not include:
        raise VerbSchemaError("include must not be empty")
    return {
        "include": include,
        "target": _str(raw, "target"),
        "detail": _enum(raw, "detail", {"summary", "diagnostic"}, "summary"),
    }


def _validate_restart_daemon(raw: Mapping[str, Any]) -> dict[str, Any]:
    _reject_extra(raw, {"daemon", "mode", "wait_ready_seconds"}, "restart-daemon params")
    return {
        "daemon": _str(raw, "daemon", required=True),
        "mode": _enum(raw, "mode", {"restart", "try-restart"}, "restart"),
        "wait_ready_seconds": _int(raw, "wait_ready_seconds", 30, min_value=0, max_value=120),
    }


def _validate_prepare_root(raw: Mapping[str, Any]) -> dict[str, Any]:
    _reject_extra(raw, {"root_name", "purpose", "ensure_empty", "expected_uid", "expected_gid", "mode"}, "prepare-owned-state-root params")
    mode = _str(raw, "mode", default="0750")
    if not _OCTAL_MODE.match(mode or ""):
        raise VerbSchemaError("mode must be a four-digit octal string")
    return {
        "root_name": _str(raw, "root_name", required=True),
        "purpose": _enum(raw, "purpose", {"controller", "worker", "openbao", "daemon", "cache"}, required=True),
        "ensure_empty": _bool(raw, "ensure_empty", False),
        "expected_uid": _int(raw, "expected_uid", 0, min_value=0),
        "expected_gid": _int(raw, "expected_gid", 0, min_value=0),
        "mode": mode,
    }


def _validate_rotate_log(raw: Mapping[str, Any]) -> dict[str, Any]:
    _reject_extra(raw, {"subsystem", "log_kind", "max_bytes", "keep"}, "rotate-attempt-log params")
    return {
        "subsystem": _str(raw, "subsystem", required=True),
        "log_kind": _enum(raw, "log_kind", {"attempt", "audit", "repair"}, required=True),
        "max_bytes": _int(raw, "max_bytes", 10_485_760, min_value=1),
        "keep": _int(raw, "keep", 5, min_value=1),
    }


def _validate_repair_unit(raw: Mapping[str, Any]) -> dict[str, Any]:
    _reject_extra(raw, {"unit", "action", "wait_ready_seconds"}, "repair-systemd-unit params")
    return {
        "unit": _str(raw, "unit", required=True),
        "action": _enum(raw, "action", {"reenable-and-restart", "reset-failed", "restart-only"}, "reenable-and-restart"),
        "wait_ready_seconds": _int(raw, "wait_ready_seconds", 30, min_value=0, max_value=120),
    }


def _validate_run_container(raw: Mapping[str, Any]) -> dict[str, Any]:
    _reject_extra(raw, {"task", "image", "args", "timeout_seconds", "network", "state_root", "dry_run"}, "run-ephemeral-container params")
    image = _str(raw, "image", required=True)
    if not _DIGEST_IMAGE.match(image or ""):
        raise VerbSchemaError("image must be digest-pinned with @sha256:<digest>")
    args_raw = raw.get("args", [])
    if not isinstance(args_raw, Sequence) or isinstance(args_raw, (str, bytes)):
        raise VerbSchemaError("args must be a list of safe tokens")
    args = []
    for item in args_raw:
        if not isinstance(item, str) or not item or not _SAFE_TEXT.match(item):
            raise VerbSchemaError("args must contain safe non-empty strings")
        args.append(item)
    return {
        "task": _str(raw, "task", required=True),
        "image": image,
        "args": args,
        "timeout_seconds": _int(raw, "timeout_seconds", 300, min_value=1),
        "network": _enum(raw, "network", {"none", "ce-maintenance"}, "none"),
        "state_root": _str(raw, "state_root"),
        "dry_run": _bool(raw, "dry_run", False),
    }


def _validate_prune(raw: Mapping[str, Any]) -> dict[str, Any]:
    _reject_extra(raw, {"namespace", "older_than_seconds", "max_remove", "dry_run"}, "prune-stopped-owned-containers params")
    return {
        "namespace": _str(raw, "namespace", required=True),
        "older_than_seconds": _int(raw, "older_than_seconds", 3600, min_value=1),
        "max_remove": _int(raw, "max_remove", 20, min_value=1),
        "dry_run": _bool(raw, "dry_run", False),
    }


def _validate_snapshot(raw: Mapping[str, Any]) -> dict[str, Any]:
    _reject_extra(raw, {"profile", "destination", "label", "verify_after_write"}, "snapshot-openbao params")
    return {
        "profile": _str(raw, "profile", required=True),
        "destination": _str(raw, "destination", required=True),
        "label": _str(raw, "label"),
        "verify_after_write": _bool(raw, "verify_after_write", True),
    }


def _validate_restore(raw: Mapping[str, Any]) -> dict[str, Any]:
    _reject_extra(raw, {"profile", "snapshot_ref", "mode", "timeout_seconds"}, "restore-drill-openbao params")
    return {
        "profile": _str(raw, "profile", required=True),
        "snapshot_ref": _str(raw, "snapshot_ref", required=True),
        "mode": _enum(raw, "mode", {"metadata-verify", "ephemeral-restore-verify"}, "metadata-verify"),
        "timeout_seconds": _int(raw, "timeout_seconds", 900, min_value=1),
    }


_VALIDATORS = {
    "status": _validate_status,
    "restart-daemon": _validate_restart_daemon,
    "prepare-owned-state-root": _validate_prepare_root,
    "rotate-attempt-log": _validate_rotate_log,
    "repair-systemd-unit": _validate_repair_unit,
    "run-ephemeral-container": _validate_run_container,
    "prune-stopped-owned-containers": _validate_prune,
    "snapshot-openbao": _validate_snapshot,
    "restore-drill-openbao": _validate_restore,
}
