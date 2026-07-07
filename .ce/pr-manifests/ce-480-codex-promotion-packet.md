# PR path manifest — ce-ops#480 · Codex controller promotion evidence packet

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-480-codex-promotion-packet` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=11

AUTHORIZED_PATHS_SHA256=6460323cdaa3aee70aea432abb26e102ca0eee59d9bb5ea154c708aeca77bfef

```text
.ce/changelog/ce-480-codex-promotion-packet.md
.ce/pr-manifests/ce-480-codex-promotion-packet.md
validators/creator_engine_validator/_versions.py
validators/creator_engine_validator/codex_controller_evidence.py
validators/creator_engine_validator/codex_launch_spec.py
validators/creator_engine_validator/launch_runtime.py
validators/creator_engine_validator/takeover_runtime.py
validators/tests/unit/test_ce_takeover_cli.py
validators/tests/unit/test_codex_controller_evidence.py
validators/tests/unit/test_launch_runtime.py
validators/tests/unit/test_version_boundary.py
```
