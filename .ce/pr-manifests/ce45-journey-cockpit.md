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
verified unchanged). No mode switcher / default-change / demotion (deferred). L2/L3
hard law honored: all computation in `runner/cockpit_readmodel.py` (`snapshot["journey"]`);
`v3_cockpit.py` view-only. No new schema/runtime-module/CLI/check; read-only surface.

**Manifest amendment (Operator-approved, option A, 2026-06-15):** the gate's 6-path
manifest omitted the bundled wheel; editing `cockpit_readmodel.py`/`v3_cockpit.py`
(both shipped in the app wheel) requires regenerating `validators/wheelhouse/<app-wheel>`
+ re-pinning `validators/wheelhouse/SHA256SUMS` for the packaging contract
(`verify_wheel_matches_source`, wheelhouse-only). +2 paths → 10. WHEELHOUSE-ONLY: the
`docs/downloads/0.2.0` published mirror is **out of scope** (handled by the release
seat under the frozen-mirror model; no `docs/llms-install.md` re-sign here). Untouched
per standing constraint: `onboard_apply.py`, `v3_cli.py` apply gate (ce-ops#85, merged), `pco_allocator.py`.

Base:
fresh `origin/main` (post ce-ops#82 #228 and ce-ops#85 #229 merges).

Per-file purpose (the closed path-set — 10 paths = the gate's 6 impl files + 2 governance carriers + 2 wheelhouse artifacts):
- **`.ce/changelog/ce45-journey-cockpit.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/ce45-journey-cockpit.md`** *(A)* — this carrier (self-inclusive).
- **`docs/architecture/cockpit.md`** *(M)* — journey L2/L3 architecture note.
- **`validators/creator_engine_validator/runner/cockpit_readmodel.py`** *(M)* — L2:
  pure `_fold_journey` projection (`snapshot["journey"]`).
- **`validators/creator_engine_validator/v3_cockpit.py`** *(M)* — L3: journey screen
  (`j` binding) + detail modal; binds snapshot only.
- **`validators/tests/unit/test_cockpit_journey.py`** *(A)* — L2 journey tests.
- **`validators/tests/unit/test_v3_cockpit.py`** *(M)* — extends the L3 source-guard.
- **`validators/tests/unit/test_v3_cockpit_journey.py`** *(A)* — L3 journey tests.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned app-wheel line for the rebuilt wheel (deps unchanged).
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* —
  rebuilt from this branch's source so the wheel↔source packaging contract holds.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=4e79a81fe2c8099c7c54ab015d989ec3dcb506a8276eccac6986ee8e1b1d0fd5

```text
.ce/changelog/ce45-journey-cockpit.md
.ce/pr-manifests/ce45-journey-cockpit.md
docs/architecture/cockpit.md
validators/creator_engine_validator/runner/cockpit_readmodel.py
validators/creator_engine_validator/v3_cockpit.py
validators/tests/unit/test_cockpit_journey.py
validators/tests/unit/test_v3_cockpit.py
validators/tests/unit/test_v3_cockpit_journey.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
