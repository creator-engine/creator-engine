# PR path manifest — ce-ops#611 · Strengthen runtime-policy recovery proof

This per-PR carrier lists the closed authorized path set for the test-only `XS`
slice. The forge sizing label remains compatible as `wc:S`.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=f06036a346a0853b370e35db2548b3c68b84b552b644ed880fdd254716db5af5

```text
.ce/changelog/ce-611-runtime-policy-recovery-proof.md
.ce/pr-manifests/ce-611-runtime-policy-recovery-proof.md
validators/tests/unit/test_onboard_apply.py
```
