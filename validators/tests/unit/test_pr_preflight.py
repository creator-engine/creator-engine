from __future__ import annotations

import io
import sys
from pathlib import Path

from creator_engine_validator import pr_preflight


class FakeRunner:
    def __init__(self, repo_root: Path, *, dirty: str = "", malformed_returncode: int = 1):
        self.repo_root = repo_root
        self.dirty = dirty
        self.malformed_returncode = malformed_returncode
        self.calls: list[tuple[list[str], Path, dict[str, str] | None]] = []

    def __call__(self, argv, cwd, env=None):
        argv = list(argv)
        self.calls.append((argv, cwd, dict(env) if env is not None else None))
        if argv == ["git", "rev-parse", "--show-toplevel"]:
            return pr_preflight.CommandResult(0, str(self.repo_root) + "\n", "")
        if argv == ["git", "status", "--porcelain"]:
            return pr_preflight.CommandResult(0, self.dirty, "")
        if argv == ["git", "branch", "--show-current"]:
            return pr_preflight.CommandResult(0, "dev4/night-lane0\n", "")
        if argv[:2] == ["git", "fetch"]:
            return pr_preflight.CommandResult(0, "", "")
        if argv == ["git", "merge-base", "origin/main", "HEAD"]:
            return pr_preflight.CommandResult(0, "abc1234\n", "")
        if argv[:3] == [sys.executable, "-m", "creator_engine_validator"] and "examples/malformed/" in argv:
            return pr_preflight.CommandResult(self.malformed_returncode, "malformed rejected\n", "")
        return pr_preflight.CommandResult(0, "ok\n", "")

    def argv_calls(self) -> list[list[str]]:
        return [call[0] for call in self.calls]


def _config(tmp_path: Path, **overrides) -> pr_preflight.PreflightConfig:
    values = {
        "repo_root": tmp_path,
        "base": "origin/main",
        "declared_work_class": "feature",
        "head_ref": "dev4-night-lane0-pr-preflight",
        "allow_dirty": False,
    }
    values.update(overrides)
    return pr_preflight.PreflightConfig(**values)


def test_preflight_refuses_dirty_tree_before_gates(tmp_path: Path):
    runner = FakeRunner(tmp_path, dirty=" M validators/creator_engine_validator/pr_preflight.py\n")
    out = io.StringIO()
    err = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=err)

    assert rc == 1
    assert "working tree is dirty" in err.getvalue()
    assert not any(call[:2] == ["git", "fetch"] for call in runner.argv_calls())


def test_preflight_allows_dirty_tree_only_with_explicit_override(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda paths, label, err: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda repo_root: None)
    runner = FakeRunner(tmp_path, dirty=" M docs/contracts/authoring-a-governed-pr.md\n")
    out = io.StringIO()
    err = io.StringIO()

    rc = pr_preflight.run_preflight(
        _config(tmp_path, allow_dirty=True),
        runner=runner,
        out=out,
        err=err,
    )

    assert rc == 0
    assert "WARNING: working tree is dirty" in out.getvalue()
    assert "GREEN: PR preflight passed" in out.getvalue()


def test_preflight_uses_merge_base_for_diff_gates_and_requires_carrier(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda paths, label, err: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda repo_root: None)
    runner = FakeRunner(tmp_path)

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=io.StringIO(), err=io.StringIO())

    assert rc == 0
    calls = runner.argv_calls()
    assert ["git", "fetch", "--no-tags", "--prune", "origin", "+refs/heads/main:refs/remotes/origin/main"] in calls
    assert ["git", "merge-base", "origin/main", "HEAD"] in calls
    assert [
        sys.executable,
        "-m",
        "creator_engine_validator",
        "check-examples",
    ] in calls
    assert [
        sys.executable,
        "-m",
        "creator_engine_validator",
        "verify-work-sizing-floor",
        "--base",
        "abc1234",
        "--declared-work-class",
        "feature",
        ".",
    ] in calls
    assert [
        sys.executable,
        "-m",
        "creator_engine_validator",
        "verify-path-manifest",
        "--base",
        "abc1234",
        "--manifest-dir",
        ".ce/pr-manifests",
        "--head-ref",
        "dev4-night-lane0-pr-preflight",
        "--require-carrier",
    ] in calls


def test_pytest_env_scrubs_host_tokens_and_sets_tmpdir(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "secret")
    monkeypatch.setenv("BAO_TOKEN", "secret")
    monkeypatch.setenv("OPENBAO_TOKEN", "secret")
    monkeypatch.setenv("CE_OVERWATCH_PAT", "secret")
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda paths, label, err: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda repo_root: None)
    runner = FakeRunner(tmp_path)

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=io.StringIO(), err=io.StringIO())

    assert rc == 0
    pytest_call = next(call for call in runner.calls if call[0][:3] == [sys.executable, "-m", "pytest"])
    env = pytest_call[2]
    assert env is not None
    assert env["TMPDIR"] == "/var/tmp"
    for key in pr_preflight.TOKEN_ENV_VARS:
        assert key not in env
