"""Worker-Container Policy schema validation and safety predicates (PCO-040, PCO-045).

Validates Worker-Container Policy records against
``schemas/worker-container-policy.schema.yaml`` and enforces the
Slice 2I-S forbidden-mount and controller-key-secret refusal
predicates.

Scope:

* ``PCO-040``: schema validation — every worker-container policy record
  MUST validate against the worker-container policy schema.
* ``PCO-045``: forbidden-mount refusal — refuses any policy whose
  mount manifest names a forbidden path (host home directory, container
  engine sockets, SSH/GPG agent sockets) or whose ``secret_allowlist``
  names the controller-key private key.

A file is treated as a candidate Worker-Container Policy record when it
satisfies all of:

* YAML extension (``.yml`` / ``.yaml``);
* not under a ``schemas/`` or ``templates/`` directory;
* its path basename does NOT contain ``".tmp."`` (atomic-write
  temp files are skipped, per protocol);
* the loaded YAML is a mapping whose ``kind`` field equals
  ``worker-container-policy-record``.

Failures cite ``PCO-040`` (schema) or ``PCO-045`` (forbidden mount /
secret) and the prose contract at
``docs/operations/WORKER_CONTAINER_PROTOCOL.md``.

See:
  - ``docs/operations/WORKER_CONTAINER_PROTOCOL.md``
  - ``docs/architecture/parallel-controller-orchestration.md``
  - ``schemas/worker-container-policy.schema.yaml``
  - ``specs/005-pco-parallel-controller-orchestration/worker-isolation-runtime.md``
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "worker_container_policy"
CONTRACT = "docs/operations/WORKER_CONTAINER_PROTOCOL.md"
SCHEMA = "schemas/worker-container-policy.schema.yaml"
KIND_VALUE = "worker-container-policy-record"
CODE_SCHEMA = "PCO-040"
CODE_FORBIDDEN_MOUNT = "PCO-045"
CODE_INVALID = "worker_container_policy_invalid_record"

# Forbidden mount path patterns (PCO-045).
# Host home directory indicators.
_HOME_PATTERNS = [
    re.compile(r"^\$HOME\b"),
    re.compile(r"^~/"),
    re.compile(r"^~$"),
]
# Container engine socket paths (docker/podman).
_ENGINE_SOCKET_SUBSTRINGS = [
    "/var/run/docker.sock",
    "/run/docker.sock",
    "/run/podman/podman.sock",
    "/var/run/podman/podman.sock",
]
_PODMAN_SOCK_RE = re.compile(r"podman\.sock$")

# Controller-key secret name patterns (PCO-045 §f.3).
# Any secret name that contains "controller" and "key" (with any separator)
# is treated as a potential controller-key private key.
_CONTROLLER_KEY_RE = re.compile(r"controller.{0,10}key", re.IGNORECASE)


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts or "templates" in parts


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _record_is_policy(record: Any) -> bool:
    return isinstance(record, dict) and record.get("kind") == KIND_VALUE


def _is_forbidden_home_path(path_str: str) -> bool:
    for pattern in _HOME_PATTERNS:
        if pattern.match(path_str):
            return True
    return False


def _is_forbidden_engine_socket(path_str: str) -> bool:
    for substr in _ENGINE_SOCKET_SUBSTRINGS:
        if path_str == substr or path_str.startswith(substr):
            return True
    if _PODMAN_SOCK_RE.search(path_str):
        return True
    return False


def _is_controller_key_secret(name: str) -> bool:
    return bool(_CONTROLLER_KEY_RE.search(name))


def _check_forbidden_mounts(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Apply PCO-045 forbidden-mount and forbidden-secret predicates."""
    errors: list[ValidationError] = []

    mount_manifest = record.get("mount_manifest", [])
    if not isinstance(mount_manifest, list):
        return errors

    for entry in mount_manifest:
        if not isinstance(entry, dict):
            continue
        mount_path = entry.get("path", "")
        if not isinstance(mount_path, str):
            continue

        if _is_forbidden_home_path(mount_path):
            errors.append(make_error(
                CODE_FORBIDDEN_MOUNT,
                path,
                f"mount_manifest[path={mount_path!r}]",
                (
                    f"forbidden mount: '{mount_path}' is a host home-directory path; "
                    "worker containers MUST NOT mount host home directory paths "
                    "(PCO-045, §f.2 of worker-isolation-runtime.md)"
                ),
                CONTRACT,
            ))
        elif _is_forbidden_engine_socket(mount_path):
            errors.append(make_error(
                CODE_FORBIDDEN_MOUNT,
                path,
                f"mount_manifest[path={mount_path!r}]",
                (
                    f"forbidden mount: '{mount_path}' is a container engine socket; "
                    "worker containers MUST NOT mount Docker/Podman sockets — "
                    "this is functionally equivalent to giving the worker host root "
                    "(PCO-045, §f.4 of worker-isolation-runtime.md)"
                ),
                CONTRACT,
            ))

    secret_allowlist = record.get("secret_allowlist", [])
    if not isinstance(secret_allowlist, list):
        return errors

    for name in secret_allowlist:
        if not isinstance(name, str):
            continue
        if _is_controller_key_secret(name):
            errors.append(make_error(
                CODE_FORBIDDEN_MOUNT,
                path,
                f"secret_allowlist[name={name!r}]",
                (
                    f"forbidden secret: '{name}' matches controller-key private-key "
                    "naming pattern; the controller-key private key MUST NOT be "
                    "injected into any worker container — workers never sign leases "
                    "(PCO-045, §f.3 of worker-isolation-runtime.md)"
                ),
                CONTRACT,
            ))

    return errors


def iter_worker_container_policy_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate Worker-Container Policy files under ``paths``."""
    seen: set[Path] = set()
    records: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if _looks_like_yaml(path) and not _is_under_excluded(path) and not _is_tmp_artifact(path):
            candidates = [path]
        elif path.is_dir():
            candidates = [
                p
                for p in sorted(path.rglob("*.yml")) + sorted(path.rglob("*.yaml"))
                if _looks_like_yaml(p)
                and not _is_under_excluded(p)
                and not _is_tmp_artifact(p)
            ]
        else:
            candidates = []
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            try:
                data = load_yaml(candidate)
            except LoaderError:
                continue
            if not _record_is_policy(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def validate_worker_container_policy(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one record against the Worker-Container Policy schema and predicates.

    Applies PCO-040 (schema validation) and PCO-045 (forbidden-mount
    and controller-key-secret refusal).
    """
    errors: list[ValidationError] = []
    errors.extend(validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT))
    errors.extend(_check_forbidden_mounts(record, path))
    return errors


@register(CHECK_NAME, [CODE_SCHEMA, CODE_FORBIDDEN_MOUNT])
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_worker_container_policy_records(paths):
        try:
            record = load_yaml(record_path)
        except LoaderError as exc:
            errors.append(make_error(CODE_INVALID, record_path, "", str(exc), CONTRACT))
            continue
        if not isinstance(record, dict):
            errors.append(make_error(
                CODE_INVALID,
                record_path,
                "/",
                "worker-container-policy record must be a YAML mapping",
                CONTRACT,
            ))
            continue
        errors.extend(validate_worker_container_policy(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
