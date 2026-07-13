from __future__ import annotations

import configparser
import os
import subprocess
from pathlib import Path


SERVICE_NAMES = (
    "ce-belt-daemon.service",
    "ce-integrator-daemon.service",
    "ce-review-pickup-daemon.service",
    "ce-ratifier-queue.service",
)
SEAT_UNIT_NAME = "ce-codex-seat@.service"


def _read_unit(repo_root: Path, name: str) -> configparser.ConfigParser:
    return _read_unit_path(repo_root / "deploy" / "systemd" / name)


def _read_unit_path(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None, strict=False)
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
        assert unit["Service"]["ExecStartPre"] == (
            "/usr/bin/mkdir -p %h/.local/state/creator-engine/daemon-heartbeats"
        )
        assert unit["Service"]["Restart"] == "on-failure"
        assert unit["Service"]["RestartSec"]
        assert "Environment" not in unit["Service"]
        assert unit["Service"]["ExecStart"].startswith(("/usr/bin/env ce ", "/usr/bin/env bash "))
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


def test_ratifier_queue_unit_is_proposal_only_and_restart_supervised(repo_root: Path):
    unit = _read_unit(repo_root, "ce-ratifier-queue.service")
    service = unit["Service"]
    assert service["EnvironmentFile"]
    assert service["WorkingDirectory"] == "/workspace/creator-engine"
    assert service["Restart"] == "on-failure"
    assert "ce ratifier-queue" in service["ExecStart"]
    assert "--loop" in service["ExecStart"]
    assert "CE_RATIFIER_QUEUE_CANDIDATES_PATH" in service["ExecStart"]
    assert "GH_TOKEN" not in service["ExecStart"]
    assert "--apply" not in service["ExecStart"]


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


def test_integrator_approval_wall_wiring_is_dormant_and_parametric(repo_root: Path):
    unit = _read_unit(repo_root, "ce-integrator-daemon.service")
    service = unit["Service"]
    exec_start = service["ExecStart"]

    # Preserve the existing queue behavior while attaching only named env inputs.
    for unchanged_arg in (
        ' --repo "$CE_GATE_REPO" ',
        " --loop ",
        " --interval 120 ",
        ' --authorized-reviewer "$CE_GATE_AUTHORIZED_REVIEWERS" ',
        " --json",
    ):
        assert unchanged_arg in exec_start

    expected_pairs = (
        ("--approval-wall-secret-backend", "CE_APPROVAL_WALL_SECRET_BACKEND"),
        ("--approval-wall-secret-mount", "CE_APPROVAL_WALL_SECRET_MOUNT"),
        ("--approval-wall-secret-path", "CE_APPROVAL_WALL_SECRET_PATH"),
        ("--approval-wall-secret-field", "CE_APPROVAL_WALL_SECRET_FIELD"),
        ("--approval-wall-secret-purpose", "CE_APPROVAL_WALL_SECRET_PURPOSE"),
        ("--approval-wall-secret-owner-ref", "CE_APPROVAL_WALL_SECRET_OWNER_REF"),
        ("--approval-wall-secret-ref-policy-sha", "CE_APPROVAL_WALL_SECRET_REF_POLICY_SHA"),
        ("--approval-wall-secret-target-ref", "CE_APPROVAL_WALL_SECRET_TARGET_REF"),
        ("--approval-wall-policy-sha", "CE_APPROVAL_WALL_POLICY_SHA"),
    )
    for flag, env_name in expected_pairs:
        assert f'{flag} "${env_name}"' in exec_start

    assert exec_start.count("--approval-wall-") == len(expected_pairs)
    assert "CE_APPROVAL_CAPABILITY_SECRET" not in exec_start
    assert "Environment" not in service


