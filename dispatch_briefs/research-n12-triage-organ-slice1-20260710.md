# RESEARCH DISPATCH — N-12 triage agent-organ slice 1 — 2026-07-10

Role: governed `architect_research` worker under `.claude/agents/architect_research.md`.
This is read-only research. Return findings only; make no repository, forge, host, queue,
credential, PR, or runtime mutation.

## Objective

Produce a novelty and seam audit for the smallest genuine N-12 slice 1 implementation:
seat-filed bug/feature triage judgment riding an existing deterministic belt feed, with
advisory-only structured output and deterministic disposal. The implementation mandate is
ratified by the strangeLoop supplement/night-3 mandate; it must preserve the daemon-vs-agent
four-invariant boundary and route the organ execution to `gpt-5.6-luna`.

## Required reads

- `.ce/state/research/ARC_STRANGELOOP2_SUPPLEMENT_RATIFIED_20260710.md`, N-12 and sequencing.
- `.ce/state/research/ARC_STRANGELOOP_NIGHT3_MANDATE_20260710.md`, L4 and hard stops.
- `.ce/state/research/MODEL_ROUTING_GPT56_RATIFIED_20260710.md`.
- `docs/design/daemon-vs-agent-rubric.md`, especially four invariants and S2.
- Current deterministic triage/belt/intake implementations and tests, including
  `ce_ops_triage_queue.py`, `forge_triage.py`, `forge/integrator_belt.py`,
  `conveyor_intake_queue.py`, `pickup_payload_schema.py`, and relevant CLI/tests.
- Git history for those paths sufficient to distinguish already-landed work from a real gap.

## Questions

1. What exact capability is absent today, and what already-landed code must be reused rather
   than duplicated?
2. What is the narrowest slice that proves all four agent-organ invariants without deploying a
   daemon, changing authority, writing labels, or embedding credentials?
3. Name the exact proposed file territory, public data schemas/API seams, deterministic trigger,
   trusted-ref policy-digest binding, luna/token-budget contract, proposal format, and disposer
   behavior.
4. Give an offline-focused test matrix including adversarial issue text, malformed model output,
   untrusted candidate policy, budget overflow, duplicate activation/idempotency, and proof of
   zero forge/authority mutation.
5. Identify collisions with every currently queued/in-flight branch visible in claims, briefs,
   and `/var/tmp/pipeline-queue.list`; if the queue file is unavailable, say so.

## Required output

Return a concise evidence-grounded report to the controller: consulted paths/commits, novelty
finding, recommended one-slice contract, exact files/tests, risks/open questions, and a clear
GO/BLOCKED recommendation for an implementer dispatch. Do not write a design file or brief.

