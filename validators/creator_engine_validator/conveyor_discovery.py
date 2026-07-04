"""Discovery runner for conveyor READY-FOR-HARVEST seat signals."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .checks.path_manifest_fidelity import branch_slug
from .pickup_payload_schema import DiscoveryPayloadRejected, validate_discovery_payload

AuditSink = Callable[[Mapping[str, Any]], None]
ProbeRunner = Callable[[Sequence[str]], str]

READY_TOKEN = "READY-FOR-HARVEST"
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
DIFF_ECHO_PATTERN = re.compile(r"^\s*(?:\d+\s*[: ]?\s*)?\+\s*READY-FOR-HARVEST\b")
SIGNAL_PREFIX_PATTERN = re.compile(r"^\s*(?:[•\-*>]\s*)?READY-FOR-HARVEST\b")
SIGNAL_TAIL_PATTERN = re.compile(r"\s+(?P<branch>\S+)\s+(?P<sha>\S+)")
ISSUE_PREFIX_PATTERN = re.compile(r"^ce-(?P<issue>\d+)-")


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
        processed = _load_processed_state(self.state_path, self.audit_sink)
        updated = set(processed)
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
                if key in updated:
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

                payloads.append(payload)
                updated.add(key)

        if updated != processed:
            _write_processed_state(self.state_path, updated)

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


def _load_processed_state(
    state_path: Path,
    audit_sink: AuditSink | None,
) -> set[tuple[str, str, str]]:
    if not state_path.exists():
        _emit_audit(audit_sink, "state_missing", state_path=str(state_path))
        return set()

    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _emit_audit(
            audit_sink,
            "corrupt_state",
            state_path=str(state_path),
            detail=type(exc).__name__,
        )
        return set()

    try:
        return _processed_entries(data)
    except ValueError as exc:
        _emit_audit(
            audit_sink,
            "corrupt_state",
            state_path=str(state_path),
            detail=str(exc),
        )
        return set()


def _processed_entries(data: Any) -> set[tuple[str, str, str]]:
    if not isinstance(data, Mapping):
        raise ValueError("state_not_mapping")
    processed = data.get("processed", [])
    if not isinstance(processed, list):
        raise ValueError("processed_not_list")

    entries: set[tuple[str, str, str]] = set()
    for item in processed:
        if not isinstance(item, Mapping):
            raise ValueError("processed_entry_not_mapping")
        seat_id = item.get("seat_id")
        branch = item.get("branch")
        sha = item.get("sha")
        if not all(isinstance(value, str) for value in (seat_id, branch, sha)):
            raise ValueError("processed_entry_not_strings")
        entries.add((seat_id, branch, sha))
    return entries


def _write_processed_state(state_path: Path, processed: set[tuple[str, str, str]]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "processed": [
            {"seat_id": seat_id, "branch": branch, "sha": sha}
            for seat_id, branch, sha in sorted(processed)
        ]
    }

    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{state_path.name}.",
        suffix=".tmp",
        dir=str(state_path.parent),
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, state_path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


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
    "ReadyForHarvestSignal",
    "SeatProbeSpec",
    "parse_ready_for_harvest_signals",
    "payload_for_signal",
    "subprocess_probe_runner",
]
