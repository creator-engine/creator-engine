# CE Contributor Onboarding — Definitive Plan (2026-06-27)

Produced via grill-me with the Operator. Reusable process for adding a human contributor to CE; instantiated for the first one, **Nitzan94** (human dev, **Claude Code** harness).

## Decisions (resolved with Operator)
- **Q1 — archetype:** Nitzan is a *human developer using Claude Code*, and we deploy **CE in TEAM MODE** for her so she works "like us." This is NOT the contained-codex fleet-seat path; it is the **shipped product path** (human + their coding agent + CE governance) — the cleanest external dogfood of what CE is for.
- **Q2 — gate/authority (hybrid):** **(iii) now → (ii) on graduation.** She gets **write + full review/comment** immediately; **approve-for-merge stays with the gate** (ce-dev-2 / Operator) while she's new; she **graduates to a CODEOWNERS peer human** (satisfying `docs/contracts/peer-authority.md`'s "two distinct humans for privileged decisions") via the existing trust-tier ladder in `docs/guide/contributing-to-ce.md`.
- **ce-ops access:** **(x) day-one READ** (Operator chose full context from day one).

## Two-phase shape: BRIDGE (today) → BUILD (the team-mode deployment)

### BRIDGE — EXECUTED 2026-06-27
Collaborator invitations sent (pending her acceptance):
- `creator-engine/creator-engine` — **write** (invite #323802094)
- `creator-engine/ce-ops` — **read** (invite #323802095)
- `creator-engine/docs` — **write** (#323802096)
- `creator-engine/ce-playbooks` — **write** (#323802097)
- CODEOWNERS unchanged (she is not an approver yet — that's the graduation step). Branch protection (1 required code-owner review + `require_last_push_approval` + merge queue) structurally enforces the hybrid gate: she can push branches + open PRs but cannot self-merge.
- Day-one packet: `CONTRIBUTING.md`, `docs/guide/contributing-to-ce.md` (trust tiers + cycle + DCO), `ce-playbooks`, and a short "how we pick up work / the gate / DCO sign-off" welcome.
- She can be productive *today* with Claude Code via the conventional PR flow while the team-mode deployment is built.

### BUILD — "CE team mode for a human + Claude Code" (the real deliverable; she is the forcing function)
Components + readiness (origin/main-grounded):
1. **Human install/onboard flow** — `onboard --apply` / `drive` S1 blockers (**ce-ops#132**, OPEN). The real gating item; her onboarding makes it human-must-work, not agent-fleet-only.
2. **Claude Code harness adapter** — #110 merged the harness-adapter *layer* but `ClaudeCodeAdapter` is a `NotImplementedError` skeleton. **Commit to implementing it** as an explicit deliverable of her onboarding — it's the missing piece between the adapter layer and a human using CE with Claude Code.
3. **CE identity for her** — the identity schema (#137/#147) has **no `human-contributor` role** (accounts assume a bot tied to host+owning_seat). Add a minimal `human-contributor` role; her formal registry entry lands with the authoritative internal registry (**ce-ops#269**). Deferred — the bridge needs no registry entry.
4. **Team-mode governance** — graduate her into CODEOWNERS as a peer human + honor `peer-authority.md` (two distinct humans for privileged merges). Tied to the trust-tier ladder.

## Governance / gate ladder (the through-line to the gate doctrine)
- Approval authority is rooted in human ratification; **containment is orthogonal isolation** (a separate axis), and attestation (**ce-ops#289 SO_PEERCRED**) is what would let delegated approve flow safely to a contained agent — not relevant to Nitzan (she's a human), but the same delegation graph: Nitzan starts gated, graduates to holding her own approve-authority as a second human.
- This onboarding is the **first concrete instance of "team mode"** (multiple humans, each an authority) — distinct from "skynet" (our one-operator→many-agents internal setup) and "solo" (one human + one CE).

## Reusable process (for the NEXT contributor)
1. Decide archetype (conventional-via-CE team-mode is the default for a human dev).
2. Bridge: invite as `write` on dev repos + `read`/`write` on ce-ops per trust; point at CONTRIBUTING + contributing-to-ce + ce-playbooks.
3. Set gate tier (hybrid-iii default): write + review now, approve withheld, graduate via trust-tier ladder → CODEOWNERS peer.
4. Build: their CE+harness deployment (install flow + harness adapter + identity).
5. Offboarding: every grant is individually revocable — repo collaborator removal, registry-entry removal, App revocation. Scope access to trust tier; review on departure.

## Immediate follow-ups (proposed, for ratification)
- Notify Nitzan / send her the day-one packet + the invite links.
- File the BUILD arc in ce-ops: (a) `ClaudeCodeAdapter` implementation, (b) human-onboarding install fixes (folds into #132), (c) `human-contributor` role in identity schema, (d) her trust-tier graduation criteria. Sequence behind the current GATE β / ARC 2 work.
