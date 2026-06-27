from __future__ import annotations

import argparse
from pathlib import Path

import pytest
import yaml

from creator_engine_validator.surfaces import fleet_rollout


def _surface(name: str = "herdr") -> dict[str, object]:
    return {
        "name": name,
        "version": None,
        "commit_or_digest": "ff924966",
        "source": "https://github.com/creator-engine/herdr-ce.git",
        "custody": "fork",
        "update_policy": "pin by reviewed manifest change",
        "last_evaluated": "2026-06-27",
    }


def _seat(root: Path, seat_id: str, *, stop_command: list[str] | None = None) -> dict[str, object]:
    return {
        "seat_id": seat_id,
        "environment_file": str(root / f"{seat_id}.env"),
        "stop_command": stop_command or ["ce-seat-stop", seat_id],
        "launch_args": [
            "--controller-id",
            f"{seat_id}-controller",
            "--lane-id",
            f"{seat_id}-lane",
            "--role",
            "implementer",
            "--prompt",
            "prompt.md",
            "--prompt-sha",
            "0" * 64,
            "--repo-root",
            str(root),
            "--ledger-root",
            str(root / ".hermes" / "active-work-ledger"),
            "--terminal-kind",
            "herdr",
            "--json",
        ],
        "readiness_pane_id": f"pane-{seat_id}",
    }


