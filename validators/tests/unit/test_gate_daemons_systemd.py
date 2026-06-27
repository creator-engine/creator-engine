from __future__ import annotations

import configparser
import subprocess
from pathlib import Path


SERVICE_NAMES = (
    "ce-belt-daemon.service",
    "ce-integrator-daemon.service",
    "ce-review-pickup-daemon.service",
)
SEAT_UNIT_NAME = "ce-codex-seat@.service"


def _read_unit(repo_root: Path, name: str) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None)
    path = repo_root / "deploy" / "systemd" / name
    with path.open(encoding="utf-8") as fh:
        parser.read_file(fh)
    return parser


def test_gate_daemon_units_parse_and_restart(repo_root: Path):
    for name in SERVICE_NAMES:
        unit = _read_unit(repo_root, name)
        assert unit.has_section("Unit")
        assert unit.has_section("Service")
        assert unit.has_section("Install")
        assert unit["Service"]["EnvironmentFile"]
        assert unit["Service"]["WorkingDirectory"] == "/workspace/creator-engine"
        assert unit["Service"]["Restart"] == "on-failure"
        assert unit["Service"]["RestartSec"]
        assert "Environment" not in unit["Service"]
        assert unit["Service"]["ExecStart"].startswith(("/usr/bin/env cev3 ", "/usr/bin/env bash "))
        assert "PYTHONPATH=validators" not in unit["Service"]["ExecStart"]
        assert "creator_engine_validator.v3_cli" not in unit["Service"]["ExecStart"]


def test_belt_daemon_unit_execstart_is_observe_only_poll_loop(repo_root: Path):
    unit = _read_unit(repo_root, "ce-belt-daemon.service")
    exec_start = unit["Service"]["ExecStart"]
    assert exec_start.startswith("/usr/bin/env bash -lc ")
    assert "while true; do ce pickup poll " in exec_start
    assert ' --identity "$CE_BELT_IDENTITY" ' in exec_start
    assert ' --repo "$CE_GATE_REPO" ' in exec_start
    assert ' ${CE_BELT_LABELS:+--label "$CE_BELT_LABELS"} ' in exec_start
    assert exec_start.endswith('sleep "${CE_BELT_INTERVAL_SECONDS:-120}"; done\'')
    assert " --json;" in exec_start
    assert "--claim" not in exec_start
    assert "--enable-launch" not in exec_start
    assert "--allow-ambient-gh" not in exec_start


def test_codex_seat_unit_supervises_detached_container(repo_root: Path):
    unit = _read_unit(repo_root, SEAT_UNIT_NAME)
    service = unit["Service"]

    assert unit.has_section("Unit")
    assert unit.has_section("Service")
    assert unit.has_section("Install")
    assert unit["Unit"]["Requires"] == "docker.service"
    assert service["Type"] == "simple"
    assert "RemainAfterExit" not in service
    assert service["WorkingDirectory"] == "/workspace/creator-engine"
    environment = service.get("Environment", "")
    assert "CE_CODEX_SEAT_LAUNCHER=deploy/dgx-runsc/run-codex-runsc.sh" in environment
    assert "CE_CODEX_SEAT_CONTAINER_NAME=ce-dgx-codex" in environment
    assert "CE_DGX_DETACH=1" in environment
    assert "CE_VPS_DETACH=1" in environment
    assert "CE_DGX_DOCKER_RESTART_POLICY" not in environment
    assert "CE_VPS_DOCKER_RESTART_POLICY" not in environment
    assert service["EnvironmentFile"] == "-/etc/creator-engine/ce-codex-seat-%i.env"
    assert service["ExecStartPre"] == (
        "-/bin/bash -lc 'container_name=\"${CE_CODEX_SEAT_CONTAINER_NAME:-${CE_DGX_CONTAINER_NAME:-${CE_VPS_CONTAINER_NAME:-ce-dgx-codex}}}\"; "
        "docker rm -f \"${container_name}\"'"
    )
    exec_start = service["ExecStart"]
    assert '"${CE_CODEX_SEAT_LAUNCHER}" --detach tui' in exec_start
    assert 'exec docker wait "${container_name}"' in exec_start
    assert 'export CE_CODEX_SEAT_CONTAINER_NAME="${container_name}"' in exec_start
    assert 'export CE_VPS_CONTAINER_NAME="${CE_VPS_CONTAINER_NAME:-${container_name}}"' in exec_start
    assert 'export CE_DGX_CONTAINER_NAME="${CE_DGX_CONTAINER_NAME:-${container_name}}"' in exec_start
    assert '*vps-runsc*)' in exec_start
    assert service["ExecStop"] == (
        "/bin/bash -lc 'container_name=\"${CE_CODEX_SEAT_CONTAINER_NAME:-${CE_DGX_CONTAINER_NAME:-${CE_VPS_CONTAINER_NAME:-ce-dgx-codex}}}\"; "
        "docker rm -f \"${container_name}\"'"
    )
    assert service["Restart"] == "always"
    assert service["RestartSec"] == "15s"


def test_integrator_unit_execstart(repo_root: Path):
    unit = _read_unit(repo_root, "ce-integrator-daemon.service")
    exec_start = unit["Service"]["ExecStart"]
    assert " queue-daemon " in exec_start
    assert ' --repo "$CE_GATE_REPO" ' in exec_start
    assert " --loop " in exec_start
    assert " --interval 120 " in exec_start
    assert ' --authorized-reviewer "$CE_GATE_AUTHORIZED_REVIEWERS" ' in exec_start
    assert exec_start.endswith(" --json")


