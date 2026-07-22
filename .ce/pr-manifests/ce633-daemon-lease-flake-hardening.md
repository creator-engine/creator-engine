# PR path manifest — ce-ops#633 · Harden daemon lease heartbeat-failure test

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce633-daemon-lease-flake-hardening`
and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=f499818228f5085b50e86ac9f905cc9e13dcffdb71d28116dcfa4523d77c4a46

```text
.ce/changelog/ce633-daemon-lease-flake-hardening.md
.ce/pr-manifests/ce633-daemon-lease-flake-hardening.md
validators/tests/unit/test_daemon_lease.py
```
