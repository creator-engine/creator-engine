---
slug: ce-n15b-composition-probe
date: 2026-07-10
kind: added
scope: validation composition detection
issue: N-15b
---

**Add a detection-only composition probe for representative changes against the current main tip.**

- Validate a real hook-free, unsigned composed commit against its exact immutable main parent.
- Retry from a standalone no-hardlink local clone so Git common state cannot contaminate classification.
- Sanitize every Git subprocess environment and disable hooks so ambient Git state cannot redirect composition.
- Run nested validation in that same scrubbed environment and report only validations that actually ran.
- Fail closed with bounded primary and cleanup evidence unless Git and filesystem cleanup verifies.
- Preserve merge-conflict classification on retries and suppress incidents whenever cleanup fails.
- Validate request shape before side effects and bound/redact validator and incident evidence.
- Return validator and optional incident-sink failures without misclassifying them as merge aborts.
- **Declared work class:** S
