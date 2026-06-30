# PR path manifest — ce-ops#197 · ssh-keygen prereq actionable error in verify paths

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-n1d-sshkeygen-preflight` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=10

AUTHORIZED_PATHS_SHA256=6537eac3c8eab0570f2c9db785c3fe77f73470dc726dc3218a87e8994b5bd5a3

```text
.ce/changelog/ce-n1d-sshkeygen-preflight.md
.ce/pr-manifests/ce-n1d-sshkeygen-preflight.md
validators/creator_engine_validator/checks/install_spec_signature_guard.py
validators/creator_engine_validator/install_prereqs.py
validators/creator_engine_validator/update.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_ce_update.py
validators/tests/unit/test_install_prereqs.py
validators/tests/unit/test_install_spec_signature_guard.py
validators/tests/unit/test_v3_cli.py
```