def test_review_pickup_unit_execstart(repo_root: Path):
    unit = _read_unit(repo_root, "ce-review-pickup-daemon.service")
    exec_start = unit["Service"]["ExecStart"]
    assert " review-pickup " in exec_start
    assert ' --repo "$CE_GATE_REPO" ' in exec_start
    assert " --identity ce-dev-2 " in exec_start
    assert " --seat ce-dev-1,ce-dev-3,ce-dev-4 " in exec_start
    assert " --loop " in exec_start
    assert " --interval 120 " in exec_start
    assert " --apply " in exec_start
    assert " --inbox-path .ce/state/controller-inbox/awaiting-review.json " in exec_start
    assert exec_start.endswith(" --json")


def test_gate_daemon_installer_is_valid_bash(repo_root: Path):
    script = repo_root / "deploy" / "systemd" / "install-gate-daemons-systemd.sh"
    result = subprocess.run(["bash", "-n", str(script)], check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_integrator_authorized_reviewer_config_is_documented(repo_root: Path):
    # The detailed integrator operations runbook is maintained in the internal
    # tracker (relocated from the public surface), so the public documentation of
    # the authorized-reviewer config lives in the systemd README and installer.
    systemd_readme = (repo_root / "deploy" / "systemd" / "README.md").read_text(encoding="utf-8")
    installer = (
        repo_root / "deploy" / "systemd" / "install-gate-daemons-systemd.sh"
    ).read_text(encoding="utf-8")

    for text in (systemd_readme, installer):
        assert "CE_GATE_AUTHORIZED_REVIEWERS" in text

    assert "CE_GATE_AUTHORIZED_REVIEWERS=reviewer-login[,reviewer-login...]" in installer


# ---------------------------------------------------------------------------
# Egress self-push broker systemd unit (ce-ops#265)
# ---------------------------------------------------------------------------

EGRESS_BROKER_UNIT = "ce-egress-broker.service"
EGRESS_SELF_REVIEW_UNIT = "ce-egress-self-review.service"


def test_egress_broker_unit_parses_and_has_required_sections(repo_root: Path):
    unit = _read_unit(repo_root, EGRESS_BROKER_UNIT)

    assert unit.has_section("Unit")
    assert unit.has_section("Service")
    assert unit.has_section("Install")


def test_egress_broker_unit_is_simple_type_with_restart(repo_root: Path):
    unit = _read_unit(repo_root, EGRESS_BROKER_UNIT)
    service = unit["Service"]

    assert service["Type"] == "simple"
    assert service["Restart"] == "on-failure"
    assert service["RestartSec"]


def test_egress_broker_unit_uses_environment_file_not_inline_env(repo_root: Path):
    unit = _read_unit(repo_root, EGRESS_BROKER_UNIT)
    service = unit["Service"]

    assert service["EnvironmentFile"]
    assert "Environment" not in service


def test_egress_broker_unit_runs_host_broker_script(repo_root: Path):
    unit = _read_unit(repo_root, EGRESS_BROKER_UNIT)
    exec_start = unit["Service"]["ExecStart"]

    assert "ce_egress_self_push_broker.py" in exec_start
    assert "--socket" in exec_start
    assert "--seat" in exec_start
    assert "--host-repo-path" in exec_start
    assert "--config" in exec_start


def test_egress_broker_unit_working_directory_is_repo(repo_root: Path):
    unit = _read_unit(repo_root, EGRESS_BROKER_UNIT)

    assert unit["Service"]["WorkingDirectory"] == "/workspace/creator-engine"


def test_egress_broker_unit_env_vars_are_parametric(repo_root: Path):
    unit = _read_unit(repo_root, EGRESS_BROKER_UNIT)
    exec_start = unit["Service"]["ExecStart"]

    # All four required broker args must reference env vars (not hardcoded values)
    assert "$CE_EGRESS_BROKER_SOCKET" in exec_start
    assert "$CE_EGRESS_BROKER_SEAT" in exec_start
    assert "$CE_EGRESS_BROKER_REPO" in exec_start
    assert "$CE_EGRESS_BROKER_CONFIG" in exec_start


def test_egress_self_review_unit_socket_is_parametric(repo_root: Path):
    unit = _read_unit(repo_root, EGRESS_SELF_REVIEW_UNIT)
    exec_start = unit["Service"]["ExecStart"]

    assert "$CE_EGRESS_SELF_REVIEW_SOCKET" in exec_start
    assert "$CE_EGRESS_SELF_REVIEW_CONFIG" in exec_start
    assert "/run/ce-egress/dev-3-review.sock" not in exec_start


def test_egress_socket_units_own_default_run_paths(repo_root: Path):
    broker_socket = _read_unit(repo_root, "ce-egress-broker.socket")
    review_socket = _read_unit(repo_root, "ce-egress-self-review.socket")

    assert broker_socket["Socket"]["ListenStream"] == "/run/ce-egress/dev-3.sock"
    assert review_socket["Socket"]["ListenStream"] == "/run/ce-egress/dev-3-review.sock"
