"""Shadow-mode launcher for the conveyor harvest daemon."""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .conveyor import ConveyorCommandResult
from .conveyor_daemon import (
    ConveyorDaemon,
    ConveyorDaemonLedgerRecord,
    ConveyorValidationLedgerBinding,
)
from .conveyor_discovery import (
    ConveyorSeatDiscoveryRunner,
    ReceiptPersistenceError, SeatProbeSpec, normalize_receipt_state_path,
    parse_ready_for_harvest_signals,
    subprocess_probe_runner,
)
from .conveyor_intake_queue import IntakeQueue, IntakeQueueReader
from .daemon_lease import DEFAULT_LEASE_TTL_SECONDS, DaemonLease, acquire
from .daemon_lease import DaemonLeaseError
from .forge.daemon_allocation import DaemonPathAllocator, DaemonRuntimeRoots
from .validation_sandbox_receipt import ValidationSandboxReceiptIssuer


DEFAULT_REPO_ROOT = Path("/workspace/creator-engine")
DEFAULT_INTERVAL_SECONDS = 60.0
DEFAULT_LANE_ID = "a1"
DEFAULT_CLAIM_REF = "".join(("ce", "-ops", "#", "388"))
SECRET_ENV_NAMES = {
    "GH_TOKEN",
    "CE_CONVEYOR_DAEMON_SIGNING_SECRET",
    "CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE",
}


class ConfigError(ValueError):
    """The daemon environment is incomplete or malformed."""


@dataclass(frozen=True)
class ConveyorDaemonConfig:
    seat_probes: tuple[SeatProbeSpec, ...]
    runtime_root: Path
    discovery_state: Path
    gh_token: str
    signing_secret: bytes
    repo_root: Path
    lease_root: Path
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS
    iterations: int | None = None
    lease_ttl_seconds: float = DEFAULT_LEASE_TTL_SECONDS
    holder_id: str | None = None
    ledger_path: Path | None = None
    validation_ledger_root: Path | None = None
    active_work_ledger_root: Path | None = None
    intake_queue_root: Path | None = None
    intake_enabled: bool = False


class SanitizedSubprocessCommandRunner:
    """Run validation-sandbox container commands without daemon secrets."""

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            env=_nonsecret_process_env(),
        )


