# PR path manifest — 523b · test: deflake JIT peercred rejection race

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-523b-jit-deflake` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=d6a810c6b853da1f75af59cf339c8dacc8252ef5592022f19f917b73fe1d8d60

```text
.ce/changelog/ce-523b-jit-deflake.md
.ce/pr-manifests/ce-523b-jit-deflake.md
validators/tests/unit/test_jit_credential_broker.py
```
