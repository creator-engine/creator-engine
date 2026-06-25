# PR path manifest — ce-ops#switch-openai-account · codex OpenAI account-switch runbook + helper

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-openai-account-switch-runbook` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=0b3cdc5a3403cae79d53244488859944be33dd84b91b362831bd47a67d5726ce

```text
.ce/changelog/ce-openai-account-switch-runbook.md
.ce/pr-manifests/ce-openai-account-switch-runbook.md
docs/operations/SWITCH_OPENAI_ACCOUNT.md
scripts/switch-openai-account.sh
```
