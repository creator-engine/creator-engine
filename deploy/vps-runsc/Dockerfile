# Build context: the REPOSITORY ROOT (not deploy/vps-runsc/). The validator
# venv stage below COPYs validators/** (pyproject + sources + offline
# wheelhouses), so this image must be built with the repo root as the context:
#   docker build -f deploy/vps-runsc/Dockerfile -t creator-engine/codex-runsc:x86_64 .
# This mirrors deploy/oci/Dockerfile, which also COPYs validators/** from root.
#
# CI-parity validator venv builder (ce-ops#309). CI runs the validator on
# Python 3.14 (.github/workflows/validate.yml) against the checked-in offline
# wheelhouses, and validators/pyproject.toml pins requires-python >=3.14. The
# bookworm runtime below ships Python 3.11, whose ABI cannot load the cp314
# wheels in validators/wheelhouse*/. We therefore bake a Python-3.14 venv from
# the SAME python:3.14 bookworm base used by deploy/oci/Dockerfile, install the
# validator runtime + dev deps OFFLINE from the vendored wheelhouses (no network
# — the seat runs under gVisor), and relocate it into the runtime stage. This
# supersedes the prior system-Python pip install into 3.11 (ce-ops#261), which
# was neither CI-parity (3.11 vs 3.14, online resolution vs the vendored cp314
# wheels) nor able to satisfy the worktree-lease Ed25519 gate (libsodium).
FROM --platform=linux/amd64 python:3.14-slim-bookworm@sha256:4ff4b92a68355dbdb52584ab3391dff8d371a61d4e063468bfd0130e3189c6d9 AS validator-venv-builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /src

COPY validators/pyproject.toml validators/pyproject.toml
COPY validators/creator_engine_validator validators/creator_engine_validator
COPY validators/requirements.txt validators/requirements.txt
COPY validators/requirements-dev.txt validators/requirements-dev.txt
COPY validators/wheelhouse validators/wheelhouse
COPY validators/wheelhouse-dev validators/wheelhouse-dev

# Offline, CI-parity install: runtime floor first, then the dev/test toolchain,
# exactly mirroring the two pip steps in .github/workflows/validate.yml. The
# venv lives at a fixed path so it relocates cleanly into the runtime stage.
RUN set -eux; \
    python3.14 -m venv /opt/ce-validator-venv; \
    /opt/ce-validator-venv/bin/pip install \
      --no-index --find-links validators/wheelhouse \
      -r validators/requirements.txt; \
    /opt/ce-validator-venv/bin/pip install \
      --no-index \
      --find-links validators/wheelhouse \
      --find-links validators/wheelhouse-dev \
      -r validators/requirements-dev.txt; \
    /opt/ce-validator-venv/bin/python -c "import pytest, yaml, jsonschema, xdist; print('validator venv imports OK')"; \
    /opt/ce-validator-venv/bin/pytest --version

FROM --platform=linux/amd64 rust:1-bookworm@sha256:c993d32d95cc146bd12c84d66f0b924a6a96f3988325f39c144f2f9893dea120 AS herdr-builder

