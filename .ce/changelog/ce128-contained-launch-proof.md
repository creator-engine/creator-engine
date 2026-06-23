---
slug: ce128-contained-launch-proof
ticket: ce-ops#128
scope: contained launch proof
type: story
---

Added the contained-launch proof path for ce-ops#128/#221. The new test proves
that `ce launch --backend gvisor` routes the seat through the gVisor runner
backend and that `ce containment-probe` returns `contained:true` /
`backend:gvisor` only from positive kernel-isolation evidence. The raw launch
fixture probes fail-closed, and unavailable gVisor runtime availability refuses
before any raw tmux fallback.

The operations note records which proof legs are mocked in CI and the exact DGX
dogfood command using `deploy/dgx-runsc/run-codex-runsc.sh`.
