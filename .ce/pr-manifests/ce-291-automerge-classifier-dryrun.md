# PR path manifest — ce-ops#291 · CEO-mode auto-merge classifier dry-run

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-291-automerge-classifier-dryrun` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=3e26be14e15ffb74ba185a822f8da554dc2fdf45f385cc0692eae1e9aa5e82f2

```text
.ce/changelog/ce-291-automerge-classifier-dryrun.md
.ce/pr-manifests/ce-291-automerge-classifier-dryrun.md
.ce/reference/schemas.generated.md
validators/creator_engine_validator/forge/automerge_mutation_policy.yaml
validators/creator_engine_validator/forge/automerge_policy.py
validators/creator_engine_validator/forge/mutation_classifier.py
validators/creator_engine_validator/schemas/automerge-decision.schema.yaml
validators/creator_engine_validator/schemas/automerge-policy.schema.yaml
validators/pyproject.toml
validators/tests/unit/test_automerge_policy.py
validators/tests/unit/test_mutation_classifier.py
```
