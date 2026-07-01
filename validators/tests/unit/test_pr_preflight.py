from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

import pytest

from creator_engine_validator import pr_preflight
from creator_engine_validator.checks import test_coupling as coupling_chk


class FakeRunner:
    def __init__(
        self,
        repo_root: Path,
        *,
        dirty: str = "",
        malformed_returncode: int = 1,
        install_spec_signature_returncode: int = 0,
        install_spec_signature_stdout: str = "ok\n",
        path_manifest_returncode: int = 0,
        path_manifest_stdout: str = "ok\n",
        test_coupling_requires_marker: bool = False,
        gh_pr_body: str | None = None,
        gh_pr_body_returncode: int = 1,
        head_test_result: pr_preflight.CommandResult | None = None,
        baseline_test_result: pr_preflight.CommandResult | None = None,
        changed_paths: str = "",
    ):
        self.repo_root = repo_root
        self.dirty = dirty
        self.malformed_returncode = malformed_returncode
        self.install_spec_signature_returncode = install_spec_signature_returncode
        self.install_spec_signature_stdout = install_spec_signature_stdout
        self.path_manifest_returncode = path_manifest_returncode
        self.path_manifest_stdout = path_manifest_stdout
        self.test_coupling_requires_marker = test_coupling_requires_marker
        self.gh_pr_body = gh_pr_body
        self.gh_pr_body_returncode = gh_pr_body_returncode
        self.head_test_result = head_test_result or pr_preflight.CommandResult(0, "ok\n", "")
        self.baseline_test_result = baseline_test_result or pr_preflight.CommandResult(0, "ok\n", "")
        self.changed_paths = changed_paths
        self.calls: list[tuple[list[str], Path, dict[str, str] | None]] = []

    def __call__(self, argv, cwd, env=None, *, timeout=None):
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
        if argv == ["git", "diff", "--name-only", "abc1234..HEAD"]:
            return pr_preflight.CommandResult(0, self.changed_paths, "")
        if argv[:3] == ["gh", "pr", "view"]:
            if self.gh_pr_body_returncode != 0:
                return pr_preflight.CommandResult(self.gh_pr_body_returncode, "", "no pull requests found\n")
            return pr_preflight.CommandResult(0, self.gh_pr_body or "", "")
        if argv[:4] == ["git", "worktree", "add", "--detach"]:
            return pr_preflight.CommandResult(0, "", "")
        if argv[:4] == ["git", "worktree", "remove", "--force"]:
            return pr_preflight.CommandResult(0, "", "")
        if argv == pr_preflight._test_command_argv(pr_preflight.DEFAULT_TEST_COMMAND):
            if str(cwd).endswith("/base"):
                return self.baseline_test_result
            return self.head_test_result
        if argv[:3] == [sys.executable, "-m", "creator_engine_validator"] and "examples/malformed/" in argv:
            return pr_preflight.CommandResult(self.malformed_returncode, "malformed rejected\n", "")
        if argv[:3] == [sys.executable, "-m", "creator_engine_validator"] and "scan-install-spec-signature" in argv:
            return pr_preflight.CommandResult(self.install_spec_signature_returncode, self.install_spec_signature_stdout, "")
        if argv[:3] == [sys.executable, "-m", "creator_engine_validator"] and "verify-test-coupling" in argv:
            if not self.test_coupling_requires_marker:
                return pr_preflight.CommandResult(0, "ok\n", "")
            pr_body = ""
            if "--pr-body-file" in argv:
                pr_body_file = Path(argv[argv.index("--pr-body-file") + 1])
                pr_body = pr_body_file.read_text(encoding="utf-8")
            if coupling_chk.has_opt_out_marker(pr_body):
                return pr_preflight.CommandResult(0, "ok\n", "")
            return pr_preflight.CommandResult(
                1,
                f"FAIL {coupling_chk.CHECK_NAME} {coupling_chk.CODE_MISSING_TEST}\n",
                "",
            )
        if argv[:3] == [sys.executable, "-m", "creator_engine_validator"] and "verify-path-manifest" in argv:
            return pr_preflight.CommandResult(self.path_manifest_returncode, self.path_manifest_stdout, "")
        return pr_preflight.CommandResult(0, "ok\n", "")

    def argv_calls(self) -> list[list[str]]:
        return [call[0] for call in self.calls]


def _config(tmp_path: Path, **overrides) -> pr_preflight.PreflightConfig:
    values = {
        "repo_root": tmp_path,
        "base": "origin/main",
        "declared_work_class": "M",
        "head_ref": "dev4-night-lane0-pr-preflight",
        "allow_dirty": False,
    }
    values.update(overrides)
    return pr_preflight.PreflightConfig(**values)


