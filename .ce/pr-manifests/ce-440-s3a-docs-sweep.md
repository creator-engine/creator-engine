# PR path manifest — ce-ops#440 · Docs sweep to the unified ce command surface

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed authorized path-set for this PR. CI runs `verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests --head-ref ce-440-s3a-docs-sweep` and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below; this carrier lists itself.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=22

AUTHORIZED_PATHS_SHA256=b038f0624bffaba2b7022be1538a7dcc78873a9574e53a48461df1d463d2aac6

```text
.ce/brain/assertions.yaml
.ce/changelog/ce-440-s3a-docs-sweep.md
.ce/pr-manifests/ce-440-s3a-docs-sweep.md
README.md
docs/architecture/cockpit.md
docs/architecture/session-status-line.md
docs/architecture/tasks-handoff-contract.md
docs/architecture/work-claim-locks.md
docs/contracts/installer.md
docs/guide/first-value-mythos.md
docs/guide/onboarding-macos-container.md
docs/guide/pilot-runbook.html
docs/guide/pilot-runbook.md
docs/guide/solo-dev-onboarding.md
docs/guide/zero-to-governed-seat-quickstart.md
docs/llms-install.md
docs/operations/AGENT_NATIVE_BOOTSTRAP.md
docs/operations/GITHUB_NATIVE_COORDINATION_PROTOCOL.md
docs/operations/GREENFIELD_FIRST_PROJECT_PROTOCOL.md
docs/operations/INSTALLED_CE_DOGFOOD_MIGRATION.md
docs/operations/SEAT_REAPER_PROTOCOL.md
playbooks/controller/runbooks/arad-pilot.md
```
