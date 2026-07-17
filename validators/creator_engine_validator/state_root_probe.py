"""Fail-closed, descriptor-pinned controller state-root durability probe.

The writable mode proves only local filesystem structure and nonce durability.
It is not a lease, fence, controller identity, or authority grant.
"""
from __future__ import annotations

import errno
import hashlib
import hmac
import json
import os
import secrets
import stat
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

__ce_version_line__ = "shared"

PROBE_KIND = "ce-state-root-durability-probe"
PROBE_VERSION = 1
NONCE_PREFIX = ".ce-state-root-probe-nonce."
_ACL_NAMES = frozenset({"system.posix_acl_access", "system.posix_acl_default"})
_ERROR_ORDER = (
    "SRP-MISSING",
    "SRP-NOT-REAL-DIR",
    "SRP-UNSUPPORTED",
    "SRP-ANCESTOR-UNSAFE",
    "SRP-OWNER",
    "SRP-MODE",
    "SRP-ACL",
    "SRP-ENTRY-TYPE",
    "SRP-FOREIGN-WRITER",
    "SRP-RACE",
    "SRP-NONCE-RESIDUE",
    "SRP-NONCE-CREATE",
    "SRP-NONCE-WRITE",
    "SRP-NONCE-FSYNC",
    "SRP-NONCE-READ",
    "SRP-NONCE-MISMATCH",
    "SRP-NONCE-UNLINK",
    "SRP-PATH-REVALIDATE",
)

ProbeMode = Literal["writable-boot", "read-only-diagnostic"]


@dataclass(frozen=True)
class _Violation:
    code: str
    relative_path_hash: str
    observed_type: str
    observed_uid: int | None
    observed_mode: int | None

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "relative_path_hash": self.relative_path_hash,
            "observed_type": self.observed_type,
            "observed_uid": self.observed_uid,
            "observed_mode": self.observed_mode,
        }


@dataclass(frozen=True)
class StateRootProbeResult:
    kind: str = PROBE_KIND
    version: int = PROBE_VERSION
    mode: ProbeMode = "read-only-diagnostic"
    status: str = "not-proven"
    writable_durability: str = "not-proven"
    error_codes: tuple[str, ...] = ()
    expected_uid: int = 0
    root_identity_sha256: str = ""
    entry_count: int = 0
    foreign_writer_count: int = 0
    violation_digest: str | None = None
    same_filesystem: bool = False
    nonce_created: bool = False
    nonce_fsynced: bool = False
    nonce_verified: bool = False
    nonce_unlinked: bool = False
    directory_fsynced_after_unlink: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "version": self.version,
            "mode": self.mode,
            "status": self.status,
            "writable_durability": self.writable_durability,
            "error_codes": list(self.error_codes),
            "expected_uid": self.expected_uid,
            "root_identity_sha256": self.root_identity_sha256,
            "entry_count": self.entry_count,
            "foreign_writer_count": self.foreign_writer_count,
            "violation_digest": self.violation_digest,
            "same_filesystem": self.same_filesystem,
            "nonce_created": self.nonce_created,
            "nonce_fsynced": self.nonce_fsynced,
            "nonce_verified": self.nonce_verified,
            "nonce_unlinked": self.nonce_unlinked,
            "directory_fsynced_after_unlink": self.directory_fsynced_after_unlink,
        }


class StateRootProbeRefused(RuntimeError):
    """Writable state-root use was refused before controller mutation."""

    code = "CE-STATE-ROOT-PROBE-REFUSED"

    def __init__(self, result: StateRootProbeResult):
        self.result = result
        codes = ",".join(result.error_codes) or "SRP-UNSUPPORTED"
        super().__init__(f"state-root durability probe refused ({codes})")

    @classmethod
    def for_code(
        cls,
        code: str,
        *,
        state_root: Path | str,
        expected_uid: int,
        mode: ProbeMode,
    ) -> "StateRootProbeRefused":
        lexical = _lexical_absolute(state_root)
        return cls(
            StateRootProbeResult(
                mode=mode,
                status="refused",
                expected_uid=expected_uid,
                root_identity_sha256=_identity_digest(lexical, None),
                error_codes=(code,),
            )
        )