ARG HERDR_SOURCE_REPO=https://github.com/creator-engine/herdr-ce.git
ARG HERDR_SOURCE_REF=ff924966bd789afabec1a52d74f24392f45838ef
ARG ZIG_VERSION=0.15.2

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      git \
      xz-utils; \
    rm -rf /var/lib/apt/lists/*; \
    arch="$(dpkg --print-architecture)"; \
    case "${arch}" in \
      arm64) zig_arch="aarch64"; zig_sha256="958ed7d1e00d0ea76590d27666efbf7a932281b3d7ba0c6b01b0ff26498f667f" ;; \
      amd64) zig_arch="x86_64"; zig_sha256="02aa270f183da276e5b5920b1dac44a63f1a49e55050ebde3aecc9eb82f93239" ;; \
      *) echo "unsupported Zig architecture: ${arch}" >&2; exit 66 ;; \
    esac; \
    zig_url="https://ziglang.org/download/${ZIG_VERSION}/zig-${zig_arch}-linux-${ZIG_VERSION}.tar.xz"; \
    curl -fsSL "${zig_url}" -o /tmp/zig.tar.xz; \
    echo "${zig_sha256}  /tmp/zig.tar.xz" | sha256sum -c -; \
    mkdir -p /opt/zig; \
    tar -xJf /tmp/zig.tar.xz -C /opt/zig --strip-components=1; \
    rm /tmp/zig.tar.xz

ENV PATH="/opt/zig:${PATH}"

WORKDIR /build

RUN set -eux; \
    git clone "${HERDR_SOURCE_REPO}" herdr; \
    cd herdr; \
    git checkout --detach "${HERDR_SOURCE_REF}"; \
    cargo build --locked --release --bin herdr; \
    ldd target/release/herdr; \
    target/release/herdr --help >/tmp/herdr-help.txt

FROM --platform=linux/amd64 debian:bookworm-slim@sha256:1def178129dfb5f24db43afbf2fcac04530012e3264ba4ff81c71184e17a9ee4 AS runtime

ARG CE_VPS_USER=cedev
ARG CE_VPS_UID=1000
ARG CE_VPS_GID=1000

ENV DEBIAN_FRONTEND=noninteractive
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      bash \
      ca-certificates \
      curl \
      git \
      less \
      libsodium23 \
      nodejs \
      procps \
      psmisc \
      python3 \
      tini; \
    rm -rf /var/lib/apt/lists/*; \
    group_name="$(getent group "${CE_VPS_GID}" | cut -d: -f1 || true)"; \
    if [ -z "${group_name}" ]; then \
      groupadd --gid "${CE_VPS_GID}" "${CE_VPS_USER}"; \
      group_name="${CE_VPS_USER}"; \
    fi; \
    useradd --uid "${CE_VPS_UID}" --gid "${CE_VPS_GID}" --create-home --shell /bin/bash "${CE_VPS_USER}"; \
    install -d -m 0755 -o "${CE_VPS_UID}" -g "${CE_VPS_GID}" /workspace/creator-engine; \
    install -d -m 0700 -o "${CE_VPS_UID}" -g "${CE_VPS_GID}" /run/creator-engine/herdr; \
    git config --system --add safe.directory /workspace/creator-engine

# CI-parity validator toolchain (ce-ops#309). Relocate the Python-3.14 venv and
# its base interpreter from the builder stage. python:3.14-slim-bookworm shares
# this Debian bookworm base, so the interpreter is binary-compatible and the
# venv's base reference stays valid when python3.14 lands at the same /usr/local
# path. The venv carries pytest + the full validator runtime/dev closure from
# the vendored cp314 wheelhouses, matching .github/workflows/validate.yml. The
# venv is placed FIRST on PATH so `python`/`pytest`/`creator-engine-validator`
# resolve to the CI-parity interpreter; the bookworm system python3 (3.11) is
# retained for herdr/launcher shell helpers.
COPY --from=validator-venv-builder /usr/local/bin/python3.14 /usr/local/bin/python3.14
COPY --from=validator-venv-builder /usr/local/lib/libpython3.14.so.1.0 /usr/local/lib/libpython3.14.so.1.0
COPY --from=validator-venv-builder /usr/local/lib/python3.14 /usr/local/lib/python3.14
COPY --from=validator-venv-builder /opt/ce-validator-venv /opt/ce-validator-venv

ENV CE_VALIDATOR_VENV=/opt/ce-validator-venv
ENV PATH="/opt/ce-validator-venv/bin:${PATH}"

RUN set -eux; \
    ldconfig; \
    /opt/ce-validator-venv/bin/python --version | grep -q '^Python 3\.14\.'; \
    /opt/ce-validator-venv/bin/pytest --version; \
    /opt/ce-validator-venv/bin/python -c "import pytest, yaml, jsonschema, xdist; print('validator toolchain OK')"; \
    /opt/ce-validator-venv/bin/python -c "import ctypes.util; assert ctypes.util.find_library('sodium'), 'libsodium not resolvable'; print('libsodium OK')"

COPY --from=herdr-builder /build/herdr/target/release/herdr /usr/local/bin/herdr
COPY deploy/vps-runsc/herdr-harness-entrypoint.sh /usr/local/bin/herdr-harness-entrypoint.sh

RUN set -eux; \
    install -d -m 0755 /usr/local/lib/node_modules/@openai; \
    printf '%s\n' \
      '#!/usr/bin/env bash' \
      'set -euo pipefail' \
      'exec node /usr/local/lib/node_modules/@openai/codex/bin/codex.js "$@"' \
      >/usr/local/bin/codex; \
    chmod 0755 /usr/local/bin/herdr /usr/local/bin/herdr-harness-entrypoint.sh; \
    chmod 0755 /usr/local/bin/codex; \
    test -x /usr/local/bin/herdr; \
    test -x /usr/local/bin/herdr-harness-entrypoint.sh; \
    test -x /usr/local/bin/codex; \
    node --version

USER ${CE_VPS_UID}:${CE_VPS_GID}
WORKDIR /workspace/creator-engine

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/herdr-harness-entrypoint.sh"]
CMD ["tui"]
