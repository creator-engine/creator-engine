# PR path manifest — ce-ops#566 · Add the policy-bound ce worker launch one-shot planner

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-566-governed-codex-worker-launcher` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** epic

AUTHORIZED_PATHS_COUNT=14

AUTHORIZED_PATHS_SHA256=13269b1bc046f287bbb3514acf65224d72360c1bfc43fb5f7c3cbebd873fe6c2

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-566-governed-codex-worker-launcher.md
.ce/pr-manifests/ce-566-governed-codex-worker-launcher.md
.ce/reference/cli.generated.md
deploy/vps-runsc/README.md
deploy/vps-runsc/run-vps-runsc.sh
docs/operations/WORKER_CONTAINER_PROTOCOL.md
governance/policies/codex-one-shot-launch-v1.yaml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/codex_worker_launcher.py
validators/tests/unit/test_ce_brain_drift.py
validators/tests/unit/test_ce_worker_cli.py
validators/tests/unit/test_codex_worker_launcher.py
validators/tests/unit/test_vps_runsc_launcher.py
```
