# syntax=docker/dockerfile:1.7

ARG CE_CANONICAL_RUNTIME_IMAGE=ghcr.io/creator-engine/creator-engine/ce-runtime@sha256:UNSET

FROM ${CE_CANONICAL_RUNTIME_IMAGE}

ARG CE_UID=10001
ARG CE_GID=10001
ARG CE_IMAGE_VERSION=0.3.6
ARG CE_IMAGE_REVISION=unknown
ARG NODE_MAJOR=22
ARG CODEX_CLI_VERSION=0.142.4
# Keep this default in sync with the claude-code surface pin.
ARG CLAUDE_CODE_CLI_VERSION=2.1.201

LABEL org.opencontainers.image.title="Creator Engine tenant seat" \
      org.opencontainers.image.description="Creator Engine runtime with pinned Codex and Claude Code CLIs for governed tenant seats." \
      org.opencontainers.image.source="https://github.com/creator-engine/creator-engine" \
      org.opencontainers.image.version="${CE_IMAGE_VERSION}" \
      org.opencontainers.image.revision="${CE_IMAGE_REVISION}" \
      org.opencontainers.image.licenses="Apache-2.0"

USER root

ENV NPM_CONFIG_AUDIT=false \
    NPM_CONFIG_FUND=false \
    NPM_CONFIG_UPDATE_NOTIFIER=false

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      gnupg; \
    install -d -m 0755 /etc/apt/keyrings /etc/apt/sources.list.d; \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key -o /tmp/nodesource-repo.gpg.key; \
    gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg /tmp/nodesource-repo.gpg.key; \
    chmod 0644 /etc/apt/keyrings/nodesource.gpg; \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" > /etc/apt/sources.list.d/nodesource.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends nodejs; \
    npm install --global \
      "@openai/codex@${CODEX_CLI_VERSION}" \
      "@anthropic-ai/claude-code@${CLAUDE_CODE_CLI_VERSION}"; \
    npm cache clean --force; \
    rm -rf /var/lib/apt/lists/* /tmp/nodesource-repo.gpg.key; \
    node --version | grep -E '^v22\.'; \
    npm --version; \
    command -v codex; \
    command -v claude; \
    codex --version; \
    claude --version

USER ${CE_UID}:${CE_GID}
WORKDIR /workspace/creator-engine

RUN set -eux; \
    test "$(id -u)" = "${CE_UID}"; \
    test "$(id -g)" = "${CE_GID}"; \
    command -v codex; \
    command -v claude; \
    codex --version; \
    claude --version

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["ce", "--help"]
