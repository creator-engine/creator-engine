"""Static/offline checks for the ce-ops#128 VPS herdr runsc image recipe."""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
VPS_DIR = REPO_ROOT / "deploy" / "vps-runsc"
DOCKERFILE = VPS_DIR / "Dockerfile"
ENTRYPOINT = VPS_DIR / "herdr-harness-entrypoint.sh"


def _dockerfile() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


def _entrypoint() -> str:
    return ENTRYPOINT.read_text(encoding="utf-8")


def test_dockerfile_builds_herdr_from_source_in_compatible_stage() -> None:
    text = _dockerfile()

    assert "FROM --platform=linux/amd64 rust:1-bookworm AS herdr-builder" in text
    assert "FROM --platform=linux/amd64 debian:bookworm-slim AS runtime" in text
    assert "ARG HERDR_SOURCE_REPO=https://github.com/creator-engine/herdr-ce.git" in text
    assert "ARG HERDR_SOURCE_REF=main" in text
    assert 'git clone --depth 1 --branch "${HERDR_SOURCE_REF}" "${HERDR_SOURCE_REPO}" .' in text
    assert "cargo build --locked --release" in text
    assert "COPY --from=herdr-builder /usr/local/bin/herdr /usr/local/bin/herdr" in text
    assert "COPY herdr" in text
    assert not re.search(r"COPY\s+(?:\./)?herdr\s+/usr/local/bin/herdr", text)


def test_dockerfile_runtime_owns_socket_dir_and_fails_on_non_executables() -> None:
    text = _dockerfile()

    assert "install -d -m 0700" in text
    assert "/run/creator-engine/herdr" in text
    assert "ENV HERDR_SOCKET_PATH" not in text
    assert "USER ${CE_VPS_UID}:${CE_VPS_GID}" in text
    assert "tini" in text
    assert "python3" in text
    assert "procps" in text
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
    assert "exec \"$@\"" not in text


def test_entrypoint_selects_harness_from_ce_dgx_harness() -> None:
    text = _entrypoint()

    assert 'CE_DGX_HARNESS="${CE_DGX_HARNESS:-codex}"' in text
    assert 'harness_bin="/usr/local/bin/codex"' in text
    assert 'harness_bin="/usr/local/bin/claude"' in text
    assert 'fail "CE_DGX_HARNESS must be codex or claude' in text
    assert 'governed_harness=(/usr/bin/env "${env_scrub_args[@]}" -- "${harness_bin}" "$@")' in text


def test_entrypoint_scrubs_raw_and_ce_dgx_socket_carriers_dynamically() -> None:
    text = _entrypoint()

    assert "env_scrub_args=(-u HERDR_SOCKET_PATH -u HERDR_SOCKET)" in text
    assert "CE_DGX*SOCKET*)" in text
    assert 'env_scrub_args+=(-u "${name}")' in text
    assert "CE_DGX_HERDR_SOCKET_PATH" not in text
    assert "scrubbed_env" not in text
    assert "--env" not in text
    assert 'herdr_cli pane run "${root_pane_id}"' in text
