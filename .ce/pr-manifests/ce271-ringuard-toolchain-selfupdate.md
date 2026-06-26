# PR path manifest — ce-ops#271 · ring-1 toolchain self-update block + readonly VPS codex binary mount

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce271-ringuard-toolchain-selfupdate` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=83c63a13e6baaf5fdfe9666d4758575eed12fc1d09a212bf932b3dc232478bcc

```text
.ce/changelog/ce271-ringuard-toolchain-selfupdate.md
.ce/pr-manifests/ce271-ringuard-toolchain-selfupdate.md
validators/creator_engine_validator/hook_check.py
validators/tests/unit/test_hook_check.py
```
