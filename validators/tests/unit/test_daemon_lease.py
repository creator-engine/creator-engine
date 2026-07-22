from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

import creator_engine_validator.daemon_lease as daemon_lease
from creator_engine_validator.daemon_lease import (
    DaemonLeaseAmbiguous,
    DaemonLeaseHeld,
    DaemonLeaseStale,
    acquire,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _payload(*, holder_id: str, heartbeat_at: float, pid: int | None = None) -> dict[str, object]:
    return {
        "holder_id": holder_id,
        "pid": os.getpid() if pid is None else pid,
        "host": socket.gethostname(),
        "acquired_at": heartbeat_at,
        "heartbeat_at": heartbeat_at,
    }


def _missing_pid() -> int:
    pid = 999_999_999
    while True:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return pid
        pid += 1


def _queue_daemon_env(tmp_path: Path, lease_root: Path, fake_bin: Path) -> dict[str, str]:
    repo_root = _repo_root()
    env = os.environ.copy()
    env.update(
        {
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
            "CE_DAEMON_LEASE_ROOT": str(lease_root),
            "CE_DAEMON_LEASE_HEARTBEAT_SECONDS": "0.05",
            "CE_DAEMON_LEASE_TTL_SECONDS": "10",
            "CE_DAEMON_LEASE_PYTHON": sys.executable,
            "CE_QUEUE_DAEMON_BIN": str(fake_bin),
            "CE_QUEUE_DAEMON_REPO_ROOT": str(repo_root),
            "CE_QUEUE_DAEMON_ROOT": str(tmp_path / "queue-root"),
            "CE_APPROVAL_WALL_SECRET_TARGET_FILE": str(tmp_path / "run" / "approval-wall-secret"),
            "CE_APPROVAL_WALL_STATE": str(tmp_path / "state" / "approval-wall-state.json"),
        }
    )
    return env


def _write_fake_queue_daemon(
    path: Path,
    *,
    marker: Path,
    stop_file: Path | None = None,
    pid_file: Path | None = None,
    term_marker: Path | None = None,
) -> None:
    pid_block = f'printf "%s\\n" "$$" > "{pid_file}"\n' if pid_file is not None else ""
    term_block = f'trap \'touch "{term_marker}"; exit 0\' TERM\n' if term_marker is not None else ""
    wait_block = ""
    if stop_file is not None:
        wait_block = f'while [ ! -e "{stop_file}" ]; do sleep 0.02; done\n'
    else:
        wait_block = "while true; do sleep 0.02; done\n"
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"{pid_block}"
        f"{term_block}"
        f'touch "{marker}"\n'
        f"{wait_block}",
        encoding="utf-8",
    )
    path.chmod(0o755)


def _write_lease_replacement_race_hook(
    path: Path,
    *,
    lease_path: Path,
    replacement_payload: dict[str, object],
) -> None:
    """Inject a replacement between normal acquisition and recovery in the child process."""

    path.write_text(
        "from pathlib import Path\n"
        "from creator_engine_validator import daemon_lease\n\n"
        "_original_acquire = daemon_lease.acquire\n"
        f"_lease_path = Path({str(lease_path)!r})\n"
        f"_replacement = {json.dumps(json.dumps(replacement_payload))}\n\n"
        "def _replace() -> None:\n"
        "    _lease_path.write_text(_replacement, encoding='utf-8')\n\n"
        "def _racing_acquire(*args, **kwargs):\n"
        "    if kwargs.get('allow_takeover'):\n"
        "        _replace()\n"
        "        return _original_acquire(*args, **kwargs)\n"
        "    try:\n"
        "        return _original_acquire(*args, **kwargs)\n"
        "    except daemon_lease.DaemonLeaseStale:\n"
        "        _replace()\n"
        "        raise\n\n"
        "daemon_lease.acquire = _racing_acquire\n",
        encoding="utf-8",
    )


def _write_os_kill_error_hook(path: Path, *, pid: int, error: str) -> None:
    """Cause only the stale lease PID probe in the launcher child to fail."""

    path.write_text(
        "import os\n\n"
        "_original_kill = os.kill\n"
        f"_target_pid = {pid!r}\n\n"
        "def _raise_for_stale_lease_pid(candidate_pid, signal_number):\n"
        "    if candidate_pid == _target_pid and signal_number == 0:\n"
        f"        raise {error}\n"
        "    return _original_kill(candidate_pid, signal_number)\n\n"
        "os.kill = _raise_for_stale_lease_pid\n",
        encoding="utf-8",
    )


def _write_fake_container_engine(path: Path, argv_file: Path) -> None:
    # The fake engine path is invoked as the command; bake the output path into
    # a tiny wrapper to avoid relying on shell-specific argv quoting in tests.
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f'printf "%s\\n" "$@" > "{argv_file}"\n',
        encoding="utf-8",
    )
    path.chmod(0o755)


def _write_fake_container_engine_with_output(path: Path, argv_file: Path) -> None:
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f'printf "%s\\n" "$@" > "{argv_file}"\n'
        'printf "fake engine stdout\\n"\n'
        'printf "fake engine stderr\\n" >&2\n',
        encoding="utf-8",
    )
    path.chmod(0o755)


def _write_fake_stat_for_preowned_state(path: Path, *, state_root: Path, owner_uid: int) -> None:
    real_stat = Path("/usr/bin/stat")
    if not real_stat.exists():
        real_stat = Path("/bin/stat")
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f'if [[ "${{1:-}}" == "-c" && "${{3:-}}" == "--" && "${{4:-}}" == "{state_root}" ]]; then\n'
        '  case "${2:-}" in\n'
        "    %a)\n"
        "      printf '700\\n'\n"
        "      exit 0\n"
        "      ;;\n"
        "    %u)\n"
        f"      printf '{owner_uid}\\n'\n"
        "      exit 0\n"
        "      ;;\n"
        "  esac\n"
        "fi\n"
        f'exec "{real_stat}" "$@"\n',
        encoding="utf-8",
    )
    path.chmod(0o755)


def _container_runner_env(tmp_path: Path, fake_engine: Path) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", ""),
        "CE_CONTAINER_ENGINE": str(fake_engine),
        "CE_DAEMON_REPO_ROOT": str(_repo_root()),
        "CE_DAEMON_STATE_ROOT": str(tmp_path / "state"),
        "CE_DAEMON_IMAGE": "example.invalid/ce-runtime@sha256:abc",
        "CE_DAEMON_LOG_DIR": str(tmp_path / "logs"),
    }


