---
name: "ce-dispatch"
description: "Compose a governed-seat dispatch brief (ticket, branch, role, allowed paths/surfaces, expected evidence, stop line) and record the work claim. Internal controller ergonomics only. Use when the controller is about to hand a unit of work to a worker seat."
argument-hint: "Optional ticket/branch/role hints for the brief"
ce-internal: true
ce-skill-class: "action"
ce-mutating: false
user-invocable: true
disable-model-invocation: false
---

> INTERNAL controller ergonomics. This skill is a **thin pointer** into the
> in-tree dispatch SSOT — it does **not** restate the procedure. The action
> SSOT is the brief in-tree; this skill only removes rediscovery friction.

## SSOT

- Procedure SSOT (in-tree): `playbooks/controller/briefs/dispatch.md`
- Mechanic SSOT (memory doctrine): the pointer + SHA dispatch mechanic
  [[ce-seat-dispatch-prompt-pointer-sha]] — save the seed brief to a file, then
  send the worker a short pointer plus its `sha256`, never a long inline prompt.

## What to do

1. Read `playbooks/controller/briefs/dispatch.md` and follow it verbatim. It is
   the source of truth for what a dispatch brief must name.
   In particular, classify every unit as test-bearing or non-test-bearing; for
   test-bearing units the SSOT requires exact node IDs plus base/prior-head RED
   output before post-change GREEN can count as build evidence.
2. Apply the pointer + SHA mechanic per [[ce-seat-dispatch-prompt-pointer-sha]]:
   write the seed brief to a file, compute its `sha256sum`, and send the worker
   only the file pointer and the hash.
3. **REQUIRED territory-check (hard stop before dispatch):** Check the live
   in-flight territory map per [[ce-dispatch-territory-map-before-dispatch]].
   Inspect ALL of: `.ce/pr-manifests/` (open carrier slugs), `.ce/briefs/`
   (active briefs), `git worktree list` output (live worktree branches), and
   `.ce/wt-*/` staging directories. Intersect EVERY candidate path against ALL
   in-flight files. If any path collision is found, do not dispatch; report the
   collision to the controller and stop.
4. Record or verify the work claim before the target seat starts.

This skill carries no authority and grants no gate. Any forge mutation that a
dispatch produces still rides on CE's `PreToolUse` hook-check seam. Do not embed
forge commands here.
