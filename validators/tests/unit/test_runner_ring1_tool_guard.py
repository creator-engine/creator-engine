"""Unit tests for runner-owned Ring-1 PATH shims."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from creator_engine_validator import fs_mediation as fm
from creator_engine_validator.runner.ring1_tool_guard import (
    DENY_EXIT_CODE,
    DEFAULT_EVIDENCE_ROOT,
    DEFAULT_SHIM_DIR,
    DEFAULT_SHIM_PARENT,
    Ring1ShimRootError,
    Ring1ToolGuardConfig,
    build_runtime,
    guarded_env,
    render_install_script,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def _write_executable(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _fake_hook_check(path: Path) -> Path:
    return _write_executable(
        path,
        """#!/usr/bin/env python3
import json
import os
import pathlib
import sys

pathlib.Path(os.environ["CE_FAKE_HOOK_CAPTURE"]).write_text(sys.stdin.read(), encoding="utf-8")
argv_capture = os.environ.get("CE_FAKE_HOOK_ARGV_CAPTURE")
if argv_capture:
    pathlib.Path(argv_capture).write_text(json.dumps(sys.argv[1:]), encoding="utf-8")
env_capture = os.environ.get("CE_FAKE_HOOK_ENV_CAPTURE")
if env_capture:
    keys = [
        "CE_WORKER_ID",
        "CE_WORKER_RECORD_REF",
        "CE_WORKER_ROLE",
        "CE_WORKER_LANE_KIND",
        "CE_WORKER_SCOPE_ID",
        "CE_WORKER_SEAT_ID",
        "CE_WORKER_ACTOR",
        "CE_WORKER_PROCESS_ID",
    ]
    pathlib.Path(env_capture).write_text(
        json.dumps({key: os.environ.get(key) for key in keys}, sort_keys=True),
        encoding="utf-8",
    )
exit_code = os.environ.get("CE_FAKE_HOOK_EXIT")
if exit_code:
    print("fake hook-check failed", file=sys.stderr)
    raise SystemExit(int(exit_code))
raw_stdout = os.environ.get("CE_FAKE_HOOK_STDOUT_RAW")
if raw_stdout is not None:
    print(raw_stdout)
    raise SystemExit(0)
print(json.dumps({
    "decision": os.environ.get("CE_FAKE_HOOK_DECISION", "allow"),
    "reason": os.environ.get("CE_FAKE_HOOK_REASON", "restricted mechanic (deploy)"),
    "posture": os.environ.get("CE_FAKE_HOOK_POSTURE", "governed"),
}))
""",
    )


def _fake_real_tool(path: Path) -> Path:
    return _write_executable(
        path,
        """#!/usr/bin/env sh
