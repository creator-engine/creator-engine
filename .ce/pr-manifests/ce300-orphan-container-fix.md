# PR path manifest - ce300-orphan-container-fix

Issue: ce-ops#300
Kind: story
- **Declared work class:** story

## Scope

- **`.ce/changelog/ce300-orphan-container-fix.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce300-orphan-container-fix.md`** *(A)* - this closed path-set carrier.
- **`deploy/vps-runsc/README.md`** *(M)* - documents the exact-name launch guard and stopped-container prune cron.
- **`deploy/vps-runsc/ce-docker-prune.cron`** *(A)* - host cron artifact for stopped-container pruning with a 24h grace.
- **`deploy/vps-runsc/run-vps-runsc.sh`** *(M)* - removes the exact named detached seat container immediately before relaunch.
- **`playbooks/controller/harness.md`** *(M)* - records the internal live-container probe rule.

## Authorized paths

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=3c55e25be182f56f0fd83c6413489ea081a6be6b465d65e9519efd9ed9b78cdd

```text
.ce/changelog/ce300-orphan-container-fix.md
.ce/pr-manifests/ce300-orphan-container-fix.md
deploy/vps-runsc/README.md
deploy/vps-runsc/ce-docker-prune.cron
deploy/vps-runsc/run-vps-runsc.sh
playbooks/controller/harness.md
```
