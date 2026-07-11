---
slug: ce-sl3-ready-attestation-nudge
date: 2026-07-11
kind: added
scope: SL-3 READY validation-attestation reducer
work_class: tiny
---

Adds a pure, injected-facts reducer that proposes pending, SHA-mismatch,
validator-live, green-attested, or failed READY-validation states. It performs
no observation, validation, queue, harvest, process, filesystem, network, or
forge action.
