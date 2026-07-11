# Build context: the REPOSITORY ROOT (not deploy/dgx-runsc/). The validator
# venv stage below COPYs validators/** so the contained seat has the same
# Python-3.14 validator toolchain as CI.
ARG OCI_CPYTHON_BASE_IMAGE_SOURCE=UNSET
ARG OCI_CPYTHON_BASE_IMAGE_VERSION=UNSET
ARG OCI_CPYTHON_BASE_IMAGE_COMMIT_OR_DIGEST=UNSET
ARG RUST_SOURCE=UNSET
ARG RUST_VERSION=UNSET
ARG RUST_COMMIT_OR_DIGEST=UNSET
ARG DEBIAN_SOURCE=UNSET
ARG DEBIAN_VERSION=UNSET
ARG DEBIAN_COMMIT_OR_DIGEST=UNSET

FROM ${OCI_CPYTHON_BASE_IMAGE_SOURCE}:${OCI_CPYTHON_BASE_IMAGE_VERSION}@sha256:${OCI_CPYTHON_BASE_IMAGE_COMMIT_OR_DIGEST} AS validator-venv-builder

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

# Install the first-party validator and its runtime/test closure offline. The
# wheelhouses carry cp314 wheels for both supported image architectures.
RUN set -eux; \
    python3.14 -m venv /opt/ce-validator-venv; \
    /opt/ce-validator-venv/bin/pip install --no-index --find-links validators/wheelhouse -r validators/requirements.txt; \
    /opt/ce-validator-venv/bin/pip install --no-index --find-links validators/wheelhouse --find-links validators/wheelhouse-dev -r validators/requirements-dev.txt; \
    /opt/ce-validator-venv/bin/pip install --no-index --no-build-isolation --no-deps validators/; \
    /opt/ce-validator-venv/bin/python -c "import creator_engine_validator, pytest, yaml, jsonschema, xdist"; \
    /opt/ce-validator-venv/bin/ce --help >/dev/null

FROM ${RUST_SOURCE}:${RUST_VERSION}@sha256:${RUST_COMMIT_OR_DIGEST} AS herdr-builder

ARG HERDR_SOURCE=UNSET
ARG HERDR_COMMIT_OR_DIGEST=UNSET
ARG ZIG_TOOLCHAIN_SOURCE=UNSET
ARG ZIG_TOOLCHAIN_VERSION=UNSET
ARG ZIG_TOOLCHAIN_LINUX_AARCH64_SHA256=UNSET
ARG ZIG_TOOLCHAIN_LINUX_X86_64_SHA256=UNSET

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
      arm64) zig_arch="aarch64"; zig_sha256="${ZIG_TOOLCHAIN_LINUX_AARCH64_SHA256}" ;; \
      amd64) zig_arch="x86_64"; zig_sha256="${ZIG_TOOLCHAIN_LINUX_X86_64_SHA256}" ;; \
      *) echo "unsupported Zig architecture: ${arch}" >&2; exit 66 ;; \
    esac; \
    zig_url="${ZIG_TOOLCHAIN_SOURCE%/}/zig-${zig_arch}-linux-${ZIG_TOOLCHAIN_VERSION}.tar.xz"; \
    curl -fsSL "${zig_url}" -o /tmp/zig.tar.xz; \
    echo "${zig_sha256}  /tmp/zig.tar.xz" | sha256sum -c -; \
    mkdir -p /opt/zig; \
    tar -xJf /tmp/zig.tar.xz -C /opt/zig --strip-components=1; \
    rm /tmp/zig.tar.xz

ENV PATH="/opt/zig:${PATH}"

WORKDIR /build
RUN set -eux; \
    git clone "${HERDR_SOURCE}" herdr; \
    cd herdr; \
    git checkout --detach "${HERDR_COMMIT_OR_DIGEST}"; \
    cargo build --locked --release --bin herdr; \
    ldd target/release/herdr; \
    target/release/herdr --help >/tmp/herdr-help.txt

FROM ${DEBIAN_SOURCE}:${DEBIAN_VERSION}@sha256:${DEBIAN_COMMIT_OR_DIGEST}

ARG CE_DGX_USER=cedev4
ARG CE_DGX_UID=1000
ARG CE_DGX_GID=1000
ARG CODEX_VERSION=0.144.1
ARG CODEX_SHA256=9513fa3f5f4ad444ac1e40d972aef0e2664834ec54da987d54aba0dc2f13ea07
ARG CODEX_ARTIFACT_URL=https://github.com/openai/codex/releases/download/rust-v0.144.1/codex-aarch64-unknown-linux-musl.tar.gz