def _error(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def _lease_refusal_error(config: ConveyorDaemonConfig, exc: DaemonLeaseError) -> str:
    lease_path = config.lease_root / "conveyor-daemon.lease"
    holder_pid = "unknown"
    try:
        payload = json.loads(lease_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = None
    if isinstance(payload, dict):
        raw_pid = payload.get("pid")
        if raw_pid is not None:
            holder_pid = str(raw_pid)
    return (
        "conveyor-daemon singleton lease refused: "
        f"{exc}; lease_path={lease_path}; holder_pid={holder_pid}"
    )


def _require_env(env: Mapping[str, str], name: str) -> str:
    value = env.get(name)
    if value is None or not value.strip():
        raise ConfigError(f"missing required environment variable: {name}")
    return value


def _optional_path(env: Mapping[str, str], name: str) -> Path | None:
    value = env.get(name)
    return Path(value) if value else None
def _receipt_state_path(raw: str) -> Path:
    try: return normalize_receipt_state_path(raw)
    except ReceiptPersistenceError as exc:
        raise ConfigError("CE_CONVEYOR_DAEMON_DISCOVERY_STATE must be a safe absolute path") from exc
def _parse_positive_float(
    env: Mapping[str, str],
    name: str,
    default: float,
) -> float:
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be numeric") from exc
    if value <= 0:
        raise ConfigError(f"{name} must be positive")
    return value


def _parse_iterations(env: Mapping[str, str]) -> int | None:
    raw = env.get("CE_CONVEYOR_DAEMON_ITERATIONS")
    if raw is None or raw == "":
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError("CE_CONVEYOR_DAEMON_ITERATIONS must be an integer") from exc
    if value < 1:
        raise ConfigError("CE_CONVEYOR_DAEMON_ITERATIONS must be >= 1")
    return value


def _parse_seat_probes(raw: str) -> tuple[SeatProbeSpec, ...]:
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError("CE_CONVEYOR_DAEMON_SEAT_PROBES must be a JSON array") from exc
    if not isinstance(decoded, list) or not decoded:
        raise ConfigError("CE_CONVEYOR_DAEMON_SEAT_PROBES must be a non-empty JSON array")

    specs: list[SeatProbeSpec] = []
    for index, entry in enumerate(decoded):
        if not isinstance(entry, dict):
            raise ConfigError(f"seat probe at index {index} must be an object")
        seat_id = entry.get("seat_id")
        argv = entry.get("argv")
        if not isinstance(seat_id, str) or not seat_id.strip():
            raise ConfigError(f"seat probe at index {index} requires non-empty seat_id")
        if not isinstance(argv, list) or not argv:
            raise ConfigError(f"seat probe {seat_id} requires non-empty argv array")
        if any(not isinstance(part, str) or part == "" for part in argv):
            raise ConfigError(f"seat probe {seat_id} argv entries must be non-empty strings")
        specs.append(SeatProbeSpec(seat_id=seat_id, argv=tuple(argv)))
    return tuple(specs)


def _load_signing_secret(env: Mapping[str, str]) -> bytes:
    file_value = env.get("CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE")
    direct_value = env.get("CE_CONVEYOR_DAEMON_SIGNING_SECRET")
    if file_value:
        path = Path(file_value)
        try:
            secret = path.read_bytes().strip()
        except OSError as exc:
            raise ConfigError(
                f"CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE is unreadable: {path}"
            ) from exc
    elif direct_value:
        secret = direct_value.encode("utf-8")
    else:
        raise ConfigError(
            "missing receipt signing secret: set CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE "
            "or CE_CONVEYOR_DAEMON_SIGNING_SECRET"
        )
    if not secret:
        raise ConfigError("receipt signing secret must be non-empty")
    return bytes(secret)


def load_config(env: Mapping[str, str] | None = None) -> ConveyorDaemonConfig:
    source = os.environ if env is None else env
    return ConveyorDaemonConfig(
        seat_probes=_parse_seat_probes(_require_env(source, "CE_CONVEYOR_DAEMON_SEAT_PROBES")),
        runtime_root=Path(_require_env(source, "CE_CONVEYOR_DAEMON_RUNTIME_ROOT")),
        discovery_state=_receipt_state_path(_require_env(source, "CE_CONVEYOR_DAEMON_DISCOVERY_STATE")),
        gh_token=_require_env(source, "GH_TOKEN"),
        signing_secret=_load_signing_secret(source),
        repo_root=Path(source.get("CE_CONVEYOR_DAEMON_REPO_ROOT") or DEFAULT_REPO_ROOT),
        lease_root=Path(_require_env(source, "CE_DAEMON_LEASE_ROOT")),
        interval_seconds=_parse_positive_float(
            source,
            "CE_CONVEYOR_DAEMON_INTERVAL_SECONDS",
            DEFAULT_INTERVAL_SECONDS,
        ),
        iterations=_parse_iterations(source),
        lease_ttl_seconds=_parse_positive_float(
            source,
            "CE_DAEMON_LEASE_TTL_SECONDS",
            DEFAULT_LEASE_TTL_SECONDS,
        ),
        holder_id=source.get("CE_DAEMON_HOLDER_ID") or None,
        ledger_path=_optional_path(source, "CE_CONVEYOR_DAEMON_LEDGER_PATH"),
        validation_ledger_root=_optional_path(
            source,
            "CE_CONVEYOR_DAEMON_VALIDATION_LEDGER_ROOT",
        ),
        active_work_ledger_root=_optional_path(
            source,
            "CE_CONVEYOR_DAEMON_ACTIVE_WORK_LEDGER_ROOT",
        ),
        intake_queue_root=_optional_path(source, "CE_CONVEYOR_INTAKE_QUEUE_ROOT"),
        intake_enabled=source.get("CE_CONVEYOR_INTAKE_ENABLED", "").strip() == "1",
    )


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(message: str) -> None:
    print(message, file=sys.stderr)


def _audit_sink(record: Mapping[str, Any]) -> None:
    _log(json.dumps(dict(record), sort_keys=True, separators=(",", ":")))


def _jsonl_ledger_writer(path: Path):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    def write(record: ConveyorDaemonLedgerRecord) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.as_dict(), sort_keys=True, default=str) + "\n")

    return write


