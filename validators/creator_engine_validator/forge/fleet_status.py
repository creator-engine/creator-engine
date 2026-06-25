"""Aggregated CE fleet status for ``ce fleet status``.

The read-model is intentionally assembled from durable CE state, daemon logs,
process liveness, and ``gh`` PR metadata. It never inspects terminal panes.
Pure helpers accept explicit paths, JSONL text, and injected runners so tests
exercise the behavior without live processes or network.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import integrator_belt, seats_status

DEFAULT_LOG_DIR = Path("~/.ce/logs").expanduser()
INTEGRATOR_DAEMON_LOG = "integrator-daemon.log"
REVIEW_DAEMON_LOG = "review-daemon.log"
DEFAULT_PR_LIMIT = 100

_MISSING = "-"


@dataclass(frozen=True)
class ProcessProbe:
    """Process liveness derived from a non-terminal process table check."""

    pattern: str
    running: bool
    pids: tuple[int, ...] = ()
    commands: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class LastPassSummary:
    """Last daemon pass found in a JSONL witness log."""

    kind: str
    event: str
    index: int | None
    summary: Mapping[str, Any]
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class DaemonHealth:
    """One daemon's liveness plus its latest logged pass."""

    name: str
    label: str
    process: ProcessProbe
    log_path: str
    last_pass: LastPassSummary | None
    log_error: str | None = None


@dataclass(frozen=True)
class PullRequestBoardItem:
    """Small open-PR board row from ``gh pr list``."""

    repo: str
    number: int
    review_decision: str | None
    mergeable: str | None
    mergeable_state: str | None


@dataclass(frozen=True)
class PullRequestBoard:
    """Open PR board summary."""

    count: int | None
    items: tuple[PullRequestBoardItem, ...]
    repo: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class FleetStatus:
    """Aggregated fleet snapshot."""

    seats: tuple[seats_status.SeatStatus, ...]
    seat_counts: Mapping[str, int]
    daemons: tuple[DaemonHealth, ...]
    pull_requests: PullRequestBoard


def daemon_specs(log_dir: Path | str = DEFAULT_LOG_DIR) -> tuple[dict[str, str], ...]:
    """Return the daemon probes used by the fleet status view."""

    root = Path(log_dir).expanduser()
    return (
        {
            "name": "integrator",
            "label": "queue-daemon",
            "pattern": r"queue-daemon.*--loop",
            "log_path": str(root / INTEGRATOR_DAEMON_LOG),
        },
        {
            "name": "review",
            "label": "review-pickup",
            "pattern": r"review-pickup.*--loop",
            "log_path": str(root / REVIEW_DAEMON_LOG),
        },
    )


def collect_fleet_status(
    *,
    state_root: Path | str,
    ledger_roots: Sequence[Path | str] | None = None,
    integrator_log: Path | str = DEFAULT_LOG_DIR / INTEGRATOR_DAEMON_LOG,
    review_log: Path | str = DEFAULT_LOG_DIR / REVIEW_DAEMON_LOG,
    repo: str | None = None,
    org: str | None = None,
    pr_limit: int = DEFAULT_PR_LIMIT,
    process_runner: Any | None = None,
    gh_runner: Any | None = None,
) -> FleetStatus:
    """Collect the complete fleet status snapshot."""

    root = Path(state_root)
    resolved_ledger_roots = (
        [Path(p) for p in ledger_roots or []] or seats_status.default_ledger_roots(root)
    )
    seat_rows = tuple(
        seats_status.read_seat_states(
            seats_status.discover_seats(root, ledger_roots=resolved_ledger_roots)
        )
    )
    return FleetStatus(
        seats=seat_rows,
        seat_counts=count_seat_states(seat_rows),
        daemons=tuple(
            read_daemon_health(
                name=spec["name"],
                label=spec["label"],
                pattern=spec["pattern"],
                log_path=Path(spec["log_path"]),
                process_runner=process_runner,
            )
            for spec in (
                {
                    "name": "integrator",
                    "label": "queue-daemon",
                    "pattern": r"queue-daemon.*--loop",
                    "log_path": str(Path(integrator_log).expanduser()),
                },
                {
                    "name": "review",
                    "label": "review-pickup",
                    "pattern": r"review-pickup.*--loop",
                    "log_path": str(Path(review_log).expanduser()),
                },
            )
        ),
        pull_requests=fetch_open_pr_board(repo=repo, org=org, limit=pr_limit, gh_runner=gh_runner),
    )


