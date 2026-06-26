---
slug: ce258-stranded-pr-sweep
date: 2026-06-26
kind: feature
scope: conveyor stranded PR sweep
issue: ce-ops#258
---

# PR path manifest - ce258-stranded-pr-sweep

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce258-stranded-pr-sweep --require-carrier
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

- **Declared work class:** story

Scope:
ce-ops#258 adds a conveyor stranded-PR sweep for approved, required-check-green,
clean creator-engine PRs that are absent from `repository.mergeQueue.entries`
for `main`, then enqueues eligible PRs through `gh pr merge <n> --auto`.

Per-file purpose:
- **`.ce/changelog/ce258-stranded-pr-sweep.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce258-stranded-pr-sweep.md`** *(A)* - this closed path-set
  carrier.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - exposes
  `ce conveyor sweep` for cron invocation.
- **`validators/creator_engine_validator/forge/integrator_belt.py`** *(M)* -
  implements GraphQL discovery, merge-queue membership checks, gate evaluation,
  approval reverify, enqueue, structured action logging, and the v3 module CLI
  bridge target.
- **`validators/tests/unit/test_stranded_sweep.py`** *(A)* - covers eligible
  enqueue, already queued skip, dirty skip, and failing merge-group/check skip
  with fake `gh` seams only.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=67b39cabf3a663e3a378e0ad7660a7ad6b79519212e00fa10c4cbdc70fd82b70

```text
.ce/changelog/ce258-stranded-pr-sweep.md
.ce/pr-manifests/ce258-stranded-pr-sweep.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/forge/integrator_belt.py
validators/tests/unit/test_stranded_sweep.py
```
