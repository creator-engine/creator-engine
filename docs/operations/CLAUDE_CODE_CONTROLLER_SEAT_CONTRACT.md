# Claude Code Controller-Seat Contract

**Gate**: CC-G-A — Claude Code Controller-seat contract (extends PCO v1 Gate 1 + Gate 2).
**Requirement**: RV1-CC-001 / RV1-CC-002 / RV1-CC-003.
**Type**: Governance document only. **No runtime code.** Strict-TDD runtime work is deferred to later gates.
**Status**: Contract authored. The hook-pack (`.claude/settings.json`, `.claude/hooks/**`), the
`creator_engine_validator hook-check` bridge, the completion-report schema/checks, and the
`ce lane launch` / `ce launch` Claude adapter are **all later gates and are not implemented here**.

---

## 1. Purpose and scope

This document defines, in tracked governance, what a **governed Claude Code Controller seat** is for
Creator Engine (CE) v1.0: the required launch posture, the prohibited flags and modes, the required
hook-pack presence as a later-gate dependency, the governed-posture predicate, and the seat↔harness
classification — so that the lane-launch primitive (Gate 3) and the deterministic launcher (Gate 6)
have a contract to validate against.

This document is **declarative and authorizes nothing**. Reading, authoring, or validating this
contract does **not** launch a pane, call Claude Code, install hooks, write settings, call GitHub,
call any network API, or mutate runtime state. It is a contract artifact, not a runtime command.

CE is a deterministic governance substrate over a probabilistic coding agent. It does not make the
model deterministic; it makes the *state transitions around the model* deterministic. Claude Code is
one of the harnesses that may occupy the **Controller seat** (alongside Hermes and Codex). This
contract specifies how that seat is constrained so the Claude harness is governed rather than free.

## 2. What a governed Claude Code Controller seat is

A **governed Claude Code Controller seat** is a Claude Code session that:

1. runs as the **visible tmux pane** that CE observes and archives (never a hidden, headless, or
   background surface);
2. is launched with a pinned, auditable flag/settings posture (§4) and free of every prohibited flag
   or mode (§5);
3. operates under a **governed posture predicate** (§7) that binds the live pane to a
   `.hermes/pane-registry` record and an unreleased Active-Work claim;
4. carries CE's law from committed governance and ratified handoffs — not from chat-pasted prompt
   bodies — and relays work via pointer-only prompts (path + expected SHA256 + verify-before-consume);
5. when the in-band hook-pack is later present and confirmed loaded (a later gate, §6), is subject to
   real-time scope, mechanics, secret, and completion gates inside the lane.

The Controller seat is the orchestrating seat: it prepares bounded handoffs, relays pointer-only
prompts, verifies evidence, archives transcripts, runs scope audits, and executes Source-ratified
mechanics. **The Controller seat is not automatically the Implementer and is not the ratifier.**
Claude Code's native instinct is to author code; this contract exists in part to keep the Controller
seat from collapsing into the Implementer seat.

Related tracked governance: [`CONTROLLER_BOUNDARY_POLICY.md`](CONTROLLER_BOUNDARY_POLICY.md),
[`CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md`](CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md),
[`CONTROLLER_IDENTITY_PROTOCOL.md`](CONTROLLER_IDENTITY_PROTOCOL.md).

## 3. Enforcement-strength vocabulary

This contract classifies every mechanism on an explicit strength axis. The terms are used precisely
throughout and must not be blurred:

1. **HARD** — a mechanism mechanically blocks or fails and cannot be talked around in-band: kernel
   refusal, non-overridable managed policy, SHA mismatch halt, `--match-head-commit` merge refusal,
   schema parse rejection. The Ring 0 kernel (`ce lane launch` / `ce launch`) refusing to launch or
   verify an ungoverned lane is the HARD repo-native floor.
2. **VALIDATOR** — an offline/deterministic check that establishes facts after the fact and fails
   non-zero (the `creator_engine_validator` checks). HARD when wired into a gate that must pass;
   advisory when run in whole-tree mode.
3. **RUNTIME (launch-pinned)** — an in-band runtime gate that blocks during the session but is
   *defeasible by local override* (a committed `.claude/settings.json` hook, which `--bare`,
   `settings.local.json`, or CLI `--setting-sources` can bypass). Stronger than prompt, weaker than
   HARD.
