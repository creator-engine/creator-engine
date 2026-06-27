---
slug: ce293-activate-belt-daemon
date: 2026-06-27
kind: pr-manifest
scope: deploy/systemd
issue: ce-ops#293
work_class: story
---

# PR path manifest - ce-ops#293 - observe-only belt daemon

This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the closed
authorized path-set for this PR. CI runs `verify-path-manifest --base <sha>
--manifest-dir .ce/pr-manifests --head-ref ce293-activate-belt-daemon` and
requires this PR's `base..HEAD` diff to equal exactly the authorized path-set
below; this carrier lists itself.

- **Declared work class:** story

Scope: add the observe-only systemd belt daemon unit, optional label filtering,
installer/docs wiring, focused tests, and run evidence for ce-ops#293.

Canonicalization: `sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=7

AUTHORIZED_PATHS_SHA256=0da7e343bc996a42b5c06d3a2e60103b68390b9a1fd2e90294f3a639eab55868

```text
.ce/changelog/ce293-activate-belt-daemon.md
.ce/pr-manifests/ce293-activate-belt-daemon.md
deploy/systemd/README.md
deploy/systemd/ce-belt-daemon-observed-run.md
deploy/systemd/ce-belt-daemon.service
deploy/systemd/install-gate-daemons-systemd.sh
validators/tests/unit/test_gate_daemons_systemd.py
```
