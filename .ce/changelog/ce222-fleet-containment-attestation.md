---
slug: ce222-fleet-containment-attestation
date: 2026-06-23
kind: added
scope: fleet containment attestation
issue: ce-ops#222
work_class: story
---

Adds `ce containment-status` for fleet-wide probe-derived seat containment
status, and extends `ce containment-probe --json` with Herdr liveness and
Ring-1 enforcement evidence. Unprobeable seats fail closed as uncontained.
