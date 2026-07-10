# BRIEF — ce-395-tag-timing-policy — L7 auto-release residual (ce-ops#395)

Role: implementer (dev-1 self-push). Branch: `ce-395-tag-timing-policy` off freshly-fetched origin/main.

## Mandate
Read ce-ops#395 directly (you have gh read access to creator-engine/ce-ops) — it is the L7
auto-release residual: the bump-to-main / tag-timing policy question left open when L7 slices
a/b/e/f merged (#698/#699/#701 era). Deliver:
1. A policy DRAFT document (docs/ or playbooks/ per where L7's release docs live — follow the
   existing release-process doc home; product lens, no ticket refs in body) laying out the options
   the ticket raises (when the version bump lands on main relative to tagging; who/what triggers
   the tag; failure/rollback ordering), with ONE recommended default clearly marked. The Operator
   ratifies the policy choice — mark the decision point explicitly as OPERATOR-DECISION.
2. ONLY the mechanically-safe implementation, IF ANY part of #395 is purely mechanical and
   ratification-independent (e.g. a guard/test that enforces invariants true under ALL options).
   If nothing qualifies, ship the draft alone — do NOT implement a policy choice ahead of ratification.

## Semantic novelty check first
Verify #395 isn't already resolved: read the ticket's current state + comments, grep main's
release automation (validators + .github/workflows) for existing tag-timing handling. If resolved
or superseded, signal `BLOCKED ce-395 already-resolved <evidence>` instead of inventing work.

## Constraints
- Files: the policy doc + changelog + carrier (+ guard/test files ONLY if part 2 applies — name
  them in the carrier). Nothing release-signed (docs/install.sh, docs/downloads/ FORBIDDEN).
- ⛔ Signed-artifact stop-line: signature-gate failure → STOP + report bytes; never sign.
- Work class: tiny (doc-only) or story (with guard). Full `ce validate-pr` GREEN one pass.

## PR + evidence
PR to main, title `docs: release tag-timing policy draft (options + recommended default)`.
Exactly one `- **Declared work class:** <class>` line. Signal:
`READY-FOR-HARVEST ce-395-tag-timing-policy <40-hex sha> PR #<n>`.

## Stop line
No approve/merge/enqueue/self-review. The policy DECISION is the Operator's — your PR carries the
draft, not the choice.
