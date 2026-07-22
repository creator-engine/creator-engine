---
name: "ce-harvest"
description: "Harvest-sequence assertion: verify READY-FOR-HARVEST and committed head, collect changelogs and carrier, then STOP. Internal controller ergonomics only. Use when the controller is about to harvest a seat's completed work."
argument-hint: "Optional branch slug or seat name"
ce-internal: true
ce-skill-class: "action"
ce-mutating: false
user-invocable: true
disable-model-invocation: false
---

> INTERNAL controller ergonomics. This skill is a **thin pointer** into the
> in-tree harvest SSOT - it does **not** restate the procedure. The action
> SSOT is the brief in-tree; this skill only removes rediscovery friction.

## SSOT

- Procedure SSOT (in-tree): `playbooks/controller/briefs/harvest.md`
- Validation doctrine: pushed current-head SHA plus the required Validate run
  URL/status for that exact head, independent review, and ratification.
- Carrier mechanic: `carrier_gen` API (`write_carriers(base="origin/main")`) -
  never hand-list filenames ([[ce-pr-path-manifest-carrier-required]]).

## What to do

1. Read `playbooks/controller/briefs/harvest.md` and follow it verbatim. It is
   the source of truth for the harvest sequence.
2. Verify the READY-FOR-HARVEST signal + commit SHA from the seat before starting.
   Admit test-bearing seals only when the SSOT's structured base/prior-head RED
   and post-change GREEN evidence is present; retain a deficient seal as
   flagged/not-ready rather than treating it as harvest evidence.
3. Harvest to staging, collect `.ce/changelog/<slug>.md`, regenerate the PR
   manifest via the `carrier_gen` API, and commit the complete carrier set.
4. Push that final committed head and open or update the delivery PR. Wait for
   the required Validate result bound to that exact head. Do not use a local
   full-suite transcript as gate evidence.
5. Enqueue for merge only after independent review, green required checks, and ratification. The
   controller never self-merges authored work.

This skill carries no authority and grants no gate. Governance rides on CE's
`PreToolUse` hook-check seam, never on this skill.
