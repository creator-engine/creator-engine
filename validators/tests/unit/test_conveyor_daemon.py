from __future__ import annotations

import dataclasses
import hashlib
import shutil
import subprocess
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
from creator_engine_validator.validation_sandbox import ValidationSandboxResult
from creator_engine_validator.validation_sandbox_runner import ValidationSandboxContainerRun
from creator_engine_validator.conveyor_daemon import (
    PLAN_ACTIONS,
    ConveyorDaemon,
    ConveyorDaemonItem,
    ConveyorDaemonLedgerRecord,
    ConveyorValidationLedgerBinding,
    _PUBLISH_TRANSPORT_CONFIG_PATTERN,
)
from creator_engine_validator.forge.daemon_allocation import DaemonPathAllocator, DaemonRuntimeRoots
from creator_engine_validator.validation_sandbox_receipt import ValidationSandboxReceiptIssuer


HEAD_SHA = "0123456789abcdef0123456789abcdef01234567"

TEST_RUNTIME_ROOT = Path(tempfile.mkdtemp(dir="/tmp", prefix="conveyor-daemon-alloc-test-"))
TEST_ALLOCATOR = DaemonPathAllocator(
    DaemonRuntimeRoots.from_root(TEST_RUNTIME_ROOT, create=True),
    secret=b"conveyor-daemon-unit-test-secret",
)


class FakeLease:
    def __init__(self, *, fail_on_call: int | None = None):
        self.heartbeat_calls = 0
        self.fail_on_call = fail_on_call

    def heartbeat(self) -> None:
        self.heartbeat_calls += 1
        if self.fail_on_call == self.heartbeat_calls:
            raise RuntimeError("lost lease heartbeat")


def _receipt_issuer() -> ValidationSandboxReceiptIssuer:
    return ValidationSandboxReceiptIssuer(secret=b"conveyor-validation-receipt-secret")


def _validation_ledger_binding() -> ConveyorValidationLedgerBinding:
    return ConveyorValidationLedgerBinding(
        controller_id="conveyor-daemon-test-controller",
        lane_id="conveyor-daemon-test-lane",
        claim_ref="claims/conveyor-daemon-test-controller/conveyor-daemon-test-lane.yaml",
        repo_root=TEST_RUNTIME_ROOT,
        side_effect_ledger_root=TEST_RUNTIME_ROOT / "side-effect-ledger",
        active_work_ledger_root=TEST_RUNTIME_ROOT / "active-work-ledger",
    )


ARMED_ROOTS = {
    "path_allocator": TEST_ALLOCATOR,
    "daemon_lease": FakeLease(),
    "receipt_issuer": _receipt_issuer(),
    "validation_ledger_binding": _validation_ledger_binding(),
}


class FakeGit:
    def __init__(
        self,
        push_returncode: int = 0,
        landed_tree_sha: str = HEAD_SHA,
        *,
        landed_tree_shas: Sequence[str] | None = None,
        landed_commit_sha: str = HEAD_SHA,
        rev_list_stdout: str = "0\t1\n",
        diff_stdout: str | None = None,
        config_returncode: int = 1,
        config_stdout: str = "",
        config_stderr: str = "",
    ):
        self.push_returncode = push_returncode
        self.landed_tree_sha = landed_tree_sha
        self.landed_tree_shas = list(landed_tree_shas or [])
        self.landed_commit_sha = landed_commit_sha
        self.rev_list_stdout = rev_list_stdout
        self.diff_stdout = diff_stdout
        self.config_returncode = config_returncode
        self.config_stdout = config_stdout
        self.config_stderr = config_stderr
        self.calls: list[tuple[tuple[str, ...], Path]] = []
        self.envs: list[Mapping[str, str]] = []

    def __call__(self, args: Sequence[str], cwd: Path, env: Mapping[str, str]) -> ConveyorCommandResult:
        self.calls.append((tuple(args), cwd))
        self.envs.append(dict(env))
        if tuple(args) == ("rev-parse", "HEAD^{tree}"):
            return ConveyorCommandResult(0, f"{self.landed_tree_sha}\n", "")
        if len(args) == 2 and args[0] == "rev-parse" and str(args[1]).endswith("^{tree}"):
            if self.landed_tree_shas:
                return ConveyorCommandResult(0, f"{self.landed_tree_shas.pop(0)}\n", "")
            return ConveyorCommandResult(0, f"{self.landed_tree_sha}\n", "")
        if len(args) == 2 and args[0] == "rev-parse" and str(args[1]).endswith("^{commit}"):
            return ConveyorCommandResult(0, f"{self.landed_commit_sha}\n", "")
        if len(args) == 4 and tuple(args[:3]) == ("rev-list", "--left-right", "--count"):
            return ConveyorCommandResult(0, self.rev_list_stdout, "")
        if len(args) == 4 and tuple(args[:3]) == ("diff", "--name-status", "--find-renames"):
            branch = str(args[3]).rsplit("..", 1)[-1]
            return ConveyorCommandResult(0, self.diff_stdout or _default_diff_name_status(branch), "")
        if tuple(args) == (
            "config",
            "--local",
            "--get-regexp",
            _PUBLISH_TRANSPORT_CONFIG_PATTERN,
        ):
            return ConveyorCommandResult(self.config_returncode, self.config_stdout, self.config_stderr)
        if tuple(args) == ("push", "--", "origin", "feature-one:feature-one"):
            if self.push_returncode:
                return ConveyorCommandResult(self.push_returncode, "", "push denied\n")
            return ConveyorCommandResult(0, "pushed\n", "")
        if tuple(args) == ("push", "--", "origin", "feature-two:feature-two"):
            return ConveyorCommandResult(0, "pushed\n", "")
        return ConveyorCommandResult(1, "", f"unexpected git call: {args}")


