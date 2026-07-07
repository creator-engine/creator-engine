# PR path manifest — ce-ops#500 · Runsc launcher durable staging and worktree roots

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-500-launcher-durability` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=ba2aa644504c28fc53962a81730a12528c3ab6b9d9a349027b880a983400f8eb

```text
.ce/changelog/ce-500-launcher-durability.md
.ce/pr-manifests/ce-500-launcher-durability.md
deploy/dgx-runsc/README.md
deploy/dgx-runsc/run-codex-runsc.sh
deploy/dgx-runsc/test-seat-logging.sh
deploy/dgx-runsc/test-term-coercion.sh
deploy/vps-runsc/README.md
deploy/vps-runsc/run-vps-runsc.sh
```
