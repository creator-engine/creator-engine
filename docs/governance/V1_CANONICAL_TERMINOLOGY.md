# Creator Engine v1.0 — Canonical Terminology Lock (`V1_CANONICAL_TERMINOLOGY.md`)

Gate: **G1 — Canonical terminology + product-contract lock** (type: **DOC**; lint only).
Authored UTC: 2026-05-24T17:52:25Z.
Lane: Gate 1 documentation-only writer, visible tmux pane, Claude Code Opus 4.7, effort high.
Controlling roadmap: **Option B re-issued definitive roadmap**, SHA256
`5a7e5ba74adcaab32c892c3cf793384eec4f121a6991b1bd5bba34a30fd48e13` (§2.3, §4).
Source Language/Packaging Decision Record: SHA256
`6bd9b87d9cccd98550c428d42b798ce748dba5307f0f1db5703d30f98e5d340c`.
Canonical baseline: live `refs/heads/main` = `36377f8c4caf6817e01d58072062eb5caccc164b`.
Requirement: **RV1-010** (`specs/_traceability_matrix.md`).

> **Authority.** This file is a Gate 1 governance control artifact. It **locks vocabulary**; it
> authorizes no implementation and re-decides no Source lock. Terms below carry **no hedged or
> probabilistic wording**. Where a term names a Source-locked decision (DP-1 = A, DP-2 = B, DP-3 = B,
> the Option B language/packaging contract), this file records that decision exactly — see
> `docs/adr/ADR-0001-v1-baseline-and-product-form.md` and `docs/governance/V1_PRODUCT_CONTRACT.md`.

---

## 1. Canonical command / package surface

### `ce`

The **canonical Creator Engine v1.0 command** (DP-1 = A). `ce` is the single top-level syscall
surface. It **wraps** the existing validator subcommands; it does not fork a second CLI. The `ce`
console script is added to the `creator-engine-validator` distribution at Gate 6 (RV1-060); its
console-script name is **independent of the distribution name**. There is **no distribution rename to
`creator-engine` in v1.0**.

### `creator-engine-validator`

The landed Python **distribution** and its retained back-compat / internal **console script**
(`creator-engine-validator = creator_engine_validator.cli:main`). It is the conformance core. v1.0
**retains** it; `ce` wraps its subcommands (`ce check` ≡ `creator-engine-validator check`). It is not
renamed and not removed.

### `ce check`

The offline **conformance validation** surface: `ce check` wraps
`creator-engine-validator check` / `check-examples` / `scan-*`. It **never mutates** tracked state and
**never ratifies**. Landed (as the validator core); wrapped under `ce` at Gate 6.

### `ce launch`

The **canonical v1.0 launch command** (DP-2 = B): a deterministic launcher that opens or attaches the
named tmux session and runs the chosen harness TUI as the Controller seat. It is **not** a CE-native
TUI. Implemented at Gate 6 (RV1-063).

### `ce hud`

An **alias / seam label** for the same launcher as `ce launch`. `ce hud` is **not** a v1.0 commitment
to a CE-native HUD/TUI; a CE-native HUD/TUI is **POST-V1 / v1.1+**. `ce hud` and `ce launch` invoke
the identical deterministic launcher.

## 2. Controller-seat and harness terms

### Controller seat

The **host-local** seat of control authority. In v1.0 the Controller seat **is the chosen harness
TUI** launched/attached by `ce launch`. Control authority stays **host-side and is not containerized**
in v1.0; only worker/agent work execution is isolated. CE remains the kernel; the harness is the seat,
never the kernel.

### harness TUI

The terminal user interface of a supported coding-agent harness, run **as** the Controller seat by
`ce launch`. Supported v1.0 Controller-seat harnesses: **Hermes `IN`, Codex `IN`, Claude Code `IN`**;
**OpenClaw `SEAM`**. New harnesses attach through the same Controller-seat seam.

## 3. Lane and visibility terms

### lane

A single governed unit of delegated work driven by one Controller, bound to one Active-Work claim and
(when it executes in a workspace) one Worktree Lease. A lane has authority **only** if it is recorded
in the Pane Registry.

### lane launch

The act of starting a governed lane. The canonical primitive is **`ce lane launch`** (with
`ce lane status` / `ce lane verify` / `ce lane archive`): it spawns/attaches the lane in a **visible
tmux pane or refuses**, writes a Pane Registry record bound to a live Active-Work claim (PCO-050),
verifies the consumed prompt/handoff pointer + SHA before launch, and refuses any non-visible surface
for a visibility-required role (PCO-049). It is the **missing syscall** built at Gate 3.

### visible tmux pane

The **only contract-conformant operator-visible terminal** for a visibility-required lane (PCO-049
accepts only `terminal.kind: tmux`). tmux is **mandatory** for v1.0 visible lanes and for the
Controller-seat harness. A hidden / headless / print-mode / one-shot surface is **refused** for a
visibility-required role.

### Pane Registry

The record set (`.hermes/pane-registry/`) binding **pane ↔ lane ↔ Active-Work claim**. Records are
landed; the live pane **spawn** is added at Gate 3. A lane not present in the Pane Registry has **no
authority**. `scan-pane-registry` is its conformance check.

### Active-Work claim

A record in the Active-Work Ledger asserting **which Controller owns which lane/worktree now**. A lane
launch must bind to a **live, unreleased** Active-Work claim with matching controller and lane.

### Worktree Lease

