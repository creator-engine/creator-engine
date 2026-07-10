# CE Work-Management Process — SSOT

> **Status:** canonical. Operator-ratified 2026-06-30. This is the single source of truth for how work flows in CE (analogous to `infra/identity-registry.yaml` for topology). On conflict with scattered docs, this wins. Home: `ce-ops/process/work-management.md`.

## 1. Purpose
Defines the end-to-end flow — **opened → classified → backlog → arc lane → worked → shipped** — plus the canonical vocabulary. Its absence let commissioned work (e.g. ce-ops#37) become invisible and rot.

## 2. The hierarchy (strategic → execution, telescoping by time)
| Layer | Definition | Horizon | Home |
|---|---|---|---|
| **Roadmap** | the program plan: where CE is going | months | `ce-ops/roadmaps/v3.5-roadmap.md` (THE roadmap) |
| **Workstream** | a durable theme of the roadmap (WS-1…WS-7) | months | roadmap §; `ws:*` labels |
| **Milestone** | a dated delivery target | weeks–months | GitHub milestone (e.g. "Sept NVIDIA pitch") |
| **Wave** | a sequenced phase toward a milestone | weeks | roadmap §4 (Wave A–D) |
| **Arc** | an Operator-ratified execution **shift** with authority grants (G/R) + lanes | hours–days | `.ce/state/research/DAYARC_*` |
| **Lane** | a parallel work segment **within an arc** (L1…Ln) | a shift | arc mandate |
| **Ticket** | the unit of work | — | a ce-ops issue |

> Arc-internal sequencing of a lane's work uses **"Batch"** (not "Wave"). Durable design programs (formerly the persistent "Lane:" issues #1–7) are **"Program:"** (not "Lane").

## 3. Classifying a ticket — three ORTHOGONAL axes
A ticket is tagged on three independent axes. Do not collapse them into one label.
| Axis | Question | Mechanism |
|---|---|---|
| **Type** | what kind of work? | issue-type label: `feature` / `fix` / `chore` / `research` / `design` / `process` / `epic` |
| **Schedule** | when? | Milestone membership + Backlog Status. *Undefined schedule = invisible — forbidden for commissioned work.* |
| **Work-class** | how big is the resulting PR? | **XS / S / M / L** (see §4) — PR-level, set in the PR body, enforced by `ce validate-pr` |

> Historical note: the `user-story` label conflated Type with "deferred." Retired — Type and Schedule are separate axes.

## 4. Work-class (PR size gate) — XS / S / M / L
The work-class is the **realized PR size**, enforced by `work_sizing_floor` against the PR diff. Metric (ratified): **included diff LOC** (→ evolve to diff token-count later).
| Class | Included diff LOC |
|---|---|
| **XS** | < 400 |
| **S** | 400–799 |
| **M** | 800–1000 |
| **L** | > 1000 |
PR body carries exactly one line: `- **Declared work class:** <XS\|S\|M\|L>`. (During migration, old `tiny/story/feature/epic` are accepted as back-compat aliases.)

> **`effort_estimate`** (separate, planning-only): an agent-effort *forecast* (agent-tokens or agent-hours) attached to a ticket at shaping time. Informs sequencing; does **not** gate a PR (not diff-computable).

## 5. Backlog & promotion (the layer that was missing)
- **Backlog = the GitHub Projects v2 board** (org project 1) — the live SSOT for ticket status. Fields: **Status** (Queued / In-flight / In-review / Done) + **Anchor** (milestone). Every open ticket has a board row; the board is kept current.
- **Promotion (Backlog → Arc Lane):** each arc explicitly promotes tickets from the Backlog into its lanes per Roadmap priority. This is a named arc step, not implicit hand-wave.
- **Safety-net (ce-ops#376 sweep):** a periodic sweep surfaces OPEN tickets that are unscheduled (no milestone, not on the board, not in the active arc) — especially Operator-commissioned ones — into arc triage, so nothing silently rots.

## 6. Triage (the function, two halves)
- **triage-planner** (`ce-ops/ce_triage/`): computes the advisory Ready Queue (ce-ops#67) from `Depends-on/Gated-on` trailers. Advisory only — never ratifies/dispatches.
- **pickup-filter** (`validators/.../forge_triage.py`): what a seat may CLAIM — filters by `ce-pickup/triage-ready` minus blockers/holds.

## 7. Naming canon (disambiguations — RATIFIED)
| Term | Canonical meaning |
|---|---|
| **Lane** | a segment within an arc, only |
| **Program** | a durable design program (the former persistent "Lane:" issues) |
| **Roadmap** | the program plan (`v3.5-roadmap.md`), only. `docs/product/ROADMAP.md` → **"Feature Map"**; the triage rollup label → **`aggregate`** |
| **Wave** | a roadmap phase; arc-internal sequencing → **"Batch"** |
| **Work-class** | PR size XS/S/M/L; never reuse Type words |
| **Backlog** | the Projects v2 board |
| **Triage** | the intake/readiness function (planner + pickup-filter) |
