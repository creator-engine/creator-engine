# SOURCE MATERIAL — "Your day-to-day with Creator Engine" welcome-package page
# (Controller-approved substance, 2026-07-03. To be rewritten product-lens for the
# package: NO ce-ops refs, NO internal fleet/seat jargon, second person, her config:
# Solo/CEO mode · one machine · Claude Code · shared org repo chmod735-dor/mythos.)

## Starting work
Terminal-first: `ce launch` inside ~/ce-mythos/mythos starts Claude Code inside CE's
governed harness. Governance is an invisible engine: tool-call-level policy hooks +
session-enforced branch/PR discipline. She never babysits rules; the machine holds them.

## The loop with her PRD
PRD → spec → implementation plan (she is here now, with Claude Code) → bounded work
units. Each unit = its own branch + PR carrying machine obligations produced by the
agent and verified by gates:
- exactly one declared work-class line (XS/S/M/L, checked against actual diff size)
- path manifest (what the change is allowed to touch)
- changelog fragment
- green `ce validate-pr` preflight before push
"Grader outside the agent": the agent produces, independent machinery verifies.

## Review and merge — CEO mode
- Author≠approver enforced mechanically; implementing agent never approves its own work;
  fresh-context review produces the verdict.
- Classes inside her ratified envelope auto-merge with an audit trail; everything else
  queues for HER press. Her involvement compresses to: FRAME (specs) · SHAPE (ratify
  plans/envelopes) · PRESS (gated merges).
- Constitution ratification is her first governed act and hers alone.

## Collaborating with the CE team on mythos
Governance attaches to the REPO (branch protection, required checks, carrier/changelog
gates) — collaborator PRs face the same machine gates hers do. Identities stay distinct
so cross-review works. TO COVER EXPLICITLY (gap flagged in audit): operating rhythm for
two parties — who reviews whom, whose envelope governs an auto-merge, what she does when
a collaborator PR sits in her merge queue.

## Session-prep facts to weave in where useful (verified 2026-07-03)
- Install is signed end-to-end (spec + trust root + wheelhouse); canary GREEN on 0.3.1.
- Her config plans NO sudo (solo profile → user-space backend); two human moments remain:
  approving anything the installer asks + the GitHub App authorization click, which must
  target the chmod735-dor ORG (not her personal account).
- Existing clone at ~/ce-mythos/mythos is where onboard runs from.

# PENDING INPUTS before the package page is finalized
1. Doc-audit worker findings (staleness of existing package + what day-to-day content
   already exists vs missing) — worker in flight.
2. Operator decision: does today's session stop at `--plan` or proceed to `--apply`
   (live adoption-write env flags on her laptop)? Page must describe the actual flow.
