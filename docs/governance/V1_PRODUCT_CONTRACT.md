# Creator Engine v1.0 — Product Contract (`V1_PRODUCT_CONTRACT.md`)

Gate: **G1 — Canonical terminology + product-contract lock** (type: **DOC**; lint only).
Authored UTC: 2026-05-24T17:52:25Z.
Lane: Gate 1 documentation-only writer, visible tmux pane, Claude Code Opus 4.7, effort high.
Controlling roadmap: **Option B re-issued definitive roadmap**, SHA256
`5a7e5ba74adcaab32c892c3cf793384eec4f121a6991b1bd5bba34a30fd48e13` (§2, §3, §8).
Source Language/Packaging Decision Record: SHA256
`6bd9b87d9cccd98550c428d42b798ce748dba5307f0f1db5703d30f98e5d340c`.
Canonical baseline: live `refs/heads/main` = `36377f8c4caf6817e01d58072062eb5caccc164b`.
Requirement: **RV1-011** (`specs/_traceability_matrix.md`).

> **Authority.** This file **records** the Source-locked v1.0 product contract. It re-decides nothing
> and authorizes no implementation. Locked decisions below carry **no hedged or probabilistic
> wording**. Terminology is defined in `docs/governance/V1_CANONICAL_TERMINOLOGY.md`.

---

## 1. v1.0 product boundary — local governed runtime kernel

Creator Engine v1.0 is a **local governed runtime kernel**: a **daemonless, repo-native, local
command-line runtime** (`ce`). It executes on demand against repository-local `.hermes/` state and
tracked substrate artifacts, then exits. It runs **no long-running daemon and no web server** as part
of v1.0 runtime authority. Authority is the local process invoked by the Operator/Controller in the
operator's shell; it is never delegated to a background service, a hosted endpoint, or a browser. **No
network call is part of kernel authority.** Work execution is isolated in **rootless Podman**; the
host-local Controller seat is **not** containerized; the operator-visible substrate is **tmux**.

v1.0 is **CLI-first and file/protocol-backed**, with **honest seams for team mode**. v1.0 is **not** a
hosted service, **not** SaaS, **not** the full GitHub-backed team-mode product, **not** PCL production,
**not** CE-event production, and **not** distributed identity. Those surfaces are present in v1.0 only
as explicit **`SEAM`** contracts or are **`POST-V1`** (see §4).

(Full kernel-boundary statement: `docs/adr/ADR-0001-v1-baseline-and-product-form.md` §2; roadmap §2.1.)

## 2. Locked product-form decisions (DP-1 / DP-2 / DP-3)

These are Source-ratified and **locked**. No later gate reopens them.

- **DP-1 = A** — Canonical command / package identity. The canonical v1.0 command is **`ce`**. The
  Python distribution **remains `creator-engine-validator`**; the `ce` console script is added to it
  and the `creator-engine-validator` console script is **retained** as back-compat/internal. **No
  distribution rename in v1.0.** `ce` **wraps** the existing validator subcommands; the `ce`
  console-script name is independent of the distribution name.
- **DP-2 = B** — v1.0 launch model. v1.0 ships a **deterministic launcher + Controller-seat-in-harness**.
  **`ce launch`** is the canonical launch command; **`ce hud`** is an alias / seam label for the same
  launcher — **not** a commitment to a CE-native HUD/TUI in v1.0. The chosen harness TUI **is** the
  v1.0 Controller seat. A CE-native HUD/TUI is **POST-V1 / v1.1+**. No G-HUD gate on the v1.0 path.
- **DP-3 = B** — Development-environment containerization scope. v1.0 **containerizes worker/agent
  execution only** (rootless Podman; rootful refused). **Host-local development is permitted in v1.0**,
  guarded by an explicit **governed-environment guard predicate** surfaced through `ce doctor` /
  `ce check` that **refuses ungoverned host drift**. **Mandatory project-dev containerization
  (`ce dev shell` / `ce dev run`) is POST-V1 / v1.1.** No G-DEV gate on the v1.0 path.

## 3. v1.0 inclusion / exclusion table (IN / SEAM / POST-V1)

From the Option B re-issued roadmap §3, **reconciled with the Gate 0 corrections** (live-main baseline
`36377f8c…`; Side-Effect Ledger substrate-landed / runtime-pending — see §5).

`IN` = shipped and authoritative in v1.0. `SEAM` = a defined interface/stub/contract present in v1.0,
implementation deferred. `POST-V1` = out of v1.0 entirely.

