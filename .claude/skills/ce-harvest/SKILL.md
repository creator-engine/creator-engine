---
name: "ce-harvest"
description: "Harvest-sequence assertion: verify READY-FOR-HARVEST signal, confirm preflight GREEN, collect changelogs and carrier, then STOP. Internal controller ergonomics only. Use when the controller is about to harvest a seat's completed work."
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
- Preflight doctrine: `scripts/ce-preflight.sh` or `ce validate-pr`; GREEN
  one-pass required ([[ce-run-full-preflight-before-push]]).
- Carrier mechanic: `carrier_gen` API (`write_carriers(base="origin/main")`) -
  never hand-list filenames ([[ce-pr-path-manifest-carrier-required]]).

## What to do

1. Read `playbooks/controller/briefs/harvest.md` and follow it verbatim. It is
   the source of truth for the harvest sequence.
2. Verify the READY-FOR-HARVEST signal + commit SHA from the seat before starting.
3. Run `ce validate-pr` (or `scripts/ce-preflight.sh`) on the branch and confirm
   GREEN before any staging or PR action.
4. Collect `.ce/changelog/<slug>.md` and regenerate the PR manifest via the
   `carrier_gen` API.
5. Enqueue for merge only after independent review and green required checks. The
   controller never self-merges authored work.

This skill carries no authority and grants no gate. Governance rides on CE's
`PreToolUse` hook-check seam, never on this skill.
