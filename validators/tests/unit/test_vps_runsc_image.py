"""Static/offline checks for the ce-ops#128 VPS herdr runsc image recipe."""

from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
VPS_DIR = REPO_ROOT / "deploy" / "vps-runsc"
DOCKERFILE = VPS_DIR / "Dockerfile"
DGX_DOCKERFILE = REPO_ROOT / "deploy" / "dgx-runsc" / "Dockerfile"
ENTRYPOINT = VPS_DIR / "herdr-harness-entrypoint.sh"
README = VPS_DIR / "README.md"


def _dockerfile() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


def _entrypoint() -> str:
    return ENTRYPOINT.read_text(encoding="utf-8")


def _readme() -> str:
    return README.read_text(encoding="utf-8")


def _entrypoint_harness_env_block() -> str:
    text = _entrypoint()
    match = re.search(r"\nharness_env=\(\n(?P<block>.*?)\n\)\n", text, re.S)
    assert match is not None
    return match.group("block")


def test_dockerfile_builds_herdr_from_source_in_compatible_stage() -> None:
    text = _dockerfile()

    assert (
        "FROM --platform=linux/amd64 ${RUST_SOURCE}:${RUST_VERSION}@sha256:${RUST_COMMIT_OR_DIGEST} "
        "AS herdr-builder"
    ) in text
    assert (
        "FROM --platform=linux/amd64 ${DEBIAN_SOURCE}:${DEBIAN_VERSION}@sha256:${DEBIAN_COMMIT_OR_DIGEST} "
        "AS runtime"
    ) in text
    assert "ARG HERDR_SOURCE=UNSET" in text
    assert "ARG HERDR_COMMIT_OR_DIGEST=UNSET" in text
    assert "ARG ZIG_TOOLCHAIN_SOURCE=UNSET" in text
    assert "ARG ZIG_TOOLCHAIN_VERSION=UNSET" in text
    assert 'git clone "${HERDR_SOURCE}" herdr' in text
    assert 'git checkout --detach "${HERDR_COMMIT_OR_DIGEST}"' in text
    assert "--branch" not in text
    assert "HERDR_COMMIT_OR_DIGEST=main" not in text
    assert "cargo build --locked --release --bin herdr" in text
    assert "ldd target/release/herdr" in text
    assert "target/release/herdr --help >/tmp/herdr-help.txt" in text
    assert (
        "COPY --from=herdr-builder /build/herdr/target/release/herdr /usr/local/bin/herdr"
        in text
    )
    # Repo-root build context (ce-ops#309): the entrypoint is COPYed by its
    # repo-relative path so the validator-venv stage can also COPY validators/**.
    assert "COPY deploy/vps-runsc/herdr-harness-entrypoint.sh" in text
    assert not re.search(r"COPY\s+(?:\./)?herdr\s+/usr/local/bin/herdr", text)


def test_dockerfile_bakes_ci_parity_validator_venv() -> None:
    """ce-ops#309: a contained seat must be able to self-run the validator
    preflight, so the image bakes a Python-3.14 venv with the validator runtime
    + dev deps installed OFFLINE from the vendored wheelhouses, plus libsodium
    for the worktree-lease Ed25519 gate (PCO-024). The cp314 wheels in
    validators/wheelhouse*/ cannot load on the image's system Python 3.11, so a
    same-Python pip install cannot reach CI parity."""
    text = _dockerfile()

    # Python-3.14 builder stage (matches deploy/oci/Dockerfile's base family).
    assert (
        "FROM --platform=linux/amd64 "
        "${OCI_CPYTHON_BASE_IMAGE_SOURCE}:${OCI_CPYTHON_BASE_IMAGE_VERSION}@sha256:${OCI_CPYTHON_BASE_IMAGE_COMMIT_OR_DIGEST} "
        "AS validator-venv-builder"
    ) in text
    # Offline install from BOTH vendored wheelhouses, mirroring validate.yml.
    assert "python3.14 -m venv /opt/ce-validator-venv" in text
    assert "--no-index --find-links validators/wheelhouse" in text
    assert "--find-links validators/wheelhouse-dev" in text
    assert "-r validators/requirements.txt" in text
    assert "-r validators/requirements-dev.txt" in text
    # No network resolution and no system-Python band-aid.
    assert "--break-system-packages" not in text
    # Relocate the venv + interpreter into the runtime and put it first on PATH.
    assert "COPY --from=validator-venv-builder /opt/ce-validator-venv /opt/ce-validator-venv" in text
    assert "COPY --from=validator-venv-builder /usr/local/bin/python3.14 /usr/local/bin/python3.14" in text
    assert 'ENV PATH="/opt/ce-validator-venv/bin:${PATH}"' in text
    # libsodium for the PCO-024 Ed25519 verification path.
    assert "libsodium23" in text
    assert "find_library('sodium')" in text
    assert "openssh-client" in text
    assert "command -v ssh-keygen" in text


