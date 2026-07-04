from __future__ import annotations

import dataclasses
import shutil
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

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
from creator_engine_validator.forge.daemon_allocation import DaemonPathAllocator, DaemonRuntimeRoots


HEAD_SHA = "0123456789abcdef0123456789abcdef01234567"

TEST_RUNTIME_ROOT = Path(tempfile.mkdtemp(dir="/tmp", prefix="conveyor-daemon-alloc-test-"))
TEST_ALLOCATOR = DaemonPathAllocator(
    DaemonRuntimeRoots.from_root(TEST_RUNTIME_ROOT, create=True),
    secret=b"conveyor-daemon-unit-test-secret",
)


class FakeLease:
    def __init__(self):
        self.heartbeat_calls = 0

    def heartbeat(self) -> None:
        self.heartbeat_calls += 1


ARMED_ROOTS = {"path_allocator": TEST_ALLOCATOR, "daemon_lease": FakeLease()}


class FakeGit:
    def __init__(self, push_returncode: int = 0):
        self.push_returncode = push_returncode
        self.calls: list[tuple[tuple[str, ...], Path]] = []
        self.envs: list[Mapping[str, str]] = []

    def __call__(self, args: Sequence[str], cwd: Path, env: Mapping[str, str]) -> ConveyorCommandResult:
        self.calls.append((tuple(args), cwd))
        self.envs.append(dict(env))
        if tuple(args) == ("push", "--", "origin", "feature-one:feature-one"):
            if self.push_returncode:
                return ConveyorCommandResult(self.push_returncode, "", "push denied\n")
            return ConveyorCommandResult(0, "pushed\n", "")
        if tuple(args) == ("push", "--", "origin", "feature-two:feature-two"):
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
    def __init__(self, branch_override: str | None = None):
        self.branch_override = branch_override
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
        landed_branch = self.branch_override or branch_name
        return ConveyorBundleLandingResult(
            ready=True,
            reasons=(),
            bundle_path=bundle_path,
            branch=landed_branch,
            branch_slug=landed_branch,
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


class CountingAllocator:
    def __init__(self):
        runtime_root = Path(tempfile.mkdtemp(dir="/tmp", prefix="conveyor-counting-alloc-"))
        self.inner = DaemonPathAllocator(
            DaemonRuntimeRoots.from_root(runtime_root, create=True),
            secret=b"conveyor-daemon-counting-secret",
        )
        self.allocate_calls: list[dict[str, object]] = []
        self.allocations = []

    @property
    def roots(self):
        return self.inner.roots

    def allocate_conveyor_paths(self, **kwargs):
        self.allocate_calls.append(dict(kwargs))
        allocation, receipt = self.inner.allocate_conveyor_paths(**kwargs)
        self.allocations.append(allocation)
        return allocation, receipt

    def verify_receipt(self, receipt):
        return self.inner.verify_receipt(receipt)

    def cleanup(self, receipt):
        return self.inner.cleanup(receipt)


def _item(branch: str = "Feature/One") -> ConveyorDaemonItem:
    allocation, receipt = TEST_ALLOCATOR.allocate_conveyor_paths(
        repo=branch.lower().replace("/", "-"),
        branch_name=branch,
    )
    return ConveyorDaemonItem(
        branch=branch,
        worktree_path=allocation.worktree_path,
        bundle_path=allocation.bundle_path,
        repo_path=allocation.repo_path,
        title=f"Land {branch}",
        body="- Conveyor item.",
        allocation_receipt=receipt,
    )


def _item_without_receipt(branch: str = "Feature/One") -> ConveyorDaemonItem:
    item = _item(branch)
    return dataclasses.replace(item, allocation_receipt=None)


def _data_only_payload() -> dict[str, str]:
    return {
        "issue": "388",
        "branch_name": "feature-one",
        "pr_title": "Land Feature/One",
        "pr_body": "- Conveyor item.",
    }


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
    logs: list[str] = []
    item = _item()

    result = ConveyorDaemon(
        discovery_runner=lambda: [item],
        armed=True,
        **ARMED_ROOTS,
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=ledger.append,
        log_runner=logs.append,
        prepare_runner=prepare,
        land_runner=land,
    ).run_once()

    assert result.results[0].status == "pr-opened"
    assert prepare.calls[0].carrier_date == "2026-07-01"
    assert prepare.calls[0].worktree_path == item.worktree_path
    assert land.calls == [(item.bundle_path, "feature-one", "origin/main", item.repo_path)]
    assert git.calls == [(("push", "--", "origin", "feature-one:feature-one"), item.repo_path)]
    assert git.envs == [
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "PATH": "/usr/bin:/bin",
        }
    ]
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
            item.repo_path,
        )
    ]
    assert [record.action for record in ledger] == ["push", "pr-open"]
    assert [record.sha for record in ledger] == [HEAD_SHA, HEAD_SHA]
    assert [record.timestamp for record in ledger] == ["2026-07-01T00:00:02Z", "2026-07-01T00:00:03Z"]
    assert any(
        "conveyor allocation audit" in message
        and '"allocation_id"' in message
        and '"item_key": "feature-one"' in message
        and '"root_kind"' in message
        and '"mode_check"' in message
        and '"cleanup": {"cleaned": true, "status": "success"}' in message
        and '"nonce"' not in message
        and '"signature"' not in message
        for message in logs
    )


