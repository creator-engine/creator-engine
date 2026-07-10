# SEED BRIEF — dev-1 BATCH (3 file-disjoint items) — 2026-07-02

Role: implementer (you self-push your own PRs). Work the three items below as
independent lanes (worktrees off fresh origin/main; item 1 continues an existing
branch). They are file-disjoint — safe to run as parallel subagent threads.

## STANDING DIRECTIVES (apply to every item)
- FULL local preflight (`ce validate-pr`, CI-parity, clean tree, ONE green pass)
  before EVERY push. Do not discover gates via CI.
- Every PR: `.ce/changelog/<branch-slug>.md` + regenerated carrier
  `.ce/pr-manifests/<branch-slug>.md` via carrier_gen API
  (`write_carriers(base="<merge-base>")`) — never hand-edit. Carrier stem MUST
  equal branch slug.
- PR body: exactly one `- **Declared work class:** <XS|S|M|L>` line
  (XS/S/M/L vocabulary — tiny/story/feature/epic is RETIRED).
- Evidence bar: report commit SHA + PR number per item. "Done" without a
  verifiable pushed SHA is not done.
- Public docs (docs/**) = product lens, ZERO ce-ops# references.

## ITEM 1 — FIRST, small: finish PR #720 fix (branch ce-329-scrum-to-ce-guide)
Re-review on 18caa335d = REQUEST_CHANGES. Your vocabulary fix PASSED. One
remaining blocker, two spots in docs/guide/agile-to-ce-sdlc.md:
  1. Line 3: `> **Draft — content pending final review.**` — DELETE (the doc is
     linked from welcome.md/solo-ceo-onboarding.md/solo-dev-onboarding.md and
     publishes today; the banner is false).
  2. Lines 243-247: entire `## Review Notes` section ("This draft still needs
     final content review…") — DELETE (same reason).
Nothing else in the doc needs changing. Push to the SAME branch; PR stays
DRAFT (controller publishes after re-review). Allowed paths: that one doc (+
changelog/carrier already exist — update changelog only if content warrants).
STOP after push; do not un-draft, do not request merge.

## ITEM 2 — ce-ops#369: Fleet-IaC guard denylist from identity-registry SSOT
Branch: ce-369-fleet-guard-ssot-denylist (off fresh origin/main).
Problem: `validators/creator_engine_validator/checks/fleet_manifest_guard.py`
hand-maintains INTERNAL_LITERAL_TOKENS; real gap already happened (cedev1/
cedev3/ubuntuaws745-cmyk initially missing, caught in #679 review).
Build: derive the denylist from the authoritative SSOT
`creator-engine/ce-ops : infra/identity-registry.yaml` (you have GH read
access; pick the mechanism — vendored codegen snapshot with a freshness check,
or CI-time fetch with fail-closed fallback to the vendored copy — justify your
choice in the PR body). Schema already on main:
`validators/creator_engine_validator/schemas/identity-registry.schema.yaml`.
Also from the same review (include if low-risk): word-bound the `dev-1..dev-4`
substring matches (regex, so `lead-dev-1` doesn't false-positive); evaluate
narrowing the broad `forge/` token — if narrowing is risky, note it in the PR
and leave for follow-up.
Allowed paths: checks/fleet_manifest_guard.py, its tests
(validators/tests/unit/), any new vendored snapshot/codegen helper under
validators/, changelog + carrier. Tests REQUIRED (test-coupling gate is live:
code-class diff must add tests). Work class: S or M honestly sized.
STOP after PR open + CI green; controller routes review.

## ITEM 3 — ce-ops#376: commissioned-but-unscheduled sweep (forge triage)
Branch: ce-376-unscheduled-sweep (off fresh origin/main).
Problem (process hole, ce-ops#37 stalled 18 days invisibly): OPEN issues that
are (a) user-story/Operator-commissioned, (b) unmilestoned, (c) unreferenced by
the active arc are invisible to day/night arcs.
Build: a sweep step in the forge-triage lane (forge/ triage modules; there is
an existing triage cron cadence) that surfaces such issues into arc triage
output — e.g. a `commissioned_unscheduled` section in the triage report/labels
(advise-mode; do NOT auto-dispatch). Definition of commissioned: user-story
label or Operator-authored; make the predicate configurable.
⚠️ TERRITORY: do NOT touch conveyor-daemon files (conveyor redesign is frozen
pending ce-ops#388 ADR). Triage modules only.
Allowed paths: validators/creator_engine_validator/forge/ (triage modules
only), validators/tests/unit/, changelog + carrier. Tests REQUIRED.
Work class: S. STOP after PR open + CI green; controller routes review.

## REPORT
Per item: branch, pushed head SHA, PR number, preflight result (one-pass
green?), declared work class, anomalies. Item 1 first (publish-today path).
