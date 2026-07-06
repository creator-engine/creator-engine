# PR path manifest — ADR-0005 · ADR-0005 slice 1 — mediated brain append daemon skeleton

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-adr0005-s1-append-daemon` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=2e1ff8866e39b19342b1e266ef1bcd86fbdde15b43893b3bb952ce9dc00184f6

```text
.ce/changelog/ce-adr0005-s1-append-daemon.md
.ce/pr-manifests/ce-adr0005-s1-append-daemon.md
validators/creator_engine_validator/brain_append_intent.schema.yaml
validators/creator_engine_validator/brain_append_worker.py
validators/tests/unit/test_brain_append_worker.py
```
