# syntax=docker/dockerfile:1.7

ARG CE_CANONICAL_RUNTIME_IMAGE=creator-engine/ce-validator:0.3.3

FROM ${CE_CANONICAL_RUNTIME_IMAGE}

LABEL org.opencontainers.image.title="Creator Engine governance daemons" \
      org.opencontainers.image.description="Thin daemon packaging layer over the canonical Creator Engine runtime image." \
      org.opencontainers.image.source="https://github.com/creator-engine/creator-engine"

WORKDIR /workspace/creator-engine
