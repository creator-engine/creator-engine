# CE v3 — Controller Context-Window Observability

*Design input for G-6/G-7 UX work (GH #157). This note records requirements and
constraints only. It does not specify a v1 behavior change, runtime hook, or
`statusLine` implementation.*

## What this is

Governed Controller seats need an in-session way to see context-window usage and
receive boundary-aware checkpoint / `/clear` nudges before a long gate arc runs
out of usable context. The requirement belongs to the CE product surface, not to
an ad hoc user configuration, because governed seats intentionally run under a
hermetic project settings posture.

This note preserves the observability requirement for future G-6 coordination and
G-7 product-surface design. It is a companion to
[`session-status-line.md`](./session-status-line.md), which records the current
unified session-frame direction, and
[`pilot-uiux-model.md`](./pilot-uiux-model.md), which describes the broader
"your agent, under CE" surface.

## Problem

CE governed Controllers launch with project-scoped settings. In that posture,
user-level agent settings are excluded, so a user-level context `statusLine` or
prompt hook is not loaded by the governed seat.

That is correct for governance: the seat should not depend on ambient user
configuration. It creates a UX gap, though. A Controller can work through many
turns of batch-strict planning, dispatch, triage, and review coordination without
seeing a reliable context-window signal. Silent context growth risks exhaustion
mid-arc, and the assistant should not be treated as the authority for estimating
remaining context.

## Requirements

- Surface the current context-window usage in the governed Controller's normal
  session experience.
- Use the harness-provided `context_window.used_percentage` as the authoritative
  input. Consume that number; do not recompute token usage in CE.
- Provide threshold-based nudges for checkpointing and considering `/clear`:
  warn at `>= 45%`, urgent at `>= 60%`.
- Deliver nudges at turn or batch boundaries, so the surface does not interrupt
  mid-output.
- Make the surface survive the governed `--setting-sources project` posture. A
  design that depends on user-level settings is not sufficient for governed
  Controllers.
- Keep the signal visually compatible with the CE session frame: stage, context,
  and spend are all session resource or health signals and should not compete as
  separate one-off surfaces.

## Non-goals

- No frozen-v1 behavior change.
- No runtime hook, vendored `statusLine` script, prompt hook, or product-code
  implementation in this note.
- No change to the governed project-settings posture.
- No token accounting implementation in CE.

## Deferred Design Questions

- Whether the final surface is a CE-native session renderer, a project-scoped
  agent integration, the web cockpit, or a combination of those surfaces.
- How the context indicator appears alongside spend and workflow stage without
  making the status line noisy.
- How checkpoint affordances should record resumable state before suggesting
  `/clear`.
- How the same requirement should render across Claude Code, Codex, OpenClaw,
  and ACP-backed surfaces when those integrations diverge.

## Prototype Detail To Preserve

A user-level prototype demonstrated the operating model for ungoverned sessions:
the status-line command displayed the harness context percentage and wrote it to
a per-session sentinel; a prompt hook read the sentinel and injected warning or
urgent checkpoint text at the thresholds above.

That prototype is evidence for the thresholds and data source. It is not the
accepted delivery mechanism for governed Controllers, because user-level settings
are deliberately excluded from governed seats.
