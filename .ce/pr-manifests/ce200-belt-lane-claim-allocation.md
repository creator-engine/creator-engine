# PR path manifest - ce200-belt-lane-claim-allocation

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce200-belt-lane-claim-allocation
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`2afc4801` (`origin/main` at branch handoff).

- **Declared work class:** story

Scope:
ce-ops#200 belt lane-claim allocation fix. The slice makes the pickup S3 launch
path allocate the Active-Work lane claim (lease + claim + event) BEFORE invoking
`ce lane launch`, so the autonomous belt `--enable-launch` path no longer refuses
with `G3-CLAIM-MISSING`.

Per-file purpose:
- **`.ce/changelog/ce200-belt-lane-claim-allocation.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce200-belt-lane-claim-allocation.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/pco_allocator.py`** *(M)* - `allocate_in_place` (claim-only, no git-worktree-add) primitive.
- **`validators/creator_engine_validator/pickup.py`** *(M)* - `launch_lane` allocates the lease+claim+event before the spawn.
- **`validators/tests/unit/test_pickup.py`** *(M)* - end-to-end allocate-before-spawn + idempotency coverage.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=4986ccc12953a71ce33223b06351a8a6d2140def0b25896144e1c16b4371b0ed

```text
.ce/changelog/ce200-belt-lane-claim-allocation.md
.ce/pr-manifests/ce200-belt-lane-claim-allocation.md
validators/creator_engine_validator/pco_allocator.py
validators/creator_engine_validator/pickup.py
validators/tests/unit/test_pickup.py
```
