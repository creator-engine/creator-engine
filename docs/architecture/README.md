# Creator Engine v3 — Architecture (design source-of-truth)

The `v3-*.md` documents in this directory are the **committed, shareable** design
source-of-truth for the Creator Engine **v3** evolution. They are the in-repo home
for the load-bearing v3 architecture decisions so that `docs/v3-roadmap.md`'s
design pointers resolve in a **fresh clone** (the original architect reports live
under a gitignored research tree and do not travel with the repo).

This directory also retains older, pre-v3 architecture documents (`SAD.md`,
`agentic-sdlc-operating-model.md`, `parallel-controller-orchestration.md`, and
companions) authored before the v3 pivot. Those describe the earlier model; the
`v3-*.md` set and `docs/v3-roadmap.md` are the current design of record.

Read these alongside the roadmap:

- **`docs/v3-roadmap.md`** — *where we are / what's next* (the gate map + per-gate
  status). Start there for orientation.
- **the documents below** — *why it is built this way* (the design decisions the
  roadmap is executing).

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
| [`v3-secure-runtime.md`](./v3-secure-runtime.md) | **Plane C — runtime safety.** The NVIDIA OpenShell adoption evaluation (defensive): deny-by-default per-endpoint L4/L7 egress, the gVisor + capability-separation-proxy ship-now backend, the credential model, the tamper-evident evidence spine, and the "sandbox is necessary, not sufficient" lesson. |
| [`v3-product-brief.md`](./v3-product-brief.md) | **The product brief that framed the above.** The consolidated, already-ratified product decisions: product identity, target market, the A/B/C scope model, monorepo-first topology, the two product principles (agent-native install; Dev-mode-only MVP), and what survives vs. what is cut. |

Note: `specs/001-v0-1-governance-substrate/` is the **superseded v2 governance
substrate** — historical context, not the v3 roadmap.

## Maintenance

These are point-in-time architecture records, not a living spec. Refresh a curated
copy only when its source Architect report is materially revised; keep the
redaction discipline above (design substance + citations in, instance/provenance
detail out). The authoritative *status* of execution always lives in
`docs/v3-roadmap.md` and `git log --oneline main`.
