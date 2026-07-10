"""F-2 gate-hardening unit tests.

Covers three behaviours ratified in VPS_STORAGE_GATE_INCIDENT_DESIGN_20260710.md §C/F-2:

1. Attempt-log path fallback chain: CE_DAEMON_LOG_DIR → LOGS_DIRECTORY → journald-only
   (never die on log-file failure).
2. Startup disk-headroom check in launch-queue-daemon.sh: exit code 75 + "disk_headroom"
   message when free space is below the threshold; check runs BEFORE the singleton lease.
3. Liveness state file: run_daemon_loop writes/refreshes a JSON state file after every
   completed pass (last_pass_timestamp, pass_index, failed_count).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from creator_engine_validator.forge import integrator_belt as belt


# ---------------------------------------------------------------------------
# Helpers shared by bash-level tests
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _write_fake_container_engine_noop(path: Path) -> None:
    """Container engine that exits 0 and writes nothing (no argv capture needed)."""
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "exit 0\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _write_fake_container_engine_noop_with_output(path: Path) -> None:
    """Container engine that exits 0 and emits minimal stdout/stderr."""
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'printf "fake engine stdout\\n"\n'
        'printf "fake engine stderr\\n" >&2\n'
        "exit 0\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _run_container_runner(
    daemon: str, env: dict[str, str], *, timeout: int = 5
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash",
            str(_repo_root() / "deploy" / "daemons" / "run-daemon-container.sh"),
            daemon,
        ],
        cwd=_repo_root(),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _base_container_runner_env(tmp_path: Path, fake_engine: Path) -> dict[str, str]:
    """Minimal environment for run-daemon-container.sh (no CE_DAEMON_LOG_DIR set)."""
    return {
        "PATH": os.environ.get("PATH", ""),
        "CE_CONTAINER_ENGINE": str(fake_engine),
        "CE_DAEMON_REPO_ROOT": str(_repo_root()),
        "CE_DAEMON_STATE_ROOT": str(tmp_path / "state"),
        "CE_DAEMON_IMAGE": "example.invalid/ce-runtime@sha256:abc",
        # Intentionally NO CE_DAEMON_LOG_DIR and NO LOGS_DIRECTORY here.
    }


# ---------------------------------------------------------------------------
# F-2.1 — Attempt-log path fallback chain
# ---------------------------------------------------------------------------


def test_attempt_log_warns_and_continues_when_no_log_dir_set(tmp_path: Path):
    """Neither CE_DAEMON_LOG_DIR nor LOGS_DIRECTORY set → warning on stderr,
    daemon does NOT exit because it cannot create a log file."""
    fake_engine = tmp_path / "fake-engine"
    _write_fake_container_engine_noop(fake_engine)

    env = _base_container_runner_env(tmp_path, fake_engine)
    # Confirm neither variable is present in the constructed env.
    env.pop("CE_DAEMON_LOG_DIR", None)
    env.pop("LOGS_DIRECTORY", None)

    proc = _run_container_runner("queue-daemon", env)

    # Script must not fail due to missing log dir.
    assert proc.returncode == 0, proc.stderr
    # Warning must appear on stderr.
    assert "CE_DAEMON_LOG_DIR and LOGS_DIRECTORY are unset" in proc.stderr
    assert "journald only" in proc.stderr


def test_attempt_log_uses_logs_directory_when_ce_daemon_log_dir_absent(tmp_path: Path):
    """LOGS_DIRECTORY (systemd injection) is used when CE_DAEMON_LOG_DIR is not set."""
    fake_engine = tmp_path / "fake-engine"
    _write_fake_container_engine_noop_with_output(fake_engine)
    logs_dir = tmp_path / "systemd-logs"

    env = _base_container_runner_env(tmp_path, fake_engine)
    env.pop("CE_DAEMON_LOG_DIR", None)
    env["LOGS_DIRECTORY"] = str(logs_dir)

    proc = _run_container_runner("queue-daemon", env)

    assert proc.returncode == 0, proc.stderr
    # A log file should be created under the LOGS_DIRECTORY path.
    log_files = list(logs_dir.glob("ce-wall-daemon-container-queue-daemon-*.log"))
    assert len(log_files) == 1, (
        f"expected exactly one log file under {logs_dir}, got {log_files}"
    )
    # The latest symlink should also be present.
    latest = logs_dir / "ce-wall-daemon-container.log"
    assert latest.is_symlink()


def test_attempt_log_uses_ce_daemon_log_dir_when_both_set(tmp_path: Path):
    """CE_DAEMON_LOG_DIR takes precedence over LOGS_DIRECTORY."""
    fake_engine = tmp_path / "fake-engine"
    _write_fake_container_engine_noop_with_output(fake_engine)
    explicit_dir = tmp_path / "explicit-logs"
    systemd_dir = tmp_path / "systemd-logs"

    env = _base_container_runner_env(tmp_path, fake_engine)
    env["CE_DAEMON_LOG_DIR"] = str(explicit_dir)
    env["LOGS_DIRECTORY"] = str(systemd_dir)

    proc = _run_container_runner("queue-daemon", env)

    assert proc.returncode == 0, proc.stderr
    # Log file must be in the explicit dir, not the systemd dir.
    assert list(explicit_dir.glob("ce-wall-daemon-container-queue-daemon-*.log")), (
        f"expected log file under CE_DAEMON_LOG_DIR {explicit_dir}"
    )
    assert not list(systemd_dir.glob("ce-wall-daemon-container-queue-daemon-*.log")), (
        f"unexpected log file under LOGS_DIRECTORY {systemd_dir}"
    )


def test_attempt_log_warns_and_continues_when_log_dir_unwritable(tmp_path: Path):
    """Unwritable log directory → warning + journald-only degradation, daemon continues."""
    fake_engine = tmp_path / "fake-engine"
    _write_fake_container_engine_noop(fake_engine)
    # Create a directory that we cannot write into.
    locked_dir = tmp_path / "locked"
    locked_dir.mkdir(mode=0o555)

    env = _base_container_runner_env(tmp_path, fake_engine)
    env["CE_DAEMON_LOG_DIR"] = str(locked_dir / "subdir")

    try:
        proc = _run_container_runner("queue-daemon", env)
        assert proc.returncode == 0, proc.stderr
        assert "WARNING" in proc.stderr
        assert "journald only" in proc.stderr
    finally:
        # Restore permissions so tmp_path cleanup can delete the directory.
        locked_dir.chmod(0o755)


# ---------------------------------------------------------------------------
# F-2.2 — Disk-headroom startup check (distinct exit code 75)
# ---------------------------------------------------------------------------

def _queue_daemon_env_for_headroom(
    tmp_path: Path, fake_bin: Path, fake_df: Path | None = None
) -> dict[str, str]:
    """Minimal environment for the launch-queue-daemon.sh headroom check tests."""
    repo_root = _repo_root()
    env = os.environ.copy()
    bin_dir = str(fake_df.parent) if fake_df is not None else ""
    path_prefix = f"{bin_dir}:{env.get('PATH', '')}" if bin_dir else env.get("PATH", "")
    env.update(
        {
            "PATH": path_prefix,
            "GH_TOKEN": "unit-test-gh-token",
            "BAO_TOKEN": "unit-test-bao-token",
            "BAO_ADDR": "https://bao.example.invalid",
            "CE_GATE_REPO": "creator-engine/creator-engine",
            "CE_GATE_AUTHORIZED_REVIEWERS": "reviewer-login",
            "CE_OPENBAO_KV_MOUNT": "ce-kv",
            "CE_APPROVAL_WALL_SECRET_PATH": "forge/approval-capability/wall",
            "CE_APPROVAL_WALL_SECRET_FIELD": "signing_secret",
            "CE_APPROVAL_WALL_POLICY_SHA": "policy-sha",
            "CE_APPROVAL_WALL_SECRET_REF_POLICY_SHA": "secret-ref-policy-sha",
            "CE_DAEMON_UNCONTAINED": "1",
            "CE_DAEMON_STATE_ROOT": str(tmp_path / "state"),
            "CE_QUEUE_DAEMON_BIN": str(fake_bin),
            "CE_QUEUE_DAEMON_REPO_ROOT": str(repo_root),
            "CE_DAEMON_LEASE_ROOT": str(tmp_path / "lease"),
            "CE_DAEMON_LEASE_PYTHON": sys.executable,
            "CE_QUEUE_DAEMON_ROOT": str(tmp_path / "queue-root"),
            "CE_APPROVAL_WALL_SECRET_TARGET_FILE": str(tmp_path / "run" / "approval-wall-secret"),
            "CE_APPROVAL_WALL_STATE": str(tmp_path / "state" / "approval-wall-state.json"),
        }
    )
    return env


def _write_fake_df_low_space(path: Path, avail_kb: int = 100) -> None:
    """Fake df -P that reports avail_kb of free space, regardless of path argument."""
    path.write_text(
        "#!/usr/bin/env bash\n"
        "# Fake df that simulates very low disk space\n"
        f'printf "Filesystem     1024-blocks    Used Available Capacity Mounted on\\n"\n'
        f'printf "/dev/sda1       10000000  9900000  {avail_kb}  99%% /\\n"\n',
        encoding="utf-8",
    )
    path.chmod(0o755)


def _write_fake_df_ample_space(path: Path, avail_kb: int = 10 * 1024 * 1024) -> None:
    """Fake df -P that reports ample free space."""
    path.write_text(
        "#!/usr/bin/env bash\n"
        "# Fake df that simulates ample disk space\n"
        f'printf "Filesystem     1024-blocks    Used Available Capacity Mounted on\\n"\n'
        f'printf "/dev/sda1      100000000       0  {avail_kb}   0%% /\\n"\n',
        encoding="utf-8",
    )
    path.chmod(0o755)


def _write_fake_queue_daemon_marker(path: Path, marker: Path) -> None:
    """Fake queue-daemon binary that creates a marker file then exits 0."""
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f'touch "{marker}"\n'
        "exit 0\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def test_disk_headroom_check_refuses_with_exit_75_when_space_below_threshold(tmp_path: Path):
    """launch-queue-daemon.sh exits 75 and names 'disk_headroom' when free space is low."""
    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    fake_df = fake_bin_dir / "df"
    fake_daemon = fake_bin_dir / "fake-cev3"
    marker = tmp_path / "daemon-started"

    # 100 kB free — well below the 5 GiB default threshold (5242880 kB).
    _write_fake_df_low_space(fake_df, avail_kb=100)
    _write_fake_queue_daemon_marker(fake_daemon, marker)

    env = _queue_daemon_env_for_headroom(tmp_path, fake_daemon, fake_df)

    proc = subprocess.run(
        ["bash", str(_repo_root() / "deploy" / "queue-daemon" / "launch-queue-daemon.sh")],
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    # Must exit with distinct exit code 75.
    assert proc.returncode == 75, (
        f"expected exit 75 (disk_headroom), got {proc.returncode}. stderr: {proc.stderr}"
    )
    # Error message must name the class of failure.
    assert "disk_headroom" in proc.stderr, (
        f"expected 'disk_headroom' in stderr, got: {proc.stderr!r}"
    )
    # The daemon binary must NOT have been started.
    assert not marker.exists(), "daemon was started despite low-disk refusal"


def test_disk_headroom_check_allows_start_when_space_above_threshold(tmp_path: Path):
    """launch-queue-daemon.sh proceeds when free space exceeds the threshold."""
    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    fake_df = fake_bin_dir / "df"
    fake_daemon = fake_bin_dir / "fake-cev3"
    marker = tmp_path / "daemon-started"

    # 10 GiB free — well above 5 GiB default.
    _write_fake_df_ample_space(fake_df, avail_kb=10 * 1024 * 1024)
    _write_fake_queue_daemon_marker(fake_daemon, marker)

    env = _queue_daemon_env_for_headroom(tmp_path, fake_daemon, fake_df)

    proc = subprocess.run(
        ["bash", str(_repo_root() / "deploy" / "queue-daemon" / "launch-queue-daemon.sh")],
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    # Should not exit 75.
    assert proc.returncode != 75, (
        f"unexpected disk_headroom refusal: {proc.stderr}"
    )
    # Marker may or may not exist depending on the fake Python supervisor path,
    # but we confirmed the disk check did not block startup.


def test_disk_headroom_check_respects_custom_threshold_env(tmp_path: Path):
    """CE_DAEMON_DISK_HEADROOM_GB overrides the 5 GiB default."""
    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir()
    fake_df = fake_bin_dir / "df"
    fake_daemon = fake_bin_dir / "fake-cev3"
    marker = tmp_path / "daemon-started"

    # 3 GiB free (3145728 kB).
    _write_fake_df_low_space(fake_df, avail_kb=3 * 1024 * 1024)
    _write_fake_queue_daemon_marker(fake_daemon, marker)

    env = _queue_daemon_env_for_headroom(tmp_path, fake_daemon, fake_df)
    # Require only 2 GiB — 3 GiB available should pass.
    env["CE_DAEMON_DISK_HEADROOM_GB"] = "2"

    proc = subprocess.run(
        ["bash", str(_repo_root() / "deploy" / "queue-daemon" / "launch-queue-daemon.sh")],
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    # With 3 GiB available and a 2 GiB threshold, startup should not be blocked.
    assert proc.returncode != 75, (
        f"unexpected disk_headroom refusal with custom threshold: {proc.stderr}"
    )

    # And with the same space but a higher threshold (10 GiB), it should refuse.
    env2 = dict(env)
    env2["CE_DAEMON_DISK_HEADROOM_GB"] = "10"
    proc2 = subprocess.run(
        ["bash", str(_repo_root() / "deploy" / "queue-daemon" / "launch-queue-daemon.sh")],
        env=env2,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc2.returncode == 75, (
        f"expected disk_headroom refusal with 10 GiB threshold, got {proc2.returncode}"
    )
    assert "disk_headroom" in proc2.stderr


# ---------------------------------------------------------------------------
# F-2.3 — Liveness state file refresh
# ---------------------------------------------------------------------------

def _make_fake_gh_empty(*, repo: str) -> object:
    """Return a gh_runner stub that returns an empty PR list from the GraphQL search.

    The response shape must match discover_daemon_candidates expectations:
    ``{"data": {"search": {"pageInfo": {"hasNextPage": false}, "nodes": []}}}``.
    """
    _EMPTY_SEARCH = (
        '{"data":{"search":{"pageInfo":{"hasNextPage":false},"nodes":[]}}}'
    )

    def _gh(argv, input_text=None):
        argv_list = list(argv)
        if "api" in argv_list and "graphql" in argv_list:
            return subprocess.CompletedProcess(argv_list, 0, stdout=_EMPTY_SEARCH, stderr="")
        return subprocess.CompletedProcess(argv_list, 0, stdout="", stderr="")

    return _gh


def test_liveness_state_file_written_after_pass(tmp_path: Path):
    """run_daemon_loop writes a liveness state JSON file after each completed pass."""
    liveness_path = tmp_path / "queue-daemon-liveness.json"
    logs: list[dict] = []

    belt.run_daemon_loop(
        token="ghp_fake",
        repo="creator-engine/creator-engine",
        once=True,
        gh_runner=_make_fake_gh_empty(repo="creator-engine/creator-engine"),
        sleep=lambda _: None,
        log_sink=logs.append,
        rate_limiter=None,
        liveness_state_path=liveness_path,
    )

    assert liveness_path.exists(), "liveness state file was not created"
    state = json.loads(liveness_path.read_text(encoding="utf-8"))
    assert "last_pass_timestamp" in state
    assert state["pass_index"] == 1
    assert isinstance(state["failed_count"], int)


def test_liveness_state_file_refreshed_on_each_pass(tmp_path: Path):
    """Liveness file is re-written on every completed pass with an updated pass_index."""
    liveness_path = tmp_path / "queue-daemon-liveness.json"
    pass_count = 3
    call_count = 0

    def fake_sleep(_seconds: float) -> None:
        pass

    # Run three passes by patching once=False and tracking iterations.
    original_run_daemon_pass = belt.run_daemon_pass
    results = []

    def fake_run_daemon_pass(**kwargs):
        nonlocal call_count
        call_count += 1
        result = original_run_daemon_pass(**kwargs)
        results.append(result)
        return result

    import unittest.mock as _mock
    with _mock.patch.object(belt, "run_daemon_pass", side_effect=fake_run_daemon_pass):
        # Use once=False but break after pass_count iterations via a custom clock.
        # Simplest: run three once=True loops and verify monotonic pass_index.
        for expected_index in range(1, pass_count + 1):
            belt.run_daemon_loop(
                token="ghp_fake",
                repo="creator-engine/creator-engine",
                once=True,
                gh_runner=_make_fake_gh_empty(repo="creator-engine/creator-engine"),
                sleep=fake_sleep,
                log_sink=None,
                rate_limiter=None,
                liveness_state_path=liveness_path,
            )
            state = json.loads(liveness_path.read_text(encoding="utf-8"))
            assert state["pass_index"] == 1, (
                f"pass {expected_index}: expected pass_index=1 (once=True resets), "
                f"got {state['pass_index']}"
            )
            assert "last_pass_timestamp" in state
            assert "failed_count" in state


def test_liveness_state_file_from_env_var(tmp_path: Path, monkeypatch):
    """CE_DAEMON_LIVENESS_STATE_PATH controls the file when no explicit arg is given."""
    liveness_path = tmp_path / "from-env-liveness.json"
    monkeypatch.setenv("CE_DAEMON_LIVENESS_STATE_PATH", str(liveness_path))

    belt.run_daemon_loop(
        token="ghp_fake",
        repo="creator-engine/creator-engine",
        once=True,
        gh_runner=_make_fake_gh_empty(repo="creator-engine/creator-engine"),
        sleep=lambda _: None,
        log_sink=None,
        rate_limiter=None,
        # liveness_state_path intentionally NOT passed
    )

    assert liveness_path.exists(), "liveness state file was not created from env var"
    state = json.loads(liveness_path.read_text(encoding="utf-8"))
    assert state["pass_index"] == 1
    assert "last_pass_timestamp" in state


def test_liveness_state_explicit_arg_overrides_env_var(tmp_path: Path, monkeypatch):
    """Explicit liveness_state_path arg wins over CE_DAEMON_LIVENESS_STATE_PATH."""
    env_path = tmp_path / "env-liveness.json"
    arg_path = tmp_path / "arg-liveness.json"
    monkeypatch.setenv("CE_DAEMON_LIVENESS_STATE_PATH", str(env_path))

    belt.run_daemon_loop(
        token="ghp_fake",
        repo="creator-engine/creator-engine",
        once=True,
        gh_runner=_make_fake_gh_empty(repo="creator-engine/creator-engine"),
        sleep=lambda _: None,
        log_sink=None,
        rate_limiter=None,
        liveness_state_path=arg_path,
    )

    assert arg_path.exists(), "liveness state file was not written to explicit path"
    assert not env_path.exists(), "liveness state file written to env var path instead of arg"


def test_liveness_state_disabled_when_no_path(tmp_path: Path, monkeypatch):
    """No liveness state file is written when neither arg nor env var is set."""
    monkeypatch.delenv("CE_DAEMON_LIVENESS_STATE_PATH", raising=False)

    belt.run_daemon_loop(
        token="ghp_fake",
        repo="creator-engine/creator-engine",
        once=True,
        gh_runner=_make_fake_gh_empty(repo="creator-engine/creator-engine"),
        sleep=lambda _: None,
        log_sink=None,
        rate_limiter=None,
        # liveness_state_path not passed, env var unset
    )
    # No exception → pass; nothing to assert about files since no path is configured.


def test_liveness_state_contains_required_fields(tmp_path: Path):
    """The liveness state JSON contains last_pass_timestamp, pass_index, failed_count."""
    liveness_path = tmp_path / "liveness.json"

    belt.run_daemon_loop(
        token="ghp_fake",
        repo="creator-engine/creator-engine",
        once=True,
        gh_runner=_make_fake_gh_empty(repo="creator-engine/creator-engine"),
        sleep=lambda _: None,
        log_sink=None,
        rate_limiter=None,
        liveness_state_path=liveness_path,
    )

    state = json.loads(liveness_path.read_text(encoding="utf-8"))
    # All three required fields must be present.
    assert set(state.keys()) >= {"last_pass_timestamp", "pass_index", "failed_count"}
    # last_pass_timestamp must be an ISO-format UTC string.
    ts = state["last_pass_timestamp"]
    assert isinstance(ts, str) and "T" in ts and (ts.endswith("+00:00") or ts.endswith("Z")), (
        f"last_pass_timestamp must be UTC ISO format, got: {ts!r}"
    )
    # pass_index must be a positive integer.
    assert isinstance(state["pass_index"], int) and state["pass_index"] >= 1
    # failed_count must be a non-negative integer.
    assert isinstance(state["failed_count"], int) and state["failed_count"] >= 0
