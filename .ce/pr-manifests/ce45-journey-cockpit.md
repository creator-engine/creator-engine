# PR path manifest — ce-ops#45 (CEO-mode journey cockpit, ratified MINIMUM)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce45-journey-cockpit
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below (the carrier lists itself); the fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified scope:
**`designs/CE45_CEOMODE_MINIMUM_GATE_SPEC_RATIFIED_20260613.md`** (ce-ops#45) — the
CEO-mode journey MINIMUM only: one-screen Frame→Ship arc + plain-language
"what-needs-me" feed + click-to-detail. Re-grounded on this HEAD (all §10 triggers
PASS; the gate's own 6-path closed manifest hash `caaa16ad45b537e7ce063908b1dbe52d81d155fed6f6615378be845c3068e68a`
verified unchanged). No mode switcher / default-change / demotion (deferred to a
separate gate). L2/L3 hard law honored: all computation in `runner/cockpit_readmodel.py`
(`snapshot["journey"]`); `v3_cockpit.py` view-only. No new schema/runtime-module/CLI/
check; read-only surface. Untouched per standing constraint: `onboard_apply.py`,
`v3_cli.py` apply gate (ce-ops#85, merged separately), `pco_allocator.py`.

Base:
fresh `origin/main` (post ce-ops#82 #228 and ce-ops#85 merges).

Per-file purpose (the closed path-set — 8 paths = the gate's 6-path manifest + 2 governance carriers):
- **`.ce/changelog/ce45-journey-cockpit.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/ce45-journey-cockpit.md`** *(A)* — this carrier (self-inclusive).
- **`docs/architecture/cockpit.md`** *(M)* — journey L2/L3 architecture note.
- **`validators/creator_engine_validator/runner/cockpit_readmodel.py`** *(M)* — L2:
  pure `_fold_journey` projection (`snapshot["journey"]`: arc, honest where-am-I,
  scopes, plain-language needs-attention, deterministic detail templates, counters).
- **`validators/creator_engine_validator/v3_cockpit.py`** *(M)* — L3: dedicated
  journey screen (`j` binding) + detail modal; binds snapshot only, computes nothing.
- **`validators/tests/unit/test_cockpit_journey.py`** *(A)* — L2 journey tests.
- **`validators/tests/unit/test_v3_cockpit.py`** *(M)* — extends the L3 source-guard.
- **`validators/tests/unit/test_v3_cockpit_journey.py`** *(A)* — L3 journey tests.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=a92aaa8cc340686ea3f1bea6c105ba728f2669719c230417ee42e2a0ba49e213

```text
.ce/changelog/ce45-journey-cockpit.md
.ce/pr-manifests/ce45-journey-cockpit.md
docs/architecture/cockpit.md
validators/creator_engine_validator/runner/cockpit_readmodel.py
validators/creator_engine_validator/v3_cockpit.py
validators/tests/unit/test_cockpit_journey.py
validators/tests/unit/test_v3_cockpit.py
validators/tests/unit/test_v3_cockpit_journey.py
```