class RealLocalGit:
    def __init__(self, *, fake_landed_tree_from_validation: bool = False):
        self.fake_landed_tree_from_validation = fake_landed_tree_from_validation
        self.calls: list[tuple[tuple[str, ...], Path]] = []
        self.envs: list[Mapping[str, str]] = []
        self.rev_parse_trees: list[str] = []

    def __call__(self, args: Sequence[str], cwd: Path, env: Mapping[str, str]) -> ConveyorCommandResult:
        self.calls.append((tuple(args), cwd))
        self.envs.append(dict(env))
        if tuple(args) == ("push", "--", "origin", "feature-one:feature-one"):
            return ConveyorCommandResult(0, "pushed\n", "")
        if (
            len(args) == 2
            and args[0] == "rev-parse"
            and str(args[1]).endswith("^{commit}")
            and not (cwd / ".git").exists()
        ):
            return ConveyorCommandResult(0, f"{HEAD_SHA}\n", "")
        if len(args) == 4 and tuple(args[:3]) == ("rev-list", "--left-right", "--count"):
            return ConveyorCommandResult(0, "0\t1\n", "")
        if len(args) == 4 and tuple(args[:3]) == ("diff", "--name-status", "--find-renames"):
            branch = str(args[3]).rsplit("..", 1)[-1]
            return ConveyorCommandResult(0, _default_diff_name_status(branch), "")
        if tuple(args) == (
            "config",
            "--local",
            "--get-regexp",
            _PUBLISH_TRANSPORT_CONFIG_PATTERN,
        ):
            return ConveyorCommandResult(1, "", "")
        if (
            self.fake_landed_tree_from_validation
            and len(args) == 2
            and args[0] == "rev-parse"
            and str(args[1]).endswith("^{tree}")
            and args[1] != "HEAD^{tree}"
            and self.rev_parse_trees
        ):
            return ConveyorCommandResult(0, f"{self.rev_parse_trees[-1]}\n", "")
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            env=dict(env),
            check=False,
            capture_output=True,
            text=True,
        )
        if tuple(args) == ("rev-parse", "HEAD^{tree}") and completed.returncode == 0:
            self.rev_parse_trees.append(completed.stdout.strip())
        return ConveyorCommandResult(completed.returncode, completed.stdout, completed.stderr)


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


def _run_fake_validation(spec: ConveyorHarvestSpec, validate_runner) -> ConveyorCommandResult:
    return validate_runner(
        spec.validate_command,
        spec.worktree_path,
        {"PATH": "/usr/bin:/bin", "PYTHONPATH": str(spec.worktree_path / "validators")},
    )


class FakePrepare:
    def __init__(self, failing_branches: set[str] | None = None, *, record_validation: bool = False):
        self.failing_branches = failing_branches or set()
        self.record_validation = record_validation
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
        if self.record_validation:
            validation = _run_fake_validation(spec, validate_runner)
            if validation.returncode != 0:
                return _harvest_result(spec, ready=False, reasons=(validation.stderr,))
        return _harvest_result(spec, ready=True, reasons=())


class FakeLand:
    def __init__(self, branch_override: str | None = None, *, behind: int = 0):
        self.branch_override = branch_override
        self.behind = behind
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
        _write_carrier_manifest(repo_path, branch_slug=landed_branch)
        return ConveyorBundleLandingResult(
            ready=True,
            reasons=(),
            bundle_path=bundle_path,
            branch=landed_branch,
            branch_slug=landed_branch,
            base_ref=base_ref,
            head_sha=HEAD_SHA,
            ahead=1,
            behind=self.behind,
        )


class FakeClock:
    def __init__(self):
        self.count = 0

    def __call__(self) -> str:
        self.count += 1
        return f"2026-07-01T00:00:0{self.count}Z"


