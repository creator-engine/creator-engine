"""Discovery runner for conveyor READY-FOR-HARVEST seat signals."""

from __future__ import annotations

import json
import hashlib
import errno
import os
import re
import secrets
import stat
import subprocess
import sys
import fcntl
from collections.abc import Callable, Iterable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .checks.path_manifest_fidelity import branch_slug
from .pickup_payload_schema import DiscoveryPayloadRejected, validate_discovery_payload

AuditSink = Callable[[Mapping[str, Any]], None]
ProbeRunner = Callable[[Sequence[str]], str]

READY_TOKEN = "READY-FOR-HARVEST"
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
RECEIPT_VERSION = 1
RECEIPT_STATES = frozenset({"observed", "processing", "pr_opened", "failed", "uncertain"})
RECEIPT_TERMINAL_STATES = frozenset({"pr_opened", "failed", "uncertain"})
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
DIFF_ECHO_PATTERN = re.compile(r"^\s*(?:\d+\s*[: ]?\s*)?\+\s*READY-FOR-HARVEST\b")
SIGNAL_PREFIX_PATTERN = re.compile(r"^\s*(?:[•\-*>]\s*)?READY-FOR-HARVEST\b")
SIGNAL_TAIL_PATTERN = re.compile(r"\s+(?P<branch>\S+)\s+(?P<sha>\S+)")
ISSUE_PREFIX_PATTERN = re.compile(r"^ce-(?P<issue>\d+)-")


class ReceiptPersistenceError(ValueError):
    """Receipt storage could not be proven private, authentic, and persistent."""


class ReceiptDurabilityUncertainError(ReceiptPersistenceError):
    """A terminal receipt replacement may be visible but was not proven durable."""


def normalize_receipt_state_path(state_path: str | Path) -> Path:
    """Return one lexical absolute receipt path without following any link."""

    raw = os.fspath(state_path)
    if not isinstance(raw, str) or "\x00" in raw or not raw.startswith("/"):
        raise ReceiptPersistenceError("receipt_state_path_invalid")
    components = raw.split("/")
    if any(component in {".", ".."} for component in components):
        raise ReceiptPersistenceError("receipt_state_path_invalid")
    normalized = "/" + "/".join(component for component in components if component)
    if normalized == "/" or raw.endswith("/"):
        raise ReceiptPersistenceError("receipt_state_path_invalid")
    if isinstance(state_path, Path) and str(state_path) == normalized:
        return state_path
    return Path(normalized)


@dataclass(frozen=True)
class SeatProbeSpec:
    """Daemon-owned probe command for one seat pane."""

    seat_id: str
    argv: Sequence[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "argv", tuple(self.argv))


@dataclass(frozen=True)
class ReadyForHarvestSignal:
    """Parsed, slug-validated conveyor harvest signal."""

    branch: str
    sha: str
    tag: str | None = None


@dataclass(frozen=True)
class HandledSignalReceipt:
    """Reference to one locally persisted, outcome-bound discovery signal."""

    state_path: Path
    seat_id: str
    branch: str
    sha: str
    audit_sink: AuditSink | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "state_path", normalize_receipt_state_path(self.state_path))

    def claim(self) -> bool:
        return _receipt_ledger(self.state_path, self.audit_sink).claim(self)

    def complete(self, state: str) -> bool:
        return _receipt_ledger(self.state_path, self.audit_sink).complete(self, state)


@dataclass(frozen=True)
class ReceiptIdentity:
    """Data-only coordinates for a receipt owned by the armed daemon."""

    seat_id: str
    branch: str
    sha: str

    def __post_init__(self) -> None:
        if not self.seat_id or not self.branch or SHA_PATTERN.fullmatch(self.sha) is None:
            raise ValueError("receipt_identity_invalid")

class ReceiptDiscoveryPayload(dict[str, str]):
    """Schema-shaped discovery data carrying receipt identity, never capability."""

    def __init__(self, payload: Mapping[str, str], receipt_identity: ReceiptIdentity) -> None:
        super().__init__(payload)
        self.receipt_identity = receipt_identity


