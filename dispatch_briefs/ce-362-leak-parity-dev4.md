# BRIEF — dev-4 — ce-ops#362: sync support-agent runtime leak filter with the zero-leak eval rule table

Born-foreman, contained/no-egress (DO NOT push — controller harvests). Fresh branch `ce-362-leak-filter-parity` off CURRENT origin/main. **PRECONDITION:** this depends on `validators/creator_engine_validator/support_eval.py` being in main (from PR #657, merging now). FIRST `git fetch origin main` and confirm `support_eval.py` exists on origin/main; if not yet present, wait ~1–2 min and re-fetch until it is, THEN branch. Drive to READY-FOR-HARVEST GREEN; report HEAD SHA. Carrier slug == branch `ce-362-leak-filter-parity`.

## Context (EMBEDDED — you cannot read the ticket; this IS the scope)
The support agent's RUNTIME leak filter `support_runtime._leak_reason` enforces only `confidentiality.FORBIDDEN_PATTERNS + _INTERNAL_OUTPUT_PATTERNS` (~12 patterns). The zero-leak EVAL (`support_eval.py` `_DEFAULT_LEAK_RULES`) checks ~10 ADDITIONAL patterns (ce-ops bracket/spacing variants, controller-key, worktree paths, `playbooks/controller/` paths, dispatch-territory-map, overwatch/foreman, `CE_`/`PRIVATE_`/`INTERNAL_` secret env vars, tailnet, in-compose). **Consequence:** the eval is STRICTER than runtime → live `ce ask` could leak a marker the eval would flag. Fix = make runtime enforcement == eval enforcement via a SINGLE shared rule table.

## Deliverables
1. **Single shared rule table:** extract the full leak-rule set into ONE shared source of truth (a neutral module — e.g. extend `confidentiality.py` or a new `support_leak_rules.py` — do NOT make `support_runtime` import from the test/eval-oriented module in a way that creates an odd runtime→eval dependency; put the shared table somewhere both can cleanly import). BOTH `support_runtime._leak_reason` AND `support_eval._DEFAULT_LEAK_RULES` must consume this single table, so runtime and eval enforce the SAME patterns. Read both modules FIRST and preserve their existing public behavior/signatures.
2. **Extend the secret-env-var pattern** to also catch `_PAT` and `_CMD` suffixes (currently `(?:TOKEN|KEY|SECRET|HOST|URL)` — add `PAT|CMD`), so e.g. `CE_OVERWATCH_PAT` is caught.
3. **Empty-eval guard:** `support_eval.run_eval([])` currently returns `passed=True` — add a guard so an empty case list raises (or returns a non-passing/explicit-error verdict), so an empty eval can't be mistaken for a green release gate.
4. **Tests:** prove (a) runtime `_leak_reason` now flags the previously-eval-only patterns (e.g. a controller-key / dispatch-territory-map / `CE_OVERWATCH_PAT` string in an answer → runtime refuses), (b) eval still catches the same set (parity), (c) `_PAT`/`_CMD` suffix caught, (d) empty-eval guard fires. Update any existing tests that asserted the old narrower runtime behavior.

## Do NOT
- Do NOT touch `os_native_backend.py`, `install.sh`, `tools/egress-broker/*`, `deploy/systemd/*`, the OpenRouter adapter, or the Discord adapter (other lanes).
- Do NOT weaken any existing pattern or the cite-or-refuse / zero-leak behavior — this only ADDS/UNIFIES coverage.

## Gates
- FULL `ce validate-pr` GREEN in ONE pass (`TMPDIR=/var/tmp`; you may need `LD_LIBRARY_PATH=/var/tmp/ce-armA-env/lib` for libsodium on this DGX host). NOTE: a pre-existing `test_install_sh_uv_hash_mismatch...` failure is x86/aarch64 arch skew (baseline==head, zero NEW failures) — not your concern. Carriers via `carrier_gen.write_carriers(base=<merge-base>)` (rm build/egg-info first; VERIFY the `- **Declared work class:** <x>` line is present — API omits it; likely `story`) + changelog. Slug == branch. STOP at green; report SHA. Do NOT push.
