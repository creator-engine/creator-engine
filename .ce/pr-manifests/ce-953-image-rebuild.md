# PR path manifest — ce-953-image-rebuild

Closed PREP-only carrier for #953 image rebuild preparation. Image building,
loading, publishing, container/host actions, and rollout execution remain
controller/host actions after merge.

- **Declared work class:** feature

Per-file purpose:

- `.ce/changelog/ce-953-image-rebuild.md` *(A)* — user-safe changelog fragment.
- `.ce/pr-manifests/ce-953-image-rebuild.md` *(A)* — this closed path-set carrier.
- `BUILD_NOTE.md` *(M)* — controller-attested Codex and CPython provenance record.
- `deploy/dgx-runsc/Dockerfile` *(M)* — verified Codex pin, baked Python 3.14 validator venv, and UID/GID build arguments.
- `deploy/dgx-runsc/README.md` *(M)* — provenance, controller-only rollout, bundle-out, canary, digest, and rollback procedure.
- `deploy/dgx-runsc/build-image.sh` *(M)* — root-context, UID/GID, Codex pin build wiring.
- `deploy/dgx-runsc/codex-default-config.toml` *(A)* — baked update-check disablement.
- `deploy/dgx-runsc/run-codex-runsc.sh` *(M)* — baked-image launch default without a host Codex binary mount.
- `deploy/oci/build-image.sh` *(M)* — platform-to-surface architecture selection for the OCI validator image.
- `surfaces/manifest.yaml` *(M)* — Codex default version and CPython manifest-list/amd64/arm64 pins.
- `validators/tests/unit/test_dgx_runsc.py` *(M)* — static/dry-run pin, venv, config, and mount coverage.
- `validators/tests/unit/test_surface_build_wiring.py` *(M)* — root-context and image-tag build wiring coverage.

Canonicalization: `sha256("\\n".join(sorted(unique_paths)) + "\\n")`.

Controller-attested CPython `3.14-slim-bookworm` provenance: manifest-list
`sha256:4ff4b92a68355dbdb52584ab3391dff8d371a61d4e063468bfd0130e3189c6d9`;
amd64 child `sha256:01d4f0a9b0f284f9ef577e86a1ae7c7c22572e19fddc052d011c38217f856a94`;
arm64 child `sha256:0670f5b579f8ba90903a95007ae10c890ac7f0d54de138ebd20574d56b10f3cc`.

AUTHORIZED_PATHS_COUNT=12

AUTHORIZED_PATHS_SHA256=6185f9c68b85bb03d82a3196ec8f7ef8077acf85dda0c66949ead9dcf77d47ca

```text
.ce/changelog/ce-953-image-rebuild.md
.ce/pr-manifests/ce-953-image-rebuild.md
BUILD_NOTE.md
deploy/dgx-runsc/Dockerfile
deploy/dgx-runsc/README.md
deploy/dgx-runsc/build-image.sh
deploy/dgx-runsc/codex-default-config.toml
deploy/dgx-runsc/run-codex-runsc.sh
deploy/oci/build-image.sh
surfaces/manifest.yaml
validators/tests/unit/test_dgx_runsc.py
validators/tests/unit/test_surface_build_wiring.py
```
