# PR path manifest — spec-kit retirement · Retire .specify/ tree except constitution (Phase 2 of spec-kit retirement)

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-speckit-retire-specify` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=39

AUTHORIZED_PATHS_SHA256=615b06e3428a5913b0a0ef1e20673471194f8a6f51ec5b30fa43673a1796e018

```text
.ce/changelog/ce-speckit-retire-specify.md
.ce/pr-manifests/ce-speckit-retire-specify.md
.specify/extensions.yml
.specify/extensions/.registry
.specify/extensions/git/README.md
.specify/extensions/git/commands/speckit.git.commit.md
.specify/extensions/git/commands/speckit.git.feature.md
.specify/extensions/git/commands/speckit.git.initialize.md
.specify/extensions/git/commands/speckit.git.remote.md
.specify/extensions/git/commands/speckit.git.validate.md
.specify/extensions/git/config-template.yml
.specify/extensions/git/extension.yml
.specify/extensions/git/git-config.yml
.specify/extensions/git/scripts/bash/auto-commit.sh
.specify/extensions/git/scripts/bash/create-new-feature.sh
.specify/extensions/git/scripts/bash/git-common.sh
.specify/extensions/git/scripts/bash/initialize-repo.sh
.specify/extensions/git/scripts/powershell/auto-commit.ps1
.specify/extensions/git/scripts/powershell/create-new-feature.ps1
.specify/extensions/git/scripts/powershell/git-common.ps1
.specify/extensions/git/scripts/powershell/initialize-repo.ps1
.specify/feature.json
.specify/init-options.json
.specify/integration.json
.specify/integrations/claude.manifest.json
.specify/integrations/codex.manifest.json
.specify/integrations/speckit.manifest.json
.specify/scripts/bash/check-prerequisites.sh
.specify/scripts/bash/common.sh
.specify/scripts/bash/create-new-feature.sh
.specify/scripts/bash/setup-plan.sh
.specify/scripts/bash/setup-tasks.sh
.specify/templates/checklist-template.md
.specify/templates/constitution-template.md
.specify/templates/plan-template.md
.specify/templates/spec-template.md
.specify/templates/tasks-template.md
.specify/workflows/speckit/workflow.yml
.specify/workflows/workflow-registry.json
```
