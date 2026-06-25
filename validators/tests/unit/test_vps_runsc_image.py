"""Static/offline checks for the ce-ops#128 VPS herdr runsc image recipe."""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
VPS_DIR = REPO_ROOT / "deploy" / "vps-runsc"
DOCKERFILE = VPS_DIR / "Dockerfile"
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

    assert "FROM --platform=linux/amd64 rust:1-bookworm AS herdr-builder" in text
    assert "FROM --platform=linux/amd64 debian:bookworm-slim AS runtime" in text
    assert "ARG HERDR_SOURCE_REPO=https://github.com/creator-engine/herdr-ce.git" in text
    assert "ARG HERDR_SOURCE_REF=ff924966bd789afabec1a52d74f24392f45838ef" in text
    assert "ARG ZIG_VERSION=0.15.2" in text
    assert 'git clone "${HERDR_SOURCE_REPO}" herdr' in text
    assert 'git checkout --detach "${HERDR_SOURCE_REF}"' in text
    assert "--branch" not in text
    assert "HERDR_SOURCE_REF=main" not in text
    assert "cargo build --locked --release --bin herdr" in text
    assert "ldd target/release/herdr" in text
    assert "target/release/herdr --help >/tmp/herdr-help.txt" in text
    assert (
        "COPY --from=herdr-builder /build/herdr/target/release/herdr /usr/local/bin/herdr"
        in text
    )
    assert "COPY herdr" in text
    assert not re.search(r"COPY\s+(?:\./)?herdr\s+/usr/local/bin/herdr", text)


def test_dockerfile_runtime_owns_socket_dir_and_fails_on_non_executables() -> None:
    text = _dockerfile()

    assert "install -d -m 0700" in text
    assert "/run/creator-engine/herdr" in text
    assert "ENV HERDR_SOCKET_PATH" not in text
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


def test_entrypoint_is_fail_closed_and_routes_harness_through_herdr() -> None:
    text = _entrypoint()

    assert "set -euo pipefail" in text
    assert 'fail "missing harness mode args"' in text
    assert '[ -x "${HERDR_BIN}" ] || fail' in text
    assert '[ -x "${harness_bin}" ] || fail' in text
    assert '[ -d "${HERDR_SOCKET_DIR}" ] || fail' in text
    assert '[ -d "${CE_SEAT_LOG_DIR}" ] || fail "seat log directory is missing: ${CE_SEAT_LOG_DIR}"' in text
    assert ': >>"${CE_CODEX_STDERR_LOG}"' in text
    assert 'XDG_CONFIG_HOME=${XDG_CONFIG_HOME:-${CE_SEAT_LOG_DIR}/xdg/config}' in text
    assert "stat -c '%a'" in text
    assert 'HERDR_SOCKET_PATH="${HERDR_SOCKET_PATH}" "${HERDR_BIN}" server &' in text
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
    assert 'harness_bin="/usr/local/bin/codex"' in text
    assert 'harness_bin="/usr/local/bin/claude"' in text
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
