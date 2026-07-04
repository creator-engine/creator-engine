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


def _payload(*, holder_id: str, heartbeat_at: float) -> dict[str, object]:
    return {
        "holder_id": holder_id,
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "acquired_at": heartbeat_at,
        "heartbeat_at": heartbeat_at,
    }


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


def _write_fake_queue_daemon(path: Path, *, marker: Path, stop_file: Path | None = None) -> None:
    wait_block = ""
    if stop_file is not None:
        wait_block = f'while [ ! -e "{stop_file}" ]; do sleep 0.02; done\n'
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f'touch "{marker}"\n'
        f"{wait_block}",
        encoding="utf-8",
    )
    path.chmod(0o755)


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
    lease_path.write_text(json.dumps(_payload(holder_id="old-holder", heartbeat_at=10.0)), encoding="utf-8")

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
    lease_path.write_text(json.dumps(_payload(holder_id="old-holder", heartbeat_at=10.0)), encoding="utf-8")

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


def test_queue_daemon_launcher_refuses_live_singleton_lease_before_child_exec(tmp_path: Path):
    lease_root = tmp_path / "leases"
    lease_root.mkdir()
    held = acquire("queue-daemon", "existing-holder", state_root=lease_root, now=1000.0)
    fake_bin = tmp_path / "fake-queue-daemon"
    marker = tmp_path / "should-not-run"
    _write_fake_queue_daemon(fake_bin, marker=marker)
    env = _queue_daemon_env(tmp_path, lease_root, fake_bin)
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
