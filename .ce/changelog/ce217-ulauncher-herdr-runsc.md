---
slug: ce217-ulauncher-herdr-runsc
date: 2026-06-23
kind: changed
scope: DGX runsc launcher / herdr harness entrypoint
issue: ce-ops#217
---

Adds a DGX runsc harness entrypoint that starts the staged herdr server inside
the container, creates a herdr workspace rooted at `/workspace/creator-engine`,
and launches the selected Codex or Claude harness through `herdr pane run`
without exposing the raw herdr socket carrier to the harness environment.

- Builds herdr-ce from a pinned source revision in a Debian bookworm builder
  stage and bakes that binary plus the shared entrypoint into the Codex runsc
  image under `tini`.
- Updates Codex and Controller wrappers to use image-default entrypoint launch
  shape with `CE_DGX_HARNESS`, `CE_DGX_HERDR_SOCKET_PATH`, and
  `CE_DGX_TERMINAL_KIND=herdr` markers, while the governed harness starts with
  a clean environment that excludes socket carriers.
- Mounts a runtime-owned `/run/creator-engine` tmpfs for herdr socket and XDG
  state so the simple image build does not depend on build-time UID ownership.
- Documents the required herdr staging/build/launch/probe commands and extends
  dry-run/static tests for the Docker argv and entrypoint contract.
