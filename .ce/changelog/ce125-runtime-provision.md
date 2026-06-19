---
slug: ce125-runtime-provision
date: 2026-06-19
kind: fixed
scope: install runtime provisioning
issue: ce-ops#125
---

Fixed the live install runtime-provisioning leg for the `gvisor-proxy` backend
so it now ensures concrete pinned gVisor runtime tools are present before
recording runtime posture: `runsc` `20260608.0` and `gvproxy` `v0.8.9`.

The runtime installer fetches the pinned upstream binaries, verifies their
sha256/sha512 digests before installation, installs only the known pinned tools,
and fail-closes on unsupported architecture, fetch failure, digest mismatch,
install failure, or post-install version mismatch.

Kept the signed install answer schema's existing `proxy` sudo-grant enum intact;
the concrete `gvproxy` install is handled inside runtime provisioning instead
of changing the trust-root-pinned answer contract. Rebuilt the checked-in
validator wheelhouse and refreshed `validators/wheelhouse/SHA256SUMS`.
