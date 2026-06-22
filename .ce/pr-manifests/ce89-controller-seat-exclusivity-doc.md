# PR path manifest - ce89-controller-seat-exclusivity-doc

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce89-controller-seat-exclusivity-doc
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
creator-engine/creator-engine#89 docs-only slice for duplicate live
mutation-capable Controller-seat refusal semantics.

- **Declared work class:** tiny

Base:
`origin/main` at branch creation.

Per-file purpose (closed path-set - 5 paths):
- **`.ce/changelog/ce89-controller-seat-exclusivity-doc.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce89-controller-seat-exclusivity-doc.md`** *(A)* - this carrier.
- **`docs/operations/ACTIVE_WORK_LEDGER_PROTOCOL.md`** *(M)* - documents `controller_id` as durable live-exclusive mutation authority identity.
- **`docs/operations/CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md`** *(M)* - records future `ce launch` / `ce hud` duplicate-refusal contract and docs-only boundary.
- **`docs/operations/PANE_REGISTRY_PROTOCOL.md`** *(M)* - distinguishes observational pane/sentinel evidence from Controller ownership authority.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=b60e2b1f44b467c0147a3d940dcfd32060026cb5188b7f218f3835171644ed7a

```text
.ce/changelog/ce89-controller-seat-exclusivity-doc.md
.ce/pr-manifests/ce89-controller-seat-exclusivity-doc.md
docs/operations/ACTIVE_WORK_LEDGER_PROTOCOL.md
docs/operations/CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md
docs/operations/PANE_REGISTRY_PROTOCOL.md
```
