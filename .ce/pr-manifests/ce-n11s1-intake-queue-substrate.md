# PR path manifest — N-11 slice 1 · intake queue claim lifecycle

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-n11s1-intake-queue-substrate` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=1cb3f7987d8f71f626c87f1a1506c0bdc0fc776457dcd1b376b038d65b5583de

```text
.ce/changelog/ce-n11s1-intake-queue-substrate.md
.ce/pr-manifests/ce-n11s1-intake-queue-substrate.md
docs/design/conveyor-intake-queue.md
validators/creator_engine_validator/conveyor_intake_queue.py
validators/tests/unit/test_conveyor_intake_queue.py
```