def count_seat_states(statuses: Sequence[seats_status.SeatStatus]) -> dict[str, int]:
    """Count seats by derived state."""

    counts = {"total": len(statuses)}
    for status in statuses:
        counts[status.state] = counts.get(status.state, 0) + 1
    return counts


def read_daemon_health(
    *,
    name: str,
    label: str,
    pattern: str,
    log_path: Path,
    process_runner: Any | None = None,
) -> DaemonHealth:
    """Read one daemon's process and last-pass log status."""

    process = probe_process(pattern, runner=process_runner)
    last_pass, log_error = read_last_pass(log_path, kind=name)
    return DaemonHealth(
        name=name,
        label=label,
        process=process,
        log_path=str(log_path),
        last_pass=last_pass,
        log_error=log_error,
    )


def probe_process(pattern: str, *, runner: Any | None = None) -> ProcessProbe:
    """Check process liveness with ``pgrep``; no terminal panes are inspected."""

    run = runner or default_process_runner
    try:
        proc = run(["pgrep", "-af", pattern])
    except (OSError, subprocess.SubprocessError) as exc:
        return ProcessProbe(pattern=pattern, running=False, error=str(exc))
    stdout = getattr(proc, "stdout", "") or ""
    rows = parse_pgrep_rows(stdout)
    if getattr(proc, "returncode", 1) not in (0, 1):
        err = (getattr(proc, "stderr", "") or "").strip() or f"pgrep exited {proc.returncode}"
        return ProcessProbe(pattern=pattern, running=False, error=err)
    return ProcessProbe(
        pattern=pattern,
        running=bool(rows),
        pids=tuple(pid for pid, _command in rows),
        commands=tuple(command for _pid, command in rows),
    )


