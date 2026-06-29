# PR path manifest — ce-ops#360 · Support agent OpenRouter adapter

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-support-openrouter-adapter` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=07d288084ae91bc8e343a26544f4ec82e0f4eed59725fc79a96107dbe59b1f11

- **Declared work class:** story

```text
.ce/changelog/ce-support-openrouter-adapter.md
.ce/pr-manifests/ce-support-openrouter-adapter.md
tools/support-agent/openrouter_model_cmd.py
validators/tests/unit/test_openrouter_model_cmd.py
```
