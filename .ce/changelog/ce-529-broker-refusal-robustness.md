---
slug: ce-529-broker-refusal-robustness
date: 2026-07-10
kind: fixed
scope: egress broker
---

**Keep the SELF-PUSH broker available after request failures.**

- Convert normal push guard denials into audited broker refusals.
- Return structured internal-error responses for forge failures and keep accepting later requests.
- Tolerate clients that disconnect while a request is being received.
