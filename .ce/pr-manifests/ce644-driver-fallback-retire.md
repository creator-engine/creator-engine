# PR path manifest — ce-ops#644 · Retire the autoclose driver inline fallback parser

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce644-driver-fallback-retire` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=55557eacb221b8a6908770af0539c49bce688af72dd6355c0b807d7dca6a70d5

```text
.ce/changelog/ce644-driver-fallback-retire.md
.ce/pr-manifests/ce644-driver-fallback-retire.md
.github/scripts/ceops_autoclose.py
validators/tests/unit/test_ceops_autoclose.py
```