class ConveyorSeatDiscoveryRunner:
    """DiscoveryRunner-compatible callable for live seat pane probes."""

    def __init__(
        self,
        specs: Iterable[SeatProbeSpec],
        state_path: str | Path,
        *,
        probe_runner: ProbeRunner | None = None,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self.specs = tuple(specs)
        self.state_path = normalize_receipt_state_path(state_path)
        self.probe_runner = probe_runner or subprocess_probe_runner
        self.audit_sink = audit_sink

    def __call__(self) -> Iterable[Mapping[str, str]]:
        ledger = _receipt_ledger(self.state_path, self.audit_sink)
        emitted: set[tuple[str, str, str]] = set()
        payloads: list[Mapping[str, str]] = []

        for spec in self.specs:
            try:
                pane_text = self.probe_runner(spec.argv)
            except Exception as exc:  # pragma: no cover - exercised with fakes.
                _emit_audit(
                    self.audit_sink,
                    "probe_failed",
                    seat_id=spec.seat_id,
                    detail=type(exc).__name__,
                )
                continue

            signals = parse_ready_for_harvest_signals(
                pane_text,
                audit_sink=self.audit_sink,
                seat_id=spec.seat_id,
            )
            for signal in signals:
                key = (spec.seat_id, signal.branch, signal.sha)
                if key in emitted:
                    continue

                payload = payload_for_signal(signal, seat_id=spec.seat_id)
                try:
                    validate_discovery_payload(
                        payload,
                        audit_sink=self.audit_sink,
                        source="conveyor_discovery",
                    )
                except DiscoveryPayloadRejected:
                    continue

                try:
                    receipt = ledger.observe(*key)
                except ValueError as exc:
                    _emit_audit(
                        self.audit_sink,
                        "corrupt_receipt_state",
                        detail=type(exc).__name__,
                    )
                    return tuple(payloads)
                payloads.append(
                    ReceiptDiscoveryPayload(
                        payload,
                        ReceiptIdentity(receipt.seat_id, receipt.branch, receipt.sha),
                    )
                )
                emitted.add(key)

        return tuple(payloads)


def subprocess_probe_runner(argv: Sequence[str]) -> str:
    """Run a daemon-owned probe argv and return stdout. No shell is involved."""

    result = subprocess.run(
        tuple(argv),
        capture_output=True,
        check=True,
        text=True,
    )
    return result.stdout


def parse_ready_for_harvest_signals(
    pane_text: str,
    *,
    audit_sink: AuditSink | None = None,
    seat_id: str | None = None,
) -> tuple[ReadyForHarvestSignal, ...]:
    """Parse pane text into the last valid READY-FOR-HARVEST signal per branch."""

    cleaned = ANSI_ESCAPE_PATTERN.sub("", pane_text)
    by_branch: dict[str, ReadyForHarvestSignal] = {}

    for line_number, line_start, line in _iter_line_spans(cleaned):
        if READY_TOKEN not in line:
            continue

        if DIFF_ECHO_PATTERN.match(line):
            _emit_audit(
                audit_sink,
                "diff_echo",
                seat_id=seat_id,
                line_number=line_number,
            )
            continue

        prefix_match = SIGNAL_PREFIX_PATTERN.match(line)
        if prefix_match is None:
            _emit_audit(
                audit_sink,
                "non_signal_ready_echo",
                seat_id=seat_id,
                line_number=line_number,
            )
            continue

        tail_match = SIGNAL_TAIL_PATTERN.match(cleaned, line_start + prefix_match.end())
        if tail_match is None:
            _emit_audit(
                audit_sink,
                "malformed_signal",
                seat_id=seat_id,
                line_number=line_number,
            )
            continue

        branch = tail_match.group("branch")
        sha = tail_match.group("sha")
        if not SHA_PATTERN.fullmatch(sha):
            _emit_audit(
                audit_sink,
                "bad_sha",
                seat_id=seat_id,
                branch=branch,
                line_number=line_number,
                detail=_sha_detail(sha),
            )
            continue

        expected_slug = branch_slug(branch)
        if expected_slug != branch:
            _emit_audit(
                audit_sink,
                "slug_mismatch",
                seat_id=seat_id,
                branch=branch,
                expected_slug=expected_slug,
                line_number=line_number,
            )
            continue

        by_branch[branch] = ReadyForHarvestSignal(
            branch=branch,
            sha=sha,
            tag=_tag_on_sha_line(cleaned, tail_match.end()),
        )

    return tuple(by_branch.values())


def _iter_line_spans(text: str) -> Iterable[tuple[int, int, str]]:
    offset = 0
    for line_number, line in enumerate(text.splitlines(keepends=True), start=1):
        line_without_newline = line.rstrip("\r\n")
        yield line_number, offset, line_without_newline
        offset += len(line)
    if text == "" or text.endswith(("\n", "\r")):
        return


def payload_for_signal(signal: ReadyForHarvestSignal, *, seat_id: str) -> dict[str, str]:
    """Build the four-field data-only discovery payload for one signal."""

    issue = _issue_for_branch(signal.branch)
    return {
        "issue": issue,
        "branch_name": signal.branch,
        "pr_title": f"Conveyor harvest for {signal.branch}",
        "pr_body": (
            f"Conveyor discovered READY-FOR-HARVEST for {signal.branch}.\n\n"
            f"Issue: {issue}\n"
            f"Seat: {seat_id}\n"
            f"Commit SHA: {signal.sha}\n\n"
            "The commit SHA is informational text only; daemon authority remains configured outside "
            "this payload."
        ),
    }


def _issue_for_branch(branch: str) -> str:
    match = ISSUE_PREFIX_PATTERN.match(branch)
    if match is None:
        return "ce-conveyor"
    return match.group("issue")


def _tag_on_sha_line(text: str, offset: int) -> str | None:
    line_end = text.find("\n", offset)
    if line_end == -1:
        line_end = len(text)
    remainder = text[offset:line_end].strip()
    if not remainder:
        return None
    return remainder.split(maxsplit=1)[0]


class _SignalReceiptLedger:
    """Versioned local receipt store, serialised by an adjacent advisory lock."""

    def __init__(self, state_path: Path, audit_sink: AuditSink | None = None) -> None:
        self.state_path = state_path
        self.audit_sink = audit_sink

    def observe(self, seat_id: str, branch: str, sha: str) -> HandledSignalReceipt:
        receipt = HandledSignalReceipt(self.state_path, seat_id, branch, sha)
        with _locked_receipt_state(self.state_path) as locked:
            entries = _receipt_entries(locked.data)
            if _find_receipt(entries, receipt) is None:
                entries.append(_receipt_record(receipt, "observed"))
                locked.write(entries)
        return receipt

    def claim(self, receipt: HandledSignalReceipt) -> bool:
        with _locked_receipt_state(self.state_path) as locked:
            entries = _receipt_entries(locked.data)
            entry = _find_receipt(entries, receipt)
            if entry is None:
                return False
            if entry.get("completion_pending") is True:
                _emit_audit(
                    self.audit_sink,
                    "receipt_terminal_durability_unproven",
                    receipt_fingerprint=_receipt_fingerprint(receipt),
                )
                return False
            if entry.get("completion_sealed") is True:
                _emit_audit(
                    self.audit_sink,
                    "receipt_terminal_sealed",
                    receipt_fingerprint=_receipt_fingerprint(receipt),
                )
                return False
            if entry["state"] == "processing":
                _emit_audit(
                    self.audit_sink,
                    "receipt_processing_recovery_required",
                    receipt_fingerprint=_receipt_fingerprint(receipt),
                )
                return False
            if entry["state"] != "observed":
                return False
            entry["state"] = "processing"
            locked.write(entries)
            return True

    def complete(self, receipt: HandledSignalReceipt, state: str) -> bool:
        if state not in RECEIPT_TERMINAL_STATES:
            raise ValueError("receipt_completion_must_be_terminal")
        with _locked_receipt_state(self.state_path) as locked:
            entries = _receipt_entries(locked.data)
            entry = _find_receipt(entries, receipt)
            if (
                entry is None
                or entry["state"] != "processing"
                or entry.get("completion_pending") is True
            ):
                return False
            entry["state"] = state
            entry["completion_sealed"] = True
            locked.write(entries)
            return True


def _receipt_ledger(state_path: Path, audit_sink: AuditSink | None = None) -> _SignalReceiptLedger:
    return _SignalReceiptLedger(normalize_receipt_state_path(state_path), audit_sink)


_OPEN_DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
_OPEN_FILE_FLAGS = getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
_TEMP_ATTEMPTS = 32
_MAX_LEDGER_BYTES = 16 * 1024 * 1024
_RECEIPT_DIR_FD_SYSCALLS = (os.open, os.stat, os.mkdir, os.rename, os.replace, os.unlink)


def _receipt_syscalls_supported() -> bool:
    # CPython documents ``replace`` with the same ``renameat`` dirfd support
    # as ``rename``; accept that equivalence when ``replace`` is absent from
    # ``supports_dir_fd``.
    return (
        all(hasattr(os, name) for name in ("O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC"))
        and all(
            function in os.supports_dir_fd
            or (function is os.replace and os.rename in os.supports_dir_fd)
            for function in _RECEIPT_DIR_FD_SYSCALLS
        )
        and os.stat in os.supports_follow_symlinks
    )


_RECEIPT_SYSCALLS_SUPPORTED = _receipt_syscalls_supported()
def _require_receipt_syscalls() -> None:
    if not _RECEIPT_SYSCALLS_SUPPORTED:
        raise ReceiptPersistenceError("receipt_platform_unsupported")
def _same_inode(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)
def _close_fd(fd: int) -> OSError | None:
    try:
        os.close(fd)
    except OSError as exc:
        return exc
    return None
def _stat_at(directory_fd: int, name: str) -> os.stat_result:
    return os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
def _validate_directory(metadata: os.stat_result, daemon_uid: int, *, private: bool) -> None:
    unsafe = not stat.S_ISDIR(metadata.st_mode) or (metadata.st_uid != daemon_uid or stat.S_IMODE(metadata.st_mode) != 0o700 if private else metadata.st_uid not in {0, daemon_uid} or bool(metadata.st_mode & 0o022 and not metadata.st_mode & stat.S_ISVTX))
    if unsafe:
        raise ReceiptPersistenceError("receipt_private_directory_unsafe" if private else "receipt_ancestor_unsafe")
def _validate_private_file(metadata: os.stat_result, daemon_uid: int, *, exact_mode: int | None = 0o600) -> None:
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != daemon_uid or metadata.st_nlink != 1 or (exact_mode is not None and stat.S_IMODE(metadata.st_mode) != exact_mode):
        raise ReceiptPersistenceError("receipt_private_file_unsafe")
@dataclass
class _DirectoryComponent:
    name: str | None
    fd: int
    metadata: os.stat_result
    private: bool
class _SecureReceiptDirectory:
    def __init__(self, state_path: Path) -> None:
        _require_receipt_syscalls()
        normalized = normalize_receipt_state_path(state_path)
        parts = tuple(part for part in str(normalized).split("/") if part)
        if len(parts) < 2:
            raise ReceiptPersistenceError("receipt_state_path_invalid")
        self.ledger_name, self._directory_names = parts[-1], parts[:-1]
        self.lock_name, self.daemon_uid = f".{self.ledger_name}.lock", os.geteuid()
        self.components: list[_DirectoryComponent] = []; self.published = False
        self._open_chain()
    @property
    def fd(self) -> int:
        return self.components[-1].fd
    def _open_chain(self) -> None:
        try:
            root_fd = os.open("/", _OPEN_DIRECTORY_FLAGS)
            root_metadata = os.fstat(root_fd)
            _validate_directory(root_metadata, self.daemon_uid, private=False)
            self.components.append(_DirectoryComponent(None, root_fd, root_metadata, False))
            for name in self._directory_names[:-1]:
                self._append_existing(name, private=False)
            self._append_private(self._directory_names[-1])
            self.rewalk()
        except ReceiptPersistenceError:
            self._close_open_components(); raise
        except OSError as exc:
            self._close_open_components()
            raise ReceiptPersistenceError("receipt_directory_unavailable") from exc
    def _append_existing(self, name: str, *, private: bool | None) -> None:
        parent_fd = self.components[-1].fd
        named_metadata = _stat_at(parent_fd, name)
        child_fd = os.open(name, _OPEN_DIRECTORY_FLAGS, dir_fd=parent_fd)
        try:
            opened_metadata = os.fstat(child_fd)
            if not _same_inode(named_metadata, opened_metadata):
                raise ReceiptPersistenceError("receipt_component_changed")
            if private is True:
                _validate_directory(opened_metadata, self.daemon_uid, private=True)
            elif private is False:
                _validate_directory(opened_metadata, self.daemon_uid, private=False)
            elif not stat.S_ISDIR(opened_metadata.st_mode) or opened_metadata.st_uid != self.daemon_uid:
                raise ReceiptPersistenceError("receipt_private_directory_unsafe")
        except BaseException:
            _close_fd(child_fd); raise
        self.components.append(_DirectoryComponent(name, child_fd, opened_metadata, private is True))
    def _append_private(self, name: str) -> None:
        parent_fd = self.components[-1].fd
        created = False
        try:
            os.mkdir(name, 0o700, dir_fd=parent_fd)
            created = True
        except FileExistsError:
            pass
        self._append_existing(name, private=None if created else True)
        component = self.components[-1]
        if created:
            try:
                _validate_directory(component.metadata, self.daemon_uid, private=False)
                os.fchmod(component.fd, 0o700)
                component.metadata = os.fstat(component.fd)
                named_metadata = _stat_at(parent_fd, name)
                if not _same_inode(component.metadata, named_metadata):
                    raise ReceiptPersistenceError("receipt_component_changed")
                _validate_directory(component.metadata, self.daemon_uid, private=True)
                os.fsync(component.fd); os.fsync(parent_fd)
                component.private = True
            except OSError as exc:
                raise ReceiptPersistenceError("receipt_directory_persistence_failed") from exc
    def rewalk(self) -> None:
        reopened: list[int] = []
        try:
            fd = os.open("/", _OPEN_DIRECTORY_FLAGS)
            reopened.append(fd)
            metadata = os.fstat(fd)
            if not _same_inode(metadata, self.components[0].metadata):
                raise ReceiptPersistenceError("receipt_component_changed")
            _validate_directory(metadata, self.daemon_uid, private=False)
            for expected in self.components[1:]:
                if expected.name is None:
                    raise ReceiptPersistenceError("receipt_component_changed")
                named_metadata = _stat_at(fd, expected.name)
                next_fd = os.open(expected.name, _OPEN_DIRECTORY_FLAGS, dir_fd=fd)
                reopened.append(next_fd)
                opened_metadata = os.fstat(next_fd)
                if not _same_inode(named_metadata, opened_metadata) or not _same_inode(opened_metadata, expected.metadata):
                    raise ReceiptPersistenceError("receipt_component_changed")
                _validate_directory(opened_metadata, self.daemon_uid, private=expected.private)
                fd = next_fd
        except ReceiptPersistenceError: raise
        except OSError as exc:
            raise ReceiptPersistenceError("receipt_component_changed") from exc
        finally:
            first_close_error: OSError | None = None
            for opened_fd in reversed(reopened):
                first_close_error = first_close_error or _close_fd(opened_fd)
            if first_close_error is not None:
                error_type = ReceiptDurabilityUncertainError if self.published else ReceiptPersistenceError
                raise error_type("receipt_descriptor_close_failed") from first_close_error
    def _close_open_components(self) -> None:
        for component in reversed(self.components): _close_fd(component.fd)
        self.components.clear()
    def close(self) -> None:
        first_error: OSError | None = None
        for component in reversed(self.components): first_error = first_error or _close_fd(component.fd)
        self.components.clear()
        if first_error is not None:
            error_type = ReceiptDurabilityUncertainError if self.published else ReceiptPersistenceError
            raise error_type("receipt_descriptor_close_failed") from first_error
def _validate_named_file(location: _SecureReceiptDirectory, name: str, fd: int, *, exact_mode: int | None = 0o600, expected: os.stat_result | None = None) -> os.stat_result:
    named, opened = _stat_at(location.fd, name), os.fstat(fd)
    if not _same_inode(named, opened) or (expected is not None and not _same_inode(opened, expected)):
        raise ReceiptPersistenceError("receipt_file_changed")
    _validate_private_file(opened, location.daemon_uid, exact_mode=exact_mode)
    return opened
def _open_verified_file(location: _SecureReceiptDirectory, name: str, flags: int) -> tuple[int, os.stat_result]:
    named_metadata = _stat_at(location.fd, name)
    try:
        fd = os.open(name, flags | _OPEN_FILE_FLAGS, dir_fd=location.fd)
    except FileNotFoundError as exc:
        raise ReceiptPersistenceError("receipt_file_changed") from exc
    try: opened_metadata = _validate_named_file(location, name, fd, expected=named_metadata)
    except BaseException: _close_fd(fd); raise
    return fd, opened_metadata
def _read_all(fd: int) -> bytes:
    chunks: list[bytes] = []; total = 0
    while True:
        chunk = os.read(fd, 64 * 1024)
        if not chunk:
            return b"".join(chunks)
        total += len(chunk)
        if total > _MAX_LEDGER_BYTES:
            raise ReceiptPersistenceError("receipt_state_too_large")
        chunks.append(chunk)
def _read_receipt_state(location: _SecureReceiptDirectory, *, uncertain: bool = False) -> tuple[Mapping[str, Any], os.stat_result | None, bytes | None]:
    try:
        fd, opened_metadata = _open_verified_file(location, location.ledger_name, os.O_RDONLY)
    except FileNotFoundError:
        return {"version": RECEIPT_VERSION, "receipts": []}, None, None
    except ReceiptPersistenceError as exc:
        if uncertain:
            raise ReceiptDurabilityUncertainError("receipt_state_unreadable") from exc
        raise
    except OSError as exc:
        error_type = ReceiptDurabilityUncertainError if uncertain else ReceiptPersistenceError
        raise error_type("receipt_state_unreadable") from exc
    close_error: OSError | None = None
    try:
        raw = _read_all(fd)
        named_after = _stat_at(location.fd, location.ledger_name)
        opened_after = os.fstat(fd)
        if not _same_inode(opened_metadata, opened_after) or not _same_inode(opened_after, named_after):
            raise ReceiptPersistenceError("receipt_file_changed")
        _validate_private_file(opened_after, location.daemon_uid)
    except ReceiptPersistenceError as exc:
        if uncertain:
            raise ReceiptDurabilityUncertainError("receipt_state_unreadable") from exc
        raise
    except OSError as exc:
        error_type = ReceiptDurabilityUncertainError if uncertain else ReceiptPersistenceError
        raise error_type("receipt_state_unreadable") from exc
    finally:
        close_error = _close_fd(fd)
    if close_error is not None:
        error_type = ReceiptDurabilityUncertainError if uncertain else ReceiptPersistenceError
        raise error_type("receipt_descriptor_close_failed") from close_error
    try:
        return json.loads(raw.decode("utf-8")), opened_metadata, raw
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        error_type = ReceiptDurabilityUncertainError if uncertain else ReceiptPersistenceError
        raise error_type("receipt_state_unreadable") from exc
@dataclass
class _LockedReceiptState:
    data: Mapping[str, Any]
    location: _SecureReceiptDirectory
    ledger_metadata: os.stat_result | None
    def write(self, receipts: list[dict[str, Any]]) -> None:
        _write_receipt_state(self.location, receipts, self.ledger_metadata)
def _create_or_open_lock(location: _SecureReceiptDirectory) -> tuple[int, os.stat_result]:
    created = False
    try:
        fd = os.open(location.lock_name, os.O_RDWR | os.O_CREAT | os.O_EXCL | _OPEN_FILE_FLAGS, 0o600, dir_fd=location.fd)
        created = True
        _validate_named_file(location, location.lock_name, fd, exact_mode=None)
        os.fchmod(fd, 0o600)
        opened_metadata = _validate_named_file(location, location.lock_name, fd)
        os.fsync(fd); os.fsync(location.fd)
        return fd, opened_metadata
    except FileExistsError:
        pass
    except BaseException:
        if created and "fd" in locals():
            _close_fd(fd)
        raise
    fd, metadata = _open_verified_file(location, location.lock_name, os.O_RDWR)
    try:
        os.fsync(fd); os.fsync(location.fd)
    except OSError:
        _close_fd(fd)
        raise
    return fd, metadata
@contextmanager
def _locked_receipt_state(state_path: Path) -> Iterable[_LockedReceiptState]:
    location: _SecureReceiptDirectory | None = None
    lock_fd: int | None = None; lock_metadata: os.stat_result | None = None
    primary_error: BaseException | None = None
    try:
        location = _SecureReceiptDirectory(normalize_receipt_state_path(state_path))
        lock_fd, lock_metadata = _create_or_open_lock(location)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        named_lock = _stat_at(location.fd, location.lock_name)
        opened_lock = os.fstat(lock_fd)
        if not _same_inode(named_lock, opened_lock) or not _same_inode(opened_lock, lock_metadata):
            raise ReceiptPersistenceError("receipt_lock_changed")
        _validate_private_file(opened_lock, location.daemon_uid)
        location.rewalk()
        data, ledger_metadata, _raw = _read_receipt_state(location)
        yield _LockedReceiptState(data, location, ledger_metadata)
    except (ReceiptPersistenceError, ValueError) as exc:
        primary_error = exc
        raise
    except OSError as exc:
        primary_error = exc
        raise ReceiptPersistenceError("receipt_state_persistence_failed") from exc
    finally:
        cleanup_error: BaseException | None = None
        if location is not None and lock_fd is not None:
            try:
                location.rewalk()
                named_lock = _stat_at(location.fd, location.lock_name)
                opened_lock = os.fstat(lock_fd)
                if lock_metadata is None or not _same_inode(named_lock, opened_lock) or not _same_inode(opened_lock, lock_metadata):
                    raise ReceiptPersistenceError("receipt_lock_changed")
                _validate_private_file(opened_lock, location.daemon_uid)
            except BaseException as exc:
                cleanup_error = exc
            try: fcntl.flock(lock_fd, fcntl.LOCK_UN)
            except OSError as exc: cleanup_error = cleanup_error or exc
            cleanup_error = cleanup_error or _close_fd(lock_fd)
        if location is not None:
            try:
                location.close()
            except BaseException as exc:
                cleanup_error = cleanup_error or exc
        if cleanup_error is not None and primary_error is None:
            error_type = ReceiptDurabilityUncertainError if location is not None and location.published else ReceiptPersistenceError
            raise error_type("receipt_state_cleanup_failed") from cleanup_error
def _receipt_entries(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(data, Mapping):
        raise ValueError("receipt_state_not_mapping")
    version = data.get("version")
    receipts = data.get("receipts")
    if version != RECEIPT_VERSION or not isinstance(receipts, list):
        raise ValueError("receipt_state_schema_invalid")
    parsed: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in receipts:
        if not isinstance(item, Mapping):
            raise ValueError("receipt_not_mapping")
        seat_id, branch, sha, state = (item.get(name) for name in ("seat_id", "branch", "sha", "state"))
        if not all(isinstance(value, str) for value in (seat_id, branch, sha, state)):
            raise ValueError("receipt_fields_not_strings")
        if not seat_id or not branch or SHA_PATTERN.fullmatch(sha) is None or state not in RECEIPT_STATES:
            raise ValueError("receipt_fields_invalid")
        key = (seat_id, branch, sha)
        if key in seen:
            raise ValueError("receipt_key_duplicate")
        seen.add(key)
        completion_pending = item.get("completion_pending", False)
        if not isinstance(completion_pending, bool):
            raise ValueError("receipt_completion_pending_invalid")
        completion_sealed = item.get("completion_sealed")
        if "completion_pending" in item and "completion_sealed" in item:
            raise ValueError("receipt_completion_markers_conflict")
        if "completion_sealed" in item and (
            completion_sealed is not True or state not in RECEIPT_TERMINAL_STATES
        ):
            raise ValueError("receipt_completion_sealed_invalid")
        parsed_entry: dict[str, Any] = {
            "seat_id": seat_id,
            "branch": branch,
            "sha": sha,
            "state": state,
        }
        if completion_pending:
            parsed_entry["completion_pending"] = True
        if completion_sealed is True:
            parsed_entry["completion_sealed"] = True
        parsed.append(parsed_entry)
    return parsed


def _find_receipt(
    entries: list[dict[str, Any]], receipt: HandledSignalReceipt
) -> dict[str, Any] | None:
    for entry in entries:
        if (entry["seat_id"], entry["branch"], entry["sha"]) == (
            receipt.seat_id,
            receipt.branch,
            receipt.sha,
        ):
            return entry
    return None


def _receipt_record(receipt: HandledSignalReceipt, state: str) -> dict[str, str]:
    return {
        "seat_id": receipt.seat_id,
        "branch": receipt.branch,
        "sha": receipt.sha,
        "state": state,
    }


def _encoded_receipt_state(receipts: list[dict[str, Any]]) -> bytes:
    payload = {"receipts": sorted(receipts, key=lambda item: (item["seat_id"], item["branch"], item["sha"])), "version": RECEIPT_VERSION}
    raw = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if len(raw) > _MAX_LEDGER_BYTES:
        raise ReceiptPersistenceError("receipt_state_too_large")
    return raw
def _name_matches_inode(location: _SecureReceiptDirectory, name: str, expected: os.stat_result) -> bool:
    try:
        current = _stat_at(location.fd, name)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise ReceiptPersistenceError("receipt_publication_identity_unreadable") from exc
    return _same_inode(current, expected)
def _ledger_matches_expected(location: _SecureReceiptDirectory, expected: os.stat_result | None) -> bool:
    try:
        current = _stat_at(location.fd, location.ledger_name)
    except FileNotFoundError:
        return expected is None
    except OSError as exc:
        raise ReceiptPersistenceError("receipt_state_identity_unreadable") from exc
    if expected is None:
        return False
    try:
        _validate_private_file(current, location.daemon_uid)
    except ReceiptPersistenceError:
        return False
    return _same_inode(current, expected)
def _cleanup_created_temp(location: _SecureReceiptDirectory, temp_name: str, temp_metadata: os.stat_result) -> None:
    try:
        current = _stat_at(location.fd, temp_name)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise ReceiptPersistenceError("receipt_temp_cleanup_failed") from exc
    if not _same_inode(current, temp_metadata):
        raise ReceiptPersistenceError("receipt_temp_changed")
    try:
        os.unlink(temp_name, dir_fd=location.fd); os.fsync(location.fd)
    except OSError as exc:
        raise ReceiptPersistenceError("receipt_temp_cleanup_failed") from exc
def _discard_created_temp(location: _SecureReceiptDirectory, temp_name: str, temp_metadata: os.stat_result) -> None:
    try: _cleanup_created_temp(location, temp_name, temp_metadata)
    except ReceiptPersistenceError: pass
def _write_all(fd: int, payload: bytes) -> None:
    view = memoryview(payload); offset = 0
    while offset < len(view):
        written = os.write(fd, view[offset:])
        if written <= 0:
            raise ReceiptPersistenceError("receipt_state_write_failed")
        offset += written
def _write_receipt_state(location: _SecureReceiptDirectory, receipts: list[dict[str, Any]], expected_ledger: os.stat_result | None) -> None:
    raw = _encoded_receipt_state(receipts)
    temp_fd: int | None = None; temp_name: str | None = None
    temp_metadata: os.stat_result | None = None
    try:
        for _attempt in range(_TEMP_ATTEMPTS):
            candidate = f".{location.ledger_name}.{secrets.token_hex(16)}.tmp"
            try:
                temp_fd = os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL | _OPEN_FILE_FLAGS, 0o600, dir_fd=location.fd)
                temp_name, temp_metadata = candidate, os.fstat(temp_fd)
                break
            except FileExistsError:
                continue
        if temp_fd is None or temp_name is None:
            raise ReceiptPersistenceError("receipt_temp_names_exhausted")
        _validate_named_file(location, temp_name, temp_fd, exact_mode=None)
        os.fchmod(temp_fd, 0o600)
        temp_metadata = _validate_named_file(location, temp_name, temp_fd)
        _write_all(temp_fd, raw)
        os.fsync(temp_fd); os.fsync(location.fd)
        _validate_named_file(location, temp_name, temp_fd, expected=temp_metadata)
        if not _ledger_matches_expected(location, expected_ledger):
            raise ReceiptPersistenceError("receipt_state_changed")
        location.rewalk()
        try:
            os.replace(temp_name, location.ledger_name, src_dir_fd=location.fd, dst_dir_fd=location.fd)
        except OSError as exc:
            try:
                final_is_temp = _name_matches_inode(location, location.ledger_name, temp_metadata)
                temp_is_temp = _name_matches_inode(location, temp_name, temp_metadata)
                old_ledger_remains = _ledger_matches_expected(location, expected_ledger)
            except ReceiptPersistenceError as inspection_error:
                location.published = True
                raise ReceiptDurabilityUncertainError("receipt_publication_uncertain") from inspection_error
            if final_is_temp:
                location.published = True
                raise ReceiptDurabilityUncertainError("receipt_publication_uncertain") from exc
            if temp_is_temp and old_ledger_remains:
                _discard_created_temp(location, temp_name, temp_metadata); temp_name = None
                raise ReceiptPersistenceError("receipt_state_write_failed") from exc
            location.published = True
            raise ReceiptDurabilityUncertainError("receipt_publication_uncertain") from exc
        location.published = True
        try:
            _validate_named_file(location, location.ledger_name, temp_fd, expected=temp_metadata)
        except ReceiptPersistenceError as exc:
            raise ReceiptDurabilityUncertainError("receipt_final_identity_unproven") from exc
        os.fsync(location.fd)
        _data, reopened_metadata, readback = _read_receipt_state(location, uncertain=True)
        if reopened_metadata is None or not _same_inode(reopened_metadata, temp_metadata) or readback != raw:
            raise ReceiptDurabilityUncertainError("receipt_readback_unproven")
        location.rewalk()
    except ReceiptDurabilityUncertainError:
        raise
    except ReceiptPersistenceError as exc:
        if location.published:
            raise ReceiptDurabilityUncertainError("receipt_durability_uncertain") from exc
        if temp_name is not None and temp_metadata is not None:
            _discard_created_temp(location, temp_name, temp_metadata); temp_name = None
        raise
    except OSError as exc:
        if location.published:
            raise ReceiptDurabilityUncertainError("receipt_durability_uncertain") from exc
        if temp_name is not None and temp_metadata is not None:
            _discard_created_temp(location, temp_name, temp_metadata); temp_name = None
        raise ReceiptPersistenceError("receipt_state_write_failed") from exc
    finally:
        if temp_fd is not None:
            close_error = _close_fd(temp_fd)
            if close_error is not None and sys.exc_info()[0] is None:
                error_type = ReceiptDurabilityUncertainError if location.published else ReceiptPersistenceError
                raise error_type("receipt_descriptor_close_failed") from close_error
def _receipt_fingerprint(receipt: HandledSignalReceipt | ReceiptIdentity) -> str:
    coordinates = "\x00".join((receipt.seat_id, receipt.branch, receipt.sha)).encode("utf-8")
    return hashlib.sha256(coordinates).hexdigest()


def _sha_detail(token: str) -> str:
    if token in {"<sha>", "<new-sha>"}:
        return "placeholder_sha"
    return "sha_must_be_40_lowercase_hex"


def _emit_audit(
    audit_sink: AuditSink | None,
    reason: str,
    **fields: Any,
) -> None:
    if audit_sink is None:
        return
    record = {
        "action": "conveyor_discovery_rejected",
        "source": "conveyor_discovery",
        "reason": reason,
    }
    for key, value in fields.items():
        if value is not None:
            record[key] = value
    audit_sink(record)


__all__ = [
    "ConveyorSeatDiscoveryRunner",
    "HandledSignalReceipt",
    "ReadyForHarvestSignal",
    "ReceiptDiscoveryPayload",
    "ReceiptDurabilityUncertainError",
    "ReceiptIdentity",
    "ReceiptPersistenceError",
    "SeatProbeSpec",
    "normalize_receipt_state_path",
    "parse_ready_for_harvest_signals",
    "payload_for_signal",
    "subprocess_probe_runner",
]