class FakePodmanRunner:
    def __init__(self):
        self.calls: list[tuple[list[str], float | None]] = []

    def podman_run_supports_timeout(self, binary: str) -> bool:
        return binary == "podman"

    def run(self, argv: Sequence[str], *, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
        self.calls.append((list(argv), timeout))
        return subprocess.CompletedProcess(list(argv), 0, "validated\n", "")


class FakeValidationSandboxRunner:
    def __init__(
        self,
        *,
        side_effect_path: Path | None = None,
        side_effect_record: Mapping[str, object] | None = None,
    ):
        self.calls: list[tuple[object, dict]] = []
        self.side_effect_path = side_effect_path
        self.side_effect_record = side_effect_record

    def __call__(self, spec, **kwargs) -> ValidationSandboxContainerRun:
        self.calls.append((spec, dict(kwargs)))
        receipt = kwargs["receipt_issuer"].mint(
            tree_sha=kwargs["tree_sha"],
            command=spec.command,
            policy_sha="a" * 64,
            image_sha="sha256:" + "b" * 64,
            mount_manifest_applied=({"path": str(spec.cwd), "mode": "ro"},),
            egress_allowlist_applied=(),
            secret_allowlist_applied=(),
            returncode=0,
        )
        return ValidationSandboxContainerRun(
            result=ValidationSandboxResult(rc=0, stdout="validated\n", stderr="", duration=0.01, spec=spec),
            receipt=receipt,
            side_effect_path=self.side_effect_path,
            side_effect_record=self.side_effect_record,
        )


class FakeLedgerResult:
    def __init__(self, record_path: Path, record: dict):
        self.record_path = record_path
        self.record = record


def _fake_ledger_recorder(record_path: Path):
    def record(**kwargs):
        return FakeLedgerResult(record_path, dict(kwargs))

    return record


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


def _git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _default_manifest_paths(branch_slug: str) -> tuple[str, ...]:
    return (
        f".ce/changelog/{branch_slug}.md",
        f".ce/pr-manifests/{branch_slug}.md",
        "validators/creator_engine_validator/conveyor.py",
    )


def _default_diff_name_status(branch_slug: str) -> str:
    return "".join(f"A\t{path}\n" for path in _default_manifest_paths(branch_slug))


def _write_carrier_manifest(repo_path: Path, *, branch_slug: str, paths: Sequence[str] | None = None) -> None:
    manifest_paths = tuple(paths or _default_manifest_paths(branch_slug))
    normalized = "\n".join(sorted(set(manifest_paths))) + "\n"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    path = repo_path / ".ce" / "pr-manifests" / f"{branch_slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"PR_PATHS_COUNT={len(set(manifest_paths))}",
                f"PR_PATHS_SHA256={digest}",
                "",
                "```text",
                *sorted(set(manifest_paths)),
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _init_clean_git_worktree(path: Path) -> str:
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "ce@example.invalid")
    _git(path, "config", "user.name", "CE Test")
    _git(path, "commit", "--allow-empty", "-q", "-m", "empty tree")
    return _git(path, "rev-parse", "HEAD^{tree}")


def _init_feature_git_worktree(path: Path) -> str:
    _git(path, "init", "-q", "--initial-branch=main")
    _git(path, "config", "user.email", "ce@example.invalid")
    _git(path, "config", "user.name", "CE Test")
    (path / "README.md").write_text("base\n", encoding="utf-8")
    _git(path, "add", "README.md")
    _git(path, "commit", "-q", "-m", "base")
    _git(path, "switch", "-q", "-c", "Feature/One")
    (path / "validators" / "creator_engine_validator").mkdir(parents=True)
    (path / "validators" / "creator_engine_validator" / "conveyor.py").write_text(
        "# payload\n",
        encoding="utf-8",
    )
    _git(path, "add", "validators/creator_engine_validator/conveyor.py")
    _git(path, "commit", "-q", "-m", "payload")
    return _git(path, "rev-parse", "HEAD^{tree}")


def _init_landing_repo(path: Path, *, remote_path: Path) -> None:
    _git(path, "init", "-q", "--initial-branch=main")
    _git(path, "config", "user.email", "ce@example.invalid")
    _git(path, "config", "user.name", "CE Test")
    _git(path, "remote", "add", "origin", str(remote_path))
    _git(path, "fetch", "origin", "main")
    _git(path, "switch", "-q", "-c", "main", "origin/main")


def _write_bundle_from_branch(source: Path, bundle_path: Path, branch: str) -> None:
    if bundle_path.is_dir():
        shutil.rmtree(bundle_path)
    elif bundle_path.exists():
        bundle_path.unlink()
    _git(source, "bundle", "create", str(bundle_path), branch)


def _write_validation_policy(tmp_path: Path) -> Path:
    path = tmp_path / "governance" / "policies" / "worker-container" / "podman-verification-v1.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        "\n".join(
            [
                "kind: worker-container-policy-record",
                "record_type: worker_container_policy",
                "schema_version: '1'",
                "policy_id: podman-verification-v1",
                f"policy_sha: {'a' * 64}",
                "role: verification",
                "runtime_engine: podman-rootless",
                "image_ref:",
                "  name: ghcr.io/example/verification:latest",
                f"  sha: sha256:{'b' * 64}",
                "mount_manifest:",
                "  - path: /worktrees/example",
                "    mode: ro",
                "egress_allowlist: []",
                "secret_allowlist: []",
                "grant_extensible: false",
                "grant_authority: source",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


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
    prepare = FakePrepare(record_validation=True)
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
        validation_sandbox_runner=FakeValidationSandboxRunner(),
    ).run_once()

    assert result.results[0].status == "pr-opened"
    assert prepare.calls[0].carrier_date == "2026-07-01"
    assert prepare.calls[0].worktree_path == item.worktree_path
    assert prepare.calls[0].allow_dirty_validation is False
    assert prepare.calls[0].commit_carriers_before_validation is True
    assert land.calls == [(item.bundle_path, "feature-one", "origin/main", item.repo_path)]
    assert git.calls == [
        (("rev-parse", "HEAD^{tree}"), item.worktree_path),
        (("rev-parse", "feature-one^{tree}"), item.repo_path),
        (("rev-parse", "feature-one^{commit}"), item.repo_path),
        (("rev-parse", "feature-one^{tree}"), item.repo_path),
        (("rev-list", "--left-right", "--count", "origin/main...feature-one"), item.repo_path),
        (("diff", "--name-status", "--find-renames", "origin/main..feature-one"), item.repo_path),
        (
            ("config", "--local", "--get-regexp", _PUBLISH_TRANSPORT_CONFIG_PATTERN),
            item.repo_path,
        ),
        (("push", "--", "origin", "feature-one:feature-one"), item.repo_path),
    ]
    assert all(
        env
        == {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "PATH": "/usr/bin:/bin",
        }
        for env in git.envs
    )
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
    assert [record.action for record in ledger] == ["validate", "push", "pr-open"]
    assert [record.sha for record in ledger] == [HEAD_SHA, HEAD_SHA, HEAD_SHA]
    assert [record.timestamp for record in ledger] == [
        "2026-07-01T00:00:02Z",
        "2026-07-01T00:00:03Z",
        "2026-07-01T00:00:04Z",
    ]
    assert any(
        "conveyor allocation audit" in message
        and '"allocation_id"' in message
        and '"action": "conveyor_allocation_audit"' in message
        and '"phase": "allocation"' in message
        and '"item_key": "feature-one"' in message
        and '"root_kind"' in message
        and '"mode_check"' in message
        and '"cleanup": {"cleaned": true, "status": "success"}' in message
        and '"nonce"' not in message
        and '"signature"' not in message
        for message in logs
    )
    assert any(
        "conveyor validation audit" in message
        and '"action": "conveyor_validation_phase_audit"' in message
        and '"tree_sha": "' in message
        and '"nonce"' not in message
        and '"signature"' not in message
        for message in logs
    )
    assert any(
        "conveyor publish audit" in message
        and '"action": "conveyor_publish_phase_audit"' in message
        and '"status": "success"' in message
        for message in logs
    )


