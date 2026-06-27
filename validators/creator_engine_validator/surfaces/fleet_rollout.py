"""Sequential rented-surface fleet rollout orchestration."""

from __future__ import annotations

import argparse
import importlib
import os
import shlex
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ..loader import LoaderError, load_yaml

DEFAULT_MANIFEST = Path("surfaces/manifest.yaml")
ENV_BLOCK_BEGIN = "# BEGIN CE SURFACES FLEET ROLLOUT"
ENV_BLOCK_END = "# END CE SURFACES FLEET ROLLOUT"
PROHIBITED_SEAT_COMMANDS = frozenset({"apt", "apt-get", "curl", "install", "npm", "pip", "pip3"})
SHELL_WRAPPED_PROHIBITED_TOKENS = frozenset(
    {"apt", "apt-get", "curl", "install", "npm", "pip", "pip3"}
)


class FleetRolloutError(Exception):
    """Raised when a fleet rollout plan or side effect fails."""


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


class SubprocessCommandRunner:
    """Small subprocess seam for stop/relaunch/readiness commands."""

    def run(self, argv: Sequence[str], *, timeout_s: float | None = None) -> CommandResult:
        completed = subprocess.run(
            list(argv),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


class HerdrReadinessPoller:
    """Poll herdr agent-status until the requested pane reports ready."""

    def __init__(
        self,
        runner: SubprocessCommandRunner | None = None,
        *,
        interval_seconds: float = 1.0,
    ) -> None:
        self._runner = runner or SubprocessCommandRunner()
        self._interval_seconds = interval_seconds

    def wait(self, seat: "SeatSpec", *, timeout_seconds: float) -> None:
        if not seat.readiness_pane_id:
            raise FleetRolloutError(f"{seat.seat_id}: missing readiness_pane_id for herdr readiness polling")
        deadline = time.monotonic() + timeout_seconds
        last_error = ""
        while time.monotonic() <= deadline:
            remaining = max(0.1, deadline - time.monotonic())
            result = self._runner.run(
                [
                    "herdr",
                    "wait",
                    "agent-status",
                    "--pane",
                    seat.readiness_pane_id,
                    "--status",
                    "ready",
                    "--json",
                ],
                timeout_s=min(remaining, 5.0),
            )
            if result.returncode == 0:
                return
            last_error = (result.stderr or result.stdout).strip()
            time.sleep(min(self._interval_seconds, max(0.0, deadline - time.monotonic())))
        detail = f": {last_error}" if last_error else ""
        raise FleetRolloutError(f"{seat.seat_id}: herdr readiness timed out after {timeout_seconds:g}s{detail}")


@dataclass(frozen=True)
class SeatSpec:
    seat_id: str
    environment_file: Path
    launch_args: tuple[str, ...]
    stop_command: tuple[str, ...] = ()
    stop_signal_path: Path | None = None
    herdr_pane_id: str | None = None
    readiness_pane_id: str | None = None
    controller_id: str | None = None
    lane_id: str | None = None
    claim_ref: str | None = None
    repo_root: Path = Path(".")
    side_effect_ledger_root: Path | None = None
    active_work_ledger_root: Path | None = None


@dataclass(frozen=True)
class RolloutReport:
    ok: bool
    dry_run: bool
    manifest_path: str
    seats: tuple[str, ...]
    updated: tuple[str, ...]
    not_updated: tuple[str, ...]
    ledger_entries: tuple[dict[str, str], ...] = ()
    warnings: tuple[str, ...] = ()
    failed_seat: str | None = None
    error: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "dry_run": self.dry_run,
            "manifest_path": self.manifest_path,
            "seats": list(self.seats),
            "updated": list(self.updated),
            "not_updated": list(self.not_updated),
            "ledger_entries": list(self.ledger_entries),
            "warnings": list(self.warnings),
            "failed_seat": self.failed_seat,
            "error": self.error,
        }


LedgerRecorder = Callable[[SeatSpec, str, str], None]


def run_cli(args: argparse.Namespace) -> int:
    manifest = Path(getattr(args, "manifest", None) or DEFAULT_MANIFEST)
    try:
        report = run_fleet_rollout(
            manifest_path=manifest,
            timeout_seconds=float(getattr(args, "timeout", 120)),
            dry_run=bool(getattr(args, "dry_run", False)),
        )
    except FleetRolloutError as exc:
        print(f"ERROR: ce surfaces fleet-rollout refused: {exc}", file=sys.stderr)
        return 1

    _print_report(report)
    return 0 if report.ok else 1


