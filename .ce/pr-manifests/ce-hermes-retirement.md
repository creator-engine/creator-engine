# PR path manifest — ce-hermes-retirement

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-hermes-retirement` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

- **Declared work class:** S

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=21

AUTHORIZED_PATHS_SHA256=e784d9ce315651a151d97c4b9112b4a20b604eaa8937a5b07e8aaf96859ce28f

```text
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
validators/creator_engine_validator/ce_cli.py
validators/creator_engine_validator/ce_onboard.py
validators/tests/unit/test_ce_onboard.py
validators/tests/unit/test_ce_onboard_cli.py
```
