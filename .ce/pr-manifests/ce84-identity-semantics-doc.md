# PR path manifest — creator-engine#84 identity semantics documentation

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce84-identity-semantics-doc
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below (the carrier lists itself); the fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified scope:
creator-engine#84 docs-only slice. Clarify how humans and Controllers interpret
`controller_id`, `lane_id`, pane identity, lease ownership, and handoff ownership
for concurrent seats. This addresses the documentation acceptance item only and
leaves schema changes, runtime enforcement, validator conflict scans, migrations,
and broader identity hardening to follow-ups.

- **Declared work class:** tiny

Per-file purpose (the closed path-set — 5 paths):
- **`.ce/changelog/ce84-identity-semantics-doc.md`** *(A)* — changelog fragment.
- **`.ce/pr-manifests/ce84-identity-semantics-doc.md`** *(A)* — this carrier
  (self-inclusive).
- **`docs/operations/ACTIVE_WORK_LEDGER_PROTOCOL.md`** *(M)* — primary identity
  semantics note for ledger controller/lane/pane/handoff interpretation.
- **`docs/operations/PANE_REGISTRY_PROTOCOL.md`** *(M)* — pane identity is
  evidence for the bound claim, not lane ownership.
- **`docs/operations/WORKTREE_LEASE_PROTOCOL.md`** *(M)* — lease ownership is the
  exact `controller_id`; handoff recipients need their own lease coverage.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=03f1d5c10e2b4f1c0faf712fc39158281a9f423133f1a756d024f4aede770a7a

```text
.ce/changelog/ce84-identity-semantics-doc.md
.ce/pr-manifests/ce84-identity-semantics-doc.md
docs/operations/ACTIVE_WORK_LEDGER_PROTOCOL.md
docs/operations/PANE_REGISTRY_PROTOCOL.md
docs/operations/WORKTREE_LEASE_PROTOCOL.md
```
