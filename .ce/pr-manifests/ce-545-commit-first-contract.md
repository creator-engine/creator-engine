# PR path manifest - ce-545-commit-first-contract

Per-PR carrier for ce-ops#545. The committed `base..HEAD` diff must equal the
closed authorized path-set below. This carrier lists itself.

- **Declared work class:** story
- **story:** ce-ops#545 Commit-first candidate validation contract

Canonicalization:
`sha256("\\n".join(sorted(unique_paths)) + "\\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=135b544bc3c72e289cfd398eadda21f0cbffdbb09c0a78a5cfc52f09934613e3

```text
.ce/changelog/ce-545-commit-first-contract.md
.ce/pr-manifests/ce-545-commit-first-contract.md
.claude/agents/implementer.md
docs/contracts/authoring-a-governed-pr.md
docs/operations/AUTHOR_A_CE_VALID_PR.md
playbooks/controller/briefs/dispatch.md
```
