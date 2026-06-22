# PR path manifest - ce203-lease-id-length

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce203-lease-id-length
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`9020a6aa` (`origin/main` at branch handoff).

- **Declared work class:** bug

Scope:
ce-ops#203 lease_id length fix. The live canary post-#200 reached
`pco_allocator.allocate_in_place()` but the lease write was REFUSED by PCO-020
schema validation: pickup's long lane id (`pickup-<repo>-<n>-<run>`, ~48 chars)
pushed the naive `lease-<lane_id>-<14-digit ts>` derivation to ~69 chars >
the 64-char `lease_id` bound `^[a-z0-9][a-z0-9-]{2,63}$`. Both `allocate()` and
`allocate_in_place()` now mint a fixed-width, lane-length-independent
`lease-<sha256(lane_id-ts)[:32]>` (38 chars) so a clean canary reaches
LAUNCHED_STATE.

Per-file purpose:
- **`.ce/changelog/ce203-lease-id-length.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce203-lease-id-length.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/pco_allocator.py`** *(M)* - new `_mint_lease_id` helper; both `allocate` and `allocate_in_place` use it.
- **`validators/tests/unit/test_pickup.py`** *(M)* - production-length lane regression tests for both allocate paths (lease/claim/event schema-validated).

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=0e43a13a67c676f9d807e8937b72219e73ecfe1381f99bbb4d98d3df35c6e710

```text
.ce/changelog/ce203-lease-id-length.md
.ce/pr-manifests/ce203-lease-id-length.md
validators/creator_engine_validator/pco_allocator.py
validators/tests/unit/test_pickup.py
```
