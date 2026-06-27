---
slug: ce-326-onboard-os-native-default
date: 2026-06-27
kind: fix
scope: onboarding isolation backend default
issue: ce-ops#326
---

**Default no-profile onboarding to the unprivileged os-native backend.**

Onboarding now treats an omitted profile as the solo-pilot journey, resolving to
`os-native` while preserving the runtime-policy resolver's schema-level
`gvisor-proxy` default. The CLI and apply path share the onboarding-specific
resolver, the dry-run output records the selected backend, and regression tests
cover no-profile planning/apply behavior plus explicit team/gvisor-proxy paths.