def run_fleet_rollout(
    *,
    manifest_path: Path | str = DEFAULT_MANIFEST,
    timeout_seconds: float = 120.0,
    dry_run: bool = False,
    command_runner: SubprocessCommandRunner | None = None,
    readiness_poller: HerdrReadinessPoller | None = None,
    ledger_recorder: LedgerRecorder | None = None,
) -> RolloutReport:
    manifest = Path(manifest_path)
    seats = _load_seats(manifest)
    renderer = _surface_render()
    try:
        rendered = renderer.render_launch_env(manifest)
    except renderer.RenderError as exc:
        raise FleetRolloutError(f"manifest_render_failed: {exc}") from exc
    env_assignments = _rendered_assignments(rendered)
    runner = command_runner or SubprocessCommandRunner()
    poller = readiness_poller or HerdrReadinessPoller(runner)

    seat_ids = tuple(seat.seat_id for seat in seats)
    warnings = tuple(rendered.warnings)
    if dry_run:
        return RolloutReport(
            ok=True,
            dry_run=True,
            manifest_path=str(manifest),
            seats=seat_ids,
            updated=(),
            not_updated=seat_ids,
            warnings=warnings,
        )

    updated: list[str] = []
    ledger_entries: list[dict[str, str]] = []
    for index, seat in enumerate(seats):
        try:
            _signal_stop(seat, runner=runner)
            _record_ledger(seat, "stop", "succeeded", ledger_recorder=ledger_recorder)
            ledger_entries.append({"seat_id": seat.seat_id, "action": "stop"})

            _update_environment_file(seat.environment_file, env_assignments, manifest)
            launch_argv = _launch_argv(seat)
            _run_required(launch_argv, runner=runner, timeout_s=timeout_seconds, context=f"{seat.seat_id}: ce launch")
            _record_ledger(seat, "relaunch", "succeeded", ledger_recorder=ledger_recorder)
            ledger_entries.append({"seat_id": seat.seat_id, "action": "relaunch"})

            poller.wait(seat, timeout_seconds=timeout_seconds)
        except Exception as exc:
            return RolloutReport(
                ok=False,
                dry_run=False,
                manifest_path=str(manifest),
                seats=seat_ids,
                updated=tuple(updated),
                not_updated=tuple(seat.seat_id for seat in seats[index:]),
                ledger_entries=tuple(ledger_entries),
                warnings=warnings,
                failed_seat=seat.seat_id,
                error=str(exc),
            )
        updated.append(seat.seat_id)

    return RolloutReport(
        ok=True,
        dry_run=False,
        manifest_path=str(manifest),
        seats=seat_ids,
        updated=tuple(updated),
        not_updated=(),
        ledger_entries=tuple(ledger_entries),
        warnings=warnings,
    )


def _load_seats(manifest: Path) -> tuple[SeatSpec, ...]:
    try:
        data = load_yaml(manifest)
    except LoaderError as exc:
        raise FleetRolloutError(f"manifest_read_failed: {exc}") from exc
    if not isinstance(data, Mapping):
        raise FleetRolloutError("manifest_shape_invalid: top-level document must be a mapping")
    rollout = data.get("fleet_rollout")
    if not isinstance(rollout, Mapping):
        raise FleetRolloutError("manifest_shape_invalid: missing fleet_rollout mapping")
    raw_seats = rollout.get("seats")
    if not isinstance(raw_seats, list) or not raw_seats:
        raise FleetRolloutError("manifest_shape_invalid: fleet_rollout.seats must be a non-empty list")
    base = _manifest_base(manifest)
    return tuple(_parse_seat(raw, index=index, base=base) for index, raw in enumerate(raw_seats))


def _parse_seat(raw: object, *, index: int, base: Path) -> SeatSpec:
    if not isinstance(raw, Mapping):
        raise FleetRolloutError(f"manifest_shape_invalid: fleet_rollout.seats[{index}] must be a mapping")
    seat_id = _required_str(raw, ("seat_id", "id", "name"), index=index)
    env_file = _path(_required_str(raw, ("environment_file", "env_file", "EnvironmentFile", "seat_env_file"), index=index), base)
    launch_args = _string_sequence(raw.get("launch_args") or raw.get("ce_launch_args"))
    if not launch_args:
        raise FleetRolloutError(f"{seat_id}: launch_args must be set for canonical ce launch")
    stop_signal = raw.get("stop_signal_path") or raw.get("canonical_stop_path")
    herdr_pane_id = _optional_str(raw.get("herdr_pane_id") or raw.get("pane_id"))
    readiness_pane_id = _optional_str(raw.get("readiness_pane_id") or raw.get("herdr_readiness_pane_id") or herdr_pane_id)
    return SeatSpec(
        seat_id=seat_id,
        environment_file=env_file,
        launch_args=launch_args,
        stop_command=_string_sequence(raw.get("stop_command")),
        stop_signal_path=_path(str(stop_signal), base) if stop_signal else None,
        herdr_pane_id=herdr_pane_id,
        readiness_pane_id=readiness_pane_id,
        controller_id=_optional_str(raw.get("controller_id")),
        lane_id=_optional_str(raw.get("lane_id")),
        claim_ref=_optional_str(raw.get("claim_ref")),
        repo_root=_path(str(raw.get("repo_root", ".")), base),
        side_effect_ledger_root=_optional_path(raw.get("side_effect_ledger_root"), base),
        active_work_ledger_root=_optional_path(raw.get("active_work_ledger_root"), base),
    )