def test_armed_path_without_validation_record_fails_before_push_or_pr():
    prepare = FakePrepare()
    land = FakeLand()
    git = FakeGit()
    gh = FakeGh()
    ledger: list[ConveyorDaemonLedgerRecord] = []
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
        prepare_runner=prepare,
        land_runner=land,
    ).run_once()

    assert result.results[0].status == "failed"
    assert result.results[0].reasons == ("refusing to land unverified tree: no successful validation record found",)
    assert result.results[0].landing_result is not None
    assert land.calls == [(item.bundle_path, "feature-one", "origin/main", item.repo_path)]
    assert git.calls == []
    assert gh.calls == []
    assert ledger == []


def test_publish_time_tree_drift_is_refused_before_push_or_pr():
    item = _item()
    drift_tree = "f" * 40
    git = FakeGit(landed_tree_shas=[HEAD_SHA, drift_tree])
    gh = FakeGh()
    logs: list[str] = []

    result = ConveyorDaemon(
        discovery_runner=lambda: [item],
        armed=True,
        **ARMED_ROOTS,
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=lambda record: None,
        log_runner=logs.append,
        prepare_runner=FakePrepare(record_validation=True),
        land_runner=FakeLand(),
        validation_sandbox_runner=FakeValidationSandboxRunner(),
    ).run_once()

    assert result.results[0].status == "failed"
    assert result.results[0].reasons == (
        "landed tip tree does not match validation record tree: "
        f"landed={drift_tree} validation_record={HEAD_SHA}",
    )
    assert ("push", "--", "origin", "feature-one:feature-one") not in [call for call, _cwd in git.calls]
    assert gh.calls == []
    assert any(
        "conveyor publish audit" in message
        and '"status": "failed"' in message
        and "head_tree_identity" in message
        for message in logs
    )


def test_publish_time_commit_drift_with_same_tree_is_refused_before_push_or_pr():
    item = _item()
    drift_commit = "c" * 40
    git = FakeGit(landed_commit_sha=drift_commit)
    gh = FakeGh()
    logs: list[str] = []

    result = ConveyorDaemon(
        discovery_runner=lambda: [item],
        armed=True,
        **ARMED_ROOTS,
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=lambda record: None,
        log_runner=logs.append,
        prepare_runner=FakePrepare(record_validation=True),
        land_runner=FakeLand(),
        validation_sandbox_runner=FakeValidationSandboxRunner(),
    ).run_once()

    assert result.results[0].status == "failed"
    assert result.results[0].reasons == (
        "landed head commit does not match landing result head: "
        f"landed={drift_commit} landing_result={HEAD_SHA}",
    )
    assert ("push", "--", "origin", "feature-one:feature-one") not in [call for call, _cwd in git.calls]
    assert gh.calls == []
    assert any("conveyor publish audit" in message and "head_tree_identity" in message for message in logs)


def test_publish_time_behind_base_is_refused_before_push_or_pr():
    item = _item()
    git = FakeGit()
    gh = FakeGh()
    logs: list[str] = []

    result = ConveyorDaemon(
        discovery_runner=lambda: [item],
        armed=True,
        **ARMED_ROOTS,
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=lambda record: None,
        log_runner=logs.append,
        prepare_runner=FakePrepare(record_validation=True),
        land_runner=FakeLand(behind=1),
        validation_sandbox_runner=FakeValidationSandboxRunner(),
    ).run_once()

    assert result.results[0].status == "failed"
    assert result.results[0].reasons == (
        "publish base ancestry re-check failed: landed result is behind base by 1 commits",
    )
    assert ("push", "--", "origin", "feature-one:feature-one") not in [call for call, _cwd in git.calls]
    assert gh.calls == []
    assert any("conveyor publish audit" in message and "base_ancestry" in message for message in logs)


