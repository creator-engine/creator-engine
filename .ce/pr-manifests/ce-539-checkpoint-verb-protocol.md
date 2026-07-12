# PR path manifest — ce-ops#539 · Checkpoint verb and agent protocol

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-539-checkpoint-verb-protocol` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=023a9fe51d35b441f041493ffdd91d80d2bd2d8e475b79fd4fe66cccbcf0db92

```text
.ce/changelog/ce-539-checkpoint-verb-protocol.md
.ce/pr-manifests/ce-539-checkpoint-verb-protocol.md
.ce/reference/cli.generated.md
.ce/reference/schemas.generated.md
.claude/skills/ce-checkpoint/SKILL.md
playbooks/controller/briefs/checkpoint.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/checkpoint_runtime.py
validators/creator_engine_validator/schemas/checkpoint-input.schema.yaml
validators/tests/unit/test_ce_checkpoint_cli.py
validators/tests/unit/test_checkpoint_runtime.py
```
