# PR path manifest — ce-ops#219 · Codex Ring-1 hook-pack

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below (the carrier lists itself).

Scope adjudication:
IN: Codex managed PreToolUse hook-pack registration, Codex PreToolUse shim,
shared `hook-check` policy invocation, Codex launch confirmation/refusal,
dispatch boundary label update, operator docs, and focused tests.

OUT: new policy rules, raw Codex launch bypasses, self-review/merge, container
containment work, and broad Codex reviewer-venue migration.

Per-file purpose:
- **`.ce/changelog/ce219-codex-ring1-hookpack.md`** *(A)* — change note.
- **`.ce/pr-manifests/ce219-codex-ring1-hookpack.md`** *(A)* — this carrier.
- **`.codex/hooks/ce-pretooluse-codex.py`** *(A)* — repo-local Codex hook entrypoint.
- **`.codex/requirements.toml`** *(A)* — managed Codex PreToolUse hook registration.
- **`docs/architecture/tasks-handoff-contract.md`** *(M)* — Codex boundary label/caveat.
- **`docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md`** *(M)* — CDX-D-8 remedy row.
- **`docs/v3-roadmap.md`** *(M)* — current Codex boundary status.
- **`schemas/dispatch-record.schema.yaml`** *(M)* — Codex boundary enum value.
- **`validators/creator_engine_validator/_versions.py`** *(M)* — v1 runtime classification.
- **`validators/creator_engine_validator/codex_launch_spec.py`** *(M)* — CDX-D-8 clause.
- **`validators/creator_engine_validator/codex_pretooluse.py`** *(A)* — Codex adapter.
- **`validators/creator_engine_validator/hook_pack_confirm.py`** *(M)* — Codex managed pack confirmation.
- **`validators/creator_engine_validator/launch_runtime.py`** *(M)* — Codex confirmation before spawn.
- **`validators/creator_engine_validator/v3_cli.py`** *(M)* — operator-facing Codex risk text.
- **`validators/creator_engine_validator/v3_seat_bridge.py`** *(M)* — dispatch boundary label/brief.
- **`validators/tests/integration/test_ce_launch_cli.py`** *(M)* — Codex launch confirmation seam.
- **`validators/tests/integration/test_codex_hook_pack_pretooluse.py`** *(A)* — real shim deny/allow tests.
- **`validators/tests/unit/test_ce_launch_cli.py`** *(M)* — Codex launch confirmation seam.
- **`validators/tests/unit/test_codex_pretooluse.py`** *(A)* — adapter normalization/fail-closed tests.
- **`validators/tests/unit/test_hook_pack_confirm.py`** *(M)* — managed pack confirmation tests.
- **`validators/tests/unit/test_launch_runtime.py`** *(M)* — Codex CDX-D-8 and launch tests.
- **`validators/tests/unit/test_launch_runtime_resource_bound.py`** *(M)* — Codex confirmation seam.
- **`validators/tests/unit/test_v3_cli.py`** *(M)* — Codex boundary expectation.
- **`validators/tests/unit/test_v3_seat_bridge.py`** *(M)* — Codex boundary expectation.
- **`validators/tests/unit/test_version_boundary.py`** *(M)* — v1 runtime count.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=25

AUTHORIZED_PATHS_SHA256=017cc81d1b35ab5db1ea0c124c3e3300ea73795a700ef746378d233dd1e7559e

```text
.ce/changelog/ce219-codex-ring1-hookpack.md
.ce/pr-manifests/ce219-codex-ring1-hookpack.md
.codex/hooks/ce-pretooluse-codex.py
.codex/requirements.toml
docs/architecture/tasks-handoff-contract.md
docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md
docs/v3-roadmap.md
schemas/dispatch-record.schema.yaml
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/codex_launch_spec.py
validators/creator_engine_validator/codex_pretooluse.py
validators/creator_engine_validator/hook_pack_confirm.py
validators/creator_engine_validator/launch_runtime.py
validators/creator_engine_validator/v3_cli.py
validators/creator_engine_validator/v3_seat_bridge.py
validators/tests/integration/test_ce_launch_cli.py
validators/tests/integration/test_codex_hook_pack_pretooluse.py
validators/tests/unit/test_ce_launch_cli.py
validators/tests/unit/test_codex_pretooluse.py
validators/tests/unit/test_hook_pack_confirm.py
validators/tests/unit/test_launch_runtime.py
validators/tests/unit/test_launch_runtime_resource_bound.py
validators/tests/unit/test_v3_cli.py
validators/tests/unit/test_v3_seat_bridge.py
validators/tests/unit/test_version_boundary.py
```