def test_approval_wall_deployment_docs_keep_dormant_fail_closed_boundaries(repo_root: Path):
    systemd_readme = (repo_root / "deploy" / "systemd" / "README.md").read_text(encoding="utf-8")
    installer = (
        repo_root / "deploy" / "systemd" / "install-gate-daemons-systemd.sh"
    ).read_text(encoding="utf-8")

    approval_env_names = (
        "BAO_ADDR",
        "BAO_TOKEN",
        "BAO_CACERT",
        "CE_OPENBAO_ALLOWED_REFS",
        "CE_APPROVAL_WALL_SECRET_BACKEND",
        "CE_APPROVAL_WALL_SECRET_MOUNT",
        "CE_APPROVAL_WALL_SECRET_PATH",
        "CE_APPROVAL_WALL_SECRET_FIELD",
        "CE_APPROVAL_WALL_SECRET_PURPOSE",
        "CE_APPROVAL_WALL_SECRET_OWNER_REF",
        "CE_APPROVAL_WALL_SECRET_REF_POLICY_SHA",
        "CE_APPROVAL_WALL_SECRET_TARGET_REF",
        "CE_APPROVAL_WALL_POLICY_SHA",
    )
    for text in (systemd_readme, installer):
        for env_name in approval_env_names:
            assert env_name in text
        assert "forge/approval-capability/wall" in text
        assert "file:/run/user/<uid>/creator-engine/approval-wall-secret" in text
        assert "fork-readable" in text
        assert "fail closed" in text
        assert "bootstrap fallback only" in text
        assert "does not arm" in text
        assert "never committed" in text

    assert "forge/reviewer/gh-token" in systemd_readme
    assert "reviewer-token" in systemd_readme
    assert "signing-secret" in systemd_readme
    assert "`env:` delivery" in systemd_readme
    assert "no backend is configured" in systemd_readme


def test_approval_wall_docs_contain_no_concrete_runtime_secret_or_policy_values(repo_root: Path):
    systemd_readme = (repo_root / "deploy" / "systemd" / "README.md").read_text(encoding="utf-8")
    installer = (
        repo_root / "deploy" / "systemd" / "install-gate-daemons-systemd.sh"
    ).read_text(encoding="utf-8")

    for text in (systemd_readme, installer):
        assert "BAO_TOKEN=<operator-supplied-runtime-token>" in text
        assert "policy_sha=<operator-supplied-64-hex>" in text
        assert "CE_APPROVAL_WALL_POLICY_SHA=<operator-supplied-policy-sha-or-id>" in text
        assert "signing_secret=" not in text


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


def test_review_spawn_provider_unit_is_default_off_and_uses_ce_console_script(repo_root: Path):
    unit = _read_unit(repo_root, "ce-review-spawn-provider.service")
    service = unit["Service"]

    assert service["EnvironmentFile"] == "/etc/creator-engine/ce-review-spawn-provider.env"
    assert "Environment" not in service
    assert service["ExecStart"] == (
        "/usr/bin/env ce review-spawn-provider "
        "--config /etc/creator-engine/ce-review-spawn-provider.env"
    )


