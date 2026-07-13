# Creator Engine Validator OCI Image

`deploy/oci` builds the portable CE CLI and validator image. The Dockerfile
builds the `creator-engine-validator` wheel from this checkout, installs it
from the repo wheelhouse, and verifies that both `ce` and
`creator-engine-validator` are on `PATH`.

Prerequisites:

- Docker with the `buildx` plugin enabled.
- No host Python packaging tools are required; the wheel is built inside the
  Dockerfile.

Build the default aarch64 image:

```bash
deploy/oci/build-image.sh
```

Build and push a multi-arch image:

```bash
deploy/oci/build-image.sh --platform linux/arm64,linux/amd64 --push
```

Inspect the build without requiring Docker or buildx:

```bash
deploy/oci/build-image.sh --dry-run
```

The build script stages a minimal temporary Docker context containing only
`validators/pyproject.toml`, `validators/creator_engine_validator`, and
`validators/wheelhouse` before running `docker buildx build`.

Run it against this checkout:

```bash
docker run --rm creator-engine/ce-validator:0.3.6 ce --help
docker run --rm \
  -v "$PWD:/workspace/creator-engine" \
  -w /workspace/creator-engine \
  creator-engine/ce-validator:0.3.6 \
  creator-engine-validator check-examples
```

The image runs as the non-root `ce` user in `/workspace/creator-engine`. It is
not the herdr/Codex seat image from `deploy/dgx-runsc` or `deploy/vps-runsc`;
use it as the common validator payload before or beside those runsc launchers.
For DGX/VPS containment parity, run this image with the same registered
`runsc-gvproxy-ptrace` Docker runtime documented in those directories.
