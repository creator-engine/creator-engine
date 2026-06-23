FROM --platform=linux/amd64 rust:1-bookworm AS herdr-builder

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

FROM --platform=linux/amd64 debian:bookworm-slim AS runtime

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

COPY --from=herdr-builder /build/herdr/target/release/herdr /usr/local/bin/herdr
COPY herdr-harness-entrypoint.sh /usr/local/bin/herdr-harness-entrypoint.sh

RUN set -eux; \
    chmod 0755 /usr/local/bin/herdr /usr/local/bin/herdr-harness-entrypoint.sh; \
    test -x /usr/local/bin/herdr; \
    test -x /usr/local/bin/herdr-harness-entrypoint.sh

USER ${CE_VPS_UID}:${CE_VPS_GID}
WORKDIR /workspace/creator-engine

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/herdr-harness-entrypoint.sh"]
CMD ["tui"]
