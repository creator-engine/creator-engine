# PR path manifest - deterministic controller no-inlining

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-557-deterministic-noninlining-w2`
and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below; this carrier lists itself.

- **Branch:** `ce-557-deterministic-noninlining-w2`
- **Base:** `be0e8cbe66acea9998553f2cec59144397029694`
- **Predecessor commit:** `3f451a284becebdc44672d84194e49cb949e1e00`
- **Declared work class:** story
- **Authority boundary:** implementation is limited to deterministic controller
  no-inlining enforcement and these two required carrier files; no implementation
  paths, authority-bound systems, validator semantics, waivers, PR approval,
  merge, push, deploy, credential movement, or service mutation are authorized
  by this repair.
- **Evidence:** predecessor focused enforcement tests reported 263 passed; this
  carrier repair is validated by the focused path-manifest check and one full
  governed validator run after the repair commit.

Per-file purpose:

- **`.ce/changelog/ce-557-deterministic-noninlining-w2.md`** *(A)* - changelog
  fragment for the governed story and carrier repair evidence.
- **`.ce/pr-manifests/ce-557-deterministic-noninlining-w2.md`** *(A)* - this
  closed path-set carrier.
- **`docs/operations/CONTROLLER_BOUNDARY_POLICY.md`** *(M)* - documents the
  deterministic controller no-inlining refusal boundary and worker dispatch hint.
- **`validators/creator_engine_validator/hook_check.py`** *(M)* - classifies and
  refuses controller execution-plane primitives unless a launch-pinned governed
  implementer worker record is present.
- **`validators/creator_engine_validator/runner/ring1_tool_guard.py`** *(M)* -
  hardens the Codex/FACE tool shim's Python resolver before execution-plane
  primitive enforcement.
- **`validators/creator_engine_validator/seat_class.py`** *(M)* - expands the
  foreman delegation denial reason with the governed implementer dispatch hint.
- **`validators/tests/unit/test_hook_check.py`** *(M)* - covers controller
  primitive denial, launch-pinned worker allowance, stale/malformed worker
  fail-closed behavior, and updated worker-context expectations.
- **`validators/tests/unit/test_runner_ring1_tool_guard.py`** *(M)* - covers
  Ring-1 shim refusal for controller execution-plane primitive commands.

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
