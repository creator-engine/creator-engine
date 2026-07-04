import subprocess
from pathlib import Path

import pytest

from creator_engine_validator import conveyor_daemon_runner as runner


class FakeLease:
    def __init__(self):
        self.heartbeats = 0
        self.released = False

    def heartbeat(self):
        self.heartbeats += 1

    def release(self):
        self.released = True


def _base_env(tmp_path: Path) -> dict[str, str]:
    secret_file = tmp_path / "signing-secret"
    secret_file.write_text("secret-value\n", encoding="utf-8")
    return {
        "CE_CONVEYOR_DAEMON_SEAT_PROBES": '[{"seat_id":"seat-a","argv":["python","--version"]}]',
        "CE_CONVEYOR_DAEMON_RUNTIME_ROOT": str(tmp_path / "runtime"),
        "CE_CONVEYOR_DAEMON_DISCOVERY_STATE": str(tmp_path / "state" / "discovery.json"),
        "GH_TOKEN": "gh-test-token",
        "CE_DAEMON_LEASE_ROOT": str(tmp_path / "leases"),
        "CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE": str(secret_file),
        "CE_CONVEYOR_DAEMON_REPO_ROOT": str(tmp_path / "repo"),
        "CE_CONVEYOR_DAEMON_ITERATIONS": "1",
    }


def test_main_assembles_armed_daemon_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    env = _base_env(tmp_path)
    lease = FakeLease()
    constructed = []

    def fake_acquire(*args, **kwargs):
        constructed.append(("acquire", args, kwargs))
        return lease

    class FakeDaemon:
        def __init__(self, **kwargs):
            constructed.append(("daemon", kwargs))

        def run_once(self):
            constructed.append(("run_once",))

    monkeypatch.setattr(runner, "acquire", fake_acquire)
    monkeypatch.setattr(runner, "ConveyorDaemon", FakeDaemon)

    assert runner.main(env) == 0

    assert constructed[0][0] == "acquire"
    assert constructed[0][1][0] == "conveyor-daemon"
    daemon_kwargs = constructed[1][1]
    assert daemon_kwargs["armed"] is True
    assert daemon_kwargs["git_runner"] is not None
    assert daemon_kwargs["gh_runner"] is not None
    assert daemon_kwargs["now"] is not None
    assert daemon_kwargs["ledger_writer"] is not None
    assert daemon_kwargs["path_allocator"] is not None
    assert daemon_kwargs["daemon_lease"] is lease
    assert daemon_kwargs["receipt_issuer"] is not None
    assert lease.released is True
    assert constructed[-1] == ("run_once",)


@pytest.mark.parametrize(
    ("missing", "expected"),
    [
        ("CE_CONVEYOR_DAEMON_SEAT_PROBES", "CE_CONVEYOR_DAEMON_SEAT_PROBES"),
        ("CE_CONVEYOR_DAEMON_SIGNING_SECRET_FILE", "receipt signing secret"),
    ],
)
def test_refuses_missing_required_env_before_daemon_construction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    missing: str,
    expected: str,
):
    env = _base_env(tmp_path)
    env.pop(missing)
    constructed = False

    class FakeDaemon:
        def __init__(self, **kwargs):
            nonlocal constructed
            constructed = True

    monkeypatch.setattr(runner, "ConveyorDaemon", FakeDaemon)

    assert runner.main(env) == 2
    assert constructed is False
    assert expected in capsys.readouterr().err


def test_existing_lease_entrypoint_reports_config_error_and_releases_lease(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    env = _base_env(tmp_path)
    env.pop("CE_CONVEYOR_DAEMON_SEAT_PROBES")
    lease = FakeLease()
    constructed = False

    class FakeDaemon:
        def __init__(self, **kwargs):
            nonlocal constructed
            constructed = True

    monkeypatch.setattr(runner, "ConveyorDaemon", FakeDaemon)

    assert runner.main_with_existing_lease(lease, env) == 2
    assert constructed is False
    assert lease.released is True
    assert "CE_CONVEYOR_DAEMON_SEAT_PROBES" in capsys.readouterr().err


def test_passes_validation_ledger_binding_unconditionally(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    env = _base_env(tmp_path)
    captured = {}

    monkeypatch.setattr(runner, "acquire", lambda *args, **kwargs: FakeLease())

    class FakeDaemon:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def run_once(self):
            return None

    monkeypatch.setattr(runner, "ConveyorDaemon", FakeDaemon)

    assert runner.main(env) == 0

    binding = captured["validation_ledger_binding"]
    assert binding is not None
    assert binding.controller_id == "conveyor-daemon"
    assert binding.lane_id == "a1"
    assert binding.claim_ref == "".join(("ce", "-ops", "#", "388"))
    assert binding.repo_root == Path(env["CE_CONVEYOR_DAEMON_REPO_ROOT"])


def test_shadow_stop_line_has_no_approval_review_or_enqueue_seams(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    env = _base_env(tmp_path)
    captured = {}

    monkeypatch.setattr(runner, "acquire", lambda *args, **kwargs: FakeLease())

    class FakeDaemon:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def run_once(self):
            return None

    monkeypatch.setattr(runner, "ConveyorDaemon", FakeDaemon)

    assert runner.main(env) == 0

    assert captured["armed"] is True
    forbidden = ("approve", "merge", "enqueue", "approval_wall", "reviewer")
    assert not any(fragment in key for key in captured for fragment in forbidden)


def test_secret_scoping_for_subprocess_runners(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    env = _base_env(tmp_path)
    env["CE_CONVEYOR_DAEMON_SIGNING_SECRET"] = "direct-secret"
    captured = {}
    subprocess_calls = []

    monkeypatch.setattr(runner, "acquire", lambda *args, **kwargs: FakeLease())

    class FakeDaemon:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def run_once(self):
            return None

    def fake_run(argv, **kwargs):
        subprocess_calls.append((tuple(argv), dict(kwargs.get("env") or {})))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(runner, "ConveyorDaemon", FakeDaemon)
    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    monkeypatch.setenv("CE_CONVEYOR_DAEMON_SIGNING_SECRET", "process-secret")
    monkeypatch.setenv("GH_TOKEN", "process-gh-token")

    assert runner.main(env) == 0

    captured["git_runner"](("status",), tmp_path, {"PATH": "/usr/bin:/bin"})
    captured["gh_runner"](("api", "user"), tmp_path)
    captured["validation_sandbox_command_runner"].run(("podman", "--version"))

    git_env = subprocess_calls[0][1]
    gh_env = subprocess_calls[1][1]
    sandbox_env = subprocess_calls[2][1]
    assert "GH_TOKEN" not in git_env
    assert gh_env["GH_TOKEN"] == "gh-test-token"
    assert "GH_TOKEN" not in sandbox_env
    assert "CE_CONVEYOR_DAEMON_SIGNING_SECRET" not in sandbox_env
