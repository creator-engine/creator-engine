# PR path manifest — ce-ops#646 · Surface autoclose parser-shim refusals through governance alerting

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce646-autoclose-refusal-alerting` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=5

AUTHORIZED_PATHS_SHA256=03159696e258bcb1912f9d71df2c87a2b180b448d2a8aad279e20631da74e05e

```text
.ce/brain/assertions.yaml
.ce/changelog/ce646-autoclose-refusal-alerting.md
.ce/pr-manifests/ce646-autoclose-refusal-alerting.md
.github/scripts/ceops_autoclose.py
validators/tests/unit/test_ceops_autoclose.py
```
