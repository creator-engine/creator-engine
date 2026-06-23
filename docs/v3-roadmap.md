# Creator Engine v3 — Roadmap

> **Historical gate-map.** v3 is done (v3.1 "pilot-ready" reached). Forward
> program planning — workstreams, waves, and the path to the NVIDIA pitch — now
> lives in [`v3.5-roadmap.md`](v3.5-roadmap.md). This file is retained as the v3
> gate history.

Durable, in-repo roadmap for the Creator Engine **v3** evolution. This is the
shareable source for *where we are* and *what's next* — kept derivable from
`git log --oneline main` rather than from any one person's notes. Update the
status table whenever a gate's PR merges (see the maintenance note at the end).

## Orientation

CE v3 is a self-run, agent-native SDLC platform for solo / small teams, built by
**evolving this repository in place** (monorepo-first), not by greenfielding a
new one. The design is organised around three planes:

- **Plane A — coordination / review / merge:** rented to a forge (GitHub) behind
  a thin adapter, so the team never hand-builds coordination.
- **Plane B — scope containment:** enforced by CI via the `path_manifest_fidelity`
  PR-diff gate (every PR's diff must equal its declared closed manifest).
- **Plane C — runtime safety:** a declarative runtime-policy plus a container +
  thin-policy enforcer (gVisor + a capability-separation egress proxy now;
  OpenShell a fast-follow behind the same adapter).

The orchestrator that drives a run is deliberately **thin glue** (resolve a
backend, gate on an approved plan, provision → run → collect → teardown, collect
evidence); the **enforcement** lives in the policy + container + forge config.

## Design source-of-truth

Curated, **fresh-clone-resolvable** copies of the load-bearing design live in
`docs/architecture/` (start with `docs/architecture/README.md`, then the spec).
These are curated/redacted for sharing; the **full-fidelity** originals live under
the gitignored `.hermes/research/v3-*-architect-*/` tree (instance-local — these
links resolve only in the authoring instance, not a fresh clone).

| Committed copy (fresh-clone) | Full-fidelity original (gitignored) | What it decides |
| --- | --- | --- |
| `docs/architecture/v3-spec.md` | `.hermes/research/v3-spec-architect-20260602T091332Z/` | **The spec** — thin-orchestrator / thick-enforcer, the version-coexistence plan (§6; supersedes the prior D0–D6 deletion plan — v1 retained + boundary-guarded), and the G-i/ii/iii → G-1 → G-2 → G-3 MVP gate map |
| `docs/architecture/v3-secure-runtime.md` | `.hermes/research/v3-secure-runtime-architect-20260602T114327Z/` | Plane C — gVisor + proxy, OpenShell, the tamper-evident evidence spine |
| `docs/architecture/v3-product-brief.md` | `.hermes/research/v3-product-architecture-brief-20260602T091332Z/` | The product brief that framed the above |
| _(not committed)_ | `.hermes/research/v3-evolve-vs-greenfield-architect-20260602T070354Z/` | Evolve this repo (don't greenfield) — the EVOLVE-dominant hybrid decision (its conclusion is captured in the brief §4 + the spec) |

Note: `specs/001-v0-1-governance-substrate/` is the **superseded v2 governance
substrate** — historical context, not the v3 roadmap.

## The MVP gate map

```
Kickoff   G-i  author-time advisory hook      G-ii  path_manifest_fidelity PR-diff gate
Plane A   G-iii GitHub-native coordination (configure_repo / install_required_checks / CODEOWNERS)
Plane C   G-1  runtime safety
            G-1.0 runtime-policy substrate      G-1.1 runner-backend adapter
            G-1.2 gVisor + proxy backend        G-1.3a hash-chained evidence spine
            G-1.3b classifier + audit overlay
G-2       thin orchestrator + ratification gate
            G-2.0 orchestrator + approved-plan gate    G-2.1 forge-native approval + no-self-approval
            G-2.2 mint_scoped_token (JIT least-privilege)   G-2.3 OpenShell backend (research-gated, deferred)
G-3       first working v3 — one real Dev-mode gate end-to-end
            G-3.0 forge-native open_change() + ChangeRef       G-3.1 orchestrator wiring (run_plan -> open_change)
            G-3.2 read-only change-status (review/checks/conflicts)   G-3.3 forge.merge() (review + checks + up-to-date)
            G-3.4 credential value-injection seam             G-3.5 evidence persistence sink
            G-3.6a run-outcome / disposition model            G-3.6b offline end-to-end dry-run
            G-3.7 live spike (first working v3)
Pilot     post-MVP stack → v3.1 pilot-ready (full-stack-first)
            G-3.7b CI-pure: merge-seam + live-merge-identity seam + pr_merged model
            G-3.8  out-of-envelope LIVE merge spike   ► v3.0 MVP-complete ✓ REACHED
            G-3.9  version coexistence / separation (declare + guard the v1⊥v3 boundary; v1 RETAINED; no deletion)
            G-4    agent-interaction contract (AgentActionEvent → decide() → runtime_agent_action)
            G-4.1  v3 naming-hygiene guard + neutral .ce/state local-state convention (v3 surface clean by machine)
            G-5    tokenomics gate (spend envelope: admission + circuit-breaker)
            G-6    coordination layer (Scope + backlog + DoR-wiring + crosswalk)
            G-7    product surface (v3 CLI [exposed as `ce` on the v3-only pilot; internal `cev3`] + session frame + unified status line + shaping detect-and-offer + ◆ Completion Report + 2-mode install [one-liner + signed agent-native]; v1 launcher retained)  ► v3.1 pilot-ready ✓ REACHED
```

## Gate status

Merged commits are short SHAs on `main`; re-derive with `git log --oneline main`.

| Gate | Scope | PR | Commit | Status |
| --- | --- | --- | --- | --- |
| G-i / G-ii | author-time advisory hook + `path_manifest_fidelity` PR-diff gate | #112 | `19bbff4` | MERGED |
| G-iii | GitHub-native coordination (carrier convention + `configure_repo`/`install_required_checks` + CODEOWNERS) | #113 | `6ecf9a5` | MERGED |
| G-1.0 | plane-C runtime-policy substrate (`runtime-policy.schema` + `ce_runtime_policy`) | #114 | `813c2dd` | MERGED |
| G-1.1 | runner-backend adapter (`RunnerBackend` ABC + registry + local-noop) | #115 | `d4df4bd` | MERGED |
| G-1.2 | gVisor + proxy backend (policy → runsc/egress-proxy translation, availability-gated) | #116 | `ae2315b` | MERGED |
| G-1.3a | hash-chained evidence-spine substrate (`runtime_evidence_spine` + `ce_runtime_evidence`) | #117 | `6fe06cd` | MERGED |
| G-1.3b | classifier + backend-agnostic audit overlay (`classify` + `AuditOverlayBackend`) | #118 | `fe0b54c` | MERGED |
| G-2.0 | thin orchestrator `run_plan` + approved-plan ratification gate | #119 | `77656e5` | MERGED |
| G-2.1 | forge-native `plan_approved()` + no-self-approval guardrail | #120 | `269c8f2` | MERGED |
| G-2.2 | `mint_scoped_token` — JIT least-privilege, time-boxed per-run credential | #122 | `b3caa5e` | MERGED |
| G-2.3 | OpenShell backend behind the runner adapter | — | — | deferred (research-gated) |
| G-3.0 | forge-native `open_change()` + `ChangeRef` (change-lifecycle "PR opened" primitive) | #124 | `65ec35d` | MERGED |
| G-3.1 | orchestrator wiring (`run_plan` → `open_change`; thread the run change-set + JIT-token `gh_runner`) | #126 | `9067034` | MERGED |
| G-3.2 | read-only forge change-status (`review_state` / `checks_state` / `change_conflicts`) | #128 | `3bee641` | MERGED |
| G-3.3 | `forge.merge()` — squash, gated on review + checks + `mergeable=="MERGEABLE"` | #130 | `25db4e5` | MERGED |
| G-3.4 | credential value-injection seam (`authenticated_gh_runner` — `ScopedToken.value` → child `gh` env only) | #132 | `4d4a65b` | MERGED |
| G-3.5 | evidence persistence sink (`file_evidence_sink` — `CollectedEvidence` → durable `runtime-evidence-chain` file; persist iff `verify_chain`+schema-valid, else refuse) | #134 | `e63ae0b` | MERGED |
| G-3.6a | run-outcome / terminal-disposition model (typed `runtime_run_outcome` record — the run-disposition axis, orthogonal to the `provision`/`run`/`collect`/`teardown` `lifecycle_phase`, appended to the same hash chain) | #136 | `bc22681` | MERGED |
| G-3.6b | offline composition-root assembly + end-to-end dry-run (`run_assembly.py` `make_run_driver` — the minter→runner `ScopedToken` bridge + the injectable `run_plan(evidence_sink=…)` seam; mint → authenticated runner → run → collect → typed `pr_opened` outcome → persisted evidence, fully offline) | #138 | `2245426` | MERGED |
| G-3.7 | live spike — first working v3: the live OPEN drive (App-JWT mint → one real PR → persisted evidence + CE-owned ratification record → correct revoke), Operator-ratified outside the CI-purity envelope; custody / ratification / leak-hardening landed; **gated merge deferred → G-3.7b/G-3.8** | #140–#145 (+ out-of-envelope live drive 3.7.3b) | `a132534` | MERGED |
| G-3.7b | CI-pure merge-driving seam + distinct live-merge-identity seam + `pr_merged` run-outcome/schema/spine (`.0` run-outcome model + `.1` merge-driving producer) | #148 (`.0`) + #149 (`.1`) | `af60f06` | MERGED |
| G-3.8 | out-of-envelope live merge spike — one real PR opened → independently reviewed → squash-merged by a **distinct merge identity** (merge identity ≠ run token); value-free `pr_merged` evidence persisted on the same chain (`verify_chain()==[]`, schema-valid); **zero repo code change** (ran the merged G-3.7b seams) → **v3.0 MVP-complete** | — (out-of-envelope live spike) | — | PROVEN (live) |
| G-3.9 | version coexistence / separation — declare the v1/v3/shared taxonomy (`_versions.py`) and guard the **v1⊥v3** boundary with the `version_boundary` check (hard runtime⊥runtime + a baselined `shared→version` allowlist ratchet); **v1.0 RETAINED whole, no deletion** (replaces the spec §6 "deletion plan") | #152 | `a02aca8` | DONE |
| G-4 | agent-interaction contract — typed `AgentActionEvent` (op × mutation_class × fidelity) → PURE `classify()` branch → deterministic `decide()` control-point (built-in deny + Zed precedence + gate-mode ladder; `auto` advisory-only) → hash-chained `runtime_agent_action` record; additive runtime-policy `action_class_allowlist`/`gate_mode_ladder`; **boundary-clean Tier-B CC-hook derivation seam** (`runner.cc_hook_adapter` via the **shared** `checks.mutation_class`, never v1 `hook_check`); CI-pure (live tap deferred) | #154 | `ec4eb3a` | DONE |
| G-4.1 | v3 naming-hygiene guard + neutral local-state convention — a self/structural `v3_naming_hygiene` check (sibling to `version_boundary`) FAILing on CE bootstrapping-harness residue (`.hermes`/`Hermes`/`Nefarious`) in the v3 CODE/SCHEMA surface (green-on-day-one + ratchet; legit adapter names Claude/gVisor/Codex/ACP carved out; v3 docs + legacy corpus excluded); neutral `.ce/state` local-state convention (`_versions.V3_LOCAL_STATE_ROOT`, never `.hermes/`/`.claude/`); standing requirement that G-5…G-7 prompts cite both | #156 | `e916df2` | DONE |
| G-5 | tokenomics gate (spend envelope) — additive runtime-policy spend fields (`spend_envelopes` nested `global→fleet→run`, most-restrictive-wins + mandatory global `$` ceiling; `max_concurrent_runs`; `model_rates` read-live-never-hardcode; `spend_cap_enforcement`/`spend_cap_optout`) → PURE `runner.spend_gate` (two-regime cost [`$` fleet / `%` seat] · ledger-as-projection over the spine · admission + synchronous soft/hard circuit-breaker · two-signal `budget_exhausted`-vs-`throttle`) → spend-ledger + breach record axis on the evidence spine; cap/detection split + ratified-HUMAN-only opt-out; new `ce_spend_envelope` check; CI-pure (live `usage`/`/usage` taps, cockpit channel, cross-process semaphore deferred) | #158 | `1ed368b` | DONE |
| G-6 | coordination layer (the Scope dispatch spine, Scope-only) — `schemas/scope.schema.yaml` (the ephemeral atom) → PURE `coordination` module (`scope_is_ready` DoR predicate · `is_ratified` · `appetite_to_spend_envelope` [the G-5 join] · `project_scope_state` [state-as-projection over the conserved spec-lifecycle, canon skin Frame→Shape→Build→Review→Ship] · `assemble_dispatch` refusing-unless-ready+ratified, producing G-4/G-5 run inputs) → new `ce_scope` check; authored in the stage-vocabulary canon (#161 — conserve the machine, no third vocabulary); CI-pure (live dispatch, durable Skill axis, finding-schema deferred) | #162 | `dee9c9b` | DONE |
| G-7 | product surface (CI-pure, 6 slices) — the v3 work-driving CLI (internal `cev3` console_script, **exposed as `ce`** on the v3-only pilot; v1 `ce` retained) · the `ce session` frame + the **unified context(#157)+spend(G-5) status line** · the **Frame→Shape shaping detect-and-offer** dialogue · the **◆ CE Completion Report** + artifact awareness · the **two-mode operator-typeless install** (one-liner + signed agent-native `llms-install.md`; verify-before-execute; detect-don't-assume deps; Default-vs-Custom cost opt-out) · the pilot runbook + in-product `ce guide`. All user-facing vocabulary is the ratified canon (stage phases / Scope-card / Completion-Report — no third vocabulary); live install drive + GitHub-App click + live taps deferred → **v3.1 pilot-ready** | #164·#166·#167·#168·#169·#170 | `5ffc28d` | DONE |
| v3.1-G1 | live-spawn keystone (the self-host blocker) — wire `cev3 drive`'s assembled `DispatchPlan` into the proven v1 spawn mechanics as **subprocess + DATA only** (`ce launch --json` → files + argv + JSON; imports NO v1 module, AST-asserted). **G1a** (assemble→spawn): new `v3_seat_bridge` (`materialize_dispatch`→value-free dispatch record + runtime-policy + seat brief · `spawn_seat`→ v1 launch leg, `--claude-arg=--dangerously-skip-permissions` iff unattended, CC-D-6 still the gate · `seed_brief`→ tmux pointer line; every subprocess edge an injected `runner=` seam) · `cev3 drive --spawn` (additive opt-in, `--no-unattended`, refuses non-claude → G1-codex follow-up) · two v1 launch fixes (defect-a: plain `ce launch` now provisions the strict MCP config; defect-b: CC-D-6 unattended-flag tests). **G1b** (run→evidence→report): `cev3 collect` folds the seat transcript → spend ledger (reusing `runner.usage_tap`) + typed `runtime_run_outcome`, hash-chained + persisted under `.ce/state/runs/` (refuses double-collect) · read-model wiring (uncollected dispatch → Build/RUN; `report`/`artifacts` default `--evidence` from a collected run) · new `schemas/dispatch-record.schema.yaml`. CI-pure (zero live tmux/claude/systemd; live per-turn tap + forge PR/merge legs + reviewer venue + retirement run deferred). | — | `86ca1d3` | MERGED |
| v3.1-G2 | forge-leg join (the pitch-arc keystone) — one gate runs Scope→ratify→drive→seat→**PR-open→independent-review→merge** through the v3 product surface, a pure v3→v3 composition (imports NO v1 module beyond the named `ce_cli --json`; AST-asserted). **G2a** (ship leg): new `forge.change_push` (the missing push primitive — pushes the seat's authored head to the CONSTRUCTED HTTPS remote, plan-by-default, idempotent, NEVER force) + new `v3_forge_join` (`load_app_config` reads the host App config AS DATA · `openssl_signer` = the first production RS256 signer, PEM off-process · `open_change_for_run` mint→push→open under a JIT least-privilege (`contents:write`+`pull_requests:write`, ≤900s) token revoked in a finally, stamping a value-free `change` block) · `cev3 pr` (plan-by-default; `--app-config` REQUIRED, no default — host filenames differ) · `cev3 collect` derives `change_set`+`pr_opened` from the stamped block. **G2b** (reviewer-venue leg, v3→v1 subprocess+DATA): `ce lane launch --json` (the one v1 surface fix) · `v3_seat_bridge` grows `compose_reviewer_envelope`/`materialize_review_dispatch`/`spawn_review_venue` (pco-allocate→lane launch→seed, fail-closed) · `cev3 review --spawn`. **G2c** (merge leg): `v3_forge_join.merge_for_run` (gated squash via a DISTINCT merge identity, NEVER the per-run token; `pr_merged` on a real merge only) · `cev3 merge` (plan-by-default; `--apply` = the Operator's gated act) · show/status surface the PR + a live reviewer venue. V3_RUNTIME 33→35; V1/registry/allowlist/V3_SCHEMAS unchanged. CI-pure (every live leg `--apply`-gated + seam-injected; the retirement RUN is ce-ops#14). | #203 | `b4fba47` | MERGED |
| v3.1-B.7 | Cockpit fleet cost meter (the last demo surface) — a pure L2 read-model fold (`cockpit_readmodel.fold_cost_meter`) over the `runtime_spend_ledger` leaves of every collected run (`run_id == scope_id` join): per-scope `$` (REUSE `project_spend`) + a fleet rollup (REUSE `fleet_spend_meter`), with **MEASURED vs UNPRICED** (subscription — managed by limits/headroom, **never a $0 lie**) honesty tiers + a measured-`$`-is-a-FLOOR headroom note; an L3 cost rail (`v3_cockpit._meter_strip_text`, render-only, top-N truncation declared) + `--json` parity + a CE_DEMO `subscription-seat` so both tiers show on camera. A demo surface, **NOT** the G-5/v3.5-G tokenomics engine (read-only; re-implements no `$` math). V3_RUNTIME 35 / V1 / registry / allowlist / V3_SCHEMAS all unchanged; no schema change. Lands via the ce-ops#14 retirement run (Scope→ratify→drive→seat→pr→review→merge through v3). | #204 | `570b20c` | MERGED |
| v3.5-B2 | Cockpit live feeds — `escalations` AWAITING-OPERATOR queue (`.ce/state/escalations/*.yaml`, schema-required recommendation, `ce escalation open/resolve/sync` fail-closed mirror) + `dispatches` G1 read-model feed (`.ce/state/dispatches/*/dispatch.yaml` + sibling spend envelope) + render-only TUI rail additions and CE_DEMO parity. Failure-stamped dispatches surface as `failed` and never project Build/RUN. | — | — | LANDING |
| ce-ops#21 | per-PR path-manifest carrier (CI-infra throughput gate) — migrate the single shared `.ce/pr-path-manifest.md` (every PR rewrote it → structural merge-tax) to per-PR carriers `.ce/pr-manifests/<branch-slug>.md`. Pure-function `branch_slug` (canonical id shape `^[a-z][a-z0-9-]{2,63}$`) + a per-PR mode of `verify-path-manifest` (`--manifest-dir`/`--head-ref`): exactly one ADDED carrier whose stem == `branch_slug(head)`, diff == its self-inclusive path-set; 4 new error classes (`…_multiple_carriers`/`…_carrier_slug_mismatch`/`…_carrier_not_added`/`…_legacy_carrier_path`); the workflow G-ii step becomes one unconditional call; the retired shared path may only ever be deleted; merged carriers accumulate as a per-PR scope-audit ledger. Registry 52 / V3_RUNTIME 35 / `--list-checks` all unchanged (no new registered check). | — | — | LANDING |
| v3.1-G2f | venue/seat spawn hardening (ce-ops#16, pitch-arc W2 demo reliability) — the demo-critical subset of the retirement-run ledger, ZERO governance-ring semantics changed. **F3** unattended reviewer venues (`spawn_review_venue` mirrors the author-seat `--claude-arg=--dangerously-skip-permissions` iff `record.unattended`; CC-D-6 on the venue worktree's committed hook-pack stays the gate; `cev3 review --no-unattended` opt-out). **F4** reviewer-credential propagation as an EXPLICIT contract not inherited tmux-server ambience — `ce lane launch --seat-env-file` (owner-only/0600-class, refused otherwise) wraps the governed command `sh -c 'set -a; . "$1"; set +a; shift; exec "$@"'` between the Ring-0 pin and the resource-bound wrap; the secret VALUE never enters argv/the tmux server/any record (path ref only). **F5** absolutized state-root refs at materialize (`Path(root).resolve()`) so the envelope/brief refs survive the venue worktree boundary. **F7** Cockpit LIVE chains read from `<root>/runs/` (`RUNS_SUBDIR` call-site fix). **F9** the dispatch NAMES its transcript: `harness_session_id` (UUIDv4) minted at materialize + stamped onto `--claude-arg=--session-id`; `cev3 collect` resolves the transcript by EXACT KEY (never an mtime guess — the #14/#21 orchestrator mis-fold machine-blocked), `--transcript-override` salvage hatch + `transcript_source` honesty stamp. **G1-followups** PATH preflight (`tmux`+harness via `shutil.which`) + a seed readiness poll (30s/0.5s `pane_current_command`, fail-closed on timeout, pane conserved) + `send-keys` rc checks. **F8** docs-only: the declared-pre-push limitation note (the JIT App push leg can't ship `.github/workflows/**`; durable conditional-`workflows:write` fix deferred to a follow-up micro-gate). Additive OPTIONAL dispatch-record schema props only (`schema_version` stays `"1"`; old records validate byte-unchanged). V3_RUNTIME 35 / registry 52 / allowlist / V3_SCHEMAS all unchanged (no new module, no new check); the wheelhouse pair re-pinned (packaging contract). | — | — | LANDING |
| G1-codex | `cev3 drive --spawn --harness codex` (managed-PreToolUse-gated authoring seat) — explicit harness choice only, no auto-routing; default Claude path conserved as the stronger Ring-1-hook-pack path. Codex is allowed by default only for `none`/`docs`/`code`, with high-risk classes requiring a value-free `--codex-risk-override <HEX64>`. v1 `codex_launch_spec` carries the CDX-D refusal set (headless subcommands, remote surfaces, transcript-disabling `--ephemeral`, trust/posture bypass, out-of-root `--add-dir`, accounted bypass mode, and managed-hook-pack confirmation) and builds `env -u ... codex` to scrub common ambient repo-write credentials before spawn; the existing resource-bound and seat-sentinel wrappers still apply after Ring 0. The v3 bridge records `harness_boundary: codex_managed_pretooluse`, omits Claude-only MCP/`--claude-arg` launch surfaces for Codex, snapshots `~/.codex/sessions/**/*.jsonl`, and hard-fails unless a new `session_meta` transcript for the launched cwd is stamped as `harness_session_id` + `transcript_ref` before live projection. `cev3 collect` is harness-keyed: Codex uses spawn-stamped `transcript_ref` primary and `~/.codex/sessions/` exact-key fallback, never mtime guessing; Codex reviewer venues stay deferred and `cev3 review --harness codex` refuses with that reason. Containment remains the backstop for Codex surfaces not covered by PreToolUse. | — | — | LANDING |
| v3.1-B.8 | Operator-notify feed (ce-ops#31 Tier 1 — the AWAITING-OPERATOR detection layer) — the v3 runtime emits a notification when an escalation enters/exits the queue, fans it to pluggable sinks, and ties clearing to resolution so no alert goes stale. New `runner.notify_feed` (usage_tap-shaped: PURE `fold_notify_feed` + payload shaping + config validation; narrow I/O edges for the ledger + sinks). **The edge-detection memory is a durable, append-only, notifier-private delivery ledger** (`<root>/notifications/ledger.ndjson`) — entry/exit detection stays a PURE fold of two L1-shaped inputs keyed `(escalation_id, event_kind, sink_id)` ⇒ idempotent across restarts/re-folds by construction; the Cockpit no-governance-write law holds (the notifier appends only to its own `notifications/` subdir, REUSES `cockpit_readmodel.load_escalations`, never touches `escalations/`/`scopes/`/chains). Two event kinds (`awaiting_operator_entry`=ratify-needed/immediate, `awaiting_operator_exit`=clear/immediate); per-class dial `immediate|off` (`digest` RESERVED + REFUSED loudly until the #28-M2 rung). Two sinks: `desktop` (`notify-send`, critical/normal urgency) + `exec` (user argv LIST on stdin — no shell, covers ntfy/email/Telegram/webhooks); per-sink `payload: pointer|full` (confidential-by-default off-host pointer strips all prose, local-desktop default full). `cev3 notify once|watch|status` (poll-only MVP, 30s default; `--sync-repo/--sync-label` REUSE the existing forge sync legs for cross-host fan-in, sync-failure tolerated). At-least-once deliver-then-record; a failed sink stays pending + retried, never crashes the loop. Zero L3/cockpit/schema/hook change. V3_RUNTIME 35→36 (`runner.notify_feed`) / V1 / registry 52 / allowlist / V3_SCHEMAS all unchanged; the wheelhouse pair rebuilt. | — | — | LANDING |

**G-1 (plane C / runtime safety) and G-2 (thin orchestrator + ratification
gate) are COMPLETE** (G-2.0 / G-2.1 / G-2.2 merged; G-2.3 OpenShell deferred —
research-gated). **G-3 (first working v3) is COMPLETE** — G-3.0
(change-lifecycle `open_change()` primitive), G-3.1 (orchestrator wiring —
`run_plan` `change_opener` seam → `open_change()`), G-3.2 (read-only forge
change-status — `review_state` / `checks_state` / `change_conflicts`), G-3.3
(`forge.merge()` — squash, gated on review + checks + `mergeable=="MERGEABLE"`),
G-3.4 (credential value-injection seam — `authenticated_gh_runner`:
`ScopedToken.value` → the child `gh` env only), G-3.5 (evidence persistence
sink — `file_evidence_sink`: `CollectedEvidence` → a durable
`runtime-evidence-chain` file), G-3.6a (run-outcome / terminal-disposition
model — the typed `runtime_run_outcome` record, orthogonal to the container
lifecycle), and G-3.6b (offline composition-root assembly — `run_assembly.py`
`make_run_driver`, the minter→runner `ScopedToken` bridge + the
`run_plan(evidence_sink=…)` seam, drivable offline end-to-end) merged (#124,
#126, #128, #130, #132, #134, #136, #138). **G-3.7 (the live spike) is COMPLETE** —
its CI-pure slices 3.7.0a/0b/1/2a/2b merged (#140–#145) and the out-of-envelope
live drive 3.7.3b opened one real governed PR with a persisted, value-free
evidence chain + a CE-owned ratification record and a correct revoke. **G-3.7b
(CI-pure: the merge-driving seam + a distinct live-merge-identity seam — never the
per-run token — + the `pr_merged` run-outcome) merged (#148 `.0` `894bc42`, #149
`.1` `af60f06`), and G-3.8 (the out-of-envelope live merge spike) PROVED the full
governed inner loop live end-to-end:** one real PR opened → independently reviewed
→ squash-merged by a **distinct merge identity** (merge identity ≠ run token), on
one tamper-evident, value-free evidence chain (open → `pr_opened` → ratification →
`pr_merged`; `verify_chain()==[]`, schema-valid), with **zero repo code change**.
**► v3.0 "MVP-complete" is REACHED.** The remaining full-stack-first arc to a
developer pilot (G-3.9 → G-7, to the **v3.1 pilot-ready** milestone) is below.
**G-4 (agent-interaction contract), G-4.1 (v3 naming-hygiene guard + neutral `.ce/state` convention), G-5 (tokenomics gate — the #1 pilot blocker closed), G-6 (coordination layer — the Scope dispatch spine), and G-7 (product surface — CI-pure, 6 slices) are DONE — ✓ v3.1 pilot-ready REACHED.** Standing requirement (G-4.1): every v3.1 planning prompt (G-5…G-7) cites the `v3_naming_hygiene` guard + the neutral local-state convention (see [`docs/contracts/v3-naming-hygiene.md`](contracts/v3-naming-hygiene.md)) — see also [`docs/contracts/spend-envelope.md`](contracts/spend-envelope.md) + [`docs/contracts/scope.md`](contracts/scope.md). The user-facing stage vocabulary is the ratified canon [`docs/architecture/stage-vocabulary.md`](architecture/stage-vocabulary.md) (Frame→Shape→Build→Review→Ship over the conserved spec-lifecycle; no third vocabulary). Standing invariants: **v1 retained + v1⊥v3 held + v3 surface naming-clean.**

## What's next

**v3.0 "MVP-complete" is REACHED.** G-3.7 (the live OPEN drive), **G-3.7b** (the
CI-pure merge substrate — merge-driving seam + a distinct live-merge-identity seam
+ the `pr_merged` run-outcome), and **G-3.8** (the out-of-envelope live merge
spike) are DONE: the governed-run engine is proven live end-to-end **including
merge** — one real PR opened → independently reviewed → squash-merged by a
**distinct merge identity** (merge identity ≠ run token), on one tamper-evident,
value-free evidence chain. The **full-stack-first** arc to a developer pilot is
complete — both milestones below are now ✓ **REACHED**:

- **v3.0 "MVP-complete"** — ✓ **REACHED** — the governed-run engine proven live
  end-to-end **including merge** (open → review → merge). Reached at the end of
  **G-3.8**.
- **v3.1 "pilot-ready"** — ✓ **REACHED** — a developer can install (two-mode,
  operator-typeless), provision repo+App, file work as a Scope, and get governed,
  cost-safe PRs + merges end-to-end, all under the branded `ce session` frame.
  Reached at the end of **G-7** (the CI-pure product surface; the live install
  drive + GitHub-App click are the deferred first-pilot seams).

1. **G-3.9** *(DONE — #152)* — version coexistence / separation: declared the
   v1/v3/shared taxonomy (`_versions.py`) and guards the **v1⊥v3** boundary with the
   `version_boundary` check (hard runtime⊥runtime + a baselined `shared→version`
   allowlist ratchet). **v1.0 is retained whole — no deletion** (this replaces the
   spec §6 "deletion plan"); any future removal is orphaned-only, proven dead to
   both versions. The v3.1 arc proceeds additively with **"v1 retained + v1⊥v3
   held"** as a standing invariant.
2. **G-4** *(lands here)* — the agent-interaction contract: a typed
   `AgentActionEvent` → a PURE `classify()` branch → a deterministic `decide()`
   control-point (built-in deny + Zed precedence + gate-mode ladder; `auto`
   advisory-only) → a hash-chained `runtime_agent_action` record; additive
   runtime-policy `action_class_allowlist`/`gate_mode_ladder`; the **boundary-clean**
   Tier-B CC-hook derivation seam (`runner.cc_hook_adapter` via the **shared**
   `checks.mutation_class`, never v1 `hook_check`). CI-pure — the live transport tap
   and the credential hardening are deferred follow-ons. **The substrate G-5 + G-6
   plug into.**
3. **G-5** *(lands here)* — the tokenomics gate (spend envelope): additive
   runtime-policy spend fields → a PURE `runner.spend_gate` (two-regime cost
   [`$` fleet / `%` seat] · ledger-as-projection over the evidence spine · a
   deny-by-default admission gate + a synchronous soft/hard circuit-breaker ·
   two-signal `budget_exhausted`-vs-`throttle`) → a spend-ledger + breach record
   axis on the spine; the cap/detection split + a ratified-HUMAN-only opt-out; a new
   `ce_spend_envelope` check. CI-pure — the live `usage`/`/usage` taps, the cockpit
   channel, and the cross-process semaphore are deferred follow-ons. **Closes the #1
   pilot blocker.**
4. **G-6** *(lands here)* — the coordination layer (the Scope dispatch spine,
   Scope-only): `schemas/scope.schema.yaml` (the ephemeral atom) → a PURE
   `coordination` module (`scope_is_ready` DoR predicate · `is_ratified` ·
   `appetite_to_spend_envelope` [the G-5 join] · `project_scope_state` [state-as-
   projection over the conserved spec-lifecycle, surfacing the canon
   Frame→Shape→Build→Review→Ship skin] · `assemble_dispatch` refusing-unless-
   ready+ratified, producing one G-4/G-5-governed run's inputs) → a new `ce_scope`
   check. Authored in the stage-vocabulary canon (#161; no third vocabulary).
   CI-pure — the live dispatch, the durable Skill axis, and the
   finding-schema/discard-on-drift gate are deferred follow-ons.
5. **G-7** *(DONE — ✓ v3.1 pilot-ready; 6 CI-pure slices #164/#166/#167/#168/#169/#170)* —
   the product surface: the v3 work-driving CLI (internal `cev3` console_script,
   **exposed as `ce`** on the v3-only pilot; v1 `ce` retained, no D2 teardown) · the
   `ce session` frame + the unified context/spend status line · the Frame→Shape
   shaping detect-and-offer dialogue · the ◆ CE Completion Report + artifact
   awareness · the two-mode operator-typeless install (a human one-liner + a signed,
   verify-before-execute agent-native `llms-install.md`; detect-don't-assume deps;
   the Default-vs-Custom cost opt-out) · the pilot runbook + in-product `ce guide`.
   All user-facing vocabulary is the ratified canon (no third vocabulary). The live
   install drive + the GitHub-App click + the live status/dispatch taps are the
   deferred first-pilot seams. **► v3.1 pilot-ready ✓ REACHED.**
6. **G-2.3** — the OpenShell backend, still deferred (research-gated; re-opens on
   the recorded trigger conditions).

**Done this arc (→ v3.0):** **G-3.7b** — the CI-pure merge-driving seam + the
distinct live-merge-identity seam + the `pr_merged` run-outcome — merged (#148
`.0`, #149 `.1`); **G-3.8** — the out-of-envelope live merge spike (real open →
review → merge), proven once → **v3.0 MVP-complete**.

The detailed designs the G-4…G-7 planning prompts build to live in
`docs/architecture/pilot-roadmap.md`, `docs/architecture/pilot-deployment-transport.md`,
and `docs/architecture/pilot-uiux-model.md`.

**Deferred to post-first-pilot** (named, not forgotten): the cockpit UI · the
ACP/acpx Tier-A transport (pilot on CC-hooks/subprocess) · the durable **Skill**
axis (pilot Scope-only) · the MCP-server `install` tool · the OpenShell backend
(G-2.3) · CEO-mode / BMAD (v3.5 / v4).

The authoritative live "next action" is always the current batch-strict prompt
chain (below), not this summary.

## Where the v3 code lives

The v3 stack is the installable package `validators/creator_engine_validator/`:

| Path | Gate | Role |
| --- | --- | --- |
| `orchestrator.py` | G-2.0 / G-2.1 / G-3.1 / G-3.6a / G-3.6b | thin `run_plan()` + the `ApprovedPlan` / `PlanNotRatified` ratification gate + the injected `change_opener` seam → `open_change()`; the terminal step appends a typed `runtime_run_outcome` record (G-3.6a) to the run's evidence chain; the injectable `run_plan(evidence_sink=…)` (G-3.6b) persists the final chain on a post-`teardown` success path (default `None` = no I/O; `EvidencePersistRefused` propagates) |
| `run_assembly.py` | G-3.6b | the production composition root `make_run_driver()` — wires the minter→runner `ScopedToken` bridge (a closure cell sharing the one live token from `mint_scoped_token` into `authenticated_gh_runner`), the production `token_minter` / `change_opener` (over `open_change(…, apply=False)`), and the G-3.5 `file_evidence_sink` into one offline `run_plan()` drive, with `revoke_scoped_token` in a `finally`; the one place `forge` is imported (the orchestrator stays forge-free) |
| `runner/backend.py` | G-1.1 / G-3.1 | `RunnerBackend` ABC + registry (`get_backend` / `available_backends`) + the value-free `RunChangeSet` pointer type |
| `runner/noop_backend.py` | G-1.1 | inert `local-noop` backend (used in CI) |
| `runner/gvisor_proxy_backend.py` | G-1.2 | hardened gVisor + egress-proxy backend |
| `runner/audit_overlay.py` | G-1.3b | `classify()` + `AuditOverlayBackend` decorator |
| `runtime_evidence_spine.py` | G-1.3a / G-3.6a | hash-chained evidence spine (`append` / `verify_chain`); the `RUN_OUTCOME_RECORD_KIND` / `RUN_OUTCOME_RECORD_TYPE` / `RUN_OUTCOMES` constants for the G-3.6a run-disposition record |
| `forge/github_repo_config.py` | G-iii | `configure_repo` / `install_required_checks` |
| `forge/plan_approval.py` | G-2.1 | forge-native `plan_approved()` (merged in #120) |
| `forge/scoped_token.py` | G-2.2 | `mint_scoped_token` / `revoke_scoped_token` (JIT per-run credential) |
| `forge/change.py` | G-3.0 | forge-native `open_change()` + `ChangeRef` (change-lifecycle "PR opened" primitive) |
| `forge/change_status.py` | G-3.2 | read-only `review_state` / `checks_state` / `change_conflicts` over a `ChangeRef` (GraphQL via `GhRunner`) |
| `forge/merge.py` | G-3.3 | gated squash-merge `merge()` → `MergeResult` (review + checks + `mergeable=="MERGEABLE"`; plan-by-default; head-pinned squash `PUT` via `GhRunner`) |
| `forge/credential_runner.py` | G-3.4 | `authenticated_gh_runner()` — a `ScopedToken` → an authenticated `GhRunner` (the live token value into the child `gh` env only; never argv / log / disk / the task container) |
| `evidence_sink.py` | G-3.5 | `file_evidence_sink()` — a `CollectedEvidence` (AuditOverlay hash-chain) → a durable `runtime-evidence-chain` file matching `runtime-evidence.schema.yaml` (persist iff `verify_chain`+schema-valid, else `EvidencePersistRefused`) |
| `schemas/*.yaml` + `docs/contracts/*.md` | various / G-3.6a | declarative + prose contracts (incl. the G-3.6a `runtime_run_outcome_record` `$def` admitted via a `records.items` `oneOf` in `runtime-evidence.schema.yaml` + its `runtime-evidence.md` run-outcome section) |

The package also retains earlier v1/v2 machinery (lane/PCO/tmux runtime, etc.) —
the v1 surface, retained and classified `v1` under the version-coexistence plan
(declared in `_versions.py`, guarded by `version_boundary`); the table above is
the v3 surface.

## How this is governed

Work lands through **batch strict-mode**: each step is composed as a
SHA-pinned, Operator-ratified prompt, then executed as
`compose → ratify → execute → review → merge`. `main` is protected (required PR +
CODEOWNERS review + `enforce_admins`), and the independent reviewer identity is
distinct from the author. The work-of-record for each gate is its directory under
`.hermes/research/v3-*-planning-*/` (planning + execution + review + merge prompts,
evidence, and completion reports).

## Maintaining this doc

When a gate's PR merges: add its merge commit short SHA to the status table and
flip Status to MERGED; add new sub-gates as they are planned. Keep every row
derivable from `git log --oneline main`. This doc is a reference table, not a
substitute for the per-gate prompt chain.
