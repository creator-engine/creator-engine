---
slug: ce-workclass-xsml
date: 2026-06-30
kind: changed
scope: work-sizing validator vocabulary
issue: L10
---

**Migrate work-class vocabulary to XS/S/M/L.**

- **Declared work class:** XS
- Renamed canonical work-class vocabulary from tiny/story/feature/epic to XS/S/M/L without changing included-diff-LOC thresholds.
- Preserved legacy PR-body and gate aliases for the migration window.
- Updated validator tests, docs, templates, brain assertions, and generated references for the canonical labels.
