# PR path manifest — ce-ops#328 · brownfield onboard --apply forge-identity resolution

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized
path-set for this PR. CI requires this PR's `base..HEAD` diff to equal exactly the
authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Fixes the brownfield `onboard --apply` hard blocker: the adoption path skipped
`github_bootstrap_token_probe` (the only leg that resolves the forge actor identity via
`GET /user`), yet `brownfield_build_scaffold` hard-requires that identity — so every solo
brownfield adoption `--apply` refused with `forge_identity_unresolved`. The probe is now
run (right-sized to identity-only for `mode != "new"` per ce-ops#94, requiring no write
scopes) in adoption mode so the identity is resolved before `build_scaffold`.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=a95014ff023ecda032c0ac022c6149a0f6587b93dbfffffc040757a45b2c2786

```text
.ce/changelog/fix-ce-ops-328-brownfield-forge-identity.md
.ce/pr-manifests/fix-ce-ops-328-brownfield-forge-identity.md
validators/creator_engine_validator/onboard_apply.py
validators/tests/unit/test_onboard_apply.py
```
