# PR path manifest — ce-ops#393 · Command deprecation policy

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-393-command-deprecation-policy` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=63c51eb1ab58db6139c3da0ea66f000d684e7557cfac016f17666dc8e2683706

```text
.ce/changelog/ce-393-command-deprecation-policy.md
.ce/pr-manifests/ce-393-command-deprecation-policy.md
docs/contracts/command-deprecation-policy.md
docs/contracts/command-deprecation.yaml
```
