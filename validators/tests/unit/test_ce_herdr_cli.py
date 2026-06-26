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
            "--surface-ref",
            "herdr-surface-918aa1506d296ee1a72da70227854392",
            "--workspace-id",
            "workspace-1",
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
    assert payload["surface_ref"] == "herdr-surface-918aa1506d296ee1a72da70227854392"
    assert payload["workspace_id"] == "workspace-1"
    assert payload["auth_channel"] == "authenticated herdr remote reach"
    assert payload["reach_plane"] == "herdr-remote"
    assert payload["isolation_plane"] == "runtime"
    assert payload["requires_host_root"] is False
    assert payload["requires_runtime_attach"] is False
    assert "docker exec" in payload["avoids_runtime_attach"]
    assert "host-root container runtime attach" in payload["avoids_runtime_attach"]
    assert hs.HERDR_SOCKET_ENV not in json.dumps(payload)
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


def test_herdr_remote_attach_dry_run_text_states_reach_isolation_contract(capsys) -> None:
    rc = ce_cli.main(
        [
            "herdr",
            "remote-attach",
            "--remote",
            "ce-vps-1",
            "--session",
            "ce-vps-codex",
            "--dry-run",
        ]
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert "ce herdr remote-attach: herdr --remote ce-vps-1 --session ce-vps-codex" in out
    assert "auth_channel: authenticated herdr remote reach" in out
    assert "reach_plane: herdr-remote" in out
    assert "isolation_plane: runtime" in out
    assert "requires_host_root: false" in out
    assert "requires_runtime_attach: false" in out
    assert "reach is authenticated herdr remote" in out
    assert "isolation is runtime" in out


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
