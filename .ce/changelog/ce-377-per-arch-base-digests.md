---
slug: ce-377-per-arch-base-digests
date: 2026-06-30
kind: fix
scope: surfaces
issue: ce-ops#377
---

**per-arch base-image digests.**

- Pin Rust and Debian base-image digests per target architecture for VPS amd64 and DGX arm64 builds.
- Teach surface rendering to select the base-image digest for the requested target architecture while preserving existing digest-map output for non-base surfaces.
- Add a surfaces manifest guard for dual-arch base images.

Follow-up: live DGX codex-runsc image reconciliation is deferred to dev-4.