A record (`.hermes/worktree-leases/`) granting a lane exclusive use of one git worktree. Acquired/
released by `ce worktree allocate` / `release` (= `pco-allocate` / `pco-release`, landed). Each worker
Container-Instance binds to exactly one Active-Work claim **and** one Worktree Lease.

## 4. The two ledgers — DISTINCT primitives (load-bearing)

**Active-Work Ledger** and **Side-Effect Ledger** are two **distinct** primitives and **must not** be
conflated. This distinction is a standing verification requirement (roadmap §4; `_assumptions.md` §3).

### Active-Work Ledger

`.hermes/active-work-ledger/` (**landed** on live main). Records **claims + lane events**. It answers
**"who owns this lane/worktree right now?"** Consumed by `ce worktree allocate`/`release` and by Pane
Registry binding. Conformance check: `scan-active-work-ledger`.

### Side-Effect Ledger

`.hermes/side-effect-ledger/` — an **append-only, classified, redacted, replayable** record of
**governed side effects** (lane launches; worker start/stop/refusal/GC; credential issuance; network
exceptions; queue dry-runs). It answers **"what governed side effects occurred, in what order, with
what mutation classification, redaction, and replay evidence?"**

- **Substrate landed** on live `refs/heads/main` under **PCO Slice 4**: the read-only-evidence-index
  schema (`schemas/side-effect-ledger.schema.yaml`), the registered validator check, the
  `scan-side-effect-ledger` conformance subcommand, well-formed + malformed examples, unit/integration
  tests, and `docs/operations/SIDE_EFFECT_LEDGER_PROTOCOL.md`.
- **Runtime pending**: the **`ce ledger record` / `ce ledger verify`** runtime (append / hash-chain /
  replay per RV1-041) is the remaining Gate 4 gap. **Gate 4 must be Source-reclassified** from "build
  from scratch" to "reconcile + complete the remaining runtime" **before G4 execution**
  (`_assumptions.md` §4).

> The Side-Effect Ledger **substrate is present on live main**; any older assertion that it is "absent"
> or "unbuilt" on live main is **superseded and stale**, and is not an operative claim of this spine.

## 5. Evidence, queue, and authority terms

### Integration Queue

The canonical landing surface. In v1.0 it is a **`SEAM`**: a local **serialized dry-run** landing
contract (authored at Gate 8); **live landing is POST-V1**.

### fan-in packet

A **read-only** local evidence aggregation produced by `ce fanin build` under `.hermes/fan-in/` and
read by `ce fanin inspect` (Gate 7). It is content-hashed and deterministic, aggregates evidence
manifests + Side-Effect Ledger references, and has **no authority**: it **never** ratifies, enqueues,
lands, merges, pushes, or approves. New fan-in output is authored as stdlib JSON (§2.2 format split).

### Source ratification

The privileged act by which **Source** accepts a gate's baseline/contract/evidence at a named
ratification boundary. Review, CI, fan-in, and harness output **inform** Source; they **do not**
ratify. Privileged mutation classes require Source ratification at the points named per gate. No gate
skips its ratification boundary.

## 6. Governed-environment terms

### governed environment

A host/repo posture that satisfies the v1.0 governance contract: contract-conformant interpreter
(floor + target `>=3.14`), tmux present, rootless Podman available for worker execution, governed
`.hermes/` state-path posture, no unsafe hidden continuation, and dependency/wheelhouse contract
fidelity. v1.0 runs as a **governed local runtime**, not an unmanaged host script bundle.

### governed-environment guard predicate

The **DP-3 = B** predicate, surfaced through `ce doctor` / `ce check`, that asserts governed-environment
posture and **refuses ungoverned host drift**. It is the v1.0 substitute for mandatory project-dev
containerization. **Gate 1 records it as a requirement + RED test plan only** (RV1-012,
`docs/governance/V1_GOVERNED_ENVIRONMENT_GUARD_REQUIREMENT.md`); **implementation is Gate 6**
(RV1-061). It is designed to be forward-compatible so a future v1.1 governed dev-container is a
detectable, validatable PASS branch.

## 7. Inclusion / exclusion classification terms

### IN / SEAM / POST-V1

The v1.0 surface-classification vocabulary (roadmap §3; `docs/governance/V1_PRODUCT_CONTRACT.md`):

- **`IN`** — shipped and authoritative in v1.0.
- **`SEAM`** — a defined interface / stub / contract present in v1.0, with implementation deferred.
- **`POST-V1`** — out of v1.0 entirely.

(`POST-V1 / v1.1` denotes a surface deferred specifically to the v1.1 line, e.g. the CE-native HUD/TUI
and the `ce dev shell` / `ce dev run` project-dev container — deferred, not rejected.)

## 8. References

- `docs/adr/ADR-0001-v1-baseline-and-product-form.md` — DP-1 = A / DP-2 = B / DP-3 = B + Option B lock.
- `docs/governance/V1_PRODUCT_CONTRACT.md` — v1.0 product boundary + IN/SEAM/POST-V1 table.
- `docs/governance/V1_GOVERNED_ENVIRONMENT_GUARD_REQUIREMENT.md` — guard predicate requirement + RED plan.
- `docs/governance/V1_DEV_CONTAINER_SEAM_CONTRACT.md` — v1.1 dev-container seam.
- `specs/_traceability_matrix.md` — RV1-010 (this doc) and RV1-011..013.
- `specs/_assumptions.md` §3–§4 — two-ledgers distinction + Side-Effect Ledger live-main correction.
- Option B re-issued roadmap §2.3, §4 — `5a7e5ba7…`.
