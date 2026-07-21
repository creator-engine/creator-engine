# PR path manifest — T4 · Retire mandatory local full validation policy

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref t4-policy-flip` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** feature

AUTHORIZED_PATHS_COUNT=43

AUTHORIZED_PATHS_SHA256=f4b4307be72766e77cc293e2ca48f2d228e1eab85d3ba982499a0eb94902ee60

```text
.ce/brain/assertions.yaml
.ce/changelog/t4-policy-flip.md
.ce/design/conveyor-harvest-push.md
.ce/pr-manifests/t4-policy-flip.md
.ce/reference/cli.generated.md
.claude/agents/implementer.md
.claude/skills/ce-harvest/SKILL.md
.github/pull_request_template.md
CONTRIBUTING.md
deploy/dgx-runsc/README.md
docs/compliance/ssdf-slsa-conformance.md
docs/contracts/authoring-a-governed-pr.md
docs/contracts/workflow-catalog.md
docs/delivery/DEFINITION_OF_DONE.md
docs/delivery/NEXT_TASK_PROTOCOL.md
docs/delivery/RELEASE_CANDIDATE_CHECKLIST.md
docs/delivery/ROLLBACK_AND_POST_RELEASE_EVIDENCE.md
docs/delivery/VERSIONING_AND_RELEASE_POLICY.md
docs/design/controller-bootstrap-ssot.json
docs/design/ephemeral-controller-provider-seam.md
docs/design/seat-side-preflight.md
docs/guide/contributing-to-ce.html
docs/guide/contributing-to-ce.md
docs/operations/AUTHOR_A_CE_VALID_PR.md
docs/operations/FORGE_HOUSEKEEPING_RUNBOOK.md
docs/reference/cli.md
playbooks/controller/briefs/dispatch.md
playbooks/controller/briefs/harvest.md
playbooks/controller/briefs/merge-gate.md
playbooks/controller/duties.yaml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/checks/documented_verbs.py
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/forge/press_merge_evidence.py
validators/creator_engine_validator/pr_preflight.py
validators/creator_engine_validator/project_init.py
validators/creator_engine_validator/public_docs_confidentiality.py
validators/tests/unit/test_cli_reference_autogen_sync.py
validators/tests/unit/test_pr_preflight.py
validators/tests/unit/test_press_merge_evidence.py
validators/tests/unit/test_project_init.py
validators/tests/unit/test_public_docs_confidentiality.py
validators/tests/unit/test_public_docs_confidentiality_cli.py
```
