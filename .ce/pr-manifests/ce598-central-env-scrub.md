# PR path manifest — ce-ops#598 · Centralize GitHub child-environment scrubbing

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce598-central-env-scrub` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** tiny

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=54ca816164dc659e103cb690f84c2f28e033dcf1f0529a253e2bfa26f50906c4

```text
.ce/changelog/ce598-central-env-scrub.md
.ce/pr-manifests/ce598-central-env-scrub.md
validators/creator_engine_validator/forge/credential_runner.py
validators/creator_engine_validator/github_child_env.py
validators/creator_engine_validator/ticket_reconcile_feed.py
validators/tests/unit/test_credential_runner.py
validators/tests/unit/test_github_child_env.py
validators/tests/unit/test_ticket_reconcile_feed.py
```