def _required_str(raw: Mapping[str, Any], names: Sequence[str], *, index: int) -> str:
    for name in names:
        value = raw.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    joined = "/".join(names)
    raise FleetRolloutError(f"manifest_shape_invalid: fleet_rollout.seats[{index}] missing {joined}")


def _optional_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _string_sequence(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(shlex.split(value))
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        result = tuple(str(part) for part in value)
        if all(part for part in result):
            return result
    raise FleetRolloutError("command values must be a string or non-empty string list")


def _path(value: str, base: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def _manifest_base(manifest: Path) -> Path:
    if manifest.name == "manifest.yaml" and manifest.parent.name == "surfaces":
        return manifest.parent.parent
    return manifest.parent


def _optional_path(value: object, base: Path) -> Path | None:
    if isinstance(value, str) and value.strip():
        return _path(value.strip(), base)
    return None


def _surface_render() -> Any:
    try:
        return importlib.import_module("surfaces.render")
    except ModuleNotFoundError as exc:
        raise FleetRolloutError("surfaces.render is unavailable; run fleet-rollout from the repo checkout") from exc


def _rendered_assignments(rendered: Any) -> tuple[str, ...]:
    assignments: list[str] = []
    for prefix, assignment in rendered.values:
        if prefix != "export":
            raise FleetRolloutError(f"unexpected launch-env render prefix {prefix!r}")
        assignments.append(assignment)
    return tuple(assignments)


def _update_environment_file(path: Path, assignments: Sequence[str], manifest: Path) -> None:
    block = [
        ENV_BLOCK_BEGIN,
        f"# source_manifest={manifest}",
        *assignments,
        ENV_BLOCK_END,
    ]
    previous_mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    kept = _strip_env_block(existing).rstrip()
    content = ("\n".join(part for part in (kept, "\n".join(block)) if part) + "\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    try:
        os.chmod(path, previous_mode)
    except OSError:
        pass


def _strip_env_block(text: str) -> str:
    lines = text.splitlines()
    output: list[str] = []
    skipping = False
    for line in lines:
        if line == ENV_BLOCK_BEGIN:
            skipping = True
            continue
        if line == ENV_BLOCK_END and skipping:
            skipping = False
            continue
        if not skipping:
            output.append(line)
    return "\n".join(output)


def _signal_stop(seat: SeatSpec, *, runner: SubprocessCommandRunner) -> None:
    if seat.stop_command:
        _run_required(seat.stop_command, runner=runner, timeout_s=30.0, context=f"{seat.seat_id}: stop")
        return
    if seat.herdr_pane_id:
        _run_required(
            ["herdr", "pane", "send-keys", seat.herdr_pane_id, "C-c"],
            runner=runner,
            timeout_s=30.0,
            context=f"{seat.seat_id}: herdr stop",
        )
        return
    if seat.stop_signal_path is not None:
        seat.stop_signal_path.parent.mkdir(parents=True, exist_ok=True)
        seat.stop_signal_path.write_text("stop\n", encoding="utf-8")
        return
    raise FleetRolloutError(f"{seat.seat_id}: missing stop_command, herdr_pane_id, or stop_signal_path")


def _launch_argv(seat: SeatSpec) -> tuple[str, ...]:
    args = seat.launch_args
    if len(args) >= 2 and args[0] == "ce" and args[1] == "launch":
        argv = list(args)
    else:
        argv = ["ce", "launch", *args]
    if "--seat-env-file" not in argv:
        argv.extend(["--seat-env-file", str(seat.environment_file)])
    return tuple(argv)


def _run_required(
    argv: Sequence[str],
    *,
    runner: SubprocessCommandRunner,
    timeout_s: float | None,
    context: str,
) -> CommandResult:
    _refuse_prohibited_command(argv)
    result = runner.run(argv, timeout_s=timeout_s)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        suffix = f": {detail}" if detail else ""
        raise FleetRolloutError(f"{context} failed with exit {result.returncode}{suffix}")
    return result


def _refuse_prohibited_command(argv: Sequence[str]) -> None:
    if not argv:
        raise FleetRolloutError("empty command refused")
    effective_argv = _unwrap_env_command(argv)
    program = Path(str(effective_argv[0])).name
    if program in PROHIBITED_SEAT_COMMANDS:
        raise FleetRolloutError(f"prohibited seat command refused: {program}")
    if _is_python_pip_command(effective_argv):
        raise FleetRolloutError("prohibited seat command refused: python -m pip")
    if program in {"sh", "bash"} and _shell_wrapped_command_is_prohibited(effective_argv):
        raise FleetRolloutError("prohibited shell-wrapped seat install/curl/npm/pip/apt command refused")


def _unwrap_env_command(argv: Sequence[str]) -> tuple[str, ...]:
    """Return the command actually executed by env-wrapped argv."""

    if not argv:
        raise FleetRolloutError("empty command refused")
    if Path(str(argv[0])).name != "env":
        return tuple(str(part) for part in argv)

    args = [str(part) for part in argv[1:]]
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--":
            index += 1
            break
        if token in {"-i", "--ignore-environment", "-0", "--null"}:
            index += 1
            continue
        if token in {"-u", "--unset"}:
            index += 2
            continue
        if token == "-S" and index + 1 < len(args):
            return tuple(shlex.split(args[index + 1]) + args[index + 2 :])
        if token.startswith("-"):
            index += 1
            continue
        if "=" in token and not token.startswith("="):
            index += 1
            continue
        break
    if index >= len(args):
        raise FleetRolloutError("env command has no child command")
    return tuple(args[index:])


def _is_python_pip_command(argv: Sequence[str]) -> bool:
    program = Path(str(argv[0])).name
    if not (program == "python" or program.startswith("python3")):
        return False
    args = [str(part) for part in argv[1:]]
    return len(args) >= 2 and args[0] == "-m" and args[1] in {"pip", "pip3"}


def _shell_wrapped_command_is_prohibited(argv: Sequence[str]) -> bool:
    try:
        tokens = shlex.split(" ".join(str(part) for part in argv[1:]))
    except ValueError:
        tokens = [str(part) for part in argv[1:]]
    basenames = {Path(token).name for token in tokens}
    return bool(SHELL_WRAPPED_PROHIBITED_TOKENS & basenames)


def _record_ledger(
    seat: SeatSpec,
    action: str,
    status: str,
    *,
    ledger_recorder: LedgerRecorder | None,
) -> None:
    if ledger_recorder is not None:
        ledger_recorder(seat, action, status)
        return
    required = (
        seat.controller_id,
        seat.lane_id,
        seat.claim_ref,
        seat.side_effect_ledger_root,
        seat.active_work_ledger_root,
    )
    if any(value is None for value in required):
        raise FleetRolloutError(f"{seat.seat_id}: missing ledger context for {action} audit entry")
    _side_effect_ledger_record()(
        controller_id=str(seat.controller_id),
        lane_id=str(seat.lane_id),
        claim_ref=str(seat.claim_ref),
        effect_id=f"fleet-rollout-{_slug(seat.seat_id)}-{action}-{uuid.uuid4().hex[:8]}",
        effect_kind="runtime_process_action",
        effect_status=status,
        summary=f"fleet rollout {action} for {seat.seat_id}",
        occurred_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        repo_root=seat.repo_root,
        side_effect_ledger_root=seat.side_effect_ledger_root,
        active_work_ledger_root=seat.active_work_ledger_root,
        actor_role="controller",
        subject_ref=f"seat:{seat.seat_id}",
        details={"surface_rollout_action": action},
    )


def _side_effect_ledger_record() -> Callable[..., object]:
    module = __import__(
        "creator_engine_validator.side_effect_ledger_runtime",
        fromlist=["record"],
    )
    return module.record


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in value.lower()).strip("-") or "seat"


def _print_report(report: RolloutReport) -> None:
    prefix = "DRY RUN " if report.dry_run else ""
    status = "OK" if report.ok else "FAILED"
    print(f"ce surfaces fleet-rollout: {prefix}{status}")
    print(f"manifest: {report.manifest_path}")
    print(f"updated: {', '.join(report.updated) if report.updated else '(none)'}")
    print(f"not_updated: {', '.join(report.not_updated) if report.not_updated else '(none)'}")
    for warning in report.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if report.error:
        print(f"error: {report.error}", file=sys.stderr)