def _stub_expensive_preflight_checks(monkeypatch) -> None:
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda paths, label, err: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda repo_root: None)


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
    assert "PASS: PR preflight" in out.getvalue()


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
        "scan-install-spec-signature",
        ".",
    ] in calls
    assert [
        sys.executable,
        "-m",
        "creator_engine_validator",
        "verify-work-sizing-floor",
        "--base",
        "abc1234",
        "--declared-work-class",
        "M",
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


def test_preflight_runs_fleet_manifest_guard(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda paths, label, err: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda repo_root: None)
    guarded = []

    def fake_fleet_manifest_guard(repo_root, out):
        guarded.append(repo_root)
        return "guarded"

    monkeypatch.setattr(pr_preflight, "_fleet_manifest_guard", fake_fleet_manifest_guard)

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=FakeRunner(tmp_path), out=io.StringIO(), err=io.StringIO())

    assert rc == 0
    assert guarded == [tmp_path]


def test_preflight_blocks_install_spec_signature_guard_failure(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda paths, label, err: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda repo_root: None)
    runner = FakeRunner(
        tmp_path,
        install_spec_signature_returncode=1,
        install_spec_signature_stdout="FAIL install_spec_signature_placeholder\n",
    )
    out = io.StringIO()
    err = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=err)

    assert rc == 1
    assert "[FAIL] Install-spec signature guard" in out.getvalue()
    assert "Install-spec signature guard failed with exit code 1" in out.getvalue()
    assert "FAIL install_spec_signature_placeholder" in out.getvalue()


