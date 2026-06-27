---
slug: ce-302-broker-namespace
date: 2026-06-27
kind: fixed
scope: egress broker / policy / self-push
issue: ce-ops#302
---

**The egress broker's configured `ce` namespace is now digit-anchored to CE
ticket branches (`ceNNN-*` and `ce-NNN-*`) instead of a broad `startswith`
prefix, and self-push refusal handling no longer carries an unreachable daemon
exception path.**

- **Declared work class:** tiny

- `tools/egress-broker/egress_broker/policy.py` treats the `ce` namespace as a
  CE-ticket namespace, denying lookalikes such as `central-banking`,
  `certbot-renew`, `ceasefire`, and bare `ce` while allowing both dash and
  non-dash ticket branch forms.
- `tools/egress-broker/apps.example.json` removes the broad `ce-` fallback from
  the example namespace lists so the example relies on the digit-anchored
  policy behavior for CE ticket branches.
- `tools/egress-broker/ce_egress_self_push_broker.py` removes the unreachable
  `EgressRefused` process-boundary handler; the host broker serializes refusals
  into the JSON socket response.
