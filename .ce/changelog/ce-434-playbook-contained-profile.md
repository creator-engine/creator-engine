---
slug: ce-434-playbook-contained-profile
date: 2026-07-05
kind: changed
scope: controller dispatch playbook
issue: ce-434
---

Document the contained-seat validation profile in the dispatch playbook.

- Contained seats whose carrier is generated harvest-side now get the real
  command: `ce validate-pr --profile contained-seat`.
- The directive describes the profile as the full suite minus the harvest-side
  carrier gate, with the contained-seat carrier notice printed.
- Non-contained seats and harvest/controller runs remain on full
  `ce validate-pr`; the ce-ops#303 preflight bar is unchanged.
