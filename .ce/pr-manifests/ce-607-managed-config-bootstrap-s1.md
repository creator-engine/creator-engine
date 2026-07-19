# PR path manifest — ce-ops#607 · managed config bootstrap S1

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-607-managed-config-bootstrap-s1` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=02986bb44493260e8959690cdf62079019c45ec5ae58432b76567b228e69412b

```text
.ce/changelog/ce-607-managed-config-bootstrap-s1.md
.ce/pr-manifests/ce-607-managed-config-bootstrap-s1.md
validators/creator_engine_validator/worker_spawn.py
validators/creator_engine_validator/codex_worker_config.py
validators/creator_engine_validator/worker_run.py
validators/tests/unit/test_worker_spawn.py
validators/tests/unit/test_codex_worker_config.py
validators/creator_engine_validator/launch_runtime.py
validators/creator_engine_validator/tmux_adapter.py
validators/tests/unit/test_launch_runtime.py
validators/tests/unit/test_tmux_adapter.py
```
