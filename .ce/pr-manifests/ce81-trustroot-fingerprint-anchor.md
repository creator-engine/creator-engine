# PR path manifest -- ce-ops#81 trustroot fingerprint anchor

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce81-trustroot-fingerprint-anchor` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Closes creator-engine/ce-ops#81

- **Declared work class:** tiny

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=780269989112e403bef129f00434af9dcd09255fc8d95c26c1ccb2d585d66b94

```text
.ce/changelog/ce81-trustroot-fingerprint-anchor.md
.ce/pr-manifests/ce81-trustroot-fingerprint-anchor.md
README.md
docs/llms.txt
docs/security/trust-anchors.md
```
