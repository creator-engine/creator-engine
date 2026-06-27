# PR path manifest - feat-vps-seat-validator-venv

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref feat/vps-seat-validator-venv
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`origin/main`.

- **Declared work class:** story

Scope:
ce-ops#309 — bake a CI-parity validator venv into the VPS contained-seat image
so a contained seat can self-run the validator preflight and self-push instead
of stranding finished work. No launcher, runtime-flag, or governance-seam
changes.

Per-file purpose:
- **`.ce/changelog/feat-vps-seat-validator-venv.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/feat-vps-seat-validator-venv.md`** *(A)* - this closed path-set carrier.
- **`deploy/vps-runsc/Dockerfile`** *(M)* - add a Python-3.14 `validator-venv-builder` stage that installs the validator runtime + dev deps offline from `validators/wheelhouse*/`; relocate that venv + interpreter into the runtime stage on `PATH`; add `libsodium23` for the PCO-024 Ed25519 gate; build now uses the repo-root context.
- **`deploy/vps-runsc/README.md`** *(M)* - document the repo-root build context and the CI-parity validator venv.
- **`validators/tests/unit/test_vps_runsc_image.py`** *(M)* - assert the CI-parity validator venv stage (offline wheelhouse install, venv relocation, libsodium) and update the entrypoint COPY assertion for the repo-root context.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=f5917108584e7a06c66b97e8cb946676a73b465d0ab5d3c1ea4829b56d2e98dc

```text
.ce/changelog/feat-vps-seat-validator-venv.md
.ce/pr-manifests/feat-vps-seat-validator-venv.md
deploy/vps-runsc/Dockerfile
deploy/vps-runsc/README.md
validators/tests/unit/test_vps_runsc_image.py
```
