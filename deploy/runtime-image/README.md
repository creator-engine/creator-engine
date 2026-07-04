# Creator Engine Canonical Runtime Image

`deploy/runtime-image` defines the canonical Linux container runtime for
Creator Engine. Daemon, validation sandbox, and future seat images should derive
from this image instead of duplicating the validator install and base OS setup.

The image is engine-agnostic: it uses standard OCI/Dockerfile features and runs
under Docker or rootless podman. It installs the Creator Engine validator from
this checkout's built wheel plus the checked-in offline wheelhouse, creates the
non-root `ce` user, and sets `/workspace/creator-engine` as the working
directory.

Consumers derive from the published runtime by digest:

```Dockerfile
ARG CE_CANONICAL_RUNTIME_IMAGE=ghcr.io/creator-engine/creator-engine/ce-runtime@sha256:<manifest-list-digest>
FROM ${CE_CANONICAL_RUNTIME_IMAGE}
```

Pin the multi-arch manifest-list digest only. Do not pin an amd64 or arm64 child
manifest digest in repo defaults, release manifests, deployment scripts, or
operator docs. Pinning a child digest caused an amd64 image reference to be used
on an aarch64 DGX seat, which fails at process start with `exec format error`.
The manifest-list digest lets Docker and podman select the correct
`linux/amd64` or `linux/arm64` image from one reference.

Publishing is handled by `.github/workflows/publish-runtime-image.yml` on manual
dispatch or release tags. The workflow publishes:

- `ghcr.io/creator-engine/creator-engine/ce-runtime:<version>`
- `ghcr.io/creator-engine/creator-engine/ce-runtime:<git-sha>`

The workflow writes the manifest-list digest and digest-pinned reference to the
GitHub Actions step summary. To bump consumers, update their image argument or
release manifest from that digest-pinned reference, then verify the target
consumer on both `linux/amd64` and `linux/arm64` before release.

`deploy/daemons/Dockerfile` is already a thin layer over a canonical runtime
argument. A follow-up release pin should set `CE_CANONICAL_RUNTIME_IMAGE` or
`CE_DAEMON_IMAGE` to the published `ce-runtime@sha256:<manifest-list-digest>`
reference rather than editing daemon code in this slice.
