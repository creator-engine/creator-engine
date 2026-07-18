# PR path manifest — ce-ops#592 · Use short test roots for AF_UNIX sockets

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-592-af-unix-temp-root` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=14d366bb4591cbe7a3fff69cd876c72a1090b25565202015f7f0086ac75ad744

```text
.ce/changelog/ce-592-af-unix-temp-root.md
.ce/pr-manifests/ce-592-af-unix-temp-root.md
validators/tests/conftest.py
validators/tests/unit/test_egress_host_broker.py
validators/tests/unit/test_jit_credential_broker.py
```
