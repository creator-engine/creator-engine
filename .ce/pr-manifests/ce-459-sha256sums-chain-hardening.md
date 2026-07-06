# PR path manifest — ce-ops#459 · Harden adopted client SHA256SUMS verification

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-459-sha256sums-chain-hardening` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=07a887490ce5c79b3e54c67fc8261eedccc495e50508dcd6f999a19739500b27

```text
.ce/changelog/ce-459-sha256sums-chain-hardening.md
.ce/pr-manifests/ce-459-sha256sums-chain-hardening.md
validators/creator_engine_validator/onboard_apply.py
validators/tests/unit/test_onboard_apply.py
```
