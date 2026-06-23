---
slug: ce128-vps-contained-herdr
ticket: ce-ops#128
type: added
scope: VPS runsc/herdr launch recipe
---

Add an x86_64 VPS runsc/herdr recipe for contained Codex and controller seats.

- Builds `herdr-ce` from source inside the image build so the runtime glibc
  matches the baked binary.
- Adds a fail-closed herdr harness entrypoint that keeps the control socket
  substrate-side and scrubs raw plus `CE_DGX*SOCKET*` carriers from the governed
  harness environment.
- Adds a VPS launcher for Codex and controller/Claude variants using
  `runsc-gvproxy-ptrace`, `--cap-drop=ALL`, `no-new-privileges`, seat UID/GID,
  and explicit x86_64 host mounts.
- Documents that VPS `--network=host` is not egress confinement; ce-ops#222
  remains the follow-on for egress mediation.
