# PR path manifest — ce-portability-guard-hygiene · Portability guard test hygiene

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-portability-guard-hygiene` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=3

AUTHORIZED_PATHS_SHA256=d1d68e2fb48b2ab1b72c5f025395134dc5e402c448b192130ce632a0d7891465

```text
.ce/changelog/ce-portability-guard-hygiene.md
.ce/pr-manifests/ce-portability-guard-hygiene.md
validators/tests/unit/test_portability_plane.py
```
