# ARC STRANGELOOP-2 — MANDATE DRAFT — 2026-07-10 (for Operator batch ratification)
# Author: ce-dev-2 controller (Claude face). Predecessor arc closeout RATIFIED 2026-07-10.
# Ratifying this document authorizes the whole arc; per the fleet-mode doctrine (ratified
# 2026-07-10) no per-artifact Operator review occurs inside the arc.

## Thesis (carried forward + sharpened)
strangeLoop-1 proved the factory loses throughput at exactly one point: the controller as a
single un-invocable session (5.5h dark gap > all other stall causes combined; confirmed twice
more by the emergency migration and the quota-cliff handoff). STRANGELOOP-2's job: make every
mechanical controller function survivable without a live face, and make the face's judgment
calls cheap when it is live.

## Mandate items (single program: controller continuity + truthfulness mechanization)
N-1 **Spawn-on-event mechanical chains** — PR-opened→review, READY→harvest-prep,
    approved→merge already have daemon seams (#915/#917 s1 merged). Land slice 2 of each:
    the chains run as daemons/ephemeral controllers; the face only adjudicates.
N-2 **Acting-liveness watchdog** — liveness = arc-ledger mtime (an ACTING signal), not
    heartbeats. Stale ⇒ PushNotification page + takeover-controller spawn under one-face
    rules (the codex-standby path, now live-proven twice).
N-3 **Truthfulness gates** — (a) documented-verbs gate: every `ce <verb>` in docs must exist
    in shipped ce_cli; (b) dual-format .md/.html sync gate. Both CI-enforced.
N-4 **Brief-composition preflight** — mechanically validate every gate input a brief declares
    (work-class enum, signal formats, profile names) AND hash-pinned-file intersections
    (ce-453 Part A guard, in flight as ce-453a) before dispatch.
N-5 **Stale-work reconciliation** — periodic sweep closing tickets whose work landed without
    a ticket ref (ce-ops#518; slice 1 in flight). Evidence: THREE stale-unit catches on
    2026-07-10 alone (ce-478, portability, ce-427) — verify-not-landed must be mechanical.
N-6 **Host capacity + admission control** — host-global single-owner admission for full-parity
    suites across ALL controllers (matching bare pytest too), named-basetemp discipline,
    disk headroom gate that fails the run BEFORE exhausting the host. Evidence: 23 GB and
    21 GB orphan trees on consecutive days; two 100%-root incidents in 12 hours.
N-7 **Durable generated config** — retire the /tmp launcher-toml class: generated configs are
    durable, owned, validated, lifecycle-managed (twice-recurred DGX footgun).
N-8 **Deployment parity** — merged≠deployed audit unit + acceptance-evidence slice 2 with
    persistent-state probes for deploy-class tickets (RATIFIED 2026-07-10); queue-daemon
    host-network topology becomes declared IaC, not local drop-in knowledge.
N-9 **Seat environment integrity** — fix dev-3 in-seat venv (ce-ops#521) so contained seats
    can self-attest; skipped-test transparency already landed (#831).
N-10 **DGX re-integration** — restore dev-4 + Arad controller reach (pubkey lane authorized
    2026-07-10); harvest ce-490; salvage DGX transcripts; then whole-fleet containment
    resumes per the ratified retirement program.

## Standing constraints (unchanged)
One-face; workers never sign; author≠reviewer; full preflight GREEN before push; bounded
work-units; no idle seats; AWAITING-OPERATOR = ratifications/credentials/spend only.

## Done-when
- Every N-item either landed (PR refs) or explicitly re-scoped with evidence.
- A full factory day (dispatch→build→review→merge→deploy) completes with zero face
  interventions in mechanical chains, measured by the arc ledger.
- Continuity drill: kill the face mid-arc; the standby resumes all lanes within one
  watchdog period, no work lost.

## ✅ RATIFIED — Operator, 2026-07-10 (verbatim: "STRANGELOOP-2 is ratified, drive it to completion")
Single batch ratification of N-1..N-10 as the STRANGELOOP-2 arc. Priority order as listed;
N-5/N-6 are already live-started under standing S1 authority (evidence-driven emergencies).
