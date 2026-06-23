FROM debian:bookworm-slim

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

COPY herdr /usr/local/bin/herdr
COPY herdr-harness-entrypoint.sh /usr/local/bin/ce-herdr-harness-entrypoint

RUN set -eux; \
    chmod 0755 /usr/local/bin/herdr /usr/local/bin/ce-herdr-harness-entrypoint; \
    test -x /usr/local/bin/herdr; \
    test -x /usr/local/bin/ce-herdr-harness-entrypoint

USER ${CE_DGX_UID}:${CE_DGX_GID}
WORKDIR /workspace/creator-engine

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/ce-herdr-harness-entrypoint"]
