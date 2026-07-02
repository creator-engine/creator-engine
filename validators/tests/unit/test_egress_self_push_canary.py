"""Tests for the contained-seat self-push smoke canary."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "tools" / "egress-broker" / "ce_self_push_canary.py"


def _serve_once(socket_path: Path, response: dict[str, object]) -> threading.Thread:
    ready = threading.Event()

    def run() -> None:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(socket_path))
            server.listen(1)
            ready.set()
            conn, _addr = server.accept()
            with conn:
                conn.recv(65536)
                conn.sendall((json.dumps(response, separators=(",", ":")) + "\n").encode("utf-8"))

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    assert ready.wait(timeout=5)
    return thread


def test_canary_passes_on_applied_noop_response(tmp_path: Path) -> None:
    socket_path = tmp_path / "dev-3.sock"
    thread = _serve_once(
        socket_path,
        {
            "status": 200,
            "seat_id": "dev-3",
            "branch": "ce-smoke",
            "applied": True,
            "pushed": False,
            "pr_number": 123,
        },
    )

    result = subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "--socket",
            str(socket_path),
            "--seat",
            "dev-3",
            "--branch",
            "ce-smoke",
            "--require-noop",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    thread.join(timeout=5)

    assert result.returncode == 0, result.stderr
    assert "SELF-PUSH CANARY PASS seat=dev-3 branch=ce-smoke applied=True pushed=False" in result.stdout


def test_canary_fails_loudly_when_socket_is_stale_or_down(tmp_path: Path) -> None:
    socket_path = tmp_path / "stale.sock"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stale:
        stale.bind(str(socket_path))

    result = subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "--socket",
            str(socket_path),
            "--seat",
            "dev-3",
            "--branch",
            "ce-smoke",
            "--timeout",
            "0.2",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 3
    assert "self-push canary FAIL: could not talk to broker socket" in result.stderr


def test_canary_reports_broker_refusal(tmp_path: Path) -> None:
    socket_path = tmp_path / "dev-3.sock"
    thread = _serve_once(socket_path, {"status": 403, "reason": "egress_refused"})

    result = subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "--socket",
            str(socket_path),
            "--seat",
            "dev-3",
            "--branch",
            "ce-smoke",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    thread.join(timeout=5)

    assert result.returncode == 4
    assert "self-push canary FAIL: broker refused request" in result.stderr


def test_canary_defaults_to_contained_environment(tmp_path: Path) -> None:
    socket_path = tmp_path / "dev-3.sock"
    thread = _serve_once(
        socket_path,
        {"status": 200, "seat_id": "dev-3", "branch": "ce-smoke", "applied": True, "pushed": False},
    )
    env = {
        **os.environ,
        "CE_EGRESS_BROKER_SOCKET": str(socket_path),
        "CE_SEAT_ID": "dev-3",
    }

    result = subprocess.run(
        ["python3", str(SCRIPT), "--branch", "ce-smoke"],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    thread.join(timeout=5)

    assert result.returncode == 0, result.stderr
    assert "SELF-PUSH CANARY PASS" in result.stdout
