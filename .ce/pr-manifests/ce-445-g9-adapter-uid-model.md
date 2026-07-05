# PR path manifest - ce-445-g9-adapter-uid-model

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-445-g9-adapter-uid-model` and
requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=1b2e85344db51e47ce2cc5d4a5432ca46643ff288a59dca957e9acac5fb1f511

```text
.ce/changelog/ce-445-g9-adapter-uid-model.md
.ce/pr-manifests/ce-445-g9-adapter-uid-model.md
deploy/daemons/run-daemon-container.sh
validators/tests/unit/test_daemon_lease.py
```
