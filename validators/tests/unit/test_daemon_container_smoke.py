from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _write_fake_engine(path: Path, calls_file: Path) -> None:
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f'calls_file="{calls_file}"\n'
        'printf "CALL" >> "$calls_file"\n'
        'for arg in "$@"; do printf "\\t%s" "$arg" >> "$calls_file"; done\n'
        'printf "\\n" >> "$calls_file"\n'
        'case "${1:-}" in\n'
        "  info)\n"
        "    exit 0\n"
        "    ;;\n"
        "  stop)\n"
        '    container_name="${@: -1}"\n'
        '    touch "${TMPDIR:-/tmp}/ce-smoke-stop-${container_name:-container}"\n'
        "    exit 0\n"
        "    ;;\n"
        "  run)\n"
        '    container_name=""\n'
        '    state_root=""\n'
        '    previous=""\n'
        '    for arg in "$@"; do\n'
        '      if [[ "$previous" == "--name" ]]; then container_name="$arg"; fi\n'
        '      if [[ "$previous" == "--volume" && "$arg" == *":/ce/state" ]]; then state_root="${arg%%:/ce/state}"; fi\n'
        '      previous="$arg"\n'
        "    done\n"
        '    mkdir -p "$state_root/daemon-leases"\n'
        '    lease="$state_root/daemon-leases/conveyor-daemon.lease"\n'
        '    printf \'{"holder_id":"fake-smoke","pid":1,"host":"fake","acquired_at":1,"heartbeat_at":1}\\n\' > "$lease"\n'
        '    stop_file="${TMPDIR:-/tmp}/ce-smoke-stop-${container_name}"\n'
        '    for _ in $(seq 1 100); do\n'
        '      [[ -e "$stop_file" ]] && break\n'
        "      sleep 0.02\n"
        "    done\n"
        '    rm -f "$lease" "$stop_file"\n'
        "    exit 0\n"
        "    ;;\n"
        "esac\n"
        "exit 0\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def test_smoke_script_skips_when_container_engine_is_missing(tmp_path: Path) -> None:
    script = _repo_root() / "deploy" / "daemons" / "smoke-daemon-container.sh"
    env = os.environ.copy()
    env["CE_CONTAINER_ENGINE"] = "ce-missing-docker-for-smoke-test"

    proc = subprocess.run(
        ["bash", str(script), str(tmp_path / "state")],
        cwd=_repo_root(),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert proc.returncode == 77
    assert "SKIP: container engine not found: ce-missing-docker-for-smoke-test" in proc.stderr


def test_smoke_script_runs_two_one_shot_passes_through_canonical_adapter(tmp_path: Path) -> None:
    fake_engine = tmp_path / "podman"
    calls_file = tmp_path / "engine-calls.txt"
    _write_fake_engine(fake_engine, calls_file)
    state_root = tmp_path / "state"
    script = _repo_root() / "deploy" / "daemons" / "smoke-daemon-container.sh"
    env = os.environ.copy()
    env.update(
        {
            "CE_CONTAINER_ENGINE": str(fake_engine),
            "CE_DAEMON_REPO_ROOT": str(_repo_root()),
            "TMPDIR": str(tmp_path),
        }
    )

    proc = subprocess.run(
        ["bash", str(script), str(state_root)],
        cwd=_repo_root(),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert proc.returncode == 0, proc.stderr
    calls = calls_file.read_text(encoding="utf-8")
    assert calls.count("\trun\t") == 2
    assert calls.count("\tstop\t--time\t20\tce-daemon-smoke-") == 2
    assert "\t--tmpfs\t/run/creator-engine/conveyor-daemon-secret:rw,size=1m,mode=0700,uid=10001,gid=10001" in calls
    assert "\t--env\tCE_DAEMON_LEASE_ROOT=/ce/state/daemon-leases" in calls
    assert "\t/workspace/creator-engine/deploy/conveyor-daemon/launch-conveyor-daemon.sh\t--one-shot" in calls
    assert not (state_root / "daemon-leases" / "conveyor-daemon.lease").exists()
    assert "OK: daemon container stateful smoke passed" in proc.stdout