ENV DEBIAN_FRONTEND=noninteractive
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      bash \
      ca-certificates \
      curl \
      git \
      libsodium23 \
      openssh-client \
      procps \
      python-is-python3 \
      python3 \
      python3-pip \
      tini; \
    rm -rf /var/lib/apt/lists/*; \
    group_name="$(getent group "${CE_DGX_GID}" | cut -d: -f1 || true)"; \
    if [ -z "${group_name}" ]; then \
      groupadd --gid "${CE_DGX_GID}" "${CE_DGX_USER}"; \
      group_name="${CE_DGX_USER}"; \
    fi; \
    useradd --uid "${CE_DGX_UID}" --gid "${CE_DGX_GID}" --create-home --shell /bin/bash "${CE_DGX_USER}"; \
    install -d -o "${CE_DGX_UID}" -g "${CE_DGX_GID}" /workspace/creator-engine; \
    install -d -m 0700 -o "${CE_DGX_UID}" -g "${CE_DGX_GID}" /run/creator-engine/herdr; \
    git config --system --add safe.directory /workspace/creator-engine

# The release URL and controller-attested first-fetch digest are intentionally
# explicit. The checksum check is mandatory: a missing/incorrect build arg
# fails the image build rather than silently using an unverified Codex binary.
RUN set -eux; \
    test "${CODEX_VERSION}" = "0.144.1"; \
    case "$(dpkg --print-architecture)" in arm64) ;; *) echo "Codex ${CODEX_VERSION} artifact is arm64-only" >&2; exit 66 ;; esac; \
    curl --fail --location --show-error --silent "${CODEX_ARTIFACT_URL}" --output /tmp/codex.tar.gz; \
    echo "${CODEX_SHA256}  /tmp/codex.tar.gz" | sha256sum -c -; \
    mkdir -p /tmp/codex-unpack; \
    tar -xzf /tmp/codex.tar.gz -C /tmp/codex-unpack; \
    codex_bin="$(find /tmp/codex-unpack -type f -name codex -perm -u+x | head -n 1)"; \
    test -n "${codex_bin}"; \
    install -m 0755 "${codex_bin}" /usr/local/bin/codex; \
    rm -rf /tmp/codex.tar.gz /tmp/codex-unpack; \
    /usr/local/bin/codex --version | grep -q "${CODEX_VERSION}"

# CI-parity validator toolchain. The runtime is bookworm-compatible with the
# pinned Python-3.14 base; putting the relocated venv first makes `ce` and
# `pytest` resolve to Python 3.14 while retaining system Python for helpers.
COPY --from=validator-venv-builder /usr/local/bin/python3.14 /usr/local/bin/python3.14
COPY --from=validator-venv-builder /usr/local/lib/libpython3.14.so.1.0 /usr/local/lib/libpython3.14.so.1.0
COPY --from=validator-venv-builder /usr/local/lib/python3.14 /usr/local/lib/python3.14
COPY --from=validator-venv-builder /opt/ce-validator-venv /opt/ce-validator-venv

ENV CE_VALIDATOR_VENV=/opt/ce-validator-venv
ENV PATH="/opt/ce-validator-venv/bin:${PATH}"

RUN set -eux; \
    ldconfig; \
    /opt/ce-validator-venv/bin/python --version | grep -q '^Python 3\\.14\\.'; \
    /opt/ce-validator-venv/bin/ce --help >/dev/null; \
    /opt/ce-validator-venv/bin/python -c "import pytest, yaml, jsonschema, xdist; print('validator toolchain OK')"; \
    /opt/ce-validator-venv/bin/python -c "import ctypes.util; assert ctypes.util.find_library('sodium'), 'libsodium not resolvable'"

COPY --from=herdr-builder /build/herdr/target/release/herdr /usr/local/bin/herdr
COPY deploy/dgx-runsc/herdr-harness-entrypoint.sh /usr/local/bin/ce-herdr-harness-entrypoint
COPY deploy/dgx-runsc/codex-default-config.toml /etc/codex/config.toml

RUN set -eux; \
    chmod 0755 /usr/local/bin/herdr /usr/local/bin/ce-herdr-harness-entrypoint; \
    test -x /usr/local/bin/herdr; \
    test -x /usr/local/bin/ce-herdr-harness-entrypoint; \
    test -x /usr/local/bin/codex; \
    test "$(cat /etc/codex/config.toml)" = 'check_for_update_on_startup = false'

USER ${CE_DGX_UID}:${CE_DGX_GID}
WORKDIR /workspace/creator-engine

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/ce-herdr-harness-entrypoint"]
