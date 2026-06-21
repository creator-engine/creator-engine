# PR path manifest - ce178-brain-bootstrap

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce178-brain-bootstrap
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Scope:
ce-ops#178 Knowledge-SSOT born-knowing bootstrap on top of the ce-ops#167
brain assertion ledger and the ce-ops#163 seat-class spine. This adds the
deterministic bootstrap mechanism only: no datastore, MCP, recall/vector
surface, or MEMORY migration.

The changes:
- Adds a pure, read-only `brain_bootstrap` projection that validates the
  assertion ledger, fails closed on invalid/missing state, and returns a
  deterministic JSON payload for controller bootstrap injection.
- Wires `ce brain bootstrap` so the injection payload can be reproduced
  directly.
- Wires the bootstrap payload into `ce launch` and `ce lane launch` before spawn
  side effects, exporting only a payload file ref + SHA through the existing
  seat-sentinel wrapper.
- Resolves seat class through the existing #163 `seat_class` spine, so absent
  or unknown values fail closed to `foreman`.
- Adds offline unit and CLI coverage for deterministic load, tamper refusal,
  scope filtering, corrected-assertion reflection, launch refusal/injection,
  and seat-class defaulting.

Per-file purpose (closed path-set - 20 paths):
- **`.ce/changelog/ce178-brain-bootstrap.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce178-brain-bootstrap.md`** *(A)* - this carrier.
- **`validators/creator_engine_validator/_version.py`** *(M)* - regenerated
  build identity after rebasing onto current main.
- **`validators/creator_engine_validator/brain_bootstrap.py`** *(A)* -
  deterministic born-knowing bootstrap projection.
- **`validators/creator_engine_validator/ce_cli.py`** *(M)* - wires
  `ce brain bootstrap`.
- **`validators/creator_engine_validator/lane_runtime.py`** *(M)* - requires and
  injects the bootstrap payload before governed lane spawn.
- **`validators/creator_engine_validator/launch_runtime.py`** *(M)* - requires
  and injects the bootstrap payload before controller spawn.
- **`validators/creator_engine_validator/seat_sentinel.py`** *(M)* - adds
  deterministic wrapper env exports for payload refs.
- **`validators/tests/integration/test_ce_brain_cli.py`** *(M)* - CLI
  bootstrap coverage.
- **`validators/tests/integration/test_claude_launch_refusal.py`** *(M)* -
  preserves Ring-0 refusal coverage with a valid bootstrap ledger.
- **`validators/tests/integration/test_lane_launch_tmux.py`** *(M)* - lane
  tmux integration coverage with valid bootstrap state.
- **`validators/tests/unit/test_brain_bootstrap.py`** *(A)* - runtime unit
  coverage.
- **`validators/tests/unit/test_ce_lane_cli.py`** *(M)* - lane CLI coverage
  with valid bootstrap state.
- **`validators/tests/unit/test_ce_launch_cli.py`** *(M)* - launch CLI coverage
  with valid bootstrap state.
- **`validators/tests/unit/test_lane_runtime.py`** *(M)* - lane refusal and
  injection regressions.
- **`validators/tests/unit/test_lane_runtime_resource_bound.py`** *(M)* -
  resource-bound lane coverage with valid bootstrap state.
- **`validators/tests/unit/test_lane_runtime_reviewer_venue.py`** *(M)* -
  reviewer-venue lane coverage with valid bootstrap state.
- **`validators/tests/unit/test_launch_runtime.py`** *(M)* - controller refusal
  and injection regressions.
- **`validators/tests/unit/test_launch_runtime_resource_bound.py`** *(M)* -
  resource-bound launch coverage with valid bootstrap state.
- **`validators/tests/unit/test_seat_sentinel.py`** *(M)* - wrapper env-export
  regression coverage.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=20

AUTHORIZED_PATHS_SHA256=5945aa1d6f2d2cf1e18f1707011d0a70602cf7b59fadd05e7249a2bfc9da9f5d

```text
.ce/changelog/ce178-brain-bootstrap.md
.ce/pr-manifests/ce178-brain-bootstrap.md
validators/creator_engine_validator/_version.py
validators/creator_engine_validator/brain_bootstrap.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/lane_runtime.py
validators/creator_engine_validator/launch_runtime.py
validators/creator_engine_validator/seat_sentinel.py
validators/tests/integration/test_ce_brain_cli.py
validators/tests/integration/test_claude_launch_refusal.py
validators/tests/integration/test_lane_launch_tmux.py
validators/tests/unit/test_brain_bootstrap.py
validators/tests/unit/test_ce_lane_cli.py
validators/tests/unit/test_ce_launch_cli.py
validators/tests/unit/test_lane_runtime.py
validators/tests/unit/test_lane_runtime_resource_bound.py
validators/tests/unit/test_lane_runtime_reviewer_venue.py
validators/tests/unit/test_launch_runtime.py
validators/tests/unit/test_launch_runtime_resource_bound.py
validators/tests/unit/test_seat_sentinel.py
```
