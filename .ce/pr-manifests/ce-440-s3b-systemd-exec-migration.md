# PR path manifest — ce-ops#440 · Migrate repo systemd units from cev3 to ce

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-440-s3b-systemd-exec-migration` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=4276f257dde2bedf251e9ee2a417b2ec1840cde11cd1da12505981824be3cfc2

```text
.ce/changelog/ce-440-s3b-systemd-exec-migration.md
.ce/pr-manifests/ce-440-s3b-systemd-exec-migration.md
deploy/systemd/ce-integrator-daemon.service
deploy/systemd/ce-review-pickup-daemon.service
validators/tests/unit/test_gate_daemons_systemd.py
```
