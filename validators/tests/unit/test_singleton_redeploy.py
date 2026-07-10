from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "deploy" / "singleton-redeploy" / "redeploy-singleton.sh"


def _run_bash(source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-lc", source],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_render_queue_unit_renders_service_user_and_unit_environment(tmp_path: Path):
    env_file = tmp_path / "ce-queue-daemon.env"
    env_file.write_text("GH_TOKEN=placeholder\nBAO_CACERT=/etc/ssl/certs/ca-certificates.crt\n", encoding="utf-8")
    os.chmod(env_file, 0o600)
    rendered = tmp_path / "ce-queue-daemon.service"
    env_out = tmp_path / "unit-env.out"

    proc = _run_bash(
        "\n".join(
            [
                "set -euo pipefail",
                f"source {shlex.quote(str(SCRIPT))}",
                (
                    "render_queue_unit "
                    f"{shlex.quote(str(REPO_ROOT))} "
                    f"{shlex.quote(str(env_file))} "
                    "ce-portable "
                    f"{shlex.quote(str(rendered))}"
                ),
                f"unit_environment_assignments {shlex.quote(str(rendered))} > {shlex.quote(str(env_out))}",
            ]
        )
    )

    assert proc.returncode == 0, proc.stderr
    unit_text = rendered.read_text(encoding="utf-8")
    env_text = env_out.read_text(encoding="utf-8")
    assert "User=ce-portable\n" in unit_text
    assert f"EnvironmentFile={env_file}\n" in unit_text
    assert f"Environment=CE_QUEUE_DAEMON_REPO_ROOT={REPO_ROOT}\n" in unit_text
    assert f"CE_DAEMON_REPO_ROOT={REPO_ROOT}\n" in env_text


def test_render_materializer_unit_renders_service_user_and_unit_environment(tmp_path: Path):
    env_file = tmp_path / "ce-materializer.env"
    env_file.write_text("CE_GATE_REPO=creator-engine/creator-engine\n", encoding="utf-8")
    os.chmod(env_file, 0o600)
    rendered = tmp_path / "ce-materializer.service"
    env_out = tmp_path / "unit-env.out"

    proc = _run_bash(
        "\n".join(
            [
                "set -euo pipefail",
                f"source {shlex.quote(str(SCRIPT))}",
                (
                    "render_materializer_unit "
                    f"{shlex.quote(str(REPO_ROOT))} "
                    f"{shlex.quote(str(env_file))} "
                    "ce-portable "
                    f"{shlex.quote(str(rendered))}"
                ),
                f"unit_environment_assignments {shlex.quote(str(rendered))} > {shlex.quote(str(env_out))}",
            ]
        )
    )

    assert proc.returncode == 0, proc.stderr
    unit_text = rendered.read_text(encoding="utf-8")
    env_text = env_out.read_text(encoding="utf-8")
    assert "User=ce-portable\n" in unit_text
    assert f"EnvironmentFile={env_file}\n" in unit_text
    assert f"Environment=CE_MATERIALIZER_REPO_ROOT={REPO_ROOT}\n" in unit_text
    assert f"CE_DAEMON_REPO_ROOT={REPO_ROOT}\n" in env_text
    assert "CE_MATERIALIZER_DRY_RUN=1\n" in env_text


def test_option_a_materializer_dry_run_prints_real_redeploy_plan(tmp_path: Path):
    env_file = tmp_path / "ce-materializer.env"
    env_file.write_text("CE_GATE_REPO=creator-engine/creator-engine\nCE_MATERIALIZER_DRY_RUN=1\n", encoding="utf-8")
    os.chmod(env_file, 0o600)

    proc = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--daemon",
            "option-a-materializer",
            "--dry-run",
            "--repo-root",
            str(REPO_ROOT),
            "--env-file",
            str(env_file),
            "--service-user",
            "ce-portable",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert "Dry-run redeploy plan for option-a-materializer" in proc.stdout
    assert f"Would verify env file exists with mode 0600: {env_file}" in proc.stdout
    assert "Would render service user: ce-portable" in proc.stdout
    assert f"Would install or update systemd unit: {REPO_ROOT}/deploy/materializer/ce-materializer.service" in proc.stdout
    assert "Would enable service: ce-materializer.service" in proc.stdout
    assert "Would wait up to 30 seconds for active state: ce-materializer.service" in proc.stdout
    assert f"Would run health probe: {REPO_ROOT}/deploy/materializer/launch-materializer.sh --health" in proc.stdout
    assert "Materializer remains dry-run only; arming is not performed by this redeploy" in proc.stdout
    assert "not deployed yet" not in proc.stdout


def test_unit_environment_assignments_preserves_quoted_value_with_spaces(tmp_path: Path):
    unit = tmp_path / "quoted.service"
    env_out = tmp_path / "unit-env.out"
    unit.write_text('[Service]\nEnvironment="CE_TEST_VALUE=value with spaces"\n', encoding="utf-8")

    proc = _run_bash(
        "\n".join(
            [
                "set -euo pipefail",
                f"source {shlex.quote(str(SCRIPT))}",
                f"unit_environment_assignments {shlex.quote(str(unit))} > {shlex.quote(str(env_out))}",
            ]
        )
    )

    assert proc.returncode == 0, proc.stderr
    assert env_out.read_text(encoding="utf-8") == "CE_TEST_VALUE=value with spaces\n"


def test_run_queue_health_probe_unit_environment_wins_over_env_file(tmp_path: Path):
    repo = tmp_path / "repo"
    queue_dir = repo / "deploy" / "queue-daemon"
    queue_dir.mkdir(parents=True)
    (repo / ".git").write_text("gitdir: /tmp/example-worktree-gitdir\n", encoding="utf-8")
    (queue_dir / "ce-queue-daemon.service").write_text(
        "\n".join(
            [
                "[Service]",
                "User=creator-engine",
                "EnvironmentFile=/etc/creator-engine/ce-queue-daemon.env",
                "Environment=CE_TEST_PRECEDENCE=unit",
                "",
            ]
        ),
        encoding="utf-8",
    )
    launch = queue_dir / "launch-queue-daemon.sh"
    launch.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        '[[ "${1:-}" == "--health" ]]\n'
        'printf "CE_TEST_PRECEDENCE=%s\\n" "$CE_TEST_PRECEDENCE"\n',
        encoding="utf-8",
    )
    launch.chmod(0o755)
    env_file = tmp_path / "ce-queue-daemon.env"
    env_file.write_text("CE_TEST_PRECEDENCE=env-file\n", encoding="utf-8")
    os.chmod(env_file, 0o600)

    proc = _run_bash(
        "\n".join(
            [
                "set -euo pipefail",
                f"source {shlex.quote(str(SCRIPT))}",
                (
                    "run_queue_health_probe "
                    f"{shlex.quote(str(repo))} "
                    f"{shlex.quote(str(env_file))} "
                    "ce-portable"
                ),
            ]
        )
    )

    assert proc.returncode == 0, proc.stderr
    assert "CE_TEST_PRECEDENCE=unit\n" in proc.stdout