def test_armed_start_without_lease_is_refused():
    with pytest.raises(ValueError, match="daemon_lease"):
        ConveyorDaemon(
            discovery_runner=lambda: [],
            armed=True,
            path_allocator=TEST_ALLOCATOR,
            git_runner=FakeGit(),
            validate_runner=FakeValidate(),
            gh_runner=FakeGh(),
            now=FakeClock(),
            ledger_writer=lambda record: None,
        )


def test_armed_run_heartbeats_lease():
    lease = FakeLease()
    daemon = ConveyorDaemon(
        discovery_runner=lambda: [],
        armed=True,
        path_allocator=TEST_ALLOCATOR,
        daemon_lease=lease,
        git_runner=FakeGit(),
        validate_runner=FakeValidate(),
        gh_runner=FakeGh(),
        now=FakeClock(),
        ledger_writer=lambda record: None,
    )

    daemon.run_once()

    assert lease.heartbeat_calls == 1


def test_per_item_failure_isolated_and_loop_continues():
    prepare = FakePrepare(failing_branches={"Feature/One"})
    git = FakeGit()
    gh = FakeGh()
    ledger: list[ConveyorDaemonLedgerRecord] = []
    failed_item = _item("Feature/One")
    good_item = _item("Feature/Two")

    result = ConveyorDaemon(
        discovery_runner=lambda: [failed_item, good_item],
        armed=True,
        **ARMED_ROOTS,
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
    assert git.calls == [(("push", "--", "origin", "feature-two:feature-two"), good_item.repo_path)]
    assert len(gh.calls) == 1
    assert [record.branch for record in ledger] == ["feature-two", "feature-two"]


def test_armed_push_failure_records_ledger_and_skips_pr_open():
    ledger: list[ConveyorDaemonLedgerRecord] = []
    gh = FakeGh()

    result = ConveyorDaemon(
        discovery_runner=lambda: [_item()],
        armed=True,
        **ARMED_ROOTS,
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


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("validate_command", ["touch", "/tmp/pwned"], "banned_control_field"),
        ("base", "--exec=touch /tmp/pwned", "banned_control_field"),
        ("remote", "ext::sh -c 'touch /tmp/pwned'", "banned_control_field"),
        ("worktree_path", "/tmp/feature-one", "banned_control_field"),
        ("bundle_path", "/tmp/feature-one.bundle", "banned_control_field"),
        ("repo_path", "/tmp/landing", "banned_control_field"),
        ("pr_base", "release", "banned_control_field"),
    ],
)
def test_discovery_mapping_with_legacy_control_field_is_rejected_and_audited(
    field: str,
    value: object,
    reason: str,
):
    prepare = FakePrepare()
    land = FakeLand()
    git = FakeGit()
    gh = FakeGh()
    ledger: list[ConveyorDaemonLedgerRecord] = []
    logs: list[str] = []
    payload = {**_data_only_payload(), field: value}

    result = ConveyorDaemon(
        discovery_runner=lambda: [payload],
        armed=True,
        **ARMED_ROOTS,
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=ledger.append,
        log_runner=logs.append,
        prepare_runner=prepare,
        land_runner=land,
    ).run_once()

    assert result.discovery_error is None
    assert result.discovered_count == 0
    assert result.results == ()
    assert any(
        "conveyor discovery payload audit" in message
        and f'"field": "{field}"' in message
        and f'"reason": "{reason}"' in message
        for message in logs
    )
    assert prepare.calls == []
    assert land.calls == []
    assert git.calls == []
    assert gh.calls == []
    assert ledger == []


