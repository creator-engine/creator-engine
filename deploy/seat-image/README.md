# Creator Engine Tenant Seat Image

`deploy/seat-image` defines the tenant seat image for Creator Engine. It derives
from the canonical `ce-runtime` image and adds the pinned coding agent CLIs a
tenant seat needs at runtime:

- `@openai/codex`
- `@anthropic-ai/claude-code`

The base image must be supplied as a manifest-list digest-pinned reference:

```Dockerfile
ARG CE_CANONICAL_RUNTIME_IMAGE=ghcr.io/creator-engine/creator-engine/ce-runtime@sha256:<manifest-list-digest>
FROM ${CE_CANONICAL_RUNTIME_IMAGE}
```

Pin the multi-arch manifest-list digest only. Do not pin an `amd64` or `arm64`
child manifest digest. The manifest-list digest lets Docker and podman select
the correct `linux/amd64` or `linux/arm64` child image for the seat host.

Publishing is handled by `.github/workflows/publish-seat-image.yml`. The
workflow resolves the `ce-runtime:<version>` manifest-list digest, builds this
image for `linux/amd64` and `linux/arm64`, publishes:

- `ghcr.io/creator-engine/creator-engine/ce-seat:<version>`
- `ghcr.io/creator-engine/creator-engine/ce-seat:<git-sha>`

and writes the published seat manifest-list digest to the GitHub Actions step
summary.

The image deliberately contains no credentials and no fleet-only harness
artifacts such as herdr, broker components, or runsc toolchains. Tenant auth and
agent configuration arrive only through explicitly enumerated runtime mounts
owned by the launcher path that starts the seat.
