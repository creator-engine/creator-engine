"""Pure conveyor daemon core for harvest-to-PR automation.

The daemon defaults to disarmed dry-run planning. Armed execution requires all
source-host mutation seams to be injected by the caller.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .conveyor import (
    DEFAULT_VALIDATE_COMMAND,
    ConveyorBundleLandingResult,
    ConveyorCommandResult,
    ConveyorHarvestResult,
    ConveyorHarvestSpec,
    land_bundle,
    prepare_harvest,
)
from .checks.path_manifest_fidelity import branch_slug


DiscoveryRunner = Callable[[], Iterable["ConveyorDaemonItem | Mapping[str, Any]"]]
CommandRunner = Callable[[Sequence[str], Path], ConveyorCommandResult | tuple[int, str, str]]
ValidateRunner = Callable[
    [Sequence[str], Path, Mapping[str, str] | None],
    ConveyorCommandResult | tuple[int, str, str],
]
PrepareRunner = Callable[..., ConveyorHarvestResult]
LandRunner = Callable[..., ConveyorBundleLandingResult]
NowRunner = Callable[[], str]
LedgerWriter = Callable[["ConveyorDaemonLedgerRecord"], None]
LogRunner = Callable[[str], None]


PLAN_ACTIONS = ("prepare-harvest", "land-bundle", "push", "pr-open")


@dataclass(frozen=True)
class ConveyorDaemonItem:
    """One discovered completed branch ready for conveyor processing."""

    branch: str
    worktree_path: Path
    bundle_path: Path
    repo_path: Path
    base: str = "origin/main"
    issue: str = "ce-conveyor"
    title: str = "Conveyor harvest"
    kind: str = "changed"
    scope: str = "conveyor harvest"
    body: str = "- Prepared conveyor harvest."
    declared_work_class: str = "story"
    carrier_date: str | None = None
    rebase: bool = True
    refresh_base: bool = True
    validate_command: tuple[str, ...] = DEFAULT_VALIDATE_COMMAND
    allow_dirty_validation: bool = True
    remote: str = "origin"
    pr_title: str | None = None
    pr_body: str | None = None
    pr_base: str | None = None
    identity: str | None = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ConveyorDaemonItem":
        return cls(
            branch=str(payload["branch"]),
            worktree_path=Path(payload["worktree_path"]),
            bundle_path=Path(payload["bundle_path"]),
            repo_path=Path(payload["repo_path"]),
            base=str(payload.get("base", "origin/main")),
            issue=str(payload.get("issue", "ce-conveyor")),
            title=str(payload.get("title", "Conveyor harvest")),
            kind=str(payload.get("kind", "changed")),
            scope=str(payload.get("scope", "conveyor harvest")),
            body=str(payload.get("body", "- Prepared conveyor harvest.")),
            declared_work_class=str(payload.get("declared_work_class", "story")),
            carrier_date=_optional_str(payload.get("carrier_date")),
            rebase=bool(payload.get("rebase", True)),
            refresh_base=bool(payload.get("refresh_base", True)),
            validate_command=tuple(str(part) for part in payload.get("validate_command", DEFAULT_VALIDATE_COMMAND)),
            allow_dirty_validation=bool(payload.get("allow_dirty_validation", True)),
            remote=str(payload.get("remote", "origin")),
            pr_title=_optional_str(payload.get("pr_title")),
            pr_body=_optional_str(payload.get("pr_body")),
            pr_base=_optional_str(payload.get("pr_base")),
            identity=_optional_str(payload.get("identity")),
        )

    @property
    def key(self) -> str:
        return self.identity or branch_slug(self.branch)

    def harvest_spec(self, *, carrier_date: str) -> ConveyorHarvestSpec:
        return ConveyorHarvestSpec(
            worktree_path=self.worktree_path,
            branch=self.branch,
            base=self.base,
            issue=self.issue,
            title=self.title,
            kind=self.kind,
            scope=self.scope,
            body=self.body,
            declared_work_class=self.declared_work_class,
            carrier_date=carrier_date,
            rebase=self.rebase,
            refresh_base=self.refresh_base,
            validate_command=self.validate_command,
            allow_dirty_validation=self.allow_dirty_validation,
        )


@dataclass(frozen=True)
class ConveyorDaemonLedgerRecord:
    """Append-only record for an armed source-host mutation attempt."""

    timestamp: str
    action: str
    path: str
    sha: str
    branch: str
    status: str
    returncode: int
    stdout: str = ""
    stderr: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "path": self.path,
            "sha": self.sha,
            "branch": self.branch,
            "status": self.status,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class ConveyorDaemonItemResult:
    """Outcome for one discovered item."""

    status: str
    branch: str
    key: str
    planned_actions: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    prepare_result: ConveyorHarvestResult | None = None
    landing_result: ConveyorBundleLandingResult | None = None
    pr_url: str | None = None
    ledger_records: tuple[ConveyorDaemonLedgerRecord, ...] = ()


@dataclass(frozen=True)
class ConveyorDaemonRunResult:
    """Outcome for one discovery pass."""

    armed: bool
    discovered_count: int
    results: tuple[ConveyorDaemonItemResult, ...]
    discovery_error: str | None = None

    @property
    def planned_count(self) -> int:
        return sum(1 for result in self.results if result.status == "planned")

    @property
    def failed_count(self) -> int:
        return sum(1 for result in self.results if result.status == "failed")


class ConveyorDaemon:
    """Testable daemon loop over injected discovery and command seams."""

    def __init__(
        self,
        *,
        discovery_runner: DiscoveryRunner,
        armed: bool = False,
        git_runner: CommandRunner | None = None,
        validate_runner: ValidateRunner | None = None,
        gh_runner: CommandRunner | None = None,
        now: NowRunner | None = None,
        ledger_writer: LedgerWriter | None = None,
        ledger_path: Path | str | None = None,
        log_runner: LogRunner | None = None,
        prepare_runner: PrepareRunner = prepare_harvest,
        land_runner: LandRunner = land_bundle,
    ) -> None:
        self.discovery_runner = discovery_runner
        self.armed = armed
        self.git_runner = git_runner
        self.validate_runner = validate_runner
        self.gh_runner = gh_runner
        self.now = now
        self.ledger_writer = ledger_writer or (_jsonl_ledger_writer(Path(ledger_path)) if ledger_path is not None else None)
        self.log_runner = log_runner
        self.prepare_runner = prepare_runner
        self.land_runner = land_runner
        self._completed_keys: set[str] = set()

        if self.armed:
            missing = []
            if self.git_runner is None:
                missing.append("git_runner")
            if self.validate_runner is None:
                missing.append("validate_runner")
            if self.gh_runner is None:
                missing.append("gh_runner")
            if self.now is None:
                missing.append("now")
            if self.ledger_writer is None:
                missing.append("ledger_writer")
            if missing:
                raise ValueError(f"armed conveyor daemon requires injected {', '.join(missing)}")

    def run_once(self) -> ConveyorDaemonRunResult:
        """Run one discovery pass.

        Disarmed mode plans only. Armed mode processes each item independently
        and continues after per-item failures.
        """

        try:
            discovered = tuple(_coerce_item(item) for item in self.discovery_runner())
        except Exception as exc:
            self._log(f"conveyor discovery failed: {exc}")
            return ConveyorDaemonRunResult(
                armed=self.armed,
                discovered_count=0,
                results=(),
                discovery_error=str(exc),
            )

        seen_this_pass: set[str] = set()
        results: list[ConveyorDaemonItemResult] = []
        for item in discovered:
            if item.key in seen_this_pass or item.key in self._completed_keys:
                results.append(
                    ConveyorDaemonItemResult(
                        status="skipped",
                        branch=item.branch,
                        key=item.key,
                        reasons=("already processed in this daemon lifetime",),
                    )
                )
                continue
            seen_this_pass.add(item.key)

            if not self.armed:
                result = ConveyorDaemonItemResult(
                    status="planned",
                    branch=item.branch,
                    key=item.key,
                    planned_actions=PLAN_ACTIONS,
                )
                self._log(f"conveyor dry-run plan {item.branch}: {', '.join(PLAN_ACTIONS)}")
            else:
                result = self._process_armed(item)
                if result.status == "pr-opened":
                    self._completed_keys.add(item.key)
            results.append(result)

        return ConveyorDaemonRunResult(
            armed=self.armed,
            discovered_count=len(discovered),
            results=tuple(results),
        )

    def run_loop(self, *, iterations: int) -> tuple[ConveyorDaemonRunResult, ...]:
        """Run a finite daemon loop without sleeping or external scheduling."""

        if iterations < 1:
            raise ValueError("iterations must be >= 1")
        return tuple(self.run_once() for _ in range(iterations))

    def _process_armed(self, item: ConveyorDaemonItem) -> ConveyorDaemonItemResult:
        records: list[ConveyorDaemonLedgerRecord] = []
        try:
            assert self.git_runner is not None
            assert self.validate_runner is not None
            assert self.gh_runner is not None
            carrier_date = item.carrier_date or _date_from_timestamp(self._timestamp())
            prepared = self.prepare_runner(
                item.harvest_spec(carrier_date=carrier_date),
                git_runner=self.git_runner,
                validate_runner=self.validate_runner,
            )
            if not prepared.ready:
                return self._failed(item, prepared.reasons, prepare_result=prepared, ledger_records=records)

            landed = self.land_runner(
                item.bundle_path,
                prepared.branch_slug,
                item.base,
                repo_path=item.repo_path,
                git_runner=self.git_runner,
            )
            if not landed.ready:
                reasons = tuple(f"{reason.code}: {reason.message}" for reason in landed.reasons)
                return self._failed(item, reasons, prepare_result=prepared, landing_result=landed, ledger_records=records)

            push_result = _coerce_result(
                self.git_runner(["push", item.remote, f"{landed.branch}:{landed.branch}"], item.repo_path)
            )
            records.append(
                self._record_mutation(
                    action="push",
                    path=f"{item.remote}/{landed.branch}",
                    sha=landed.head_sha or "",
                    branch=landed.branch,
                    command=("git", "push", item.remote, f"{landed.branch}:{landed.branch}"),
                    result=push_result,
                )
            )
            if push_result.returncode != 0:
                return self._failed(
                    item,
                    (f"push failed: {_command_detail(push_result)}",),
                    prepare_result=prepared,
                    landing_result=landed,
                    ledger_records=records,
                )

            pr_result = _coerce_result(self.gh_runner(_pr_create_args(item, landed), item.repo_path))
            pr_url = _first_stdout_line(pr_result.stdout)
            records.append(
                self._record_mutation(
                    action="pr-open",
                    path=pr_url or f"{_pr_base(item)}<-{landed.branch}",
                    sha=landed.head_sha or "",
                    branch=landed.branch,
                    command=("gh", *_pr_create_args(item, landed)),
                    result=pr_result,
                )
            )
            if pr_result.returncode != 0:
                return self._failed(
                    item,
                    (f"pr-open failed: {_command_detail(pr_result)}",),
                    prepare_result=prepared,
                    landing_result=landed,
                    ledger_records=records,
                )

            return ConveyorDaemonItemResult(
                status="pr-opened",
                branch=item.branch,
                key=item.key,
                prepare_result=prepared,
                landing_result=landed,
                pr_url=pr_url,
                ledger_records=tuple(records),
            )
        except Exception as exc:
            return self._failed(item, (f"exception: {exc}",), ledger_records=records)

    def _record_mutation(
        self,
        *,
        action: str,
        path: str,
        sha: str,
        branch: str,
        command: Sequence[str],
        result: ConveyorCommandResult,
    ) -> ConveyorDaemonLedgerRecord:
        assert self.ledger_writer is not None
        record = ConveyorDaemonLedgerRecord(
            timestamp=self._timestamp(),
            action=action,
            path=path,
            sha=sha,
            branch=branch,
            status="success" if result.returncode == 0 else "failed",
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            details={"command": tuple(command)},
        )
        self.ledger_writer(record)
        return record

    def _failed(
        self,
        item: ConveyorDaemonItem,
        reasons: Sequence[str],
        *,
        prepare_result: ConveyorHarvestResult | None = None,
        landing_result: ConveyorBundleLandingResult | None = None,
        ledger_records: Sequence[ConveyorDaemonLedgerRecord] = (),
    ) -> ConveyorDaemonItemResult:
        reason_tuple = tuple(str(reason) for reason in reasons)
        self._log(f"conveyor item failed {item.branch}: {'; '.join(reason_tuple)}")
        return ConveyorDaemonItemResult(
            status="failed",
            branch=item.branch,
            key=item.key,
            reasons=reason_tuple,
            prepare_result=prepare_result,
            landing_result=landing_result,
            ledger_records=tuple(ledger_records),
        )

    def _timestamp(self) -> str:
        assert self.now is not None
        timestamp = self.now()
        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError("now must return a non-empty timestamp string")
        return timestamp

    def _log(self, message: str) -> None:
        if self.log_runner is not None:
            self.log_runner(message)


def _coerce_item(item: ConveyorDaemonItem | Mapping[str, Any]) -> ConveyorDaemonItem:
    if isinstance(item, ConveyorDaemonItem):
        return item
    if isinstance(item, Mapping):
        return ConveyorDaemonItem.from_mapping(item)
    raise TypeError(f"unsupported discovery item type: {type(item).__name__}")


def _coerce_result(result: ConveyorCommandResult | tuple[int, str, str]) -> ConveyorCommandResult:
    if isinstance(result, ConveyorCommandResult):
        return result
    return ConveyorCommandResult(result[0], result[1], result[2])


def _jsonl_ledger_writer(path: Path) -> LedgerWriter:
    def write(record: ConveyorDaemonLedgerRecord) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.as_dict(), sort_keys=True) + "\n")

    return write


def _pr_create_args(item: ConveyorDaemonItem, landed: ConveyorBundleLandingResult) -> tuple[str, ...]:
    return (
        "pr",
        "create",
        "--base",
        _pr_base(item),
        "--head",
        landed.branch,
        "--title",
        item.pr_title or item.title,
        "--body",
        item.pr_body or item.body,
    )


def _pr_base(item: ConveyorDaemonItem) -> str:
    if item.pr_base:
        return item.pr_base
    if "/" in item.base:
        return item.base.rsplit("/", 1)[1]
    return item.base


def _first_stdout_line(stdout: str) -> str | None:
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _command_detail(result: ConveyorCommandResult) -> str:
    return result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"


def _date_from_timestamp(timestamp: str) -> str:
    if len(timestamp) >= 10 and timestamp[4:5] == "-" and timestamp[7:8] == "-":
        return timestamp[:10]
    raise ValueError("timestamp must begin with YYYY-MM-DD when carrier_date is omitted")


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


__all__ = [
    "ConveyorDaemon",
    "ConveyorDaemonItem",
    "ConveyorDaemonItemResult",
    "ConveyorDaemonLedgerRecord",
    "ConveyorDaemonRunResult",
    "PLAN_ACTIONS",
]
