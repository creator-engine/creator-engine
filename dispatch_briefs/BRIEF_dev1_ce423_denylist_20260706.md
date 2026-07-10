# DISPATCH BRIEF — dev-1 — ce-ops#423 [G7] bidirectional per-tenant confidentiality denylist matrix
Dispatched: 2026-07-06 ~04:1xZ by CE-DEV-2 (controller). Role: implementer, self-push seat.

## Housekeeping FIRST
Your local branch `ce-414-installer-doc-egress` (b7db0e75) ALREADY LANDED on main as PR #802
(7916c43a, same title/content) and ce-ops#414 is CLOSED. Delete or park that branch; do NOT
push it and do NOT include its commit in this unit.

## Unit
- Ticket: creator-engine/ce-ops#423 — per ratified design §5 (ce-ops#421,
  .ce/state/research/CLIENT_TENANT_DEPLOYMENT_DESIGN_20260703.md — dual-written to your host;
  if the file is absent, STOP and request it from the controller, do not guess the design).
- Branch: `ce-423-tenant-denylist-matrix` off FRESH `origin/main` (fetch first).
- Declared work class: **story** (CI enum tiny|story|feature|epic; ticket label wc:S).

## Scope (from ticket, binding)
Generalize `validators/creator_engine_validator/public_docs_confidentiality.py`:
1. CE `FORBIDDEN_PATTERNS` stay UNCONDITIONAL — never gated, never weakened.
2. Add per-tenant `denylist_ref` supplying data-driven patterns enforced BOTH directions:
   tenant A identifiers never reach tenant B venues nor CE public; CE internals never reach
   tenant venues.
3. Reuse the shrink-only debt-ratchet allowlist mechanic per tenant.
4. Scan surface extends to PR bodies, issue text, evidence bundles.
Review bar carried from #839 round-1: use the config-object seam (patterns/config passed as
a structured object, not scattered params). No weakened patterns anywhere — additive only.

## Allowed paths (territory-checked 2026-07-06; collisions = STOP + report)
- validators/creator_engine_validator/public_docs_confidentiality.py
- NEW tenant-denylist module/config under validators/creator_engine_validator/ (+ schema if needed)
- validators/tests/ (matching unit/integration tests)
- .ce/changelog/ce-423-tenant-denylist-matrix.md + carrier
DO NOT touch (in-flight elsewhere): onboard_apply.py, dependency_unlock.py,
.github/workflows/*, list-checks/digest-normalization code (dev-3's #458/#460).

## Evidence bar + stop lines
- Standing preflight directive (ce-ops#303): FULL `ce validate-pr` (CI-parity) GREEN in one
  pass BEFORE self-push; do not discover gates via CI.
- Carrier via carrier_gen `write_carriers(base="origin/main")` — never hand-list; carrier
  stem == branch slug. Changelog fragment required. PR body must carry
  `- **Declared work class:** story`.
- Self-push + open PR (your standing authority), then report: PR #, head SHA, validate-pr
  summary. Controller reviews/gates — you never approve or merge.
- STOP lines: any sha256-pinned/signed-chain file → STOP+report (release op). Signature
  invalid anywhere → STOP, report bytes; controller signs. Path outside allowed set needed →
  STOP+report.
