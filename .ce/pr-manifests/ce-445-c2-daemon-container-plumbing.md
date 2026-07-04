# PR path manifest - daemon container launcher plumbing

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-445-c2-daemon-container-plumbing` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=db010b5bd156abb8f3388d0d8216006723f428085a2251b1e740afccf5cb548d

```text
.ce/changelog/ce-445-c2-daemon-container-plumbing.md
.ce/pr-manifests/ce-445-c2-daemon-container-plumbing.md
deploy/daemons/run-daemon-container.sh
validators/tests/unit/test_daemon_lease.py
```
