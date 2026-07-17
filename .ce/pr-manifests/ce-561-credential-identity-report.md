# PR path manifest - Credential identity architecture findings

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path set for this change. The path-manifest check compares the
base-to-head diff with this list; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=3d92bb475408aed43e985173328f6c6d86e89f8c357f5860314f41362766f1c2

```text
.ce/changelog/ce-561-credential-identity-report.md
.ce/pr-manifests/ce-561-credential-identity-report.md
docs/architecture/README.md
docs/architecture/credential-identity-architecture-20260713.md
```
