# ADR-V2-001 — Creator Engine v2.0 Foundation Substrate (`.ce/` namespace + state-boundary contract)

- **Status:** Accepted (records ratified Operator decisions; this ADR ratifies
  nothing of its own).
- **Date:** 2026-05-29
- **Namespace:** `ADR-V2-NNN` under `specs/v2/adrs/` (Q-C8).
- **Spec:** `specs/v2/001-v2-foundation-substrate/` (`spec.md`, `spec.ce.yml`).
- **Gate:** `G2.001.0` — `.ce` namespace + state-boundary contract (Layer 0).
- **Authoring run:** CE-governed redo under the true CE-governed Claude Code
  Controller (Ring 0 launcher, CE hook pack, `--strict-mcp-config`). The prior
  non-CE-governed output is archived for comparison and was not edited.
- **Class:** Documentation / rationale only. This ADR changes no schema enum, no
  validator behavior, no template output, no CLI/runtime text, and no example
  fixture. It authorizes no runtime implementation, commit, push, PR, merge,
  GitHub settings change, external side effect, or autonomy activation.

> This ADR **records** the rationale, alternatives, and consequences of the v2
> foundation substrate as decided by the Operator decision ledgers cited under
> *Authority basis*. The Operator decision ledgers remain the authority source
> for ratified governance choices. This ADR summarizes and applies them; it does
> **not** ratify authority and does **not** override any ledger decision.

---

## Authority basis (verified by SHA256 before authoring)

- **Operator Phase 2 decision ledger** (OD-01..OD-24, OD-06A) —
  `.hermes/research/ce-phase-2-distributed-platform-architect-20260528T145107Z/OPERATOR_PHASE_2_DECISION_LEDGER.md`,
  SHA256 `514b537f175eb92f3c8780ebb934f8ec1ecad26a8362c0b18efd4b74a7f2835c`.
- **Operator Phase 2 / v2 roadmap-review decision ledger** (Q-O1..Q-O7,
  Q-C1..Q-C8) —
  `.hermes/research/phase-2-v2-opus-4-8-architect-reframe-handoff-20260528T181939Z/OPERATOR_PHASE_2_V2_ROADMAP_REVIEW_DECISION_LEDGER.md`,
  SHA256 `dadedc719f16b676802ff5f9334113fc484eb324f4451b644ec410a5b8d48d65`.
- **Phase 2 / v2 roadmap review packet** —
  `.hermes/research/phase-2-v2-roadmap-review-20260529T032445Z/OPERATOR_PHASE_2_V2_ROADMAP_REVIEW_PACKET.md`,
  SHA256 `57f5af4686f39b3633623356941b792204c582ab9b1cb0629d6a9866eb53150f`.
- **Architect roadmap / development map / risk inputs (research, non-ratifying):**
  - `ARCHITECT_PHASE_2_V2_ROADMAP.md`, SHA256 `80b34c88e1a8e48673452979865987c5dfe30080ed64c3126690c1f9a181659c`.
  - `ARCHITECT_PHASE_2_V2_DEVELOPMENT_MAP.md`, SHA256 `a2ce11aa339b46c6336b8ba2da5c46dfa69efb6bc06acef4fb0d96359e7fcb00`.
  - `ARCHITECT_PHASE_2_V2_RISK_AND_OPEN_QUESTIONS.md`, SHA256 `6848cbe5febf7131c617e1e373a9c6898005c691f45fa2dfbb546edfcb61558b`.

---

## Context

Creator Engine v1.0 is a local governed runtime kernel whose active state lives
under `.hermes/` (wholesale gitignored), whose human-authority machine role is
`source`, and whose specs live under `specs/NNN`. OD-23 reframes Phase 2 as the
**CE v2.0 foundation line** — v1.0 is a proof-of-concept and historical
compatibility source, not a backward-compatibility chain. The v2 reset (OD-06,
OD-06A, OD-08, OD-21) introduces a clean foundation: `.ce/` active state,
`operator`-canonical role surfaces, and the `specs/v2/NNN` namespace.

That reset creates a foundation layer (Layer 0) that did not previously exist.
Before any v2 ledger, event, PCL, connector, or directive-pack feature can be
authored or implemented, the substrate needs: a canonical `.ce/` root with an
enforceable tracked-vs-instance boundary; a hard `.hermes/` write-freeze; a
read-only v1→v2 importer; the v2 terminology/role canon; the v2 sidecar shape
and risk-inventory placement; and the authoritative v1→v2 crosswalk. This ADR
records the decision to establish that substrate, beginning with gate
`G2.001.0` (the `.ce/` namespace + state-boundary contract).

## Decision

Establish the v2.0 foundation substrate as specified in
`specs/v2/001-v2-foundation-substrate/`, applying the ratified decisions:

1. **Canonical `.ce/` namespace with a two-zone state-boundary** (Q-O1, OD-06A).
   Repo-authored governance/configuration subtrees are tracked and
   validator-visible; runtime/session-local/credential-adjacent subtrees are
   gitignored. CE-event and PCL storage split canonical published records from
   local spool/cache. The boundary fails closed on secret-bearing or
   runtime-only files entering tracked governance paths.
2. **`.hermes/` hard write-freeze for v2 flows** (Q-O2). `.hermes/` remains
   readable only as legacy/import/archive/historical/Hermes-controller context;
   v2 flows never write active CE state there.
3. **Read-only v1→v2 importer contract** (Q-O3). The importer reads legacy
   material, maps it through `specs/v2/_crosswalk.yml`, and emits canonical
   `.ce/` outputs or a dry-run report with provenance; it never mutates
   `.hermes/`, no-ops cleanly on empty input, and never reintroduces `.hermes/`
   as active state. Real tenant migration activation is separately
   Operator-ratified.
