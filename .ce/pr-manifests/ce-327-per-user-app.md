# PR path manifest - ce-ops#327 - per-user GitHub App onboarding

- **Declared work class:** tiny

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention).
CI runs:

    verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce-327-per-user-app

and requires this PR's `base..HEAD` diff to equal exactly the authorized path
set below. This carrier lists itself.

Ratified:
ce-ops#327 makes contained-seat onboarding fail closed when an own-App
declaration reuses a known shared/foreign CE App id.

The change:
- Add apply-time own-App id refusal before side-effect planning.
- Add onboarding manifest guidance for creating and supplying a per-user GitHub App.
- Add focused regression coverage for rejected foreign App ids and accepted unlisted per-user App ids.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=ca5dff52cdfc3b2363bf53e9b68b79402f21cfa996725a3e084104de19c27075

```text
.ce/changelog/ce-327-per-user-app.md
.ce/pr-manifests/ce-327-per-user-app.md
validators/creator_engine_validator/ce_onboard.py
validators/creator_engine_validator/onboard_apply.py
validators/tests/unit/test_ce_onboard.py
validators/tests/unit/test_onboard_apply.py
```
