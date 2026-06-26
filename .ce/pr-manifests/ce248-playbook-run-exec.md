# PR path manifest — ce-ops#248 · playbook run/list execution

- **Declared work class:** feature

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce248-playbook-run-exec` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=92e0bdb897013166fa90e11954e239cfb3aef24a5338381accb8e7ca1a1cc7bb

```text
.ce/changelog/ce248-playbook-run-exec.md
.ce/pr-manifests/ce248-playbook-run-exec.md
docs/contracts/playbook-format.md
schemas/playbook.schema.yaml
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/playbook_runtime.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_playbook_runtime.py
```
