# PR path manifest — ce-hermes-retirement

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-hermes-retirement` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** story

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=27

AUTHORIZED_PATHS_SHA256=e8d6a4620afa4542154113ea4f3755a4cf13a99c13be54063dba61ea4de561ca

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-hermes-retirement.md
.ce/pr-manifests/ce-hermes-retirement.md
.ce/reference/cli.generated.md
.claude/hooks/ce-hook-common.sh
.claude/hooks/ce-pretooluse.sh
.claude/hooks/ce-stop.sh
.gitignore
CONTRIBUTING.md
deploy/dgx-runsc/run-codex-runsc.sh
deploy/vps-runsc/run-vps-runsc.sh
docs/architecture/agent-interaction-model.md
docs/architecture/parallel-controller-orchestration.md
docs/contracts/forge-claim.md
docs/contracts/v3-naming-hygiene.md
docs/decisions/0005-openbao-secret-identity-backend.md
docs/delivery/NEXT_TASK_PROTOCOL.md
docs/delivery/WORKTREE_RUNTIME_PROTOCOL.md
docs/operations/CLAUDE_CODE_HOOK_PACK.md
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/ce_onboard.py
validators/tests/integration/test_claude_hook_pack_stop.py
validators/tests/unit/test_ce_brain_drift.py
validators/tests/unit/test_ce_onboard.py
validators/tests/unit/test_ce_onboard_cli.py
validators/tests/unit/test_dgx_runsc.py
validators/tests/unit/test_vps_runsc_launcher.py
```
