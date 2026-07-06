# PR path manifest — ce-ops#426 · G11 reviewer-authority in-launcher minting

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-426-g11-reviewer-authority-minting` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=88cdb62b8790d4836a4394b6a9193107d0169886208fb8613885d2009d9dbb7b

```text
.ce/changelog/ce-426-g11-reviewer-authority-minting.md
.ce/pr-manifests/ce-426-g11-reviewer-authority-minting.md
.ce/reference/cli.generated.md
docs/operations/GOVERNED_LANE_LAUNCH_PROTOCOL.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/lane_runtime.py
validators/tests/unit/test_lane_runtime_reviewer_venue.py
```