def _nonsecret_process_env() -> dict[str, str]:
    env = dict(os.environ)
    for name in SECRET_ENV_NAMES:
        env.pop(name, None)
    return env


def _git_runner(
    args: Sequence[str],
    cwd: Path,
    env: Mapping[str, str],
) -> ConveyorCommandResult:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            env=dict(env),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        return ConveyorCommandResult(1, "", str(exc))
    return ConveyorCommandResult(completed.returncode, completed.stdout, completed.stderr)


def _gh_runner_factory(gh_token: str):
    def run(args: Sequence[str], cwd: Path) -> ConveyorCommandResult:
        env = _nonsecret_process_env()
        env["GH_TOKEN"] = gh_token
        try:
            completed = subprocess.run(
                ["gh", *args],
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
            return ConveyorCommandResult(1, "", str(exc))
        return ConveyorCommandResult(completed.returncode, completed.stdout, completed.stderr)

    return run


def _holder_id(config: ConveyorDaemonConfig) -> str:
    return config.holder_id or f"conveyor-daemon:{socket.gethostname()}:{os.getpid()}"


def _ensure_private_dir(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.chmod(0o700)


class _RecordingProbeRunner:
    def __init__(self, specs: Sequence[SeatProbeSpec]) -> None:
        self._seat_by_argv = {tuple(spec.argv): spec.seat_id for spec in specs}
        self._results = {spec.seat_id: False for spec in specs}

    def reset(self) -> None:
        for seat_id in self._results:
            self._results[seat_id] = False

    @property
    def seat_probe_results(self) -> Mapping[str, bool]:
        return dict(self._results)

    def __call__(self, argv: Sequence[str]) -> str:
        seat_id = self._seat_by_argv.get(tuple(argv))
        try:
            pane_text = subprocess_probe_runner(argv)
        except Exception:
            if seat_id is not None:
                self._results[seat_id] = False
            raise
        if seat_id is not None:
            self._results[seat_id] = bool(parse_ready_for_harvest_signals(pane_text))
        return pane_text


def _build_daemon(
    config: ConveyorDaemonConfig,
    lease: DaemonLease,
    *,
    probe_runner: _RecordingProbeRunner | None = None,
) -> ConveyorDaemon:
    roots = DaemonRuntimeRoots.from_root(config.runtime_root, create=True)
    path_allocator = DaemonPathAllocator(roots)
    discovery_runner = ConveyorSeatDiscoveryRunner(
        config.seat_probes,
        config.discovery_state,
        probe_runner=probe_runner,
        audit_sink=_audit_sink,
    )
    receipt_issuer = ValidationSandboxReceiptIssuer(secret=config.signing_secret)

    ledger_path = config.ledger_path or (config.runtime_root / "conveyor-daemon-ledger.jsonl")
    side_effect_ledger_root = config.validation_ledger_root or (
        config.runtime_root / "side-effect-ledger"
    )
    active_work_ledger_root = config.active_work_ledger_root or (
        config.runtime_root / "active-work-ledger"
    )
    _ensure_private_dir(side_effect_ledger_root)
    _ensure_private_dir(active_work_ledger_root)

    validation_ledger_binding = ConveyorValidationLedgerBinding(
        controller_id="conveyor-daemon",
        lane_id=DEFAULT_LANE_ID,
        claim_ref=DEFAULT_CLAIM_REF,
        repo_root=config.repo_root,
        side_effect_ledger_root=side_effect_ledger_root,
        active_work_ledger_root=active_work_ledger_root,
    )

    return ConveyorDaemon(
        discovery_runner=discovery_runner,
        armed=True,
        git_runner=_git_runner,
        gh_runner=_gh_runner_factory(config.gh_token),
        now=_utc_now,
        ledger_writer=_jsonl_ledger_writer(ledger_path),
        receipt_state_path=config.discovery_state,
        log_runner=_log,
        repo_root=roots.repo_root,
        bundle_root=roots.bundle_root,
        path_allocator=path_allocator,
        daemon_lease=lease,
        receipt_issuer=receipt_issuer,
        validation_sandbox_command_runner=SanitizedSubprocessCommandRunner(),
        validation_ledger_binding=validation_ledger_binding,
    )


def _run_loop(config: ConveyorDaemonConfig, lease: DaemonLease) -> int:
    stop_event = threading.Event()
    previous_sigterm = signal.getsignal(signal.SIGTERM)
    previous_sigint = signal.getsignal(signal.SIGINT)

    def _request_stop(signum: int, _frame: object) -> None:
        stop_event.set()
        _log(f"conveyor-daemon received signal {signum}; exiting after current pass")

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    try:
        recording_probe = (
            _RecordingProbeRunner(config.seat_probes)
            if config.intake_enabled and config.intake_queue_root is not None
            else None
        )
        daemon = _build_daemon(config, lease, probe_runner=recording_probe)
        completed = 0
        while not stop_event.is_set():
            if recording_probe is not None:
                recording_probe.reset()
            daemon.run_once()
            if recording_probe is not None and config.intake_queue_root is not None:
                try:
                    _log_intake_plans(config.intake_queue_root, recording_probe.seat_probe_results)
                except Exception as exc:
                    _log(f"conveyor-intake planning failed: {exc}")
            completed += 1
            if config.iterations is not None and completed >= config.iterations:
                break
            stop_event.wait(config.interval_seconds)
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
        signal.signal(signal.SIGINT, previous_sigint)
        lease.release()
    return 0


def _log_intake_plans(intake_queue_root: Path, seat_probe_results: Mapping[str, bool]) -> None:
    queue = IntakeQueue(intake_queue_root)
    for plan in IntakeQueueReader(
        queue,
        seat_probe_results,
        read_error_sink=_log_intake_read_error,
    ):
        _log(
            "conveyor-intake dry-run: "
            f"{plan.action} unit {plan.unit.unit_id} "
            f"(branch {plan.unit.branch}) to seat {plan.seat_id}"
        )


def _log_intake_read_error(path: Path, exc: Exception) -> None:
    _log(f"conveyor-intake skipped pending file {path}: {exc}")


def main_with_existing_lease(
    lease: DaemonLease,
    env: Mapping[str, str] | None = None,
) -> int:
    try:
        config = load_config(env)
    except ConfigError as exc:
        _error(str(exc))
        lease.release()
        return 2
    return _run_loop(config, lease)


def main(env: Mapping[str, str] | None = None) -> int:
    try:
        config = load_config(env)
    except ConfigError as exc:
        _error(str(exc))
        return 2

    _ensure_private_dir(config.lease_root)
    try:
        lease = acquire(
            "conveyor-daemon",
            _holder_id(config),
            state_root=config.lease_root,
            ttl_seconds=config.lease_ttl_seconds,
        )
    except DaemonLeaseError as exc:
        _error(_lease_refusal_error(config, exc))
        return 73
    return _run_loop(config, lease)


if __name__ == "__main__":  # pragma: no cover - exercised by python -m.
    raise SystemExit(main())
