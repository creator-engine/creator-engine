# PR path manifest — ce-ops#429 · Forward automerge repo root

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-429-repo-root-forward` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=9e04556f84886c72a52b9b2ba648c46862b4d1d32c3fc3124a04f2168cdfeacc

```text
.ce/changelog/ce-429-repo-root-forward.md
.ce/pr-manifests/ce-429-repo-root-forward.md
validators/creator_engine_validator/ce_cli.py
validators/tests/unit/test_automerge_decide_cli.py
```