def test_publish_time_manifest_mismatch_is_refused_before_push_or_pr():
    item = _item()
    git = FakeGit(diff_stdout=_default_diff_name_status("feature-one") + "A\tdocs/extra.md\n")
    gh = FakeGh()
    logs: list[str] = []

    result = ConveyorDaemon(
        discovery_runner=lambda: [item],
        armed=True,
        **ARMED_ROOTS,
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=lambda record: None,
        log_runner=logs.append,
        prepare_runner=FakePrepare(record_validation=True),
        land_runner=FakeLand(),
        validation_sandbox_runner=FakeValidationSandboxRunner(),
    ).run_once()

    assert result.results[0].status == "failed"
    assert result.results[0].reasons == (
        "publish manifest fidelity re-check failed: diff paths do not match carrier manifest "
        "extra_diff=['docs/extra.md'] missing_diff=[]",
    )
    assert ("push", "--", "origin", "feature-one:feature-one") not in [call for call, _cwd in git.calls]
    assert gh.calls == []
    assert any("conveyor publish audit" in message and "manifest_fidelity" in message for message in logs)


def test_publish_time_malformed_manifest_diff_is_refused_before_push_or_pr():
    item = _item()
    git = FakeGit(diff_stdout=_default_diff_name_status("feature-one") + "this is not name-status\n")
    gh = FakeGh()
    logs: list[str] = []

    result = ConveyorDaemon(
        discovery_runner=lambda: [item],
        armed=True,
        **ARMED_ROOTS,
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=lambda record: None,
        log_runner=logs.append,
        prepare_runner=FakePrepare(record_validation=True),
        land_runner=FakeLand(),
        validation_sandbox_runner=FakeValidationSandboxRunner(),
    ).run_once()

    assert result.results[0].status == "failed"
    assert result.results[0].reasons == (
        "publish manifest fidelity re-check failed: malformed name-status output: "
        "line 4 expected status and path",
    )
    assert ("push", "--", "origin", "feature-one:feature-one") not in [call for call, _cwd in git.calls]
    assert gh.calls == []
    assert any("conveyor publish audit" in message and "manifest_fidelity" in message for message in logs)


def test_publish_time_local_transport_config_mutation_is_refused_before_push_or_pr():
    item = _item()
    git = FakeGit(config_returncode=0, config_stdout="core.hookspath .githooks\nurl.ext::foo.insteadof ssh://git@\n")
    gh = FakeGh()
    logs: list[str] = []

    result = ConveyorDaemon(
        discovery_runner=lambda: [item],
        armed=True,
        **ARMED_ROOTS,
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=lambda record: None,
        log_runner=logs.append,
        prepare_runner=FakePrepare(record_validation=True),
        land_runner=FakeLand(),
        validation_sandbox_runner=FakeValidationSandboxRunner(),
    ).run_once()

    assert result.results[0].status == "failed"
    assert result.results[0].reasons == (
        "publish transport config guard failed: forbidden local git config keys present: "
        "core.hookspath .githooks, url.ext::foo.insteadof ssh://git@",
    )
    assert ("push", "--", "origin", "feature-one:feature-one") not in [call for call, _cwd in git.calls]
    assert gh.calls == []
    assert any("conveyor publish audit" in message and "transport_config" in message for message in logs)


def test_validation_audit_summarizes_side_effect_record_without_nonce_or_signature():
    item = _item()
    logs: list[str] = []
    side_effect_record = {
        "effect_kind": "validation_sandbox_run",
        "subject_git_sha": HEAD_SHA,
        "nonce": "nonce-secret-value",
        "signature": "signature-secret-value",
        "unexpected_payload": {"nested": "not for audit logs"},
    }

    result = ConveyorDaemon(
        discovery_runner=lambda: [item],
        armed=True,
        **ARMED_ROOTS,
        git_runner=FakeGit(),
        validate_runner=FakeValidate(),
        gh_runner=FakeGh(),
        now=FakeClock(),
        ledger_writer=lambda record: None,
        log_runner=logs.append,
        prepare_runner=FakePrepare(record_validation=True),
        land_runner=FakeLand(),
        validation_sandbox_runner=FakeValidationSandboxRunner(side_effect_record=side_effect_record),
    ).run_once()

    assert result.results[0].status == "pr-opened"
    validation_audits = [message for message in logs if "conveyor validation audit" in message]
    assert len(validation_audits) == 1
    audit = validation_audits[0]
    assert '"effect_kind": "validation_sandbox_run"' in audit
    assert f'"subject_git_sha": "{HEAD_SHA}"' in audit
    assert "nonce" not in audit
    assert "signature" not in audit
    assert "unexpected_payload" not in audit
    assert "nonce-secret-value" not in audit
    assert "signature-secret-value" not in audit


