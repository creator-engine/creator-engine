from __future__ import annotations

import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from creator_engine_validator.conveyor import (
    ConveyorCommandResult,
    ConveyorGitPhase,
    ConveyorHarvestSpec,
    _default_git_runner,
    _default_validate_runner,
    git_env_for_phase,
    land_bundle,
    prepare_harvest,
)
from creator_engine_validator.harvest_evidence import parse_harvest_evidence


NON_TEST_EVIDENCE = {
    "test_bearing": False,
    "justification": "The conveyor unit exercises only data-only admission helpers; no implementation test was added.",
}
VALID_TEST_EVIDENCE = {
    "test_bearing": True,
    "node_ids": ["validators/tests/unit/test_conveyor.py::test_prepare_harvest_refuses_missing_test_evidence_before_carriers"],
    "base_or_prior_head": "0123456789abcdef0123456789abcdef01234567",
    "red_command": "python -m pytest exact-node",
    "red_output": "1 failed",
    "green_command": "python -m pytest exact-node",
    "green_output": "1 passed",
}


class FakeGit:
    def __init__(self, current_branch: str = "Feature/Test", diff: str = "validators/creator_engine_validator/conveyor.py\n"):
        self.current_branch = current_branch
        self.diff = diff
        self.calls: list[tuple[str, ...]] = []
        self.envs: list[Mapping[str, str]] = []

    def __call__(self, args: Sequence[str], cwd: Path, env: Mapping[str, str]) -> ConveyorCommandResult:
        self.calls.append(tuple(args))
        self.envs.append(dict(env))
        if tuple(args) == ("branch", "--show-current"):
            return ConveyorCommandResult(0, f"{self.current_branch}\n", "")
        if tuple(args) == ("branch", "-m", "feature-test"):
            self.current_branch = "feature-test"
            return ConveyorCommandResult(0, "", "")
        if tuple(args) == ("fetch", "origin", "main"):
            return ConveyorCommandResult(0, "", "")
        if tuple(args) == ("rebase", "origin/main"):
            return ConveyorCommandResult(0, "", "")
        if tuple(args) == ("merge-base", "--is-ancestor", "origin/main", "HEAD"):
            return ConveyorCommandResult(0, "", "")
        if tuple(args) == ("diff", "--name-only", "--find-renames", "origin/main..HEAD"):
            return ConveyorCommandResult(0, self.diff, "")
        return ConveyorCommandResult(1, "", f"unexpected git call: {args}")


class FakeValidate:
    def __init__(self, returncode: int = 0):
        self.returncode = returncode
        self.calls: list[tuple[tuple[str, ...], Path, Mapping[str, str] | None]] = []

    def __call__(
        self,
        args: Sequence[str],
        cwd: Path,
        env: Mapping[str, str] | None,
    ) -> ConveyorCommandResult:
        self.calls.append((tuple(args), cwd, env))
        (cwd / "validators" / "build").mkdir(parents=True, exist_ok=True)
        return ConveyorCommandResult(self.returncode, "ok\n", "" if self.returncode == 0 else "failed\n")


class FakeLandingGit:
    def __init__(self, rebase_returncode: int = 0):
        self.rebase_returncode = rebase_returncode
        self.calls: list[tuple[str, ...]] = []
        self.envs: list[Mapping[str, str]] = []

    def __call__(self, args: Sequence[str], cwd: Path, env: Mapping[str, str]) -> ConveyorCommandResult:
        self.calls.append(tuple(args))
        self.envs.append(dict(env))
        if tuple(args) == ("bundle", "verify", "/tmp/ce-test-bundle.bundle"):
            return ConveyorCommandResult(0, "The bundle is okay\n", "")
        if tuple(args) == (
            "fetch",
            "/tmp/ce-test-bundle.bundle",
            "ce-test-bundle-landing:ce-test-bundle-landing",
        ):
            return ConveyorCommandResult(0, "", "")
        if tuple(args) == ("fetch", "origin", "main"):
            return ConveyorCommandResult(0, "", "")
        if tuple(args) == ("switch", "ce-test-bundle-landing"):
            return ConveyorCommandResult(0, "", "")
        if tuple(args) == ("rebase", "origin/main"):
            if self.rebase_returncode:
                return ConveyorCommandResult(self.rebase_returncode, "", "base conflict\n")
            return ConveyorCommandResult(0, "", "")
        if tuple(args) == ("rev-parse", "HEAD"):
            return ConveyorCommandResult(0, "0123456789abcdef0123456789abcdef01234567\n", "")
        if tuple(args) == ("rev-list", "--left-right", "--count", "origin/main...HEAD"):
            return ConveyorCommandResult(0, "0\t2\n", "")
        return ConveyorCommandResult(1, "", f"unexpected git call: {args}")


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "validators" / "build").mkdir(parents=True)
    (root / "validators" / "creator_engine_validator").mkdir(parents=True)
    (root / "validators" / "old.egg-info").mkdir()
    return root


