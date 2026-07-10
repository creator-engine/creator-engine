# AMENDMENT: ce-391-triage-advisory-text (supersedes Ticket B scope in ce-n6-batch-dev3-BRIEF.md)

Your path-fence stop was CORRECT — the brief mislocated `_has_milestone` (it lives in
validators/creator_engine_validator/forge_triage.py, not ce_cli.py). Scope change:

1. PROCEED NOW with the main fix ONLY: `_pickup_triage` text-mode advisory output in
   validators/creator_engine_validator/ce_cli.py (~3565-3578) — wire result.commissioned_unscheduled
   + count into the plain-text branch, matching --json's information. Tests in the existing
   _pickup_triage text-mode test file(s). Allowed paths: ce_cli.py (that function only) + its
   test file(s) + changelog + carrier.
2. DROP the `_has_milestone` minor entirely from this branch — forge_triage.py is territory-locked
   by another in-flight PR. It will be re-dispatched separately later. Do not touch forge_triage.py.
3. Everything else from the original Ticket B stands: branch ce-391-triage-advisory-text off
   origin/main, work class XS, changelog + carrier via carrier_gen API, full ce validate-pr GREEN
   (ssh-keygen known-exception rule applies), commit && echo SHA, then exactly:
   `READY-FOR-HARVEST ce-391-triage-advisory-text <full-sha>`
Stop line unchanged: no pushes, no PRs, no brain ledger, no config.
