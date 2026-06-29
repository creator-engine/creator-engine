# PR path manifest — ce-ops#313 · ARM-A automerge actuation wiring

- **Declared work class:** story

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-arm-automerge-actuate` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=4658a8f06c9291fcbf0d9187209c497b8ec88f5ddd0c66749ec52181ce3c4d53

```text
.ce/changelog/ce-arm-automerge-actuate.md
.ce/pr-manifests/ce-arm-automerge-actuate.md
.github/workflows/automerge-actuate.yml
validators/creator_engine_validator/forge/automerge_actuate_cli.py
validators/creator_engine_validator/forge/automerge_mutation_policy.yaml
validators/tests/unit/test_automerge_policy.py
```
