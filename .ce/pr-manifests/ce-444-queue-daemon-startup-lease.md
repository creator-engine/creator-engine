# PR path manifest — ce-ops#444 · queue daemon startup lease

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-444-queue-daemon-startup-lease`
and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** M

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=a094dd435a4dc576e8a853008a41454e0aef6ebfa17a465d5d98a7591b9e7e58

```text
.ce/changelog/ce-444-queue-daemon-startup-lease.md
.ce/pr-manifests/ce-444-queue-daemon-startup-lease.md
deploy/queue-daemon/RELOCATION.md
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_integrator_belt.py
```
