from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

import pytest

from creator_engine_validator import brain_runtime as rt
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
        portability_returncode: int = 0,
        portability_stdout: str = "ok\n",
        portability_stderr: str = "",
        test_coupling_requires_marker: bool = False,
        head_test_result: pr_preflight.CommandResult | None = None,
        baseline_test_result: pr_preflight.CommandResult | None = None,
        changed_paths: str = "",
        brain_drift_result: pr_preflight.CommandResult | None = None,
        ledger_show: dict[tuple[str, str], pr_preflight.CommandResult] | None = None,
        autogen_generator_result: pr_preflight.CommandResult | None = None,
        autogen_artifact_changed: bool = False,
        git_common_dir: str = ".git",
        git_dir: str = ".git",
    ):
        self.repo_root = repo_root
        self.dirty = dirty
        self.malformed_returncode = malformed_returncode
        self.install_spec_signature_returncode = install_spec_signature_returncode
        self.install_spec_signature_stdout = install_spec_signature_stdout
        self.path_manifest_returncode = path_manifest_returncode
        self.path_manifest_stdout = path_manifest_stdout
        self.portability_returncode = portability_returncode
        self.portability_stdout = portability_stdout
        self.portability_stderr = portability_stderr
        self.test_coupling_requires_marker = test_coupling_requires_marker
        self.head_test_result = head_test_result or pr_preflight.CommandResult(0, "1 passed in 0.01s\n", "")
        self.baseline_test_result = baseline_test_result or pr_preflight.CommandResult(0, "1 passed in 0.01s\n", "")
        self.changed_paths = changed_paths
        self.brain_drift_result = brain_drift_result or pr_preflight.CommandResult(0, "ok\n", "")
        self.ledger_show = ledger_show or {}
        self.autogen_generator_result = autogen_generator_result or pr_preflight.CommandResult(0, "generated\n", "")
        self.autogen_artifact_changed = autogen_artifact_changed
        self.git_common_dir = git_common_dir
        self.git_dir = git_dir
        self.calls: list[tuple[list[str], Path, dict[str, str] | None, float | None]] = []

    def __call__(self, argv, cwd, env=None, *, timeout=None):
        argv = list(argv)
        self.calls.append((argv, cwd, dict(env) if env is not None else None, timeout))
        if argv == ["git", "rev-parse", "--show-toplevel"]:
            return pr_preflight.CommandResult(0, str(self.repo_root) + "\n", "")
        if argv == ["git", "rev-parse", "--git-common-dir"]:
            return pr_preflight.CommandResult(0, self.git_common_dir + "\n", "")
        if argv == ["git", "rev-parse", "--git-dir"]:
            return pr_preflight.CommandResult(0, self.git_dir + "\n", "")
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
        if argv == ["git", "diff", "--name-status", "-z", "abc1234..HEAD"]:
            return pr_preflight.CommandResult(0, "", "")
        if argv[:2] == ["git", "show"] and len(argv) == 3 and ":" in argv[2]:
            ref, path = argv[2].split(":", 1)
            return self.ledger_show.get(
                (ref, path),
                pr_preflight.CommandResult(1, "", f"missing fixture for {argv[2]}"),
            )
        if argv[:4] == ["git", "worktree", "add", "--detach"]:
            return pr_preflight.CommandResult(0, "", "")
        if argv[:4] == ["git", "worktree", "remove", "--force"]:
            return pr_preflight.CommandResult(0, "", "")
        if argv[1:] in (
            pr_preflight._test_command_argv(pr_preflight.DEFAULT_TEST_COMMAND)[1:],
            pr_preflight._test_command_argv(pr_preflight.SEAT_READY_TEST_COMMAND)[1:],
        ):
            if str(cwd).endswith("/base"):
                return self.baseline_test_result
            return self.head_test_result
        if argv in (
            [sys.executable, "scripts/gen_cli_reference.py", "--write"],
            [sys.executable, "scripts/gen_schema_reference.py", "--write"],
        ):
            return self.autogen_generator_result
        if argv[:4] == ["git", "diff", "--quiet", "--"]:
            return pr_preflight.CommandResult(1 if self.autogen_artifact_changed else 0, "", "")
        if argv[:4] == ["git", "diff", "--cached", "--quiet"]:
            return pr_preflight.CommandResult(1 if self.autogen_artifact_changed else 0, "", "")
        if argv[:2] == ["git", "add"]:
            return pr_preflight.CommandResult(0, "", "")
        if argv[:2] == ["git", "commit"]:
            return pr_preflight.CommandResult(0, "[ce-499 test] refresh\n", "")
        if argv[1:3] == ["-m", "creator_engine_validator"] and "examples/malformed/" in argv:
            return pr_preflight.CommandResult(self.malformed_returncode, "malformed rejected\n", "")
        if argv[1:3] == ["-m", "creator_engine_validator"] and "scan-install-spec-signature" in argv:
            return pr_preflight.CommandResult(self.install_spec_signature_returncode, self.install_spec_signature_stdout, "")
        if argv[1:3] == ["-m", "creator_engine_validator"] and "scan-portability-plane" in argv:
            return pr_preflight.CommandResult(
                self.portability_returncode,
                self.portability_stdout,
                self.portability_stderr,
            )
        if argv[1:3] == ["-m", "creator_engine_validator"] and "verify-test-coupling" in argv:
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
        if argv[1:3] == ["-m", "creator_engine_validator"] and "verify-path-manifest" in argv:
            return pr_preflight.CommandResult(self.path_manifest_returncode, self.path_manifest_stdout, "")
        if argv[1:3] == ["-m", "creator_engine_validator.ce_cli"] and argv[3:7] == [
            "brain",
            "verify",
            "--drift",
            "--state-root",
        ]:
            return self.brain_drift_result
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
        "scratch_parent": tmp_path,
    }
    values.update(overrides)
    return pr_preflight.PreflightConfig(**values)


def test_preflight_owns_one_scratch_root_for_baseline_and_head(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    caller_tmpdir = tmp_path / "caller-owned"
    caller_tmpdir.mkdir()
    sibling = tmp_path / "sibling-invocation"
    sibling.mkdir()
    monkeypatch.setenv("TMPDIR", str(caller_tmpdir))
    runner = FakeRunner(tmp_path)

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=io.StringIO(), err=io.StringIO())

    assert rc == 0
    pytest_calls = [call for call in runner.calls if call[0][:3] == [sys.executable, "-m", "pytest"]]
    assert len(pytest_calls) == 2
    pytest_tmpdirs = {call[2]["TMPDIR"] for call in pytest_calls if call[2] is not None}
    assert len(pytest_tmpdirs) == 1
    owned_scratch = Path(pytest_tmpdirs.pop())
    assert owned_scratch.parent == tmp_path
    assert owned_scratch.name.startswith("cv-")
    baseline_add = next(call for call in runner.calls if call[0][:4] == ["git", "worktree", "add", "--detach"])
    assert Path(baseline_add[0][4]) == owned_scratch / "base"
    assert not owned_scratch.exists()
    assert caller_tmpdir.is_dir()
    assert sibling.is_dir()


