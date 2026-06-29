---
slug: ce-358-installer-trust-fixes
date: 2026-06-29
kind: fixed
scope: installer bootstrap trust boundary
issue: ce-ops#358
---

**Fix installer uv trust boundary.**

- Fetch uv from the signed manifest URL, verify the archive SHA256 before extraction, and install a versioned bootstrap uv binary.
- Persist verified installer inputs under the bootstrap root so the printed onboard plan command remains executable after temp cleanup.
- Cover uv hash mismatch fail-closed behavior and the durable next-step command in installer integration tests.
