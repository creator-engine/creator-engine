# BRIEF — dev-3 — Support corpus widen: scrub contributing + playbook docs off KNOWN_PENDING (ce-ops#354 sibling)

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Drive to READY-FOR-HARVEST. Stay in allowed paths.

## Goal
Widen the `ce ask` support corpus by getting two product-lens-INTENT docs off the confidentiality KNOWN_PENDING ratchet and back into the support allowlist — this is exactly the CONTRIBUTOR surface the support agent needs to answer Nitzan. Two docs are on KNOWN_PENDING because they carry internal refs: scrub them to product-lens, drop them from the ratchet (strengthens the gate), and re-include them in the support corpus.

## Branch
`ce-corpus-scrub-contributing` off CURRENT origin/main (git fetch origin main first). Fresh worktree.

## Scope
1. SCRUB to product-lens (remove ALL internal refs — ce-ops#NNN, ce-ops-NNN, internal identities/topology/host-paths/IPs, internal codenames):
   - `docs/guide/contributing-to-ce.md`
   - `docs/contracts/playbook-format.md`
   Preserve the useful product content; abstract internal references to descriptive prose.
2. `validators/creator_engine_validator/public_docs_confidentiality.py`: REMOVE both entries from the `KNOWN_PENDING` allowlist (lines ~94 playbook-format.md, ~108 contributing-to-ce.md). Ratchet may only SHRINK — do NOT remove any FORBIDDEN_PATTERN or add anything. (After scrub, the docs pass the gate on their own, so they no longer need allowlisting.)
3. `validators/creator_engine_validator/support_corpus_allowlist.yaml`: RE-ADD both docs to the corpus (the file has NOTE comments at ~line 51 and ~line 60 saying "Re-add once it leaves KNOWN_PENDING" — uncomment/add the entries per those instructions so the eligibility intersection now includes them).

## Allowed paths (HARD limit)
- `docs/guide/contributing-to-ce.md`
- `docs/contracts/playbook-format.md`
- `validators/creator_engine_validator/public_docs_confidentiality.py` (KNOWN_PENDING shrink only)
- `validators/creator_engine_validator/support_corpus_allowlist.yaml` (re-add the two entries only)
- `.ce/changelog/ce-corpus-scrub-contributing.md`, `.ce/pr-manifests/ce-corpus-scrub-contributing.md`
Do NOT touch support_runtime.py, support_corpus.py, support_profile.py, or ce_cli.py (another seat is in support_runtime).

## Evidence (stop-line)
- FULL preflight GREEN: `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-corpus-scrub-contributing`
  (the hardened public_docs_confidentiality gate must PASS with both docs scrubbed + no longer allowlisted; the scan-support-corpus check must now ACCEPT both docs).
- Carriers via carrier_gen (dashed slug); single carrier; manifest `- **Declared work class:** story`.
- STOP and emit: `READY-FOR-HARVEST: branch ce-corpus-scrub-contributing, SHA <sha>, merge-base <mb>, changed paths: <list>, validate-pr GREEN.`
- No push/approve/merge. Both docs must be genuinely product-lens clean (no residual internal refs). Stay in allowed paths.
