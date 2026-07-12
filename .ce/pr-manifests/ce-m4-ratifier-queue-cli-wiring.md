# PR path manifest — ce-m4-ratifier-queue-cli-wiring · M4 ratifier queue CLI wiring

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-m4-ratifier-queue-cli-wiring` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=17

AUTHORIZED_PATHS_SHA256=65585ff4b2b25cabdea3e3861dd0f1f3f35657df330a5bafbeb39525acb03cad

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-m4-ratifier-queue-cli-wiring.md
.ce/pr-manifests/ce-m4-ratifier-queue-cli-wiring.md
.ce/reference/cli.generated.md
deploy/systemd/README.md
deploy/systemd/ce-ratifier-queue.service
deploy/systemd/install-gate-daemons-systemd.sh
docs/reference/cli.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/checks/documented_verbs.py
validators/creator_engine_validator/forge/ratifier_queue_runtime.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_ce_cli_v3_shim.py
validators/tests/unit/test_gate_daemons_systemd.py
validators/tests/unit/test_ratifier_queue_runtime.py
validators/tests/unit/test_v1_docs_reconciliation.py
validators/tests/unit/test_v3_cli.py
```
