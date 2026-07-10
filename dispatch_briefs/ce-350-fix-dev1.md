# BRIEF — dev-1 — #350 (PR #625) hardening fix (ce-ops#350)

Your #350 PR (#625, branch ce-350-reviewer-authority-envelope-wiring) is substantively GOOD and CI is GREEN. Independent review CONFIRMED: the broker fail-closed gates are intact (APPROVE refused in dev/solo/team/unset; author≠approver before mint; envelope double-validated; inline-envelope-wins precedence correct). It also raised two "blocking" findings that are FALSE (stale-checkout artifacts) — IGNORE these, they need NO action: (a) "validate_approve_authority absent from main" — it IS on main via the merged ce-ops#349; (b) "missing pr-manifest carrier" — it IS present and CI's carrier gate passed.

Apply TWO real hardening fixes on the SAME branch (ce-350-reviewer-authority-envelope-wiring), then re-validate + re-push.

## Fix 1 (MEDIUM security — file-read oracle)
In `tools/egress-broker/ce_egress_self_review_broker.py`, the payload-ref path (~lines 393-438: the loop over `reviewer_authority_ref`/`reviewer_authority_envelope_ref` from the socket payload → `_load_reviewer_authority_ref`) loads an arbitrary path from the HOST filesystem with no repo-root restriction. A configured seat could pass an absolute path and probe file existence / read arbitrary file content into the broker.
- Restrict PAYLOAD-provided refs to REPO-ROOT-ANCHORED relative paths only: reject absolute paths and any path that escapes the repo root via `..` traversal (resolve and confirm it's within repo root) → on violation, refuse (no file read), same fail-closed style as the other broker refusals.
- The TRUSTED env-var carrier path (`CE_REVIEWER_AUTHORITY_REF`, host-injected) MAY keep absolute-path loading — only the untrusted socket-payload path needs the restriction.
- Add a unit test in `test_egress_self_review_broker.py`: a payload ref with an absolute path AND one with a `../` escape → both refused, no host file opened.

## Fix 2 (confidentiality — internal identity in public repo)
In `validators/tests/integration/test_claude_hook_pack_pretooluse.py` (~line 188), the fixture uses `"actor": "ubuntuaws745-cmyk"` — a real internal CE reviewer GitHub login. Replace it with a generic fixture handle (e.g. `"example-reviewer"`). If the same internal login appears elsewhere in this PR's changed test files, replace those too. (Public-repo permanent history — no internal identities.)

## Stay in scope
Touch only: `tools/egress-broker/ce_egress_self_review_broker.py`, `validators/tests/unit/test_egress_self_review_broker.py`, `validators/tests/integration/test_claude_hook_pack_pretooluse.py`, and regenerate the carrier if the diff shifts work-class. Do NOT add the unrelated cred_injection_proxy or lane_runtime files — those legs already exist on main.

## Evidence
- FULL preflight GREEN one pass: `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-350-reviewer-authority-envelope-wiring`
- Re-push the branch as ce-dev-1 (updates PR #625). Report the new head SHA + validate result.
- Preserve all existing fail-closed gates; no arming; APPROVE stays reserved/ratified-run-mode-only. Do NOT approve/merge.
