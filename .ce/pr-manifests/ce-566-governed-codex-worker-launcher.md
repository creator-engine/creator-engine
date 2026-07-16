# PR path manifest — ce-ops#566 / ce-ops#567 governed Codex one-shot launcher

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this candidate. CI requires the base..HEAD diff to
equal this set exactly; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** feature

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=1b1cd556774d4501474d45564ff6707a5f392a07948447d673d74b7523d2261e

```text
.ce/changelog/ce-566-governed-codex-worker-launcher.md
.ce/pr-manifests/ce-566-governed-codex-worker-launcher.md
deploy/vps-runsc/README.md
deploy/vps-runsc/run-vps-runsc.sh
docs/operations/WORKER_CONTAINER_PROTOCOL.md
governance/policies/codex-one-shot-launch-v1.yaml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/codex_worker_launcher.py
validators/tests/unit/test_ce_worker_cli.py
validators/tests/unit/test_codex_worker_launcher.py
validators/tests/unit/test_vps_runsc_launcher.py
```
