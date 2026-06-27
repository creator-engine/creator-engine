---
slug: fix-ce-ops-328-brownfield-forge-identity
date: 2026-06-27
kind: fix
scope: brownfield onboard --apply — forge actor identity resolution
issue: ce-ops#328
---

**Brownfield `onboard --apply` resolves the forge actor identity before building the join-PR scaffold.**

The adoption path skipped `github_bootstrap_token_probe` — the only leg that resolves the forge
actor identity from the bootstrap token's `GET /user` — yet `brownfield_build_scaffold`
hard-requires that identity and refused with `forge_identity_unresolved` when it was unset, so
every solo brownfield adoption `--apply` refused unconditionally. The probe now runs in adoption
mode, right-sized to identity-only for `mode != "new"` (ce-ops#94: `bootstrap_required_scopes`
returns `()`, demanding no greenfield write scopes) so it resolves the actor identity without
requiring write capability. Fail-closed behavior is preserved — a missing or invalid bootstrap
token still refuses at the probe leg before any scaffold build.