def test_schema_rejected_discovery_item_is_skipped_without_dropping_valid_item():
    prepare = FakePrepare()
    land = FakeLand()
    git = FakeGit()
    gh = FakeGh()
    ledger: list[ConveyorDaemonLedgerRecord] = []
    logs: list[str] = []
    rejected_payload = {**_data_only_payload(), "validate_command": ["touch", "/tmp/pwned"]}
    valid_item = _item()

    result = ConveyorDaemon(
        discovery_runner=lambda: [valid_item, rejected_payload],
        armed=True,
        **ARMED_ROOTS,
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=ledger.append,
        log_runner=logs.append,
        prepare_runner=prepare,
        land_runner=land,
    ).run_once()

    assert result.discovery_error is None
    assert result.discovered_count == 1
    assert [item.status for item in result.results] == ["pr-opened"]
    assert [spec.branch for spec in prepare.calls] == ["Feature/One"]
    assert land.calls == [(valid_item.bundle_path, "feature-one", "origin/main", valid_item.repo_path)]
    assert git.calls == [(("push", "--", "origin", "feature-one:feature-one"), valid_item.repo_path)]
    assert len(gh.calls) == 1
    assert any(
        "conveyor discovery payload audit" in message
        and '"field": "validate_command"' in message
        and '"reason": "banned_control_field"' in message
        for message in logs
    )
    assert not any("conveyor discovery failed" in message for message in logs)


def test_data_only_discovery_mapping_plans_without_payload_paths():
    logs: list[str] = []

    result = ConveyorDaemon(
        discovery_runner=lambda: [_data_only_payload()],
        log_runner=logs.append,
    ).run_once()

    assert result.discovery_error is None
    assert result.discovered_count == 1
    assert result.results[0].status == "planned"
    assert result.results[0].branch == "feature-one"
    assert result.results[0].key == "feature-one"
    assert not any("payload audit" in message for message in logs)


def test_data_only_discovery_mapping_allocates_once_and_flows_downstream():
    prepare = FakePrepare()
    git = FakeGit()
    gh = FakeGh()
    allocator = CountingAllocator()

    result = ConveyorDaemon(
        discovery_runner=lambda: [_data_only_payload()],
        armed=True,
        path_allocator=allocator,
        daemon_lease=FakeLease(),
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=lambda record: None,
        prepare_runner=prepare,
        land_runner=FakeLand(),
    ).run_once()

    assert result.results[0].status == "pr-opened"
    assert allocator.allocate_calls == [{"repo": "feature-one", "branch_name": "feature-one"}]
    assert len(allocator.allocations) == 1
    allocation = allocator.allocations[0]
    assert prepare.calls[0].worktree_path == allocation.worktree_path
    assert git.calls == [(("push", "--", "origin", "feature-one:feature-one"), allocation.repo_path)]
    assert len(gh.calls) == 1


def test_direct_item_with_paths_and_no_receipt_fails_before_prepare_land_git_or_gh():
    prepare = FakePrepare()
    land = FakeLand()
    git = FakeGit()
    gh = FakeGh()

    result = ConveyorDaemon(
        discovery_runner=lambda: [_item_without_receipt()],
        armed=True,
        **ARMED_ROOTS,
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=lambda record: None,
        prepare_runner=prepare,
        land_runner=land,
    ).run_once()

    assert result.results[0].status == "failed"
    assert result.results[0].reasons == ("executable item paths require a valid daemon allocation receipt",)
    assert prepare.calls == []
    assert land.calls == []
    assert git.calls == []
    assert gh.calls == []


