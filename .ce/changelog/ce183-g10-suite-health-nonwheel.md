---
slug: ce183-g10-suite-health-nonwheel
date: 2026-06-21
kind: fixed
scope: validator suite health
issue: ce-ops#183
---

Stabilizes the non-wheel validator full-suite clusters reproduced on clean
main.

- Uses a shared git-worktree detector so empty ambient ancestor `.git`
  directories no longer make pytest temp trees look tracked by `/tmp`.
- Keeps local unauthenticated git calls token-clean when the parent shell
  exports `GH_TOKEN` or `GITHUB_TOKEN`, while explicit scoped-token calls still
  receive the intended credential.
- Keeps greenfield onboarding CLI tests inside tmp-scoped workspace roots.

Known residual: the full suite still has packaging/version failures tied to the
committed first-party app wheel and generated version SHA; that remains pending
the #312 wheel/packaging cleanup scope.