def test_preflight_removes_only_owned_scratch_after_test_failure(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    sibling = tmp_path / "sibling-invocation"
    sibling.mkdir()
    runner = FakeRunner(
        tmp_path,
        head_test_result=pr_preflight.CommandResult(
            1,
            "1 failed in 0.01s\nFAILED validators/tests/test_new.py::test_new\n",
            "",
        ),
    )

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=io.StringIO(), err=io.StringIO())

    assert rc == 1
    pytest_call = next(call for call in runner.calls if call[0][:3] == [sys.executable, "-m", "pytest"])
    assert pytest_call[2] is not None
    assert not Path(pytest_call[2]["TMPDIR"]).exists()
    assert sibling.is_dir()


def test_preflight_removes_owned_scratch_after_runner_exception(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)

    class ExplodingHeadRunner(FakeRunner):
        def __call__(self, argv, cwd, env=None, *, timeout=None):
            if list(argv)[:3] == [sys.executable, "-m", "pytest"] and not str(cwd).endswith("/base"):
                self.calls.append((list(argv), cwd, dict(env) if env is not None else None, timeout))
                raise RuntimeError("controlled head runner explosion")
            return super().__call__(argv, cwd, env, timeout=timeout)

    runner = ExplodingHeadRunner(tmp_path)

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=io.StringIO(), err=io.StringIO())

    assert rc == 1
    pytest_call = next(call for call in runner.calls if call[0][:3] == [sys.executable, "-m", "pytest"])
    assert pytest_call[2] is not None
    assert not Path(pytest_call[2]["TMPDIR"]).exists()


def _stub_expensive_preflight_checks(monkeypatch) -> None:
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda paths, label, err: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda repo_root: None)


def _ledger_text(value: str) -> str:
    captured: list[str] = []
    rt.assert_claim(
        assertion_id=f"brain-assertion-preflight-{value}",
        claim={"subject": "brain", "predicate": "state", "object": value},
        scope="unit",
        evidence_ref="manual-preflight-test",
        records=[],
        write=lambda _path, text: captured.append(text),
    )
    return captured[-1]


def _append_ledger_text(existing: str, value: str) -> str:
    captured: list[str] = []
    rt.assert_claim(
        assertion_id=f"brain-assertion-preflight-{value}",
        claim={"subject": "brain", "predicate": "state", "object": value},
        scope="unit",
        evidence_ref="manual-preflight-test",
        records=rt.load_ledger_text(existing),
        write=lambda _path, text: captured.append(text),
    )
    return captured[-1]


def _write_brain_ledgers(repo_root: Path, *, canonical: str, local: str) -> None:
    canonical_path = repo_root / ".ce" / "brain" / "assertions.yaml"
    local_path = repo_root / ".ce" / "state" / "brain" / "assertions.yaml"
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    canonical_path.write_text(_ledger_text(canonical), encoding="utf-8")
    local_path.write_text(_ledger_text(local), encoding="utf-8")


def test_fetch_base_passes_network_timeout(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(pr_preflight.NETWORK_SUBPROCESS_TIMEOUT_ENV, "7.5")
    runner = FakeRunner(tmp_path)

    pr_preflight._fetch_base("origin/main", tmp_path, runner, io.StringIO(), io.StringIO())

    fetch_call = next(call for call in runner.calls if call[0][:2] == ["git", "fetch"])
    assert fetch_call[3] == 7.5


def test_fetch_base_timeout_surfaces_actionable_error(tmp_path: Path, monkeypatch):
    monkeypatch.setenv(pr_preflight.NETWORK_SUBPROCESS_TIMEOUT_ENV, "3")

    def timeout_runner(argv, cwd, env=None, *, timeout=None):
        if list(argv)[:2] == ["git", "fetch"]:
            raise subprocess.TimeoutExpired(argv, timeout)
        return FakeRunner(tmp_path)(argv, cwd, env, timeout=timeout)

    with pytest.raises(RuntimeError) as exc:
        pr_preflight._fetch_base("origin/main", tmp_path, timeout_runner, io.StringIO(), io.StringIO())

    message = str(exc.value)
    assert "git fetch for base branch 'main' timed out after 3s" in message
    assert "network connectivity" in message
    assert "GitHub availability" in message
    assert "origin remote" in message


def test_pr_body_lookup_uses_conventional_local_carrier(tmp_path: Path):
    carrier = tmp_path / ".ce" / "pr-manifests" / "dev4-night-lane0-pr-preflight.md"
    carrier.parent.mkdir(parents=True)
    carrier.write_text("local body\n", encoding="utf-8")
    runner = FakeRunner(tmp_path)

    body = pr_preflight._resolve_test_coupling_pr_body(_config(tmp_path), runner, io.StringIO())

    assert body == "local body\n"
    assert pr_preflight._conventional_pr_body_file(_config(tmp_path)) == carrier


def test_local_preflight_calls_do_not_receive_network_timeout(tmp_path: Path):
    runner = FakeRunner(tmp_path)

    pr_preflight._assert_clean_tree(_config(tmp_path), runner, io.StringIO())

    status_call = next(call for call in runner.calls if call[0] == ["git", "status", "--porcelain"])
    assert status_call[3] is None


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
        "verify-version-drift",
        ".",
    ] in calls
    assert [
        sys.executable,
        "-m",
        "creator_engine_validator",
        "verify-harness-promotion-matrix",
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


def test_preflight_runs_shared_image_build_smoke_tier(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    # This fixture calls the full preflight orchestration only to assert the
    # shared smoke-tier seam. Keep the unrelated production disk gate outside
    # this unit's scope, as nested preflight test subprocesses do.
    monkeypatch.setenv(pr_preflight.DISK_HEADROOM_GATE_DISABLED_ENV, "1")
    calls = []

    def fake_smoke(base, repo_root, *, runner, out):
        calls.append((base, repo_root, runner, out))
        return "no-op: no changed Dockerfile"

    monkeypatch.setattr(pr_preflight.image_build_smoke, "run_image_build_smoke", fake_smoke)
    runner = FakeRunner(tmp_path)

    assert pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=io.StringIO(), err=io.StringIO()) == 0
    assert len(calls) == 1
    assert calls[0][:3] == ("abc1234", tmp_path, runner)


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


def test_preflight_refuses_brain_ledger_delta_when_live_base_tail_moved(tmp_path: Path):
    pr_base_ledger = _ledger_text("base")
    live_base_ledger = _append_ledger_text(pr_base_ledger, "main-moved")
    runner = FakeRunner(
        tmp_path,
        changed_paths=f"{pr_preflight.BRAIN_LEDGER_PATH}\n",
        ledger_show={
            ("abc1234", pr_preflight.BRAIN_LEDGER_PATH): pr_preflight.CommandResult(0, pr_base_ledger, ""),
            ("origin/main", pr_preflight.BRAIN_LEDGER_PATH): pr_preflight.CommandResult(0, live_base_ledger, ""),
        },
    )
    out = io.StringIO()
    err = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=err)

    assert rc == 1
    output = out.getvalue()
    assert "[FAIL] Creator Engine validator - brain ledger current-tail PR-diff gate" in output
    assert "live base ledger tail moved after the PR base" in output
    assert "semantic fork/re-chain from a non-current tail" in output
    assert "`ce brain assert`" in output
    assert "`ce brain correct`" in output
    assert not any(
        call[:3] == [sys.executable, "-m", "creator_engine_validator"]
        and "verify-work-sizing-floor" in call
        for call in runner.argv_calls()
    )