def test_forged_receipt_from_another_allocator_instance_is_refused_before_prepare():
    prepare = FakePrepare()
    git = FakeGit()
    gh = FakeGh()
    foreign_allocator = CountingAllocator()
    foreign_allocation, foreign_receipt = foreign_allocator.allocate_conveyor_paths(
        repo="feature-one",
        branch_name="Feature/One",
    )
    item = ConveyorDaemonItem(
        branch="Feature/One",
        worktree_path=foreign_allocation.worktree_path,
        bundle_path=foreign_allocation.bundle_path,
        repo_path=foreign_allocation.repo_path,
        title="Land Feature/One",
        body="- Conveyor item.",
        allocation_receipt=foreign_receipt,
    )

    result = ConveyorDaemon(
        discovery_runner=lambda: [item],
        armed=True,
        **ARMED_ROOTS,
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=lambda record: None,
        prepare_runner=prepare,
        land_runner=FakeLand(),
    ).run_once()

    assert result.results[0].status == "failed"
    assert result.results[0].reasons == ("daemon allocation receipt rejected: receipt was not issued by this allocator",)
    assert prepare.calls == []
    assert git.calls == []
    assert gh.calls == []


def test_daemon_pinned_validate_command_used_for_item_objects():
    prepare = FakePrepare()
    daemon = ConveyorDaemon(
        discovery_runner=lambda: [_item()],
        armed=True,
        **ARMED_ROOTS,
        git_runner=FakeGit(),
        validate_runner=FakeValidate(),
        gh_runner=FakeGh(),
        now=FakeClock(),
        ledger_writer=lambda record: None,
        prepare_runner=prepare,
        land_runner=FakeLand(),
        validate_command=(sys.executable, "-m", "creator_engine_validator.ce_cli", "validate-pr"),
    )
    daemon.run_once()

    assert prepare.calls[0].validate_command == (
        sys.executable,
        "-m",
        "creator_engine_validator.ce_cli",
        "validate-pr",
    )


def test_daemon_pinned_base_and_remote_used_for_item_objects():
    prepare = FakePrepare()
    land = FakeLand()
    git_calls: list[tuple[str, ...]] = []

    def git_runner(args: Sequence[str], cwd: Path, env: Mapping[str, str]) -> ConveyorCommandResult:
        git_calls.append(tuple(args))
        return ConveyorCommandResult(0, "pushed\n", "")

    ConveyorDaemon(
        discovery_runner=lambda: [_item()],
        armed=True,
        **ARMED_ROOTS,
        git_runner=git_runner,
        validate_runner=FakeValidate(),
        gh_runner=FakeGh(),
        now=FakeClock(),
        ledger_writer=lambda record: None,
        prepare_runner=prepare,
        land_runner=land,
        base="origin/main",
        remote="origin",
    ).run_once()

    assert prepare.calls[0].base == "origin/main"
    assert land.calls[0][2] == "origin/main"
    assert ("push", "--", "origin", "feature-one:feature-one") in git_calls


def test_gh_pr_title_and_body_leading_dashes_remain_flag_values():
    gh = FakeGh()
    item = dataclasses.replace(
        _item(),
        pr_title="--not-a-gh-flag",
        pr_body="--still-free-text",
    )

    result = ConveyorDaemon(
        discovery_runner=lambda: [item],
        armed=True,
        **ARMED_ROOTS,
        git_runner=FakeGit(),
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=lambda record: None,
        prepare_runner=FakePrepare(),
        land_runner=FakeLand(),
    ).run_once()

    assert result.results[0].status == "pr-opened"
    pr_args = gh.calls[0][0]
    assert pr_args[pr_args.index("--title") + 1] == "--not-a-gh-flag"
    assert pr_args[pr_args.index("--body") + 1] == "--still-free-text"


def test_daemon_construction_rejects_dangerous_base():
    """Defense-in-depth: even trusted constructor-level config is rejected
    if it is shaped like a git argv-injection gadget."""

    with pytest.raises(ValueError):
        ConveyorDaemon(discovery_runner=lambda: [], base="--exec=touch /tmp/pwned")