def _run_git(cwd: Path, args: Sequence[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


def _init_repo(path: Path) -> None:
    path.mkdir()
    _run_git(path, ["init", "--initial-branch=main"])
    _run_git(path, ["config", "user.name", "CE Test"])
    _run_git(path, ["config", "user.email", "ce-test@example.invalid"])


def test_prepare_harvest_renames_branch_cleans_artifacts_writes_carriers_and_validates(tmp_path: Path):
    root = _repo(tmp_path)
    git = FakeGit()
    validate = FakeValidate()

    result = prepare_harvest(
        ConveyorHarvestSpec(
            worktree_path=root,
            branch="Feature/Test",
            issue="ce-ops#1",
            title="Conveyor harvest",
            body="- Added conveyor helper.",
            carrier_date="2026-06-30",
            harvest_evidence=NON_TEST_EVIDENCE,
        ),
        git_runner=git,
        validate_runner=validate,
    )

    assert result.ready is True
    assert result.reasons == ()
    assert result.branch_slug == "feature-test"
    assert result.removed_artifacts == ("validators/build", "validators/old.egg-info")
    assert git.calls == [
        ("branch", "--show-current"),
        ("branch", "-m", "feature-test"),
        ("fetch", "origin", "main"),
        ("rebase", "origin/main"),
        ("diff", "--name-only", "--find-renames", "origin/main..HEAD"),
    ]
    assert all(env["GIT_CONFIG_NOSYSTEM"] == "1" for env in git.envs)
    assert all(env["GIT_TERMINAL_PROMPT"] == "0" for env in git.envs)
    assert all(env["PATH"] == "/usr/bin:/bin" for env in git.envs)
    assert all("GH_TOKEN" not in env and "SSH_AUTH_SOCK" not in env for env in git.envs)
    assert validate.calls == [
        (
            (
                sys.executable,
                "-m",
                "creator_engine_validator.ce_cli",
                "validate-pr",
                "--repo-root",
                str(root),
                "--base",
                "origin/main",
                "--declared-work-class",
                "story",
                "--head-ref",
                "feature-test",
                "--allow-dirty",
            ),
            root,
            {"PYTHONPATH": str(root / "validators"), "TMPDIR": "/var/tmp", "PATH": "/usr/bin:/bin"},
        )
    ]
    assert not (root / "validators" / "build").exists()
    assert result.changelog_path == root / ".ce" / "changelog" / "feature-test.md"
    assert result.manifest_path == root / ".ce" / "pr-manifests" / "feature-test.md"
    manifest = result.manifest_path.read_text(encoding="utf-8")
    assert "- **Declared work class:** story\n" in manifest
    assert "validators/creator_engine_validator/conveyor.py" in manifest


def test_prepare_harvest_refuses_unexpected_current_branch_before_mutation(tmp_path: Path):
    root = _repo(tmp_path)
    git = FakeGit(current_branch="other-branch")
    validate = FakeValidate()

    result = prepare_harvest(
        ConveyorHarvestSpec(worktree_path=root, branch="Feature/Test", harvest_evidence=NON_TEST_EVIDENCE),
        git_runner=git,
        validate_runner=validate,
    )

    assert result.ready is False
    assert result.reasons == ("current branch 'other-branch' is neither requested branch 'Feature/Test' nor slug 'feature-test'",)
    assert git.calls == [("branch", "--show-current")]
    assert validate.calls == []


def test_prepare_harvest_validation_failure_is_not_ready_and_post_cleans(tmp_path: Path):
    root = _repo(tmp_path)
    git = FakeGit(current_branch="feature-test")
    validate = FakeValidate(returncode=2)

    result = prepare_harvest(
        ConveyorHarvestSpec(worktree_path=root, branch="Feature/Test", harvest_evidence=NON_TEST_EVIDENCE),
        git_runner=git,
        validate_runner=validate,
    )

    assert result.ready is False
    assert result.validation_returncode == 2
    assert result.reasons == ("validate-pr failed: failed",)
    assert not (root / "validators" / "build").exists()


def test_prepare_harvest_can_verify_base_without_rebase(tmp_path: Path):
    root = _repo(tmp_path)
    git = FakeGit(current_branch="feature-test")
    validate = FakeValidate()

    result = prepare_harvest(
        ConveyorHarvestSpec(
            worktree_path=root,
            branch="Feature/Test",
            rebase=False,
            refresh_base=False,
            harvest_evidence=NON_TEST_EVIDENCE,
        ),
        git_runner=git,
        validate_runner=validate,
    )

    assert result.ready is True
    assert ("rebase", "origin/main") not in git.calls
    assert ("merge-base", "--is-ancestor", "origin/main", "HEAD") in git.calls


def test_land_bundle_with_fake_git_fetches_rebases_and_reports_ahead_behind(tmp_path: Path):
    git = FakeLandingGit()

    result = land_bundle(
        "/tmp/ce-test-bundle.bundle",
        "ce-test-bundle-landing",
        "origin/main",
        repo_path=tmp_path,
        git_runner=git,
    )

    assert result.ready is True
    assert result.reasons == ()
    assert result.branch == "ce-test-bundle-landing"
    assert result.branch_slug == "ce-test-bundle-landing"
    assert result.base_ref == "origin/main"
    assert result.head_sha == "0123456789abcdef0123456789abcdef01234567"
    assert result.ahead == 2
    assert result.behind == 0
    assert git.calls == [
        ("bundle", "verify", "/tmp/ce-test-bundle.bundle"),
        ("fetch", "/tmp/ce-test-bundle.bundle", "ce-test-bundle-landing:ce-test-bundle-landing"),
        ("fetch", "origin", "main"),
        ("switch", "ce-test-bundle-landing"),
        ("rebase", "origin/main"),
        ("rev-parse", "HEAD"),
        ("rev-list", "--left-right", "--count", "origin/main...HEAD"),
    ]


def test_land_bundle_imports_real_tiny_bundle(tmp_path: Path):
    branch = "ce-test-bundle-landing"
    source = tmp_path / "source"
    _init_repo(source)
    (source / "README.md").write_text("base\n", encoding="utf-8")
    _run_git(source, ["add", "README.md"])
    _run_git(source, ["commit", "-m", "base"])
    _run_git(source, ["switch", "-c", branch])
    (source / "feature.txt").write_text("feature\n", encoding="utf-8")
    _run_git(source, ["add", "feature.txt"])
    _run_git(source, ["commit", "-m", "feature"])
    bundle = tmp_path / "feature.bundle"
    _run_git(source, ["bundle", "create", str(bundle), branch])

    landing = tmp_path / "landing"
    _init_repo(landing)
    _run_git(landing, ["remote", "add", "origin", str(source)])
    _run_git(landing, ["fetch", "origin", "main"])
    _run_git(landing, ["switch", "-c", "main", "origin/main"])

    result = land_bundle(bundle, branch, "origin/main", repo_path=landing)

    assert result.ready is True
    assert result.reasons == ()
    assert result.branch == branch
    assert result.branch_slug == branch
    assert result.head_sha is not None
    assert len(result.head_sha) == 40
    assert result.ahead == 1
    assert result.behind == 0
    assert _run_git(landing, ["branch", "--show-current"]).strip() == branch
    assert (landing / "feature.txt").read_text(encoding="utf-8") == "feature\n"


def test_land_bundle_rejects_malformed_bundle(tmp_path: Path):
    landing = tmp_path / "landing"
    _init_repo(landing)
    malformed = tmp_path / "not-a.bundle"
    malformed.write_text("not a bundle\n", encoding="utf-8")

    result = land_bundle(malformed, "ce-test-bundle-landing", "origin/main", repo_path=landing)

    assert result.ready is False
    assert [reason.code for reason in result.reasons] == ["bundle_verify_failed"]
    assert "bundle" in result.reasons[0].message


def test_land_bundle_wrong_base_rebase_failure_is_not_ready(tmp_path: Path):
    git = FakeLandingGit(rebase_returncode=1)

    result = land_bundle(
        "/tmp/ce-test-bundle.bundle",
        "ce-test-bundle-landing",
        "origin/main",
        repo_path=tmp_path,
        git_runner=git,
    )

    assert result.ready is False
    assert [reason.code for reason in result.reasons] == ["base_rebase_failed"]
    assert "base conflict" in result.reasons[0].detail
    assert ("rev-parse", "HEAD") not in git.calls


def test_default_git_runner_uses_explicit_scrubbed_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    captured: dict[str, Mapping[str, str]] = {}

    monkeypatch.setenv("GH_TOKEN", "ambient-secret")
    monkeypatch.setenv("SSH_AUTH_SOCK", "/tmp/ambient-agent.sock")

    def fake_run(*args, **kwargs):
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(args[0], 0, "ok\n", "")

    monkeypatch.setattr("creator_engine_validator.conveyor.subprocess.run", fake_run)

    result = _default_git_runner(
        ["status", "--short"],
        tmp_path,
        git_env_for_phase(ConveyorGitPhase.LOCAL),
    )

    assert result.returncode == 0
    assert captured["env"] == {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "PATH": "/usr/bin:/bin",
    }


def test_default_validate_runner_uses_only_passed_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    captured: dict[str, Mapping[str, str]] = {}
    allowed_env = {"PYTHONPATH": str(tmp_path / "validators"), "TMPDIR": "/var/tmp", "PATH": "/usr/bin:/bin"}

    monkeypatch.setenv("GH_TOKEN", "ambient-secret")

    def fake_run(*args, **kwargs):
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(args[0], 0, "ok\n", "")

    monkeypatch.setattr("creator_engine_validator.conveyor.subprocess.run", fake_run)

    result = _default_validate_runner([sys.executable, "-m", "validator"], tmp_path, allowed_env)

    assert result.returncode == 0
    assert captured["env"] == allowed_env


def test_default_validate_runner_resolves_current_interpreter_with_scrubbed_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    monkeypatch.setenv("GH_TOKEN", "ambient-secret")

    result = _default_validate_runner(
        [
            sys.executable,
            "-c",
            "import os; print(os.environ.get('GH_TOKEN', '')); print(os.environ['PATH'])",
        ],
        tmp_path,
        {"PYTHONPATH": str(tmp_path / "validators"), "TMPDIR": "/var/tmp", "PATH": "/usr/bin:/bin"},
    )

    assert result.returncode == 0
    assert result.stdout.splitlines() == ["", "/usr/bin:/bin"]


def test_run_validation_preserves_slice6_command_and_env(tmp_path: Path):
    root = _repo(tmp_path)
    validate = FakeValidate()

    result = prepare_harvest(
        ConveyorHarvestSpec(
            worktree_path=root,
            branch="feature-test",
            base="origin/main",
            declared_work_class="story",
            refresh_base=False,
            rebase=False,
            harvest_evidence=NON_TEST_EVIDENCE,
        ),
        git_runner=FakeGit(current_branch="feature-test"),
        validate_runner=validate,
    )

    assert result.ready is True
    assert validate.calls[-1] == (
        (
            sys.executable,
            "-m",
            "creator_engine_validator.ce_cli",
            "validate-pr",
            "--repo-root",
            str(root),
            "--base",
            "origin/main",
            "--declared-work-class",
            "story",
            "--head-ref",
            "feature-test",
            "--allow-dirty",
        ),
        root,
        {"PYTHONPATH": str(root / "validators"), "TMPDIR": "/var/tmp", "PATH": "/usr/bin:/bin"},
    )


@pytest.mark.parametrize(
    ("payload", "reason_code"),
    (
        (VALID_TEST_EVIDENCE, None),
        ({**VALID_TEST_EVIDENCE, "red_command": ""}, "missing_red_command"),
        ({**VALID_TEST_EVIDENCE, "red_output": ""}, "missing_red_output"),
        ({**VALID_TEST_EVIDENCE, "node_ids": []}, "missing_test_node_ids"),
        ({**VALID_TEST_EVIDENCE, "base_or_prior_head": ""}, "missing_base_or_prior_head"),
        ({**VALID_TEST_EVIDENCE, "green_command": ""}, "missing_green_command"),
        ({**VALID_TEST_EVIDENCE, "green_output": ""}, "missing_green_output"),
        (NON_TEST_EVIDENCE, None),
        ({"test_bearing": False}, "missing_non_test_justification"),
        ({"test_bearing": False, "justification": "   "}, "missing_non_test_justification"),
    ),
)
def test_parse_harvest_evidence_returns_named_ready_or_flagged_result(payload, reason_code):
    assessment = parse_harvest_evidence(payload)

    assert assessment.ready is (reason_code is None)
    assert assessment.status == ("ready" if reason_code is None else "flagged")
    assert assessment.reason_code == reason_code


def test_parse_harvest_evidence_requires_an_explicit_non_test_classification():
    assessment = parse_harvest_evidence(None)

    assert assessment.status == "flagged"
    assert assessment.ready is False
    assert assessment.reason_code == "missing_evidence_classification"


def test_prepare_harvest_refuses_missing_test_evidence_before_carrier_generation(tmp_path: Path):
    root = _repo(tmp_path)
    git = FakeGit(current_branch="feature-test")
    validate = FakeValidate()

    result = prepare_harvest(
        ConveyorHarvestSpec(
            worktree_path=root,
            branch="Feature/Test",
            harvest_evidence={**VALID_TEST_EVIDENCE, "red_output": ""},
        ),
        git_runner=git,
        validate_runner=validate,
    )

    assert result.ready is False
    assert result.harvest_evidence is not None
    assert result.harvest_evidence.status == "flagged"
    assert result.harvest_evidence.reason_code == "missing_red_output"
    assert result.reasons == (
        "harvest evidence not ready: missing_red_output: test-bearing evidence must retain captured RED output",
    )
    assert git.calls == []
    assert validate.calls == []
    assert not (root / ".ce" / "pr-manifests").exists()