def test_armed_validation_runs_through_sandbox_and_records_receipt(tmp_path: Path):
    item = _item()
    assert item.worktree_path is not None
    tree_sha = _init_clean_git_worktree(item.worktree_path)
    podman = FakePodmanRunner()
    ledger: list[ConveyorDaemonLedgerRecord] = []
    side_effect_records: list[dict] = []

    def ledger_recorder(**kwargs):
        side_effect_records.append(dict(kwargs))
        return FakeLedgerResult(tmp_path / "side-effect.json", dict(kwargs))

    armed_roots = {
        **ARMED_ROOTS,
        "validation_ledger_binding": ConveyorValidationLedgerBinding(
            controller_id="hermes-primary",
            lane_id="conveyor-slice8c",
            claim_ref="claims/hermes-primary/conveyor-slice8c.yaml",
            repo_root=tmp_path,
            side_effect_ledger_root=tmp_path / "side-effect-ledger",
            active_work_ledger_root=tmp_path / "active-work-ledger",
        ),
    }

    def prepare_runner(
        spec: ConveyorHarvestSpec,
        *,
        git_runner,
        validate_runner,
    ) -> ConveyorHarvestResult:
        result = validate_runner(
            ("ce", "validate-pr", "--repo-root", str(spec.worktree_path)),
            spec.worktree_path,
            {"PATH": "/usr/bin:/bin", "PYTHONPATH": str(spec.worktree_path / "validators")},
        )
        return _harvest_result(
            spec,
            ready=result.returncode == 0,
            reasons=() if result.returncode == 0 else (result.stderr,),
        )

    result = ConveyorDaemon(
        discovery_runner=lambda: [item],
        armed=True,
        **armed_roots,
        git_runner=FakeGit(landed_tree_sha=tree_sha),
        validate_runner=FakeValidate(),
        gh_runner=FakeGh(),
        now=FakeClock(),
        ledger_writer=ledger.append,
        prepare_runner=prepare_runner,
        land_runner=FakeLand(),
        validation_sandbox_policy_path=_write_validation_policy(tmp_path),
        validation_sandbox_command_runner=podman,
        validation_ledger_recorder=ledger_recorder,
    ).run_once()

    assert result.results[0].status == "pr-opened"
    assert [record.action for record in ledger] == ["validate", "push", "pr-open"]
    validate_record = ledger[0]
    assert validate_record.sha == tree_sha
    receipt = validate_record.details["receipt"]
    assert receipt["tree_sha"] == tree_sha
    assert receipt["secret_allowlist_applied"] == []
    assert validate_record.details["side_effect_record"]["effect_kind"] == "validation_sandbox_run"
    assert validate_record.details["side_effect_record"]["subject_git_sha"] == tree_sha
    assert side_effect_records[0]["effect_kind"] == "validation_sandbox_run"
    assert side_effect_records[0]["subject_git_sha"] == tree_sha
    assert podman.calls
    podman_argv = podman.calls[0][0]
    assert "--secret" not in podman_argv
    assert "conveyor-validation-receipt-secret" not in " ".join(podman_argv)


def test_armed_real_prepare_commits_carriers_before_container_validation(tmp_path: Path):
    item = _item()
    assert item.worktree_path is not None
    pre_carrier_tree = _init_feature_git_worktree(item.worktree_path)
    git = RealLocalGit(fake_landed_tree_from_validation=True)
    podman = FakePodmanRunner()
    ledger: list[ConveyorDaemonLedgerRecord] = []

    result = ConveyorDaemon(
        discovery_runner=lambda: [item],
        armed=True,
        **ARMED_ROOTS,
        git_runner=git,
        gh_runner=FakeGh(),
        now=FakeClock(),
        ledger_writer=ledger.append,
        land_runner=FakeLand(),
        base="main",
        validation_sandbox_policy_path=_write_validation_policy(tmp_path),
        validation_sandbox_command_runner=podman,
        validation_ledger_recorder=_fake_ledger_recorder(tmp_path / "side-effect.json"),
    ).run_once()

    assert result.results[0].status == "pr-opened"
    committed_tree = git.rev_parse_trees[-1]
    assert committed_tree != pre_carrier_tree
    assert (
        ("add", "--", ".ce/changelog/feature-one.md", ".ce/pr-manifests/feature-one.md"),
        item.worktree_path,
    ) in git.calls
    assert (
        (
            "commit",
            "-m",
            "Add conveyor harvest carriers for feature-one",
            "--",
            ".ce/changelog/feature-one.md",
            ".ce/pr-manifests/feature-one.md",
        ),
        item.worktree_path,
    ) in git.calls
    validate_record = ledger[0]
    assert validate_record.action == "validate"
    assert validate_record.sha == committed_tree
    assert validate_record.details["receipt"]["tree_sha"] == committed_tree
    assert podman.calls
    podman_argv = podman.calls[0][0]
    assert "--allow-dirty" not in podman_argv
    assert "validation sandbox mounted tree must be clean" not in result.results[0].reasons


def test_armed_real_land_fails_before_push_when_landed_tree_differs_from_validation_record(tmp_path: Path):
    item = _item()
    assert item.worktree_path is not None
    assert item.repo_path is not None
    assert item.bundle_path is not None
    _init_feature_git_worktree(item.worktree_path)
    _git(item.worktree_path, "branch", "-m", "feature-one")
    pre_carrier_tree = _git(item.worktree_path, "rev-parse", "HEAD^{tree}")
    _write_bundle_from_branch(item.worktree_path, item.bundle_path, "feature-one")
    _init_landing_repo(item.repo_path, remote_path=item.worktree_path)
    git = RealLocalGit()
    podman = FakePodmanRunner()
    gh = FakeGh()
    ledger: list[ConveyorDaemonLedgerRecord] = []

    result = ConveyorDaemon(
        discovery_runner=lambda: [item],
        armed=True,
        **ARMED_ROOTS,
        git_runner=git,
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=ledger.append,
        base="main",
        validation_sandbox_policy_path=_write_validation_policy(tmp_path),
        validation_sandbox_command_runner=podman,
        validation_ledger_recorder=_fake_ledger_recorder(tmp_path / "side-effect.json"),
    ).run_once()

    assert result.results[0].status == "failed"
    validate_record = ledger[0]
    validation_tree = validate_record.details["receipt"]["tree_sha"]
    assert validation_tree != pre_carrier_tree
    assert result.results[0].landing_result is not None
    assert result.results[0].landing_result.ready is True
    assert result.results[0].reasons == (
        "landed tip tree does not match validation record tree: "
        f"landed={pre_carrier_tree} validation_record={validation_tree}",
    )
    assert ("push", "--", "origin", "feature-one:feature-one") not in [call for call, _cwd in git.calls]
    assert gh.calls == []