def default_process_runner(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Default local process runner."""

    return subprocess.run(
        list(argv),
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


def parse_pgrep_rows(stdout: str) -> tuple[tuple[int, str], ...]:
    """Parse ``pgrep -af`` rows into ``(pid, command)`` tuples."""

    rows: list[tuple[int, str]] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        pid_text, sep, command = line.partition(" ")
        if not sep:
            continue
        try:
            pid = int(pid_text)
        except ValueError:
            continue
        rows.append((pid, command.strip()))
    return tuple(rows)


def read_last_pass(log_path: Path, *, kind: str) -> tuple[LastPassSummary | None, str | None]:
    """Read the latest pass summary from a daemon JSONL log."""

    path = Path(log_path).expanduser()
    if not path.is_file():
        return None, "missing-log"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return None, f"unreadable-log: {exc}"
    return parse_last_pass_summary(lines, kind=kind), None


def parse_last_pass_summary(
    lines: Sequence[str],
    *,
    kind: str | None = None,
) -> LastPassSummary | None:
    """Return the last supported daemon pass summary in ``lines``."""

    last: LastPassSummary | None = None
    for line in lines:
        try:
            payload = json.loads(line)
        except ValueError:
            continue
        if not isinstance(payload, Mapping):
            continue
        summary = _summary_from_log_payload(payload)
        if summary is None:
            continue
        if kind is not None and summary.kind != kind:
            continue
        last = summary
    return last


def _summary_from_log_payload(payload: Mapping[str, Any]) -> LastPassSummary | None:
    action = payload.get("action")
    if action == "daemon_pass_complete":
        return LastPassSummary(
            kind="integrator",
            event=str(action),
            index=_int_or_none(payload.get("index")),
            summary={
                "enqueue": _int_or_zero(payload.get("enqueue_count")),
                "skip": _int_or_zero(payload.get("skip_count")),
                "defer": _int_or_zero(payload.get("defer_count")),
                "failed": _int_or_zero(payload.get("failed_count")),
            },
            raw=dict(payload),
        )
    event = payload.get("event")
    if event == "review_pickup_pass_complete":
        return LastPassSummary(
            kind="review",
            event=str(event),
            index=_int_or_none(payload.get("index")),
            summary={
                "routes": _int_or_zero(payload.get("routes")),
                "skipped": _int_or_zero(payload.get("skipped")),
                "dry_run": bool(payload.get("dry_run", False)),
            },
            raw=dict(payload),
        )
    return None


def fetch_open_pr_board(
    *,
    repo: str | None = None,
    org: str | None = None,
    limit: int = DEFAULT_PR_LIMIT,
    gh_runner: Any | None = None,
) -> PullRequestBoard:
    """Fetch open PR board rows through the integrator daemon's ``gh`` adapter."""

    if not repo and not org:
        return PullRequestBoard(count=None, items=(), repo=None, error="repo-or-org-required")
    try:
        candidates = integrator_belt.discover_daemon_candidates(
            repo=repo,
            org=org,
            gh_runner=gh_runner,
            first=limit,
        )
    except (integrator_belt.IntegratorBeltError, integrator_belt.ForgeConfigError) as exc:
        return PullRequestBoard(count=None, items=(), repo=repo or org, error=str(exc))
    return board_from_daemon_candidates(candidates, repo=repo or org)


def default_gh_runner(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Default ``gh`` runner."""

    return subprocess.run(
        list(argv),
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def board_from_daemon_candidates(
    candidates: Sequence[integrator_belt.DaemonPullRequest],
    *,
    repo: str | None = None,
) -> PullRequestBoard:
    """Project integrator daemon PR candidates into the compact board rows."""

    items = tuple(
        PullRequestBoardItem(
            repo=candidate.repo,
            number=candidate.pr_number,
            review_decision=candidate.review_decision,
            mergeable=candidate.mergeable,
            mergeable_state=candidate.merge_state_status,
        )
        for candidate in candidates
    )
    return PullRequestBoard(count=len(items), items=items, repo=repo)


def render_table(status: FleetStatus) -> str:
    """Render a compact human-readable fleet table."""

    lines = [
        "CE fleet status",
        _seat_summary_line(status.seat_counts),
        "",
        seats_status.render_table(status.seats),
        "",
        _daemon_table(status.daemons),
        "",
        _pr_table(status.pull_requests),
    ]
    return "\n".join(lines)


def render_json(status: FleetStatus) -> str:
    """Render machine-readable fleet status JSON."""

    payload = {
        "seats": {
            "count": len(status.seats),
            "states": dict(status.seat_counts),
            "items": [asdict(seat) for seat in status.seats],
        },
        "daemons": [asdict(daemon) for daemon in status.daemons],
        "pull_requests": asdict(status.pull_requests),
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def add_parser(subparsers: argparse._SubParsersAction, *, default_root: str) -> None:
    """Register the ``fleet status`` CLI surface on an existing parser."""

    fleet = subparsers.add_parser("fleet", help="aggregated fleet status")
    fleet_sub = fleet.add_subparsers(dest="fleet_command", required=True)
    status = fleet_sub.add_parser("status", help="show aggregated fleet status")
    status.add_argument(
        "--root",
        default=default_root,
        help=f"CE local state root containing dispatches/ (default: {default_root})",
    )
    status.add_argument(
        "--ledger-root",
        action="append",
        default=None,
        dest="ledger_roots",
        help="repeatable lifecycle ledger root containing seats/<host>/*.yaml",
    )
    status.add_argument(
        "--integrator-log",
        default=str(DEFAULT_LOG_DIR / INTEGRATOR_DAEMON_LOG),
        help=f"Integrator daemon JSONL log (default: {DEFAULT_LOG_DIR / INTEGRATOR_DAEMON_LOG})",
    )
    status.add_argument(
        "--review-log",
        default=str(DEFAULT_LOG_DIR / REVIEW_DAEMON_LOG),
        help=f"Review-pickup daemon JSONL log (default: {DEFAULT_LOG_DIR / REVIEW_DAEMON_LOG})",
    )
    board_scope = status.add_mutually_exclusive_group()
    board_scope.add_argument("--repo", default=None, help="owner/name repository for open PR board")
    board_scope.add_argument("--org", default=None, help="org/user scope for open PR board")
    status.add_argument("--pr-limit", type=int, default=DEFAULT_PR_LIMIT, help="open PR board limit")
    status.add_argument("--json", action="store_true", dest="json_output")


def run_cli(args: argparse.Namespace) -> int:
    """CLI adapter for ``fleet status``."""

    if getattr(args, "fleet_command", None) != "status":
        print("ERROR: fleet subcommand required", file=sys.stderr)
        return 2
    status = collect_fleet_status(
        state_root=Path(args.root),
        ledger_roots=[Path(p) for p in getattr(args, "ledger_roots", None) or []],
        integrator_log=Path(args.integrator_log),
        review_log=Path(args.review_log),
        repo=getattr(args, "repo", None),
        org=getattr(args, "org", None),
        pr_limit=int(getattr(args, "pr_limit", DEFAULT_PR_LIMIT)),
    )
    if getattr(args, "json_output", False):
        print(render_json(status))
    else:
        print(render_table(status))
    return 0


def _seat_summary_line(counts: Mapping[str, int]) -> str:
    keys = [
        seats_status.STATE_WORKING,
        seats_status.STATE_UP,
        seats_status.STATE_IDLE,
        seats_status.STATE_DOWN,
        seats_status.STATE_UNKNOWN,
    ]
    parts = [f"seats={counts.get('total', 0)}"]
    parts.extend(f"{key}={counts.get(key, 0)}" for key in keys if counts.get(key, 0))
    return " ".join(parts)


def _daemon_table(daemons: Sequence[DaemonHealth]) -> str:
    rows = [
        [
            daemon.label,
            "up" if daemon.process.running else "down",
            ",".join(str(pid) for pid in daemon.process.pids) or _MISSING,
            _last_pass_text(daemon),
            daemon.log_path,
        ]
        for daemon in daemons
    ]
    headers = ["DAEMON", "STATE", "PID", "LAST PASS", "LOG"]
    widths = [max(len(str(row[i])) for row in ([headers] + rows)) for i in range(len(headers))]
    lines = [_format_row(headers, widths), _format_row(["-" * w for w in widths], widths)]
    lines.extend(_format_row(row, widths) for row in rows)
    return "\n".join(lines)


def _pr_table(board: PullRequestBoard) -> str:
    headers = ["PR", "REVIEW", "MERGEABLE"]
    if board.error:
        rows = [["(unavailable)", board.error[:80], _MISSING]]
    else:
        rows = [
            [
                f"#{item.number}",
                item.review_decision or _MISSING,
                item.mergeable_state or item.mergeable or _MISSING,
            ]
            for item in board.items
        ]
        if not rows:
            rows = [["(no open PRs)", _MISSING, _MISSING]]
    widths = [max(len(str(row[i])) for row in ([headers] + rows)) for i in range(len(headers))]
    lines = [_format_row(headers, widths), _format_row(["-" * w for w in widths], widths)]
    lines.extend(_format_row(row, widths) for row in rows)
    return "\n".join(lines)


def _last_pass_text(daemon: DaemonHealth) -> str:
    if daemon.last_pass is None:
        return daemon.log_error or _MISSING
    bits = [f"{key}={value}" for key, value in daemon.last_pass.summary.items()]
    index = f"#{daemon.last_pass.index} " if daemon.last_pass.index is not None else ""
    return index + " ".join(bits)


def _format_row(row: Sequence[str], widths: Sequence[int]) -> str:
    return "  ".join(str(value).ljust(width) for value, width in zip(row, widths, strict=True))


def _int_or_zero(value: Any) -> int:
    parsed = _int_or_none(value)
    return parsed if parsed is not None else 0


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _str_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None
