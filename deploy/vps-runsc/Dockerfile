FROM --platform=linux/amd64 rust:1-bookworm AS herdr-builder

ARG HERDR_SOURCE_REPO=https://github.com/creator-engine/herdr-ce.git
ARG HERDR_SOURCE_REF=main

WORKDIR /src/herdr-ce

RUN set -eux; \
    git clone --depth 1 --branch "${HERDR_SOURCE_REF}" "${HERDR_SOURCE_REPO}" .; \
    cargo build --locked --release; \
    install -m 0755 target/release/herdr /usr/local/bin/herdr; \
    test -x /usr/local/bin/herdr

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

COPY --from=herdr-builder /usr/local/bin/herdr /usr/local/bin/herdr
COPY herdr-harness-entrypoint.sh /usr/local/bin/herdr-harness-entrypoint.sh

RUN set -eux; \
    chmod 0755 /usr/local/bin/herdr /usr/local/bin/herdr-harness-entrypoint.sh; \
    test -x /usr/local/bin/herdr; \
    test -x /usr/local/bin/herdr-harness-entrypoint.sh

USER ${CE_VPS_UID}:${CE_VPS_GID}
WORKDIR /workspace/creator-engine

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/herdr-harness-entrypoint.sh"]
CMD ["tui"]
