# PR path manifest — ce-ops#305 · de-flake egress broker half-closed-client socket test

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-305-fix-egress-socket-test` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=49379a6c5486157328b4f1d50c46006066f46bd0837da65891aad0a01b2b77f9

```text
.ce/changelog/ce-305-fix-egress-socket-test.md
.ce/pr-manifests/ce-305-fix-egress-socket-test.md
validators/tests/unit/test_egress_host_broker.py
```
