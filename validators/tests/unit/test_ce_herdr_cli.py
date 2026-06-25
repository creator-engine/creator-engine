"""Unit tests for the ``ce herdr`` reach-plane CLI."""

from __future__ import annotations

import json
import subprocess

from creator_engine_validator import ce_cli
from creator_engine_validator.runner import herdr_session as hs


class FakeAttachRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], dict[str, str]]] = []

    def run(self, argv, *, env=None):
        self.calls.append((list(argv), dict(env or {})))
        return subprocess.CompletedProcess(list(argv), 0, "", "")


def test_herdr_remote_attach_dry_run_json_emits_exact_herdr_remote_command(capsys) -> None:
    rc = ce_cli.main(
        [
            "herdr",
            "remote-attach",
            "--remote",
            "ce-vps-1",
            "--session",
            "ce-vps-codex",
            "--pane-id",
            "pane-1",
            "--dry-run",
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["argv"] == [
        "herdr",
        "--remote",
        "ce-vps-1",
        "--session",
        "ce-vps-codex",
    ]
    assert payload["pane_id"] == "pane-1"
    assert payload["reach_plane"] == "herdr-remote"
    assert "docker exec" in payload["avoids_runtime_attach"]
    assert "host-root container runtime attach" in payload["avoids_runtime_attach"]
    rendered = " ".join(payload["argv"])
    assert "docker exec" not in rendered
    assert "sudo" not in rendered


def test_herdr_remote_attach_json_without_dry_run_is_plan_only(monkeypatch, capsys) -> None:
    runner = FakeAttachRunner()
    monkeypatch.setattr(ce_cli, "_make_herdr_attach_runner", lambda: runner)

    rc = ce_cli.main(
        [
            "herdr",
            "remote-attach",
            "--remote",
            "ce-vps-1",
            "--session",
            "ce-vps-codex",
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["argv"] == [
        "herdr",
        "--remote",
        "ce-vps-1",
        "--session",
        "ce-vps-codex",
    ]
    assert runner.calls == []


def test_herdr_remote_attach_executes_with_injected_runner_no_live_ssh(monkeypatch) -> None:
    runner = FakeAttachRunner()
    monkeypatch.setattr(ce_cli, "_make_herdr_attach_runner", lambda: runner)

    rc = ce_cli.main(
        [
            "herdr",
            "remote-attach",
            "--remote",
            "operator@ce-vps-1",
            "--session",
            "ce-vps-codex",
            "--pane-id",
            "pane-1",
        ]
    )

    assert rc == 0
    assert runner.calls == [
        (
            ["herdr", "--remote", "operator@ce-vps-1", "--session", "ce-vps-codex"],
            {},
        )
    ]
    assert hs.HERDR_SOCKET_ENV not in runner.calls[0][1]
    assert hs.LEGACY_HERDR_SOCKET_ENV not in runner.calls[0][1]


def test_herdr_remote_attach_refuses_docker_exec_shape(capsys) -> None:
    rc = ce_cli.main(
        [
            "herdr",
            "remote-attach",
            "--remote",
            "ce-vps-1",
            "--herdr-binary",
            "docker",
            "--dry-run",
        ]
    )

    assert rc == 1
    assert "docker" in capsys.readouterr().err
