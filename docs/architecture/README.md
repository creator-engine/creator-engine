# Creator Engine v3 — Architecture (design source-of-truth)

The `v3-*.md` documents in this directory are the **committed, shareable** design
source-of-truth for the Creator Engine **v3** evolution. They are the in-repo home
for the load-bearing v3 architecture decisions, so the design pointers resolve in
a **fresh clone** (the original architect reports live under a gitignored research
tree and do not travel with the repo).

This directory also retains older, pre-v3 architecture documents (`SAD.md`,
`agentic-sdlc-operating-model.md`, `parallel-controller-orchestration.md`, and
companions) authored before the v3 pivot. Those describe the earlier model; the
`v3-*.md` set is the current design of record.

Read these as the *why* behind what is built:

- **the documents below** — *why it is built this way* (the design decisions being
  executed). For *where we are / what's next*, see the project README's **Current
  Status** section and `git log --oneline main`.

## Provenance (read this first)

Each document here is a **curated, redacted copy** of a read-only Architect report.
The copies preserve the **design substance and the dated external citations
verbatim**, and **strip instance-specific / sensitive provenance** that is
irrelevant to the design and should not travel with a shared repo: transient
commit/tree SHAs, internal handoff/bootstrap SHAs, internal research-workflow run
IDs, machine/account/host identifiers, and gitignored absolute path pointers.

The **full-fidelity, unredacted** originals (with their evidence trees) live under
the gitignored research tree at `.hermes/research/v3-*-architect-*/` and
`.hermes/research/v3-product-architecture-brief-*/` — available in the working
checkout, not in a fresh clone. When a citation or provenance detail matters beyond
what is committed here, that gitignored tree is the system of record.

## Index

| Document | What it decides |
| --- | --- |
| [`v3-spec.md`](./v3-spec.md) | **The spec — read first.** The thin-orchestrator / thick-enforcer architecture, the five-component / three-plane (A/B/C) model, the forge-adapter interface, the container + in-container enforcer design, the D0–D6 deletion plan, the G-i/ii/iii → G-1 → G-2 → G-3 MVP gate map, and the OD-04′ supersession. |
| [`v3-secure-runtime.md`](./v3-secure-runtime.md) | **Plane C — runtime safety.** A defensive evaluation of the NVIDIA OpenShell runtime: deny-by-default per-endpoint L4/L7 egress, the gVisor + capability-separation-proxy ship-now backend, the credential model, the tamper-evident evidence spine, and the "sandbox is necessary, not sufficient" lesson. |
| [`v3-product-brief.md`](./v3-product-brief.md) | **The product brief that framed the above.** The consolidated, already-ratified product decisions: product identity, target market, the A/B/C scope model, monorepo-first topology, the two product principles (agent-native install; Dev-mode-only MVP), and what survives vs. what is cut. |
| [`credential-identity-architecture-20260713.md`](./credential-identity-architecture-20260713.md) | **Credential identity findings.** A curated, redacted scorecard of the current identity posture, immediate containment conditions, roadmap categories, and explicit unknowns. Findings only; it authorizes no operational act. |

Note: `specs/001-v0-1-governance-substrate/` is the **superseded v2 governance
substrate** — historical context, not the v3 roadmap.

## Pilot design (v3.0 → v3.1)

The pilot arc — building the full stack (agent-interaction contract · tokenomics
gate · coordination layer) + the product surface to a **pilot-ready** build. These
are **DESIGNED / pilot-target** (re-ground at the implementing gate, G-4…G-7);
execution status lives in the project README's **Current Status** section.

| Document | What it decides |
| --- | --- |
| `pilot-roadmap.md` | **The full-stack-first roadmap to pilot.** Milestones v3.0 (MVP-complete) / v3.1 (pilot-ready); the gate clusters G-3.7b/G-3.8 → G-3.9 (D1–D6, launcher-guarded) → G-4 (contract) → G-5 (tokenomics) → G-6 (coordination) → G-7 (product surface, incl. the two-mode installer); acceptance per cluster + the build-order rationale + the deferred backlog. |
| [`pilot-deployment-transport.md`](./pilot-deployment-transport.md) | **Pilot deployment + transport selection.** The per-scenario transport matrix (subscription vs API-key × vendor ToS), the auto-select logic, the deployment invariants (gVisor box · two-credential custody · dev-as-reviewer for N=1 · two-mode installer), and the cost regime. |
| [`pilot-uiux-model.md`](./pilot-uiux-model.md) | **The pilot UI/UX.** The surface (the Operator's own agent + `ce` CLI + GitHub; cockpit deferred), the branded experience layer (`ce session` frame · staged workflow · the ◆ CE Completion Report · artifact awareness), and the cockpit graduation path. |
| [`stage-vocabulary.md`](./stage-vocabulary.md) | **The vocabulary canon — three user-facing vocabularies** over the conserved machine: the fractal **stage phases** `Frame → Shape → Build → Review → Ship`, the **Scope-card fields** (`Goal · Done-when · Budget · Change-type · Ready`), and the **◆ Completion Report** (`Outcome · Verdict · Next`) — each dual-mapped (label ↔ mechanical state/field/enum), plus the fractal/altitude framing. Consumed by G-6 (coordination) / G-7 (product surface). |
| [`shaping-ux.md`](./shaping-ux.md) | **The shaping UX — Frame→Shape dialogue + the chat→Scope trigger.** One grill-me engine + per-locus rubrics; Frame = free pre-Scope chat; the `Ready` gate; the detect-and-offer trigger with the risk-aware eagerness dial (`f(persona, risk-class)`); the differentiation thesis + current-date research grounding. The G-7 build-input. |
| [`cockpit.md`](./cockpit.md) | **The cockpit (post-pilot graduation — NOT a pilot deliverable).** The fleet mission-control board (stages as columns) where CE owns the screen; the escalation queue; the scaled-up cost meter; the ACP transport; "graduation not replacement" (same vocabulary + artifacts, re-rendered); the CEO-mode pairing. The design anchor so the pilot TUI stays cockpit-ready. |

**User guide:** [`../guide/understanding-ce.md`](../guide/understanding-ce.md) — the plain-language front door to CE's vocabulary + workflow (the seed of the in-product help; built out at G-7).

## Maintenance

These are point-in-time architecture records, not a living spec. Refresh a curated
copy only when its source Architect report is materially revised; keep the
redaction discipline above (design substance + citations in, instance/provenance
detail out). The authoritative *status* of execution always lives in the project
README's **Current Status** section and `git log --oneline main`.
