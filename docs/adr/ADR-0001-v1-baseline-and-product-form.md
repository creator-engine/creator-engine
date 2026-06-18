# ADR-0001 — Creator Engine v1.0 baseline, runtime-kernel boundary, and locked product form

- **Status:** Accepted (recorded at Gate 0; Source ratification pending at the Gate 0 boundary).
- **Date:** 2026-05-24
- **Gate:** G0 — SDD/TDD bootstrap + repo-state reconciliation (DOC).
- **Controlling roadmap:** Option B re-issued definitive roadmap, SHA256
  `5a7e5ba74adcaab32c892c3cf793384eec4f121a6991b1bd5bba34a30fd48e13`.
- **Authority basis:** Source Product-Form Decision Record (`14280f5e…`); Source Language/Packaging
  Decision Record (`6bd9b87d…`); Dual-Architect Reconciliation Note (`9723dd55…`).

> This ADR **records** locked decisions. It re-decides nothing and authorizes no implementation. The
> decisions below carry **no hedged or probabilistic wording** — they are locked.

---

## 1. Canonical baseline

**Decision.** The canonical Creator Engine v1.0 baseline is live **`refs/heads/main` =
`36377f8c4caf6817e01d58072062eb5caccc164b`**.

- The previously-ratified-but-blocked baseline `31229cdf9b1fe10f0cb64e111508ff6921112be6` is
  **superseded**; live main is 4 commits ahead of it (behind_by 0, clean fast-forward ancestry),
  carrying the PCO Slice 4 Side-Effect Ledger substrate, PCO orchestration docs, and the product
  roadmap update.
- The checked-out `remediation/oss-readiness-public-launch-blockers` branch (HEAD
  `e9f495334fa6e5ed3c486702c1a865e2806bcccb`) is **48 behind / 1 ahead** of the pinned baseline; it
  **predates the canonical substrate line** and is **not** authoritative.
- Reconciling the branch state (merge/rebase/reset/cherry-pick/branch deletion/force-push) is a
  separate Source-ratified Controller action. Gate 0 **records** the divergence and the per-artifact
  triage (`specs/_assumptions.md` §2); it does not **resolve** it by mutating git.

## 2. Local governed runtime kernel boundary

**Decision.** Creator Engine v1.0 is a **daemonless, repo-native, local command-line runtime** (`ce`).

- It executes on demand against repository-local `.hermes/` state and tracked substrate artifacts,
  then exits. It runs **no long-running daemon and no web server** as part of v1.0 runtime authority.
- Authority is the local process invoked by the Operator/Controller in the operator's shell; it is
  never delegated to a background service, a hosted endpoint, or a browser. **No network call is part
  of kernel authority.**
- Work execution is isolated in **rootless Podman**; the **host-local Controller seat is not
  containerized** in v1.0 (control authority stays host-side; only work execution is isolated). The
  operator-visible substrate is **tmux** (the only contract-conformant visible terminal, PCO-049).
- Canonical instance state lives under **`.hermes/`** (git-ignored). Tracked templates/protocols live
  under `templates/hermes/**` and `docs/operations/**`. The split is: **template/protocol → tracked;
  live instance state → `.hermes/` ignored.** (The Codex draft's `.ce/` layout and root
  `creator-engine` distribution rename are **not adopted** — see the dual-architect reconciliation.)

## 3. Locked product-form decisions (DP-1 / DP-2 / DP-3)

These are Source-ratified and locked. No later gate reopens them.

### DP-1 = A — canonical command / package identity

The canonical Creator Engine v1.0 command is **`ce`**. The Python distribution **remains
`creator-engine-validator`**; the `ce` console script is added to it and the
`creator-engine-validator` console script is **retained** as a back-compat/internal entrypoint.
**There is no distribution rename in v1.0.** `ce` **wraps** the existing validator subcommands
(`ce check` ≡ `creator-engine-validator check`); it does not fork a second CLI. The `ce`
console-script name is independent of the distribution name.

### DP-2 = B — v1.0 launch model

v1.0 ships a **deterministic launcher + Controller-seat-in-harness**. **`ce launch`** is the canonical
launch command; **`ce hud`** is an alias / seam label for the same launcher — **not** a commitment to a
CE-native HUD/TUI in v1.0. The chosen harness TUI **is** the v1.0 Controller seat (Hermes / Codex /
Claude Code `IN`; OpenClaw `SEAM`). A **CE-native HUD/TUI is POST-V1 / v1.1+**. There is no G-HUD gate
on the v1.0 critical path.

### DP-3 = B — development-environment containerization scope

v1.0 **containerizes worker/agent execution only**, with rootless Podman (rootful refused).
**Host-local development is permitted in v1.0**, guarded by an explicit governed-environment
predicate surfaced through `ce doctor` / `ce check` that **refuses ungoverned host drift**. **Mandatory
project-dev containerization (`ce dev shell` / `ce dev run`) is POST-V1 / v1.1.** There is no G-DEV gate
on the v1.0 critical path.

### Source add-on — v1.1 dev-container seam (deferred, not rejected)

