---
slug: ce-489-brain-init-refusal-teaches
date: 2026-07-06
kind: fix
scope: onboard / launch
issue: ce-ops#489
---

**Brain genesis is part of onboard apply.**

- `ce onboard --apply` now emits the same genesis brain assertion ledger that `ce brain init` creates, so a freshly onboarded tenant has `.ce/state/brain/assertions.yaml` before launch.
- `G6-LAUNCH-BRAIN-BOOTSTRAP-REFUSED` now names the exact recovery command: `ce brain init`.
- Added regression coverage for fresh onboard brain bootstrap readiness, exact refusal recovery text, and re-apply idempotency without clobbering an existing ledger.
