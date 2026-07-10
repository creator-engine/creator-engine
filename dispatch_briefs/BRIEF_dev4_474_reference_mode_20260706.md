# BRIEF — dev-4 — ce-ops#474 PRODUCT half: verify_preserved_checks must honor declared protections:reference (0.3.4)
2026-07-06 ~13:1xZ by CE-DEV-2. Role: implementer (foreman), contained, COMMIT-ONLY → harvest. Branch `ce-474-verify-reference-mode` off FRESH origin/main. Class: story.

You cannot read ce-ops; the FULL ticket is embedded below. Scope = the ticket's ask (a), OPTION 1 ONLY (the ratified product direction). The ops/tenant half (b) is an Operator decision — NOT yours, do not touch tenant configs or live repos.

Implementation requirements beyond the ticket text:
1. Honor reference mode ONLY when the answers file explicitly declares `github.protections: reference` — the 403-acceptance path must be gated on that declaration. An undeclared 403 stays a hard failure exactly as today (the #171 fail-early inventory gate remains the guard for undeclared cases; do not weaken it).
2. Evidence record: emit `protection_floor: documented-not-enforced` in the verify evidence artifact per the ticket, including which branch/repo and the declared mode, so tenant records are auditable.
3. Tests, failure-direction proven: (a) declared reference + 403 → verify PASSES with the evidence record; (b) NO declaration + 403 → verify still FAILS with protection_floor_unenforceable; (c) declared reference + 200 (protection actually exists) → verify runs its normal assertions (declaring reference must not skip checks that ARE enforceable).
4. Docs: update whatever doc describes protections modes / verify behavior (product lens, no ce-ops refs in public docs).

Bar: FULL `ce validate-pr --declared-work-class story` GREEN one pass (env-failure protocol as before: reproduce on clean origin/main, evidence to /var/tmp/ce-474-evidence/, signal BLOCKED-ENV); carrier via write_carriers (stem == branch slug); changelog fragment. COMMIT-ONLY; signal `READY-474 <sha>`. STOP lines standard; no sha-pinned files; do NOT touch live tenant repos or canary sandboxes.

---- EMBEDDED TICKET ce-ops#474 (verbatim) ----
TITLE: verify_preserved_checks refuses free-plan private repos even with protections:reference — and live tenant mythos has NO enforceable protection floor

## Symptom

Found 2026-07-06 by canary C3 (0.3.3, own-App lane, /var/tmp/ce-canary-c3/):

Apply chain ran fully green through the join PR (#2 on chmod735-dor/ce-canary-sandbox), but the **brownfield `verify_preserved_checks` leg REFUSED** with `protection_floor_unenforceable` — GitHub 403 "Upgrade to GitHub Pro or make this repository public".

## Evidence

- Canary C3 log: `/var/tmp/ce-canary-c3/` on DGX controller host (2026-07-06)
- The repo's **answers file declared `github.protections: reference`** — the operator explicitly chose reference mode, acknowledging the floor cannot be forge-enforced
- `verify_preserved_checks` still attempted to call the branch-protection API and refused when it got 403, rather than honoring the declared mode
- Verified same wall on the **LIVE tenant**: `chmod735-dor/mythos` (private, org on Free plan) returns the same 403 on `branches/main/protection` — Arad's install runs with reference-mode protections only, no forge enforcement
- Adjacent closed issues: ce-ops#160 (Rulesets fallback for apply step), ce-ops#171 (fail-early detection at inventory) — both implemented via creator-engine#319, but neither updated the **verify leg** to accept reference mode

## Root cause

The `verify_preserved_checks` component was not updated when `protections:reference` mode was introduced. It still treats any non-200 from the branch-protection API as a hard failure, rather than checking whether the answers file declared reference mode and short-circuiting to an evidence record of `floor: documented-not-enforced`.

## Impact

- Any free-plan private repo tenant that correctly declares `protections:reference` will hit a spurious hard failure at the verify step (last leg of apply), making the install appear broken even though the operator made a deliberate, valid choice
- The live Mythos tenant (Arad, first customer) is currently operating with **no enforceable governance floor** and no tracked decision about it

## Two asks

### (a) PRODUCT — 0.3.4 candidate

Decide and implement one of:

1. **Honor reference mode in verify:** When `github.protections: reference` is declared, `verify_preserved_checks` should accept the 403, skip forge-enforcement assertions, and record `protection_floor: documented-not-enforced` in the evidence artifact. This is the correct behavior for a declared reference-mode install.

2. **Fail early at INVENTORY time:** Treat a plan that cannot enforce protections as a hard prerequisite failure, surfaced during `ce inventory` / pre-apply, not silently at the last apply leg. If the operator has not pre-declared `protections:reference`, the install must halt with a clear upgrade-or-go-public message before any forge changes are made.

Option 1 is preferred (reference mode is a valid, declared operator choice) but the product call is Operator's.

### (b) OPS/TENANT — Operator call needed for mythos

`chmod735-dor/mythos` is currently unprotected at the forge level. Options:

- Upgrade the `chmod735-dor` org to GitHub Team (paid) — enables classic branch protection and rulesets
- Make `mythos` a public repo — free plan lifts the restriction
- Formally accept `protections:reference` for mythos and update the install evidence record accordingly

Decision affects the Arad DoD narrative and the demo story for the NVIDIA pitch.

## Refs

- ce-ops#160 (closed: apply via Rulesets) — apply step, not verify step
- ce-ops#171 (closed: fail-early detection) — inventory gate, not reference-mode honor
- ce-ops#421 (open: client-tenant deployment design) — tenant model context
- ce-ops#469 (open: canary batch findings) — adjacent canary findings from same session
- creator-engine#319 (merged: landed #160+#171 fixes)
