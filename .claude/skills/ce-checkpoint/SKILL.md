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
2. Put only labeled, redaction-safe facts in a JSON document conforming to
   `validators/creator_engine_validator/schemas/checkpoint-input.schema.yaml`.
3. Invoke `ce checkpoint --facts <facts.json> --clean-boundary <reason>` and
   retain its terminal `path`, `sha256`, and `complete` result. Add
   `--prior-checkpoint <path>` only to record a known predecessor; the verb
   does not read ambient controller state.
4. The caller may consider `/clear` only after independently verifying the
   persisted-byte hash and terminal green completeness result. The verb never
   performs or claims `/clear`.

This skill carries no authority and grants no gate. Any forge mutation still
rides on CE's `PreToolUse` hook-check seam. Do not embed forge commands here.

## Resume side

Writing a checkpoint is only half of this skill's lifecycle. Resuming from
one — after a fresh boot, `/clear`, relaunch, or handoff — carries a
symmetric obligation: re-derive every pin the resume-state record claims
against a live, durable source before any binding act, per
`docs/operations/BOOT_TIME_PIN_REDERIVATION_PROTOCOL.md`. Do not treat the
checkpoint's `probed`/`asserted`/`unknown` labels, or the checkpoint step 5
resume procedure in `playbooks/controller/briefs/checkpoint.md`, as a
substitute for that live re-derivation — a mismatch between the record and
the live derivation is a STOP, not a note-to-self.
