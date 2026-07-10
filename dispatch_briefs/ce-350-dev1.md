# BRIEF — dev-1 — Authority spine slice #350 (ce-ops#350 / G2.007.3)

You are a born-foreman builder seat (non-contained; you SELF-PUSH your own PR as ce-dev-1). This is the authority spine follow-on to #349 (which you authored and which is now MERGED to main). Drive it to a green PR. You may use subagent threads; stay inside the allowed paths.

## Goal
Wire the reviewer-authority-envelope carrier into the LIVE launch→hook→broker review path, so a distinct reviewer venue can carry an already-minted envelope end-to-end. Fail-closed throughout. This implements G2.007.3 as specced in `docs/operations/REVIEWER_VENUE_AUTHORITY.md` §4 (READ IT FIRST — it is on main and is your authority).

## Branch
`ce-350-reviewer-authority-envelope-wiring` off current `origin/main` (it now contains your merged #349). Fresh worktree.

## Allowed paths (HARD territory limit)
- `schemas/reviewer-authority-envelope.schema.yaml` (CREATE if absent — it is currently MISSING on main; author it to match the envelope contract the forge validator + §4 require)
- `validators/creator_engine_validator/lane_runtime.py`
- `.claude/hooks/ce-pretooluse.sh`
- `tools/egress-broker/ce_egress_self_review_broker.py` (the APPROVE path — receive + validate the envelope ref; builds on your #349 decouple)
- `validators/tests/integration/` + `validators/tests/unit/` — new/extended tests for this slice only
- `.ce/changelog/ce-350-reviewer-authority-envelope-wiring.md`, `.ce/pr-manifests/ce-350-reviewer-authority-envelope-wiring.md`
Do NOT touch cred_injection_proxy.py (consume its existing envelope-validation API), forge/ auto-merge modules, or anything else.

## Scope (per §4)
0. DISCOVER the envelope contract: grep the forge validator for the existing reviewer-authority-envelope validation entrypoint (the one #349's APPROVE chain calls) and the §4 fields — at minimum `mechanic: pr_review`, `pr_number`, `head_sha`, `emitting_role: reviewer`, `operating_mode`, `ratified_prompt_sha`. CREATE `schemas/reviewer-authority-envelope.schema.yaml` to match exactly what the validator expects (so an envelope that passes the schema also passes the runtime validator).
1. `lane_runtime.launch`: add `is_distinct_reviewer_venue` (role `reviewer` + lane_kind `review`); validate the envelope ref as schema-valid BEFORE any side effect (fail-closed `G3-REVIEWER-AUTHORITY-INVALID`; a ref on a non-reviewer venue → `G3-REVIEWER-VENUE-IDENTITY`); export it to the pane env as `CE_REVIEWER_AUTHORITY_REF` via tmux `-e` (NEVER printed); record the venue identity (role, lane_kind, reviewer_venue:true, reviewer_authority_ref) in the ignored governance sidecar. The canonical-root authoring Controller seat is NOT a reviewer venue.
2. `.claude/hooks/ce-pretooluse.sh`: when `CE_REVIEWER_AUTHORITY_REF` is set, forward `--reviewer-authority-ref <ref>` to the validator (injected as `ce.reviewer_authority_ref` BEFORE `hook_check.build_context()`). An event that already carries its own `ce` authority WINS (the flag is a fallback carrier, never an override).
3. broker APPROVE path: receive the envelope ref from the herdr pane env and validate it before APPROVE (on top of your #349 author≠approver + run-mode gates).
4. Integration test: a distinct reviewer lane with a valid envelope submits a verdict — COMMENT works; APPROVE only under a ratified run-mode (keep it COMMENT in the test unless you assert the strangeLoop-gated path explicitly).

## Evidence (stop-line)
- FULL local preflight GREEN one pass:
  `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-350-reviewer-authority-envelope-wiring`
- Carriers via carrier_gen (DASHED slug); PR-manifest AND PR body carry `- **Declared work class:** story`.
- SELF-PUSH as ce-dev-1, open the PR (mention ce-ops#350; cross-repo Closes is a no-op), report PR# + head SHA.
- HARD STOP-LINE: FAIL-CLOSED end to end (no env var ⇒ no flag ⇒ no authority ⇒ restricted mechanics stay denied; invalid/missing envelope ⇒ no authority). Envelope MINTING stays OUT-OF-BAND — do NOT change how envelopes are authored. Preserve author≠approver. APPROVE only under ratified run-mode (the arming stays RESERVED — do not enable it). Stay within allowed paths.
