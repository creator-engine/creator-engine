"""Discovery runner for conveyor READY-FOR-HARVEST seat signals."""

from __future__ import annotations

import json
import hashlib
import os
import re
import subprocess
import tempfile
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


class ReceiptDurabilityUncertainError(ValueError):
    """A terminal receipt replacement may be visible but was not proven durable."""


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
        self.state_path = Path(state_path)
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
                        state_path=str(self.state_path),
                        detail=str(exc),
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
        with _locked_receipt_state(self.state_path) as state:
            entries = _receipt_entries(state)
            if _find_receipt(entries, receipt) is None:
                entries.append(_receipt_record(receipt, "observed"))
                _write_receipt_state(self.state_path, entries)
        return receipt

    def claim(self, receipt: HandledSignalReceipt) -> bool:
        with _locked_receipt_state(self.state_path) as state:
            entries = _receipt_entries(state)
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
            if entry["state"] != "observed":
                return False
            entry["state"] = "processing"
            _write_receipt_state(self.state_path, entries)
            return True

    def complete(self, receipt: HandledSignalReceipt, state: str) -> bool:
        if state not in RECEIPT_TERMINAL_STATES:
            raise ValueError("receipt_completion_must_be_terminal")
        with _locked_receipt_state(self.state_path) as data:
            entries = _receipt_entries(data)
            entry = _find_receipt(entries, receipt)
            if entry is None or entry["state"] != "processing":
                return False
            entry["completion_pending"] = True
            _write_receipt_state(self.state_path, entries)
            entry["state"] = state
            _write_receipt_state(self.state_path, entries)
            entry.pop("completion_pending")
            _write_receipt_state(self.state_path, entries)
            return True


def _receipt_ledger(state_path: Path, audit_sink: AuditSink | None = None) -> _SignalReceiptLedger:
    return _SignalReceiptLedger(state_path, audit_sink)


@contextmanager
def _locked_receipt_state(state_path: Path) -> Iterable[Mapping[str, Any]]:
    lock_path = state_path.with_name(f".{state_path.name}.lock")
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ValueError(f"receipt_state_lock_unavailable:{type(exc).__name__}") from exc
    try:
        lock_file = lock_path.open("a+", encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"receipt_state_lock_unavailable:{type(exc).__name__}") from exc
    with lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
        except OSError as exc:
            raise ValueError(f"receipt_state_lock_unavailable:{type(exc).__name__}") from exc
        try:
            if not state_path.exists():
                yield {"version": RECEIPT_VERSION, "receipts": []}
                return
            try:
                raw = state_path.read_text(encoding="utf-8")
                data = json.loads(raw)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError(f"receipt_state_unreadable:{type(exc).__name__}") from exc
            yield data
        finally:
            try:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
            except OSError as exc:
                raise ValueError(f"receipt_state_lock_unavailable:{type(exc).__name__}") from exc


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
        parsed_entry: dict[str, Any] = {
            "seat_id": seat_id,
            "branch": branch,
            "sha": sha,
            "state": state,
        }
        if completion_pending:
            parsed_entry["completion_pending"] = True
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


def _write_receipt_state(state_path: Path, receipts: list[dict[str, Any]]) -> None:
    payload = {
        "receipts": sorted(receipts, key=lambda item: (item["seat_id"], item["branch"], item["sha"])),
        "version": RECEIPT_VERSION,
    }
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{state_path.name}.", suffix=".tmp", dir=str(state_path.parent), text=True
    )
    try:
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise ValueError(f"receipt_state_write_failed:{type(exc).__name__}") from exc
        try:
            os.replace(tmp_name, state_path)
        except OSError as exc:
            raise ValueError(f"receipt_state_write_failed:{type(exc).__name__}") from exc
        try:
            parent_fd = os.open(state_path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
        except OSError as exc:
            raise ReceiptDurabilityUncertainError(
                f"receipt_state_durability_uncertain:{type(exc).__name__}"
            ) from exc
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def _receipt_fingerprint(receipt: HandledSignalReceipt) -> str:
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
    "ReceiptIdentity",
    "SeatProbeSpec",
    "parse_ready_for_harvest_signals",
    "payload_for_signal",
    "subprocess_probe_runner",
]