def test_daemon_construction_rejects_dangerous_remote():
    """Defense-in-depth: even trusted constructor-level config is rejected
    if it is shaped like a git transport-helper gadget."""

    with pytest.raises(ValueError):
        ConveyorDaemon(discovery_runner=lambda: [], remote="ext::sh -c 'touch /tmp/pwned'")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"base": "--main"},
        {"remote": "--origin"},
        {"base": "origin/feature branch"},
        {"remote": "origin:evil"},
    ],
)
def test_daemon_construction_rejects_ref_shape_violations(kwargs: dict[str, str]):
    with pytest.raises(ValueError):
        ConveyorDaemon(discovery_runner=lambda: [], **kwargs)


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("branch", "--feature", "must not start with '-'"),
        ("branch", "feature topic", "disallowed in git refs"),
        ("branch", "feature..topic", "must not contain '..'"),
        ("branch", "feature.lock", "must not end with '.lock'"),
        ("pr_base", "--release", "must not start with '-'"),
        ("pr_base", "release topic", "disallowed in git refs"),
    ],
)
def test_hostile_item_ref_shape_is_rejected_before_git_or_gh(field: str, value: str, reason: str):
    prepare = FakePrepare()
    land = FakeLand()
    git = FakeGit()
    gh = FakeGh()

    hostile_item = dataclasses.replace(_item(), **{field: value})

    result = ConveyorDaemon(
        discovery_runner=lambda: [hostile_item],
        armed=True,
        **ARMED_ROOTS,
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=lambda record: None,
        prepare_runner=prepare,
        land_runner=land,
    ).run_once()

    assert result.results[0].status == "failed"
    assert any(field in rejected and reason in rejected for rejected in result.results[0].reasons)
    assert prepare.calls == []
    assert land.calls == []
    assert git.calls == []
    assert gh.calls == []


def test_landed_branch_shape_is_rejected_before_push_or_pr_open():
    prepare = FakePrepare()
    land = FakeLand(branch_override="feature topic")
    git = FakeGit()
    gh = FakeGh()

    result = ConveyorDaemon(
        discovery_runner=lambda: [_item()],
        armed=True,
        **ARMED_ROOTS,
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=lambda record: None,
        prepare_runner=prepare,
        land_runner=land,
    ).run_once()

    assert result.results[0].status == "failed"
    assert result.results[0].landing_result is not None
    assert any("landed.branch" in reason and "disallowed in git refs" in reason for reason in result.results[0].reasons)
    assert len(prepare.calls) == 1
    assert len(land.calls) == 1
    assert git.calls == []
    assert gh.calls == []


