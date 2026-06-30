# PR path manifest — L10 · Migrate work-class vocabulary to XS/S/M/L

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-workclass-xsml` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=40

AUTHORIZED_PATHS_SHA256=8c4c3e3823c5d09c4862b4bd56feb4d582aff852b52789fc7249770fc3f68950

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-workclass-xsml.md
.ce/pr-manifests/ce-workclass-xsml.md
.ce/reference/cli.generated.md
.ce/reference/schemas.generated.md
.github/pull_request_template.md
.github/workflows/validate.yml
docs/contracts/authoring-a-governed-pr.md
docs/contracts/work-sizing-tiers.md
docs/design/ce-orchestrator-agent.md
docs/design/controller-bootstrap-ssot.json
docs/operations/AUTHOR_A_CE_VALID_PR.md
tools/egress-broker/egress_broker/orchestrator.py
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/checks/work_sizing_floor.py
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/forge/automerge_actuator.py
validators/creator_engine_validator/forge/automerge_policy.py
validators/creator_engine_validator/forge/change.py
validators/creator_engine_validator/forge_triage.py
validators/creator_engine_validator/playbook_runtime.py
validators/creator_engine_validator/pr_preflight.py
validators/creator_engine_validator/schemas/automerge-decision.schema.yaml
validators/creator_engine_validator/schemas/orchestrator-checkpoint.schema.yaml
validators/creator_engine_validator/schemas/work-sizing-floor.schema.yaml
validators/creator_engine_validator/schemas/work-sizing.schema.yaml
validators/creator_engine_validator/work_sizing.py
validators/tests/unit/test_automerge_actuator.py
validators/tests/unit/test_automerge_policy.py
validators/tests/unit/test_dispatch_plan.py
validators/tests/unit/test_egress_orchestrator.py
validators/tests/unit/test_forge_triage.py
validators/tests/unit/test_open_change.py
validators/tests/unit/test_orchestrator_records.py
validators/tests/unit/test_orchestrator_status.py
validators/tests/unit/test_playbook_runtime.py
validators/tests/unit/test_pr_preflight.py
validators/tests/unit/test_work_sizing.py
validators/tests/unit/test_work_sizing_floor.py
validators/tests/unit/test_work_sizing_floor_ci_wiring.py
```
