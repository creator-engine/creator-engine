from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from creator_engine_validator.conveyor import (
    ConveyorBundleLandingResult,
    ConveyorCommandResult,
    ConveyorHarvestResult,
    ConveyorHarvestSpec,
)
from creator_engine_validator.conveyor_daemon import (
    PLAN_ACTIONS,
    ConveyorDaemon,
    ConveyorDaemonItem,
    ConveyorDaemonLedgerRecord,
)


HEAD_SHA = "0123456789abcdef0123456789abcdef01234567"


class FakeGit:
    def __init__(self, push_returncode: int = 0):
        self.push_returncode = push_returncode
        self.calls: list[tuple[tuple[str, ...], Path]] = []

    def __call__(self, args: Sequence[str], cwd: Path) -> ConveyorCommandResult:
        self.calls.append((tuple(args), cwd))
        if tuple(args) == ("push", "origin", "feature-one:feature-one"):
            if self.push_returncode:
                return ConveyorCommandResult(self.push_returncode, "", "push denied\n")
            return ConveyorCommandResult(0, "pushed\n", "")
        if tuple(args) == ("push", "origin", "feature-two:feature-two"):
            return ConveyorCommandResult(0, "pushed\n", "")
        return ConveyorCommandResult(1, "", f"unexpected git call: {args}")


class FakeGh:
    def __init__(self):
        self.calls: list[tuple[tuple[str, ...], Path]] = []

    def __call__(self, args: Sequence[str], cwd: Path) -> ConveyorCommandResult:
        self.calls.append((tuple(args), cwd))
        branch = tuple(args)[tuple(args).index("--head") + 1]
        return ConveyorCommandResult(0, f"https://github.example/{branch}/pull/1\n", "")


class FakeValidate:
    def __init__(self):
        self.calls: list[tuple[tuple[str, ...], Path, Mapping[str, str] | None]] = []

    def __call__(
        self,
        args: Sequence[str],
        cwd: Path,
        env: Mapping[str, str] | None,
    ) -> ConveyorCommandResult:
        self.calls.append((tuple(args), cwd, env))
        return ConveyorCommandResult(0, "ok\n", "")


class FakePrepare:
    def __init__(self, failing_branches: set[str] | None = None):
        self.failing_branches = failing_branches or set()
        self.calls: list[ConveyorHarvestSpec] = []

    def __call__(
        self,
        spec: ConveyorHarvestSpec,
        *,
        git_runner,
        validate_runner,
    ) -> ConveyorHarvestResult:
        self.calls.append(spec)
        if spec.branch in self.failing_branches:
            return _harvest_result(spec, ready=False, reasons=("prepare failed",))
        return _harvest_result(spec, ready=True, reasons=())


class FakeLand:
    def __init__(self):
        self.calls: list[tuple[Path, str, str, Path]] = []

    def __call__(
        self,
        bundle_path: Path,
        branch_name: str,
        base_ref: str = "origin/main",
        *,
        repo_path: Path,
        git_runner,
    ) -> ConveyorBundleLandingResult:
        self.calls.append((bundle_path, branch_name, base_ref, repo_path))
        return ConveyorBundleLandingResult(
            ready=True,
            reasons=(),
            bundle_path=bundle_path,
            branch=branch_name,
            branch_slug=branch_name,
            base_ref=base_ref,
            head_sha=HEAD_SHA,
            ahead=1,
            behind=0,
        )


class FakeClock:
    def __init__(self):
        self.count = 0

    def __call__(self) -> str:
        self.count += 1
        return f"2026-07-01T00:00:0{self.count}Z"


def _item(branch: str = "Feature/One") -> ConveyorDaemonItem:
    return ConveyorDaemonItem(
        branch=branch,
        worktree_path=Path(f"/tmp/{branch.lower().replace('/', '-')}"),
        bundle_path=Path(f"/tmp/{branch.lower().replace('/', '-')}.bundle"),
        repo_path=Path("/tmp/landing"),
        title=f"Land {branch}",
        body="- Conveyor item.",
    )


def _harvest_result(
    spec: ConveyorHarvestSpec,
    *,
    ready: bool,
    reasons: tuple[str, ...],
) -> ConveyorHarvestResult:
    slug = spec.branch.lower().replace("/", "-")
    return ConveyorHarvestResult(
        ready=ready,
        reasons=reasons,
        worktree_path=spec.worktree_path,
        branch=spec.branch,
        branch_slug=slug,
        base=spec.base,
        removed_artifacts=(),
    )


def test_dry_run_plans_no_mutation():
    prepare = FakePrepare()
    land = FakeLand()
    ledger: list[ConveyorDaemonLedgerRecord] = []

    result = ConveyorDaemon(
        discovery_runner=lambda: [_item()],
        prepare_runner=prepare,
        land_runner=land,
        ledger_writer=ledger.append,
    ).run_once()

    assert result.armed is False
    assert result.discovered_count == 1
    assert result.results[0].status == "planned"
    assert result.results[0].planned_actions == PLAN_ACTIONS
    assert prepare.calls == []
    assert land.calls == []
    assert ledger == []


