ARG RUST_SOURCE=UNSET
ARG RUST_VERSION=UNSET
ARG RUST_COMMIT_OR_DIGEST=UNSET
ARG DEBIAN_SOURCE=UNSET
ARG DEBIAN_VERSION=UNSET
ARG DEBIAN_COMMIT_OR_DIGEST=UNSET

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

ENV DEBIAN_FRONTEND=noninteractive
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV PYTHONPATH=/workspace/creator-engine/validators
ENV CE_DGX_CREDENTIAL_INJECTION=SEAM-STUB
ENV CE_TRANSPORT_DEPUTY_SEAM_STATUS=stub-ce-ops-239-no-secret-injection

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      bash \
      ca-certificates \
      gh \
      git \
      less \
      openssh-client \
      procps \
      python3 \
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

COPY --from=herdr-builder /build/herdr/target/release/herdr /usr/local/bin/herdr
COPY deploy/dgx-runsc/herdr-harness-entrypoint.sh /usr/local/bin/ce-herdr-harness-entrypoint
COPY deploy/dgx-controller-runsc/ce-controller-gh-guard.sh /usr/local/bin/ce-controller-gh-guard

RUN set -eux; \
    ln -s /usr/local/bin/ce-controller-gh-guard /usr/local/bin/gh; \
    { \
      printf '%s\n' '#!/usr/bin/env bash'; \
      printf '%s\n' 'set -euo pipefail'; \
      printf '%s\n' 'validator_path="/workspace/creator-engine/validators"'; \
      printf '%s\n' 'case ":${PYTHONPATH:-}:" in'; \
      printf '%s\n' '  *":${validator_path}:"*) ;;'; \
      printf '%s\n' '  *) export PYTHONPATH="${validator_path}${PYTHONPATH:+:${PYTHONPATH}}" ;;'; \
      printf '%s\n' 'esac'; \
      printf '%s\n' 'if [ -S /run/ce-supervisor.sock ]; then'; \
      printf '%s\n' '  export CE_SUPERVISOR_SOCKET=/run/ce-supervisor.sock'; \
      printf '%s\n' 'fi'; \
      printf '%s\n' 'export CE_DGX_CREDENTIAL_INJECTION="${CE_DGX_CREDENTIAL_INJECTION:-SEAM-STUB}"'; \
      printf '%s\n' 'export CE_TRANSPORT_DEPUTY_SEAM_STATUS="${CE_TRANSPORT_DEPUTY_SEAM_STATUS:-stub-ce-ops-239-no-secret-injection}"'; \
      printf '%s\n' 'exec /usr/local/bin/claude "$@"'; \
    } >/usr/local/bin/ce-controller-harness; \
    chmod 0755 \
      /usr/local/bin/herdr \
      /usr/local/bin/ce-herdr-harness-entrypoint \
      /usr/local/bin/ce-controller-gh-guard \
      /usr/local/bin/ce-controller-harness; \
    test -x /usr/local/bin/herdr; \
    test -x /usr/local/bin/ce-herdr-harness-entrypoint; \
    test -x /usr/local/bin/ce-controller-gh-guard; \
    test -x /usr/local/bin/gh; \
    test -x /usr/local/bin/ce-controller-harness; \
    git --version; \
    /usr/bin/gh --version >/tmp/gh-version.txt; \
    CE_TRANSPORT_DEPUTY_SEAM_STATUS=stub-ce-ops-239-no-secret-injection /usr/local/bin/gh auth status >/tmp/gh-guard-out.txt 2>/tmp/gh-guard-err.txt && exit 1 || test "$?" = "78"; \
    python3 -c 'import sys; sys.path.insert(0, "/workspace/creator-engine/validators"); print("creator_engine_validator import path scaffolded")'

USER ${CE_DGX_UID}:${CE_DGX_GID}
WORKDIR /workspace/creator-engine

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/ce-herdr-harness-entrypoint"]
