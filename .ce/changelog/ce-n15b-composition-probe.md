---
slug: ce-n15b-composition-probe
date: 2026-07-10
kind: added
scope: validation composition detection
issue: N-15b
---

**Add a detection-only composition probe for representative changes against the current main tip.**

- Validate a real hook-free, unsigned composed commit against its exact immutable main parent.
- Retry from a separately owned worktree so validator state cannot contaminate classification.
- Validate request shape before side effects and bound/redact validator and incident evidence.
- Return validator and optional incident-sink failures without misclassifying them as merge aborts.
- **Declared work class:** S
