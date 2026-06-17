---
slug: ce85-e3-adoption-apply
date: 2026-06-17
kind: added
scope: onboard_apply executor + live-forge driver (E3 brownfield adoption-apply — the governance join-PR layer)
issue: ce-ops#85
base: 1a0672071c1c77e2ee78c28490e81a40a947901a
---

**E3 brownfield ADOPTION-APPLY — the governance join-PR layer.** Converts the
`brownfield_deferred` / `e2_brownfield_seam_unavailable` dead-end (for a genuine
non-CE existing repo) into a non-destructive **governance join PR**: a stable
adoption branch carrying the CE scaffold (`.ce/skills/*`, the scope seed, and
`.github/workflows/ce-validate.yml` at the pinned digest) + a real PR against the
repo's default branch. PR-mediated and non-destructive by construction — never
direct-pushes the default branch, never force-pushes, never mutates branch
protection, and idempotent (a re-run reconciles to the same branch + same PR).

- **Seven mode-gated adoption legs** appended to `onboard_apply.LEG_IDS` (E2 §6
  seam 1 — the `Ledger`/`LegOutcome` shape is unchanged): drift-check → scrub →
  build-scaffold → push → open-join-PR → verify-preserved-checks → record-evidence.
  In a greenfield/plain-join run they `skip` (`not_brownfield_adoption`); in an
  authorized adoption run the greenfield FORGE legs `skip`
  (`brownfield_adoption_mode`). `BROWNFIELD_APPLY_STEP_IDS` is reconciled to this
  exact executor leg-set (verify-verdict MINOR — `github_branch_protection` dropped
  from the projection, since the join PR never mutates protection).
- **Default-OFF dual escalation.** The adoption write path requires BOTH host ENV
  flags `CE_FORGE_LIVE_FORGE=1` and `CE_FORGE_ADOPTION_WRITE=1` (mirrors #233; ENV
  not answers-schema → no ce-root-v1 re-sign cascade). Unauthorized, behaviour is
  byte-identical to today's refuse. No auto-merge (a human merges); live = VPS
  Mode-A only. `administration:write` is excluded (OQ-1).
- **Two-token model (HARD).** Reads (drift, scrub, the local clone,
  preserved-checks) ride the inherited Phase-1 READ token
  (`{metadata:read, contents:read, administration:read}` — `administration:read`
  gates the protection read); the push + open-PR legs ride a SEPARATE WRITE token
  (`{metadata:read, contents:write, workflows:write, pull_requests:write}`, binding
  the `(contents,write)`+`(workflows,write)` Tier-2 escalation, `pull_requests:write`
  Tier-3 baseline) minted for those two legs ONLY and revoked immediately after.
- **Secrets-scrub affirmatively fail-closed (HARD).** `brownfield_secret_preflight`
  requires an affirmative zero-exit AND a parsed empty-findings list from BOTH
  sha256-pinned scanners (Gitleaks AND TruffleHog). Any finding, scanner non-zero
  exit, exec error, timeout, unparseable output, or a missing scanner report
  raises `ApplyRefused` BEFORE any branch is built/pushed/PR'd — the absence of
  parsed findings is never treated as clean. The plan-side fail-open seam is fixed:
  a `clean` status now requires an affirmative `scanner_available: True`. The live
  scanner binary pins are commissioned at the VPS Mode-A rehearsal; until pinned the
  live scrub fail-closes (no unverified binary is ever executed).
- **PR #251 fail-closed fixes.** Branch-protection preservation now treats only
  GitHub's explicit "Branch not protected" response as the no-protection case; 403,
  transient errors, generic 404s, and API/read exceptions raise
  `brownfield_protection_read_failed`. Scaffold creation now raises on real `git add`
  or `git commit` failures and verifies the committed `HEAD` tree (`.ce/` scaffold
  paths plus the pinned CE validate workflow blob) before any push/PR. The live
  scanner supply path is wired through host env pins:
  `CE_FORGE_GITLEAKS_URL`, `CE_FORGE_GITLEAKS_SHA256`,
  `CE_FORGE_TRUFFLEHOG_URL`, and `CE_FORGE_TRUFFLEHOG_SHA256`; absent or invalid
  pins keep the scrub fail-closed.
- **Scope reconcile.** This PR deliberately names
  `validators/tests/unit/test_v3_installer.py` as an exception to the ratified
  10-path seed manifest because it owns the planner-side `_apply_steps` contract
  that must stay aligned with the executor leg ids. The per-PR carrier records the
  full closed 15-path set and this exception.
- **Honest counters (§4):** `brownfield_adopted` (a join PR opened OR idempotently
  claimed AND verified this run — never on a planned-but-unpushed branch or an
  unverified PR), `brownfield_adoption_pr`, `brownfield_scrub_findings(_waived/
  _blocking)`.
- **plan_ref = inventory_sha256** (per the ratified spec): confirmed no downstream
  consumer mis-reads it as a runtime-policy digest — the only `ce-policy-sha`
  consumer (`forge.plan_approval`) runs in the coordination/merge flow, which the
  adoption phase (open PR + stop) never enters.

Reuses the shipped `forge/*` primitives unchanged (`push_change`, `open_change`,
`scoped_token`) — zero minter/schema edits. Fakes-only CI tests (the §10 plan +
the new fail-closed / two-token / push-never-force / PR-idempotent cases); the
live join PR is the VPS Mode-A rehearsal DoD.
