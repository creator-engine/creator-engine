from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


PREFLIGHT = Path("deploy/egress-broker/v1/preflight-peer-identity.sh")


def _write_fake_docker(bin_dir: Path) -> None:
    docker = bin_dir / "docker"
    docker.write_text(
        "#!/usr/bin/env sh\n"
        "set -eu\n"
        "case \"$1\" in\n"
        "  inspect)\n"
        "    test \"$2\" = --format && test \"$4\" = -- && test \"$5\" = fixture-seat || exit 2\n"
        "    test \"${FAKE_TARGET_EXISTS:-1}\" = 1 || exit 42\n"
        "    test \"${FAKE_FAIL_COMMAND:-}\" != inspect || exit 43\n"
        "    printf '%s\\n' \"$FAKE_TARGET_SEAT\"\n"
        "    ;;\n"
        "  exec)\n"
        "    test \"$2\" = -- && test \"$3\" = fixture-seat && test \"$4\" = id || exit 2\n"
        "    test \"${FAKE_TARGET_EXISTS:-1}\" = 1 || exit 42\n"
        "    case \"$5\" in\n"
        "      -u) test \"${FAKE_FAIL_COMMAND:-}\" != exec-uid || exit 44; printf '%s\\n' \"$FAKE_TARGET_UID\" ;;\n"
        "      -g) test \"${FAKE_FAIL_COMMAND:-}\" != exec-gid || exit 45; printf '%s\\n' \"$FAKE_TARGET_GID\" ;;\n"
        "      *) exit 2 ;;\n"
        "    esac\n"
        "    ;;\n"
        "  *) exit 2 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    docker.chmod(0o755)


def _write_env(
    path: Path,
    *,
    values: dict[str, str] | None = None,
    omit: tuple[str, ...] = (),
    extra_lines: tuple[str, ...] = (),
) -> None:
    env = {
        "CE_EGRESS_BROKER_SOCKET": "/run/ce-egress/dev-4.sock",
        "CE_EGRESS_BROKER_SEAT": "dev-4",
        "CE_EGRESS_BROKER_EXPECTED_PEER_UID": "1008",
        "CE_EGRESS_BROKER_EXPECTED_PEER_GID": "1008",
    }
    env.update(values or {})
    path.write_text(
        "\n".join(
            [f"{key}={value}" for key, value in env.items() if key not in omit] + list(extra_lines)
        )
        + "\n",
        encoding="utf-8",
    )


def _run_preflight(
    repo_root: Path,
    env_file: Path,
    bin_dir: Path,
    *,
    target_container: str = "fixture-seat",
    container_runtime: str = "docker",
    runtime_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ | {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "FAKE_TARGET_UID": "1008",
        "FAKE_TARGET_GID": "1008",
        "FAKE_TARGET_SEAT": "dev-4",
        "FAKE_TARGET_EXISTS": "1",
    }
    env.update(runtime_env or {})
    return subprocess.run(
        [
            str(repo_root / PREFLIGHT),
            "--env-file",
            str(env_file),
            "--target-container",
            target_container,
            "--container-runtime",
            container_runtime,
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_preflight_accepts_controlled_matching_seat_and_identity(repo_root: Path, tmp_path: Path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_docker(bin_dir)
    env_file = tmp_path / "broker.env"
    _write_env(env_file)

    result = _run_preflight(repo_root, env_file, bin_dir)

    assert result.returncode == 0, result.stderr
    assert "PASS: egress peer identity preflight v1 matched seat dev-4 target fixture-seat" in result.stdout


@pytest.mark.parametrize(
    ("case", "values", "omit", "extra_lines", "target_container", "container_runtime", "runtime_env", "message"),
    (
        (
            "uid mismatch",
            {"CE_EGRESS_BROKER_EXPECTED_PEER_UID": "1007"},
            (),
            (),
            "fixture-seat",
            "docker",
            {},
            "configured peer uid 1007 differs from target uid 1008",
        ),
        (
            "gid mismatch",
            {},
            (),
            (),
            "fixture-seat",
            "docker",
            {"FAKE_TARGET_GID": "1007"},
            "configured peer gid 1008 differs from target gid 1007",
        ),
        (
            "same identity unrelated seat",
            {},
            (),
            (),
            "fixture-seat",
            "docker",
            {"FAKE_TARGET_SEAT": "dev-3"},
            "configured broker seat dev-4 differs from target seat label dev-3",
        ),
        (
            "missing target",
            {},
            (),
            (),
            "missing-seat",
            "docker",
            {},
            "could not read Creator Engine seat label from target container: missing-seat",
        ),
        (
            "missing runtime",
            {},
            (),
            (),
            "fixture-seat",
            "missing-container-runtime",
            {},
            "container runtime not found: missing-container-runtime",
        ),
        (
            "malformed uid configuration",
            {"CE_EGRESS_BROKER_EXPECTED_PEER_UID": "1008x"},
            (),
            (),
            "fixture-seat",
            "docker",
            {},
            "configured CE_EGRESS_BROKER_EXPECTED_PEER_UID must be a decimal integer",
        ),
        (
            "malformed gid configuration",
            {"CE_EGRESS_BROKER_EXPECTED_PEER_GID": "1008x"},
            (),
            (),
            "fixture-seat",
            "docker",
            {},
            "configured CE_EGRESS_BROKER_EXPECTED_PEER_GID must be a decimal integer",
        ),
        (
            "malformed uid output",
            {},
            (),
            (),
            "fixture-seat",
            "docker",
            {"FAKE_TARGET_UID": "1008x"},
            "target container returned a non-decimal uid",
        ),
        (
            "malformed gid output",
            {},
            (),
            (),
            "fixture-seat",
            "docker",
            {"FAKE_TARGET_GID": "1008x"},
            "target container returned a non-decimal gid",
        ),
        (
            "duplicate environment key",
            {},
            (),
            ("CE_EGRESS_BROKER_EXPECTED_PEER_UID=1008",),
            "fixture-seat",
            "docker",
            {},
            "duplicate environment key: CE_EGRESS_BROKER_EXPECTED_PEER_UID",
        ),
        (
            "missing environment key",
            {},
            ("CE_EGRESS_BROKER_EXPECTED_PEER_GID",),
            (),
            "fixture-seat",
            "docker",
            {},
            "missing environment key: CE_EGRESS_BROKER_EXPECTED_PEER_GID",
        ),
        (
            "container command failure",
            {},
            (),
            (),
            "fixture-seat",
            "docker",
            {"FAKE_FAIL_COMMAND": "exec-gid"},
            "could not read gid from target container: fixture-seat",
        ),
    ),
    ids=lambda case: case,
)
def test_preflight_fails_closed_for_controlled_rejections(
    repo_root: Path,
    tmp_path: Path,
    case: str,
    values: dict[str, str],
    omit: tuple[str, ...],
    extra_lines: tuple[str, ...],
    target_container: str,
    container_runtime: str,
    runtime_env: dict[str, str],
    message: str,
):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_docker(bin_dir)
    env_file = tmp_path / "broker.env"
    _write_env(env_file, values=values, omit=omit, extra_lines=extra_lines)

    result = _run_preflight(
        repo_root,
        env_file,
        bin_dir,
        target_container=target_container,
        container_runtime=container_runtime,
        runtime_env=runtime_env,
    )

    assert result.returncode == 1, case
    assert message in result.stderr
