---
slug: ce-automerge-kill-switch-cli
date: 2026-07-01
kind: added
scope: forge autonomy
issue: L2 auto-merge P1
---

**Automerge kill-switch CLI.**

- **Declared work class:** S
- Added `ce automerge-kill-switch status|on|off` over the durable live-policy state store.
- Classified the governed operator kill switch as internal-only while keeping CLI inventory guards explicit.
- Preserved actuator gate behavior while adding fail-closed operator fallback guidance for failed disarm writes.
