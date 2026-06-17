---
slug: ce103-s2-posture
date: 2026-06-17
kind: changed
scope: runner / Ring-1 posture non-spoofability
base: 54b3c737a9f0bacb1a49dae56dc5247e5689806f
---

Hardens Ring-1 runner-installed `git`/`gh` shims so a child process cannot
downgrade governed posture by exporting mutable environment.

- Pins runner `Ring1ToolGuardConfig.posture` to `governed`; `auto` and
  `ungoverned` are rejected for runner shim configs.
- Renders `--posture governed` as an immutable generated-shim constant. The
  shim no longer reads `CE_RING1_POSTURE` or `CE_LEDGER_ROOT` from child
  environment when deciding posture or ledger binding.
- Wires OpenShell default guard provisioning to bake the runtime worktree root;
  ledger-root baking is explicit-only so the v3 runner surface does not
  redeclare legacy local-state path literals.
- Leaves the deployed-Claude `--posture auto` hook path unchanged.
- Adds both-direction coverage: env-spoofed `git push` still exits with the CE
  Ring-1 deny code, while governed `git status` still reaches the real git
  binary.
- Rebuilds `creator_engine_validator-0.2.0-py3-none-any.whl` and refreshes
  `validators/wheelhouse/SHA256SUMS` with digest
  `f94d6db443a980be06e7fbe6e977559b7cb0efb77d94ae6a70714a048b42559c`.
