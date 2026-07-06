# PR path manifest — ce-ops#426 · G11 reviewer-authority in-launcher minting

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-426-g11-reviewer-authority-minting` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=16

AUTHORIZED_PATHS_SHA256=5bd7d0b9dc516540b09f08d9e0ede8309bd2656eb88b8c43566c66ad5c7aafaf

```text
.ce/changelog/ce-426-g11-reviewer-authority-minting.md
.ce/pr-manifests/ce-426-g11-reviewer-authority-minting.md
.ce/reference/cli.generated.md
docs/operations/GOVERNED_LANE_LAUNCH_PROTOCOL.md
docs/operations/REVIEWER_VENUE_AUTHORITY.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/checks/reviewer_authority_envelope.py
validators/creator_engine_validator/forge/cred_injection_proxy.py
validators/creator_engine_validator/hook_check.py
validators/creator_engine_validator/lane_runtime.py
validators/creator_engine_validator/schemas/reviewer-authority-envelope.schema.yaml
validators/tests/unit/test_cred_injection_proxy.py
validators/tests/unit/test_egress_self_review_broker.py
validators/tests/unit/test_hook_check_reviewer_authority.py
validators/tests/unit/test_lane_runtime_reviewer_venue.py
validators/tests/unit/test_reviewer_authority_envelope.py
```
