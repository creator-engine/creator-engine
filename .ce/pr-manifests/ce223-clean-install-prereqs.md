# PR path manifest — 223 · clean-room install auto-provisions or remediates missing prereqs

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs `verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref ce223-clean-install-prereqs` and requires this PR's `origin/main..HEAD` diff to equal exactly the authorized path-set below (the carrier lists itself).

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=9ab7a54041a515b3dd927f8bb6b4acada03d6b041253b1e4eeef10ff06307203

```text
.ce/changelog/ce223-clean-install-prereqs.md
.ce/pr-manifests/ce223-clean-install-prereqs.md
docs/install.sh
validators/creator_engine_validator/bootstrap_runtime.py
validators/creator_engine_validator/install_prereqs.py
validators/tests/integration/test_install_bootstrap.py
validators/tests/unit/test_install_prereqs.py
```
