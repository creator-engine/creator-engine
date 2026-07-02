from __future__ import annotations

import shutil
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


HEAD_SHA = "0123456789abcdef0123456789abcdef01234567"

# Trusted confinement roots for armed-daemon tests. All fake item paths below
# (worktree_path/repo_path under /tmp/..., bundle_path under
# /tmp/....bundle) are constructed to resolve under these roots so the new
# path-confinement gate (ConveyorDaemon._path_confinement_violations) does
# not reject otherwise-legitimate test fixtures. Hostile-payload tests below
# deliberately point OUTSIDE these roots (or use gadget-shaped filenames) to
# exercise the rejection path.
TRUSTED_REPO_ROOT = Path("/tmp")
TRUSTED_BUNDLE_ROOT = Path("/tmp")
ARMED_ROOTS = {"repo_root": TRUSTED_REPO_ROOT, "bundle_root": TRUSTED_BUNDLE_ROOT}


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
    assert git.calls == [(("push", "origin", "feature-two:feature-two"), Path("/tmp/landing"))]
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
        **ARMED_ROOTS,
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


def test_hostile_payload_base_override_is_ignored():
    """A malicious/compromised discovery payload must never control `base`:
    it flows into a bare positional `git rebase <base>` / `git fetch`
    argv slot, so `--exec=<cmd>` there is RCE. `base` is pinned at the
    daemon level (mirrors validate_command) and any payload-supplied
    override is dropped (and logged), not honored."""

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
        "base": "--exec=touch /tmp/pwned",
    }

    daemon = ConveyorDaemon(
        discovery_runner=lambda: [hostile_payload],
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

    assert result.results[0].status == "pr-opened"
    used_base = prepare.calls[0].base
    assert used_base == daemon.base == "origin/main"
    assert used_base != "--exec=touch /tmp/pwned"
    assert land.calls == [(Path("/tmp/feature-one.bundle"), "feature-one", "origin/main", Path("/tmp/landing"))]
    assert not any("--exec" in str(call) for call in git.calls)
    assert any("attempted to override base" in message for message in logs)


def test_hostile_payload_remote_override_is_ignored():
    """A malicious/compromised discovery payload must never control
    `remote`: it flows into the bare `<repository>` positional of
    `git push <remote> ...`, so an `ext::<cmd>` transport-helper value there
    is RCE. `remote` is pinned at the daemon level and any payload-supplied
    override is dropped (and logged), not honored."""

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
        "remote": "ext::sh -c 'touch /tmp/pwned'",
    }

    daemon = ConveyorDaemon(
        discovery_runner=lambda: [hostile_payload],
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

    assert result.results[0].status == "pr-opened"
    assert daemon.remote == "origin"
    assert git.calls == [(("push", "origin", "feature-one:feature-one"), Path("/tmp/landing"))]
    assert not any("ext::" in str(call) for call in git.calls)
    assert any("attempted to override remote" in message for message in logs)


def test_daemon_pinned_base_and_remote_used_regardless_of_payload():
    """Even benign-looking payload base/remote values are ignored: the
    daemon's own configured base/remote (constructor-level) is always what
    gets used for rebase/land/push."""

    prepare = FakePrepare()
    land = FakeLand()
    git_calls: list[tuple[str, ...]] = []

    def git_runner(args: Sequence[str], cwd: Path) -> ConveyorCommandResult:
        git_calls.append(tuple(args))
        return ConveyorCommandResult(0, "pushed\n", "")

    gh = FakeGh()
    daemon = ConveyorDaemon(
        discovery_runner=lambda: [
            {
                "branch": "Feature/One",
                "worktree_path": "/tmp/feature-one",
                "bundle_path": "/tmp/feature-one.bundle",
                "repo_path": "/tmp/landing",
                "title": "Land Feature/One",
                "body": "- Conveyor item.",
                "base": "origin/release",
                "remote": "upstream",
            }
        ],
        armed=True,
        **ARMED_ROOTS,
        git_runner=git_runner,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=lambda record: None,
        prepare_runner=prepare,
        land_runner=land,
        base="origin/main",
        remote="origin",
    )
    daemon.run_once()

    assert prepare.calls[0].base == "origin/main"
    assert land.calls[0][2] == "origin/main"
    assert ("push", "origin", "feature-one:feature-one") in git_calls


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


def test_hostile_payload_bundle_path_transport_gadget_is_rejected_never_reaches_git():
    """A compromised harvest seat authors the bundle file, so it controls
    the bundle's FILENAME. Naming it `ext::sh -c '<cmd>'` would pass
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

    hostile_payload = {
        "branch": "Feature/One",
        "worktree_path": "/tmp/feature-one",
        "bundle_path": "ext::sh -c 'touch /tmp/pwned'",
        "repo_path": "/tmp/landing",
        "title": "Land Feature/One",
        "body": "- Conveyor item.",
    }

    daemon = ConveyorDaemon(
        discovery_runner=lambda: [hostile_payload],
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
def test_hostile_payload_path_outside_trusted_root_is_rejected(field: str, value: str):
    """A payload path (bundle_path/repo_path/worktree_path) that resolves
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

    hostile_payload = {
        "branch": "Feature/One",
        "worktree_path": "/tmp/feature-one",
        "bundle_path": "/tmp/feature-one.bundle",
        "repo_path": "/tmp/landing",
        "title": "Land Feature/One",
        "body": "- Conveyor item.",
    }
    hostile_payload[field] = value

    daemon = ConveyorDaemon(
        discovery_runner=lambda: [hostile_payload],
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


def test_hostile_payload_dotdot_traversal_path_is_rejected():
    """A path that starts under the trusted root syntactically but walks
    back out via `..` must resolve to outside the root and be rejected,
    the same as an absolute directory-redirection path."""

    prepare = FakePrepare()
    land = FakeLand()
    git = FakeGit()
    gh = FakeGh()
    ledger: list[ConveyorDaemonLedgerRecord] = []

    hostile_payload = {
        "branch": "Feature/One",
        "worktree_path": "/tmp/feature-one",
        "bundle_path": "/tmp/feature-one.bundle",
        "repo_path": "/tmp/../var/tmp/attacker-repo",
        "title": "Land Feature/One",
        "body": "- Conveyor item.",
    }

    daemon = ConveyorDaemon(
        discovery_runner=lambda: [hostile_payload],
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


def test_hostile_payload_pr_base_gadget_is_rejected():
    """`pr_base` reaches a fixed `gh pr create --base <value>` flag-value
    slot (not RCE from that slot), but a gadget-shaped value must still be
    rejected fail-closed rather than silently misdirecting the PR."""

    prepare = FakePrepare()
    land = FakeLand()
    git = FakeGit()
    gh = FakeGh()
    ledger: list[ConveyorDaemonLedgerRecord] = []

    hostile_payload = {
        "branch": "Feature/One",
        "worktree_path": "/tmp/feature-one",
        "bundle_path": "/tmp/feature-one.bundle",
        "repo_path": "/tmp/landing",
        "title": "Land Feature/One",
        "body": "- Conveyor item.",
        "pr_base": "ext::sh -c 'touch /tmp/pwned'",
    }

    daemon = ConveyorDaemon(
        discovery_runner=lambda: [hostile_payload],
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

    `_path_confinement_violations` resolves each payload path (symlinks +
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

    real_repo = Path(tempfile.mkdtemp(dir="/tmp", prefix="conveyor-toctou-real-repo-"))
    real_worktree = Path(tempfile.mkdtemp(dir="/tmp", prefix="conveyor-toctou-real-wt-"))
    real_bundle_dir = Path(tempfile.mkdtemp(dir="/tmp", prefix="conveyor-toctou-real-bundle-"))
    real_bundle = real_bundle_dir / "feature-one.bundle"
    real_bundle.write_bytes(b"")
    scratch = Path(tempfile.mkdtemp(dir="/tmp", prefix="conveyor-toctou-symlinks-"))

    symlink_repo = scratch / "repo-symlink"
    symlink_worktree = scratch / "worktree-symlink"
    symlink_bundle = scratch / "bundle-symlink.bundle"
    symlink_repo.symlink_to(real_repo)
    symlink_worktree.symlink_to(real_worktree)
    symlink_bundle.symlink_to(real_bundle)

    try:
        prepare = FakePrepare()
        land = FakeLand()
        git = FakeGit()
        gh = FakeGh()
        ledger: list[ConveyorDaemonLedgerRecord] = []

        item = ConveyorDaemonItem(
            branch="Feature/One",
            worktree_path=symlink_worktree,
            bundle_path=symlink_bundle,
            repo_path=symlink_repo,
            title="Land Feature/One",
            body="- Conveyor item.",
        )

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

        assert git.calls == [(("push", "origin", "feature-one:feature-one"), real_repo)]
        assert all(cwd != symlink_repo for _, cwd in git.calls)

        assert len(gh.calls) == 1
        assert gh.calls[0][1] == real_repo
        assert gh.calls[0][1] != symlink_repo
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
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
