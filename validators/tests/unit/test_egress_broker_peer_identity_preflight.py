from __future__ import annotations

import os
import subprocess
from pathlib import Path


PREFLIGHT = Path("deploy/egress-broker/v1/preflight-peer-identity.sh")


def _write_fake_docker(bin_dir: Path) -> None:
    docker = bin_dir / "docker"
    docker.write_text(
        "#!/usr/bin/env sh\n"
        "test \"$1\" = exec && test \"$2\" = -- && test \"$3\" = fixture-seat\n"
        "case \"$5\" in\n"
        "  -u) printf '%s\\n' \"$FAKE_TARGET_UID\" ;;\n"
        "  -g) printf '%s\\n' \"$FAKE_TARGET_GID\" ;;\n"
        "  *) exit 2 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    docker.chmod(0o755)


def _write_env(path: Path, *, uid: str, gid: str) -> None:
    path.write_text(
        "\n".join(
            (
                "CE_EGRESS_BROKER_SOCKET=/run/ce-egress/dev-4.sock",
                "CE_EGRESS_BROKER_SEAT=dev-4",
                f"CE_EGRESS_BROKER_EXPECTED_PEER_UID={uid}",
                f"CE_EGRESS_BROKER_EXPECTED_PEER_GID={gid}",
            )
        )
        + "\n",
        encoding="utf-8",
    )


def _run_preflight(repo_root: Path, env_file: Path, bin_dir: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ | {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "FAKE_TARGET_UID": "1008",
        "FAKE_TARGET_GID": "1008",
    }
    return subprocess.run(
        [str(repo_root / PREFLIGHT), "--env-file", str(env_file), "--target-container", "fixture-seat"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_preflight_refuses_controlled_identity_mismatch(repo_root: Path, tmp_path: Path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_docker(bin_dir)
    env_file = tmp_path / "broker.env"
    _write_env(env_file, uid="1007", gid="1008")

    result = _run_preflight(repo_root, env_file, bin_dir)

    assert result.returncode == 1
    assert "refusing installation: configured peer uid 1007 differs from target uid 1008" in result.stderr


def test_preflight_accepts_controlled_matching_identity(repo_root: Path, tmp_path: Path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_docker(bin_dir)
    env_file = tmp_path / "broker.env"
    _write_env(env_file, uid="1008", gid="1008")

    result = _run_preflight(repo_root, env_file, bin_dir)

    assert result.returncode == 0
    assert "PASS: egress peer identity preflight v1 matched target fixture-seat" in result.stdout
