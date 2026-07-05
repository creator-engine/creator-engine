# PR path manifest — ce-434 · Document the contained-seat validation profile in the dispatch playbook

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-434-playbook-contained-profile` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=73d6865752b96957a61d5241a69ef82f49af93c08b032edd23f24e7f57b4b630

```text
.ce/changelog/ce-434-playbook-contained-profile.md
.ce/pr-manifests/ce-434-playbook-contained-profile.md
playbooks/controller/briefs/dispatch.md
```
