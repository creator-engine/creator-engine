# PR path manifest — L7-a · Add automatic release tag workflow

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-l7a-auto-tag` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** tiny

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=d5cd049feccd8eed681b040c958e63ce3deb9f18a6021167721945bb26540c67

```text
.ce/changelog/ce-l7a-auto-tag.md
.ce/pr-manifests/ce-l7a-auto-tag.md
.github/workflows/release-auto-tag.yml
validators/tests/unit/test_release_auto_tag_workflow.py
```