| Surface | Status | Rationale | Gate |
|---|---|---|---|
| `ce` CLI umbrella (name `ce`, DP-1 = A) | `IN` | Single syscall surface wrapping the validator. | G6 |
| `creator-engine-validator` (distribution + console script) | `IN` | Landed conformance core; retained, wrapped by `ce`. | reuse |
| Python packaging (`>=3.14`, setuptools, uv-first + `uv.lock`, cp314-only offline wheelhouse) | `IN` | Locked install identity (Source Option B). | G6 |
| Node.js / Bun | `POST-V1` | No JS runtime in kernel. | — |
| tmux | `IN` (mandatory) | Only contract-conformant visible terminal (PCO-049). | G3 |
| Podman (rootless) | `IN` (worker-runtime-mandatory) | Worker/agent isolation engine; rootful refused. | G5 |
| Git worktrees | `IN` | Landed (`pco-allocate`/`pco-release`). | reuse |
| Active-Work Ledger | `IN` | Landed; claims + lane events. | reuse |
| Pane Registry | `IN` | Records landed; spawn added at G3. | reuse / G3 |
| Worktree Lease | `IN` | Landed. | reuse |
| `ce lane launch` (governed visible launch) | `IN` (gap) | The missing syscall; visible-pane-or-refuse. | G3 |
| **Side-Effect Ledger** | `IN` — **substrate landed (PCO Slice 4) / runtime pending** | Distinct from Active-Work Ledger; substrate (schema + check + `scan-side-effect-ledger` + examples + tests + protocol doc) landed on live main; `ce ledger record`/`verify` runtime is the remaining gap. **G4 must be Source-reclassified before execution.** | G4 (reconcile + complete) |
| Worker isolation runtime (Slice 2I-R) | `IN` (gap) | Shapes landed (2I-S); runtime unbuilt. | G5 |
| `ce launch` / `ce hud` alias (deterministic launcher, DP-2 = B) | `IN` (gap) | Single-command launch into harness Controller seat; `ce hud` is an alias, not a CE-native TUI. | G6 |
| `ce doctor` / `ce init` (+ governed-environment guard, DP-3 = B) | `IN` (gap) | Preflight + repo-state init + ungoverned-host refusal. | G6 |
| Agent-native install/bootstrap doc + YAML | `IN` | Machine-readable bootstrap + preflight + blocked-report. | G6 |
| fan-in packet (read-only) | `IN` (gap) | Local evidence aggregation; never ratifies. | G7 |
| Integration Queue | `SEAM` | Local serialized dry-run landing in v1.0; live landing POST-V1. | G8 / seam |
| CE-event protocol (signed blocks) | `SEAM` | Team-mode coordination; built on `controller-key`. | seam |
| PCL (Project Coordination Ledger) | `SEAM` | Team-mode materialized state. | seam |
| Distributed identity | `SEAM` | `identity-record` / `controller-key` are the local seam (landed). | seam |
| GitHub connector (live read/write) | `POST-V1` | Live external side effects excluded from local kernel. | — |
| local web cockpit / dashboard | `POST-V1` | No web server in kernel authority (§1). | — |
| CE-native HUD/TUI | `POST-V1 / v1.1+` (DP-2 = B) | Presentation, not kernel authority; deferred. | — (seam) |
| Hermes / Codex / Claude Code harness | `IN` (Controller seat) | Named current harnesses. | G2 / G6 |
| OpenClaw harness | `SEAM` | Named example; attaches via Controller-seat seam. | seam |
| host-local Controller seat | `IN` | Control authority stays host-side. | G2 |
| governed-environment guard predicate | `IN` (DP-3 = B) | Proves non-ungoverned-host posture without mandatory dev container. | **G1 (req) / G6 (impl)** |
| containerized project-dev env / `ce dev shell` / `ce dev run` | `POST-V1 / v1.1 seam` (DP-3 = B) | Worker-only containerization in v1.0; project-dev deferred, not rejected. | — (seam) |
| hosted service / SaaS | `POST-V1` | v1.0 is local-first. | — |

## 4. Team-mode / external surfaces — seam-only or POST-V1

No GitHub / team-mode / SaaS / PCL / CE-event / distributed-identity expansion is part of v1.0 **except
as explicit seam contracts** (roadmap §8):

- **Integration Queue** — `SEAM`: local serialized dry-run landing contract (G8); live landing POST-V1.
- **CE-event protocol (signed blocks)** — `SEAM`: signed-block schema stub + verify test; built on
  `controller-key`.
- **Distributed identity** — `SEAM`: `identity-record` + `controller-key` are the landed local seam.
- **PCL (Project Coordination Ledger)** — `SEAM`: schema stub only.
- **GitHub connector (live read/write)** — `POST-V1`: none in v1.0.
- **Hosted service / SaaS / web cockpit** — `POST-V1`: none in v1.0.
- **CE-native HUD/TUI** — `POST-V1 / v1.1+` (DP-2 = B).
- **Mandatory project-dev container (`ce dev shell` / `ce dev run`)** — `POST-V1 / v1.1` seam
  (DP-3 = B; `docs/governance/V1_DEV_CONTAINER_SEAM_CONTRACT.md`).
