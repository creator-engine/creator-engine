---
slug: ce-supportagent-eval-corpus-expand-harvest
date: 2026-06-30
kind: added
scope: support agent eval
issue: ce-ops#360
---

**Harvest: expand support-agent zero-leak eval corpus.**

- **Declared work class:** story
- Harvested dev-3 seat branch `ce-supportagent-eval-corpus-expand` (SHA e52cc4f6) onto post-#664 main.
- Reconciliation: all 29 corpus cases (12 answered-with-citation + 17 refused) are IDENTICAL between the seat's commit and #664; no duplicates, no dropped cases.
- Test semantics: seat encoded pre-#662 `hard_fail`/`leak_violations` assertions in `test_expanded_probe_markers_hard_fail_with_planted_leaks`; #664 already corrected this to `test_expanded_probe_markers_blocked_by_runtime_filter` with post-#662 semantics (runtime-filter intercepts before eval detect_leaks). Current main version is kept; seat's pre-#662 variant is NOT applied to avoid regression.
- Carrier-only diff: core content (JSON, test, original changelog/manifest) already on main from #664; this harvest PR carries the harvest-slug carriers as the audit trail.
