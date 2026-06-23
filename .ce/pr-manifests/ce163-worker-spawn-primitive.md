# PR path manifest — ce-ops#163 (worker-spawn primitive REQ-2)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce163-worker-spawn-primitive
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below (the carrier lists itself); the fidelity scan requires the declared count
and SHA256 to match the fenced block.

Ratified scope:
ce-ops#163 REQ-2 foundation only: a first-class harness-agnostic CE worker-spawn
primitive with typed worker roles, explicit worker worktree isolation,
credential-scrubbed child environment, value-free worker artifacts, and a thin
injectable launcher seam over the retained v1 launch surface.

Explicitly excluded: born-a-foreman injection (REQ-1), hard-deny enforcement
(REQ-3), reviewer-author gates, controller merge gates, and any change to the
existing worker container allocation lifecycle.

Per-file purpose:
- **`.ce/changelog/ce163-worker-spawn-primitive.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/ce163-worker-spawn-primitive.md`** *(A)* — this carrier
  (self-inclusive).
- **`validators/creator_engine_validator/_versions.py`** *(M)* — classifies
  `worker_spawn` as v1 runtime and updates the boundary count.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* — wires
  `ce worker spawn` into the existing worker subcommand group.
- **`validators/creator_engine_validator/launch_runtime.py`** *(M)* — pins
  worker-spawn cwd/env at the tmux adapter boundary and fails closed when the
  cwd cannot be verified.
- **`validators/creator_engine_validator/worker_spawn.py`** *(A)* — pure
  worker-spawn planning, env scrub, artifact, and injectable launch seam.
- **`validators/tests/unit/test_ce_worker_cli.py`** *(M)* — CLI tests for
  dry-run/no-side-effect and injected live spawn token scrub.
- **`validators/tests/unit/test_launch_runtime.py`** *(M)* — adapter-boundary
  regression coverage for worker-spawn cwd/env pinning.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* — v1 taxonomy
  count/classification updates.
- **`validators/tests/unit/test_worker_spawn.py`** *(A)* — runtime unit tests
  for roles, worktree/depth validation, value-free records, env scrub, dry-run,
  and injected launcher behavior.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=baa04d1cfa3cb14ba8514bdfaaa997678a2f0a2712b105b25877982da6870171

```text
.ce/changelog/ce163-worker-spawn-primitive.md
.ce/pr-manifests/ce163-worker-spawn-primitive.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/launch_runtime.py
validators/creator_engine_validator/worker_spawn.py
validators/tests/unit/test_ce_worker_cli.py
validators/tests/unit/test_launch_runtime.py
validators/tests/unit/test_version_boundary.py
validators/tests/unit/test_worker_spawn.py
```
