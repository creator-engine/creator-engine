---
claim_id: ce-496-controller-bootstrap-doc-s1
ticket: ce-496
slice: controller-bootstrap-doc-s1
branch: ce-496-controller-bootstrap-doc-s1
seat: dev-1
size: S
units: 1
priority: TOP
status: QUEUED
queue_note: Behind ce-478-posture-banner (in-compose 2026-07-09) + ce-470-infra-identity-schema (PR #925 open)
brief: .ce/briefs/BRIEF_dev1_controller_bootstrap_20260709.md
grounded_on: origin/main@6ffd0fe19b8169d6b50a905e2de4ee4c92ea65d8
claimed_at: 2026-07-09
---

# Claim: ce-496-controller-bootstrap-doc-s1

QUEUED for dev-1 (CE-DEV-1, host, self-push). Do not begin until
ce-478-posture-banner is shipped and ce-470-infra-identity-schema (PR #925)
is merged or this unit is explicitly re-dispatched.

## Territory

```
docs/operations/CONTROLLER_BOOTSTRAP.md
validators/tests/unit/test_controller_bootstrap_paths.py
.ce/changelog/ce-496-controller-bootstrap-doc-s1.md
.ce/pr-manifests/ce-496-controller-bootstrap-doc-s1.md
```

## Context

Slice 1 of the controller parity program (ce-496). Delivers the governed runbook
for spawning a replacement main controller on the VPS when the DGX is unavailable.
Covers: prerequisites, identity hydration from `ce-ops:infra/identity-registry.yaml`,
state hydration from the controller snapshot (ce-497 s1), standby surface
provisioning (provision-standby-surface.sh — dependency on standby surface PR),
harness-agnostic launch via `ce launch`, takeover drill reference, and an explicit
gap list (secrets custody → OpenBao; live sync push → ce-497 s2; identity recall
CLI pending).

Smoke test (`test_controller_bootstrap_paths.py`) gates doc references against
actual repo paths; not-yet-merged dependencies (provision-standby-surface.sh,
tools/controller/state_sync.py) are skipif-guarded so the PR passes on current main.

## Critical PR body obligation

The PR body MUST contain the bolded line:
`**Declared work class: story**`
Dev-1 has omitted this from recent PRs. It is a hard gate requirement.

## Frozen paths (do not touch)

- `.ce/brain/assertions.yaml` (FROZEN)
- `validators/creator_engine_validator/ce_cli.py` (PR #918)
- `docs/operations/CLAUDE_CODE_HOOK_PACK.md` (PR #918)

## Acceptance

- `PYTHONPATH=validators .venv/bin/python -m pytest validators/tests/unit/test_controller_bootstrap_paths.py -v` → all pass (skipif guards on pending-PR paths are SKIPPED, not FAILED)
- `validate-pr --declared-work-class S` → PASS
- `**Declared work class: story**` present and bolded in PR body
- Doc has all 9 sections (0–8) present with matching headings
- Gap list explicitly names: secrets custody / OpenBao, state sync push, identity recall CLI
