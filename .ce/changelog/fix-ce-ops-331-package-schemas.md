---
slug: fix-ce-ops-331-package-schemas
date: 2026-06-27
kind: fix
scope: schema packaging — ship schemas/ inside the validator wheel
issue: ce-ops#331
---

**package schemas/ into the wheel so installed CLIs resolve them.**

CE's installed wheel shipped ZERO schema files: schemas/ lived at the repo root, above the validators/ build root, with no package-data, so it was outside the wheel tree and every schema-validating CLI crashed in an installed environment. The schema files now live inside the package (creator_engine_validator/schemas/) and ship via package-data; a repo-root schemas symlink keeps repo-root-relative tooling unchanged; and schema._resolve_schema_path anchors to the packaged dir so the schemas/... constants resolve in both a source tree and an installed wheel.