def test_armed_path_calls_prepare_land_push_pr_and_ledger():
    prepare = FakePrepare()
    land = FakeLand()
    git = FakeGit()
    gh = FakeGh()
    ledger: list[ConveyorDaemonLedgerRecord] = []

    result = ConveyorDaemon(
        discovery_runner=lambda: [_item()],
        armed=True,
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=ledger.append,
        prepare_runner=prepare,
        land_runner=land,
    ).run_once()

    assert result.results[0].status == "pr-opened"
    assert prepare.calls[0].carrier_date == "2026-07-01"
    assert land.calls == [(Path("/tmp/feature-one.bundle"), "feature-one", "origin/main", Path("/tmp/landing"))]
    assert git.calls == [(("push", "origin", "feature-one:feature-one"), Path("/tmp/landing"))]
    assert gh.calls == [
        (
            (
                "pr",
                "create",
                "--base",
                "main",
                "--head",
                "feature-one",
                "--title",
                "Land Feature/One",
                "--body",
                "- Conveyor item.",
            ),
            Path("/tmp/landing"),
        )
    ]
    assert [record.action for record in ledger] == ["push", "pr-open"]
    assert [record.sha for record in ledger] == [HEAD_SHA, HEAD_SHA]
    assert [record.timestamp for record in ledger] == ["2026-07-01T00:00:02Z", "2026-07-01T00:00:03Z"]


def test_per_item_failure_isolated_and_loop_continues():
    prepare = FakePrepare(failing_branches={"Feature/One"})
    git = FakeGit()
    gh = FakeGh()
    ledger: list[ConveyorDaemonLedgerRecord] = []

    result = ConveyorDaemon(
        discovery_runner=lambda: [_item("Feature/One"), _item("Feature/Two")],
        armed=True,
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=ledger.append,
        prepare_runner=prepare,
        land_runner=FakeLand(),
    ).run_once()

    assert [item.status for item in result.results] == ["failed", "pr-opened"]
    assert result.results[0].reasons == ("prepare failed",)
    assert git.calls == [(("push", "origin", "feature-two:feature-two"), Path("/tmp/landing"))]
    assert len(gh.calls) == 1
    assert [record.branch for record in ledger] == ["feature-two", "feature-two"]


def test_armed_push_failure_records_ledger_and_skips_pr_open():
    ledger: list[ConveyorDaemonLedgerRecord] = []
    gh = FakeGh()

    result = ConveyorDaemon(
        discovery_runner=lambda: [_item()],
        armed=True,
        git_runner=FakeGit(push_returncode=1),
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=ledger.append,
        prepare_runner=FakePrepare(),
        land_runner=FakeLand(),
    ).run_once()

    assert result.results[0].status == "failed"
    assert result.results[0].reasons == ("push failed: push denied",)
    assert [(record.action, record.status, record.returncode) for record in ledger] == [("push", "failed", 1)]
    assert gh.calls == []


def test_hostile_payload_validate_command_override_is_ignored():
    """A malicious/compromised discovery payload must never control the
    executed validate command: it is pinned at the daemon level and any
    payload-supplied override is dropped (and logged), not honored."""

    prepare = FakePrepare()
    land = FakeLand()
    git = FakeGit()
    gh = FakeGh()
    ledger: list[ConveyorDaemonLedgerRecord] = []
    logs: list[str] = []

    hostile_payload = {
        "branch": "Feature/One",
        "worktree_path": "/tmp/feature-one",
        "bundle_path": "/tmp/feature-one.bundle",
        "repo_path": "/tmp/landing",
        "title": "Land Feature/One",
        "body": "- Conveyor item.",
        "validate_command": ["touch", "/tmp/pwned"],
    }

    daemon = ConveyorDaemon(
        discovery_runner=lambda: [hostile_payload],
        armed=True,
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=ledger.append,
        log_runner=logs.append,
        prepare_runner=prepare,
        land_runner=land,
    )
    result = daemon.run_once()

    assert result.results[0].status == "pr-opened"
    assert len(prepare.calls) == 1
    used_command = prepare.calls[0].validate_command
    assert used_command == daemon.validate_command
    assert used_command != ("touch", "/tmp/pwned")
    assert "touch" not in used_command
    assert any("attempted to override validate_command" in message for message in logs)


def test_daemon_pinned_validate_command_used_regardless_of_payload():
    """Even a benign-looking payload validate_command is ignored: the daemon's
    own configured command (constructor-level) is always the one executed."""

    prepare = FakePrepare()
    daemon = ConveyorDaemon(
        discovery_runner=lambda: [
            {
                "branch": "Feature/One",
                "worktree_path": "/tmp/feature-one",
                "bundle_path": "/tmp/feature-one.bundle",
                "repo_path": "/tmp/landing",
                "title": "Land Feature/One",
                "body": "- Conveyor item.",
                "validate_command": ["python", "-m", "some.other.module"],
            }
        ],
        armed=True,
        git_runner=FakeGit(),
        validate_runner=FakeValidate(),
        gh_runner=FakeGh(),
        now=FakeClock(),
        ledger_writer=lambda record: None,
        prepare_runner=prepare,
        land_runner=FakeLand(),
        validate_command=("python", "-m", "creator_engine_validator.ce_cli", "validate-pr"),
    )
    daemon.run_once()

    assert prepare.calls[0].validate_command == (
        "python",
        "-m",
        "creator_engine_validator.ce_cli",
        "validate-pr",
    )


def test_idempotent_re_discovery_skips_completed_item():
    git = FakeGit()
    gh = FakeGh()
    daemon = ConveyorDaemon(
        discovery_runner=lambda: [_item()],
        armed=True,
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=lambda record: None,
        prepare_runner=FakePrepare(),
        land_runner=FakeLand(),
    )

    first, second = daemon.run_loop(iterations=2)

    assert first.results[0].status == "pr-opened"
    assert second.results[0].status == "skipped"
    assert len(git.calls) == 1
    assert len(gh.calls) == 1