set -eu
printf '%s\\n' "$*" > "$CE_REAL_TOOL_MARKER"
""",
    )


def _install(tmp_path: Path, config: Ring1ToolGuardConfig) -> Path:
    shim_dir = tmp_path / "guard"
    completed = subprocess.run(
        ["sh", "-c", render_install_script(config, str(shim_dir))],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return shim_dir


def _config(tmp_path: Path) -> tuple[Ring1ToolGuardConfig, Path, Path]:
    hook = _fake_hook_check(tmp_path / "fake-hook-check")
    real_git = _fake_real_tool(tmp_path / "real-git")
    config = Ring1ToolGuardConfig(
        tools=("git",),
        real_binaries=(("git", str(real_git)),),
        validator_argv=(str(hook),),
        base_path=os.environ.get("PATH", ""),
    )
    return config, hook, real_git


def test_rendered_shim_maps_git_push_to_bash_pretooluse_event(tmp_path):
    config, _, _ = _config(tmp_path)
    shim_dir = _install(tmp_path, config)
    capture = tmp_path / "event.json"
    argv_capture = tmp_path / "argv.json"
    marker = tmp_path / "real-git-ran"
    workdir = tmp_path / "work"
    workdir.mkdir()
    attacker_ledger = tmp_path / "attacker-ledger"
    attacker_ledger.mkdir()

    env = {
        **os.environ,
        "CE_RING1_POSTURE": "ungoverned",
        "CE_RING1_POSTURE_ROOT": str(tmp_path / "attacker-root"),
        "CE_LEDGER_ROOT": str(attacker_ledger),
        "CE_FAKE_HOOK_CAPTURE": str(capture),
        "CE_FAKE_HOOK_ARGV_CAPTURE": str(argv_capture),
        "CE_REAL_TOOL_MARKER": str(marker),
    }
    completed = subprocess.run(
        [str(shim_dir / "git"), "push", "origin", "main"],
        cwd=workdir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    event = json.loads(capture.read_text(encoding="utf-8"))
    assert event["hook_event_name"] == "PreToolUse"
    assert event["tool_name"] == "Bash"
    assert event["tool_input"] == {"command": "git push origin main"}
    assert event["cwd"] == str(workdir)
    assert event["ce"]["posture"] == "governed"
    assert event["ce"]["evidence_root"] == DEFAULT_EVIDENCE_ROOT
    assert marker.read_text(encoding="utf-8").strip() == "push origin main"

    shim_text = (shim_dir / "git").read_text(encoding="utf-8")
    assert "CE_RING1_POSTURE" not in shim_text
    assert "CE_LEDGER_ROOT" not in shim_text

    hook_argv = json.loads(argv_capture.read_text(encoding="utf-8"))
    assert hook_argv[:5] == ["hook-check", "--stdin", "--format", "raw", "--posture"]
    assert hook_argv[hook_argv.index("--posture") + 1] == "governed"
    assert "--posture-root" in hook_argv
    assert str(workdir) in hook_argv
    assert "--ledger-root" not in hook_argv


def test_default_guard_surface_includes_execution_plane_entrypoints():
    config = Ring1ToolGuardConfig()

    assert set(config.tools) >= {"git", "gh", "ce", "tar", "python", "python3", "carrier-gen", "carrier_gen"}
    real = dict(config.real_binaries)
    for tool in config.tools:
        assert real[tool]


def test_rendered_shim_propagates_launcher_pinned_worker_context(tmp_path):
    hook = _fake_hook_check(tmp_path / "fake-hook-check")
    real_ce = _fake_real_tool(tmp_path / "real-ce")
    config = Ring1ToolGuardConfig(
        tools=("ce",),
        real_binaries=(("ce", str(real_ce)),),
        validator_argv=(str(hook),),
        base_path=os.environ.get("PATH", ""),
        worker_context={
            "worker_id": "worker-impl",
            "record_ref": "/runtime/worktree/.ce/state/workers/worker-impl/worker.yaml",
            "role": "implementer",
            "lane_kind": "implementation",
            "scope_id": "ce-ops#557",
            "seat_id": "seat-impl",
            "actor": "actor-impl",
        },
    )
    shim_dir = _install(tmp_path, config)
    capture = tmp_path / "event.json"
    env_capture = tmp_path / "env.json"
    marker = tmp_path / "real-ce-ran"
    env = {
        **os.environ,
        "CE_FAKE_HOOK_CAPTURE": str(capture),
        "CE_FAKE_HOOK_ENV_CAPTURE": str(env_capture),
        "CE_REAL_TOOL_MARKER": str(marker),
    }

    completed = subprocess.run(
        [str(shim_dir / "ce"), "validate-pr", "--declared-work-class", "story"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    event = json.loads(capture.read_text(encoding="utf-8"))
    worker_context = event["ce"]["authenticated_worker_context"]
    assert worker_context["worker_id"] == "worker-impl"
    assert worker_context["role"] == "implementer"
    assert worker_context["process_id"].isdigit()

    hook_env = json.loads(env_capture.read_text(encoding="utf-8"))
    assert hook_env["CE_WORKER_ID"] == "worker-impl"
    assert hook_env["CE_WORKER_RECORD_REF"].endswith("/worker-impl/worker.yaml")
    assert hook_env["CE_WORKER_ROLE"] == "implementer"
    assert hook_env["CE_WORKER_PROCESS_ID"] == worker_context["process_id"]
    assert marker.read_text(encoding="utf-8").strip() == "validate-pr --declared-work-class story"


def test_raw_deny_exits_nonzero_without_execing_real_binary(tmp_path):
    config, _, _ = _config(tmp_path)
    shim_dir = _install(tmp_path, config)
    marker = tmp_path / "real-git-ran"
    env = {
        **os.environ,
        "CE_FAKE_HOOK_CAPTURE": str(tmp_path / "event.json"),
        "CE_FAKE_HOOK_DECISION": "deny",
        "CE_FAKE_HOOK_POSTURE": "governed",
        "CE_REAL_TOOL_MARKER": str(marker),
    }

    completed = subprocess.run(
        [str(shim_dir / "git"), "push", "origin", "main"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == DENY_EXIT_CODE
    assert "git deny by hook-check (posture=governed)" in completed.stderr
    assert "restricted mechanic (deploy)" in completed.stderr
    assert not marker.exists()


@pytest.mark.parametrize(
    ("tool", "args", "primitive"),
    [
        ("ce", ["validate-pr", "--declared-work-class", "story"], "full_preflight"),
        ("tar", ["-xf", "harvest-bundle.tar"], "bundle_extraction"),
        (
            "python3",
            ["-m", "creator_engine_validator.carrier_gen", "--check"],
            "carrier_regeneration",
        ),
    ],
)
def test_codex_ring1_shim_refuses_controller_execution_plane_primitives(
    tmp_path, tool, args, primitive
):
    real_tool = _fake_real_tool(tmp_path / f"real-{tool}")
    tools = ("ce", "tar", "python3")
    config = Ring1ToolGuardConfig(
        tools=tools,
        real_binaries=tuple((name, str(real_tool)) for name in tools),
        validator_argv=(sys.executable, "-m", "creator_engine_validator"),
        base_path=os.environ.get("PATH", ""),
        posture_root=str(tmp_path),
    )
    shim_dir = _install(tmp_path, config)
    marker = tmp_path / "real-tool-ran"
    env = {
        **os.environ,
        "CE_REAL_TOOL_MARKER": str(marker),
        "PYTHONPATH": f"{REPO_ROOT / 'validators'}:{os.environ.get('PYTHONPATH', '')}",
    }

    completed = subprocess.run(
        [str(shim_dir / tool), *args],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == DENY_EXIT_CODE
    assert f"execution-plane primitive ({primitive})" in completed.stderr
    assert "ce worker run --role implementer" in completed.stderr
    assert not marker.exists()


def test_hook_check_cli_failure_is_fail_closed(tmp_path):
    config, _, _ = _config(tmp_path)
    shim_dir = _install(tmp_path, config)
    marker = tmp_path / "real-git-ran"
    env = {
        **os.environ,
        "CE_FAKE_HOOK_CAPTURE": str(tmp_path / "event.json"),
        "CE_FAKE_HOOK_EXIT": "2",
        "CE_REAL_TOOL_MARKER": str(marker),
    }

    completed = subprocess.run(
        [str(shim_dir / "git"), "status"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == DENY_EXIT_CODE
    assert "hook-check CLI failed for git" in completed.stderr
    assert not marker.exists()


def test_hook_check_invalid_json_is_fail_closed(tmp_path):
    config, _, _ = _config(tmp_path)
    shim_dir = _install(tmp_path, config)
    marker = tmp_path / "real-git-ran"
    env = {
        **os.environ,
        "CE_FAKE_HOOK_CAPTURE": str(tmp_path / "event.json"),
        "CE_FAKE_HOOK_STDOUT_RAW": "not-json",
        "CE_REAL_TOOL_MARKER": str(marker),
    }

    completed = subprocess.run(
        [str(shim_dir / "git"), "status"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == DENY_EXIT_CODE
    assert "hook-check returned invalid JSON for git" in completed.stderr
    assert not marker.exists()


def test_hook_check_non_object_decision_is_fail_closed(tmp_path):
    config, _, _ = _config(tmp_path)
    shim_dir = _install(tmp_path, config)
    marker = tmp_path / "real-git-ran"
    env = {
        **os.environ,
        "CE_FAKE_HOOK_CAPTURE": str(tmp_path / "event.json"),
        "CE_FAKE_HOOK_STDOUT_RAW": '["allow"]',
        "CE_REAL_TOOL_MARKER": str(marker),
    }

    completed = subprocess.run(
        [str(shim_dir / "git"), "status"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == DENY_EXIT_CODE
    assert "hook-check returned a non-object decision for git" in completed.stderr
    assert not marker.exists()


def test_hook_check_malformed_decision_is_fail_closed(tmp_path):
    config, _, _ = _config(tmp_path)
    shim_dir = _install(tmp_path, config)
    marker = tmp_path / "real-git-ran"
    env = {
        **os.environ,
        "CE_FAKE_HOOK_CAPTURE": str(tmp_path / "event.json"),
        "CE_FAKE_HOOK_DECISION": "permit",
        "CE_REAL_TOOL_MARKER": str(marker),
    }

    completed = subprocess.run(
        [str(shim_dir / "git"), "status"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == DENY_EXIT_CODE
    assert "hook-check returned malformed decision 'permit' for git" in completed.stderr
    assert not marker.exists()


def test_allow_exec_failure_is_fail_closed(tmp_path):
    hook = _fake_hook_check(tmp_path / "fake-hook-check")
    missing_real_git = tmp_path / "missing-real-git"
    config = Ring1ToolGuardConfig(
        tools=("git",),
        real_binaries=(("git", str(missing_real_git)),),
        validator_argv=(str(hook),),
        base_path=os.environ.get("PATH", ""),
    )
    shim_dir = _install(tmp_path, config)
    env = {
        **os.environ,
        "CE_FAKE_HOOK_CAPTURE": str(tmp_path / "event.json"),
    }

    completed = subprocess.run(
        [str(shim_dir / "git"), "status"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == DENY_EXIT_CODE
    assert "allowed git could not exec real binary" in completed.stderr
    assert str(missing_real_git) in completed.stderr


def test_guarded_env_puts_shim_dir_first():
    config = Ring1ToolGuardConfig(base_path="/usr/bin")
    env = guarded_env(config, "/tmp/guard")
    assert env["PATH"] == "/tmp/guard:/usr/bin"
    assert env["CE_RING1_POSTURE"] == "governed"
    assert env["CE_RING1_EVIDENCE_ROOT"] == DEFAULT_EVIDENCE_ROOT


def test_default_shim_dir_is_process_scoped():
    assert DEFAULT_SHIM_DIR == f"{DEFAULT_SHIM_PARENT}/shim"
    if hasattr(os, "getuid"):
        assert f"-{os.getuid()}-" in DEFAULT_SHIM_PARENT
    assert DEFAULT_SHIM_PARENT.endswith(f"-{os.getpid()}")


def test_guarded_env_includes_backend_pinned_roots():
    config = Ring1ToolGuardConfig(
        base_path="/usr/bin",
        posture_root="/runtime/worktree",
        ledger_root="/runtime/worktree/.hermes/active-work-ledger",
    )
    env = guarded_env(config, "/tmp/guard")
    assert env["CE_RING1_POSTURE_ROOT"] == "/runtime/worktree"
    assert env["CE_LEDGER_ROOT"] == "/runtime/worktree/.hermes/active-work-ledger"


def test_build_runtime_carries_required_landlock_preexec(monkeypatch, tmp_path):
    monkeypatch.setattr(fm, "landlock_abi_version", lambda: 8)
    work = tmp_path / "worktree"
    runtime_code = tmp_path / "validator-code"
    shim_dir = tmp_path / "guard"
    work.mkdir()
    runtime_code.mkdir()
    config = Ring1ToolGuardConfig(
        base_path="/usr/bin",
        posture_root=str(work),
        extra_read_roots=(str(runtime_code),),
    )

    runtime = build_runtime(config, str(shim_dir))

    assert runtime.env["PATH"] == f"{shim_dir}:/usr/bin"
    assert runtime.fs_capability.sandbox_fs_enforced is True
    assert runtime.fs_capability.mechanism == fm.MECHANISM_LANDLOCK
    assert str(work) in runtime.fs_capability.allow_read_roots
    assert str(shim_dir) in runtime.fs_capability.allow_read_roots
    assert str(runtime_code) in runtime.fs_capability.allow_read_roots
    assert runtime.fs_preexec_fn is not None


def test_build_runtime_uses_resolved_private_shim_root_for_landlock(monkeypatch, tmp_path):
    monkeypatch.setattr(fm, "landlock_abi_version", lambda: 8)
    work = tmp_path / "worktree"
    parent = tmp_path / "private"
    work.mkdir()
    parent.mkdir(mode=0o700)
    raw_shim = parent / ".." / "private" / "guard"
    resolved_shim = str((parent / "guard").resolve())
    config = Ring1ToolGuardConfig(base_path="/usr/bin", posture_root=str(work))

    runtime = build_runtime(config, str(raw_shim))

    assert runtime.shim_dir == resolved_shim
    assert runtime.env["PATH"] == f"{resolved_shim}:/usr/bin"
    assert resolved_shim in runtime.fs_capability.allow_read_roots
    assert str(raw_shim) not in runtime.fs_capability.allow_read_roots


def test_build_runtime_rejects_symlinked_shim_root_before_landlock_allowlist(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(fm, "landlock_abi_version", lambda: 8)
    work = tmp_path / "worktree"
    secrets = tmp_path / "secrets"
    work.mkdir()
    (secrets / ".ssh").mkdir(parents=True)
    (secrets / ".ssh" / "id_rsa").write_text("SECRET\n", encoding="utf-8")
    shim_link = tmp_path / "shim-link"
    shim_link.symlink_to(secrets, target_is_directory=True)
    config = Ring1ToolGuardConfig(base_path="/usr/bin", posture_root=str(work))

    with pytest.raises(Ring1ShimRootError, match="symlink"):
        build_runtime(config, str(shim_link))


def test_build_runtime_rejects_unsafe_existing_shim_root(monkeypatch, tmp_path):
    monkeypatch.setattr(fm, "landlock_abi_version", lambda: 8)
    work = tmp_path / "worktree"
    shim_dir = tmp_path / "guard"
    work.mkdir()
    shim_dir.mkdir()
    shim_dir.chmod(0o777)
    config = Ring1ToolGuardConfig(base_path="/usr/bin", posture_root=str(work))

    with pytest.raises(Ring1ShimRootError, match="not private"):
        build_runtime(config, str(shim_dir))


def test_build_runtime_fails_closed_when_required_landlock_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(fm, "landlock_abi_version", lambda: None)
    work = tmp_path / "worktree"
    shim_dir = tmp_path / "guard"
    work.mkdir()
    config = Ring1ToolGuardConfig(base_path="/usr/bin", posture_root=str(work))

    with pytest.raises(fm.FsMediationUnavailable, match="fail-closed"):
        build_runtime(config, str(shim_dir))


@pytest.mark.parametrize("posture", ["auto", "ungoverned"])
def test_guard_config_rejects_non_governed_posture(posture):
    with pytest.raises(ValueError, match="hard-pinned"):
        Ring1ToolGuardConfig(posture=posture)