def test_gate_daemon_installer_is_valid_bash(repo_root: Path):
    script = repo_root / "deploy" / "systemd" / "install-gate-daemons-systemd.sh"
    result = subprocess.run(["bash", "-n", str(script)], check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_model_drift_watcher_uses_its_own_zero_token_environment(repo_root: Path):
    unit_path = repo_root / "deploy" / "systemd" / "ce-model-drift-watcher.service"
    unit = _read_unit_path(unit_path)
    text = unit_path.read_text(encoding="utf-8")
    installer = (repo_root / "deploy" / "systemd" / "install-gate-daemons-systemd.sh").read_text(encoding="utf-8")
    service = unit["Service"]
    assert service["EnvironmentFile"] == "/etc/creator-engine/ce-model-drift.env"
    assert service["ExecStart"].endswith("-m creator_engine_validator.model_drift_watcher")
    assert service["Restart"] == "on-failure"
    assert service["NoNewPrivileges"] == "true"
    assert service["ProtectSystem"] == "strict"
    assert "gate-daemons.env" not in text
    for forbidden in ("GH_TOKEN", "GITHUB_TOKEN", "BAO_TOKEN", "VAULT_TOKEN", "PAT", "CREDENTIAL"):
        assert forbidden not in text
    for allowed in ("CE_MODEL_DRIFT_CANON", "CE_MODEL_DRIFT_STATE_PATH", "CE_MODEL_DRIFT_LEASE_ROOT", "CE_MODEL_DRIFT_INBOX_PATH", "CE_MODEL_DRIFT_CADENCE_SECONDS"):
        assert allowed in installer
    assert "ce-model-drift-watcher.service)" in installer
    assert "chmod 0600 \"$model_drift_env_file\"" in installer
    assert "services+=(ce-model-drift-watcher.service)" in installer
    assert "ensure_model_drift_directory /var/lib/creator-engine/model-drift" in installer
    assert "ensure_model_drift_directory /var/lib/creator-engine/controller-inbox" in installer
    assert "refusing symlinked model drift runtime path" in installer
    assert "-o creator-engine -g creator-engine -m 0700" in installer


def test_model_drift_watcher_is_system_only_and_user_installs_skip_it(tmp_path: Path, repo_root: Path):
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    (fake_repo / ".git").mkdir()
    fake_python = fake_repo / ".venv" / "bin" / "python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    fake_python.chmod(0o755)
    env_dir = tmp_path / "env"
    env_dir.mkdir()
    gate_env = env_dir / "gate-daemons.env"
    broker_env = env_dir / "broker.env"
    review_env = env_dir / "review.env"
    for path in (gate_env, broker_env, review_env):
        path.write_text("ok\n", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "systemctl").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (fake_bin / "systemctl").chmod(0o755)
    result = subprocess.run(
        [
            "bash", str(repo_root / "deploy" / "systemd" / "install-gate-daemons-systemd.sh"),
            "--repo-root", str(fake_repo), "--unit-dir", str(tmp_path / "units"),
            "--env-file", str(gate_env), "--egress-broker-env-file", str(broker_env),
            "--egress-self-review-env-file", str(review_env), "--no-start",
        ],
        check=False, capture_output=True, text=True,
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )
    assert result.returncode == 0, result.stderr
    assert "skipped: ce-model-drift-watcher.service (system-only:" in result.stdout
    assert not (tmp_path / "units" / "ce-model-drift-watcher.service").exists()


def test_materializer_unit_supervises_disarmed_dry_run_loop(repo_root: Path):
    unit_path = repo_root / "deploy" / "materializer" / "ce-materializer.service"
    unit = _read_unit_path(unit_path)
    service = unit["Service"]
    unit_text = unit_path.read_text(encoding="utf-8")

    assert unit.has_section("Unit")
    assert unit.has_section("Service")
    assert unit.has_section("Install")
    assert service["Type"] == "simple"
    assert service["User"] == "creator-engine"
    assert service["WorkingDirectory"] == "/workspace/creator-engine"
    assert service["EnvironmentFile"] == "/etc/creator-engine/ce-materializer.env"
    assert service["ExecStart"] == (
        "/bin/bash -lc 'exec /workspace/creator-engine/deploy/materializer/launch-materializer.sh'"
    )
    assert service["Restart"] == "always"
    assert service["RuntimeDirectory"] == "ce-materializer"
    assert service["StateDirectory"] == "ce-materializer"
    assert service["LogsDirectory"] == "ce-materializer"
    assert service["LogsDirectoryMode"] == "0700"
    assert "Environment=CE_MATERIALIZER_DRY_RUN=1" in unit_text
    assert "Environment=CE_MATERIALIZER_STATE_ROOT=/workspace/creator-engine/.ce/state/brain-intent-materializer" in unit_text
    assert "PRIVATE_KEY_FILE" not in unit_text
    assert "CE_MATERIALIZER_APP_PRIVATE_KEY" not in unit_text


def test_materializer_env_template_is_dry_run_only(repo_root: Path):
    template = repo_root / "deploy" / "materializer" / "ce-materializer.env.example"
    text = template.read_text(encoding="utf-8")

    assert "CE_MATERIALIZER_DRY_RUN=1" in text
    assert "CE_GATE_REPO=creator-engine/creator-engine" in text
    assert "CE_MATERIALIZER_PRIVATE_KEY_FILE" not in text
    assert "CE_MATERIALIZER_APP_PRIVATE_KEY" not in text


def test_materializer_launcher_is_valid_bash(repo_root: Path):
    script = repo_root / "deploy" / "materializer" / "launch-materializer.sh"
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


def test_review_pickup_openbao_deployment_settings_use_reviewer_secret_path(repo_root: Path):
    systemd_readme = (repo_root / "deploy" / "systemd" / "README.md").read_text(encoding="utf-8")
    installer = (
        repo_root / "deploy" / "systemd" / "install-gate-daemons-systemd.sh"
    ).read_text(encoding="utf-8")

    for text in (systemd_readme, installer):
        assert "path=forge/reviewer/gh-token;field=token;purpose=review-pickup-token" in text
        assert "forge/ce-dev-2/gh-token" not in text

    assert "CE_PICKUP_TOKEN_SECRET_PATH=forge/reviewer/gh-token" in systemd_readme


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
    assert "--expected-peer-uid" in exec_start
    assert "--expected-peer-gid" in exec_start
    assert "--host-repo-path" in exec_start
    assert "--config" in exec_start


def test_egress_broker_unit_working_directory_is_repo(repo_root: Path):
    unit = _read_unit(repo_root, EGRESS_BROKER_UNIT)

    assert unit["Service"]["WorkingDirectory"] == "/workspace/creator-engine"


def test_egress_broker_unit_env_vars_are_parametric(repo_root: Path):
    unit = _read_unit(repo_root, EGRESS_BROKER_UNIT)
    exec_start = unit["Service"]["ExecStart"]

    # Required broker args must reference env vars (not hardcoded values).
    assert "$CE_EGRESS_BROKER_SOCKET" in exec_start
    assert "$CE_EGRESS_BROKER_SEAT" in exec_start
    assert "$CE_EGRESS_BROKER_EXPECTED_PEER_UID" in exec_start
    assert "$CE_EGRESS_BROKER_EXPECTED_PEER_GID" in exec_start
    assert "$CE_EGRESS_BROKER_REPO" in exec_start
    assert "$CE_EGRESS_BROKER_CONFIG" in exec_start


def test_egress_self_review_unit_socket_is_parametric(repo_root: Path):
    unit = _read_unit(repo_root, EGRESS_SELF_REVIEW_UNIT)
    exec_start = unit["Service"]["ExecStart"]

    assert "$CE_EGRESS_SELF_REVIEW_SOCKET" in exec_start
    assert "$CE_EGRESS_SELF_REVIEW_CONFIG" in exec_start
    assert "${CE_BROKER_HOME:-/opt/ce-broker/creator-engine}" in exec_start
    assert "/run/ce-egress/dev-3-review.sock" not in exec_start


def test_egress_self_review_unit_uses_stable_broker_checkout(repo_root: Path):
    unit = _read_unit(repo_root, EGRESS_SELF_REVIEW_UNIT)
    service = unit["Service"]
    exec_start = service["ExecStart"]

    assert service["WorkingDirectory"] == "/opt/ce-broker/creator-engine"
    assert "CE_BROKER_HOME=/opt/ce-broker/creator-engine" in service["Environment"]
    assert 'broker_home="${CE_BROKER_HOME:-/opt/ce-broker/creator-engine}"' in exec_start
    assert 'cd "$broker_home"' in exec_start
    assert "$broker_home/tools/egress-broker/ce_egress_self_review_broker.py" in exec_start

    unit_text = (repo_root / "deploy" / "systemd" / EGRESS_SELF_REVIEW_UNIT).read_text(
        encoding="utf-8"
    )
    assert "/workspace/creator-engine" not in unit_text
    assert "/home/ce-dev-" not in unit_text
    assert "/home/cedev" not in unit_text


def test_egress_self_review_unit_run_mode_is_env_driven_and_default_dev(repo_root: Path):
    unit = _read_unit(repo_root, EGRESS_SELF_REVIEW_UNIT)
    service = unit["Service"]
    exec_start = service["ExecStart"]

    assert "CE_EGRESS_RUN_MODE=dev" in service["Environment"]
    assert service["EnvironmentFile"].endswith("ce-egress-self-review.env")
    assert '--run-mode "${CE_EGRESS_RUN_MODE}"' in exec_start
    assert "strangeLoop" not in service["Environment"]


def test_installer_renders_egress_service_specific_env_files(tmp_path: Path, repo_root: Path):
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    (fake_repo / ".git").mkdir()
    fake_python = fake_repo / ".venv" / "bin" / "python"
    fake_python.parent.mkdir(parents=True)
    fake_python.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    fake_python.chmod(0o755)

    env_dir = tmp_path / "env"
    env_dir.mkdir()
    gate_env = env_dir / "gate-daemons.env"
    egress_broker_env = env_dir / "ce-egress-broker.env"
    egress_self_review_env = env_dir / "ce-egress-self-review.env"
    gate_env.write_text(
        "CE_GATE_REPO=creator-engine/creator-engine\n"
        "CE_GATE_AUTHORIZED_REVIEWERS=ce-dev-1\n"
        "CE_BELT_IDENTITY=ce-dev-4\n",
        encoding="utf-8",
    )
    egress_broker_env.write_text(
        "CE_EGRESS_BROKER_SOCKET=/run/ce-egress/dev-3.sock\n"
        "CE_EGRESS_BROKER_SEAT=dev-3\n"
        "CE_EGRESS_BROKER_REPO=/workspace/creator-engine\n"
        "CE_EGRESS_BROKER_CONFIG=/etc/ce-egress/broker-dev3.json\n",
        encoding="utf-8",
    )
    egress_self_review_env.write_text(
        "CE_EGRESS_SELF_REVIEW_SOCKET=/run/ce-egress/dev-3-review.sock\n"
        "CE_EGRESS_SELF_REVIEW_CONFIG=/etc/ce-egress/broker-dev3.json\n"
        "CE_EGRESS_RUN_MODE=dev\n",
        encoding="utf-8",
    )

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    systemctl_calls = tmp_path / "systemctl.calls"
    fake_systemctl = fake_bin / "systemctl"
    fake_systemctl.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$*\" >> \"$SYSTEMCTL_CALLS\"\n",
        encoding="utf-8",
    )
    fake_systemctl.chmod(0o755)

    unit_dir = tmp_path / "units"
    script = repo_root / "deploy" / "systemd" / "install-gate-daemons-systemd.sh"
    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "SYSTEMCTL_CALLS": str(systemctl_calls),
    }
    result = subprocess.run(
        [
            "bash",
            str(script),
            "--repo-root",
            str(fake_repo),
            "--unit-dir",
            str(unit_dir),
            "--env-file",
            str(gate_env),
            "--egress-broker-env-file",
            str(egress_broker_env),
            "--egress-self-review-env-file",
            str(egress_self_review_env),
            "--no-start",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    rendered_review = _read_unit_path(unit_dir / EGRESS_SELF_REVIEW_UNIT)
    rendered_broker = _read_unit_path(unit_dir / EGRESS_BROKER_UNIT)
    rendered_gate = _read_unit_path(unit_dir / "ce-integrator-daemon.service")

    assert rendered_review["Service"]["EnvironmentFile"] == str(egress_self_review_env)
    assert rendered_review["Service"]["WorkingDirectory"] == "/opt/ce-broker/creator-engine"
    assert "CE_EGRESS_RUN_MODE=dev" in rendered_review["Service"]["Environment"]
    assert "CE_BROKER_HOME=/opt/ce-broker/creator-engine" in rendered_review["Service"]["Environment"]
    assert '--run-mode "${CE_EGRESS_RUN_MODE}"' in rendered_review["Service"]["ExecStart"]
    assert rendered_broker["Service"]["EnvironmentFile"] == str(egress_broker_env)
    assert rendered_gate["Service"]["EnvironmentFile"] == str(gate_env)
    assert "start " not in systemctl_calls.read_text(encoding="utf-8")


def test_egress_socket_units_own_default_run_paths(repo_root: Path):
    broker_socket = _read_unit(repo_root, "ce-egress-broker.socket")
    review_socket = _read_unit(repo_root, "ce-egress-self-review.socket")

    assert broker_socket["Socket"]["ListenStream"] == "/run/ce-egress/dev-3.sock"
    assert review_socket["Socket"]["ListenStream"] == "/run/ce-egress/dev-3-review.sock"
