# PR path manifest — none · Queue daemon IaC declaration

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-n8-queue-daemon-iac` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=ca0c08024aa69382448ebf7146280fd673214085a707ad70f1be9e431dc1b224

```text
.ce/changelog/ce-n8-queue-daemon-iac.md
.ce/pr-manifests/ce-n8-queue-daemon-iac.md
deploy/daemons/run-daemon-container.sh
deploy/queue-daemon/RELOCATION.md
deploy/queue-daemon/ce-queue-daemon.env.template
deploy/queue-daemon/ce-queue-daemon.service
validators/tests/unit/test_daemon_lease.py
```
