# PR path manifest — ce-ops#296 · close-bot token fallback + ce-NNN title parsing

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce296-closebot-token-and-parser` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=c55de1a93f61df6e800ec434ed7266bb2982cd17daca345d330144bf99210ddf

```text
.ce/changelog/ce296-closebot-token-and-parser.md
.ce/pr-manifests/ce296-closebot-token-and-parser.md
.github/workflows/ce-ops-autoclose.yml
tools/ce-ops-autoclose/parse_issue_refs.py
validators/tests/unit/test_ceops_autoclose.py
```
