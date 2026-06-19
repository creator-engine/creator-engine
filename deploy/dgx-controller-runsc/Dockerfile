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
      less \
      openssh-client \
      procps \
      tini \
      tmux; \
    rm -rf /var/lib/apt/lists/*; \
    group_name="$(getent group "${CE_DGX_GID}" | cut -d: -f1 || true)"; \
    if [ -z "${group_name}" ]; then \
      groupadd --gid "${CE_DGX_GID}" "${CE_DGX_USER}"; \
      group_name="${CE_DGX_USER}"; \
    fi; \
    useradd --uid "${CE_DGX_UID}" --gid "${CE_DGX_GID}" --create-home --shell /bin/bash "${CE_DGX_USER}"; \
    install -d -o "${CE_DGX_UID}" -g "${CE_DGX_GID}" /workspace/creator-engine; \
    git config --system --add safe.directory /workspace/creator-engine

USER ${CE_DGX_UID}:${CE_DGX_GID}
WORKDIR /workspace/creator-engine

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/usr/local/bin/claude"]
