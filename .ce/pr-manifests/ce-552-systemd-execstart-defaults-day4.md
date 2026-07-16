# PR path manifest - systemd ExecStart default expansion fix

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-552-systemd-execstart-defaults-day4` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=41232fd4ce735a1341e795d36108657c1b45514e6a90bf6f5f6858a93a7b5367

```text
.ce/changelog/ce-552-systemd-execstart-defaults-day4.md
.ce/pr-manifests/ce-552-systemd-execstart-defaults-day4.md
deploy/systemd/README.md
deploy/systemd/ce-belt-daemon.service
deploy/systemd/ce-ratifier-queue.service
docs/contracts/installer.md
validators/tests/unit/test_gate_daemons_systemd.py
```