def test_dockerfile_runtime_owns_socket_dir_and_fails_on_non_executables() -> None:
    text = _dockerfile()

    assert "install -d -m 0700" in text
    assert "/run/creator-engine/herdr" in text
    assert text.count("ENV HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock") == 1
    assert "USER ${CE_VPS_UID}:${CE_VPS_GID}" in text
    assert "tini" in text
    assert "nodejs" in text
    assert "python3" in text
    assert "procps" in text
    assert "install -d -m 0755 /usr/local/lib/node_modules/@openai" in text
    assert 'exec node /usr/local/lib/node_modules/@openai/codex/bin/codex.js "$@"' in text
    assert "test -x /usr/local/bin/codex" in text
    assert "node --version" in text
    assert "test -x /usr/local/bin/herdr" in text
    assert "test -x /usr/local/bin/herdr-harness-entrypoint.sh" in text
    assert (
        'ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/herdr-harness-entrypoint.sh"]'
        in text
    )
    assert 'CMD ["tui"]' in text


def test_dgx_dockerfile_preserves_full_preflight_toolchain() -> None:
    text = DGX_DOCKERFILE.read_text(encoding="utf-8")

    assert "ARG CODEX_VERSION=0.144.1" in text
    assert (
        "ARG CODEX_SHA256=9513fa3f5f4ad444ac1e40d972aef0e2664834ec54da987d54aba0dc2f13ea07"
        in text
    )
    assert "codex-aarch64-unknown-linux-musl.tar.gz" in text
    assert "check_for_update_on_startup = false" in text
    assert "openssh-client" in text
    assert "libsodium23" in text
    assert "command -v ssh-keygen" in text
    assert "command -v ce" in text
    assert "/opt/ce-validator-venv/bin/python --version | grep -q '^Python 3" in text
    assert "import pytest, yaml, jsonschema, xdist" in text
    assert "find_library('sodium')" in text


