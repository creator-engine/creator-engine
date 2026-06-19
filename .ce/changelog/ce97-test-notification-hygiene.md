---
slug: ce97-test-notification-hygiene
date: 2026-06-19
kind: fixed
scope: validator integration tests
issue: ce-ops#97
base: d2d22b0e3a52a551ec8fbc79571ab3e806353b40
---

Prevents resource-bound live integration tests from leaking OOM/application
stopped notifications to interactive dogfood desktops.

- Gates the live `systemd-run` resource-bound proof behind `CI=1` or
  `CE_RUN_RESOURCE_BOUND_SYSTEMD_TESTS=1` on a non-desktop host.
- Refuses the live OOM/systemd tests whenever desktop session environment
  variables are present, while keeping pure tests and recorded evidence as the
  ordinary local coverage path.
- Adds regression coverage for the notification-hygiene gate.
