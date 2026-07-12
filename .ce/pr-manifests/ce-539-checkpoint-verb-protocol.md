# PR path manifest — ce-ops#539 · Checkpoint verb and agent protocol

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-539-checkpoint-verb-protocol` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=15

AUTHORIZED_PATHS_SHA256=e0db092bf3c9c8a86cb9dfc7aaf46cc4a7e6f7b20d81cfbd386da0f8eb5abb09

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-539-checkpoint-verb-protocol.md
.ce/pr-manifests/ce-539-checkpoint-verb-protocol.md
.ce/reference/cli.generated.md
.ce/reference/schemas.generated.md
.claude/skills/ce-checkpoint/SKILL.md
docs/reference/cli.md
playbooks/controller/briefs/checkpoint.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/checkpoint_runtime.py
validators/creator_engine_validator/checks/documented_verbs.py
validators/creator_engine_validator/schemas/checkpoint-input.schema.yaml
validators/tests/unit/test_ce_checkpoint_cli.py
validators/tests/unit/test_checkpoint_runtime.py
validators/tests/unit/test_v1_docs_reconciliation.py
```
