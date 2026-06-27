---
slug: feat-vps-seat-validator-venv
ticket: ce-ops#309
type: fixed
scope: VPS contained-seat validator toolchain
---

Bake a CI-parity validator venv into the VPS contained-seat image so a contained
seat (e.g. `ce-vps-codex`) can self-run the validator preflight and self-push
instead of stranding finished work for courier recovery (ce-ops#309).

- Adds a Python-3.14 `validator-venv-builder` stage (same `python:3.14-slim`
  bookworm base as `deploy/oci/Dockerfile`) that installs the validator runtime
  and dev/test closure **offline** from the vendored `validators/wheelhouse/`
  and `validators/wheelhouse-dev/` (no network — the seat runs under gVisor),
  exactly mirroring the two pip steps in `.github/workflows/validate.yml`.
- Relocates that venv plus its `python3.14` interpreter into the bookworm
  runtime stage at a fixed path and puts it first on `PATH`, so `python`,
  `pytest`, and `creator-engine-validator` resolve to a CI-equivalent (3.14)
  toolchain. The cp314 wheels in `validators/wheelhouse*/` cannot load on the
  image's system Python 3.11, which is why a same-Python pip install could not
  reach parity.
- Installs the `libsodium23` runtime so the worktree-lease Ed25519 gate
  (`worktree_lease_schema.py`, PCO-024, which loads libsodium via
  `ctypes.util.find_library`) verifies instead of failing closed.
- Supersedes the prior 3.11 `--break-system-packages` online pip install
  (ce-ops#261): neither CI-parity (3.11 vs 3.14, online resolution vs the
  vendored wheels) nor able to satisfy the libsodium-backed signature gate.
- The image now builds from the **repository root** context (matching
  `deploy/oci/Dockerfile`) because the venv stage COPYs `validators/**`; the
  README build command is updated accordingly.
