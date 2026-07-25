# PR path manifest — ce643-installer-helper-dedupe

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI requires the `base..HEAD` diff to equal
exactly the paths below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

Base: `c245fa6c3ee334d3284f05b067a8e9f700324f14` (`origin/main` at branch
handoff).

- **Declared work class:** S

Scope: deduplicate the signed-release and main-HEAD venv installer mechanics,
then re-verify `cev3 --help` through the promoted live symlink before either
route records install state.

AUTHORIZED_PATHS_COUNT=8

AUTHORIZED_PATHS_SHA256=832eb72e3e83672596aeb31051a28b9dc06de2227336f5599fa64f8028122d80

```text
.ce/changelog/ce643-installer-helper-dedupe.md
.ce/pr-manifests/ce643-installer-helper-dedupe.md
validators/creator_engine_validator/main_head_install.py
validators/creator_engine_validator/update.py
validators/creator_engine_validator/venv_install_common.py
validators/tests/unit/test_ce_update.py
validators/tests/unit/test_main_head_install.py
validators/tests/unit/test_venv_install_common.py
```