def _run_container_runner(daemon: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(_repo_root() / "deploy" / "daemons" / "run-daemon-container.sh"), daemon],
        cwd=_repo_root(),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )


def _wait_for(predicate, *, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("condition did not become true before timeout")


def test_acquire_refuses_live_lease(tmp_path: Path):
    root = tmp_path / "leases"
    root.mkdir()

    first = acquire("conveyor", "holder-one", state_root=root, now=1000.0)
    try:
        with pytest.raises(DaemonLeaseHeld, match="live conveyor lease"):
            acquire("conveyor", "holder-two", state_root=root, now=1001.0)
    finally:
        first.release()


def test_stale_lease_requires_explicit_audited_takeover_record(tmp_path: Path):
    root = tmp_path / "leases"
    root.mkdir()
    lease_path = root / "conveyor.lease"
    lease_path.write_text(
        json.dumps(_payload(holder_id="old-holder", heartbeat_at=10.0, pid=_missing_pid())),
        encoding="utf-8",
    )

    with pytest.raises(DaemonLeaseStale, match="explicit audited takeover"):
        acquire("conveyor", "new-holder", state_root=root, ttl_seconds=30.0, now=100.0)

    lease = acquire(
        "conveyor",
        "new-holder",
        state_root=root,
        ttl_seconds=30.0,
        allow_takeover=True,
        takeover_reason="operator confirmed old daemon stopped",
        now=100.0,
    )
    try:
        payload = json.loads(lease_path.read_text(encoding="utf-8"))
        assert payload["holder_id"] == "new-holder"

        audit_path = root / "conveyor.lease.takeovers.jsonl"
        records = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
        assert len(records) == 1
        assert records[0]["action"] == "daemon_lease_takeover"
        assert records[0]["reason"] == "operator confirmed old daemon stopped"
        assert records[0]["old"]["holder_id"] == "old-holder"
        assert records[0]["new"]["holder_id"] == "new-holder"
    finally:
        lease.release()


def test_same_host_expired_ttl_with_alive_pid_is_live_and_refuses_takeover(tmp_path: Path):
    root = tmp_path / "leases"
    root.mkdir()
    lease_path = root / "conveyor.lease"
    lease_path.write_text(json.dumps(_payload(holder_id="old-holder", heartbeat_at=10.0)), encoding="utf-8")

    with pytest.raises(DaemonLeaseHeld, match="live conveyor lease"):
        acquire(
            "conveyor",
            "new-holder",
            state_root=root,
            ttl_seconds=30.0,
            allow_takeover=True,
            takeover_reason="operator requested takeover",
            now=1000.0,
        )

    payload = json.loads(lease_path.read_text(encoding="utf-8"))
    assert payload["holder_id"] == "old-holder"
    assert not (root / "conveyor.lease.takeovers.jsonl").exists()


def test_malformed_lease_fails_closed(tmp_path: Path):
    root = tmp_path / "leases"
    root.mkdir()
    (root / "conveyor.lease").write_text("{not json", encoding="utf-8")

    with pytest.raises(DaemonLeaseAmbiguous, match="malformed daemon lease"):
        acquire("conveyor", "holder", state_root=root, now=1000.0)


def test_missing_state_root_fails_closed(tmp_path: Path):
    with pytest.raises(DaemonLeaseAmbiguous, match="state root is missing"):
        acquire("conveyor", "holder", state_root=tmp_path / "missing", now=1000.0)


def test_release_is_idempotent(tmp_path: Path):
    root = tmp_path / "leases"
    root.mkdir()
    lease = acquire("conveyor", "holder", state_root=root, now=1000.0)

    lease.release()
    lease.release()

    assert not (root / "conveyor.lease").exists()


def test_stale_release_object_does_not_delete_newer_same_holder_lease(tmp_path: Path):
    root = tmp_path / "leases"
    root.mkdir()
    first = acquire("conveyor", "same-holder", state_root=root, now=1000.0)
    first.release()
    second = acquire("conveyor", "same-holder", state_root=root, now=1000.0)

    first.release()

    payload = json.loads((root / "conveyor.lease").read_text(encoding="utf-8"))
    assert payload["holder_id"] == "same-holder"
    assert payload["acquired_at"] == second.payload.acquired_at
    second.release()


def test_heartbeat_updates_payload_and_mtime(tmp_path: Path):
    root = tmp_path / "leases"
    root.mkdir()
    lease = acquire("conveyor", "holder", state_root=root, now=1000.0)
    try:
        lease.heartbeat(now=1010.0)

        payload = json.loads((root / "conveyor.lease").read_text(encoding="utf-8"))
        assert payload["heartbeat_at"] == 1010.0
        assert (root / "conveyor.lease").stat().st_mtime == 1010.0
    finally:
        lease.release()


def test_two_same_second_acquirers_have_exactly_one_winner(tmp_path: Path):
    root = tmp_path / "leases"
    root.mkdir()
    barrier = threading.Barrier(2)
    winners: list[str] = []
    failures: list[type[BaseException]] = []

    def contender(holder_id: str) -> None:
        barrier.wait()
        try:
            lease = acquire("conveyor", holder_id, state_root=root, now=1000.0)
        except BaseException as exc:  # noqa: BLE001 - test records the loser type
            failures.append(type(exc))
            return
        winners.append(lease.holder_id)

    threads = [threading.Thread(target=contender, args=(f"holder-{idx}",)) for idx in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(winners) == 1
    assert failures == [DaemonLeaseHeld]


def test_takeover_lock_blocks_unaudited_normal_acquire_during_audited_takeover(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path / "leases"
    root.mkdir()
    lease_path = root / "conveyor.lease"
    lease_path.write_text(
        json.dumps(_payload(holder_id="old-holder", heartbeat_at=10.0, pid=_missing_pid())),
        encoding="utf-8",
    )

    original_replace = daemon_lease._replace_lease
    takeover_paused = threading.Event()
    finish_takeover = threading.Event()
    takeover_result: list[str] = []

    def paused_replace(path, payload):
        takeover_paused.set()
        assert finish_takeover.wait(timeout=5)
        return original_replace(path, payload)

    monkeypatch.setattr(daemon_lease, "_replace_lease", paused_replace)

    def takeover() -> None:
        lease = acquire(
            "conveyor",
            "takeover-holder",
            state_root=root,
            ttl_seconds=30.0,
            allow_takeover=True,
            takeover_reason="operator audited takeover",
            now=100.0,
        )
        takeover_result.append(lease.holder_id)
        lease.release()

    thread = threading.Thread(target=takeover)
    thread.start()
    assert takeover_paused.wait(timeout=5)

    with pytest.raises(DaemonLeaseHeld, match="operation is in progress"):
        acquire("conveyor", "normal-holder", state_root=root, ttl_seconds=30.0, now=101.0)

    finish_takeover.set()
    thread.join(timeout=5)
    assert not thread.is_alive()

    assert takeover_result == ["takeover-holder"]
    records = [
        json.loads(line)
        for line in (root / "conveyor.lease.takeovers.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == 1
    assert records[0]["action"] == "daemon_lease_takeover"
    assert records[0]["new"]["holder_id"] == "takeover-holder"


def test_release_operation_lock_prevents_audited_takeover_clobber(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "leases"
    root.mkdir()
    lease = acquire("conveyor", "old-holder", state_root=root, now=10.0)

    original_unlink = daemon_lease._unlink_lease
    release_paused = threading.Event()
    finish_release = threading.Event()

    def paused_unlink(path: Path) -> None:
        release_paused.set()
        assert finish_release.wait(timeout=5)
        original_unlink(path)

    monkeypatch.setattr(daemon_lease, "_unlink_lease", paused_unlink)

    release_thread = threading.Thread(target=lease.release)
    release_thread.start()
    assert release_paused.wait(timeout=5)

    with pytest.raises(DaemonLeaseHeld, match="operation is in progress"):
        acquire(
            "conveyor",
            "takeover-holder",
            state_root=root,
            ttl_seconds=1.0,
            allow_takeover=True,
            takeover_reason="operator audited takeover",
            now=100.0,
        )

    finish_release.set()
    release_thread.join(timeout=5)
    assert not release_thread.is_alive()
    assert not (root / "conveyor.lease").exists()
    assert not (root / "conveyor.lease.takeovers.jsonl").exists()


def test_heartbeat_operation_lock_prevents_audited_takeover_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path / "leases"
    root.mkdir()
    lease = acquire("conveyor", "old-holder", state_root=root, now=10.0)

    original_replace = daemon_lease._replace_lease
    heartbeat_paused = threading.Event()
    finish_heartbeat = threading.Event()

    def paused_replace(path: Path, payload) -> None:
        heartbeat_paused.set()
        assert finish_heartbeat.wait(timeout=5)
        original_replace(path, payload)

    monkeypatch.setattr(daemon_lease, "_replace_lease", paused_replace)

    heartbeat_thread = threading.Thread(target=lease.heartbeat, kwargs={"now": 20.0})
    heartbeat_thread.start()
    assert heartbeat_paused.wait(timeout=5)

    with pytest.raises(DaemonLeaseHeld, match="operation is in progress"):
        acquire(
            "conveyor",
            "takeover-holder",
            state_root=root,
            ttl_seconds=1.0,
            allow_takeover=True,
            takeover_reason="operator audited takeover",
            now=100.0,
        )

    finish_heartbeat.set()
    heartbeat_thread.join(timeout=5)
    assert not heartbeat_thread.is_alive()
    payload = json.loads((root / "conveyor.lease").read_text(encoding="utf-8"))
    assert payload["holder_id"] == "old-holder"
    assert payload["heartbeat_at"] == 20.0
    assert not (root / "conveyor.lease.takeovers.jsonl").exists()
    lease.release()


def test_queue_daemon_launcher_holds_and_heartbeats_singleton_lease(tmp_path: Path):
    lease_root = tmp_path / "leases"
    fake_bin = tmp_path / "fake-queue-daemon"
    started = tmp_path / "started"
    stop_file = tmp_path / "stop"
    _write_fake_queue_daemon(fake_bin, marker=started, stop_file=stop_file)
    env = _queue_daemon_env(tmp_path, lease_root, fake_bin)
    script = _repo_root() / "deploy" / "queue-daemon" / "launch-queue-daemon.sh"

    proc = subprocess.Popen(
        ["bash", str(script)],
        cwd=_repo_root(),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        lease_path = lease_root / "queue-daemon.lease"
        _wait_for(lambda: started.exists() and lease_path.exists())
        first_payload = json.loads(lease_path.read_text(encoding="utf-8"))
        assert first_payload["holder_id"].startswith("queue-daemon:")

        def heartbeat_advanced() -> bool:
            payload = json.loads(lease_path.read_text(encoding="utf-8"))
            return payload["heartbeat_at"] > payload["acquired_at"]

        _wait_for(heartbeat_advanced)
        stop_file.touch()
        stdout, stderr = proc.communicate(timeout=5)
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)

    assert proc.returncode == 0, stderr
    assert stdout == ""
    assert not lease_path.exists()


def test_queue_daemon_launcher_heartbeat_failure_terminates_child_and_exits_74(tmp_path: Path):
    lease_root = tmp_path / "leases"
    fake_bin = tmp_path / "fake-queue-daemon"
    started = tmp_path / "started"
    child_terminated = tmp_path / "child-terminated"
    _write_fake_queue_daemon(fake_bin, marker=started, term_marker=child_terminated)
    env = _queue_daemon_env(tmp_path, lease_root, fake_bin)
    script = _repo_root() / "deploy" / "queue-daemon" / "launch-queue-daemon.sh"

    proc = subprocess.Popen(
        ["bash", str(script)],
        cwd=_repo_root(),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        lease_path = lease_root / "queue-daemon.lease"
        _wait_for(lambda: started.exists() and lease_path.exists())
        lease_path.unlink()
        # The launcher itself gives the child up to 10 seconds to reap after a
        # heartbeat failure.  Keep this test-local observation bounded while
        # allowing scheduler contention beyond that production contract.
        stdout, stderr = proc.communicate(timeout=15)
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)

    assert proc.returncode == 74
    assert stdout == ""
    assert "queue-daemon singleton lease heartbeat failed" in stderr
    # The launcher returned only after wait(); this child-owned TERM marker
    # therefore proves the terminated child was observed without PID reuse.
    assert child_terminated.exists()


def test_queue_daemon_launcher_refuses_live_singleton_lease_before_child_exec(tmp_path: Path):
    lease_root = tmp_path / "leases"
    lease_root.mkdir()
    held = acquire("queue-daemon", "existing-holder", state_root=lease_root, now=1000.0)
    fake_bin = tmp_path / "fake-queue-daemon"
    marker = tmp_path / "should-not-run"
    _write_fake_queue_daemon(fake_bin, marker=marker)
    env = _queue_daemon_env(tmp_path, lease_root, fake_bin)
    env["CE_DAEMON_LEASE_TAKEOVER_REASON"] = "operator requested takeover"
    script = _repo_root() / "deploy" / "queue-daemon" / "launch-queue-daemon.sh"

    try:
        proc = subprocess.run(
            ["bash", str(script)],
            cwd=_repo_root(),
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    finally:
        held.release()

    assert proc.returncode == 73
    assert "queue-daemon singleton lease refused" in proc.stderr
    assert not marker.exists()
    assert not (lease_root / "queue-daemon.lease.takeovers.jsonl").exists()


def test_queue_daemon_launcher_sigterm_forwards_once_and_releases_lease(tmp_path: Path):
    lease_root = tmp_path / "leases"
    fake_bin = tmp_path / "fake-queue-daemon"
    started = tmp_path / "started"
    child_pid_file = tmp_path / "child.pid"
    term_marker = tmp_path / "child-saw-term"
    _write_fake_queue_daemon(
        fake_bin,
        marker=started,
        pid_file=child_pid_file,
        term_marker=term_marker,
    )
    env = _queue_daemon_env(tmp_path, lease_root, fake_bin)
    script = _repo_root() / "deploy" / "queue-daemon" / "launch-queue-daemon.sh"

    proc = subprocess.Popen(
        ["bash", str(script)],
        cwd=_repo_root(),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        lease_path = lease_root / "queue-daemon.lease"
        _wait_for(lambda: started.exists() and child_pid_file.exists() and lease_path.exists())
        child_pid = int(child_pid_file.read_text(encoding="utf-8"))
        proc.terminate()
        stdout, stderr = proc.communicate(timeout=5)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)

    assert proc.returncode == 0, stderr
    assert stdout == ""
    assert term_marker.exists()
    assert not lease_path.exists()
    with pytest.raises(ProcessLookupError):
        os.kill(child_pid, 0)


def test_queue_daemon_launcher_recovers_only_same_host_dead_pid_with_fixed_audit_reason(tmp_path: Path):
    lease_root = tmp_path / "leases"
    lease_root.mkdir()
    lease_path = lease_root / "queue-daemon.lease"
    lease_path.write_text(
        json.dumps(_payload(holder_id="old-queue", heartbeat_at=time.time(), pid=_missing_pid())),
        encoding="utf-8",
    )
    fake_bin = tmp_path / "fake-queue-daemon"
    started = tmp_path / "started"
    stop_file = tmp_path / "stop"
    _write_fake_queue_daemon(fake_bin, marker=started, stop_file=stop_file)
    env = _queue_daemon_env(tmp_path, lease_root, fake_bin)
    env["CE_DAEMON_LEASE_TAKEOVER_REASON"] = "operator supplied reason must be ignored"
    script = _repo_root() / "deploy" / "queue-daemon" / "launch-queue-daemon.sh"

    proc = subprocess.Popen(
        ["bash", str(script)],
        cwd=_repo_root(),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for(lambda: started.exists())
        records = [
            json.loads(line)
            for line in (lease_root / "queue-daemon.lease.takeovers.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        stop_file.touch()
        stdout, stderr = proc.communicate(timeout=5)
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)

    assert proc.returncode == 0, stderr
    assert stdout == ""
    assert [record["reason"] for record in records] == [
        "automatic queue-daemon same-host dead-pid recovery"
    ]


@pytest.mark.parametrize(
    ("case", "payload", "kill_error"),
    [
        ("malformed-payload", "{not json", None),
        (
            "missing-pid",
            {
                "holder_id": "old-queue",
                "host": socket.gethostname(),
                "acquired_at": 0.0,
                "heartbeat_at": 0.0,
            },
            None,
        ),
        ("non-positive-pid", _payload(holder_id="old-queue", heartbeat_at=0.0, pid=0), None),
        ("boolean-pid", _payload(holder_id="old-queue", heartbeat_at=0.0, pid=True), None),
        ("non-integer-pid", _payload(holder_id="old-queue", heartbeat_at=0.0, pid="not-a-pid"), None),
        (
            "permission-error",
            _payload(holder_id="old-queue", heartbeat_at=0.0, pid=424_242),
            "PermissionError()",
        ),
        (
            "ambiguous-oserror",
            _payload(holder_id="old-queue", heartbeat_at=0.0, pid=424_243),
            "OSError(5, 'I/O error')",
        ),
    ],
)
def test_queue_daemon_launcher_refuses_ineligible_automatic_recovery_without_mutating_lease(
    tmp_path: Path,
    case: str,
    payload: str | dict[str, object],
    kill_error: str | None,
):
    lease_root = tmp_path / "leases"
    lease_root.mkdir()
    lease_path = lease_root / "queue-daemon.lease"
    raw_payload = payload if isinstance(payload, str) else json.dumps(payload)
    lease_path.write_text(raw_payload, encoding="utf-8")
    fake_bin = tmp_path / "fake-queue-daemon"
    marker = tmp_path / "should-not-run"
    _write_fake_queue_daemon(fake_bin, marker=marker)
    env = _queue_daemon_env(tmp_path, lease_root, fake_bin)
    if kill_error is not None:
        hook_dir = tmp_path / "hook"
        hook_dir.mkdir()
        assert isinstance(payload, dict)
        _write_os_kill_error_hook(
            hook_dir / "sitecustomize.py",
            pid=payload["pid"],
            error=kill_error,
        )
        env["PYTHONPATH"] = f"{hook_dir}{os.pathsep}{_repo_root() / 'validators'}"
    script = _repo_root() / "deploy" / "queue-daemon" / "launch-queue-daemon.sh"

    proc = subprocess.run(
        ["bash", str(script)],
        cwd=_repo_root(),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert proc.returncode == 73, case
    assert "queue-daemon singleton lease refused" in proc.stderr
    assert not marker.exists()
    assert lease_path.read_text(encoding="utf-8") == raw_payload
    assert not (lease_root / "queue-daemon.lease.takeovers.jsonl").exists()


def test_queue_daemon_launcher_refuses_cross_host_stale_lease_even_with_operator_reason(tmp_path: Path):
    lease_root = tmp_path / "leases"
    lease_root.mkdir()
    lease_path = lease_root / "queue-daemon.lease"
    payload = _payload(holder_id="remote-queue", heartbeat_at=0.0, pid=_missing_pid())
    payload["host"] = "different-host.invalid"
    lease_path.write_text(json.dumps(payload), encoding="utf-8")
    fake_bin = tmp_path / "fake-queue-daemon"
    marker = tmp_path / "should-not-run"
    _write_fake_queue_daemon(fake_bin, marker=marker)
    env = _queue_daemon_env(tmp_path, lease_root, fake_bin)
    env["CE_DAEMON_LEASE_TAKEOVER_REASON"] = "operator requested cross-host takeover"
    script = _repo_root() / "deploy" / "queue-daemon" / "launch-queue-daemon.sh"

    proc = subprocess.run(
        ["bash", str(script)],
        cwd=_repo_root(),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert proc.returncode == 73
    assert "queue-daemon singleton lease refused" in proc.stderr
    assert not marker.exists()
    assert not (lease_root / "queue-daemon.lease.takeovers.jsonl").exists()


def test_queue_daemon_launcher_refuses_replaced_lease_after_dead_pid_recovery_check(tmp_path: Path):
    lease_root = tmp_path / "leases"
    lease_root.mkdir()
    lease_path = lease_root / "queue-daemon.lease"
    lease_path.write_text(
        json.dumps(_payload(holder_id="old-local", heartbeat_at=0.0, pid=_missing_pid())),
        encoding="utf-8",
    )
    hook_dir = tmp_path / "hook"
    hook_dir.mkdir()
    replacement = _payload(holder_id="replaced-remote", heartbeat_at=0.0, pid=_missing_pid())
    replacement["host"] = "different-host.invalid"
    _write_lease_replacement_race_hook(
        hook_dir / "sitecustomize.py",
        lease_path=lease_path,
        replacement_payload=replacement,
    )
    fake_bin = tmp_path / "fake-queue-daemon"
    marker = tmp_path / "should-not-run"
    _write_fake_queue_daemon(fake_bin, marker=marker)
    env = _queue_daemon_env(tmp_path, lease_root, fake_bin)
    env["PYTHONPATH"] = f"{hook_dir}{os.pathsep}{_repo_root() / 'validators'}"
    script = _repo_root() / "deploy" / "queue-daemon" / "launch-queue-daemon.sh"

    proc = subprocess.run(
        ["bash", str(script)],
        cwd=_repo_root(),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert proc.returncode == 73
    assert "queue-daemon singleton lease refused" in proc.stderr
    assert not marker.exists()
    assert not (lease_root / "queue-daemon.lease.takeovers.jsonl").exists()
    assert json.loads(lease_path.read_text(encoding="utf-8"))["host"] == "different-host.invalid"


def test_container_runner_maps_host_lease_root_to_container_state_mount(tmp_path: Path):
    fake_engine = tmp_path / "fake-engine"
    argv_file = tmp_path / "engine-argv.txt"
    _write_fake_container_engine(fake_engine, argv_file)
    host_state = tmp_path / "state"
    host_lease = host_state / "daemon-leases"
    env = os.environ.copy()
    env.update(
        {
            "CE_CONTAINER_ENGINE": str(fake_engine),
            "CE_DAEMON_REPO_ROOT": str(_repo_root()),
            "CE_DAEMON_STATE_ROOT": str(host_state),
            "CE_DAEMON_LEASE_ROOT": str(host_lease),
            "CE_DAEMON_IMAGE": "example.invalid/ce-runtime@sha256:abc",
        }
    )

    proc = subprocess.run(
        ["bash", str(_repo_root() / "deploy" / "daemons" / "run-daemon-container.sh"), "queue-daemon"],
        cwd=_repo_root(),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert proc.returncode == 0, proc.stderr
    argv = argv_file.read_text(encoding="utf-8").splitlines()
    assert "--env" in argv
    assert "CE_DAEMON_LEASE_ROOT=/ce/state/daemon-leases" in argv
    assert str(host_lease) not in argv


def test_container_runner_forwards_liveness_state_path_without_log_directory(tmp_path: Path):
    fake_engine = tmp_path / "fake-engine"
    argv_file = tmp_path / "engine-argv.txt"
    _write_fake_container_engine(fake_engine, argv_file)
    env = _container_runner_env(tmp_path, fake_engine)
    env["CE_DAEMON_LIVENESS_STATE_PATH"] = "/ce/state/queue-daemon/liveness-state.json"

    proc = _run_container_runner("queue-daemon", env)

    assert proc.returncode == 0, proc.stderr
    argv = argv_file.read_text(encoding="utf-8").splitlines()
    assert "CE_DAEMON_LIVENESS_STATE_PATH" in argv
    assert "CE_DAEMON_LOG_DIR" not in argv


def test_queue_daemon_iac_declares_liveness_without_log_directory():
    root = _repo_root() / "deploy" / "queue-daemon"
    declared_topology = "\n".join(
        (root / name).read_text(encoding="utf-8")
        for name in ("ce-queue-daemon.service", "ce-queue-daemon.env.template", "RELOCATION.md")
    )

    assert "CE_DAEMON_LIVENESS_STATE_PATH" in declared_topology
    assert "CE_DAEMON_LOG_DIR" not in declared_topology


def test_container_runner_rejects_env_file_without_0600_mode(tmp_path: Path):
    fake_engine = tmp_path / "fake-engine"
    argv_file = tmp_path / "engine-argv.txt"
    _write_fake_container_engine(fake_engine, argv_file)
    env_file = tmp_path / "daemon.env"
    env_file.write_text("GH_TOKEN=from-env-file\n", encoding="utf-8")
    env_file.chmod(0o644)
    env = _container_runner_env(tmp_path, fake_engine)
    env["CE_DAEMON_ENV_FILE"] = str(env_file)

    proc = _run_container_runner("queue-daemon", env)

    assert proc.returncode != 0
    assert "CE_DAEMON_ENV_FILE must be mode 0600" in proc.stderr
    assert not argv_file.exists()


def test_container_runner_refuses_missing_env_file_before_container_invocation(tmp_path: Path):
    fake_engine = tmp_path / "fake-engine"
    argv_file = tmp_path / "engine-argv.txt"
    _write_fake_container_engine(fake_engine, argv_file)
    missing_env_file = tmp_path / "missing-daemon.env"
    env = _container_runner_env(tmp_path, fake_engine)
    env["CE_DAEMON_ENV_FILE"] = str(missing_env_file)

    proc = _run_container_runner("queue-daemon", env)

    assert proc.returncode != 0
    assert proc.stdout == ""
    assert proc.stderr == f"ERROR: CE_DAEMON_ENV_FILE does not name a file: {missing_env_file}\n"
    assert not argv_file.exists()


def test_container_runner_passes_env_file_before_explicit_env(tmp_path: Path):
    fake_engine = tmp_path / "fake-engine"
    argv_file = tmp_path / "engine-argv.txt"
    _write_fake_container_engine(fake_engine, argv_file)
    env_file = tmp_path / "daemon.env"
    env_file.write_text("GH_TOKEN=from-env-file\n", encoding="utf-8")
    env_file.chmod(0o600)
    env = _container_runner_env(tmp_path, fake_engine)
    env.update({"CE_DAEMON_ENV_FILE": str(env_file), "GH_TOKEN": "explicit-token"})

    proc = _run_container_runner("queue-daemon", env)

    assert proc.returncode == 0, proc.stderr
    argv = argv_file.read_text(encoding="utf-8").splitlines()
    assert argv[argv.index("--env-file") + 1] == str(env_file)
    assert argv.index("--env-file") < argv.index("GH_TOKEN")


def test_container_runner_maps_cacert_file_to_container_bao_cacert(tmp_path: Path):
    fake_engine = tmp_path / "fake-engine"
    argv_file = tmp_path / "engine-argv.txt"
    _write_fake_container_engine(fake_engine, argv_file)
    cacert_file = tmp_path / "openbao-ca.crt"
    cacert_file.write_text("unit-test-ca\n", encoding="utf-8")
    env = _container_runner_env(tmp_path, fake_engine)
    env.update(
        {
            "BAO_CACERT": "/usr/local/share/ca-certificates/host-only.crt",
            "CE_DAEMON_CACERT_FILE": str(cacert_file),
        }
    )

    proc = _run_container_runner("queue-daemon", env)

    assert proc.returncode == 0, proc.stderr
    argv = argv_file.read_text(encoding="utf-8").splitlines()
    assert f"{cacert_file}:/ce/etc/openbao-ca.crt:ro" in argv
    assert "BAO_CACERT=/ce/etc/openbao-ca.crt" in argv
    assert "BAO_CACERT" not in argv
    assert "/usr/local/share/ca-certificates/host-only.crt" not in argv


def test_container_runner_refuses_missing_cacert_file_before_container_invocation(tmp_path: Path):
    fake_engine = tmp_path / "fake-engine"
    argv_file = tmp_path / "engine-argv.txt"
    _write_fake_container_engine(fake_engine, argv_file)
    missing_cacert_file = tmp_path / "missing-openbao-ca.crt"
    env = _container_runner_env(tmp_path, fake_engine)
    env["CE_DAEMON_CACERT_FILE"] = str(missing_cacert_file)

    proc = _run_container_runner("queue-daemon", env)

    assert proc.returncode != 0
    assert proc.stdout == ""
    assert proc.stderr == f"ERROR: CE_DAEMON_CACERT_FILE does not name a file: {missing_cacert_file}\n"
    assert not argv_file.exists()


def test_container_runner_uses_tmpfs_for_queue_secret_target_when_host_sets_target(tmp_path: Path):
    fake_engine = tmp_path / "fake-engine"
    argv_file = tmp_path / "engine-argv.txt"
    _write_fake_container_engine(fake_engine, argv_file)
    host_secret_target = tmp_path / "run" / "approval-wall-secret"
    env = _container_runner_env(tmp_path, fake_engine)
    env["CE_APPROVAL_WALL_SECRET_TARGET_FILE"] = str(host_secret_target)

    proc = _run_container_runner("queue-daemon", env)

    assert proc.returncode == 0, proc.stderr
    argv = argv_file.read_text(encoding="utf-8").splitlines()
    assert "--tmpfs" in argv
    assert "/ce/state/queue-daemon-secret:rw,size=1m,mode=0700,uid=10001,gid=10001" in argv
    assert "CE_APPROVAL_WALL_SECRET_TARGET_FILE=/ce/state/queue-daemon-secret/approval-wall-secret" in argv
    assert str(host_secret_target) not in argv


def test_container_runner_creates_missing_state_and_lease_roots(tmp_path: Path):
    fake_engine = tmp_path / "fake-engine"
    argv_file = tmp_path / "engine-argv.txt"
    _write_fake_container_engine(fake_engine, argv_file)
    env = _container_runner_env(tmp_path, fake_engine)
    state_root = tmp_path / "state"
    lease_root = state_root / "daemon-leases"

    proc = _run_container_runner("queue-daemon", env)

    assert proc.returncode == 0, proc.stderr
    assert state_root.is_dir()
    assert lease_root.is_dir()
    assert oct(state_root.stat().st_mode & 0o777) == "0o700"
    assert oct(lease_root.stat().st_mode & 0o777) == "0o700"


@pytest.mark.skipif(os.getuid() == 0, reason="mixed-uid inaccessible-root simulation is for non-root callers")
def test_container_runner_defers_lease_root_prep_for_preowned_mixed_uid_docker_state_root(tmp_path: Path):
    fake_docker = tmp_path / "docker"
    argv_file = tmp_path / "engine-argv.txt"
    _write_fake_container_engine(fake_docker, argv_file)
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700)
    state_root.chmod(0)
    image_uid = os.getuid() + 1
    fake_stat = tmp_path / "stat"
    _write_fake_stat_for_preowned_state(fake_stat, state_root=state_root, owner_uid=image_uid)
    env = _container_runner_env(tmp_path, fake_docker)
    env.update(
        {
            "PATH": f"{tmp_path}:{os.environ.get('PATH', '')}",
            "CE_DAEMON_IMAGE_UID": str(image_uid),
            "CE_DAEMON_STATE_ROOT": str(state_root),
            "CE_DAEMON_LEASE_ROOT": str(state_root / "daemon-leases"),
        }
    )

    try:
        proc = _run_container_runner("queue-daemon", env)
    finally:
        state_root.chmod(0o700)

    assert proc.returncode == 0, proc.stderr
    argv = argv_file.read_text(encoding="utf-8").splitlines()
    assert "run" in argv
    assert f"{state_root}:/ce/state" in argv


@pytest.mark.skipif(os.getuid() == 0, reason="non-root Docker creation branch is not exercised as root")
def test_container_runner_creates_missing_docker_roots_for_non_root_caller_when_uid_matches(tmp_path: Path):
    fake_docker = tmp_path / "docker"
    argv_file = tmp_path / "engine-argv.txt"
    _write_fake_container_engine(fake_docker, argv_file)
    env = _container_runner_env(tmp_path, fake_docker)
    env["CE_DAEMON_IMAGE_UID"] = str(os.getuid())
    state_root = tmp_path / "state"
    lease_root = state_root / "daemon-leases"

    proc = _run_container_runner("queue-daemon", env)

    assert proc.returncode == 0, proc.stderr
    assert state_root.is_dir()
    assert lease_root.is_dir()
    assert state_root.stat().st_uid == os.getuid()
    assert lease_root.stat().st_uid == os.getuid()
    assert oct(state_root.stat().st_mode & 0o777) == "0o700"
    assert oct(lease_root.stat().st_mode & 0o777) == "0o700"
    assert argv_file.exists()


@pytest.mark.skipif(os.getuid() == 0, reason="non-root Docker creation branch is not exercised as root")
def test_container_runner_refuses_freshly_created_docker_state_root_when_uid_mismatches(tmp_path: Path):
    fake_docker = tmp_path / "docker"
    argv_file = tmp_path / "engine-argv.txt"
    _write_fake_container_engine(fake_docker, argv_file)
    env = _container_runner_env(tmp_path, fake_docker)
    wrong_uid = os.getuid() + 1
    env["CE_DAEMON_IMAGE_UID"] = str(wrong_uid)
    state_root = tmp_path / "state"

    proc = _run_container_runner("queue-daemon", env)

    assert proc.returncode != 0
    assert proc.stdout == ""
    assert "CE_DAEMON_STATE_ROOT owner uid" in proc.stderr
    assert f"Run: chown -R {wrong_uid}:{wrong_uid} {state_root}" in proc.stderr
    assert not argv_file.exists()
    # The state root did not exist before this run. The non-root caller
    # cannot chown it to the mismatched image uid, so install -d's chown
    # attempt fails and falls back to creating the directory without
    # ownership changes -- it ends up owned by the caller, not the image
    # uid, and first-boot creation must not silently paper over that with a
    # false pass.
    assert state_root.is_dir()
    assert state_root.stat().st_uid == os.getuid()


def test_container_runner_refuses_docker_state_root_with_wrong_owner(tmp_path: Path):
    fake_docker = tmp_path / "docker"
    argv_file = tmp_path / "engine-argv.txt"
    _write_fake_container_engine(fake_docker, argv_file)
    state_root = tmp_path / "state"
    state_root.mkdir(mode=0o700)
    state_root.chmod(0o700)
    wrong_uid = os.getuid() + 1
    env = _container_runner_env(tmp_path, fake_docker)
    env["CE_DAEMON_IMAGE_UID"] = str(wrong_uid)

    proc = _run_container_runner("queue-daemon", env)

    assert proc.returncode != 0
    assert proc.stdout == ""
    assert "CE_DAEMON_STATE_ROOT owner uid" in proc.stderr
    assert f"Run: chown -R {wrong_uid}:{wrong_uid} {state_root}" in proc.stderr
    assert not argv_file.exists()


def test_container_runner_keeps_queue_default_invocation_byte_identical(tmp_path: Path):
    fake_engine = tmp_path / "fake-engine"
    argv_file = tmp_path / "engine-argv.txt"
    _write_fake_container_engine(fake_engine, argv_file)
    env = _container_runner_env(tmp_path, fake_engine)
    repo_root = _repo_root()
    state_root = tmp_path / "state"

    proc = _run_container_runner("queue-daemon", env)

    assert proc.returncode == 0, proc.stderr
    assert argv_file.read_text(encoding="utf-8") == "\n".join(
        [
            "run",
            "--rm",
            "--name",
            "ce-queue-daemon",
            "--workdir",
            "/workspace/creator-engine",
            "--user",
            "10001:10001",
            "--volume",
            f"{repo_root}:/workspace/creator-engine:ro",
            "--volume",
            f"{state_root}:/ce/state",
            "--env",
            "CE_DAEMON_UNCONTAINED=1",
            "--env",
            "CE_DAEMON_STATE_ROOT=/ce/state",
            "--env",
            "CE_DAEMON_LEASE_ROOT=/ce/state/daemon-leases",
            "--env",
            "CE_QUEUE_DAEMON_BIN=cev3",
            "--env",
            "CE_QUEUE_DAEMON_REPO_ROOT=/workspace/creator-engine",
            "--env",
            "CE_QUEUE_DAEMON_ROOT=/ce/state/queue-daemon/v3",
            "--env",
            "CE_APPROVAL_WALL_SECRET_TARGET_FILE=/ce/state/queue-daemon/approval-wall-secret",
            "--env",
            "CE_APPROVAL_WALL_STATE=/ce/state/queue-daemon/approval-wall-state.json",
            "example.invalid/ce-runtime@sha256:abc",
            "bash",
            "/workspace/creator-engine/deploy/queue-daemon/launch-queue-daemon.sh",
        ]
    ) + "\n"


def test_container_runner_default_image_uses_canonical_runtime_name(tmp_path: Path):
    fake_engine = tmp_path / "fake-engine"
    argv_file = tmp_path / "engine-argv.txt"
    _write_fake_container_engine(fake_engine, argv_file)
    env = _container_runner_env(tmp_path, fake_engine)
    env.pop("CE_DAEMON_IMAGE")

    proc = _run_container_runner("queue-daemon", env)

    assert proc.returncode == 0, proc.stderr
    argv = argv_file.read_text(encoding="utf-8").splitlines()
    assert "ghcr.io/creator-engine/creator-engine/ce-runtime:0.3.6" in argv


def test_container_runner_writes_per_attempt_logs_and_latest_symlink(tmp_path: Path):
    fake_engine = tmp_path / "fake-engine"
    argv_file = tmp_path / "engine-argv.txt"
    _write_fake_container_engine_with_output(fake_engine, argv_file)
    env = _container_runner_env(tmp_path, fake_engine)
    log_dir = tmp_path / "attempt-logs"
    env["CE_DAEMON_LOG_DIR"] = str(log_dir)

    first = _run_container_runner("queue-daemon", env)
    second = _run_container_runner("queue-daemon", env)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    logs = sorted(log_dir.glob("ce-wall-daemon-container-queue-daemon-*.log"))
    assert len(logs) == 2
    assert all("fake engine stdout" in path.read_text(encoding="utf-8") for path in logs)
    latest = log_dir / "ce-wall-daemon-container.log"
    assert latest.is_symlink()
    assert latest.resolve() == logs[-1].resolve()


def test_container_runner_keeps_conveyor_default_invocation_byte_identical(tmp_path: Path):
    fake_engine = tmp_path / "fake-engine"
    argv_file = tmp_path / "engine-argv.txt"
    _write_fake_container_engine(fake_engine, argv_file)
    env = _container_runner_env(tmp_path, fake_engine)
    repo_root = _repo_root()
    state_root = tmp_path / "state"

    proc = _run_container_runner("conveyor-daemon", env)

    assert proc.returncode == 0, proc.stderr
    assert argv_file.read_text(encoding="utf-8") == "\n".join(
        [
            "run",
            "--rm",
            "--name",
            "ce-conveyor-daemon",
            "--workdir",
            "/workspace/creator-engine",
            "--user",
            "10001:10001",
            "--volume",
            f"{repo_root}:/workspace/creator-engine:ro",
            "--volume",
            f"{state_root}:/ce/state",
            "--env",
            "CE_DAEMON_UNCONTAINED=1",
            "--env",
            "CE_DAEMON_STATE_ROOT=/ce/state",
            "--env",
            "CE_DAEMON_LEASE_ROOT=/ce/state/daemon-leases",
            "--env",
            "CE_QUEUE_DAEMON_BIN=cev3",
            "--env",
            "CE_QUEUE_DAEMON_REPO_ROOT=/workspace/creator-engine",
            "--env",
            "CE_QUEUE_DAEMON_ROOT=/ce/state/queue-daemon/v3",
            "--env",
            "CE_APPROVAL_WALL_SECRET_TARGET_FILE=/ce/state/queue-daemon/approval-wall-secret",
            "--env",
            "CE_APPROVAL_WALL_STATE=/ce/state/queue-daemon/approval-wall-state.json",
            "--env",
            "CE_CONVEYOR_DAEMON_REPO_ROOT=/workspace/creator-engine",
            "--env",
            "CE_CONVEYOR_DAEMON_RUNTIME_ROOT=/ce/state/conveyor-daemon/runtime",
            "--env",
            "CE_CONVEYOR_DAEMON_DISCOVERY_STATE=/ce/state/conveyor-daemon/discovery-state.json",
            "--env",
            "CE_CONVEYOR_DAEMON_LEDGER_PATH=/ce/state/conveyor-daemon/conveyor-daemon-ledger.jsonl",
            "--env",
            "CE_CONVEYOR_DAEMON_VALIDATION_LEDGER_ROOT=/ce/state/conveyor-daemon/side-effect-ledger",
            "--env",
            "CE_CONVEYOR_DAEMON_ACTIVE_WORK_LEDGER_ROOT=/ce/state/conveyor-daemon/active-work-ledger",
            "example.invalid/ce-runtime@sha256:abc",
            "bash",
            "/workspace/creator-engine/deploy/conveyor-daemon/launch-conveyor-daemon.sh",
        ]
    ) + "\n"


def test_container_runner_uses_tmpfs_for_conveyor_secret_file_mount(tmp_path: Path):
    fake_engine = tmp_path / "fake-engine"
    argv_file = tmp_path / "engine-argv.txt"
    _write_fake_container_engine(fake_engine, argv_file)
    signing_secret_file = tmp_path / "signing-secret"
    signing_secret_file.write_text("unit-test-secret\n", encoding="utf-8")
    env = _container_runner_env(tmp_path, fake_engine)
    env["CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE"] = str(signing_secret_file)

    proc = _run_container_runner("conveyor-daemon", env)

    assert proc.returncode == 0, proc.stderr
    argv = argv_file.read_text(encoding="utf-8").splitlines()
    assert "/run/creator-engine/conveyor-daemon-secret:rw,size=1m,mode=0700,uid=10001,gid=10001" in argv
    assert f"{signing_secret_file}:/run/creator-engine/conveyor-daemon-secret/signing-secret:ro" in argv
    assert "CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE=/run/creator-engine/conveyor-daemon-secret/signing-secret" in argv


def test_container_runner_refuses_unmounted_host_lease_root(tmp_path: Path):
    fake_engine = tmp_path / "fake-engine"
    argv_file = tmp_path / "engine-argv.txt"
    _write_fake_container_engine(fake_engine, argv_file)
    env = os.environ.copy()
    env.update(
        {
            "CE_CONTAINER_ENGINE": str(fake_engine),
            "CE_DAEMON_REPO_ROOT": str(_repo_root()),
            "CE_DAEMON_STATE_ROOT": str(tmp_path / "state"),
            "CE_DAEMON_LEASE_ROOT": str(tmp_path / "outside-leases"),
        }
    )

    proc = subprocess.run(
        ["bash", str(_repo_root() / "deploy" / "daemons" / "run-daemon-container.sh"), "queue-daemon"],
        cwd=_repo_root(),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert proc.returncode != 0
    assert "CE_DAEMON_LEASE_ROOT must be under CE_DAEMON_STATE_ROOT" in proc.stderr
    assert not argv_file.exists()
