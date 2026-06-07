"""Runtime Policy schema validation and plane-C safety predicates (v3 G-1.0).

Validates Runtime Policy records against
``schemas/runtime-policy.schema.yaml`` and enforces the plane-C
runtime-safety predicates. This is the v3 translation of the kept v2
``worker_container_policy`` check (PCO-040 / PCO-045): the record shape
and its safety defaults are lifted; the v2 runtime engine wiring is
dropped (adopt-and-drop).

Scope (G-1.0 — substrate / record-shape only):

* schema validation — every Runtime Policy record MUST validate against
  the runtime-policy schema; and
* the runtime-policy safety predicates, each with an explicit error
  class: image digest-pin, image-name credential refusal, forbidden
  mount refusal, rw-mount justification, names-only secret refusal, and
  deny-by-default egress.

v3 G-4 (additive): the schema gained two OPTIONAL plane-C fields the
audit-overlay classifier/control-point consume at runtime —
``action_class_allowlist`` (per ``(op, mutation_class)`` grants) and
``gate_mode_ladder`` (the gate-mode + ``always_*`` precedence rules). They
are schema-validated here (shape only); a record WITHOUT them remains a
valid G-1.0 policy. This check enforces only their shape — the gate
*semantics* live in ``runner.audit_overlay`` (``classify`` / ``decide``).

This check is **defensive** — it hardens the Creator Engine's own agent
runtime. It NEVER allocates a container, invokes gVisor/Podman/Docker/
OpenShell, opens a network socket, or implements an egress proxy. Live
runtime is G-1.1 (adapter) / G-1.2 (gVisor + proxy) / G-1.3 (overlay).

A file is treated as a candidate Runtime Policy record when it
satisfies all of:

* YAML extension (``.yml`` / ``.yaml``);
* not under a ``schemas/`` or ``templates/`` directory;
* its path basename does NOT contain ``".tmp."`` (atomic-write temp
  files are skipped);
* the loaded YAML is a mapping whose ``kind`` field equals
  ``runtime-policy-record``.

Failures cite the offending error class and the prose contract at
``docs/contracts/runtime-policy.md``.

See:
  - ``docs/contracts/runtime-policy.md``
  - ``schemas/runtime-policy.schema.yaml``
  - ``docs/operations/WORKER_CONTAINER_PROTOCOL.md`` (v2 provenance)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from ..loader import LoaderError, load_yaml
from ..reporting import CheckResult, ValidationError, make_error
from ..schema import validate_with_schema
from . import register

CHECK_NAME = "ce_runtime_policy"
CONTRACT = "docs/contracts/runtime-policy.md"
SCHEMA = "schemas/runtime-policy.schema.yaml"
KIND_VALUE = "runtime-policy-record"

# Failure codes (explicit error classes, per the contract's predicate table).
CODE_SCHEMA = "runtime_policy_schema_violation"
CODE_INVALID = "runtime_policy_invalid_record"
CODE_IMAGE_NOT_DIGEST_PINNED = "runtime_policy_image_not_digest_pinned"
CODE_IMAGE_NAME_CREDENTIAL = "runtime_policy_image_name_carries_credential"
CODE_FORBIDDEN_MOUNT = "runtime_policy_forbidden_mount"
CODE_RW_WITHOUT_JUSTIFICATION = "runtime_policy_rw_mount_without_justification"
CODE_SECRET_NAMES_ONLY = "runtime_policy_secret_names_only_violation"
CODE_EGRESS_NOT_DENY_BY_DEFAULT = "runtime_policy_egress_not_deny_by_default"

# ---- image digest pin (sha256:<hex64>) ----
_IMAGE_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

# ---- forbidden mount patterns (translate PCO-045) ----
# Host home-directory indicators.
_HOME_PATTERNS = [
    re.compile(r"^\$HOME\b"),
    re.compile(r"^~/"),
    re.compile(r"^~$"),
]
# Container engine socket paths (docker / podman).
_ENGINE_SOCKET_SUBSTRINGS = [
    "/var/run/docker.sock",
    "/run/docker.sock",
    "/run/podman/podman.sock",
    "/var/run/podman/podman.sock",
]
_DOCKER_SOCK_RE = re.compile(r"docker\.sock$")
_PODMAN_SOCK_RE = re.compile(r"podman\.sock$")
# SSH/GPG agent + key material directories and agent sockets.
_SSH_DIR_RE = re.compile(r"(^|/)\.ssh($|/)")
_GNUPG_DIR_RE = re.compile(r"(^|/)\.gnupg($|/)")
_AGENT_SOCK_RE = re.compile(r"(^|/)[A-Za-z0-9._-]*-agent(\.sock)?($|/?$|/)")

# ---- image-name credential material (userinfo / embedded token) ----
_IMAGE_USERINFO_RE = re.compile(r"[^/@\s]+:[^/@\s]+@")

# ---- secret-name predicates (translate PCO-045) ----
# Names that are paths or values rather than bare secret names.
_SECRET_PATH_OR_VALUE_RE = re.compile(r"[/\s=]")
# Key-file extensions.
_SECRET_KEYFILE_RE = re.compile(r"\.(pem|key|p12|pfx|asc|crt)$", re.IGNORECASE)
# Controller-key private key (any separator, up to 10 chars between).
_CONTROLLER_KEY_RE = re.compile(r"controller.{0,10}key", re.IGNORECASE)
# Other private-key-shaped names.
_PRIVATE_KEY_RE = re.compile(r"private.{0,10}key", re.IGNORECASE)
_SSH_KEYNAME_RE = re.compile(r"\bid_(rsa|ed25519|ecdsa|dsa)\b", re.IGNORECASE)


def _is_under_excluded(path: Path) -> bool:
    parts = path.parts
    return "schemas" in parts or "templates" in parts


def _is_tmp_artifact(path: Path) -> bool:
    return ".tmp." in path.name


def _looks_like_yaml(path: Path) -> bool:
    return path.is_file() and path.suffix in {".yml", ".yaml"}


def _record_is_runtime_policy(record: Any) -> bool:
    return isinstance(record, dict) and record.get("kind") == KIND_VALUE


def _forbidden_mount_reason(path_str: str) -> str | None:
    """Return a human-readable reason if ``path_str`` is a forbidden mount."""
    for pattern in _HOME_PATTERNS:
        if pattern.match(path_str):
            return "host home-directory path"
    for substr in _ENGINE_SOCKET_SUBSTRINGS:
        if path_str == substr or path_str.startswith(substr):
            return "container-engine socket"
    if _DOCKER_SOCK_RE.search(path_str) or _PODMAN_SOCK_RE.search(path_str):
        return "container-engine socket"
    if _SSH_DIR_RE.search(path_str):
        return "SSH key / agent directory"
    if _GNUPG_DIR_RE.search(path_str):
        return "GPG key / agent directory"
    if _AGENT_SOCK_RE.search(path_str):
        return "credential-agent socket"
    return None


def _image_name_carries_credential(name: str) -> bool:
    if _IMAGE_USERINFO_RE.search(name):
        return True
    # The digest belongs in the separate ``sha`` field; an ``@`` in the
    # name signals embedded reference material / userinfo.
    return "@" in name


def _secret_violation_reason(name: str) -> str | None:
    """Return a reason if a secret-allowlist entry violates names-only."""
    if name.startswith("~") or name.startswith("$") or _SECRET_PATH_OR_VALUE_RE.search(name):
        return "is a path or value, not a bare secret name"
    if _SECRET_KEYFILE_RE.search(name):
        return "is a key-file name, not a bare secret name"
    if _CONTROLLER_KEY_RE.search(name):
        return "names the controller-key private key"
    if _PRIVATE_KEY_RE.search(name) or _SSH_KEYNAME_RE.search(name):
        return "names a private key"
    return None


def _check_image(record: dict[str, Any], path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    image_ref = record.get("image_ref")
    if not isinstance(image_ref, dict):
        return errors  # schema validation owns missing / mistyped image_ref
    sha = image_ref.get("sha")
    if not isinstance(sha, str) or not _IMAGE_DIGEST_RE.match(sha):
        errors.append(make_error(
            CODE_IMAGE_NOT_DIGEST_PINNED,
            path,
            "image_ref/sha",
            (
                "image is not digest-pinned: image_ref.sha is absent or not a "
                "'sha256:<hex64>' digest; the runtime MUST run an exact, "
                "content-addressed image"
            ),
            CONTRACT,
        ))
    name = image_ref.get("name")
    if isinstance(name, str) and _image_name_carries_credential(name):
        errors.append(make_error(
            CODE_IMAGE_NAME_CREDENTIAL,
            path,
            "image_ref/name",
            (
                "image name carries credential material (userinfo / embedded '@' / "
                "token); image references MUST NOT embed credentials"
            ),
            CONTRACT,
        ))
    return errors


def _check_mounts(record: dict[str, Any], path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    mount_manifest = record.get("mount_manifest")
    if not isinstance(mount_manifest, list):
        return errors
    for index, entry in enumerate(mount_manifest):
        if not isinstance(entry, dict):
            continue
        mount_path = entry.get("path")
        if isinstance(mount_path, str):
            reason = _forbidden_mount_reason(mount_path)
            if reason:
                errors.append(make_error(
                    CODE_FORBIDDEN_MOUNT,
                    path,
                    f"mount_manifest[{index}][path={mount_path!r}]",
                    (
                        f"forbidden mount: {reason}; the runtime MUST NOT bind host "
                        "home directories, container-engine sockets, or SSH/GPG agent "
                        "sockets (translates PCO-045)"
                    ),
                    CONTRACT,
                ))
        if entry.get("mode") == "rw":
            justification = entry.get("write_justification")
            if not (isinstance(justification, str) and justification.strip()):
                errors.append(make_error(
                    CODE_RW_WITHOUT_JUSTIFICATION,
                    path,
                    f"mount_manifest[{index}]",
                    "rw mount requires a non-empty write_justification",
                    CONTRACT,
                ))
    return errors


def _check_secret_allowlist(record: dict[str, Any], path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    secret_allowlist = record.get("secret_allowlist")
    if not isinstance(secret_allowlist, list):
        return errors
    for name in secret_allowlist:
        if not isinstance(name, str):
            continue
        reason = _secret_violation_reason(name)
        if reason:
            errors.append(make_error(
                CODE_SECRET_NAMES_ONLY,
                path,
                f"secret_allowlist[name={name!r}]",
                (
                    f"secret allowlist entry {reason}; entries MUST be bare secret "
                    "names — never values, paths, or the controller-key / a private "
                    "key (translates PCO-045)"
                ),
                CONTRACT,
            ))
    return errors


def _check_egress(record: dict[str, Any], path: Path) -> list[ValidationError]:
    errors: list[ValidationError] = []
    egress_allowlist = record.get("egress_allowlist")
    if not isinstance(egress_allowlist, list):
        return errors
    # An empty allowlist declares no-egress — the deny-by-default floor — and is valid.
    for index, rule in enumerate(egress_allowlist):
        if not isinstance(rule, dict):
            continue
        host = rule.get("host")
        if not (isinstance(host, str) and host.strip()):
            errors.append(make_error(
                CODE_EGRESS_NOT_DENY_BY_DEFAULT,
                path,
                f"egress_allowlist[{index}]",
                "egress rule missing 'host'; deny-by-default requires every rule name its target host",
                CONTRACT,
            ))
            continue
        assurance = rule.get("assurance")
        if isinstance(assurance, list) and "l7" in assurance:
            if rule.get("tls_terminated") is not True:
                errors.append(make_error(
                    CODE_EGRESS_NOT_DENY_BY_DEFAULT,
                    path,
                    f"egress_allowlist[{index}]",
                    "l7-assured egress rule MUST set tls_terminated: true",
                    CONTRACT,
                ))
    return errors


def iter_runtime_policy_records(paths: Iterable[Path]) -> list[Path]:
    """Return candidate Runtime Policy files under ``paths``."""
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
            if not _record_is_runtime_policy(data):
                continue
            seen.add(resolved)
            records.append(candidate)
    return records


def validate_runtime_policy(record: dict[str, Any], path: Path) -> list[ValidationError]:
    """Validate one record against the Runtime Policy schema and safety predicates."""
    errors: list[ValidationError] = []
    errors.extend(validate_with_schema(record, SCHEMA, path, code=CODE_SCHEMA, contract=CONTRACT))
    errors.extend(_check_image(record, path))
    errors.extend(_check_mounts(record, path))
    errors.extend(_check_secret_allowlist(record, path))
    errors.extend(_check_egress(record, path))
    return errors


@register(
    CHECK_NAME,
    [
        CODE_SCHEMA,
        CODE_IMAGE_NOT_DIGEST_PINNED,
        CODE_IMAGE_NAME_CREDENTIAL,
        CODE_FORBIDDEN_MOUNT,
        CODE_RW_WITHOUT_JUSTIFICATION,
        CODE_SECRET_NAMES_ONLY,
        CODE_EGRESS_NOT_DENY_BY_DEFAULT,
    ],
)
def run(paths: Iterable[Path]) -> CheckResult:
    errors: list[ValidationError] = []
    for record_path in iter_runtime_policy_records(paths):
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
                "runtime-policy record must be a YAML mapping",
                CONTRACT,
            ))
            continue
        errors.extend(validate_runtime_policy(record, record_path))
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
