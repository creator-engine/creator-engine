# PR path manifest — ce-366-mainhead-resolver-adr · Main-HEAD artifact resolver ADR

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-366-mainhead-resolver-adr` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** `S`

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=97a29f18c47177ef5a11a69a2b947e159c16f2fa530777ff62ca4aeb7a68a506

```text
.ce/changelog/ce-366-mainhead-resolver-adr.md
.ce/pr-manifests/ce-366-mainhead-resolver-adr.md
docs/adr/ADR-0003-main-head-artifact-resolver-builder-verifier.md
```
