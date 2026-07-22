---
slug: ce620-launch-wrapper-model-effort-floor
date: 2026-07-22
kind: fixed
scope: governed launch wrappers and dispatch receipts
issue: ce-ops#620
---

**Enforce the ratified model-tier and reasoning-effort floor at launch.**

- Resolve model and effort before spawning; Luna is refused for persistent
  seat/foreman roles, low effort clamps to medium with an auditable warning,
  and stale raw flags are removed before canonical args are injected.
- Reassert the resolved Terra/high standing policy when DGX or VPS recreates a
  contained Codex configuration after stale session state.
- Require dispatch receipts to carry the canonical resolved model/effort stamp
  instead of arbitrary nonempty status prose.
- Thread every governed worker role through the live worker-spawn entry point
  into the model-tier resolver: verification workers are explicit Luna-eligible
  organs; implementation workers remain persistent-seat tier and are refused
  from Luna.
- An attached `--resume` session cannot honestly claim the wrapper reasserted
  its model/effort. It now emits a loud warning and permits only the bounded
  receipt note `unverified-attached-session: --resume did not recreate or
  reassert model/effort`; recreate paths remain the strong reassertion.
- The duplicated shell stripping functions intentionally remain local to their
  substrate scripts: sourcing a shared helper across the DGX/VPS images would
  add an image/runtime dependency to the launch-critical path. A static test
  binds both injected argv literals and `surfaces/model-canon.yaml` to the
  single Python policy constants. DGX injects unconditionally because it is a
  Codex-only wrapper; VPS injects only for its Codex image because it also
  launches Claude, whose model flags are not Codex flags.

Closure waiver (controller, 20260722): live-target observation deferred to the next canonical seat relaunch on each substrate (vps-runsc: ce-vps-codex / ce-vps-codex-dev4; dgx-runsc: next DGX seat stand-up), scope = strip-and-reassert argv behavior at revision 47d70e8b44ce60d304027738716630a78e4ec710, reason = relaunch is Operator-gated and next relaunch is the natural canary; tracking = watcher asserts the reasserted model/effort line in the first post-merge relaunch receipt.