def test_armed_start_without_receipt_issuer_is_refused():
    with pytest.raises(ValueError, match="receipt_issuer"):
        ConveyorDaemon(
            discovery_runner=lambda: [],
            armed=True,
            path_allocator=TEST_ALLOCATOR,
            daemon_lease=FakeLease(),
            git_runner=FakeGit(),
            validate_runner=FakeValidate(),
            gh_runner=FakeGh(),
            now=FakeClock(),
            ledger_writer=lambda record: None,
            validation_ledger_binding=_validation_ledger_binding(),
        )


def test_armed_start_without_validation_ledger_binding_is_refused():
    with pytest.raises(ValueError, match="validation_ledger_binding"):
        ConveyorDaemon(
            discovery_runner=lambda: [],
            armed=True,
            path_allocator=TEST_ALLOCATOR,
            daemon_lease=FakeLease(),
            receipt_issuer=_receipt_issuer(),
            git_runner=FakeGit(),
            validate_runner=FakeValidate(),
            gh_runner=FakeGh(),
            now=FakeClock(),
            ledger_writer=lambda record: None,
        )


def test_disarmed_path_does_not_require_or_call_validation_sandbox_runner():
    called = False

    def sandbox_runner(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("disarmed planning must not call validation sandbox")

    result = ConveyorDaemon(
        discovery_runner=lambda: [_item()],
        validation_sandbox_runner=sandbox_runner,
    ).run_once()

    assert result.results[0].status == "planned"
    assert called is False


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
            validation_ledger_binding=_validation_ledger_binding(),
        )


def test_armed_run_heartbeats_lease():
    lease = FakeLease()
    daemon = ConveyorDaemon(
        discovery_runner=lambda: [],
        armed=True,
        path_allocator=TEST_ALLOCATOR,
        daemon_lease=lease,
        receipt_issuer=_receipt_issuer(),
        git_runner=FakeGit(),
        validate_runner=FakeValidate(),
        gh_runner=FakeGh(),
        now=FakeClock(),
        ledger_writer=lambda record: None,
        validation_ledger_binding=_validation_ledger_binding(),
    )

    daemon.run_once()

    assert lease.heartbeat_calls == 1


def test_armed_run_heartbeats_before_each_item_boundary():
    lease = FakeLease()
    first_item = _item("Feature/One")
    second_item = _item("Feature/Two")
    prepare_seen_heartbeats: list[int] = []

    def prepare_runner(
        spec: ConveyorHarvestSpec,
        *,
        git_runner,
        validate_runner,
    ) -> ConveyorHarvestResult:
        prepare_seen_heartbeats.append(lease.heartbeat_calls)
        validation = _run_fake_validation(spec, validate_runner)
        if validation.returncode != 0:
            return _harvest_result(spec, ready=False, reasons=(validation.stderr,))
        return _harvest_result(spec, ready=True, reasons=())

    result = ConveyorDaemon(
        discovery_runner=lambda: [first_item, second_item],
        armed=True,
        path_allocator=TEST_ALLOCATOR,
        daemon_lease=lease,
        receipt_issuer=_receipt_issuer(),
        git_runner=FakeGit(),
        validate_runner=FakeValidate(),
        gh_runner=FakeGh(),
        now=FakeClock(),
        ledger_writer=lambda record: None,
        prepare_runner=prepare_runner,
        land_runner=FakeLand(),
        validation_sandbox_runner=FakeValidationSandboxRunner(),
        validation_ledger_binding=_validation_ledger_binding(),
    ).run_once()

    assert [item.status for item in result.results] == ["pr-opened", "pr-opened"]
    assert prepare_seen_heartbeats == [2, 3]
    assert lease.heartbeat_calls == 3


def test_armed_run_heartbeat_failure_before_item_stops_without_processing_item():
    lease = FakeLease(fail_on_call=3)
    prepare = FakePrepare(record_validation=True)
    git = FakeGit()
    gh = FakeGh()
    logs: list[str] = []
    first_item = _item("Feature/One")
    second_item = _item("Feature/Two")

    result = ConveyorDaemon(
        discovery_runner=lambda: [first_item, second_item],
        armed=True,
        path_allocator=TEST_ALLOCATOR,
        daemon_lease=lease,
        receipt_issuer=_receipt_issuer(),
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=lambda record: None,
        log_runner=logs.append,
        prepare_runner=prepare,
        land_runner=FakeLand(),
        validation_sandbox_runner=FakeValidationSandboxRunner(),
        validation_ledger_binding=_validation_ledger_binding(),
    ).run_once()

    assert [item.status for item in result.results] == ["pr-opened", "failed"]
    assert result.results[1].branch == "Feature/Two"
    assert result.results[1].reasons == ("daemon lease heartbeat failed: lost lease heartbeat",)
    assert [spec.branch for spec in prepare.calls] == ["Feature/One"]
    assert (("push", "--", "origin", "feature-one:feature-one"), first_item.repo_path) in git.calls
    assert len(gh.calls) == 1
    assert lease.heartbeat_calls == 3
    assert any("daemon lease heartbeat failed: lost lease heartbeat" in message for message in logs)


