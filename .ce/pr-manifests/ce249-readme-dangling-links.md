# PR path manifest — ce-ops#249 · remove dangling roadmap links from README + guard dangling internal-doc links

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce249-readme-dangling-links` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=550e03fa9d1d5e2057e33045a49ab30ad924f9adc5f8308c0a4769c1e51a0b97

```text
.ce/changelog/ce249-readme-dangling-links.md
.ce/pr-manifests/ce249-readme-dangling-links.md
README.md
validators/tests/unit/test_public_docs_confidentiality.py
```
