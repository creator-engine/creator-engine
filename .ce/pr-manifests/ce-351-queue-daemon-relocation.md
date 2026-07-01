# PR path manifest - ce-ops#351 - queue daemon relocation

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-351-queue-daemon-relocation` and
requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M
- **CE-TEST-COUPLING-EXEMPT:** pure deploy/runbook artifacts; no daemon Python
  logic or production application behavior changed.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=480638fbbccaf26c7695be14981f867f8d64a8e18dbdf1c6cf0b4ef644789bd4

```text
.ce/changelog/ce-351-queue-daemon-relocation.md
.ce/pr-manifests/ce-351-queue-daemon-relocation.md
deploy/queue-daemon/RELOCATION.md
deploy/queue-daemon/ce-queue-daemon.service
deploy/queue-daemon/launch-queue-daemon.sh
```
