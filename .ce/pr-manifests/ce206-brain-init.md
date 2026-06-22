# PR path manifest - ce206-brain-init

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce206-brain-init
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#206 — add an idempotent `ce brain init` CLI command that bootstraps a
valid genesis brain assertion ledger so a fresh CE workspace passes the
`lane launch` `G3-BRAIN-BOOTSTRAP-REFUSED` gate with no hand-run step.

Base:
`b344549800dbadf1b550262c2b35b82c599172be` (`origin/main` at branch creation).

Per-file purpose (closed path-set - 5 paths):
- **`.ce/changelog/ce206-brain-init.md`** *(A)* - changelog fragment (type: feature).
- **`.ce/pr-manifests/ce206-brain-init.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - add the `ce brain init` subparser, `_brain_init` handler, and `_BRAIN_DISPATCH` wiring; document the command in the module docstring.
- **`validators/tests/integration/test_ce_brain_init_lane_gate.py`** *(A)* - integration: a workspace bootstrapped via `ce brain init` passes the lane-launch brain gate end-to-end through the real CLI.
- **`validators/tests/unit/test_ce_brain_init.py`** *(A)* - unit coverage: fresh-init verifies ok, idempotent byte-preserving no-op, fail-closed refusal on a corrupt/non-mapping ledger, and the lane-launch brain preflight passing post-init.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=49a3e0f842611388dbf6857c39b75d48b3d40b7d8d243b8c9f3d163ba41a47ef

```text
.ce/changelog/ce206-brain-init.md
.ce/pr-manifests/ce206-brain-init.md
validators/creator_engine_validator/ce_cli.py
validators/tests/integration/test_ce_brain_init_lane_gate.py
validators/tests/unit/test_ce_brain_init.py
```
