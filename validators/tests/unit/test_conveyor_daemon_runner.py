import os
import stat
import subprocess
from pathlib import Path

import pytest

from creator_engine_validator import conveyor_daemon_runner as runner
from creator_engine_validator.daemon_lease import DaemonLeaseHeld, DaemonLeaseStale


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
    assert daemon_kwargs["receipt_state_path"] == Path(env["CE_CONVEYOR_DAEMON_DISCOVERY_STATE"])
    assert daemon_kwargs["path_allocator"] is not None
    assert daemon_kwargs["daemon_lease"] is lease
    assert daemon_kwargs["receipt_issuer"] is not None
    assert lease.released is True
    assert constructed[-1] == ("run_once",)


def test_build_daemon_pins_production_receipt_identity_to_controller_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    env = _base_env(tmp_path)
    config = runner.load_config(env)
    captured = {}

    class FakeDaemon:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(runner, "ConveyorDaemon", FakeDaemon)

    runner._build_daemon(
        config,
        FakeLease(),
        probe_runner=lambda _argv: (
            "READY-FOR-HARVEST ce-497-signal-receipt-ledger "
            "0123456789abcdef0123456789abcdef01234567"
        ),
    )

    payload = next(iter(captured["discovery_runner"]()))
    assert payload.receipt_identity is not None
    assert captured["receipt_state_path"] is config.discovery_state
    assert captured["discovery_runner"].state_path is config.discovery_state


def test_jsonl_ledger_writer_creates_private_ledger_despite_permissive_umask(tmp_path: Path):
    ledger_path = tmp_path / "ledger" / "daemon.jsonl"
    prior = os.umask(0)
    try:
        writer = runner._jsonl_ledger_writer(ledger_path)
        writer(type("Record", (), {"as_dict": lambda self: {"action": "test"}})())
    finally:
        os.umask(prior)

    assert stat.S_IMODE(ledger_path.stat().st_mode) == 0o600


def test_jsonl_ledger_writer_refuses_existing_nonprivate_ledger(tmp_path: Path):
    ledger_path = tmp_path / "ledger" / "daemon.jsonl"
    ledger_path.parent.mkdir(mode=0o700)
    ledger_path.touch(mode=0o644)
    ledger_path.chmod(0o644)
    writer = runner._jsonl_ledger_writer(ledger_path)

    with pytest.raises(runner.ConfigError, match="ledger file is unsafe"):
        writer(type("Record", (), {"as_dict": lambda self: {"action": "test"}})())

    assert stat.S_IMODE(ledger_path.stat().st_mode) == 0o644
    assert ledger_path.read_text(encoding="utf-8") == ""


def test_ensure_private_dir_refuses_existing_permissive_directory(tmp_path: Path):
    unsafe = tmp_path / "unsafe"
    unsafe.mkdir(mode=0o755)

    with pytest.raises(runner.ConfigError, match="private directory is unsafe"):
        runner._ensure_private_dir(unsafe)

    assert stat.S_IMODE(unsafe.stat().st_mode) == 0o755


def test_main_reports_clean_private_lease_directory_refusal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    env = _base_env(tmp_path)
    lease_root = Path(env["CE_DAEMON_LEASE_ROOT"])
    lease_root.mkdir(mode=0o755)
    lease_root.chmod(0o755)
    acquired = False

    def fake_acquire(*args, **kwargs):
        nonlocal acquired
        acquired = True
        return FakeLease()

    monkeypatch.setattr(runner, "acquire", fake_acquire)

    assert runner.main(env) == 2
    assert acquired is False
    assert capsys.readouterr().err == "ERROR: conveyor private directory is unsafe\n"


@pytest.mark.parametrize(
    "root_env",
    [
        "CE_CONVEYOR_DAEMON_VALIDATION_LEDGER_ROOT",
        "CE_CONVEYOR_DAEMON_ACTIVE_WORK_LEDGER_ROOT",
    ],
)
def test_main_reports_clean_private_runtime_directory_refusal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    root_env: str,
):
    env = _base_env(tmp_path)
    unsafe_root = tmp_path / root_env.lower()
    unsafe_root.mkdir(mode=0o755)
    unsafe_root.chmod(0o755)
    env[root_env] = str(unsafe_root)
    lease = FakeLease()

    monkeypatch.setattr(runner, "acquire", lambda *args, **kwargs: lease)

    assert runner.main(env) == 2
    assert lease.released is True
    assert capsys.readouterr().err == "ERROR: conveyor private directory is unsafe\n"


@pytest.mark.parametrize(
    "unsafe",
    ["relative/state.json", "/", "/tmp/../state.json", "/tmp/./state.json", "/tmp/x\x00y"],
)
def test_load_config_rejects_nonlexical_receipt_state_paths(tmp_path: Path, unsafe: str):
    env = _base_env(tmp_path)
    env["CE_CONVEYOR_DAEMON_DISCOVERY_STATE"] = unsafe
    with pytest.raises(runner.ConfigError, match="safe absolute path"):
        runner.load_config(env)


def test_load_config_normalizes_receipt_state_once_without_following_links(tmp_path: Path):
    env = _base_env(tmp_path)
    env["CE_CONVEYOR_DAEMON_DISCOVERY_STATE"] = f"{tmp_path}//private///receipts.json"
    config = runner.load_config(env)
    assert config.discovery_state == tmp_path / "private" / "receipts.json"


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


@pytest.mark.parametrize(
    ("lease_error", "expected_reason"),
    [
        (
            DaemonLeaseHeld("live conveyor-daemon lease is held by holder-a pid=4321 host=host-a"),
            "live conveyor-daemon lease is held by holder-a pid=4321 host=host-a",
        ),
        (
            DaemonLeaseStale("stale conveyor-daemon lease requires explicit audited takeover"),
            "stale conveyor-daemon lease requires explicit audited takeover",
        ),
    ],
)
def test_main_reports_clean_lease_refusal_and_exit_73(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    lease_error: Exception,
    expected_reason: str,
):
    env = _base_env(tmp_path)
    lease_path = Path(env["CE_DAEMON_LEASE_ROOT"]) / "conveyor-daemon.lease"

    def fake_acquire(*args, **kwargs):
        lease_path.write_text(
            (
                '{"acquired_at":1.0,"heartbeat_at":2.0,"holder_id":"holder-a",'
                '"host":"host-a","pid":4321}\n'
            ),
            encoding="utf-8",
        )
        raise lease_error

    monkeypatch.setattr(runner, "acquire", fake_acquire)

    assert runner.main(env) == 73

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.count("\n") == 1
    assert captured.err == (
        "ERROR: conveyor-daemon singleton lease refused: "
        f"{expected_reason}; lease_path={lease_path}; holder_pid=4321\n"
    )


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
