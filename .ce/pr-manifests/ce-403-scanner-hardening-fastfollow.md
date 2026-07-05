# PR path manifest — ce-ops#403 · Record public docs scanner hardening fast-follow

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-403-scanner-hardening-fastfollow` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=2

AUTHORIZED_PATHS_SHA256=cd47782d4a4a159079105dcfa92d51037ca0b9e43c2c3a8f7e1f2348746445c4

```text
.ce/changelog/ce-403-scanner-hardening-fastfollow.md
.ce/pr-manifests/ce-403-scanner-hardening-fastfollow.md
```