4. **PROMPT/SKILL** — a behavioral instruction (`CLAUDE.md`, memory, skills, this contract's prose).
   Useful, never sufficient alone.
5. **FUTURE SEAM** — a designed interface present but with implementation deferred (managed settings,
   http hooks, plugin-packaged hook distribution, team-mode).

The honest layering: the committed Claude hook-pack, when it ships, is **RUNTIME** strength — strong
but locally defeasible. The HARD floor is the Ring 0 kernel. The non-overridable host lock (managed
settings) is a **FUTURE SEAM** for v1.1. See §8.

## 4. Required launch flags / settings-source constraints

A governed Claude Code Controller seat **must** be launched with:

| Constraint | Requirement | Strength |
|---|---|---|
| `--model` | Explicit model pin (e.g. `--model claude-opus-4-7` for reasoning-heavy Controller work; Sonnet for simple lanes). No implicit default model. | RUNTIME (kernel-pinned at Gate 6) |
| `--effort high` | Controller reasoning runs at high effort. | RUNTIME |
| `--setting-sources project` | Settings load from the committed `project` source (plus managed where present). The governed launch **must pin `--setting-sources` to exclude `local`**, so `settings.local.json` cannot weaken the posture. | RUNTIME → HARD at Ring 0 (Gate 3/Gate 6) |
| Visible tmux pane | The seat runs in a CE-observed tmux pane (`terminal.kind: tmux`, `PCO-049`); the pane is bound to a Pane Registry record and an Active-Work claim (§7). | HARD at Ring 0 (Gate 3) |

The committed settings source is the **only** authorized CE enforcement source. The user
`~/.claude/settings.json` is personal ergonomics only (PROMPT/SKILL-equivalent) and **must not** be
the CE enforcement source. The committed `.claude/settings.json` hook-pack itself is authored in a
**later gate** (§6); this contract only fixes the posture it must satisfy.

## 5. Prohibited flags and modes

The following are **prohibited** for governed Claude Code Controller (and implementer) lanes. The
prohibitions are stated without hedging:

| Prohibited | Why it is forbidden | Enforcement intent |
|---|---|---|
| `--bare` | Skips hooks, plugin sync, auto-memory, and `CLAUDE.md` discovery — it defeats the entire enforcement layer. | HARD refusal at Ring 0 (`ce lane launch`). |
| `-p` / `--print` (headless) | Non-interactive print mode skips the workspace-trust dialog, silently ignores invalid settings, and disables session persistence — it is not the visible, archivable pane CE requires. Permitted only for read-only internal scripted `ce` checks, never for governed authoring lanes. | HARD refusal at Ring 0 for governed lanes. |
| background `agents` (the `agents` subcommand / `--agents` background sessions) | Background sessions are invisible and unarchivable; they violate the `PCO-049` visible-pane requirement. | HARD refusal at Ring 0; managed `disableAgentView` makes it HARD host-side (FUTURE SEAM, v1.1). |
| `--remote-control` (and `remoteControlAtStartup`) | An external control channel outside the visible/archived model. | HARD refusal at Ring 0; managed `disableRemoteControl` (FUTURE SEAM, v1.1). |
| weakening `settings.local.json` usage | A gitignored local-override source can silently weaken or disable the committed hook-pack; governed launches pin `--setting-sources project` to exclude `local`. | RUNTIME → HARD at Ring 0. |
| `--dangerously-skip-permissions` | Removes interactive permission friction. **Permitted only when the hook-pack is confirmed loaded later by Ring 0.** PreToolUse hooks fire and can deny even under skip-permissions, and `permissions.deny` outranks hook output — so skip-permissions is safe *only* once Ring 0 has verified the pack is active. Without that confirmation it is prohibited. | HARD precondition at Ring 0: refuse skip-permissions unless the pack is confirmed loaded. |

`-p` and `--print` denote the same headless print mode. The `agents` subcommand and background
`--agents` sessions are both covered by the background-`agents` prohibition.

## 6. Required hook-pack presence — a later-gate dependency, not implemented in CC-G-A

A governed seat's in-band enforcement depends on a **committed, posture-aware Claude hook-pack**. That
pack is a **later-gate dependency and is explicitly NOT implemented in CC-G-A**. The following are all
**later gates, not implemented here**:

- `.claude/settings.json` — the committed Claude harness adapter carrying `hooks` and
  `permissions.deny` rules. **Later gate (CC-G-C). Not authored here.**
- `.claude/hooks/**` — the `command`-type hook scripts that call the validator bridge. **Later gate
  (CC-G-C). Not authored here.**
- `hook-check` — the `creator_engine_validator hook-check` subcommand that returns allow/deny from a
  single TDD-tested code path (the in-band reuse of `role_boundary_attribution` +
  `path_manifest_fidelity` + `mutation_class`). **Later gate (CC-G-B). Not implemented here.**
- completion-report schema / checks — `schemas/completion-report.schema.yaml` and the
  `completion_report_schema` check that the `Stop`/completion gate evaluates. **Later gate (CC-G-B).
  Not implemented here.**
- `ce lane launch` / `ce launch` Claude adapter — the Ring 0 kernel code that verifies the hook-pack
  is loaded, pins `--setting-sources`, refuses prohibited flags, verifies prompt+SHA, and binds the
  Pane Registry ↔ Active-Work claim. **Later gate (CC-G-D, extending Gate 3 / Gate 6). Not implemented
  here.**

CC-G-A authorizes exactly one tracked path — this document — and **no runtime code, no settings, no
hooks, and no launcher adapter**. The hook-pack's *required presence* is recorded here as a contract
obligation that the later gates must satisfy; its *implementation* is out of scope for CC-G-A.

The required gate dependency is: a governed seat that opts into `--dangerously-skip-permissions`
**must** have the hook-pack confirmed loaded by Ring 0 first (§5). Until CC-G-B/CC-G-C/CC-G-D land,
no live hooked Claude session is authorized, and the only active deterministic layer remains the
offline VALIDATOR plus Controller verification and human audit.

## 7. Governed-posture predicate

The **governed-posture predicate** decides whether a Claude Code session is a *governed lane* (hooks
enforce HARD/deny) or *ordinary repo usage* (hooks advisory/observability-only). It is the
DP-3=B governed-environment guard, surfaced at the seat layer. A session is **governed** when, and
only when:

1. a live `.hermes/pane-registry` record exists for the pane (`terminal.kind: tmux`), and
2. that record is bound to a **live, unreleased Active-Work claim** (`PCO-050`) whose controller and
   lane match the pane.

When governed, in-band gates (once the later hook-pack exists) enforce **deny** on out-of-manifest
edits, unauthorized mechanics, and secret reads. When ungoverned (no live Pane Registry binding / no
Active-Work claim), the same hooks are **advisory-only** so ordinary contributor Claude usage is never
hard-blocked. In an **ambiguous** posture *inside a lane bound to a live Active-Work claim*, the
predicate fails **closed** (treat as governed): an ambiguous-posture allow of an out-of-manifest edit
is a release blocker, not a default-allow.

Related tracked governance: [`PANE_REGISTRY_PROTOCOL.md`](PANE_REGISTRY_PROTOCOL.md),
[`ACTIVE_WORK_LEDGER_PROTOCOL.md`](ACTIVE_WORK_LEDGER_PROTOCOL.md),
[`GOVERNED_LANE_LAUNCH_PROTOCOL.md`](GOVERNED_LANE_LAUNCH_PROTOCOL.md),
[`SIDE_EFFECT_LEDGER_PROTOCOL.md`](SIDE_EFFECT_LEDGER_PROTOCOL.md).

Note: `.hermes/` is git-ignored instance state. The hooks **enforce on tracked files but read and
write only `.hermes/` ignored state**; the posture inputs (`pane-registry`, `active-work-ledger`) and
any deny/block ledger entries are never tracked governance artifacts.

## 8. Seat↔harness classification and defeasibility honesty

### 8.1 Classification

For the v1.0 Controller seat, **Claude Code is classified `IN`** — an in-seat harness alongside Hermes
and Codex, with host-local Controller authority. This row extends the Controller Runtime Contract
(RV1-020, Gate 2): the in-seat harnesses are exactly `{hermes, claude-code, codex}`; OpenClaw is a
seam; hosted-service / SaaS / GitHub-connector authorities are unauthorized for v1.0 kernel authority.

**Managed settings are a v1.1 seam**, not a v1.0 requirement. The non-overridable host-level tier
(`/etc/claude-code/managed-settings.json`: `allowManagedHooksOnly`, `allowManagedPermissionRulesOnly`,
`disableAgentView`, `disableRemoteControl`, `disableAutoMode`, `strictPluginOnlyCustomization`,
`disableSkillShellExecution`) would make Ring 1 non-overridable, but it is host-invasive, requires
root, and conflicts with the v1.0 local/daemonless tenet if *mandated*. It is therefore recorded as a
**FUTURE SEAM** (CC-G-E, v1.1) — deferred, not rejected — and is never on the v1.0 critical path.

### 8.2 Defeasibility honesty (load-bearing)

The committed project hooks/settings (the Ring 1 hook-pack, once it ships) are **RUNTIME
(launch-pinned) enforcement — they are defeasible and are NOT non-overridable HARD enforcement unless
managed settings are present.** A committed `.claude/settings.json` hook-pack can be bypassed locally
by `--bare`, `settings.local.json`, CLI `--setting-sources` excluding `project`, or `disableAllHooks`.
The committed pack must therefore **never** be marketed as HARD or non-overridable on its own.

The HARD repo-native floor in v1.0 is **Ring 0**: `ce lane launch` (and `ce launch`) refusing to
launch or verify a lane that is not governed — refusing hidden/headless/background surfaces, refusing
prohibited flags, refusing a prompt/SHA mismatch, refusing skip-permissions when the pack is not
confirmed, and refusing a pane with no live Active-Work claim. The committed hook-pack is
defense-in-depth *inside* the lane; managed settings (v1.1 FUTURE SEAM) are the optional hard host
lock that makes Ring 1 non-defeasible. If any later gate's documentation claims the committed
hook-pack is non-overridable *without* managed settings, that is a defect to halt and correct.

The three concentric rings, kernel-anchored:

- **Ring 0 — KERNEL (`ce lane launch` / `ce launch`). HARD.** Repo-native, local, daemonless. The hard
  boundary even if every inner ring is bypassed. *(Later gate: CC-G-D.)*
- **Ring 1 — CLAUDE HOOK-PACK (committed `.claude/settings.json` + `.claude/hooks/*.sh`). RUNTIME
  (launch-pinned), in-band, defeasible.** *(Later gate: CC-G-C, powered by the CC-G-B `hook-check`
  bridge.)*
- **Ring 2 — VALIDATOR (`creator_engine_validator`). VALIDATOR, post-hoc and shared.** The single
  source of scope/role/manifest truth that the hooks call in-band so Ring 1 and post-hoc verification
  never diverge.
- *(v1.1 outer shell — managed settings. HARD, host-level, non-overridable. **FUTURE SEAM.**)*

## 9. Traceability

### 9.1 Tracked governance (this repository, baseline `origin/main` `1623727`)

- [`CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md`](CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md) — RV1-020 CRC;
  the seat↔harness classification this contract extends with the Claude `IN` row (§8.1).
- [`CONTROLLER_BOUNDARY_POLICY.md`](CONTROLLER_BOUNDARY_POLICY.md) — Controller/Implementer boundary.
- [`GOVERNED_LANE_LAUNCH_PROTOCOL.md`](GOVERNED_LANE_LAUNCH_PROTOCOL.md) — the Gate 3 lane-launch
  primitive that will enforce this contract at Ring 0.
- [`PANE_REGISTRY_PROTOCOL.md`](PANE_REGISTRY_PROTOCOL.md) and
  [`ACTIVE_WORK_LEDGER_PROTOCOL.md`](ACTIVE_WORK_LEDGER_PROTOCOL.md) — the posture-predicate inputs
  (§7).
- [`PATH_MANIFEST_FIDELITY_PROTOCOL.md`](PATH_MANIFEST_FIDELITY_PROTOCOL.md),
  [`TRANSCRIPT_ARCHIVE_PROTOCOL.md`](TRANSCRIPT_ARCHIVE_PROTOCOL.md),
  [`COMPLETION_REPORT_PROTOCOL.md`](COMPLETION_REPORT_PROTOCOL.md),
  [`SIDE_EFFECT_LEDGER_PROTOCOL.md`](SIDE_EFFECT_LEDGER_PROTOCOL.md) — scope, archive, completion, and
  audit surfaces the later hook-pack reuses.

### 9.2 Definitive roadmap (research provenance, git-ignored research artifact)

- Path: `/home/nefarious/projects/creator-engine/.hermes/research/pco-v1-language-packaging-reassessment-20260524T152750Z/source-decision-20260524T162414Z/option-b-reissue-output/V1_DEFINITIVE_SDD_TDD_ROADMAP_DEVELOPMENT_PLAN_OPTION_B_REISSUED.md`
- SHA256: `5a7e5ba74adcaab32c892c3cf793384eec4f121a6991b1bd5bba34a30fd48e13`
- Anchors: §0 DP-1=A (`ce` kernel), DP-2=B (`ce launch` deterministic launcher + Controller-seat-in-harness),
  DP-3=B (host-local development permitted, guarded by the governed-environment predicate); §2.6 launch
  model; §2.7 governed-environment guard; Gate 1 (terminology/product-contract), Gate 2 (RV1-020 CRC +
  state boundary), Gate 3 (RV1-030 `ce lane launch`, visible-tmux-or-refuse, `PCO-049`/`PCO-050`),
  Gate 6 (RV1-063 `ce launch`).

### 9.3 Prior architect report (research provenance, git-ignored local artifact)

- Path: `/home/nefarious/Documents/creator-engine documentation/creator-engine-hermes-vs-claude-code-controller-optimization-architect-report.md`
- SHA256: `9d2be4280e5a47c4c7aa1b3338241a8547145b4dc7012724437de53badf4adb5`
- Anchors: §2 enforcement-strength vocabulary; §9 Claude capability inventory and CE applicability;
  §10 three-ring target architecture; §11 CC-G-A gate definition (RV1-CC-001/002/003) and the CC-G-B /
  CC-G-C / CC-G-D / CC-G-E sequence; §15 defeasibility honesty (K-1) and decision forks.

---

*This contract is docs/governance only. It authorizes no mutation and is not Source ratification of
any implementation. The hook-pack, validator bridge, completion-report schema, and launcher adapter
named above are later gates, not implemented in CC-G-A.*