def test_preflight_reports_missing_required_carrier(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda paths, label, err: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda repo_root: None)
    runner = FakeRunner(
        tmp_path,
        path_manifest_returncode=1,
        path_manifest_stdout="FAIL path_manifest_fidelity path_manifest_carrier_required\n",
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 1
    assert "FAIL: PR preflight" in out.getvalue()
    assert "path_manifest_carrier_required" in out.getvalue()


def test_preflight_reports_manifest_count_or_sha_desync(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda paths, label, err: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda repo_root: None)
    runner = FakeRunner(
        tmp_path,
        path_manifest_returncode=1,
        path_manifest_stdout=(
            "FAIL path_manifest_fidelity path_manifest_count_mismatch\n"
            "FAIL path_manifest_fidelity path_manifest_hash_mismatch\n"
        ),
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 1
    assert "path_manifest_count_mismatch" in out.getvalue()
    assert "path_manifest_hash_mismatch" in out.getvalue()


def test_preflight_discovers_legacy_declared_work_class_from_carrier(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda paths, label, err: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda repo_root: None)
    carrier = tmp_path / ".ce" / "pr-manifests" / "dev4-night-lane0-pr-preflight.md"
    carrier.parent.mkdir(parents=True)
    carrier.write_text("- **Declared work class:** feature\n", encoding="utf-8")
    runner = FakeRunner(
        tmp_path,
        changed_paths=".ce/pr-manifests/dev4-night-lane0-pr-preflight.md\n",
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(
        _config(tmp_path, declared_work_class=None),
        runner=runner,
        out=out,
        err=io.StringIO(),
    )

    assert rc == 0
    assert "[PASS] declared work class: M" in out.getvalue()


def test_preflight_discovers_canonical_declared_work_class_from_carrier(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda paths, label, err: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda repo_root: None)
    carrier = tmp_path / ".ce" / "pr-manifests" / "dev4-night-lane0-pr-preflight.md"
    carrier.parent.mkdir(parents=True)
    carrier.write_text("- **Declared work class:** S\n", encoding="utf-8")
    runner = FakeRunner(
        tmp_path,
        changed_paths=".ce/pr-manifests/dev4-night-lane0-pr-preflight.md\n",
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(
        _config(tmp_path, declared_work_class=None),
        runner=runner,
        out=out,
        err=io.StringIO(),
    )

    assert rc == 0
    assert "[PASS] declared work class: S" in out.getvalue()


def test_preflight_rejects_unknown_declared_work_class_from_carrier(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda paths, label, err: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda repo_root: None)
    carrier = tmp_path / ".ce" / "pr-manifests" / "dev4-night-lane0-pr-preflight.md"
    carrier.parent.mkdir(parents=True)
    carrier.write_text("- **Declared work class:** bogus\n", encoding="utf-8")
    runner = FakeRunner(
        tmp_path,
        changed_paths=".ce/pr-manifests/dev4-night-lane0-pr-preflight.md\n",
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(
        _config(tmp_path, declared_work_class=None),
        runner=runner,
        out=out,
        err=io.StringIO(),
    )

    assert rc == 1
    assert "expected one of: XS, S, M, L" in out.getvalue()
    assert "legacy aliases: tiny, story, feature, epic" in out.getvalue()
    assert not any("verify-work-sizing-floor" in call for call in runner.argv_calls())


def test_preflight_build_parser_accepts_canonical_and_legacy_work_class_inputs():
    parser = pr_preflight.build_parser()

    for declared, expected in {
        "XS": "XS",
        "S": "S",
        "M": "M",
        "L": "L",
        "tiny": "XS",
        "story": "S",
        "feature": "M",
        "epic": "L",
    }.items():
        args = parser.parse_args(["--declared-work-class", declared])

        assert args.declared_work_class == declared
        assert pr_preflight.normalize_work_class(args.declared_work_class) == expected


def test_preflight_build_parser_still_rejects_bogus_work_class():
    parser = pr_preflight.build_parser()

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--declared-work-class", "Z"])

    assert exc_info.value.code == 2


def test_preflight_fails_when_declared_work_class_line_missing(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda paths, label, err: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda repo_root: None)
    carrier = tmp_path / ".ce" / "pr-manifests" / "dev4-night-lane0-pr-preflight.md"
    carrier.parent.mkdir(parents=True)
    carrier.write_text("no declared line here\n", encoding="utf-8")
    runner = FakeRunner(
        tmp_path,
        changed_paths=".ce/pr-manifests/dev4-night-lane0-pr-preflight.md\n",
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(
        _config(tmp_path, declared_work_class=None),
        runner=runner,
        out=out,
        err=io.StringIO(),
    )

    assert rc == 1
    assert "exactly one declared work class line" in out.getvalue()
    assert "legacy aliases accepted: tiny, story, feature, epic" in out.getvalue()
    assert not any("verify-work-sizing-floor" in call for call in runner.argv_calls())


def test_preflight_fails_on_planted_new_test_failure(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda paths, label, err: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda repo_root: None)
    runner = FakeRunner(
        tmp_path,
        baseline_test_result=pr_preflight.CommandResult(0, "1 passed\n", ""),
        head_test_result=pr_preflight.CommandResult(
            1,
            "FAILED validators/tests/unit/test_example.py::test_planted\n",
            "",
        ),
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 1
    assert "baseline-diff test gate found new failure(s)" in out.getvalue()
    assert "validators/tests/unit/test_example.py::test_planted" in out.getvalue()
    assert not any("verify-path-manifest" in call for call in runner.argv_calls())


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


def test_preflight_passes_resolved_pr_body_to_test_coupling_gate(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    runner = FakeRunner(
        tmp_path,
        test_coupling_requires_marker=True,
        gh_pr_body=f"Documented exemption: {coupling_chk.OPT_OUT_MARKER}\n",
        gh_pr_body_returncode=0,
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 0
    coupling_call = next(call for call in runner.argv_calls() if "verify-test-coupling" in call)
    assert "--pr-body-file" in coupling_call
    assert "PASS: PR preflight" in out.getvalue()


def test_preflight_pr_body_file_marker_exempts_test_coupling_gate(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    pr_body_file = tmp_path / "body.md"
    pr_body_file.write_text(f"Documented exemption: {coupling_chk.OPT_OUT_MARKER}\n", encoding="utf-8")
    runner = FakeRunner(
        tmp_path,
        test_coupling_requires_marker=True,
        gh_pr_body_returncode=1,
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(
        _config(tmp_path, pr_body_file=pr_body_file),
        runner=runner,
        out=out,
        err=io.StringIO(),
    )

    assert rc == 0
    coupling_call = next(call for call in runner.argv_calls() if "verify-test-coupling" in call)
    assert "--pr-body-file" in coupling_call
    assert "PASS: PR preflight" in out.getvalue()


def test_preflight_without_exemption_marker_still_flags_test_coupling(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    runner = FakeRunner(
        tmp_path,
        test_coupling_requires_marker=True,
        gh_pr_body="No exemption here.\n",
        gh_pr_body_returncode=0,
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 1
    assert coupling_chk.CODE_MISSING_TEST in out.getvalue()


def test_preflight_keeps_strict_behavior_when_pr_body_unresolvable(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    runner = FakeRunner(
        tmp_path,
        test_coupling_requires_marker=True,
        gh_pr_body_returncode=1,
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 1
    coupling_call = next(call for call in runner.argv_calls() if "verify-test-coupling" in call)
    assert "--pr-body-file" not in coupling_call
    assert "could not read PR body via gh" in out.getvalue()
    assert coupling_chk.CODE_MISSING_TEST in out.getvalue()


def test_preflight_keeps_strict_behavior_when_pr_body_lookup_times_out(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    runner = FakeRunner(tmp_path, test_coupling_requires_marker=True)

    def timeout_runner(argv, cwd, env=None, *, timeout=None):
        if list(argv)[:3] == ["gh", "pr", "view"]:
            raise subprocess.TimeoutExpired(argv, timeout)
        return runner(argv, cwd, env, timeout=timeout)

    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=timeout_runner, out=out, err=io.StringIO())

    assert rc == 1
    coupling_call = next(call for call in runner.argv_calls() if "verify-test-coupling" in call)
    assert "--pr-body-file" not in coupling_call
    assert "timed out reading PR body via gh" in out.getvalue()
    assert coupling_chk.CODE_MISSING_TEST in out.getvalue()
