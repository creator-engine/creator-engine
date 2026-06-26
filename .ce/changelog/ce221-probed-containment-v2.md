---
slug: ce221-probed-containment-v2
date: 2026-06-26
kind: fixed
scope: validators launch/runtime containment proof
issue: ce-ops#221
---

**Probe contained launch with launch-owned gVisor proof.**

- Require contained runtime launches to carry a launch-owned probe contract before /proc containment proof is accepted.
- Bind gVisor Docker runs to a stable CE-owned name and labels, then derive the live runtime probe PID from docker inspect.
- Normalize OpenShell host FS-mediation refusal to the runtime backend error contract so the suite remains host-portable.
- Cover absent, mismatched, non-launch-owned, and inspect-derived probe paths in unit tests.