def test_per_item_failure_isolated_and_loop_continues():
    prepare = FakePrepare(failing_branches={"Feature/One"}, record_validation=True)
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
        validation_sandbox_runner=FakeValidationSandboxRunner(),
    ).run_once()

    assert [item.status for item in result.results] == ["failed", "pr-opened"]
    assert result.results[0].reasons == ("prepare failed",)
    assert (("push", "--", "origin", "feature-two:feature-two"), good_item.repo_path) in git.calls
    assert len(gh.calls) == 1
    assert [record.branch for record in ledger] == ["Feature/Two", "feature-two", "feature-two"]


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
        prepare_runner=FakePrepare(record_validation=True),
        land_runner=FakeLand(),
        validation_sandbox_runner=FakeValidationSandboxRunner(),
    ).run_once()

    assert result.results[0].status == "failed"
    assert result.results[0].reasons == ("push failed: push denied",)
    assert [(record.action, record.status, record.returncode) for record in ledger] == [
        ("validate", "success", 0),
        ("push", "failed", 1),
    ]
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
    prepare = FakePrepare(record_validation=True)
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
        validation_sandbox_runner=FakeValidationSandboxRunner(),
    ).run_once()

    assert result.discovery_error is None
    assert result.discovered_count == 1
    assert [item.status for item in result.results] == ["pr-opened"]
    assert [spec.branch for spec in prepare.calls] == ["Feature/One"]
    assert land.calls == [(valid_item.bundle_path, "feature-one", "origin/main", valid_item.repo_path)]
    assert (("push", "--", "origin", "feature-one:feature-one"), valid_item.repo_path) in git.calls
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
    prepare = FakePrepare(record_validation=True)
    git = FakeGit()
    gh = FakeGh()
    allocator = CountingAllocator()

    result = ConveyorDaemon(
        discovery_runner=lambda: [_data_only_payload()],
        armed=True,
        path_allocator=allocator,
        daemon_lease=FakeLease(),
        receipt_issuer=_receipt_issuer(),
        git_runner=git,
        validate_runner=FakeValidate(),
        gh_runner=gh,
        now=FakeClock(),
        ledger_writer=lambda record: None,
        prepare_runner=prepare,
        land_runner=FakeLand(),
        validation_sandbox_runner=FakeValidationSandboxRunner(),
        validation_ledger_binding=_validation_ledger_binding(),
    ).run_once()

    assert result.results[0].status == "pr-opened"
    assert allocator.allocate_calls == [{"repo": "feature-one", "branch_name": "feature-one"}]
    assert len(allocator.allocations) == 1
    allocation = allocator.allocations[0]
    assert prepare.calls[0].worktree_path == allocation.worktree_path
    assert (("push", "--", "origin", "feature-one:feature-one"), allocation.repo_path) in git.calls
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
    prepare = FakePrepare(record_validation=True)
    land = FakeLand()
    git_calls: list[tuple[str, ...]] = []

    def git_runner(args: Sequence[str], cwd: Path, env: Mapping[str, str]) -> ConveyorCommandResult:
        git_calls.append(tuple(args))
        if len(args) == 2 and args[0] == "rev-parse" and str(args[1]).endswith(("^{tree}", "^{commit}")):
            return ConveyorCommandResult(0, f"{HEAD_SHA}\n", "")
        if tuple(args) == ("rev-list", "--left-right", "--count", "origin/main...feature-one"):
            return ConveyorCommandResult(0, "0\t1\n", "")
        if tuple(args) == ("diff", "--name-status", "--find-renames", "origin/main..feature-one"):
            return ConveyorCommandResult(0, _default_diff_name_status("feature-one"), "")
        if tuple(args) == (
            "config",
            "--local",
            "--get-regexp",
            _PUBLISH_TRANSPORT_CONFIG_PATTERN,
        ):
            return ConveyorCommandResult(1, "", "")
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
        validation_sandbox_runner=FakeValidationSandboxRunner(),
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
        prepare_runner=FakePrepare(record_validation=True),
        land_runner=FakeLand(),
        validation_sandbox_runner=FakeValidationSandboxRunner(),
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
        prepare_runner=FakePrepare(record_validation=True),
        land_runner=FakeLand(),
        validation_sandbox_runner=FakeValidationSandboxRunner(),
    )

    first, second = daemon.run_loop(iterations=2)

    assert first.results[0].status == "pr-opened"
    assert second.results[0].status == "skipped"
    assert [call for call, _cwd in git.calls].count(("push", "--", "origin", "feature-one:feature-one")) == 1
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
        prepare = FakePrepare(record_validation=True)
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
            validation_sandbox_runner=FakeValidationSandboxRunner(),
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

        assert (("push", "--", "origin", "feature-one:feature-one"), real_repo) in git.calls
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
            validation_ledger_binding=_validation_ledger_binding(),
        )
