---
slug: ce-585-strategy-epoch
date: 2026-07-17
declared_work_class: story
---

# PR path manifest - CI strategy epoch clarification

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path set for this documentation correction. It lists itself and
declares the canonical work class `story`.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=79cc3a8dc2eebc7f314e25081943cfbfeebdcd3e847ac901af3a888ba97f2888

```text
.ce/changelog/ce-585-strategy-epoch.md
.ce/pr-manifests/ce-585-strategy-epoch.md
docs/architecture/integration-map.md
docs/devops/CI_CD_STRATEGY.md
docs/quality/TESTING_STRATEGY.md
specs/002-canonical-docs-and-operating-model/spec.md
```
