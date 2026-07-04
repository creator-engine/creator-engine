# syntax=docker/dockerfile:1.7

ARG OCI_CPYTHON_BASE_IMAGE_SOURCE=UNSET
ARG OCI_CPYTHON_BASE_IMAGE_VERSION=UNSET
ARG OCI_CPYTHON_BASE_IMAGE_COMMIT_OR_DIGEST=UNSET

FROM --platform=$BUILDPLATFORM ${OCI_CPYTHON_BASE_IMAGE_SOURCE}:${OCI_CPYTHON_BASE_IMAGE_VERSION}@sha256:${OCI_CPYTHON_BASE_IMAGE_COMMIT_OR_DIGEST} AS wheel-builder

ARG SOURCE_DATE_EPOCH=946684800

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=0 \
    PYTHONNOUSERSITE=1 \
    SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH}

WORKDIR /src

COPY validators/pyproject.toml validators/pyproject.toml
COPY validators/creator_engine_validator validators/creator_engine_validator

RUN set -eux; \
    python -m pip wheel \
      --no-deps \
      --no-build-isolation \
      --wheel-dir /out \
      /src/validators; \
    test "$(find /out -maxdepth 1 -name 'creator_engine_validator-*.whl' | wc -l | tr -d '[:space:]')" = "1"

FROM --platform=$TARGETPLATFORM ${OCI_CPYTHON_BASE_IMAGE_SOURCE}:${OCI_CPYTHON_BASE_IMAGE_VERSION}@sha256:${OCI_CPYTHON_BASE_IMAGE_COMMIT_OR_DIGEST} AS runtime

ARG CE_USER=ce
ARG CE_UID=10001
ARG CE_GID=10001
ARG CE_IMAGE_VERSION=0.3.1
ARG CE_IMAGE_REVISION=unknown
ARG CE_VALIDATOR_WHEEL=/opt/creator-engine/app/creator_engine_validator-*.whl
ARG SOURCE_DATE_EPOCH=946684800
ARG TARGETARCH

LABEL org.opencontainers.image.title="Creator Engine canonical runtime" \
      org.opencontainers.image.description="Engine-agnostic base runtime for Creator Engine daemons, validation sandboxes, and future seats." \
      org.opencontainers.image.source="https://github.com/creator-engine/creator-engine" \
      org.opencontainers.image.version="${CE_IMAGE_VERSION}" \
      org.opencontainers.image.revision="${CE_IMAGE_REVISION}" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=0 \
    PYTHONNOUSERSITE=1 \
    SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH} \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

RUN set -eux; \
    case "${TARGETARCH:-unknown}" in \
      arm64|amd64|unknown) ;; \
      *) echo "unsupported target architecture: ${TARGETARCH}" >&2; exit 66 ;; \
    esac; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      bash \
      ca-certificates \
      git \
      tini; \
    rm -rf /var/lib/apt/lists/*; \
    group_name="$(getent group "${CE_GID}" | cut -d: -f1 || true)"; \
    if [ -z "${group_name}" ]; then \
      groupadd --gid "${CE_GID}" "${CE_USER}"; \
      group_name="${CE_USER}"; \
    fi; \
    useradd --uid "${CE_UID}" --gid "${CE_GID}" --create-home --shell /bin/bash "${CE_USER}"; \
    install -d -m 0755 -o "${CE_UID}" -g "${CE_GID}" /workspace/creator-engine; \
    git config --system --add safe.directory /workspace/creator-engine

COPY validators/wheelhouse /opt/creator-engine/wheelhouse
COPY --from=wheel-builder /out/*.whl /opt/creator-engine/app/

RUN set -eux; \
    wheel_path="$(find /opt/creator-engine/app -maxdepth 1 -name "$(basename "${CE_VALIDATOR_WHEEL}")" -print -quit)"; \
    test -n "${wheel_path}"; \
    python -m pip install \
      --no-index \
      --find-links=/opt/creator-engine/wheelhouse \
      "${wheel_path}"; \
    command -v ce; \
    command -v cev3; \
    command -v creator-engine-validator; \
    ce --help >/tmp/ce-help.txt; \
    cev3 --help >/tmp/cev3-help.txt; \
    creator-engine-validator --help >/tmp/creator-engine-validator-help.txt

USER ${CE_UID}:${CE_GID}
WORKDIR /workspace/creator-engine

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["ce", "--help"]
