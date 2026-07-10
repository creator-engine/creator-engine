# BRIEF — dev-4 — 2026-07-09 — P4: ratification-binding DESIGN ARTIFACT (STRANGELOOP-1 pool)

Role: **implementer** (design-artifact unit — one .md deliverable + carrier/changelog; NO product
code changes). Contained COMMIT-ONLY seat. Fresh worktree /var/tmp/wt-513-design off origin/main
(fetch first). Branch `ce-513-ratification-binding-design`.
Signal: `READY ce-513-ratification-binding-design <sha> .ce/pr-manifests/ce-513-ratification-binding-design.md`
or `BLOCKED ce-513-ratification-binding-design <reason>`. Declared work class: **story**.
NO .ce/brain/assertions.yaml edits. Standing preflight directive: FULL `ce validate-pr` before READY.

## U1 — docs/design/ratification-authorization-binding.md (work class: story)

DESIGN PROBLEM (verified facts, 2026-07-08, all on main): `--approver-ref` is format-validated
only (any 64-hex; "value-free opaque digest" — v3_cli.py:128,826). The PreToolUse hook blocks only
`ce launch` (hook_check.py:200) — `ce ratify` / `ce merge --apply` pass through. Docs claim "the
agent cannot ratify on its own behalf" with ZERO enforcement. The bootstrap smoke test already
ratifies programmatically. Ratified doctrine: users NEVER type commands — the user supplies intent
and natural-language authorization; the governed agent invokes verbs and records authorization.

DESIGN MANDATE — produce the full design for binding agent-invoked ratification to recorded user
authorization:
1. **Authorization event**: pending-ratification lands in the operator's AWAITING-OPERATOR inbox;
   the user's natural-language yes mints an authorization event (schema: who/when/scope_sha/
   utterance-digest/channel).
2. **Derived approver_ref**: HMAC over scope_sha + authorization event (unforgeable without
   recorded consent), replacing the value-free token. Key custody + rotation via the existing
   approval-capability mint system (design it as the template).
3. **authorization_source record** in the evidence chain (fields, storage, verification at gate).
4. `ce merge --apply` gets the same capability-marker treatment.
5. Smoke-test coupling: bootstrap smoke must exercise the binding, not bypass it (design the
   test-mode seam explicitly — no prod bypass flags).
6. Enforcement layering: hooks are advisory for Codex Ring-1 (deferral bypasses them) — binding
   must hold at the VALIDATOR/gate layer, not hooks alone.
7. Migration: current hex approver_refs → derived refs (compat window, cutover gate).
8. Slice plan: 2-3 mergeable slices with acceptance evidence each (evidence-gated closure).

Deliverable quality bar: implementable-without-further-design; every claim about current code
grounded with file:line refs verified in YOUR worktree (fresh origin/main — never trust this
brief's line numbers blindly); include a threat table (who can forge what, before vs after).
Public-repo product lens: no ce-ops#N refs, no internal hostnames/seat topology.
