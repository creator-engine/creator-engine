# PR path manifest - ce-f2-logsdirectory-bind - F-2.1b: restore LogsDirectory= / LogsDirectoryMode= binding in ce-queue-daemon.service

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-f2-logsdirectory-bind` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=ad47416f71ffda40fb89f70de47c19655e50b361e09176c51439db81a70ef14a

```text
.ce/changelog/ce-f2-logsdirectory-bind.md
.ce/pr-manifests/ce-f2-logsdirectory-bind.md
deploy/queue-daemon/ce-queue-daemon.service
```
