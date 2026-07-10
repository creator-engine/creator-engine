# CORRECTION 1 — dev-1 — 2026-07-08 — unblock ce-iac-singleton-redeploy (U1 scope extension)

Controller ruling on your BLOCKED line: the runbook stays at
`docs/operations/SINGLETON_DAEMON_REDEPLOY_RUNBOOK.md`. The failing test
(`test_public_docs_internal_trees_have_only_known_exceptions`) is the deliberate
exception ratchet from ce-ops#283 — net-new docs/operations files must be added
consciously to the allowlist. That update is now IN SCOPE for U1.

## Scope extension (U1 allowed paths += exactly one file, one change)

- `validators/creator_engine_validator/public_docs_confidentiality.py` — add EXACTLY
  ONE entry, the string `"docs/operations/SINGLETON_DAEMON_REDEPLOY_RUNBOOK.md"`, to
  the `KNOWN_OPERATIONS_EXCEPTIONS` frozenset (keep ordering/formatting conventions of
  the existing entries). No other edit to that file. Do not touch
  `KNOWN_DELIVERY_EXCEPTIONS`, `ALLOWED_OFFENSES`, or any other allowlist.

## Conditions

1. Before adding the exception, re-verify the runbook content itself passes the
   OTHER confidentiality tests (no internal host names, user names, tailnet IPs,
   container names, ce-ops# refs — public-docs product lens). The exception ratchet
   only covers tree placement, not content offenses.
2. Update the carrier (`.ce/pr-manifests/ce-iac-singleton-redeploy.md`) to include the
   newly-changed validator file; recompute AUTHORIZED_PATHS_COUNT / AUTHORIZED_PATHS_SHA256.
3. Mention the deliberate exception in the PR body (one line: what was added to the
   ratchet and why).
4. Then: FULL `ce validate-pr` green → push → PR → `READY ce-iac-singleton-redeploy <sha> PR#<n>`
   as per the original brief, and proceed to U2.

All other terms of BRIEF_dev1_iac_ring1_20260708.md unchanged, including the stop line.
