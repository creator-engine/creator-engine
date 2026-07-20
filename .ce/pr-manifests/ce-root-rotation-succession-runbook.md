# PR Path Manifest - CE Root Rotation And Succession Runbook

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this change. It is self-inclusive.

- **Declared work class:** tiny

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

This documentation-only correction records an eventual installer-contract
update without changing the consumer contract itself.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=40be29319c02518b1fe3096c06851a795234cf249c8b2691282f58c88af4f240

```text
.ce/changelog/ce-root-rotation-succession-runbook.md
.ce/pr-manifests/ce-root-rotation-succession-runbook.md
docs/security/CE_ROOT_ROTATION_AND_SUCCESSION_RUNBOOK.md
```
