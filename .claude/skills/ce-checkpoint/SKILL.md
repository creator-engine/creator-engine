---
name: ce-checkpoint
description: Create a redaction-safe, durable, resumable controller checkpoint at a clean boundary; use when handing off, pausing, recovering context, or considering /clear.
argument-hint: "Optional prior-checkpoint path or boundary description"
ce-internal: true
ce-skill-class: "action"
ce-mutating: false
user-invocable: true
disable-model-invocation: false
---

> INTERNAL controller ergonomics. This skill is a **thin pointer** into the
> in-tree checkpoint SSOT — it does **not** restate the procedure. The action
> SSOT is the brief in-tree; this skill only removes rediscovery friction.

## SSOT

- Procedure SSOT (in-tree): `playbooks/controller/briefs/checkpoint.md`
- Resume-state doctrine: write one untracked file under `.ce/state/research/`
  named `RESUME_STATE_<UTC timestamp>.md`, verify with `sha256sum`, and record
  the digest before reporting completion.
- Authority-boundary doctrine: a checkpoint never transfers an authority or key;
  escalate `AWAITING-OPERATOR` items rather than treating the checkpoint as
  permission.

## What to do

1. Read `playbooks/controller/briefs/checkpoint.md` and follow it verbatim. It
   is the source of truth for the checkpoint procedure and format.
2. Apply the refuse-unsafe-input rule (no secrets, credentials, raw logs, or
   committed `READY` file) per the brief.
3. Write the `RESUME_STATE_<UTC timestamp>.md` file, run `sha256sum` on it, and
   record the digest before reporting completion.
4. Verify the completeness checklist in the brief before handoff.

This skill carries no authority and grants no gate. Any forge mutation still
rides on CE's `PreToolUse` hook-check seam. Do not embed forge commands here.