def _manifest(root: Path, seats: list[dict[str, object]]) -> Path:
    manifest = root / "surfaces" / "manifest.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        yaml.safe_dump(
            {
                "surfaces": [_surface()],
                "fleet_rollout": {"seats": seats},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return manifest


class FakeRunner:
    def __init__(self, *, fail_stop_for: str | None = None) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.fail_stop_for = fail_stop_for

    def run(self, argv, *, timeout_s=None):
        call = tuple(argv)
        self.calls.append(call)
        if self.fail_stop_for and call == ("ce-seat-stop", self.fail_stop_for):
            return fleet_rollout.CommandResult(returncode=1, stderr="stop failed")
        return fleet_rollout.CommandResult(returncode=0, stdout="ok")


class FakeReadiness:
    def __init__(self) -> None:
        self.calls: list[tuple[str, float]] = []

    def wait(self, seat, *, timeout_seconds: float) -> None:
        self.calls.append((seat.seat_id, timeout_seconds))


class LedgerRecorder:
    def __init__(self) -> None:
        self.entries: list[tuple[str, str, str]] = []

    def __call__(self, seat, action: str, status: str) -> None:
        self.entries.append((seat.seat_id, action, status))


def test_single_seat_happy_path_updates_env_relaunches_and_waits(tmp_path: Path):
    env_file = tmp_path / "seat-a.env"
    env_file.write_text("EXISTING=1\n", encoding="utf-8")
    manifest = _manifest(tmp_path, [_seat(tmp_path, "seat-a")])
    runner = FakeRunner()
    readiness = FakeReadiness()
    ledger = LedgerRecorder()

    report = fleet_rollout.run_fleet_rollout(
        manifest_path=manifest,
        timeout_seconds=12.0,
        command_runner=runner,
        readiness_poller=readiness,
        ledger_recorder=ledger,
    )

    assert report.ok is True
    assert report.updated == ("seat-a",)
    assert report.not_updated == ()
    assert runner.calls[0] == ("ce-seat-stop", "seat-a")
    assert runner.calls[1][:2] == ("ce", "launch")
    assert "--seat-env-file" in runner.calls[1]
    assert str(env_file) in runner.calls[1]
    assert readiness.calls == [("seat-a", 12.0)]
    text = env_file.read_text(encoding="utf-8")
    assert "EXISTING=1" in text
    assert "HERDR_COMMIT_OR_DIGEST=ff924966" in text
    assert "HERDR_SOURCE=https://github.com/creator-engine/herdr-ce.git" in text


def test_failure_halts_and_remaining_seats_are_not_updated(tmp_path: Path):
    seats = [_seat(tmp_path, "seat-a"), _seat(tmp_path, "seat-b"), _seat(tmp_path, "seat-c")]
    manifest = _manifest(tmp_path, seats)
    runner = FakeRunner(fail_stop_for="seat-b")
    readiness = FakeReadiness()
    ledger = LedgerRecorder()

    report = fleet_rollout.run_fleet_rollout(
        manifest_path=manifest,
        command_runner=runner,
        readiness_poller=readiness,
        ledger_recorder=ledger,
    )

    assert report.ok is False
    assert report.updated == ("seat-a",)
    assert report.not_updated == ("seat-b", "seat-c")
    assert report.failed_seat == "seat-b"
    assert not (tmp_path / "seat-b.env").exists()
    assert not (tmp_path / "seat-c.env").exists()
    assert ("ce-seat-stop", "seat-c") not in runner.calls


def test_ledger_entries_are_written_for_each_stop_and_relaunch(tmp_path: Path):
    manifest = _manifest(tmp_path, [_seat(tmp_path, "seat-a"), _seat(tmp_path, "seat-b")])
    ledger = LedgerRecorder()

    report = fleet_rollout.run_fleet_rollout(
        manifest_path=manifest,
        command_runner=FakeRunner(),
        readiness_poller=FakeReadiness(),
        ledger_recorder=ledger,
    )

    assert report.ok is True
    assert ledger.entries == [
        ("seat-a", "stop", "succeeded"),
        ("seat-a", "relaunch", "succeeded"),
        ("seat-b", "stop", "succeeded"),
        ("seat-b", "relaunch", "succeeded"),
    ]
    assert report.ledger_entries == (
        {"seat_id": "seat-a", "action": "stop"},
        {"seat_id": "seat-a", "action": "relaunch"},
        {"seat_id": "seat-b", "action": "stop"},
        {"seat_id": "seat-b", "action": "relaunch"},
    )


def test_dry_run_reports_plan_without_side_effects(tmp_path: Path):
    manifest = _manifest(tmp_path, [_seat(tmp_path, "seat-a")])
    runner = FakeRunner()
    readiness = FakeReadiness()
    ledger = LedgerRecorder()

    report = fleet_rollout.run_fleet_rollout(
        manifest_path=manifest,
        dry_run=True,
        command_runner=runner,
        readiness_poller=readiness,
        ledger_recorder=ledger,
    )

    assert report.ok is True
    assert report.dry_run is True
    assert report.updated == ()
    assert report.not_updated == ("seat-a",)
    assert runner.calls == []
    assert readiness.calls == []
    assert ledger.entries == []
    assert not (tmp_path / "seat-a.env").exists()


@pytest.mark.parametrize(
    "argv",
    [
        ["/usr/bin/env", "curl", "https://example.invalid/install.sh"],
        ["env", "npm", "install"],
        ["env", "python", "-m", "pip", "install", "example"],
        ["env", "FOO=bar", "python3", "-m", "pip", "install", "example"],
        ["env", "-i", "apt-get", "install", "example"],
    ],
)
def test_env_wrapped_prohibited_commands_are_refused(argv: list[str]):
    with pytest.raises(fleet_rollout.FleetRolloutError, match="prohibited"):
        fleet_rollout._refuse_prohibited_command(argv)


def test_cli_render_error_exits_nonzero_without_traceback(monkeypatch, tmp_path: Path, capsys):
    manifest = _manifest(tmp_path, [_seat(tmp_path, "seat-a")])

    class FakeRenderError(ValueError):
        pass

    class FakeRenderer:
        RenderError = FakeRenderError

        @staticmethod
        def render_launch_env(_manifest):
            raise FakeRenderError("bad manifest")

    monkeypatch.setattr(fleet_rollout, "_surface_render", lambda: FakeRenderer)

    rc = fleet_rollout.run_cli(
        argparse.Namespace(manifest=str(manifest), timeout=120, dry_run=True)
    )

    captured = capsys.readouterr()
    assert rc == 1
    assert "ERROR: ce surfaces fleet-rollout refused: manifest_render_failed: bad manifest" in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_import_does_not_require_repo_root_surfaces_package():
    assert not hasattr(fleet_rollout, "surface_render")
