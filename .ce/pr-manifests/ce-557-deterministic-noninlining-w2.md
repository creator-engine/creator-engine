# PR path manifest - deterministic controller no-inlining

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-557-deterministic-noninlining-w2`
and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below; this carrier lists itself.

- **Branch:** `ce-557-deterministic-noninlining-w2`
- **Base:** `be0e8cbe66acea9998553f2cec59144397029694`
- **Predecessor commit:** `1e6764ee6f6f7585b25fca35b721a63d45d14cbc`
- **Declared work class:** epic
- **Authority boundary:** this follow-up is limited to the blocking PR #1014
  execution-plane classifier correction, focused hook-check regressions, and
  carrier wording for that bounded rework; no authority-bound systems, waivers,
  PR approval, merge, push, deploy, credential movement, service mutation, or
  canonical path-set expansion are authorized by this repair.
- **Evidence:** final-review rework focused tests reported
  `test_hook_check.py` plus `test_runner_ring1_tool_guard.py` as `264 passed`;
  stale integration follow-up focused tests reported the affected
  `test_hook_check_cli.py` nodes plus `test_hook_check.py` as `233 passed`;
  PR #1014 gate rework focused tests reported
  `validators/tests/unit/test_hook_check.py` plus
  `validators/tests/integration/test_hook_check_cli.py` as `272 passed`;
  this branch is validated by one full governed validator run after the gate
  rework commit.

Per-file purpose:

- **`.ce/changelog/ce-557-deterministic-noninlining-w2.md`** *(A)* - changelog
  fragment for the governed epic and carrier repair evidence.
- **`.ce/pr-manifests/ce-557-deterministic-noninlining-w2.md`** *(A)* - this
  closed path-set carrier.
- **`docs/operations/CONTROLLER_BOUNDARY_POLICY.md`** *(M)* - documents the
  deterministic controller no-inlining refusal boundary, worker dispatch hint,
  and fail-closed launch-pinned identity requirement.
- **`validators/creator_engine_validator/hook_check.py`** *(M)* - classifies and
  refuses controller execution-plane primitives unless a complete launcher-pinned
  governed implementer worker context validates against the current worker
  record; parses shell composition, env/alias first-token indirection,
  execution-shaped opaque fallthrough, and archive operation grammar
  fail-closed while preserving read-only list/test captures.
- **`validators/creator_engine_validator/runner/ring1_tool_guard.py`** *(M)* -
  guards the concrete Ring-1 command entry points, scrubs inherited
  `CE_WORKER_*`, and propagates authenticated worker context from
  launcher-controlled configuration.
- **`validators/creator_engine_validator/seat_class.py`** *(M)* - expands the
  foreman delegation denial reason with the governed implementer dispatch hint.
- **`validators/tests/unit/test_hook_check.py`** *(M)* - covers hard denial
  across missing/ungoverned context, launch-pinned worker allowance,
  replay/mismatch/stale/malformed fail-closed behavior, parsed command
  primitive classification, env/alias/unrecognized first-token evasion,
  archive read-vs-extract/mutate seams, safe read-only output capture, and
  closed spawn capability identifiers.
- **`validators/tests/integration/test_hook_check_cli.py`** *(M)* - corrects
  the CLI integration seam so partial inherited worker identity stays denied
  while complete launcher-owned worker context remains allowed, and pins the
  CLI output-capture boundary for archive read versus opaque execution-plane
  substitution.
- **`validators/tests/unit/test_runner_ring1_tool_guard.py`** *(M)* - covers
  Ring-1 shim refusal for controller execution-plane primitive commands,
  default governed entry points, hostile inherited env scrubbing, and
  worker-context propagation.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=9

AUTHORIZED_PATHS_SHA256=3764d9b418d824ac2ad9a83e56a7dda90f0b45c3b03c241979ae0e17d67706ff

```text
.ce/changelog/ce-557-deterministic-noninlining-w2.md
.ce/pr-manifests/ce-557-deterministic-noninlining-w2.md
docs/operations/CONTROLLER_BOUNDARY_POLICY.md
validators/creator_engine_validator/hook_check.py
validators/creator_engine_validator/runner/ring1_tool_guard.py
validators/creator_engine_validator/seat_class.py
validators/tests/integration/test_hook_check_cli.py
validators/tests/unit/test_hook_check.py
validators/tests/unit/test_runner_ring1_tool_guard.py
```