def test_brain_current_tail_adapter_delegates_to_preflight_invariant(tmp_path: Path, monkeypatch):
    captured = {}

    def fake_gate(config, comparison_base, runner):
        captured.update(config=config, comparison_base=comparison_base, runner=runner)
        return "current tail"

    runner = FakeRunner(tmp_path)
    monkeypatch.setattr(pr_preflight, "_assert_brain_ledger_delta_uses_current_tail", fake_gate)

    assert (
        pr_preflight.run_brain_current_tail_gate(
            tmp_path,
            comparison_base="pr-merge-base",
            live_base="origin/main",
            runner=runner,
        )
        == "current tail"
    )
    assert captured["config"].repo_root == tmp_path
    assert captured["config"].base == "origin/main"
    assert captured["comparison_base"] == "pr-merge-base"
    assert captured["runner"] is runner


def test_brain_append_intent_xor_adapter_delegates_and_preserves_refusal(tmp_path: Path, monkeypatch):
    def refusing_gate(config, comparison_base, runner):
        assert config.repo_root == tmp_path
        assert config.base == comparison_base == "pr-merge-base"
        raise RuntimeError("hybrid brain edit refused")

    monkeypatch.setattr(pr_preflight, "_assert_brain_append_intent_xor", refusing_gate)

    with pytest.raises(RuntimeError, match="hybrid brain edit refused"):
        pr_preflight.run_brain_append_intent_xor_gate(
            tmp_path,
            comparison_base="pr-merge-base",
            runner=FakeRunner(tmp_path),
        )


def test_fleet_manifest_adapter_delegates_to_preflight_guard(tmp_path: Path, monkeypatch):
    captured = {}

    def fake_guard(repo_root, out):
        captured.update(repo_root=repo_root, out=out)
        return "fleet guarded"

    output = io.StringIO()
    monkeypatch.setattr(pr_preflight, "_fleet_manifest_guard", fake_guard)

    assert pr_preflight.run_fleet_manifest_guard(tmp_path, out=output) == "fleet guarded"
    assert captured == {"repo_root": tmp_path, "out": output}


def test_preflight_fails_closed_when_comparison_base_missing(tmp_path: Path):
    class MissingComparisonBaseRunner(FakeRunner):
        def __call__(self, argv, cwd, env=None, *, timeout=None):
            if list(argv) == ["git", "merge-base", "origin/main", "HEAD"]:
                self.calls.append((list(argv), cwd, dict(env) if env is not None else None, timeout))
                return pr_preflight.CommandResult(1, "", "fatal: Not a valid object name origin/main\n")
            return super().__call__(argv, cwd, env, timeout=timeout)

    runner = MissingComparisonBaseRunner(tmp_path)
    out = io.StringIO()
    err = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=err)

    assert rc == 1
    output = out.getvalue()
    assert "[FAIL] comparison base" in output
    assert "Not a valid object name origin/main" in output
    assert "FAIL: PR preflight" in output
    assert not any("verify-work-sizing-floor" in call for call in runner.argv_calls())