- **`uvx` one-line operator install** — `POST-V1` (B3).

## 5. Side-Effect Ledger substrate correction (live-main)

Reconciled with the Gate 0 correction (`_assumptions.md` §3–§4; ADR-0001 §5):

- The Side-Effect Ledger **substrate is landed** on live `refs/heads/main` under **PCO Slice 4** as a
  read-only evidence index (schema, registered validator check, `scan-side-effect-ledger`, well-formed
  + malformed examples, unit/integration tests, `docs/operations/SIDE_EFFECT_LEDGER_PROTOCOL.md`).
- The **runtime is pending**: there is **no `ce ledger record` / `ce ledger verify`** runtime on live
  main (append / hash-chain / replay per RV1-041) — only the conformance `scan-*` surface.
- **Gate 4 must be Source-reclassified** from "build from scratch" to "reconcile + ratify the landed
  PCO-Slice-4 substrate and complete the remaining runtime" **before G4 execution**.
- The Side-Effect Ledger remains **distinct** from the Active-Work Ledger
  (`docs/governance/V1_CANONICAL_TERMINOLOGY.md` §4).

> Any older assertion that the Side-Effect Ledger substrate is "absent" or "unbuilt" on live main is
> **superseded and stale**, and is not an operative claim of this contract.

## 6. Option B language/packaging contract (implementation deferred to Gate 6)

Source-locked (Option B / 1B; Source decision record `6bd9b87d…`). **Recorded here; implemented at
Gate 6 (RV1-060). Gate 1 authors no packaging/dependency/wheelhouse change.** Full statement:
ADR-0001 §4; `_assumptions.md` §6; roadmap §2.2.

- **Python floor `requires-python = ">=3.14"`**; tested/current target **Python 3.14.x** (current
  stable patch at decision time 3.14.5, released 2026-05-10). Floor = compatibility promise; target =
  what is built/tested/shipped. **Python 3.13 intentionally excluded** unless Source later widens
  support by a fresh decision; 3.11/3.12 rejected (security-only); 3.15 invalid (unreleased).
- **v1.0 wheelhouse is cp314-only** (x86-64). Any later ABI widening is a fresh Source decision.
- **Install is uv-first** (`uv pip install --no-index --find-links validators/wheelhouse …` /
  `uv sync --offline --locked`) with a **pip/`--no-index` fallback** retained for a uv-less host. No
  network fetch at install or runtime authority.
- **Reproducibility contract = `pyproject.toml` + `uv.lock` (per-file hashes) + offline wheelhouse**;
  `validators/requirements.txt` is a `uv export`-derived **fallback/export** artifact kept in lockstep,
  **not** the primary lock contract.
- **Pinned deps `PyYAML==6.0.3` and `jsonschema==4.26.0`**, with transitives (`attrs`,
  `jsonschema-specifications`, `referencing`, `rpds-py`) refreshed in lockstep.
- **Build backend `setuptools.build_meta`** retained; package stays nested at `validators/pyproject.toml`;
  no root distribution restructure; **DP-1 = A not reopened**.
- **Format split (B6/B7):** JSON Schema 2020-12 (schema language) unchanged; new machine evidence/ledgers
  use stdlib `json`; new operator/developer config uses TOML via stdlib `tomllib` (read-only) or
  CE-managed JSON; existing `schemas/*.schema.yaml`, Spec Kit sidecars, and identity records remain YAML
  (read-only). **No TOML writer dependency** in v1.0.
- **`uvx` one-line install is POST-V1 (B3)**; v1.0 install surface is source checkout (`git clone`) +
  offline wheelhouse.

## 7. References

- `docs/adr/ADR-0001-v1-baseline-and-product-form.md` — baseline, kernel boundary, DP + Option B lock.
- `docs/governance/V1_CANONICAL_TERMINOLOGY.md` — terms (incl. IN/SEAM/POST-V1, two ledgers).
- `docs/governance/V1_GOVERNED_ENVIRONMENT_GUARD_REQUIREMENT.md` — guard predicate requirement (RV1-012).
- `docs/governance/V1_DEV_CONTAINER_SEAM_CONTRACT.md` — v1.1 dev-container seam (RV1-013).
- `specs/_traceability_matrix.md` — RV1-011 (this doc) and the gate rows.
- `specs/_assumptions.md` §3–§6 — ledger correction, G4 reclassification, Option B contract.
- Option B re-issued roadmap §2–§4, §7, §8 — `5a7e5ba7…`.
