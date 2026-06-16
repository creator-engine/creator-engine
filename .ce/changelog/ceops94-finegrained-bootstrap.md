---
slug: ceops94-finegrained-bootstrap
date: 2026-06-16
kind: fixed
scope: validator engine (onboard --apply bootstrap-token probe)
issue: ce-ops#94
---

**`onboard --apply` now accepts fine-grained GitHub PATs, and the bootstrap-token
requirement is right-sized to the operation — unblocking ce-dev-3 onboarding (#90)
with its existing fine-grained PAT and no admin role.**

The live-forge bootstrap probe rejected **fine-grained** PATs because it derived a
token's capabilities only from the classic `X-OAuth-Scopes` header, which
fine-grained PATs never emit (→ empty scopes → all four `REQUIRED_BOOTSTRAP_SCOPES`
read as "missing" → `ApplyRefused("bootstrap_token_scope_refused")`). Fine-grained
PATs are GitHub's recommended default, so external pilot installs hit it too. The
fix is two complementary parts, both fail-closed:

- **Part 2 — right-size the requirement to the operation.** New
  `v3_installer.bootstrap_required_scopes(mode, org_create_needed)`: a **plain-join**
  (joining an already-CE repo, `github.mode != "new"`) performs ZERO forge writes
  with the bootstrap PAT — every forge op rides the App installation token and
  branch protection is verify-first/defer-not-mutate (never written) — so the
  requirement is **identity-only** (`()`); **greenfield** keeps the full write set
  (+ org repo-create when new-in-org). `bootstrap_scope_table` gains a `required=`
  override (default unchanged). The probe leg (`onboard_apply.py`
  `github_bootstrap_token_probe`) branches on the right-sized requirement.
- **Part 1 — accept fine-grained PATs.** New `onboard_apply_live._detect_token_type`
  classifies by prefix (`github_pat_` → fine-grained; `ghp_`/`gho_`/`ghu_` →
  classic), with classic-header presence as a fallback. `probe_bootstrap_token` now
  reports `token_type` and derives a classic scope set **only** for classic tokens
  (no empty "missing-everything" set is fabricated for fine-grained). The leg accepts
  a classic token via its scopes (unchanged), accepts a fine-grained token with
  greenfield write-capability **enforced fail-closed at the write legs** (each
  refuses on a 403 — a fine-grained PAT's grant is not non-destructively
  introspectable, per GitHub's API model), and refuses an unrecognized/unverifiable
  token type (`bootstrap_token_unverifiable`) or an invalid token
  (`bootstrap_token_invalid`). Identity-vs-bot refusal is unchanged.

Verified against current GitHub API behavior (token-format prefixes; fine-grained
PATs emit no `X-OAuth-Scopes` and expose no permission introspection; token
capability = user-access ∩ token-grant, so a write-not-admin dev cannot mint an
`administration:write` fine-grained PAT). The fine-grained `GET /user` unit fixture
(`user_response_finegrained.txt`) is a VERBATIM capture from ce-dev-3's real
fine-grained PAT (CAPTURE.md), PII-reduced.

**Known follow-up (flagged, not in this PR):** the dry-run plan projection
(`v3_installer.build_github_leg_plan`) still reports the full greenfield scope set
for a plain-join and is not right-sized — it is a non-gating projection (the apply
path does not consult its `scopes.ok`) and right-sizing it would alter the tested
`test_github_leg_unprobed_scopes_fail_closed` invariant; plan/apply parity is a
clean follow-up.

The `validators/creator_engine_validator/**` edits require the app wheel to be
rebuilt: `creator_engine_validator-0.2.0-py3-none-any.whl` is rebuilt from current
source (`setuptools.build_meta`) and `validators/wheelhouse/SHA256SUMS` re-pinned to
the rebuilt digest (only the app-wheel line). `_version.py` is left untouched (the
baked `BUILD_GIT_SHA` is an ancestor of HEAD, so the freshness check stays clean —
no version bump).
