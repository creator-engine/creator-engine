FROM rust:1-bookworm@sha256:c993d32d95cc146bd12c84d66f0b924a6a96f3988325f39c144f2f9893dea120 AS herdr-builder

ARG HERDR_CE_REPO=https://github.com/creator-engine/herdr-ce.git
ARG HERDR_CE_REF=ff924966bd789afabec1a52d74f24392f45838ef
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
    git clone "${HERDR_CE_REPO}" herdr; \
    cd herdr; \
    git checkout --detach "${HERDR_CE_REF}"; \
    cargo build --locked --release --bin herdr; \
    ldd target/release/herdr; \
    target/release/herdr --help >/tmp/herdr-help.txt

FROM debian:bookworm-slim@sha256:1def178129dfb5f24db43afbf2fcac04530012e3264ba4ff81c71184e17a9ee4

ARG CE_DGX_USER=cedev4
ARG CE_DGX_UID=1000
ARG CE_DGX_GID=1000

ENV DEBIAN_FRONTEND=noninteractive
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      bash \
      ca-certificates \
      git \
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

RUN set -eux; \
    python -m pip install \
      --break-system-packages \
      --no-cache-dir \
      --disable-pip-version-check \
      attrs==26.1.0 \
      build==1.3.0 \
      execnet==2.1.2 \
      iniconfig==2.3.0 \
      jsonschema==4.26.0 \
      jsonschema-specifications==2025.9.1 \
      packaging==26.2 \
      pluggy==1.6.0 \
      Pygments==2.20.0 \
      pyproject_hooks==1.2.0 \
      pytest==9.0.2 \
      pytest-xdist==3.8.0 \
      PyYAML==6.0.3 \
      referencing==0.37.0 \
      rpds-py==0.30.0 \
      setuptools==82.0.1 \
      wheel==0.47.0; \
    python -m pytest --co -q -n auto --dist loadgroup --help > /dev/null 2>&1 && echo "pytest-xdist smoke: OK"

COPY --from=herdr-builder /build/herdr/target/release/herdr /usr/local/bin/herdr
COPY herdr-harness-entrypoint.sh /usr/local/bin/ce-herdr-harness-entrypoint

RUN set -eux; \
    chmod 0755 /usr/local/bin/herdr /usr/local/bin/ce-herdr-harness-entrypoint; \
    test -x /usr/local/bin/herdr; \
    test -x /usr/local/bin/ce-herdr-harness-entrypoint

USER ${CE_DGX_UID}:${CE_DGX_GID}
WORKDIR /workspace/creator-engine

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/ce-herdr-harness-entrypoint"]
