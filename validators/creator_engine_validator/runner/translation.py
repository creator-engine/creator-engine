"""Shared runner translation helpers.

The Docker and Docker/runsc backends intentionally render different argv
shapes, but they share the same policy-field validation and launch-owned probe
contract. Keep those pure helpers here so backend modules do not reach into each
other's private symbols.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

LAUNCH_PROBE_CONTRACT = "ce-launch-owned-probe-v1"
LAUNCH_PROBE_RUN_ID_LABEL = "creator-engine.run-id"
LAUNCH_PROBE_CONTRACT_LABEL = "creator-engine.probe-contract"

_IMAGE_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class MountSpec:
    source: str
    target: str
    mode: str


def mount_from_policy_entry(
    entry: dict[str, Any],
    index: int,
    *,
    error_type: type[ValueError],
) -> MountSpec:
    path = require_abs_path(entry.get("path"), f"mount_manifest[{index}].path", error_type=error_type)
    return MountSpec(
        source=path,
        target=path,
        mode=require_mode(entry.get("mode", "ro"), f"mount_manifest[{index}].mode", error_type=error_type),
    )


def first_writable_mount_target(mounts: tuple[MountSpec, ...]) -> str | None:
    for mount in mounts:
        if mount.mode == "rw":
            return mount.target
    return None


def render_mount(mount: MountSpec) -> str:
    rendered = f"type=bind,source={mount.source},target={mount.target}"
    if mount.mode == "ro":
        rendered = f"{rendered},readonly"
    return rendered


def require_nonempty_str(value: Any, field: str, *, error_type: type[ValueError]) -> str:
    if not isinstance(value, str) or not value.strip():
        raise error_type(f"{field} is required")
    return value


def require_abs_path(value: Any, field: str, *, error_type: type[ValueError]) -> str:
    path = require_nonempty_str(value, field, error_type=error_type)
    if not path.startswith("/") or path.startswith("//") or "\x00" in path:
        raise error_type(f"{field} must be a non-empty absolute path")
    return path


def require_mode(value: Any, field: str, *, error_type: type[ValueError]) -> str:
    mode = require_nonempty_str(value, field, error_type=error_type)
    if mode not in {"ro", "rw"}:
        raise error_type(f"{field} must be 'ro' or 'rw'")
    return mode


def require_image_digest(value: Any, *, error_type: type[ValueError]) -> str:
    digest = require_nonempty_str(value, "image_ref.sha", error_type=error_type)
    if not _IMAGE_DIGEST_RE.match(digest):
        raise error_type("image_ref.sha must be a sha256:<hex64> digest")
    return digest


def require_uid_gid(value: int | str | None, field: str, *, error_type: type[ValueError]) -> int:
    if isinstance(value, bool) or value is None:
        raise error_type(f"{field} is required")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise error_type(f"{field} must be a non-negative integer") from None
    if parsed < 0:
        raise error_type(f"{field} must be a non-negative integer")
    return parsed


def optional_uid_gid(value: int | str | None, field: str, *, error_type: type[ValueError]) -> int | None:
    if value is None:
        return None
    return require_uid_gid(value, field, error_type=error_type)


def launch_probe_container_name(run_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(run_id)).strip("-._")
    if not cleaned or not cleaned[0].isalnum():
        cleaned = f"run-{cleaned}" if cleaned else "run"
    digest = hashlib.sha256(str(run_id).encode("utf-8")).hexdigest()[:12]
    base = cleaned[:48].rstrip("-._") or "run"
    return f"ce-probe-{base}-{digest}"


def launch_probe_contract_args(run_id: str) -> tuple[str, ...]:
    name = launch_probe_container_name(run_id)
    return (
        "--name",
        name,
        "--label",
        f"{LAUNCH_PROBE_RUN_ID_LABEL}={run_id}",
        "--label",
        f"{LAUNCH_PROBE_CONTRACT_LABEL}={LAUNCH_PROBE_CONTRACT}",
    )


def bind_launch_owned_probe_contract(argv: Sequence[str], *, run_id: str) -> tuple[str, ...]:
    parts = tuple(str(part) for part in argv)
    if len(parts) < 2 or parts[1] != "run":
        return (*launch_probe_contract_args(run_id), *parts)
    insert_at = 2
    if len(parts) > insert_at and parts[insert_at] == "--rm":
        insert_at += 1
    return (*parts[:insert_at], *launch_probe_contract_args(run_id), *parts[insert_at:])


def argv_carries_launch_probe_contract(
    argv: Sequence[str],
    *,
    run_id: str,
    name: str,
) -> bool:
    parts = [str(part) for part in argv]
    labels = {
        f"{LAUNCH_PROBE_RUN_ID_LABEL}={run_id}",
        f"{LAUNCH_PROBE_CONTRACT_LABEL}={LAUNCH_PROBE_CONTRACT}",
    }
    if "--name" not in parts:
        return False
    try:
        if parts[parts.index("--name") + 1] != name:
            return False
    except IndexError:
        return False
    seen_labels = {
        parts[index + 1]
        for index, part in enumerate(parts[:-1])
        if part == "--label"
    }
    return labels.issubset(seen_labels)