def test_dockerfile_installs_durable_governed_ce_launcher(tmp_path: Path) -> None:
    """ce-ops#572: the image, rather than a writable live layer, owns `ce`."""
    text = _dockerfile()

    launcher = re.search(
        r"printf '%s\\n' \\\n(?P<body>(?:\s+'.*' \\\n)+)\s+>/usr/local/bin/ce;",
        text,
    )
    assert launcher is not None
    launcher_lines = re.findall(
        r"^\s*'(?P<line>[^']*)' \\\s*$", launcher.group("body"), re.M
    )
    assert launcher_lines == [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "export PYTHONPATH=/workspace/creator-engine/validators",
        'exec /opt/ce-validator-venv/bin/python3 -m creator_engine_validator.ce_cli "$@"',
    ]

    # The last ownership/mode operations in the production RUN command must
    # still leave the wrapper root-owned and seat-executable.
    production_run = text[launcher.start() : text.index("\n\nUSER ", launcher.start())]
    operation_prefix = r"(?:^|;\s*\\?\s*)"
    ownership_operations = re.findall(
        operation_prefix + r"chown (?P<args>[^;]+)", production_run
    )
    mode_operations = re.findall(
        operation_prefix + r"chmod (?P<args>[^;]+)", production_run
    )
    assert ownership_operations
    assert mode_operations
    assert shlex.split(ownership_operations[-1].replace("\\\n", "").strip()) == [
        "root:root",
        "/usr/local/bin/ce",
    ]
    assert shlex.split(mode_operations[-1].replace("\\\n", "").strip()) == [
        "0755",
        "/usr/local/bin/ce",
    ]
    assert re.search(operation_prefix + r"test -x /usr/local/bin/ce", production_run)
    assert "root:root:755" in production_run

    # Parse the production exec rather than a separately-maintained expected
    # command.  The pinned interpreter and one quoted expansion are its only
    # allowed argv tokens.
    exec_line = launcher_lines[-1]
    assert exec_line.startswith("exec ")
    assert shlex.split(exec_line.removeprefix("exec ")) == [
        "/opt/ce-validator-venv/bin/python3",
        "-m",
        "creator_engine_validator.ce_cli",
        "$@",
    ]

    # Materialize the actual wrapper with only its absolute interpreter
    # replaced by a local argv recorder.  This proves the quoted "$@" keeps
    # whitespace and shell metacharacters as distinct arguments.
    fake_interpreter = tmp_path / "argv-recorder"
    argv_path = tmp_path / "argv"
    fake_interpreter.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"$@\" > \"$CE_TEST_ARGV_PATH\"\n",
        encoding="utf-8",
    )
    fake_interpreter.chmod(0o755)
    wrapper = tmp_path / "ce"
    wrapper.write_text(
        "\n".join(launcher_lines).replace(
            "/opt/ce-validator-venv/bin/python3", str(fake_interpreter), 1
        )
        + "\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    supplied_args = ["worker run", "semi;colon", "dollar$sign", "quote'\"mix"]
    result = subprocess.run(
        [str(wrapper), *supplied_args],
        check=False,
        env={"CE_TEST_ARGV_PATH": str(argv_path), "PATH": "/usr/bin:/bin"},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert argv_path.read_text(encoding="utf-8").splitlines() == [
        "-m",
        "creator_engine_validator.ce_cli",
        *supplied_args,
    ]


def test_entrypoint_is_fail_closed_and_routes_harness_through_herdr() -> None:
    text = _entrypoint()

    assert "set -euo pipefail" in text
    assert 'fail "missing harness mode args"' in text
    assert '[ -x "${HERDR_BIN}" ] || fail' in text
    assert '[ -x "${harness_bin}" ] || fail' in text
    assert '[ -d "${HERDR_SOCKET_DIR}" ] || fail' in text
    assert '[ -d "${CE_SEAT_LOG_DIR}" ] || fail "seat log directory is missing: ${CE_SEAT_LOG_DIR}"' in text
    assert 'CE_HERDR_SERVER_LOG="${CE_HERDR_SERVER_LOG:-${CE_SEAT_LOG_DIR}/herdr-server.log}"' in text
    assert ': >>"${CE_HERDR_SERVER_LOG}"' in text
    assert ': >>"${CE_CODEX_STDERR_LOG}"' in text
    assert 'XDG_CONFIG_HOME=${XDG_CONFIG_HOME:-${CE_SEAT_LOG_DIR}/xdg/config}' in text
    assert "stat -c '%a'" in text
    assert 'HERDR_SOCKET_PATH="${HERDR_SOCKET_PATH}" "${HERDR_BIN}" server >>"${CE_HERDR_SERVER_LOG}" 2>&1 &' in text
    assert "server --socket" not in text
    assert '[ -S "${HERDR_SOCKET_PATH}" ] || fail "herdr server did not create socket"' in text
    assert 'herdr_cli()' in text
    assert 'HERDR_SOCKET_PATH="${HERDR_SOCKET_PATH}" "${HERDR_BIN}" "$@"' in text
    assert 'herdr_cli workspace create --cwd "${PWD}" --label "${HERDR_WORKSPACE_NAME}"' in text
    assert "root_pane_id" in text
    assert "herdr_cli pane run" in text
    assert "fail \"could not start governed harness through herdr\"" in text
    assert 'exec "$@" 2>>"${CE_CODEX_STDERR_LOG}"' in text
    assert re.search(r"^exec \"\\$@\"$", text, re.M) is None


def test_entrypoint_selects_harness_from_ce_dgx_harness() -> None:
    text = _entrypoint()

    assert 'CE_DGX_HARNESS="${CE_DGX_HARNESS:-codex}"' in text
    assert 'harness_bin="${CE_DGX_HARNESS_BIN:-/usr/local/bin/codex}"' in text
    assert 'harness_bin="${CE_DGX_HARNESS_BIN:-/usr/local/bin/claude}"' in text
    assert 'fail "CE_DGX_HARNESS must be codex or claude' in text
    assert 'governed_harness=(/usr/bin/env -i "${harness_env[@]}" "${harness_bin}" "$@")' in text


def test_entrypoint_runs_governed_harness_with_explicit_safe_env() -> None:
    text = _entrypoint()
    block = _entrypoint_harness_env_block()

    assert 'governed_harness=(/usr/bin/env -i "${harness_env[@]}" "${harness_bin}" "$@")' in text
    assert '"HOME=${HOME:-/home/ce}"' in block
    assert (
        '"PATH=${PATH:-/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin}"'
        in block
    )
    assert '"TERM=${TERM:-xterm-256color}"' in block
    assert '"CE_DGX_HARNESS=${CE_DGX_HARNESS}"' in block
    assert '"XDG_CONFIG_HOME=${XDG_CONFIG_HOME:-${CE_SEAT_LOG_DIR}/xdg/config}"' in block
    assert '"XDG_STATE_HOME=${XDG_STATE_HOME:-${CE_SEAT_LOG_DIR}/xdg/state}"' in block
    assert '"XDG_CACHE_HOME=${XDG_CACHE_HOME:-${CE_SEAT_LOG_DIR}/xdg/cache}"' in block
    assert 'if [ -n "${CODEX_HOME:-}" ]; then' in text
    assert 'harness_env+=("CODEX_HOME=${CODEX_HOME}")' in text
    assert 'harness_env+=("CE_CODEX_STDERR_LOG=${CE_CODEX_STDERR_LOG}")' in text
    assert '/bin/sh -c \'exec "$@" 2>>"${CE_CODEX_STDERR_LOG}"\'' in text
    assert "env_scrub_args" not in text
    assert " -u " not in text
    assert "CE_DGX_HARNESS_MODE" not in text
    assert "--env" not in text
    assert 'herdr_cli pane run "${root_pane_id}"' in text


def test_entrypoint_harness_env_has_no_socket_or_ambient_ce_dgx_carriers() -> None:
    text = _entrypoint()
    harness_env_region = text[
        text.index("\nharness_env=(") : text.index("\nworkspace_json=")
    ]

    assert "HERDR_SOCKET_PATH" not in harness_env_region
    assert "HERDR_SOCKET" not in harness_env_region
    assert "SOCKET" not in harness_env_region
    assert "CE_DGX_HARNESS_MODE" not in harness_env_region
    assert set(re.findall(r"\bCE_DGX[A-Z0-9_]*", harness_env_region)) == {"CE_DGX_HARNESS"}

    dockerfile = _dockerfile()
    assert "ENV HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock" in dockerfile
    assert 'governed_harness=(/usr/bin/env -i "${harness_env[@]}"' in text


def test_readme_documents_contained_codex_config_and_node_package_mount() -> None:
    text = _readme()

    assert 'approval_policy = "never"' in text
    assert 'sandbox_mode = "danger-full-access"' in text
    assert "`workspace-write` mode starts an inner sandbox using bubblewrap/Landlock" in text
    assert "nested bubblewrap or Landlock cannot run inside runsc/gVisor" in text
    assert "container is the sandbox boundary for this recipe" in text
    assert "CE_VPS_CONTAINED_CODEX_CONFIG" in text
    assert "CE_VPS_CODEX_PACKAGE_ROOT" in text
    assert "/usr/local/lib/node_modules/@openai/codex" in text
    assert "standalone Codex bundles" in text


def test_readme_documents_plain_exact_name_herdr_route_and_scrubbed_pane() -> None:
    text = _readme()

    for command in (
        "docker exec ce-vps-codex herdr pane list",
        "docker exec ce-vps-codex herdr pane read w1:p1",
        "docker exec ce-vps-codex herdr pane send w1:p1",
    ):
        assert command in text
    assert "docker exec --env HERDR_SOCKET_PATH=" not in text
    assert "image owns the fixed client route" in text
    assert "governed pane still starts through `/usr/bin/env -i`" in text
    assert "omits `HERDR_SOCKET_PATH`, `HERDR_SOCKET`, and every other socket carrier" in text
