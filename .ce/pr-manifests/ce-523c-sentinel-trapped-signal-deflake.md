# PR path manifest — ce-523c · Sentinel trapped-signal deflake

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce-523c-sentinel-trapped-signal-deflake`
and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below; this carrier lists itself.

Canonicalization: `sha256("\\n".join(sorted(unique_paths)) + "\\n")`.

- **Declared work class:** XS

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=0eef789027f27684ff2715848d36af382190f56af83ed6eb7a6f0120147e8a1d

```text
.ce/changelog/ce-523c-sentinel-trapped-signal-deflake.md
.ce/pr-manifests/ce-523c-sentinel-trapped-signal-deflake.md
validators/tests/unit/test_seat_sentinel.py
```