def test_run_materializer_health_probe_unit_environment_wins_over_env_file(tmp_path: Path):
    repo = tmp_path / "repo"
    materializer_dir = repo / "deploy" / "materializer"
    materializer_dir.mkdir(parents=True)
    (repo / ".git").write_text("gitdir: /tmp/example-worktree-gitdir\n", encoding="utf-8")
    (materializer_dir / "ce-materializer.service").write_text(
        "\n".join(
            [
                "[Service]",
                "User=creator-engine",
                "EnvironmentFile=/etc/creator-engine/ce-materializer.env",
                "Environment=CE_TEST_PRECEDENCE=unit",
                "",
            ]
        ),
        encoding="utf-8",
    )
    launch = materializer_dir / "launch-materializer.sh"
    launch.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        '[[ "${1:-}" == "--health" ]]\n'
        'printf "CE_TEST_PRECEDENCE=%s\\n" "$CE_TEST_PRECEDENCE"\n',
        encoding="utf-8",
    )
    launch.chmod(0o755)
    env_file = tmp_path / "ce-materializer.env"
    env_file.write_text("CE_TEST_PRECEDENCE=env-file\n", encoding="utf-8")
    os.chmod(env_file, 0o600)

    proc = _run_bash(
        "\n".join(
            [
                "set -euo pipefail",
                f"source {shlex.quote(str(SCRIPT))}",
                (
                    "run_materializer_health_probe "
                    f"{shlex.quote(str(repo))} "
                    f"{shlex.quote(str(env_file))} "
                    "ce-portable"
                ),
            ]
        )
    )

    assert proc.returncode == 0, proc.stderr
    assert "CE_TEST_PRECEDENCE=unit\n" in proc.stdout


def test_validate_service_user_rejects_invalid_systemd_usernames():
    proc = _run_bash(
        "\n".join(
            [
                "set -euo pipefail",
                f"source {shlex.quote(str(SCRIPT))}",
                "validate_service_user 'Root User'",
            ]
        )
    )

    assert proc.returncode != 0
    assert "service user must match" in proc.stderr


def test_validate_repo_root_accepts_git_file_worktree(tmp_path: Path):
    repo = tmp_path / "linked-worktree"
    unit_dir = repo / "deploy" / "queue-daemon"
    unit_dir.mkdir(parents=True)
    (repo / ".git").write_text("gitdir: /tmp/example-worktree-gitdir\n", encoding="utf-8")
    (unit_dir / "ce-queue-daemon.service").write_text("[Service]\n", encoding="utf-8")
    launch = unit_dir / "launch-queue-daemon.sh"
    launch.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    launch.chmod(0o755)

    proc = _run_bash(
        "\n".join(
            [
                "set -euo pipefail",
                f"source {shlex.quote(str(SCRIPT))}",
                f"validate_repo_root {shlex.quote(str(repo))}",
            ]
        )
    )

    assert proc.returncode == 0, proc.stderr
