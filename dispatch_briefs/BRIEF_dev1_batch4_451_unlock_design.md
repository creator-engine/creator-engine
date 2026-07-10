# BRIEF — dev-1 batch 4 (foreman mode, 2 file-disjoint units)

Role: implementer-foreman (dev-1, non-contained). Per unit: own worktree off FRESH origin/main,
own branch/PR/changelog/carrier, semantic novelty check FIRST. You have gh — read the referenced
tickets directly.

## U1 — branch `ce-451-surfaces-checker-hardening` — work class: story
Implement ce-ops#451 (read the ticket with gh for full detail; it is precise). Two coupled gaps
in validators/creator_engine_validator/checks/surfaces_manifest.py:
(a) `_pinnable_null_digest_errors` (~216-235): the literal "UNSET" placeholder string bypasses
the pinnable-digest gate. Fix: treat "UNSET" as unpinned, gated by an EXPLICIT allowlist
(shrink-only ratchet style, like the repo's other debt allowlists) so publish→pin becomes
CI-enforced.
⚠️ CRITICAL CONSTRAINT: surfaces/manifest.yaml on current main has the CE seat image at
commit_or_digest: UNSET — your change MUST keep current main GREEN by seeding the allowlist with
exactly that entry. The 0.3.2 release ceremony will pin the real digest and remove the allowlist
entry (that's the forcing function working as intended). A version of this change that turns
main red is WRONG, not strict.
(b) `_matching_surface_for_image` (~284-292): `key.split("-")[0]` yields generic alias "ce"
which substring-matches nearly any FROM token. Fix per ticket: exact first-component matching +
explicit overrides instead of substring.
Tests: extend the checker's existing test file — cover UNSET-not-allowlisted → error,
UNSET-allowlisted → pass, allowlist shrink-only if you implement it as a ratchet, and the alias
misattribution case (a FROM token containing "ce" that must NOT match).
Allowed paths: checks/surfaces_manifest.py + its test file + changelog/carrier ONLY. Do NOT
edit surfaces/manifest.yaml data. If the fix seems to require touching the manifest schema or
other checkers, STOP and report.

## U2 — branch `ce-454-dependency-unlock-contract` — work class: tiny
Design-doc slice 1 of ce-ops#454 (read the ticket + ALL its comments with gh — they carry the
full design record incl. mechanism references). Author a NEW page
docs/contracts/dependency-unlock.md in the exact style of docs/contracts/forge-trigger-taxonomy.md
(read it first; mirror its "documentation-only, defines no executor" posture): the vocabulary and
contract for merge-triggered dependency unlock — how a work item declares blockers
(blocked-by label / structured body field, aligned with what forge_triage.readiness_blockers
already parses), which merge/close events re-evaluate blockers, what an unlock mutation is
(label flip + eligibility), idempotency/replay guards, and fail-closed rules (unresolvable
blocker ref = stays blocked). Documentation ONLY — no code, no workflow files.
PRODUCT LENS HARD RULE: zero ce-ops#/internal-fleet/seat/tenant references in the page itself —
write it as ecosystem product vocabulary (the ticket link belongs in the PR body, not the page).
Allowed paths: the new docs/contracts page + changelog/carrier ONLY.

## STOP lines (both)
⛔ docs/install.sh, docs/downloads/**, docs/llms-install.md, install-answers.schema.yaml, and any
file hash-pinned in llms-install.md (`_sha256:` pins) — never touch. Never sign. No
review/approve/merge/enqueue.

## Evidence bar
Full `ce validate-pr` GREEN one pass before push. Changelog + carrier per branch (stem == slug).
Exactly one `- **Declared work class:** <story|tiny>` line per PR body (U1=story, U2=tiny).
Signal per unit: `READY <branch> <40-hex sha> PR=<url>` (or `READY <branch> already-resolved`).
