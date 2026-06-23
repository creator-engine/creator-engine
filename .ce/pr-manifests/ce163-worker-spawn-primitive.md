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
- **`validators/creator_engine_validator/worker_spawn.py`** *(A)* — pure
  worker-spawn planning, env scrub, artifact, and injectable launch seam.
- **`validators/tests/unit/test_ce_worker_cli.py`** *(M)* — CLI tests for
  dry-run/no-side-effect and injected live spawn token scrub.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* — v1 taxonomy
  count/classification updates.
- **`validators/tests/unit/test_worker_spawn.py`** *(A)* — runtime unit tests
  for roles, worktree/depth validation, value-free records, env scrub, dry-run,
  and injected launcher behavior.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=5a5ff26ea404f5d52ebf5235ef92f4879c5a3037f32cbfb02535f654c485f8e7

```text
.ce/changelog/ce163-worker-spawn-primitive.md
.ce/pr-manifests/ce163-worker-spawn-primitive.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/worker_spawn.py
validators/tests/unit/test_ce_worker_cli.py
validators/tests/unit/test_version_boundary.py
validators/tests/unit/test_worker_spawn.py
```
