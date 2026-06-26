from __future__ import annotations

import configparser
import subprocess
from pathlib import Path


SERVICE_NAMES = (
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
        assert unit["Service"]["ExecStart"].startswith("/usr/bin/env cev3 ")
        assert "PYTHONPATH=validators" not in unit["Service"]["ExecStart"]
        assert "creator_engine_validator.v3_cli" not in unit["Service"]["ExecStart"]


def test_codex_seat_unit_supervises_detached_container(repo_root: Path):
    unit = _read_unit(repo_root, SEAT_UNIT_NAME)
    service = unit["Service"]
    environment = service.get("Environment", "")

    assert unit.has_section("Unit")
    assert unit.has_section("Service")
    assert unit.has_section("Install")
    assert unit["Unit"]["Requires"] == "docker.service"
    assert service["Type"] == "simple"
    assert "RemainAfterExit" not in service
    assert service["WorkingDirectory"] == "/workspace/creator-engine"
    assert "CE_DGX_DETACH=1" in environment
    assert "CE_VPS_DETACH=1" in environment
    assert "CE_DGX_DOCKER_RESTART_POLICY" not in environment
    assert "CE_VPS_DOCKER_RESTART_POLICY" not in environment
    assert service["EnvironmentFile"] == "-/etc/creator-engine/ce-codex-seat-%i.env"
    assert 'docker rm -f "${container_name}"' in service["ExecStartPre"]
    assert '"${CE_CODEX_SEAT_LAUNCHER}" --detach tui' in service["ExecStart"]
    assert 'exec docker wait "${container_name}"' in service["ExecStart"]
    assert 'export CE_VPS_CONTAINER_NAME="${CE_VPS_CONTAINER_NAME:-${container_name}}"' in service[
        "ExecStart"
    ]
    assert 'export CE_DGX_CONTAINER_NAME="${CE_DGX_CONTAINER_NAME:-${container_name}}"' in service[
        "ExecStart"
    ]
    assert 'docker rm -f "${container_name}"' in service["ExecStop"]
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
