"""Optional live herdr binary probes for ce-ops#217 U3."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from creator_engine_validator.runner.herdr_session import (
    HERDR_SOCKET_ENV,
    SubprocessHerdrCommandRunner,
)


HERDR_LIVE_BINARY = Path(
    os.environ.get("HERDR_LIVE_BINARY", "/tmp/herdr-share/target/release/herdr")
)


@pytest.mark.skipif(
    not HERDR_LIVE_BINARY.is_file(),
    reason=(
        "live herdr binary is unavailable; set HERDR_LIVE_BINARY or stage "
        "/tmp/herdr-share/target/release/herdr"
    ),
)
def test_live_herdr_binary_can_be_invoked_safely():
    runner = SubprocessHerdrCommandRunner(timeout_seconds=5)
    completed = runner.run([str(HERDR_LIVE_BINARY), "--help"])
    assert completed.returncode == 0


@pytest.mark.skipif(
    not HERDR_LIVE_BINARY.is_file(),
    reason=(
        "live herdr binary is unavailable; set HERDR_LIVE_BINARY or stage "
        "/tmp/herdr-share/target/release/herdr"
    ),
)
def test_live_herdr_workspace_run_read_and_send_text_cli_shapes_reach_socket_layer(tmp_path):
    """Exercise real CLI argument parsing without requiring a persistent server.

    The task environment does not provide a deterministic herdr server lifecycle
    harness for CE tests. A missing socket keeps this opt-in probe hermetic: if
    the command shapes are accepted, herdr fails at socket connection; if CE's
    argv drifts, it fails earlier as usage/argument parsing.
    """

    runner = SubprocessHerdrCommandRunner(timeout_seconds=5)
    socket_path = tmp_path / "missing-herdr.sock"
    env = {HERDR_SOCKET_ENV: str(socket_path)}

    create = runner.run(
        [
            str(HERDR_LIVE_BINARY),
            "workspace",
            "create",
            "--cwd",
            str(tmp_path),
            "--label",
            "ce-live-shape",
            "--env",
            "CE_LEDGER_ROOT=/ledger",
        ],
        env=env,
    )
    assert create.returncode == 1
    assert "No such file or directory" in create.stderr
    assert "usage: herdr workspace create" not in create.stderr
    assert "--json" not in create.stderr

    run = runner.run(
        [str(HERDR_LIVE_BINARY), "pane", "run", "pane-1", "printf hello"],
        env=env,
    )
    assert run.returncode == 1
    assert "No such file or directory" in run.stderr
    assert "usage: herdr pane run" not in run.stderr
    assert "--cwd" not in run.stderr
    assert "--env" not in run.stderr

    read = runner.run(
        [
            str(HERDR_LIVE_BINARY),
            "pane",
            "read",
            "pane-1",
            "--source",
            "recent",
            "--lines",
            "1",
            "--format",
            "text",
        ],
        env=env,
    )
    assert read.returncode == 1
    assert "No such file or directory" in read.stderr
    assert "usage: herdr pane read" not in read.stderr
    assert "invalid read format" not in read.stderr

    send = runner.run(
        [str(HERDR_LIVE_BINARY), "pane", "send-text", "pane-1", "hello"],
        env=env,
    )
    assert send.returncode == 1
    assert "No such file or directory" in send.stderr
    assert "usage: herdr pane send-text" not in send.stderr
