# PR path manifest - ce195-launch-argv-python-m

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce195-launch-argv-python-m
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Base:
`e963eaf` (`origin/main` at branch handoff).

- **Declared work class:** tiny

Scope:
ce-ops#195 pickup lane launch argv fix. The slice removes the bare `ce`
executable dependency from the gated launch path by invoking the lane CLI as a
Python module through the active interpreter.

Per-file purpose:
- **`.ce/changelog/ce195-launch-argv-python-m.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce195-launch-argv-python-m.md`** *(A)* - this closed path-set carrier.
- **`validators/creator_engine_validator/pickup.py`** *(M)* - `build_lane_argv` interpreter/module launch prefix.
- **`validators/tests/unit/test_pickup.py`** *(M)* - offline argv regression coverage.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=65e317851c022fc2bfa494db9434eb980e62bb9ec8641eda4151d34e23285a92

```text
.ce/changelog/ce195-launch-argv-python-m.md
.ce/pr-manifests/ce195-launch-argv-python-m.md
validators/creator_engine_validator/pickup.py
validators/tests/unit/test_pickup.py
```
