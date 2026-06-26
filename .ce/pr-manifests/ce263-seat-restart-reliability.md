# PR path manifest - ce263-seat-restart-reliability

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).
CI runs `verify-path-manifest --base <PR base sha> --manifest-dir
.ce/pr-manifests --head-ref ce263-seat-restart-reliability --require-carrier`
and requires this PR's `base..HEAD` diff to equal exactly the authorized
path-set below. This carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=6c4def3dae056e4336cb4a2e7c6c917bc9e0b882eb732e8f4002022303a35e39

```text
.ce/changelog/ce263-seat-restart-reliability.md
.ce/pr-manifests/ce263-seat-restart-reliability.md
deploy/systemd/README.md
deploy/systemd/ce-codex-seat@.service
validators/tests/unit/test_gate_daemons_systemd.py
```