class _ProbeFailure(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _lexical_absolute(path: Path | str) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _identity_digest(path: Path, identity: tuple[int, int] | None) -> str:
    dev, ino = identity if identity is not None else ("missing", "missing")
    return hashlib.sha256(f"{dev}:{ino}:{path}".encode("utf-8")).hexdigest()


def _path_hash(relative_path: str) -> str:
    return hashlib.sha256(relative_path.encode("utf-8")).hexdigest()


def _ordered_codes(codes: set[str]) -> tuple[str, ...]:
    return tuple(code for code in _ERROR_ORDER if code in codes)


def _violation_digest(violations: list[_Violation]) -> str | None:
    if not violations:
        return None
    records = [item.to_dict() for item in sorted(violations, key=lambda item: (item.code, item.relative_path_hash))]
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _file_type(st_mode: int) -> str:
    if stat.S_ISDIR(st_mode):
        return "directory"
    if stat.S_ISREG(st_mode):
        return "regular"
    if stat.S_ISLNK(st_mode):
        return "symlink"
    if stat.S_ISFIFO(st_mode):
        return "fifo"
    if stat.S_ISSOCK(st_mode):
        return "socket"
    if stat.S_ISCHR(st_mode):
        return "character-device"
    if stat.S_ISBLK(st_mode):
        return "block-device"
    return "unknown"


def _require_primitives() -> None:
    required_constants = ("O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC")
    if os.name != "posix" or any(not hasattr(os, name) for name in required_constants):
        raise _ProbeFailure("SRP-UNSUPPORTED")
    if os.stat not in os.supports_dir_fd or os.open not in os.supports_dir_fd:
        raise _ProbeFailure("SRP-UNSUPPORTED")
    if os.unlink not in os.supports_dir_fd or os.stat not in os.supports_follow_symlinks:
        raise _ProbeFailure("SRP-UNSUPPORTED")
    if not callable(getattr(os, "listxattr", None)) or not callable(getattr(os, "fsync", None)):
        raise _ProbeFailure("SRP-UNSUPPORTED")


def _acl_present(fd: int) -> bool:
    try:
        attrs = os.listxattr(fd)
    except (AttributeError, NotImplementedError, TypeError, OSError) as exc:
        raise _ProbeFailure("SRP-UNSUPPORTED") from exc
    return bool(_ACL_NAMES.intersection(attrs))


def _open_component(parent_fd: int, name: str, *, final: bool) -> tuple[int, os.stat_result]:
    try:
        before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError as exc:
        raise _ProbeFailure("SRP-MISSING" if final else "SRP-NOT-REAL-DIR") from exc
    except OSError as exc:
        raise _ProbeFailure("SRP-NOT-REAL-DIR") from exc
    if not stat.S_ISDIR(before.st_mode):
        raise _ProbeFailure("SRP-NOT-REAL-DIR")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        fd = os.open(name, flags, dir_fd=parent_fd)
    except OSError as exc:
        raise _ProbeFailure("SRP-NOT-REAL-DIR") from exc
    try:
        after = os.fstat(fd)
    except OSError as exc:
        os.close(fd)
        raise _ProbeFailure("SRP-RACE") from exc
    if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
        os.close(fd)
        raise _ProbeFailure("SRP-RACE")
    return fd, after


def _walk_root(path: Path, expected_uid: int) -> tuple[int, os.stat_result, list[_Violation]]:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    try:
        current_fd = os.open("/", flags)
    except OSError as exc:
        raise _ProbeFailure("SRP-UNSUPPORTED") from exc
    violations: list[_Violation] = []
    components = path.parts[1:]
    if not components:
        os.close(current_fd)
        raise _ProbeFailure("SRP-NOT-REAL-DIR")
    try:
        for index, component in enumerate(components):
            final = index == len(components) - 1
            child_fd, child_stat = _open_component(current_fd, component, final=final)
            try:
                parent_stat = os.fstat(current_fd)
            except OSError as exc:
                os.close(child_fd)
                raise _ProbeFailure("SRP-RACE") from exc
            parent_mode = stat.S_IMODE(parent_stat.st_mode)
            writable = bool(parent_mode & 0o022)
            sticky_safe = bool(parent_mode & stat.S_ISVTX) and child_stat.st_uid in {0, expected_uid}
            owner_safe = parent_stat.st_uid in {0, expected_uid}
            try:
                parent_acl = _acl_present(current_fd)
            except _ProbeFailure:
                os.close(child_fd)
                raise
            if not owner_safe or (writable and not sticky_safe) or parent_acl:
                violations.append(
                    _Violation(
                        code="SRP-ANCESTOR-UNSAFE",
                        relative_path_hash=_path_hash(f"ancestor:{index}"),
                        observed_type="directory",
                        observed_uid=parent_stat.st_uid,
                        observed_mode=parent_mode,
                    )
                )
                if parent_acl:
                    violations.append(
                        _Violation(
                            code="SRP-ACL",
                            relative_path_hash=_path_hash(f"ancestor-acl:{index}"),
                            observed_type="directory",
                            observed_uid=parent_stat.st_uid,
                            observed_mode=parent_mode,
                        )
                    )
            os.close(current_fd)
            current_fd = child_fd
        return current_fd, child_stat, violations
    except Exception:
        os.close(current_fd)
        raise


def _append_metadata_violations(
    violations: list[_Violation],
    *,
    relative_path: str,
    metadata: os.stat_result,
    expected_uid: int,
    expected_modes: frozenset[int],
    fd: int,
) -> None:
    kind = _file_type(metadata.st_mode)
    mode = stat.S_IMODE(metadata.st_mode)
    if metadata.st_uid != expected_uid:
        violations.append(_Violation("SRP-OWNER", _path_hash(relative_path), kind, metadata.st_uid, mode))
    if mode not in expected_modes:
        violations.append(_Violation("SRP-MODE", _path_hash(relative_path), kind, metadata.st_uid, mode))
    if _acl_present(fd):
        violations.append(_Violation("SRP-ACL", _path_hash(relative_path), kind, metadata.st_uid, mode))


def _enumerate_tree(root_fd: int, expected_uid: int) -> tuple[int, list[_Violation]]:
    violations: list[_Violation] = []
    entry_count = 0
    try:
        root_stat = os.fstat(root_fd)
    except OSError as exc:
        raise _ProbeFailure("SRP-RACE") from exc
    _append_metadata_violations(
        violations,
        relative_path=".",
        metadata=root_stat,
        expected_uid=expected_uid,
        expected_modes=frozenset({0o700}),
        fd=root_fd,
    )

    def visit(directory_fd: int, prefix: str) -> None:
        nonlocal entry_count
        try:
            names = sorted(os.listdir(directory_fd))
        except (TypeError, NotImplementedError, OSError) as exc:
            raise _ProbeFailure("SRP-UNSUPPORTED") from exc
        for name in names:
            relative = f"{prefix}/{name}" if prefix else name
            entry_count += 1
            try:
                before = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            except OSError as exc:
                raise _ProbeFailure("SRP-RACE") from exc
            kind = _file_type(before.st_mode)
            mode = stat.S_IMODE(before.st_mode)
            if name.startswith(NONCE_PREFIX):
                violations.append(
                    _Violation("SRP-NONCE-RESIDUE", _path_hash(relative), kind, before.st_uid, mode)
                )
            if not (stat.S_ISDIR(before.st_mode) or stat.S_ISREG(before.st_mode)):
                violations.append(
                    _Violation("SRP-ENTRY-TYPE", _path_hash(relative), kind, before.st_uid, mode)
                )
                continue
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
            if stat.S_ISDIR(before.st_mode):
                flags |= os.O_DIRECTORY
            try:
                child_fd = os.open(name, flags, dir_fd=directory_fd)
            except OSError as exc:
                raise _ProbeFailure("SRP-RACE") from exc
            try:
                try:
                    after = os.fstat(child_fd)
                except OSError as exc:
                    raise _ProbeFailure("SRP-RACE") from exc
                if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                    raise _ProbeFailure("SRP-RACE")
                _append_metadata_violations(
                    violations,
                    relative_path=relative,
                    metadata=after,
                    expected_uid=expected_uid,
                    expected_modes=frozenset({0o700}) if stat.S_ISDIR(after.st_mode) else frozenset({0o600, 0o700}),
                    fd=child_fd,
                )
                if stat.S_ISDIR(after.st_mode):
                    visit(child_fd, relative)
            finally:
                os.close(child_fd)

    visit(root_fd, "")
    return entry_count, violations


def _base_result(
    *,
    path: Path,
    expected_uid: int,
    mode: ProbeMode,
    root_stat: os.stat_result | None,
    entry_count: int = 0,
    violations: list[_Violation] | None = None,
    extra_codes: set[str] | None = None,
) -> StateRootProbeResult:
    violations = violations or []
    codes = {item.code for item in violations} | set(extra_codes or ())
    foreign_codes = {
        "SRP-ANCESTOR-UNSAFE",
        "SRP-OWNER",
        "SRP-MODE",
        "SRP-ACL",
        "SRP-ENTRY-TYPE",
        "SRP-RACE",
    }
    foreign_count = sum(1 for item in violations if item.code in foreign_codes)
    if foreign_count:
        codes.add("SRP-FOREIGN-WRITER")
    identity = None if root_stat is None else (root_stat.st_dev, root_stat.st_ino)
    return StateRootProbeResult(
        mode=mode,
        status="refused" if codes else "not-proven",
        expected_uid=expected_uid,
        root_identity_sha256=_identity_digest(path, identity),
        entry_count=entry_count,
        foreign_writer_count=foreign_count,
        violation_digest=_violation_digest(violations),
        error_codes=_ordered_codes(codes),
    )


def _raise_if_writable_refused(result: StateRootProbeResult) -> StateRootProbeResult:
    if result.mode == "writable-boot" and result.status != "pass":
        raise StateRootProbeRefused(result)
    return result


def _directory_fsync_failure_code(exc: OSError) -> str:
    unsupported = {errno.EINVAL, errno.ENOSYS}
    unsupported.add(getattr(errno, "ENOTSUP", errno.EINVAL))
    unsupported.add(getattr(errno, "EOPNOTSUPP", errno.EINVAL))
    return "SRP-UNSUPPORTED" if exc.errno in unsupported else "SRP-NONCE-FSYNC"


def _revalidate_path(path: Path, expected_identity: tuple[int, int], expected_uid: int) -> None:
    fd: int | None = None
    try:
        fd, metadata, violations = _walk_root(path, expected_uid)
        if violations:
            raise _ProbeFailure("SRP-PATH-REVALIDATE")
        if (metadata.st_dev, metadata.st_ino) != expected_identity:
            raise _ProbeFailure("SRP-PATH-REVALIDATE")
    except _ProbeFailure as exc:
        if exc.code in {"SRP-RACE", "SRP-NOT-REAL-DIR", "SRP-MISSING"}:
            raise _ProbeFailure("SRP-PATH-REVALIDATE") from exc
        raise
    finally:
        if fd is not None:
            os.close(fd)


def _run_nonce(root_fd: int, root_stat: os.stat_result, result: StateRootProbeResult) -> StateRootProbeResult:
    nonce = secrets.token_bytes(32)
    name = NONCE_PREFIX + secrets.token_hex(16)
    fd: int | None = None
    created = False
    unlinked = False
    current = result
    failure: str | None = None
    try:
        try:
            fd = os.open(
                name,
                os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                0o600,
                dir_fd=root_fd,
            )
            created = True
            current = replace(current, nonce_created=True)
        except OSError:
            failure = "SRP-NONCE-CREATE"
            return replace(current, status="refused", error_codes=(failure,))

        try:
            nonce_stat = os.fstat(fd)
        except OSError:
            failure = "SRP-RACE"
            nonce_stat = None
        if nonce_stat is not None and (
            not stat.S_ISREG(nonce_stat.st_mode)
            or nonce_stat.st_uid != result.expected_uid
            or stat.S_IMODE(nonce_stat.st_mode) != 0o600
            or nonce_stat.st_dev != root_stat.st_dev
        ):
            failure = "SRP-RACE"
        elif nonce_stat is not None:
            current = replace(current, same_filesystem=True)

        if failure is None:
            offset = 0
            try:
                while offset < len(nonce):
                    written = os.write(fd, nonce[offset:])
                    if written <= 0:
                        raise OSError(errno.EIO, "short nonce write")
                    offset += written
            except OSError:
                failure = "SRP-NONCE-WRITE"

        if failure is None:
            try:
                os.fsync(fd)
                current = replace(current, nonce_fsynced=True)
            except OSError:
                failure = "SRP-NONCE-FSYNC"

        received = bytearray()
        if failure is None:
            try:
                os.lseek(fd, 0, os.SEEK_SET)
                while len(received) < len(nonce) + 1:
                    chunk = os.read(fd, len(nonce) + 1 - len(received))
                    if not chunk:
                        break
                    received.extend(chunk)
            except OSError:
                failure = "SRP-NONCE-READ"
        if failure is None:
            if len(received) != len(nonce) or not hmac.compare_digest(bytes(received), nonce):
                failure = "SRP-NONCE-MISMATCH"
            else:
                current = replace(current, nonce_verified=True)

        if failure is None:
            try:
                os.fsync(root_fd)
            except OSError as exc:
                failure = _directory_fsync_failure_code(exc)
    finally:
        if fd is not None:
            os.close(fd)
        if created:
            try:
                os.unlink(name, dir_fd=root_fd)
                unlinked = True
                current = replace(current, nonce_unlinked=True)
            except OSError:
                if failure is None:
                    failure = "SRP-NONCE-UNLINK"
            if unlinked:
                try:
                    os.fsync(root_fd)
                    current = replace(current, directory_fsynced_after_unlink=True)
                except OSError as exc:
                    if failure is None:
                        failure = _directory_fsync_failure_code(exc)
    if failure is not None:
        return replace(current, status="refused", error_codes=_ordered_codes({failure}))
    return current


def probe_state_root(
    state_root: Path | str,
    *,
    expected_uid: int,
    mode: ProbeMode,
) -> StateRootProbeResult:
    """Validate a controller state root and optionally prove nonce durability."""

    if mode not in {"writable-boot", "read-only-diagnostic"}:
        raise ValueError(f"unsupported state-root probe mode: {mode!r}")
    path = _lexical_absolute(state_root)
    root_fd: int | None = None
    root_stat: os.stat_result | None = None
    try:
        try:
            _require_primitives()
            root_fd, root_stat, ancestor_violations = _walk_root(path, expected_uid)
            entry_count, tree_violations = _enumerate_tree(root_fd, expected_uid)
        except _ProbeFailure as exc:
            result = _base_result(
                path=path,
                expected_uid=expected_uid,
                mode=mode,
                root_stat=root_stat,
                extra_codes={exc.code},
            )
            return _raise_if_writable_refused(result)

        violations = [*ancestor_violations, *tree_violations]
        extra_codes: set[str] = set()
        if mode == "writable-boot" and os.geteuid() != expected_uid:
            extra_codes.add("SRP-OWNER")
        result = _base_result(
            path=path,
            expected_uid=expected_uid,
            mode=mode,
            root_stat=root_stat,
            entry_count=entry_count,
            violations=violations,
            extra_codes=extra_codes,
        )
        if result.error_codes:
            return _raise_if_writable_refused(result)
        if mode == "read-only-diagnostic":
            try:
                after = os.fstat(root_fd)
                if (after.st_dev, after.st_ino) != (root_stat.st_dev, root_stat.st_ino):
                    raise _ProbeFailure("SRP-RACE")
                _revalidate_path(path, (root_stat.st_dev, root_stat.st_ino), expected_uid)
            except OSError:
                return replace(result, status="refused", error_codes=("SRP-RACE",))
            except _ProbeFailure as exc:
                return replace(result, status="refused", error_codes=_ordered_codes({exc.code}))
            return result

        result = _run_nonce(root_fd, root_stat, result)
        if result.status == "refused":
            raise StateRootProbeRefused(result)
        try:
            after = os.fstat(root_fd)
            if (after.st_dev, after.st_ino) != (root_stat.st_dev, root_stat.st_ino):
                raise _ProbeFailure("SRP-RACE")
            try:
                residue_present = any(
                    name.startswith(NONCE_PREFIX) for name in os.listdir(root_fd)
                )
            except (TypeError, NotImplementedError, OSError) as exc:
                raise _ProbeFailure("SRP-PATH-REVALIDATE") from exc
            if residue_present:
                raise _ProbeFailure("SRP-NONCE-RESIDUE")
            _revalidate_path(path, (root_stat.st_dev, root_stat.st_ino), expected_uid)
        except OSError as exc:
            raise StateRootProbeRefused(
                replace(result, status="refused", error_codes=("SRP-RACE",))
            ) from exc
        except _ProbeFailure as exc:
            raise StateRootProbeRefused(
                replace(result, status="refused", error_codes=_ordered_codes({exc.code}))
            ) from exc
        return replace(result, status="pass", writable_durability="proven")
    finally:
        if root_fd is not None:
            os.close(root_fd)
