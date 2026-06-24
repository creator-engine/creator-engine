---
slug: ce221-containment-probe-failclosed
date: 2026-06-24
kind: added
scope: validator runtime (launch/lane) — contained-launch attestation
issue: ce-ops#221
---

**Contained launches are PROBED, not self-reported, and fail closed.** `ce launch` /
`ce lane launch` gVisor visible-runtime launches now probe the launched surface PID before
returning success (`runtime_backend_bridge.py`), carrying the attestation in
`runner_runtime["containment_attestation"]`. If the launch returns no terminal record, no
probeable PID, or the PID probes raw/uncontained, it raises
`RuntimeBackendBridgeError`/`RuntimePolicyRefused` instead of silently running raw. Builds on
ce-ops#222's `/proc`-based containment probe.
