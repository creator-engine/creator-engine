---
slug: ce215-seat-ceops-readonly
date: 2026-06-24
kind: added
scope: seat ce-ops read-only checkout
issue: ce-ops#215
work_class: story
---

Adds a host-side `tools/provision-ce-ops-readonly.sh` helper that idempotently
clones or fast-forwards a local read-only `ce-ops` checkout, disables push URLs,
and documents `ce-ops:<relative-path>` brief references for private design and
mandate artifacts.
