# PR path manifest — ce-ops#345 · path manifest D-status carrier cleanup

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-345-path-manifest-dstatus` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=14c2ee6a297715d1246e0fc68a5b7c6f0dac5c8ea9d86d5b8094d4675ebcb2a6

```text
.ce/changelog/ce-345-path-manifest-dstatus.md
.ce/changelog/ce291a-automerge-classifier-dryrun.md
.ce/pr-manifests/ce-345-path-manifest-dstatus.md
.ce/pr-manifests/ce291a-automerge-classifier-dryrun.md
validators/creator_engine_validator/checks/path_manifest_fidelity.py
validators/tests/unit/test_path_manifest_fidelity.py
```
