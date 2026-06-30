---
slug: ce-363-optionc-openshell-egress
date: 2026-06-30
kind: story
scope: validator runner
issue: ce-ops#363
---

**Option C OpenShell egress delegation.**

- Delegate non-empty os-native egress policies to OpenShell when available.
- Fail closed without the ambiguous proxy PATH probe when OpenShell is unavailable.
- Verify OpenShell P3 denied-egress evidence before delegated user commands run.
- No-egress path now fails closed at provision time (previously deferred to run time) — intentional documented change.
- Remove dead native-execution plumbing; Option C delegates and does not execute natively.
