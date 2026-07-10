---
claim_id: ce-497-controller-state-sync-s1
ticket: ce-497
slice: controller-state-sync-s1
branch: ce-497-controller-state-sync-s1
seat: dev-3
size: S
units: 1
priority: TOP
status: DISPATCHED
brief: .ce/briefs/BRIEF_dev3_controller_state_sync_20260709.md
grounded_on: origin/main@6ffd0fe19b8169d6b50a905e2de4ee4c92ea65d8
claimed_at: 2026-07-09
---

# Claim: ce-497-controller-state-sync-s1

Dispatched to dev-3 (ce-dgx-codex, contained, commit-only).

## Territory

```
tools/controller/state_sync.py
validators/tests/unit/test_controller_state_sync.py
.ce/changelog/ce-497-controller-state-sync-s1.md
.ce/pr-manifests/ce-497-controller-state-sync-s1.md
```

## Context

Slice 1 of the controller state sync program (parent: controller parity program,
ce-496). Delivers the snapshot tool that collects controller data classes (b) arc
state, (c) dispatch state, and optionally (a) memory into a structured output
directory with a manifest (sha256s, source host, timestamp, restore instructions).
Dry-run default. Hard denylist for secrets (*.pat, *.pem, *.pass, *.key,
.ce-keys/*) is test-pinned. No live push in slice 1.

## Frozen paths (do not touch)

- `.ce/brain/assertions.yaml` (FROZEN)
- `validators/creator_engine_validator/ce_cli.py` (PR #918)
- `validators/creator_engine_validator/continuity_drill_runtime.py` (PR #920)
- `tools/mint-forge-token.py` (PR #920)

## Acceptance

- `PYTHONPATH=validators .venv/bin/python -m pytest validators/tests/unit/test_controller_state_sync.py -v` → GREEN
- `validate-pr --declared-work-class S` → PASS
- Denylist tests pass (pat/pem/pass/key/ce-keys all excluded, recorded in denied_paths)
- Dry-run writes nothing
