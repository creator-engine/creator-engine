# PR path manifest — ce-ops#484 · Ephemeral controller provider seam design

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-484-ephemeral-controller-seam-design` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=5475f819b116477c766546a7717fa1362109c2d2c72b33225675497dcdb33c08

```text
.ce/changelog/ce-484-ephemeral-controller-seam-design.md
.ce/pr-manifests/ce-484-ephemeral-controller-seam-design.md
docs/design/ephemeral-controller-provider-seam.md
```