The v1.1 project-dev-container seam is recorded now so v1.0 does not block it later: v1.0 keeps host
Controller state, worker/container state, and project-workspace boundaries distinct; the DP-3=B guard
predicate is designed so a future dev-container mode is a detectable/validatable PASS branch; the v1.0
Worker-Container Policy is the policy foundation a v1.1 dev profile reuses; and the `ce dev …` namespace
is reserved. v1.0 docs (G8) state the deferral explicitly. **Deferred, not rejected.**

## 4. Locked language/packaging contract (Source Option B / 1B — controlling §2.2)

**Decision.** v1.0 implementation language is **Python**, locked to the Source Option B / 1B contract
(Source Language/Packaging Decision Record `6bd9b87d…`, B1–B8 bundle). **Not reopened by any lane.**

- **Floor `requires-python = ">=3.14"`**; tested/current **target Python 3.14.x** (current stable patch
  3.14.5, released 2026-05-10). Floor = compatibility promise; target = what is built/tested/shipped.
- **3.13 intentionally excluded** (cleaner/narrower support + cp314-only wheelhouse simplicity);
  **3.11 / 3.12 rejected** as security-only floors; **3.15 invalid** (unreleased; planned 2026-10-01).
- **v1.0 wheelhouse is cp314-only** for Linux x86_64 and Linux aarch64; any later ABI
  widening beyond those architectures is a fresh Source decision.
- **Install is uv-first** with a **pip/`--no-index` fallback** retained for a uv-less host; no network
  fetch at install or runtime authority. **Reproducibility contract = `pyproject.toml` + `uv.lock`
  (per-file hashes) + offline wheelhouse**; `validators/requirements.txt` is a `uv export`-derived
  fallback/export artifact, not the primary lock contract.
- **Pinned deps `PyYAML==6.0.3` / `jsonschema==4.26.0`** with transitives (`attrs`,
  `jsonschema-specifications`, `referencing`, `rpds-py`) refreshed in lockstep.
- **Format split (B6/B7):** JSON Schema 2020-12 (schema language) unchanged; new machine evidence/ledgers
  use stdlib `json`; new operator/developer config uses TOML read via stdlib `tomllib` (read-only) or
  CE-managed JSON; existing `schemas/*.schema.yaml`, Spec Kit sidecars, and identity records remain YAML
  (read-only). **No TOML writer dependency** in v1.0. Schema language, schema serialization, and
  validation engine (`jsonschema`) are separate axes and must not be conflated.
- **Build backend `setuptools.build_meta`** retained; package stays nested at `validators/pyproject.toml`;
  no root distribution restructure; **DP-1 not reopened**. **`uvx` one-line install is POST-V1 (B3).**

**Implementation of this contract is Gate 6 (RV1-060).** Gate 0 only records it here and in
`specs/_traceability_matrix.md`. **Gate 0 authors no packaging/dependency/wheelhouse change.**

## 5. Side-Effect Ledger reconciliation (live-main correction)

The Side-Effect Ledger **substrate** (schema, validator check, `scan-side-effect-ledger`, well-formed +
malformed examples, unit/integration tests, `docs/operations/SIDE_EFFECT_LEDGER_PROTOCOL.md`) is
**built on live main under PCO Slice 4** as a read-only evidence index; the **G4 runtime CLI**
(`ce ledger record` / `ce ledger verify`, append/hash-chain/replay per RV1-041) **remains a gap**. The
Side-Effect Ledger is **distinct** from the Active-Work Ledger. The prior contrary absence claim is
superseded. Roadmap **G4 must be reclassified by Source** from "build from scratch" to
"reconcile + complete the remaining runtime"; Gate 0 flags this (`specs/_assumptions.md` §3–§4) and does
not re-decide it.

## 6. Consequences

- All v1.0 implementation builds on live main `36377f8…`; "landed" means landed on `refs/heads/main`.
- The product form has **no unresolved forks**: DP-1/DP-2/DP-3 and the Option B language/packaging
  contract are locked, enabling the Gate 1 terminology/contract lock to proceed.
- Gate 0 introduces **no** CLI/runtime/container/schema/validator/test/config change and **no**
  packaging/dependency/wheelhouse work; it produces only the SDD spine (`specs/_status.md`,
  `specs/_traceability_matrix.md`, `specs/_assumptions.md`) and this ADR.

## 7. References

- Option B re-issued definitive roadmap — `5a7e5ba7…` (§0, §1, §2, §4, §6, §7).
- Gate 0 SDD bootstrap implementation envelope — `f5df5f0a…` (amended by the re-pinned prompt §9).
- Source Product-Form Decision Record — `14280f5e…`; Dual-Architect Reconciliation Note — `9723dd55…`.
- Source Language/Packaging Decision Record (Option B / 1B, B1–B8) — `6bd9b87d…`.
- Gate 0 baseline-refresh architect report — `21b092fa…`; verification notes — `47910a90…`.
- `specs/_status.md`, `specs/_traceability_matrix.md`, `specs/_assumptions.md` (this gate).
