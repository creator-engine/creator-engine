# SEED BRIEF — CE Orchestrator Agent: ground-up research + design (DESIGN-ONLY lane)

**Seat:** dev-1 (non-contained, broad read + web). **Role:** architect/research. **Design-only — produce artifacts, NO product code in this lane.**

## Why
The "CE Orchestrator" role — coordination, supervision, and management of the dev fleet — is currently performed AD-HOC by CE-DEV-2 (the live controller), stitched together from memory + resume-state checkpoints + playbooks. It has never been formally DEFINED, CODIFIED, or CANONIZED. It is also a first-class PRODUCT direction (CE's future Orchestrator Agent). This lane designs it from the ground up.

## Deliverable
A design doc at `docs/design/ce-orchestrator-agent.md` (or `.ce/state/research/` first if you prefer a draft) + a proposed ce-ops EPIC with sliced tickets. Cover:
1. **Role definition** — the orchestrator's responsibilities: intake → territory-map → dispatch (born-foreman fan-out, no seat idle) → progress/stall watch → harvest → independent review → gate/merge → conveyor next lane; checkpointing; surfacing decisions to the Operator.
2. **Decision model** — what it decides autonomously vs escalates (Operator decisions, R-reserved/HALT).
3. **Authority model** — gate-holding; the G1–G5 grants + R-reserved reserves; how authority is substrate-independent (see ADR-0013 draft `.ce/state/research/ADR_DRAFT_substrate_independent_authority_20260628.md` / ce-ops#348).
4. **Worker/seat model it drives** — the 4 governed roles, model/effort routing, contained vs non-contained seats, harvest mechanics.
5. **Knowledge substrate** — how it loads its operating knowledge deterministically (the controller-bootstrap overlay, ce-ops#344; the skills ce-dispatch/ce-harvest, ce-ops#344 slice 3) rather than by recall.
6. **Cadence** — the harvest-monitor loop + crons.
7. **Composition with CEO-mode / strangeLoop** (ce-ops#6) and the company brain (recall for orchestration knowledge).
8. **Productization path** — how this graduates from CE-DEV-2's ad-hoc behavior into a shippable, governed Orchestrator Agent.

## Where to look (ground it in the ACTUAL current practice)
- The resume-state checkpoints `.ce/state/research/RESUME_STATE_CE_DEV2_*` (they ENCODE the piecemeal practice — mine the disciplines + mechanics from them).
- `docs/design/controller-bootstrap-ssot.json` + `scripts/gen-controller-bootstrap.py` (ce-ops#344 overlay — the codified-knowledge seam).
- `.claude/skills/ce-dispatch/` (+ ce-harvest once slice 3 lands); `playbooks/controller/`.
- `.ce/state/research/PETER_STEINBERGER_AUTONOMY_ANALYSIS_20260627.md` (autonomy direction).
- The 4 worker roles in `.claude/agents/`.
- Ground research in CURRENT-date actual sources where you use web (agent-orchestration patterns), not pre-training.

## DoD / stop-line
Design doc + ce-ops epic proposal (titles + sliced scope) reported back. NO code changes. If you find the role is already partly codified somewhere, note it + build on it (don't duplicate). Report READY (design doc path + the proposed epic/slices) — controller reviews + files the epic.