4. **v2 terminology and role canon** (OD-06, OD-21, Q-O4, Q-O7). `operator` is
   the only canonical emitted human-authority machine role; `source` is an
   import alias only. `agent_reviewer` is active advisory (non-ratifying);
   `agent_ratifier` is reserved-inactive and validator-rejected for any active
   authority binding, with future activation reserved to the named post-v2
   `AOS-RATIFIER-MILESTONE`.
5. **Operator-only privileged floor preserved in every mode** (OD-01, OD-02,
   OD-22). Modes are `strict`/`auto`/`transcendence`; privileged-class
   ratification and emergency governed override remain Operator-only.
6. **v2 sidecar shape + risk-inventory placement** (OD-24, Q-C2, OD-20, Q-C7).
   CE metadata lives in adjacent `*.ce.yml` sidecars; standard Spec Kit Markdown
   stays free of CE metadata; the authoritative `risk_inventory` lives in
   `spec.ce.yml` and required validation is mapped against each declared risk.
7. **Authoritative v1→v2 crosswalk** (Q-C3, OD-08). `specs/v2/_crosswalk.yml` is
   the single tracked spec-level crosswalk; `.ce/crosswalks/` is derived only.
8. **Convention bindings** (Q-C1, Q-C4, Q-C8, OD-07). Gates are
   `G2.<feature>.<slice>` bound to `specs/v2/NNN`; requirement IDs are
   `RV2-<specNNN>-<reqNNN>`; v2 ADRs are `ADR-V2-NNN` under `specs/v2/adrs/`.
9. **No destructive v1 removal** (Q-O5) and **migrated tenants default to
   `strict`** (Q-O6).

## Alternatives considered

- **Continue on `.hermes/` + `specs/008…021` + `source` (v1.x additive arc).**
  Rejected by OD-06A/OD-08/OD-23: it would entrench dual-namespace drift and
  legacy terminology debt instead of a clean v2 foundation.
- **Destructively remove v1 (`source` alias, `.hermes/` readability) at v2.0.**
  Rejected by Q-O5: v2.0 keeps legacy material readable for
  import/crosswalk/archive/history; any destructive removal needs a separate
  Operator-ratified gate.
- **Embed CE metadata inline in `spec.md`** to avoid a sidecar round-trip.
  Rejected by OD-24/Q-C2: byte-clean Spec Kit Markdown is preserved; CE metadata
  lives in `*.ce.yml` sidecars.
- **Single wholesale-gitignored `.ce/` (mirroring `.hermes/`).** Rejected by
  Q-O1: governance/configuration must be tracked and validator-visible, so a
  finer two-zone split is required.
- **Activate `agent_ratifier` (or treat the Operator-only floor as permanent).**
  Both rejected: Q-O7/OD-06 keep `agent_ratifier` reserved-inactive now, while
  OD-02's caveat preserves the long-term autonomous-OS endgame via a separately
  ratified future milestone — the floor is a v2 floor, not a permanent ceiling.
- **Defer the v1→v2 importer until a tenant migrates.** Rejected by Q-O3: a
  bounded read-only importer/dry-run surface is in scope at `G2.001.0` so the
  migration path exists and is provenance-bearing from the foundation.

## Consequences

- **Positive.** Later v2 gates author and implement on a clean, enforceable
  substrate; tracked governance is validator-visible; runtime/secret state
  cannot leak into tracked paths; v1 history stays importable and reversible;
  terminology/role/authority debt is prevented at inception.
- **Cost / obligations.** Foundation validators are specified across the slice
  sequence (`ce_path_namespace`, `ce_terminology_v2`, `role_enum_v2`,
  `sidecar_schema_v2`, `crosswalk_register`); the crosswalk is a living artifact
  requiring freshness discipline; the tracked-vs-instance split must be
  implemented exactly to avoid mis-tracking.
- **Bootstrap note.** `G2.001.3` formalizes the `spec.ce.yml` sidecar schema and
  risk-coverage validator. The crosswalk register schema/validator (`G2.001.4`)
  remains a later foundation slice; `specs/v2/_crosswalk.yml` therefore remains
  forward-declared until that gate.
- **Sequencing.** `G2.001.0` establishes the namespace, boundary, write-freeze,
  and importer contract; `G2.001.1`–`G2.001.4` add the terminology canon, role
  enum, sidecar schema, and crosswalk validator. Feature work (`specs/v2/002+`)
  depends on the foundation phase completing.

## Authority boundaries

- This ADR is documentation/rationale only and ratifies nothing. The Operator
  decision ledgers cited above are the authority source.
- Privileged-class ratification and emergency governed override are
  Operator-only in every mode (OD-02, OD-22).
- This gate authorizes **spec authoring only**: no runtime implementation,
  commit, push, PR, merge, GitHub settings change, external side effect, or
  autonomy activation.
- `agent_ratifier` remains reserved-inactive (Q-O7); nothing in this ADR binds
  or activates it.

## References

- `specs/v2/001-v2-foundation-substrate/spec.md` — Spec Kit specification.
- `specs/v2/001-v2-foundation-substrate/spec.ce.yml` — CE metadata sidecar
  (authority, requirements `RV2-001-NNN`, `risk_inventory`, `required_validation`,
  boundary/importer/role decisions).
- `specs/v2/_crosswalk.yml` — authoritative v1→v2 crosswalk register.
- `docs/adr/ADR-0001-v1-baseline-and-product-form.md`,
  `docs/adr/ADR-0002-operator-terminology-reconciliation.md` — v1 ADR baseline
  (the v2 ADR series uses the distinct `ADR-V2-NNN` namespace per Q-C8).
