---
slug: ce-291-automerge-classifier-dryrun
date: 2026-06-28
kind: added
scope: forge automerge classifier dry-run
issue: ce-ops#291
---

Adds the classify-only automerge dry-run spine for ce-ops#291. The change is
decision-only and ships armed off: it does not approve, merge, enqueue, enable
auto-merge, mint approval markers, or call GitHub mutation paths.

- Adds a config-driven mutation classifier for PR path sets.
- Adds a secret-free durable automerge policy state and structured decision
  emitter under `.ce/state/automerge/decisions/`.
- Adds packaged YAML schemas for policy state/config and decision records.
- Refreshes the generated schema reference for the new automerge schemas.
- Adds focused unit coverage for fail-closed classification, size ceremony
  composition, dev-mode halt, kill switch behavior, dry-run writes, and
  gesture-class blocking even when class flags are enabled.
- Leaves CLI registration and workflow wiring out of scope for the follow-up
  owner; no `ce_cli.py`, `v3_cli.py`, workflow, sizing, or approval wall files
  are edited.

Local dry-run evidence was emitted with an armed test policy
(`run_mode=ceo`, all class flags enabled, green checks) and written under
`.ce/state/automerge/decisions/`, which is ignored by `.gitignore` via
`.ce/state/`.

| PR | Commit | Expected | Actual | Mutation | Size | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| #545 | `26968a9f8e947365d9c8a82a8476e753d82b22d0` | AUTO | AUTO | docs | target_advisory/tiny | `all_auto_guards_passed` |
| #584 | `2b34e39486b7d075913579861ae222e564b4c3a2` | GESTURE | GESTURE | security | warn/story | `gates_not_auto_back_gate_only`, `gesture_class` |
| #546 | `33887a6ff4b87448b6fe978b20cebd8757c47fd1` | GESTURE | GESTURE | schema | warn/story | `gates_not_auto_back_gate_only`, `gesture_class` |
