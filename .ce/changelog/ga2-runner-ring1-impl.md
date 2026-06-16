---
slug: ga2-runner-ring1-impl
date: 2026-06-16
kind: added
scope: runner / Ring-1 PATH shim proof
base: bcf84649ab6343784bd1aa45690f32ded21ba339
---

Adds increment 1 of runner-owned Ring-1 enforcement for OpenShell-backed runs.

- Added runner-rendered `git`/`gh` PATH shims that build Bash-shaped
  PreToolUse events, invoke the public `hook-check --format raw` CLI, parse the
  JSON decision, and convert `deny`/`block` to exit 126 before the real binary
  can execute.
- Added opt-in OpenShell backend plumbing to install the guard after sandbox
  creation and inject the guarded PATH into sandbox runs.
- Added unit coverage for shim event mapping, allow/deny behavior, fail-closed
  hook-check errors, OpenShell install ordering, policy-validation ordering, and
  PATH environment injection.
- Added an integration proof where a fake `codex` child process runs
  `git push origin main`; the runner-installed shim resolves governed posture
  through the real hook-check CLI and denies before downstream git is reached.
- Rebuilt the validator app wheel and refreshed `validators/wheelhouse/SHA256SUMS`.

Coverage is precise: this increment proves harness-agnostic shell-level
`git`/`gh` denial via runner-injected PATH shims. It does not harden absolute
`/usr/bin/git`, bundled binaries, libgit2/JGit, raw HTTPS/curl API writes, PATH
resets, or arbitrary non-shell filesystem access. Binary hiding/mount-over,
filesystem mediation, and egress defense remain the tracked next gate.