def test_preflight_brain_ledger_fast_path_skips_tail_hashing_when_ledger_unchanged(
    tmp_path: Path, monkeypatch
):
    _stub_expensive_preflight_checks(monkeypatch)
    runner = FakeRunner(
        tmp_path,
        changed_paths="validators/creator_engine_validator/pr_preflight.py\n",
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 0
    assert "authoritative brain ledger unchanged" in out.getvalue()
    assert not any(
        call[:2] == ["git", "show"] and call[2].endswith(f":{pr_preflight.BRAIN_LEDGER_PATH}")
        for call in runner.argv_calls()
    )


def test_preflight_allows_brain_ledger_delta_when_live_base_tail_matches(
    tmp_path: Path, monkeypatch
):
    _stub_expensive_preflight_checks(monkeypatch)
    base_ledger = _ledger_text("base")
    runner = FakeRunner(
        tmp_path,
        changed_paths=f"{pr_preflight.BRAIN_LEDGER_PATH}\n",
        ledger_show={
            ("abc1234", pr_preflight.BRAIN_LEDGER_PATH): pr_preflight.CommandResult(0, base_ledger, ""),
            ("origin/main", pr_preflight.BRAIN_LEDGER_PATH): pr_preflight.CommandResult(0, base_ledger, ""),
        },
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 0
    assert "authoritative brain ledger tail is current" in out.getvalue()


def test_run_preflight_enforces_brain_append_intent_xor_after_tail_gate(
    tmp_path: Path, monkeypatch
):
    _stub_expensive_preflight_checks(monkeypatch)
    base_ledger = _ledger_text("base")
    intent_path = ".ce/brain/append-intents/ce-491-prearming.yaml"
    runner = FakeRunner(
        tmp_path,
        changed_paths=f"{intent_path}\n{pr_preflight.BRAIN_LEDGER_PATH}\n",
        ledger_show={
            ("abc1234", pr_preflight.BRAIN_LEDGER_PATH): pr_preflight.CommandResult(0, base_ledger, ""),
            ("origin/main", pr_preflight.BRAIN_LEDGER_PATH): pr_preflight.CommandResult(0, base_ledger, ""),
        },
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    output = out.getvalue()
    assert rc == 1
    assert "[PASS] Creator Engine validator - brain ledger current-tail PR-diff gate" in output
    assert "[FAIL] Creator Engine validator - brain_append_intent_xor_direct_ledger" in output
    assert "brain_append_intent_xor_direct_ledger" in output
    assert "hybrid PRs are refused" in output

    intent_only_runner = FakeRunner(tmp_path, changed_paths=f"{intent_path}\n")
    intent_only_out = io.StringIO()

    intent_only_rc = pr_preflight.run_preflight(
        _config(tmp_path),
        runner=intent_only_runner,
        out=intent_only_out,
        err=io.StringIO(),
    )

    assert intent_only_rc == 0
    assert "[PASS] Creator Engine validator - brain_append_intent_xor_direct_ledger" in intent_only_out.getvalue()


def test_preflight_auto_reconciles_instance_local_brain_state_when_canonical_unchanged(
    tmp_path: Path, monkeypatch
):
    _stub_expensive_preflight_checks(monkeypatch)
    _write_brain_ledgers(tmp_path, canonical="canonical", local="stale-local")
    runner = FakeRunner(tmp_path, changed_paths="validators/creator_engine_validator/pr_preflight.py\n")
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 0
    assert (tmp_path / ".ce" / "state" / "brain" / "assertions.yaml").read_text(encoding="utf-8") == (
        tmp_path / ".ce" / "brain" / "assertions.yaml"
    ).read_text(encoding="utf-8")
    output = out.getvalue()
    assert "reconciled ignored instance-local .ce/state/brain from tracked .ce/brain" in output
    assert "`ce brain sync`" in output
    assert "CI is unaffected" in output
    assert [
        sys.executable,
        "-m",
        "creator_engine_validator.ce_cli",
        "brain",
        "verify",
        "--drift",
        "--state-root",
        ".ce/state",
    ] in runner.argv_calls()


def test_preflight_does_not_reconcile_when_canonical_brain_source_changed_and_gate_still_fails(
    tmp_path: Path, monkeypatch
):
    _stub_expensive_preflight_checks(monkeypatch)
    _write_brain_ledgers(tmp_path, canonical="canonical", local="stale-local")
    canonical = (tmp_path / ".ce" / "brain" / "assertions.yaml").read_text(encoding="utf-8")
    stale_local = (tmp_path / ".ce" / "state" / "brain" / "assertions.yaml").read_text(encoding="utf-8")
    runner = FakeRunner(
        tmp_path,
        changed_paths=".ce/brain/assertions.yaml\n",
        ledger_show={
            ("abc1234", pr_preflight.BRAIN_LEDGER_PATH): pr_preflight.CommandResult(0, canonical, ""),
            ("origin/main", pr_preflight.BRAIN_LEDGER_PATH): pr_preflight.CommandResult(0, canonical, ""),
        },
        brain_drift_result=pr_preflight.CommandResult(
            1,
            "ce brain verify --drift: FAIL (1 record(s))\n",
            "  ERROR: planted canonical drift\n",
        ),
    )
    out = io.StringIO()
    err = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=err)

    assert rc == 1
    assert (tmp_path / ".ce" / "state" / "brain" / "assertions.yaml").read_text(encoding="utf-8") == stale_local
    output = out.getvalue()
    assert "Creator Engine validator - brain drift check failed with exit code 1" in output
    assert "If this is ignored instance-local .ce/state/brain drift, run `ce brain sync`" in output
    assert "CI is unaffected by ignored instance-local runtime state" in output
    assert "PR changes to tracked .ce/brain sources are still gated" in output


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


def test_preflight_default_profile_none_is_byte_identical(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda paths, label, err: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda repo_root: None)
    runner_default = FakeRunner(
        tmp_path,
        path_manifest_returncode=1,
        path_manifest_stdout="FAIL path_manifest_fidelity path_manifest_carrier_required\n",
    )
    runner_explicit_none = FakeRunner(
        tmp_path,
        path_manifest_returncode=1,
        path_manifest_stdout="FAIL path_manifest_fidelity path_manifest_carrier_required\n",
    )
    out_default = io.StringIO()
    out_explicit_none = io.StringIO()
    err_default = io.StringIO()
    err_explicit_none = io.StringIO()

    rc_default = pr_preflight.run_preflight(
        _config(tmp_path),
        runner=runner_default,
        out=out_default,
        err=err_default,
    )
    rc_explicit_none = pr_preflight.run_preflight(
        _config(tmp_path, profile=None),
        runner=runner_explicit_none,
        out=out_explicit_none,
        err=err_explicit_none,
    )

    assert rc_default == rc_explicit_none == 1
    assert out_default.getvalue() == out_explicit_none.getvalue()
    assert err_default.getvalue() == err_explicit_none.getvalue()
    assert pr_preflight.CONTAINED_SEAT_CARRIER_NOTICE not in out_default.getvalue()


def test_contained_seat_profile_omits_only_carrier_required_gate(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda paths, label, err: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda repo_root: [])
    workflow_audits = []
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda repo_root: workflow_audits.append(repo_root))
    runner = FakeRunner(
        tmp_path,
        path_manifest_returncode=1,
        path_manifest_stdout="FAIL path_manifest_fidelity path_manifest_carrier_required\n",
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(
        _config(tmp_path, profile=pr_preflight.CONTAINED_SEAT_PROFILE),
        runner=runner,
        out=out,
        err=io.StringIO(),
    )

    assert rc == 0
    output = out.getvalue()
    assert pr_preflight.CONTAINED_SEAT_CARRIER_NOTICE in output
    assert "[PASS] Creator Engine validator - path-manifest PR-diff gate: passed; omitted" in output
    assert "PASS: PR preflight" in output
    assert workflow_audits == [tmp_path]
    assert any("verify-test-coupling" in call for call in runner.argv_calls())
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
    ] in runner.argv_calls()


def test_contained_seat_profile_still_enforces_non_carrier_path_manifest_failures(
    tmp_path: Path, monkeypatch
):
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda paths, label, err: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda repo_root: None)
    runner = FakeRunner(
        tmp_path,
        path_manifest_returncode=1,
        path_manifest_stdout=(
            "FAIL path_manifest_fidelity path_manifest_carrier_required\n"
            "FAIL path_manifest_fidelity path_manifest_count_mismatch\n"
        ),
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(
        _config(tmp_path, profile=pr_preflight.CONTAINED_SEAT_PROFILE),
        runner=runner,
        out=out,
        err=io.StringIO(),
    )

    assert rc == 1
    output = out.getvalue()
    assert "path_manifest_count_mismatch" in output
    assert "FAIL: PR preflight" in output
    assert pr_preflight.CONTAINED_SEAT_CARRIER_NOTICE not in output


def test_seat_ready_profile_does_not_omit_missing_carrier(tmp_path: Path, monkeypatch):
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

    rc = pr_preflight.run_preflight(
        _config(tmp_path, profile=pr_preflight.SEAT_READY_PROFILE),
        runner=runner,
        out=out,
        err=io.StringIO(),
    )

    output = out.getvalue()
    assert rc == 1
    assert "path_manifest_carrier_required" in output
    assert pr_preflight.CONTAINED_SEAT_CARRIER_NOTICE not in output
    assert "omitted path_manifest_carrier_required" not in output


def test_seat_ready_default_test_command_caps_pytest_workers(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    runner = FakeRunner(tmp_path)

    rc = pr_preflight.run_preflight(
        _config(tmp_path, profile=pr_preflight.SEAT_READY_PROFILE),
        runner=runner,
        out=io.StringIO(),
        err=io.StringIO(),
    )

    assert rc == 0
    assert "-n auto" not in pr_preflight.SEAT_READY_TEST_COMMAND
    assert f"-n {pr_preflight.SEAT_READY_PYTEST_WORKER_CAP}" in pr_preflight.SEAT_READY_TEST_COMMAND
    pytest_call = next(call for call in runner.calls if call[0][:3] == [sys.executable, "-m", "pytest"])
    assert "-n" in pytest_call[0]
    assert pytest_call[0][pytest_call[0].index("-n") + 1] == "4"
    assert "auto" not in pytest_call[0]


def test_seat_ready_pytest_env_uses_owned_scratch(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    runner = FakeRunner(tmp_path)

    rc = pr_preflight.run_preflight(
        _config(tmp_path, profile=pr_preflight.SEAT_READY_PROFILE),
        runner=runner,
        out=io.StringIO(),
        err=io.StringIO(),
    )

    assert rc == 0
    pytest_call = next(call for call in runner.calls if call[0][:3] == [sys.executable, "-m", "pytest"])
    env = pytest_call[2]
    assert env is not None
    owned_scratch = Path(env["TMPDIR"])
    assert owned_scratch.parent == tmp_path
    assert owned_scratch.name.startswith("cv-")
    assert not owned_scratch.exists()


def test_linked_worktree_default_test_command_uses_shared_main_venv_python(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    monkeypatch.delenv(pr_preflight.CE_VALIDATOR_PYTHON_ENV, raising=False)
    worktree = tmp_path / "worktree"
    main_repo = tmp_path / "main"
    worktree.mkdir()
    main_repo.mkdir()
    shared_python = str(main_repo / ".venv" / "bin" / "python")
    resolved: list[tuple[Path, Path]] = []

    def fake_ensure_worktree_python(worktree_root: Path, main_repo_root: Path) -> str:
        resolved.append((Path(worktree_root), Path(main_repo_root)))
        return shared_python

    monkeypatch.setattr(pr_preflight, "ensure_worktree_python", fake_ensure_worktree_python)
    runner = FakeRunner(
        worktree,
        git_common_dir=str(main_repo / ".git"),
        git_dir=str(main_repo / ".git" / "worktrees" / "worktree"),
    )

    rc = pr_preflight.run_preflight(_config(worktree), runner=runner, out=io.StringIO(), err=io.StringIO())

    assert rc == 0
    assert resolved == [(worktree.resolve(), main_repo.resolve())]
    pytest_call = next(call for call in runner.calls if call[0][1:3] == ["-m", "pytest"])
    assert pytest_call[0][0] == shared_python


def test_seat_ready_profile_skips_portability_guard_failure(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    runner = FakeRunner(
        tmp_path,
        portability_returncode=1,
        portability_stdout="FAIL portability_plane_detected\n",
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(
        _config(tmp_path, profile=pr_preflight.SEAT_READY_PROFILE),
        runner=runner,
        out=out,
        err=io.StringIO(),
    )

    output = out.getvalue()
    assert rc == 0
    assert "[PASS] Control-plane portability guard" in output
    assert "skipped for seat-ready because seat-image runtime characteristics produce proven false failures" in output
    assert "enforced by default-profile preflight at controller harvest" in output
    assert not any("scan-portability-plane" in call for call in runner.argv_calls())


def test_default_profile_enforces_portability_guard_failure(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    runner = FakeRunner(
        tmp_path,
        portability_returncode=1,
        portability_stdout="FAIL portability_plane_detected\n",
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(
        _config(tmp_path, profile=None),
        runner=runner,
        out=out,
        err=io.StringIO(),
    )

    output = out.getvalue()
    assert rc == 1
    assert "[FAIL] Control-plane portability guard" in output
    assert any("scan-portability-plane" in call for call in runner.argv_calls())


def test_seat_ready_autogen_gate_runs_only_for_profile_and_touched_surface(
    tmp_path: Path, monkeypatch
):
    _stub_expensive_preflight_checks(monkeypatch)

    seat_ready_runner = FakeRunner(
        tmp_path,
        changed_paths="validators/creator_engine_validator/pr_preflight.py\n",
    )
    rc = pr_preflight.run_preflight(
        _config(tmp_path, profile=pr_preflight.SEAT_READY_PROFILE),
        runner=seat_ready_runner,
        out=io.StringIO(),
        err=io.StringIO(),
    )
    assert rc == 0
    assert [sys.executable, "scripts/gen_cli_reference.py", "--write"] in seat_ready_runner.argv_calls()

    contained_runner = FakeRunner(
        tmp_path,
        changed_paths="validators/creator_engine_validator/pr_preflight.py\n",
    )
    rc = pr_preflight.run_preflight(
        _config(tmp_path, profile=pr_preflight.CONTAINED_SEAT_PROFILE),
        runner=contained_runner,
        out=io.StringIO(),
        err=io.StringIO(),
    )
    assert rc == 0
    assert [sys.executable, "scripts/gen_cli_reference.py", "--write"] not in contained_runner.argv_calls()

    unprofiled_runner = FakeRunner(
        tmp_path,
        changed_paths="validators/creator_engine_validator/pr_preflight.py\n",
    )
    rc = pr_preflight.run_preflight(
        _config(tmp_path, profile=None),
        runner=unprofiled_runner,
        out=io.StringIO(),
        err=io.StringIO(),
    )
    assert rc == 0
    assert [sys.executable, "scripts/gen_cli_reference.py", "--write"] not in unprofiled_runner.argv_calls()

    unchanged_surface_runner = FakeRunner(
        tmp_path,
        changed_paths="docs/design/seat-side-preflight.md\n",
    )
    rc = pr_preflight.run_preflight(
        _config(tmp_path, profile=pr_preflight.SEAT_READY_PROFILE),
        runner=unchanged_surface_runner,
        out=io.StringIO(),
        err=io.StringIO(),
    )
    assert rc == 0
    assert [sys.executable, "scripts/gen_cli_reference.py", "--write"] not in unchanged_surface_runner.argv_calls()


def test_seat_ready_autogen_gate_commits_only_regenerated_artifact(
    tmp_path: Path, monkeypatch
):
    _stub_expensive_preflight_checks(monkeypatch)
    runner = FakeRunner(
        tmp_path,
        changed_paths="validators/creator_engine_validator/pr_preflight.py\n",
        autogen_artifact_changed=True,
    )

    rc = pr_preflight.run_preflight(
        _config(tmp_path, profile=pr_preflight.SEAT_READY_PROFILE),
        runner=runner,
        out=io.StringIO(),
        err=io.StringIO(),
    )

    assert rc == 0
    calls = runner.argv_calls()
    artifact = ".ce/reference/cli.generated.md"
    assert ["git", "add", artifact] in calls
    assert [
        "git",
        "commit",
        "-m",
        "chore: refresh cli_reference_autogen_sync artifact",
        "--",
        artifact,
    ] in calls
    assert calls.index(["git", "add", artifact]) < calls.index(
        [
            "git",
            "commit",
            "-m",
            "chore: refresh cli_reference_autogen_sync artifact",
            "--",
            artifact,
        ]
    )


def test_seat_ready_autogen_gate_commits_only_regenerated_schema_artifact(
    tmp_path: Path, monkeypatch
):
    _stub_expensive_preflight_checks(monkeypatch)
    runner = FakeRunner(
        tmp_path,
        changed_paths="schemas/work-sizing.schema.yaml\n",
        autogen_artifact_changed=True,
    )

    rc = pr_preflight.run_preflight(
        _config(tmp_path, profile=pr_preflight.SEAT_READY_PROFILE),
        runner=runner,
        out=io.StringIO(),
        err=io.StringIO(),
    )

    assert rc == 0
    calls = runner.argv_calls()
    artifact = ".ce/reference/schemas.generated.md"
    assert [sys.executable, "scripts/gen_schema_reference.py", "--write"] in calls
    assert ["git", "add", artifact] in calls
    assert [
        "git",
        "commit",
        "-m",
        "chore: refresh schema_reference_autogen_sync artifact",
        "--",
        artifact,
    ] in calls


def test_seat_ready_autogen_gate_reports_env_skip_for_missing_generator_environment(
    tmp_path: Path, monkeypatch
):
    _stub_expensive_preflight_checks(monkeypatch)
    runner = FakeRunner(
        tmp_path,
        changed_paths="validators/creator_engine_validator/pr_preflight.py\n",
        autogen_generator_result=pr_preflight.CommandResult(
            1,
            "",
            "ModuleNotFoundError: No module named 'jinja2'\n",
        ),
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(
        _config(tmp_path, profile=pr_preflight.SEAT_READY_PROFILE),
        runner=runner,
        out=out,
        err=io.StringIO(),
    )

    assert rc == 0
    output = out.getvalue()
    assert "ENV-SKIP cli_reference_autogen_sync" in output
    assert "No module named 'jinja2'" in output


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


def test_preflight_build_parser_labels_command_as_optional_diagnostic():
    parser = pr_preflight.build_parser()

    assert "optional local PR diagnostic" in parser.description
    assert "not gate evidence" in parser.description


def test_preflight_build_parser_still_rejects_bogus_work_class():
    parser = pr_preflight.build_parser()

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--declared-work-class", "Z"])

    assert exc_info.value.code == 2


def test_preflight_build_parser_rejects_unknown_profile():
    parser = pr_preflight.build_parser()

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--profile", "bogus"])

    assert exc_info.value.code == 2


def test_validate_profile_accepts_seat_ready():
    pr_preflight._validate_profile(pr_preflight.SEAT_READY_PROFILE)


def test_validate_pr_profiles_include_seat_ready():
    assert pr_preflight.SEAT_READY_PROFILE in pr_preflight.VALIDATE_PR_PROFILES


def test_preflight_build_parser_hides_profile_from_help(capsys):
    parser = pr_preflight.build_parser()

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--help"])

    assert exc_info.value.code == 0
    assert "--profile" not in capsys.readouterr().out


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
            "FAILED validators/tests/unit/test_example.py::test_planted\n1 failed in 0.01s\n",
            "",
        ),
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 1
    assert "baseline-diff test gate found new failure(s)" in out.getvalue()
    assert "validators/tests/unit/test_example.py::test_planted" in out.getvalue()
    assert not any("verify-path-manifest" in call for call in runner.argv_calls())


def test_preflight_fails_closed_when_pytest_missing_on_both_sides(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda paths, label, err: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda repo_root: None)
    missing_pytest = pr_preflight.CommandResult(1, "", "/usr/bin/python: No module named pytest\n")
    runner = FakeRunner(
        tmp_path,
        baseline_test_result=missing_pytest,
        head_test_result=missing_pytest,
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 1
    output = out.getvalue()
    assert "baseline-diff test command did not execute tests on baseline" in output
    assert "CE_VALIDATOR_PYTHON" in output
    assert "No module named pytest" in output
    assert not any("verify-path-manifest" in call for call in runner.argv_calls())


def test_preflight_fails_closed_when_collection_or_import_exits_nonzero(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    collection_failure = pr_preflight.CommandResult(
        2,
        "ERROR collecting validators/tests/unit/test_import.py\n1 error in 0.01s\n",
        "ImportError while importing test module\n",
    )
    runner = FakeRunner(tmp_path, baseline_test_result=collection_failure)
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 1
    assert "baseline-diff test command did not execute tests on baseline" in out.getvalue()
    assert "collection/import failure" in out.getvalue()


def test_preflight_fails_closed_when_one_side_collects_zero_tests(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda paths, label, err: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda repo_root: None)
    runner = FakeRunner(
        tmp_path,
        baseline_test_result=pr_preflight.CommandResult(0, "1 passed in 0.01s\n", ""),
        head_test_result=pr_preflight.CommandResult(5, "collected 0 items\n\nno tests ran in 0.01s\n", ""),
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 1
    output = out.getvalue()
    assert "baseline-diff test command did not execute tests on head" in output
    assert "collected zero tests" in output
    assert not any("verify-path-manifest" in call for call in runner.argv_calls())


def test_preflight_fails_closed_when_one_leg_has_no_output(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    runner = FakeRunner(tmp_path, head_test_result=pr_preflight.CommandResult(0, "", ""))
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 1
    assert "baseline-diff test command did not execute tests on head" in out.getvalue()
    assert "no trustworthy terminal test-execution summary" in out.getvalue()


def test_preflight_fails_closed_when_summary_counts_are_untrustworthy(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    runner = FakeRunner(
        tmp_path,
        baseline_test_result=pr_preflight.CommandResult(0, "collected 2 items\n1 passed\n", ""),
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 1
    assert "baseline-diff test command did not execute tests on baseline" in out.getvalue()
    assert "no trustworthy terminal test-execution summary" in out.getvalue()


def test_preflight_surfaces_baseline_and_head_collected_passed_counts(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    result = pr_preflight.CommandResult(0, "collected 2 items\n2 passed in 0.01s\n", "")
    runner = FakeRunner(tmp_path, baseline_test_result=result, head_test_result=result)
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 0
    assert "baseline collected/passed=2/2" in out.getvalue()
    assert "head collected/passed=2/2" in out.getvalue()


def test_preflight_still_passes_genuine_identical_test_failures(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(pr_preflight, "_yaml_parse", lambda paths, label, err: None)
    monkeypatch.setattr(pr_preflight, "_workflow_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_artifact_yaml_paths", lambda repo_root: [])
    monkeypatch.setattr(pr_preflight, "_workflow_permissions_audit", lambda repo_root: None)
    identical_failure = pr_preflight.CommandResult(
        1,
        "FAILED validators/tests/unit/test_example.py::test_existing\n1 failed in 0.01s\n",
        "",
    )
    runner = FakeRunner(
        tmp_path,
        baseline_test_result=identical_failure,
        head_test_result=identical_failure,
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 0
    assert "zero new failures (baseline=1 failures, head=1 failures" in out.getvalue()
    assert "baseline collected/passed=1/0" in out.getvalue()
    assert "head collected/passed=1/0" in out.getvalue()
    assert "PASS: PR preflight" in out.getvalue()


def test_preflight_reports_skipped_tests_with_file_reasons_and_pass_flag(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    runner = FakeRunner(
        tmp_path,
        head_test_result=pr_preflight.CommandResult(
            0,
            "\n".join(
                [
                    "=========================== short test summary info ===========================",
                    "SKIPPED [1] validators/tests/integration/test_container_deps.py:14: ssh-keygen unavailable",
                    "SKIPPED [1] validators/tests/integration/test_worker_runtime.py:22: podman unavailable",
                    "2 passed, 2 skipped in 0.02s",
                    "",
                ]
            ),
            "",
        ),
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 0
    output = out.getvalue()
    assert "REPORT-FLAG skipped tests: 2 skipped tests in head baseline-diff test run" in output
    assert (
        "REPORT-FLAG skipped tests: validators/tests/integration/test_container_deps.py: "
        "1 skipped test reason=ssh-keygen unavailable"
    ) in output
    assert (
        "REPORT-FLAG skipped tests: validators/tests/integration/test_worker_runtime.py: "
        "1 skipped test reason=podman unavailable"
    ) in output
    assert "PASS: PR preflight (with 2 skipped tests -- see report above)" in output


def test_preflight_zero_skip_run_does_not_print_report_flag(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    runner = FakeRunner(
        tmp_path,
        head_test_result=pr_preflight.CommandResult(0, "3 passed in 0.02s\n", ""),
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 0
    output = out.getvalue()
    assert "REPORT-FLAG skipped tests" not in output
    assert "PASS: PR preflight (with" not in output
    assert "PASS: PR preflight" in output


def test_contained_seat_profile_reports_skips_without_changing_carrier_notice(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    runner = FakeRunner(
        tmp_path,
        path_manifest_returncode=1,
        path_manifest_stdout="FAIL path_manifest_fidelity path_manifest_carrier_required\n",
        head_test_result=pr_preflight.CommandResult(
            0,
            "\n".join(
                [
                    "=========================== short test summary info ===========================",
                    "SKIPPED [1] validators/tests/integration/test_container_deps.py:14: ssh-keygen unavailable",
                    "4 passed, 1 skipped in 0.02s",
                    "",
                ]
            ),
            "",
        ),
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(
        _config(tmp_path, profile=pr_preflight.CONTAINED_SEAT_PROFILE),
        runner=runner,
        out=out,
        err=io.StringIO(),
    )

    assert rc == 0
    output = out.getvalue()
    assert pr_preflight.CONTAINED_SEAT_CARRIER_NOTICE in output
    assert "REPORT-FLAG skipped tests: validators/tests/integration/test_container_deps.py" in output
    assert "PASS: PR preflight (with 1 skipped test -- see report above)" in output


def test_pytest_env_scrubs_host_tokens_and_replaces_caller_tmpdir_with_owned_scratch(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "secret")
    monkeypatch.setenv("BAO_TOKEN", "secret")
    monkeypatch.setenv("OPENBAO_TOKEN", "secret")
    monkeypatch.setenv("CE_OVERWATCH_PAT", "secret")
    monkeypatch.setenv("TMPDIR", "/custom/path")
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
    owned_scratch = Path(env["TMPDIR"])
    assert owned_scratch != Path("/custom/path")
    assert owned_scratch.parent == tmp_path
    assert owned_scratch.name.startswith("cv-")
    assert not owned_scratch.exists()
    for key in pr_preflight.TOKEN_ENV_VARS:
        assert key not in env


def test_preflight_passes_resolved_pr_body_to_test_coupling_gate(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    carrier = tmp_path / ".ce" / "pr-manifests" / "dev4-night-lane0-pr-preflight.md"
    carrier.parent.mkdir(parents=True)
    carrier.write_text(f"Documented exemption: {coupling_chk.OPT_OUT_MARKER}\n", encoding="utf-8")
    runner = FakeRunner(
        tmp_path,
        test_coupling_requires_marker=True,
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
    carrier = tmp_path / ".ce" / "pr-manifests" / "dev4-night-lane0-pr-preflight.md"
    carrier.parent.mkdir(parents=True)
    carrier.write_text("No exemption here.\n", encoding="utf-8")
    runner = FakeRunner(
        tmp_path,
        test_coupling_requires_marker=True,
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
    )
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 1
    coupling_call = next(call for call in runner.argv_calls() if "verify-test-coupling" in call)
    assert "--pr-body-file" not in coupling_call
    assert coupling_chk.CODE_MISSING_TEST in out.getvalue()


def test_preflight_keeps_strict_behavior_when_local_pr_body_fallback_unreadable(tmp_path: Path, monkeypatch):
    _stub_expensive_preflight_checks(monkeypatch)
    carrier = tmp_path / ".ce" / "pr-manifests" / "dev4-night-lane0-pr-preflight.md"
    carrier.parent.mkdir(parents=True)
    carrier.write_bytes(b"\xff")
    runner = FakeRunner(tmp_path, test_coupling_requires_marker=True)
    out = io.StringIO()

    rc = pr_preflight.run_preflight(_config(tmp_path), runner=runner, out=out, err=io.StringIO())

    assert rc == 1
    coupling_call = next(call for call in runner.argv_calls() if "verify-test-coupling" in call)
    assert "--pr-body-file" not in coupling_call
    assert "could not read local PR body fallback" in out.getvalue()
    assert coupling_chk.CODE_MISSING_TEST in out.getvalue()


# --- Governed workflow-permissions audit ---------------------------------


def _write_workflow(root: Path, name: str, body: str) -> Path:
    workflow_dir = root / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    path = workflow_dir / name
    path.write_text(body, encoding="utf-8")
    return path


_READ_ONLY_WORKFLOW = """\
name: Read Only
on:
  pull_request: {}
permissions:
  contents: read
  pull-requests: read
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - run: 'true'
"""

_WRITE_CAPABLE_WORKFLOW = """\
name: Write Capable
on:
  workflow_dispatch: {}
permissions:
  contents: read
jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - run: 'true'
"""


def test_workflow_permissions_audit_accepts_read_only_governed_profile(tmp_path: Path, monkeypatch):
    _write_workflow(tmp_path, "read-only.yml", _READ_ONLY_WORKFLOW)
    monkeypatch.setattr(
        pr_preflight,
        "GOVERNED_WORKFLOW_PERMISSIONS",
        {"read-only.yml": {"": {"contents": "read", "pull-requests": "read"}}},
    )

    # No exception == pass.
    pr_preflight._workflow_permissions_audit(tmp_path)


def test_workflow_permissions_audit_accepts_write_capable_governed_profile(tmp_path: Path, monkeypatch):
    _write_workflow(tmp_path, "write-capable.yml", _WRITE_CAPABLE_WORKFLOW)
    monkeypatch.setattr(
        pr_preflight,
        "GOVERNED_WORKFLOW_PERMISSIONS",
        {
            "write-capable.yml": {
                "": {"contents": "read"},
                "jobs.publish": {"contents": "read", "packages": "write"},
            }
        },
    )

    pr_preflight._workflow_permissions_audit(tmp_path)


def test_workflow_permissions_audit_discovers_yaml_and_yml_extensions(tmp_path: Path, monkeypatch):
    _write_workflow(tmp_path, "a.yml", _READ_ONLY_WORKFLOW)
    _write_workflow(tmp_path, "b.yaml", _READ_ONLY_WORKFLOW)
    monkeypatch.setattr(
        pr_preflight,
        "GOVERNED_WORKFLOW_PERMISSIONS",
        {
            "a.yml": {"": {"contents": "read", "pull-requests": "read"}},
            "b.yaml": {"": {"contents": "read", "pull-requests": "read"}},
        },
    )

    pr_preflight._workflow_permissions_audit(tmp_path)


def test_workflow_permissions_audit_rejects_stale_governed_registry_entry(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(
        pr_preflight,
        "GOVERNED_WORKFLOW_PERMISSIONS",
        {"removed-workflow.yml": {"": {"contents": "read"}}},
    )

    with pytest.raises(RuntimeError, match="workflow permissions audit failed"):
        pr_preflight._workflow_permissions_audit(tmp_path)

    output = capsys.readouterr().out
    assert "FAIL removed-workflow.yml: governed workflow is missing from .github/workflows" in output


def test_workflow_permissions_audit_rejects_unregistered_workflow_with_permissions(tmp_path: Path, monkeypatch, capsys):
    _write_workflow(tmp_path, "rogue.yml", _READ_ONLY_WORKFLOW)
    monkeypatch.setattr(pr_preflight, "GOVERNED_WORKFLOW_PERMISSIONS", {})

    with pytest.raises(RuntimeError, match="workflow permissions audit failed"):
        pr_preflight._workflow_permissions_audit(tmp_path)

    output = capsys.readouterr().out
    assert "FAIL rogue.yml: unregistered workflow declares permissions" in output
    assert ".permissions (top-level)" in output


def test_workflow_permissions_audit_rejects_unregistered_workflow_without_permissions(tmp_path: Path, monkeypatch, capsys):
    _write_workflow(
        tmp_path,
        "rogue.yml",
        "name: Rogue\non:\n  push: {}\njobs:\n  check:\n    runs-on: ubuntu-latest\n    steps:\n      - run: 'true'\n",
    )
    monkeypatch.setattr(pr_preflight, "GOVERNED_WORKFLOW_PERMISSIONS", {})

    with pytest.raises(RuntimeError, match="workflow permissions audit failed"):
        pr_preflight._workflow_permissions_audit(tmp_path)

    output = capsys.readouterr().out
    assert (
        "FAIL rogue.yml: unregistered workflow; add an explicit permission profile "
        "to GOVERNED_WORKFLOW_PERMISSIONS"
    ) in output


def test_workflow_permissions_audit_rejects_unratified_expansion(tmp_path: Path, monkeypatch, capsys):
    _write_workflow(tmp_path, "expander.yml", _WRITE_CAPABLE_WORKFLOW)
    # Registry only sanctions read at the job node; the committed workflow adds
    # packages: write -> unratified expansion.
    monkeypatch.setattr(
        pr_preflight,
        "GOVERNED_WORKFLOW_PERMISSIONS",
        {
            "expander.yml": {
                "": {"contents": "read"},
                "jobs.publish": {"contents": "read"},
            }
        },
    )

    with pytest.raises(RuntimeError, match="workflow permissions audit failed"):
        pr_preflight._workflow_permissions_audit(tmp_path)

    output = capsys.readouterr().out
    assert "FAIL expander.yml: permission profile drift" in output
    assert ".jobs.publish.permissions" in output
    assert "packages" in output


def test_workflow_permissions_audit_rejects_undeclared_block(tmp_path: Path, monkeypatch, capsys):
    _write_workflow(tmp_path, "write-capable.yml", _WRITE_CAPABLE_WORKFLOW)
    # Registry omits the job-level block entirely -> undeclared permissions.
    monkeypatch.setattr(
        pr_preflight,
        "GOVERNED_WORKFLOW_PERMISSIONS",
        {"write-capable.yml": {"": {"contents": "read"}}},
    )

    with pytest.raises(RuntimeError, match="workflow permissions audit failed"):
        pr_preflight._workflow_permissions_audit(tmp_path)

    output = capsys.readouterr().out
    assert "FAIL write-capable.yml: undeclared permissions block" in output
    assert ".jobs.publish.permissions" in output


def test_workflow_permissions_audit_flags_missing_governed_block(tmp_path: Path, monkeypatch, capsys):
    _write_workflow(tmp_path, "read-only.yml", _READ_ONLY_WORKFLOW)
    monkeypatch.setattr(
        pr_preflight,
        "GOVERNED_WORKFLOW_PERMISSIONS",
        {
            "read-only.yml": {
                "": {"contents": "read", "pull-requests": "read"},
                "jobs.check": {"contents": "write"},
            }
        },
    )

    with pytest.raises(RuntimeError, match="workflow permissions audit failed"):
        pr_preflight._workflow_permissions_audit(tmp_path)

    output = capsys.readouterr().out
    assert "governed permissions block" in output
    assert "is missing from the workflow" in output


def test_workflow_permissions_audit_string_form_never_matches_scoped_profile(tmp_path: Path, monkeypatch, capsys):
    _write_workflow(
        tmp_path,
        "shorthand.yml",
        "name: Shorthand\non:\n  push: {}\npermissions: write-all\njobs:\n"
        "  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: 'true'\n",
    )
    monkeypatch.setattr(
        pr_preflight,
        "GOVERNED_WORKFLOW_PERMISSIONS",
        {"shorthand.yml": {"": {"contents": "write"}}},
    )

    with pytest.raises(RuntimeError, match="workflow permissions audit failed"):
        pr_preflight._workflow_permissions_audit(tmp_path)

    output = capsys.readouterr().out
    assert "__all__" in output


def test_governed_registry_matches_committed_workflows():
    # The shipped registry must keep the real repository green: every governed
    # profile audits clean against the checked-in workflows.
    repo_root = Path(__file__).resolve().parents[3]
    pr_preflight._workflow_permissions_audit(repo_root)
