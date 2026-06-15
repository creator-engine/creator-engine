# PR path manifest — ce98-pco-release-collision · pco-release claim_released event filename collision

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce98-pco-release-collision

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below (the carrier
lists itself); the repo-wide fidelity scan requires the declared count and SHA256 to match the fenced block.

Base:
`8adc993` (`main` = #231, the 0.2.0 download-mirror republish to match the post-#85 wheel).

The change (collision-proof pco-release event ids):
`creator-engine#98` — two `pco-release` calls in the same second wrote the same
`events/YYYY/MM/DD/claim-released-YYYYMMDDhhmmss.yaml` (the id had second resolution and no
controller/lane/entropy component), so the second `_atomic_write` overwrote the first and a
`claim_released` event was silently lost — schema and `active_work_ledger_conflicts` checks still PASSED.
The fix adds `_event_id(prefix, ts_compact)`, appending an 8-hex random suffix (the module's existing
`uuid.uuid4().hex[:8]` nonce idiom) so same-second events never collide, within the schema's 64-char
`event_id` bound. Applied at both emission sites — `release()` (`claim_released`) and the parallel
`allocate()` (`claim_created`), which share the identical latent collision.

Per-file purpose (the closed path-set — 6 paths):
- **`.ce/changelog/ce98-pco-release-collision.md`** *(A)* — per-PR changelog fragment for the fix.
- **`.ce/pr-manifests/ce98-pco-release-collision.md`** *(A)* — this carrier (self-inclusive).
- **`validators/creator_engine_validator/pco_allocator.py`** *(M)* — `_event_ts_compact()` seam +
  `_event_id()` helper (8-hex entropy suffix); both `release()` and `allocate()` event ids routed through it.
- **`validators/tests/unit/test_pco_allocator.py`** *(M)* — regression tests: two same-second releases (and
  two same-second allocates) keep BOTH event files, with distinct event ids matching the schema pattern.
- **`validators/wheelhouse/SHA256SUMS`** *(M)* — re-pinned the app-wheel line for the rebuilt wheel (the
  6 dependency-wheel lines are byte-unchanged).
- **`validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl`** *(M)* — rebuilt 0.2.0 app
  wheel (source parity: `packaging_runtime.verify_wheel_matches_source` requires the committed wheel's
  `.py` bytes to equal source). The standard per-PR wheel-rebuild tax for any source change; `_version.py`
  is unchanged (its baked `BUILD_GIT_SHA` stays a valid HEAD-ancestor, so no re-bake is required).

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=2ab8186a57747a1fcb86c7ad43ce4e7c86efe6f27e5a53f88fd3d367b2068cca

```text
.ce/changelog/ce98-pco-release-collision.md
.ce/pr-manifests/ce98-pco-release-collision.md
validators/creator_engine_validator/pco_allocator.py
validators/tests/unit/test_pco_allocator.py
validators/wheelhouse/SHA256SUMS
validators/wheelhouse/creator_engine_validator-0.2.0-py3-none-any.whl
```
