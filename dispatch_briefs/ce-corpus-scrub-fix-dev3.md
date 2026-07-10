# BRIEF — dev-3 — corpus-scrub follow-up: fix the KNOWN_PENDING test (re-brief)

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Amend your EXISTING branch `ce-corpus-scrub-contributing`, drive back to READY-FOR-HARVEST GREEN.

## Why (your honest RED stop was correct)
Your validate-pr went RED on `validators/tests/unit/test_support_agent_p0.py::test_known_pending_doc_excluded_from_corpus`. That test asserts `docs/guide/contributing-to-ce.md` is on KNOWN_PENDING and therefore excluded from the corpus. Your lane correctly REMOVES that doc from KNOWN_PENDING and re-adds it to the allowlist — so the test's premise is now stale. You stopped rather than touch an out-of-scope file. Good. This re-brief widens your allowed paths to fix it.

## Allowed paths (ADD the test file)
Your prior paths PLUS: `validators/tests/unit/test_support_agent_p0.py`. Nothing else new.

## The fix
Update `test_known_pending_doc_excluded_from_corpus` so it still validates the KNOWN_PENDING-exclusion BEHAVIOR but no longer depends on `contributing-to-ce.md` being KNOWN_PENDING:
1. Re-point the test's fixture/assertion at a doc that IS STILL on KNOWN_PENDING (pick any remaining KNOWN_PENDING entry from `public_docs_confidentiality.py`) so the exclusion behavior stays covered.
2. If no KNOWN_PENDING entries remain, assert the exclusion using a synthetic/None-eligible fixture per the test's existing style.
3. ADD positive coverage of your scrub: assert `docs/guide/contributing-to-ce.md` is now INCLUDED/eligible (it left KNOWN_PENDING and is in the allowlist). Same for `docs/contracts/playbook-format.md` if it was similarly gated.
Keep the test's intent intact — do not just delete the assertion.

## Re-run + carriers
`rm -rf validators/*.egg-info validators/build` first. Then `TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-corpus-scrub-contributing` GREEN. Regen the two carriers if line counts shifted (write_carriers API, not hand-edit).

## On READY
Emit: validate-pr GREEN, the updated test name(s), the full changed-paths list, and `commit && echo <SHA>`. Do NOT push.