def test_idempotent_re_discovery_skips_completed_item():
    git = FakeGit()
    gh = FakeGh()
    daemon = ConveyorDaemon(
        discovery_runner=lambda: [_item()],
        armed=True,
        **ARMED_ROOTS,
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


def test_hostile_item_bundle_path_transport_gadget_is_rejected_never_reaches_git():
    """A compromised harvest seat authors the bundle file, so a trusted
    in-process item can still carry a hostile bundle FILENAME. Naming it
    `ext::sh -c '<cmd>'` would pass
    `git bundle verify` (real bundle bytes can live at that literal path)
    and then `git fetch` resolves `ext::` as a transport-helper invocation
    -- RCE. This must be rejected before the item ever reaches git_runner,
    not merely before the fetch call."""

    prepare = FakePrepare()
    land = FakeLand()
    git = FakeGit()
    gh = FakeGh()
    ledger: list[ConveyorDaemonLedgerRecord] = []
    logs: list[str] = []

    hostile_item = dataclasses.replace(
        _item(),
        bundle_path=Path("ext::sh -c 'touch /tmp/pwned'"),
    )

    daemon = ConveyorDaemon(
        discovery_runner=lambda: [hostile_item],
        armed=True,
        **ARMED_ROOTS,
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

    assert result.results[0].status == "failed"
    assert any("bundle_path" in reason for reason in result.results[0].reasons)
    assert prepare.calls == []
    assert land.calls == []
    assert git.calls == []
    assert gh.calls == []
    assert ledger == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("bundle_path", "/var/tmp/attacker-repo/evil.bundle"),
        ("repo_path", "/var/tmp/attacker-repo"),
        ("worktree_path", "/var/tmp/attacker-repo/worktree"),
    ],
)
def test_hostile_item_path_outside_trusted_root_is_rejected(field: str, value: str):
    """An item path (bundle_path/repo_path/worktree_path) that resolves
    OUTSIDE the daemon's pinned trusted root must be rejected fail-closed
    and the item skipped -- this is what stops an attacker-staged repo
    (with a poisoned `.git/config` remote) from ever becoming the git cwd,
    which would let a trusted literal `remote`/`base` resolve to an
    attacker-controlled transport-helper URL."""

    prepare = FakePrepare()
    land = FakeLand()
    git = FakeGit()
    gh = FakeGh()
    ledger: list[ConveyorDaemonLedgerRecord] = []
    logs: list[str] = []

    hostile_item = dataclasses.replace(_item(), **{field: Path(value)})

    daemon = ConveyorDaemon(
        discovery_runner=lambda: [hostile_item],
        armed=True,
        **ARMED_ROOTS,
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

    assert result.results[0].status == "failed"
    assert any(field in reason and "trusted root" in reason for reason in result.results[0].reasons)
    assert prepare.calls == []
    assert land.calls == []
    assert git.calls == []
    assert gh.calls == []
    assert ledger == []


def test_hostile_item_dotdot_traversal_path_is_rejected():
    """A path that starts under the trusted root syntactically but walks
    back out via `..` must resolve to outside the root and be rejected,
    the same as an absolute directory-redirection path."""

    prepare = FakePrepare()
    land = FakeLand()
    git = FakeGit()
    gh = FakeGh()
    ledger: list[ConveyorDaemonLedgerRecord] = []

    hostile_item = dataclasses.replace(_item(), repo_path=Path("/tmp/../var/tmp/attacker-repo"))

    daemon = ConveyorDaemon(
        discovery_runner=lambda: [hostile_item],
        armed=True,
        **ARMED_ROOTS,
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=ledger.append,
        prepare_runner=prepare,
        land_runner=land,
    )
    result = daemon.run_once()

    assert result.results[0].status == "failed"
    assert any("repo_path" in reason and "trusted root" in reason for reason in result.results[0].reasons)
    assert prepare.calls == []
    assert git.calls == []
    assert gh.calls == []


def test_hostile_item_pr_base_gadget_is_rejected():
    """`pr_base` reaches a fixed `gh pr create --base <value>` flag-value
    slot (not RCE from that slot), but a gadget-shaped value must still be
    rejected fail-closed rather than silently misdirecting the PR."""

    prepare = FakePrepare()
    land = FakeLand()
    git = FakeGit()
    gh = FakeGh()
    ledger: list[ConveyorDaemonLedgerRecord] = []

    hostile_item = dataclasses.replace(_item(), pr_base="ext::sh -c 'touch /tmp/pwned'")

    daemon = ConveyorDaemon(
        discovery_runner=lambda: [hostile_item],
        armed=True,
        **ARMED_ROOTS,
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=ledger.append,
        prepare_runner=prepare,
        land_runner=land,
    )
    result = daemon.run_once()

    assert result.results[0].status == "failed"
    assert any("pr_base" in reason for reason in result.results[0].reasons)
    assert prepare.calls == []
    assert git.calls == []
    assert gh.calls == []


def test_toctou_resolved_path_used_not_raw_item_value_after_confinement_check():
    """Regression test for the TOCTOU (CWE-367) fix.

    `_path_confinement_violations` resolves each item path (symlinks +
    `..` collapsed) and validates the RESULT lands under the trusted root --
    but the earlier buggy version discarded that resolved value and let
    `_process_armed` go on using the raw, unresolved `item.bundle_path` /
    `item.repo_path` / `item.worktree_path` for every real git/gh call. That
    is a check-then-use race: an attacker who passes the check with a
    legitimate-looking path, then swaps that path for a symlink into an
    attacker-controlled repo before the harvest/validate/land/push/pr-open
    sequence actually runs, would defeat confinement entirely even though
    the check itself "passed".

    Here every raw item path IS a symlink that legitimately resolves under
    the trusted root (so confinement correctly allows it), and this test
    asserts every downstream call (prepare/land/push/pr-open) receives the
    RESOLVED realpath -- not the raw symlink Path -- proving the daemon
    operates on the value validated under root, immune to a later swap of
    the symlink target.
    """

    real_repo = Path(tempfile.mkdtemp(dir=TEST_ALLOCATOR.roots.repo_root, prefix="conveyor-toctou-real-repo-"))
    real_worktree = Path(tempfile.mkdtemp(dir=TEST_ALLOCATOR.roots.worktree_root, prefix="conveyor-toctou-real-wt-"))
    real_bundle_dir = Path(tempfile.mkdtemp(dir=TEST_ALLOCATOR.roots.bundle_root, prefix="conveyor-toctou-real-bundle-"))
    real_bundle = real_bundle_dir / "feature-one.bundle"
    real_bundle.write_bytes(b"")
    item = _item()

    assert item.repo_path is not None
    assert item.worktree_path is not None
    assert item.bundle_path is not None
    symlink_repo = item.repo_path
    symlink_worktree = item.worktree_path
    symlink_bundle = item.bundle_path
    symlink_repo.rmdir()
    symlink_worktree.rmdir()
    symlink_bundle.rmdir()
    symlink_repo.symlink_to(real_repo)
    symlink_worktree.symlink_to(real_worktree)
    symlink_bundle.symlink_to(real_bundle)

    try:
        prepare = FakePrepare()
        land = FakeLand()
        git = FakeGit()
        gh = FakeGh()
        ledger: list[ConveyorDaemonLedgerRecord] = []

        result = ConveyorDaemon(
            discovery_runner=lambda: [item],
            armed=True,
            **ARMED_ROOTS,
            git_runner=git,
            validate_runner=FakeValidate(),
            gh_runner=gh,
            now=FakeClock(),
            ledger_writer=ledger.append,
            prepare_runner=prepare,
            land_runner=land,
        ).run_once()

        assert result.results[0].status == "pr-opened"

        # The raw symlink paths legitimately clear confinement (they resolve
        # under /tmp), but every real call below must have been made with
        # the RESOLVED realpath, never the raw symlink Path.
        assert prepare.calls[0].worktree_path == real_worktree
        assert prepare.calls[0].worktree_path != symlink_worktree

        assert land.calls == [(real_bundle, "feature-one", "origin/main", real_repo)]
        assert land.calls[0][0] != symlink_bundle
        assert land.calls[0][3] != symlink_repo

        assert git.calls == [(("push", "--", "origin", "feature-one:feature-one"), real_repo)]
        assert all(cwd != symlink_repo for _, cwd in git.calls)

        assert len(gh.calls) == 1
        assert gh.calls[0][1] == real_repo
        assert gh.calls[0][1] != symlink_repo
    finally:
        for symlink in (symlink_repo, symlink_worktree, symlink_bundle):
            if symlink.is_symlink():
                symlink.unlink()
        shutil.rmtree(real_repo, ignore_errors=True)
        shutil.rmtree(real_worktree, ignore_errors=True)
        shutil.rmtree(real_bundle_dir, ignore_errors=True)


def test_path_confinement_violations_returns_resolved_paths_on_success():
    """`_path_confinement_violations` must hand back the resolved Path for
    each confined field (not just report pass/fail) -- this is the value
    `_process_armed` threads through the rest of processing to close the
    TOCTOU window. This test exercises the helper directly."""

    daemon = ConveyorDaemon(
        discovery_runner=lambda: [],
        armed=True,
        **ARMED_ROOTS,
        git_runner=FakeGit(),
        validate_runner=FakeValidate(),
        gh_runner=FakeGh(),
        now=FakeClock(),
        ledger_writer=lambda record: None,
        prepare_runner=FakePrepare(),
        land_runner=FakeLand(),
    )

    item = _item()
    violations, resolved = daemon._path_confinement_violations(item)

    assert violations == ()
    assert resolved == {
        "bundle_path": item.bundle_path.resolve(),
        "repo_path": item.repo_path.resolve(),
        "worktree_path": item.worktree_path.resolve(),
    }


def test_daemon_construction_requires_repo_root_and_bundle_root_when_armed():
    """Armed mode has no safe default trusted root (unlike base/remote),
    so repo_root/bundle_root must be supplied explicitly, mirroring the
    other armed-mode required seams (git_runner, validate_runner, ...)."""

    with pytest.raises(ValueError):
        ConveyorDaemon(
            discovery_runner=lambda: [],
            armed=True,
            git_runner=FakeGit(),
            validate_runner=FakeValidate(),
            gh_runner=FakeGh(),
            now=FakeClock(),
            ledger_writer=lambda record: None,
        )
