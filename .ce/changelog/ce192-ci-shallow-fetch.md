---
slug: ce192-ci-shallow-fetch
date: 2026-06-22
kind: fixed
scope: validate workflow live-base fetch
issue: ce-ops#192
---

Fixes the Validate workflow's intermittent live-base shallow-fetch failure.

- Adds a bounded retry around the `Resolve live comparison base` Git fetches
  when Git reports `shallow file has changed since we read it`.
- Keeps the checkout depth unchanged and preserves the packaging contract by
  avoiding a global full-history checkout.
