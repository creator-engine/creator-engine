# Feasibility & Usability Assessment — "Playbooks/Runbooks → Skills + CE Plugin"

Date: 2026-06-27
Author seat: research worker (read-only on code; writes this plan)
Doctrine anchor: [[ce-codified-actions-not-rediscovery]] — reconstructing an ops procedure by reading a playbook each time is the bug; the fix is self-verifying, agent-invokable SSOT actions.
Reconciles: ce-ops#248 (`ce playbook run`, CLOSED/SHIPPED), ce-ops#145 (playbook format scaffold).

---

## 0. TL;DR — HYBRID, GO on a narrow pilot

**Verdict: HYBRID (GO on a tightly-scoped pilot, NO-GO on a "convert everything" program).**

Skills are a genuine **redundancy / ergonomics layer** for the controller, not a replacement for the playbook SSOT and not a replacement for `ce playbook run`. The win is real but narrow: a Skill turns "open `playbooks/controller/briefs/dispatch.md`, re-derive the pointer+SHA dance, then act" into a single named, progressively-disclosed invocation whose body is *already in the controller's procedural muscle*. That cuts rediscovery latency and per-dispatch token cost.

But three hard constraints bound the scope:

1. **The action SSOT must stay singular.** We already have two layers (in-tree `playbooks/**` + `ce playbook run` runtime). A Skill must be a **thin pointer into one of those**, never a third hand-authored copy of the procedure, or we manufacture exactly the drift the doctrine forbids.
2. **Governance cannot ride on the Skill.** Current Claude Code `allowed-tools` skill-frontmatter restriction is **parsed-but-unenforced** (confirmed June 2026, issues #37683 / #18837). A Skill grants *no* containment and *no* gate. All safety must continue to ride on CE's existing `PreToolUse` hook seam.
3. **Skills are Claude-Code-only.** Codex worker seats (the fleet's default per [[codex-first-routing-directive]]) cannot consume a SKILL.md. So a skills bundle helps the **controller** (Claude Code) and any Claude-Code seats — it is not a fleet-wide mechanism. `ce playbook run` remains the harness-agnostic path.

### Candidate-skill shortlist (pilot order)

| # | Skill | Backs onto | Mutating? | Pilot phase |
| - | ----- | ---------- | --------- | ----------- |
| 1 | `ce-dispatch` | `playbooks/controller/briefs/dispatch.md` + [[ce-seat-dispatch-prompt-pointer-sha]] | read-mostly (writes a brief/claim file) | **Pilot 1** |
| 2 | `ce-merge-gate` | `playbooks/controller/briefs/merge-gate.md` | **mutating (gate)** — checklist only, never auto-merges | **Pilot 1** |
| 3 | `ce-seat-refresh` | `playbooks/controller/briefs/seat-refresh.md` | read-only (instructs a seat) | Phase 2 |
| 4 | `ce-harvest` | controller habit (extract→validate→push) + `ce validate-pr` | mutating (push) — runs validate, drafts push | Phase 2 |
| 5 | `ce-launch` | `docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md` | mutating (spawns seat) | Phase 2 |
| 6 | `ce-playbook` (meta) | wraps `ce playbook list/show/run` | per-playbook | Phase 3 (plugin) |

### ce-ops tickets to open

- **ce-ops#NEW-A** — Pilot: `ce-dispatch` + `ce-merge-gate` skills under `.claude/skills/` (controller-local, internal-only), each a thin pointer to the in-tree playbook brief; no embedded procedure copy.
- **ce-ops#NEW-B** — Governance guard: a CI/validator check that asserts every CE action-skill references an in-tree playbook/CLI SSOT and contains **no** mutating forge command in its body (defense-in-depth against drift + against a skill smuggling a gate-bypass).
- **ce-ops#NEW-C** — `ce-operations` plugin scaffold (`.claude-plugin/plugin.json` + `skills/` + bundled `PreToolUse` hook = the CE hook-check shim). Internal marketplace only. Graduation-gated per [[ce-herdr-command-internal-then-public]].
- **ce-ops#NEW-D** — Decision spike: should the shipped public surface be **skills-over-`ce` commands** (skill body = "run `ce playbook run X`") so the action stays SSOT in the CLI? Reconcile with ce-ops#248's already-shipped `ce playbook run`.

---

## 1. Skill / Plugin Mechanics (grounded in current Claude Code docs, June 2026)

### 1.1 SKILL.md format

- Lives at `.claude/skills/<name>/SKILL.md` (project), `~/.claude/skills/<name>/SKILL.md` (user), or bundled in a plugin at `<plugin>/skills/<name>/SKILL.md`.
- Frontmatter fields that matter for us:
  - `name` — becomes the `/name` slash command.
  - `description` — **the load-bearing field for model-invocation.** Encodes *what* + *when*. This is what sits in context at ~100 tokens/skill and decides auto-trigger.
  - `disable-model-invocation: true` — user-only (`/name`); Claude won't auto-fire. **This is the right default for any mutating CE action** (dispatch, merge-gate, harvest) so the gate-touching action is never auto-triggered. (Caveat: open bug #26251 can over-block explicit `/name` for *plugin* skills; mitigate by piloting at user/project level, not plugin, first.)
  - `user-invocable: false` — Claude-only, hidden from slash menu; good for pure background-knowledge skills, not for our actions.
  - `allowed-tools` — **documented but UNENFORCED as of June 2026 (#37683/#18837).** Treat as a no-op for governance. Do not rely on it.
  - Supporting dirs alongside SKILL.md: `scripts/` (executables), `references/` (lazy-loaded docs), `assets/`.

### 1.2 Invocation model

- **User-invocable**: `/skill-name [args]`; args reach the body via `$ARGUMENTS` (and `$1`…).
- **Model-invocable**: Claude reads the `description` at startup and auto-invokes when the task matches. Combat *under*-triggering with a "pushy" description; combat *over*-triggering (for mutating actions) with `disable-model-invocation: true`.

### 1.3 Token / progressive-disclosure model — the core efficiency claim

Three tiers:
1. **Startup**: only `name` + `description` (~100 tokens/skill). 8 skills ≈ 500 tokens resident vs. ~70k if all bodies loaded — the headline efficiency argument.
2. **Invocation**: full SKILL.md body loads (~1–5k tokens) only when fired.
3. **Lazy**: `references/*` stay on disk until the body's instructions cause Claude to read one.

This maps **directly** onto the doctrine: the procedure is *resident-by-name* (no rediscovery), but its full text only enters context when actually needed (no permanent bloat). This is strictly better than today's "controller reads `playbooks/controller/briefs/dispatch.md` from disk each time."

### 1.4 How a plugin bundles things

- `<plugin>/.claude-plugin/plugin.json` (manifest: name, version, description; can inline hooks/settings). **Only `plugin.json` goes in `.claude-plugin/`.**
- At plugin root: `skills/`, `agents/`, `commands/`, `hooks/hooks.json`, `.mcp.json`, `settings.json`.
- Namespacing: plugin `ce-operations` → `/ce-operations:dispatch`. Prevents collision with speckit skills already present in this repo.
- Distribution: `marketplace.json` in a registry repo; `/plugin install`; or local `claude --plugin-dir ./ce-operations` for dev. Versioning explicit (`version`) or implicit (commit SHA). **Private GitHub marketplace** is supported → fits internal-only-then-public graduation.

### 1.5 openclaw pattern (relevance)

Steinberger's openclaw bundles operational skills with a **precedence hierarchy** (bundled → global → workspace, workspace wins). The borrowable convention for CE: ship a `ce-operations` plugin as the bundled baseline, but let a seat/host shadow a skill via `~/.claude/skills/` for per-host quirks **without forking the SSOT**. We should adopt the *hierarchy* idea but keep the **procedure body pointing at the in-tree playbook**, so an override changes invocation ergonomics, never the governed procedure.

---

## 2. Playbook Inventory + Skill-Candidacy

Full inventory of `playbooks/**` (31 files across 4 playbooks). Classification: **REFERENCE** (stays a doc) / **ACTION** (good skill: thin pointer) / **JUDGMENT** (must NOT be made rote).

### controller/ (role-action) — the primary target

| Brief / file | Content | Class | Skill? |
| ------------ | ------- | ----- | ------ |
| `briefs/dispatch.md` | "name ticket/branch/role/paths/evidence/stop-line; record work claim" | **ACTION** | **YES — `ce-dispatch`** (pilot). Mechanical, the controller does it constantly, has a memorized pointer+SHA protocol [[ce-seat-dispatch-prompt-pointer-sha]] worth codifying. |
| `briefs/merge-gate.md` | "confirm independent review + green checks + ratification; else don't merge" | **ACTION (gate)** | **YES — `ce-merge-gate`** (pilot) — but **checklist-only**. Skill asserts the three gates and *stops*; the human-ratified merge stays a separate, explicit step. Never auto-merge from the skill. |
| `briefs/seat-refresh.md` | "save resume state, clear, resume from precise state file" | **ACTION** | **YES — `ce-seat-refresh`** (phase 2). Read-only w.r.t. forge. |
| `briefs/courier-forge-op.md` | ADR-0007 model-b courier dance | **JUDGMENT/SUNSET** | **NO.** Sunsets when the egress gateway lands; rote-ifying a soon-dead, identity-sensitive path is wrong. Keep as doc. |
| `workflow.ce.yml`, `harness.md`, `envelope.template.yml`, `README.md` | descriptor / contract / scope skeleton | **REFERENCE** | NO — these *are* the SSOT a skill points at. |

### author/ (role-action)

| Brief | Class | Skill? |
| ----- | ----- | ------ |
| `briefs/base-only-refresh.md` ("rebase, re-pin hashed artifacts, validate, push, no fresh ratification") | **ACTION** | **MAYBE — `ce-base-refresh`** (phase 2/3). Highly mechanical and a frequent source of churn; good skill candidate, but author-seat work (often codex → can't consume a skill). Better expressed as `ce playbook run` step. |
| `briefs/address-review.md` ("read findings, smallest fix or justify, push, report map") | **JUDGMENT** | NO — fixing is judgment; only the push/report mechanics are rote. Keep doc. |
| `workflow/harness/envelope/README` | **REFERENCE** | NO. |

### reviewer/ (role-action)

| Brief | Class | Skill? |
| ----- | ----- | ------ |
| `briefs/review.md` ("inspect diff, lead with findings by severity, approve/comment") | **JUDGMENT** | NO — review is the canonical judgment act; must never be rote ([[ce-dismiss-is-not-approve]]). |
| `briefs/re-review.md` | **JUDGMENT** | NO. |
| `briefs/refresh-seat.md` ("save state, clear, resume; confirm reviewer ≠ author") | **ACTION** | Folds into `ce-seat-refresh` with a "reviewer ≠ author" guard. Phase 2. |
| `workflow/harness/envelope/README` | **REFERENCE** | NO. |

### computer-use-ticket/ (workflow)

| Brief | Class | Skill? |
| ----- | ----- | ------ |
| `prepare-ticket`, `connect-browser`, `execute-change`, `capture-evidence`, `closeout` | mostly **WORKFLOW/ACTION** but browser-bound, low-frequency, already executable as a `ce playbook run` workflow | **NO (defer).** This is exactly what `ce playbook run` was built for (ce-ops#248 `command`/`expected_result` steps). Don't duplicate into skills. |

### Non-playbook ACTION candidates named in the brief

- **`ce-harvest`** — the controller's extract→validate→push habit (no formal playbook today). Strong skill candidate *because* it has no SSOT doc — but the skill body must point at `ce validate-pr` (ce-ops#252) + the conveyor/intake directive, not embed a fresh procedure. Phase 2.
- **`ce-launch`** — backed by `docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md`. Mutating (spawns a seat). Phase 2.

**Summary counts:** ~5 ACTION skill candidates worth building (`ce-dispatch`, `ce-merge-gate`, `ce-seat-refresh`, `ce-harvest`, `ce-launch`), ~4 JUDGMENT briefs that must stay docs (reviews, address-review, courier-forge-op), the rest REFERENCE scaffold (the SSOT itself) + one workflow (computer-use) better served by `ce playbook run`.

---

## 3. Usability / the "Redundancy" Value

### Does a skill layer measurably cut rediscovery + tokens + drift vs. reading playbooks?

- **Rediscovery (latency + cognitive):** YES. Today the controller must (a) remember the playbook exists, (b) open `playbooks/controller/briefs/dispatch.md`, (c) re-derive the pointer+SHA mechanic from [[ce-seat-dispatch-prompt-pointer-sha]] (which lives in memory, not the brief). A `/ce-dispatch` skill collapses (a)+(b)+(c): the `description` keeps it resident-by-name, the body carries the *combined* brief + memorized mechanic. This is the doctrine's "self-verifying agent-invokable action" almost verbatim.
- **Token cost:** YES, modestly. Progressive disclosure means the procedure costs ~100 tokens resident vs. a full file-read (a `Read` of the brief + re-reading memory each dispatch). Across a saturated 6-thread conveyor day this is non-trivial.
- **Drift:** NEUTRAL-to-NEGATIVE **unless** the skill is a thin pointer. A hand-copied procedure in SKILL.md is a *new* drift source. The mitigation (ce-ops#NEW-B guard) is mandatory: a skill must reference an in-tree SSOT and not restate it.

### Concrete before/after

**Harvest — before:** controller recalls "extract the seat's commit, validate, push as the seat identity"; greps for the side-effect ledger protocol; re-derives the validate command set; runs `ce validate-pr` (if it remembers it exists); drafts the push. ~Several tool calls + memory recall, repeated per harvest.

**Harvest — after (`/ce-harvest <seat> <branch>`):** skill body, resident-by-name, says: "1) confirm work claim; 2) run `ce validate-pr` (SSOT); 3) on green, draft the push as the seat identity per courier rule; 4) record ledger evidence per `SIDE_EFFECT_LEDGER_PROTOCOL.md`. STOP before any forge mutation that lacks ratification." One invocation, the gate steps inlined, the SSOT commands referenced not re-derived.

**Dispatch — before:** open brief → fill envelope → recall pointer+SHA mechanic (`save seed to file → send pointer + sha256`) → check territory map → record claim. ~4–6 steps reconstructed each time.

**Dispatch — after (`/ce-dispatch`):** body carries the brief + the pointer+SHA mechanic + the territory-map check + the claim step as a single checklist; `description` keeps it resident. Controller fills ticket-specific fields only.

### How skills compose with the worker-dispatch model

- Skills live on the **controller** (Claude Code), which already holds the dispatch role. `/ce-dispatch` *produces* the brief that gets sent to a (codex) worker; it does not require the worker to understand skills. Clean fit.
- Skills do **not** compose into the worker seats themselves (codex). So this is a controller-ergonomics layer, deliberately. `ce playbook run` remains the harness-agnostic execution path for worker-side workflows.

---

## 4. Governance / Safety

Action-skills for `dispatch`, `harvest`, `merge-gate` touch the gate/forge. Keeping human-ratification + no-self-approval when the action is "one command":

1. **The Skill grants no authority.** A SKILL.md is just instructions Claude reads; it carries no containment and (because `allowed-tools` is unenforced — #37683) no tool restriction. **Therefore the gate must NOT be expressed in the skill.** It must ride on CE's existing `PreToolUse` `hook-check` seam — the same seam `ce playbook run`'s `default_step_executor` already uses (every command routed through `hook-check`, deny → exit 121). Mutating skills inherit that protection only because the *underlying CLI/hook* enforces it, not because the skill does.
2. **No-self-approval / no-auto-merge.** `ce-merge-gate` must be **checklist-only**: it asserts independent review + green + ratification and **stops**. It must contain zero merge command. The merge stays a separate, explicit, human-ratified act ([[ce-dismiss-is-not-approve]], [[ce-257-resign-merge-grant]]). Enforce via ce-ops#NEW-B: a validator that rejects any CE action-skill body containing a mutating forge command (`gh pr merge`, `git push`, `gh pr review --approve`, etc.).
3. **Mutating vs. read-only split.** Tag each skill:
   - **Read-only / drafting** (`ce-dispatch` drafts a brief, `ce-seat-refresh` instructs a seat) → low risk, can be `disable-model-invocation: false` if desired.
   - **Mutating** (`ce-harvest` pushes, `ce-launch` spawns) → **`disable-model-invocation: true`** (user-only), and the mutation itself goes through `ce`/hook seam, never a raw command embedded in the skill.
4. **Defense in depth.** Even though governance lives in the hook, the ce-ops#NEW-B guard makes the *skill itself* incapable of smuggling a gate-bypass — important because a future edit could otherwise quietly add a `gh pr merge` line.

---

## 5. Product Lens + Reconcile ce-ops#248

### Current state of ce-ops#248 (verified)

ce-ops#248 is **CLOSED / SHIPPED** (changelog `ce248-playbook-run-exec.md`, 2026-06-26). `ce playbook list/show/run` exist (`validators/creator_engine_validator/ce_cli.py` → `playbook_runtime.run_cli`). The runtime parses dual-use `PLAYBOOK.md` frontmatter, projects it onto the internal `workflow.ce.yml` descriptor/schema, and the live executor routes **every `command` step through the CE `hook-check` governance seam** before running it (`default_step_executor`). Dry-run plans without executing. This is the harness-agnostic, governed SSOT execution path and it already works.

### Relationship — skills ARE NOT a competitor to `ce playbook run`; they are a different layer

| Layer | Audience | Strength | Weakness |
| ----- | -------- | -------- | -------- |
| `playbooks/**` (in-tree) | seats + humans, any harness | the SSOT; PR-mediated; validated | must be read each time → rediscovery |
| `ce playbook run` (#248) | any harness (codex + claude) | governed execution; hook-gated; dry-run | a CLI invocation the controller must remember to call |
| **Skills (proposed)** | **Claude-Code controller only** | **resident-by-name; progressive disclosure; zero-rediscovery** | **Claude-Code only; no governance of its own; can drift if it copies** |

### The reconciliation — **skills-over-`ce`-commands (recommended)**

To keep the action SSOT singular, the recommended pattern is **skill body = "run the corresponding `ce` command,"** not "skill body = a re-authored procedure." Concretely:

- `/ce-dispatch`'s body says: *fill these ticket fields, then dispatch per `playbooks/controller/briefs/dispatch.md`; record claim.* It points; it does not restate.
- A `ce-playbook` meta-skill's body is literally: *run `ce playbook run <id>` (or `--dry-run` first); surface PASS/FAIL.* The procedure stays in the CLI/playbook; the skill only removes rediscovery friction.

This makes skills a **thin ergonomic veneer over the #248 CLI + in-tree playbooks** — exactly the "redundancy layer" framing in the brief, with the SSOT untouched. ce-ops#NEW-D is the explicit decision spike to ratify this "skills-over-commands" pattern repo-wide.

### Internal-only vs. shippable

- **Internal first.** Per [[ce-herdr-command-internal-then-public]] and [[ce-public-docs-product-lens-doctrine]], a `ce-operations` plugin with controller-ops skills is **internal machinery** (dispatch/merge-gate/courier are the internal governance loop — NOT product surface). It must NOT ship in the public README or public marketplace, and skill descriptions must carry **zero ce-ops# refs**.
- **Graduation path.** A *subset* could become product: a public `ce` user's own controller benefits from `/ce-merge-gate` and `/ce-playbook`. Those graduate to a public marketplace plugin later, product-lensed, after internal maturity — same internal-then-public arc as `ce herdr`.

---

## 6. Recommendation — HYBRID

### GO / NO-GO / HYBRID: **HYBRID**

GO on a 2-skill internal pilot that proves the ergonomics + the governance-via-hook story; NO-GO on any "convert all playbooks to skills" program (most briefs are REFERENCE or JUDGMENT, and codex seats can't consume skills). The default product execution path stays `ce playbook run`.

### Architecture

```
.claude/skills/                      # PILOT — controller-local, project-scoped
  ce-dispatch/SKILL.md               # thin pointer → playbooks/controller/briefs/dispatch.md + pointer+SHA mechanic
  ce-merge-gate/SKILL.md             # checklist-only; zero merge command; disable-model-invocation:true

# ...graduates to...

plugins/ce-operations/               # PHASE 3 — bundled, internal marketplace
  .claude-plugin/plugin.json
  skills/{ce-dispatch,ce-merge-gate,ce-seat-refresh,ce-harvest,ce-launch,ce-playbook}/SKILL.md
  hooks/hooks.json                   # PreToolUse → CE hook-check shim (the real gate)
  references/                        # lazy-loaded copies/links of the in-tree briefs
```

Governance invariant (all phases): **the gate lives in the `PreToolUse` hook (same seam as `ce playbook run`), never in skill frontmatter.** `allowed-tools` is treated as non-functional.

### Prioritized candidate-skill list

1. `ce-dispatch` (pilot) — highest frequency, has a memorized mechanic worth codifying.
2. `ce-merge-gate` (pilot) — highest governance value; proves the checklist-only/no-self-approval pattern.
3. `ce-seat-refresh` (phase 2) — read-only, easy, frequent.
4. `ce-harvest` (phase 2) — high value (no SSOT today) but must wait on `ce validate-pr` (ce-ops#252).
5. `ce-launch` (phase 2) — mutating; backs onto the seat-launch runbook.
6. `ce-playbook` meta (phase 3) — wraps `ce playbook run`; the cleanest "skills-over-commands" exemplar.

### Risks

- **R1 — Drift (a third copy of the procedure).** *Highest risk.* Mitigation: ce-ops#NEW-B validator (skill must reference an in-tree SSOT, must not restate it, must contain no mutating forge command).
- **R2 — False sense of governance.** A reader may assume the skill gates the action. It does not. Mitigation: governance stays in the hook; document loudly; the NEW-B guard makes the skill body structurally incapable of holding a mutating command.
- **R3 — `allowed-tools` / `disable-model-invocation` plugin bugs (#37683, #26251, #22345).** Mitigation: pilot at **project/user level** (not plugin) where invocation control works; rely on hooks for tool gating; only move to a plugin (phase 3) once the bug status is re-checked.
- **R4 — Codex seats can't consume skills.** Mitigation: scope skills explicitly to the controller; keep `ce playbook run` as the fleet-wide path. Don't over-sell skills as fleet infrastructure.
- **R5 — Public-surface leak.** Internal ops skills must not ship publicly or carry ce-ops# refs. Mitigation: internal marketplace only; [[ce-public-docs-product-lens-doctrine]] applies; graduation-gated.

### Phased plan

- **Pilot (1–2 skills):** `ce-dispatch` + `ce-merge-gate` under `.claude/skills/` (project-scoped, internal). Each a thin pointer; `ce-merge-gate` checklist-only with `disable-model-invocation: true`. Measure: dispatch/merge rediscovery steps before vs. after; confirm the hook still gates a deliberately-bad merge attempt. → **ce-ops#NEW-A**.
- **Guard:** land the drift/no-mutating-command validator before adding more skills. → **ce-ops#NEW-B**.
- **Phase 2:** add `ce-seat-refresh`, `ce-harvest` (after #252), `ce-launch`. Still project/user-level.
- **Phase 3 (plugin):** package as internal `ce-operations` plugin with a bundled `PreToolUse` hook-check shim; private marketplace. → **ce-ops#NEW-C**.
- **Decision spike (parallel):** ratify "skills-over-`ce`-commands" as the SSOT-preserving pattern, reconciled with #248. → **ce-ops#NEW-D**.

### Concrete ce-ops tickets

- **ce-ops#NEW-A** — Pilot `ce-dispatch` + `ce-merge-gate` skills (project-scoped, internal-only, thin pointers).
- **ce-ops#NEW-B** — Validator guard: CE action-skills must reference an in-tree SSOT and contain no mutating forge command.
- **ce-ops#NEW-C** — `ce-operations` internal plugin scaffold + bundled hook-check `PreToolUse` shim; private marketplace.
- **ce-ops#NEW-D** — Decision spike: "skills-over-`ce`-commands" pattern; reconcile with shipped `ce playbook run` (#248).

---

## Appendix — Key facts pinned

- `allowed-tools` skill frontmatter is **parsed but NOT enforced** (Claude Code, June 2026; issues #37683, #18837). Governance must use `PreToolUse` hooks.
- `disable-model-invocation: true` has bug #26251 (can over-block explicit `/name`) and plugin-skills bug #22345 — pilot at project/user level first.
- Progressive disclosure: ~100 tokens/skill resident (name+description); full body only on invocation; `references/*` lazy. ~140x efficiency vs. loading all bodies.
- `ce playbook run` (#248, CLOSED/SHIPPED) already routes every step `command` through CE `hook-check` (`default_step_executor`, deny→exit 121) — the existing governed execution seam skills should *point at*, not duplicate.
- Plugins: `.claude-plugin/plugin.json` only in `.claude-plugin/`; `skills/`,`agents/`,`hooks/hooks.json` at plugin root; namespaced as `/plugin:skill`; private GitHub marketplace supported (fits internal-then-public).
- Codex worker seats cannot consume SKILL.md → skills are a controller (Claude-Code) ergonomics layer, not fleet infrastructure.
