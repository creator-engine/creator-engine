# PR path manifest — ce-ops#395 · Add release-bump commit mode

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-395-bump-to-main` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** S

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=8bfa488e0115673f54bf76a5685326951e8fbfbf639a6765855ae912e3ecfb6c

```text
.ce/changelog/ce-395-bump-to-main.md
.ce/pr-manifests/ce-395-bump-to-main.md
validators/creator_engine_validator/cli.py
validators/creator_engine_validator/release_bump.py
validators/creator_engine_validator/release_orchestrate.py
validators/tests/unit/test_release_bump_commit.py
```
