# PR path manifest - deterministic controller no-inlining

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-557-deterministic-noninlining-w2`
and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below; this carrier lists itself.

- **Branch:** `ce-557-deterministic-noninlining-w2`
- **Base:** `be0e8cbe66acea9998553f2cec59144397029694`
- **Predecessor commit:** `2b357a8a5dac8e3b010384cf5afdf397864b12dc`
- **Declared work class:** story
- **Authority boundary:** implementation is limited to deterministic controller
  no-inlining enforcement and these two required carrier files; no implementation
  paths, authority-bound systems, validator semantics, waivers, PR approval,
  merge, push, deploy, credential movement, or service mutation are authorized
  by this repair.
- **Evidence:** final-review rework focused tests reported
  `test_hook_check.py` plus `test_runner_ring1_tool_guard.py` as `264 passed`;
  this branch is validated by one full governed validator run after the rework
  commit.

Per-file purpose:

- **`.ce/changelog/ce-557-deterministic-noninlining-w2.md`** *(A)* - changelog
  fragment for the governed story and carrier repair evidence.
- **`.ce/pr-manifests/ce-557-deterministic-noninlining-w2.md`** *(A)* - this
  closed path-set carrier.
- **`docs/operations/CONTROLLER_BOUNDARY_POLICY.md`** *(M)* - documents the
  deterministic controller no-inlining refusal boundary, worker dispatch hint,
  and fail-closed launch-pinned identity requirement.
- **`validators/creator_engine_validator/hook_check.py`** *(M)* - classifies and
  refuses controller execution-plane primitives unless a complete launcher-pinned
  governed implementer worker context validates against the current worker
  record; parses shell composition and archive operation grammar fail-closed.
- **`validators/creator_engine_validator/runner/ring1_tool_guard.py`** *(M)* -
  guards the concrete Ring-1 command entry points, scrubs inherited
  `CE_WORKER_*`, and propagates authenticated worker context from
  launcher-controlled configuration.
- **`validators/creator_engine_validator/seat_class.py`** *(M)* - expands the
  foreman delegation denial reason with the governed implementer dispatch hint.
- **`validators/tests/unit/test_hook_check.py`** *(M)* - covers hard denial
  across missing/ungoverned context, launch-pinned worker allowance,
  replay/mismatch/stale/malformed fail-closed behavior, parsed command
  primitive classification, archive read-vs-extract seams, and closed spawn
  capability identifiers.
- **`validators/tests/unit/test_runner_ring1_tool_guard.py`** *(M)* - covers
  Ring-1 shim refusal for controller execution-plane primitive commands,
  default governed entry points, hostile inherited env scrubbing, and
  worker-context propagation.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=83a11b9a88c276c9b6235a49aa3b6ab4720d97557a6177d55a656faa0af268c6

```text
.ce/changelog/ce-557-deterministic-noninlining-w2.md
.ce/pr-manifests/ce-557-deterministic-noninlining-w2.md
docs/operations/CONTROLLER_BOUNDARY_POLICY.md
validators/creator_engine_validator/hook_check.py
validators/creator_engine_validator/runner/ring1_tool_guard.py
validators/creator_engine_validator/seat_class.py
validators/tests/unit/test_hook_check.py
validators/tests/unit/test_runner_ring1_tool_guard.py
```
