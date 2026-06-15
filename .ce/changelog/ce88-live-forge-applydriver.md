---
slug: ce88-live-forge-applydriver
date: 2026-06-15
kind: added
scope: onboard --apply / forge driver
issue: ce-ops#88
---

**Production live-forge `ApplyDriver` (Phase 1) — an existing already-CE repo's
`onboard --apply` now COMPLETES instead of dead-ending at `e2_brownfield_seam_unavailable`.**

Published 0.2.0's existing-repo `onboard --apply` was inert: the `_onboard_apply_driver`
seam handed back the base `ApplyDriver`, whose forge methods are all noop stubs, so the #85
plain-join path could never fire in production (detection's first live read failed →
brownfield refuse). This wires the concrete forge legs so the most common pilot case — a new
dev joining an already-CE repo — converges.

- **`LiveForgeApplyDriver`** (`onboard_apply_live.py`) overrides only the forge legs and
  inherits the host legs unchanged: live read-only detection (`repo_exists`, `verify_repo`,
  `verify_workflow` at the pinned `CE_WORKFLOW_SHA256`, `verify_branch_protection`,
  `existing_branch_protection_contexts`, `probe_bootstrap_token`) plus the idempotent
  plain-join apply legs — a **verify-first, defer-not-mutate** `configure_branch_protection`
  (OQ-F: **zero forge writes on the happy path**) and a local-clone `checkout_workspace`.
- **Auth is composed, not invented:** each forge read routes through the shipped
  `mint_scoped_token` → `app_jwt_gh_runner` (Bearer) → `authenticated_gh_runner` (`GH_TOKEN`
  in the child env only) → `revoke_scoped_token` toolchain, at the Phase-1 read ceiling
  `{metadata:read, contents:read, administration:read}`. The App PEM stays behind a host-side
  RS256 signer; the token value never touches argv / a log / an exception / evidence / disk.
- **Ceiling-driven three-tier minter (ce-ops#88 amendment):** `scoped_token` now enforces the
  requested `(scope, level)` against the bound policy's ratified ceiling — a permanent
  never-list (`organization_administration`/`secrets`), an escalation-gated default-deny tier
  (`administration:write`/`contents:write`/`workflows:write`, mintable only against explicit
  per-install authority), and the read-mostly baseline. Replaces the old level-blind blanket
  ban (which could not mint the ratified `administration:read` branch-protection-read scope).
  Phase-2 write authority needs **zero** further minter edits.
- **Fail-closed selection (OQ-D):** the `live_forge_select` factory returns the live driver
  ONLY when the explicit `CE_FORGE_LIVE_FORGE` env flag is set AND the App credentials resolve
  host-side; otherwise it returns the base noop driver. Default **OFF**; autodetect rejected.
  The flag is a host **env** flag (OQ-D permits "answers/env flag") rather than an
  install-answers key, because the answers schema's sha256 is pinned inside the
  ce-root-v1-signed `docs/llms-install.md` — keeping the flag host-side avoids a trust-root
  re-sign and co-locates it with the App credentials it gates. The `_onboard_apply_driver()`
  seam signature is unchanged (the factory wraps its result at the call sites).
- **Phase-1 app-installation coverage:** `verify_app_installation` is a read-only coverage GET
  (`GET /installation/repositories`) confirming the already-installed App covers the repo — no
  install click, no mutation. The install click / greenfield legs stay Phase-2.
- **OQ-C:** `verify_workflow` keeps the exact-digest byte-pin and surfaces a distinct
  `workflow_digest_mismatch` diagnostic for a byte-drifted workflow.

REAL-shape acceptance (ce-ops#44): Mode-B tests replay VERBATIM-captured live `gh api` JSON
(capture commands recorded in `fixtures/ce88_live_forge/CAPTURE.md`). The live Mode-A run is
the clean-room VPS install rehearsal DoD. No Phase-2 greenfield legs (repo-create / workflow
install) in this gate.
