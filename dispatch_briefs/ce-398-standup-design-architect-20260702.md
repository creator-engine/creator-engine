# ce-ops#398 Research Brief: Controller De-SPOF Phase A — IaC One-Liner Standup

Read-only research for controller filing. No repository writes performed.

## 1. Current-State Map (grounded, file:line)

### 1.1 Hydration seams — what a launch actually receives today

**Brain bootstrap (assertion ledger, not free text).**
`/home/cedev2/creator-engine/validators/creator_engine_validator/brain_bootstrap.py`

- `build_bootstrap_payload()` (line 121) / `bootstrap()` (line 226) is a **deterministic, fail-closed** projection over a hash-chained assertion ledger (`brain_runtime`). It refuses to return a payload if the ledger is missing/invalid (`BrainBootstrapRefused`, line 96) or if a live self-identity probe drifts from a remembered assertion (`_reconcile_live_self_identity_assertions`, line 392-450).
- The payload embeds a **hard-coded, non-optional foreman charter** (`FOREMAN_CHARTER`, line 41), **worker-spawn capability contract** (line 54), and **foreman dispatch contract** naming exactly three dispatch roles: `researcher`, `implementer`, `reviewer` (`REQUIRED_FOREMAN_DISPATCH_ROLES`, line 38; `FOREMAN_DISPATCH_CONTRACT`, line 73). This is launch-pinned, not advisory — `require_foreman_dispatch_contract()` raises if malformed.
- `DEFAULT_ROLE = "controller"`, `DEFAULT_SEAT_CLASS = "foreman"` (lines 30-31) — a controller launch scopes the ledger query to `{role: controller, seat_class: foreman}` plus `global` scope, i.e. it pulls only assertions tagged for the controller role, not the whole brain.
- The payload is **only assertions + operating-mode contract**, not resume state, not duty lists, not credentials.

**Where this actually gets invoked for a controller launch.**
`/home/cedev2/creator-engine/validators/creator_engine_validator/launch_runtime.py`

- `_build_controller_brain_bootstrap()` (line 349-380) calls `brain_bootstrap.build_bootstrap_payload(role=DEFAULT_ROLE, seat_class=DEFAULT_SEAT_CLASS)`, then **additionally** attempts a semantic recall hydration via `brain_recall_surface.open_surface(...).hydrate_session(...)` (lines 361-377) with `embedder_name="vllm-openai"`, `top_k=5`, `allow_confidential_egress=False`. Recall failures are caught and logged as a **warning, not a refusal** (`except Exception ... LOGGER.warning`, line 378) — so semantic recall is best-effort/advisory, consistent with the "memory is advisory" invariant in `docs/contracts/orchestrator.md:104`.
- This function only runs when `--claim-ticket` is passed to `ce launch` (`_preflight_launch_brain_bootstrap`, `validators/creator_engine_validator/ce_cli.py:4304-4324`) — **without a claim ticket, a controller launch today receives NO brain bootstrap payload at all.**
- The materialized payload is written to `<seat_dir>/brain-bootstrap.json` with a sha256 digest and exposed via env vars `CE_BRAIN_BOOTSTRAP_REF` / `CE_BRAIN_BOOTSTRAP_SHA256` (`_materialize_brain_bootstrap`, line 393-402; `payload_env`, `brain_bootstrap.py:170-174`). This is the **only structured, in-repo hydration channel** a fresh controller launch gets today.

**`ce launch` itself is the existing controller-launch primitive** — there is no separate "controller launch" CLI verb; `ce launch`/`ce hud` opens a visible tmux Controller seat (`_launch`, `ce_cli.py:3537-3594`; `launch_runtime.launch()`, `launch_runtime.py:405`). It accepts `--controller-id`, `--host-id`, `--purpose`, `--claim-ticket`, `--repo-root`, `--ledger-root`, `--runtime-policy` and is documented authoritatively in `docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md:1-70`. A **worker** launch (`ce lane launch`, `ce_cli.py:432`) goes through a different code path (`lane_runtime._build_lane_brain_bootstrap`, referenced at `ce_cli.py:4310`) scoped to a role/lane rather than controller/foreman.

**What a controller launch needs beyond a worker launch (concretely, from the code):**
- `role=controller, seat_class=foreman` ledger scope (already exists) vs. a lane's `role=<worker-role>` scope.
- The **launch-pinned foreman dispatch contract** enforcement (`_require_launch_pinned_foreman_contract`, line 383-390) that a worker launch does not carry.
- Broader forge/credential surface (overwatch env, PAT, reviewer token pointer) — none of which is wired through `brain_bootstrap` or `launch_runtime` today; it is 100% out-of-repo (host env files, human memory).
- No duty manifest, no cron/daemon inventory, no watcher registry is loaded by any of the above — this is the gap Phase A must fill.

**Semantic recall / brain surfaces.**
`brain_recall_surface.py`, `brain_recall.py`, `brain_ingest_runtime.py` (all under `validators/creator_engine_validator/`) provide the ingest/recall substrate the controller bootstrap taps for advisory hydration. Treat these as the "memory is advisory" layer per `docs/contracts/orchestrator.md:104` ("Memory is advisory: recalled state may guide search, but live repository, forge, validation, and record evidence decide.") — not a source of duty or credential truth.

**Resume-state convention (`.ce/state/research/RESUME_STATE_*`).**
Not tracked in git (glob returned nothing; it is session-local/gitignored working state, consistent with `.ce/` being mostly untracked per current `git status`). The convention itself is **named directly in the tracked SSOT**: `docs/design/controller-bootstrap-ssot.json` `controller_knowledge_overlay.startup_sequence` (lines 195-200): *"Load the newest `.ce/state/research/RESUME_STATE_*` by mtime."* This SSOT is explicitly **preview-only, not ratified for live bootstrap injection** (`docs/design/controller-bootstrap-ssot.json:6-7`; `docs/design/controller-bootstrap-injection.md:1-5,30-42`). So the resume-state pickup convention is **codified as design text but not enforced by any runtime code** — a fresh controller has no programmatic way to discover/verify "newest RESUME_STATE by mtime, dual-write to CE-DEV-1" without a human or an ad hoc script reading it.

Directly relevant self-critique already in-repo: **ADR-0013** (`docs/decisions/ADR-0013-substrate-independent-authority.md:164-167`) states the prior G1–G5 authority framing was "terse pointer shorthand... recorded only in resume-state checkpoints and **never authoritative**." That is the exact knowledge-fragility problem #398 targets, already flagged by governance once.

### 1.2 Codified duties vs session-only duties

**In-tree (codified, discoverable by a fresh controller reading the repo):**

| Duty | Where codified |
|---|---|
| Dispatch brief shape + preflight-before-push directive | `playbooks/controller/briefs/dispatch.md` |
| Harvest sequence (READY signal, `ce validate-pr`, staging worktree, carrier regen, review-before-enqueue) | `playbooks/controller/briefs/harvest.md` |
| Merge-gate predicates | `playbooks/controller/briefs/merge-gate.md` |
| Seat-refresh pattern | `playbooks/controller/briefs/seat-refresh.md` |
| Courier-forge-op (ADR-0007 model-b bridging for contained seats) | `playbooks/controller/briefs/courier-forge-op.md` |
| Formal workflow/gates/stages | `playbooks/controller/workflow.ce.yml` |
| Authority envelope shape | `playbooks/controller/envelope.template.yml` |
| Contained-seat probe method (`docker exec`, not `docker run`) | `playbooks/controller/harness.md:17-27` |
| Full 9-step Orchestrator lifecycle, state machine, invariants, action taxonomy (autonomous vs reserved), 4 runtime record schemas (Checkpoint, Territory-Map, Harvest-Packet, Operator-Decision-Queue) | `docs/contracts/orchestrator.md` (ratified-shaped contract) and `docs/design/ce-orchestrator-agent.md` (design, with a 12-item ce-ops epic table at lines 549-561 that **already proposes** most of what #398 needs — see §7 below) |
| Action-taxonomy ratification | `docs/decisions/ADR-0013-substrate-independent-authority.md` |
| Role/tool/mount/egress/credential defaults per worker role, launch-pinned bootstrap SSOT | `docs/design/controller-bootstrap-ssot.json` (preview-only) |
| Preview generator for bootstrap artifacts | `scripts/gen-controller-bootstrap.py` |
| Non-secret credential/host-topology registry **schema** | `validators/creator_engine_validator/schemas/identity-registry.schema.yaml` |
| Credential pointer/backend abstraction (OpenBao, value-free) | `validators/creator_engine_validator/secret_identity.py` |
| `ce doctor` host/guard self-test pattern | `validators/creator_engine_validator/doctor_runtime.py` |
| Prior "standup"-shaped ADR precedent (OpenBao micro-unit standup) | `docs/decisions/ADR-0012-openbao-micro-unit-standup.md` |
| Seat launch governance runbook (structure precedent for a new runbook) | `docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md` |

**NOT in-tree (per task's seed list, and confirmed absent by grep for `watcher|cron|daemon` under `playbooks/` — zero hits):**

- Session-level watchers: PR-board monitor, 3-seat stall watcher.
- Host crons: seat-check `:00`, poll-devs `:05`, conveyor-tend `:30` (only referenced as *design proposal* text in `docs/design/ce-orchestrator-agent.md:317-324`, not as a runtime artifact — no crontab, no systemd timer unit, no script in `scripts/`).
- The merge-queue daemon (separate long-lived process) — not represented anywhere as a manifest entry, health-check, or restart command in-tree.
- The approval-wall daemon and its token-refresh dependency — same gap. (`docs/devops/openbao-approval-wall-arming.md` documents OpenBao arming but not the daemon's own duty/health surface.)
- Dispatch/harvest/review-gate *procedural mechanics* beyond the one-paragraph briefs (e.g., "check `.ce/pr-manifests/`, `.ce/briefs/`, `git worktree list`, `.ce/wt-*/`" territory-check sequence) — this level of detail exists only in `docs/design/controller-bootstrap-ssot.json` `controller_knowledge_overlay.pre_dispatch_checklist` (lines 201-206), which is **preview-only**, and in the operator's personal MEMORY.md (not repo-tracked, not readable by a fresh non-Operator-scoped seat).
- Queue-stocking / conveyor cadence.
- Resume-state checkpointing mechanics (format, mtime-pickup, dual-write target) — named in the preview SSOT but no runtime code enforces or verifies it.

This is exactly the split the task asked for: **the duty manifest's job is to make the second column into first-class data**, because today it exists only as prose in a preview-only design doc plus (outside this repo) an individual's memory file.

### 1.3 Credential surface

Confirmed mechanisms:

- `validators/creator_engine_validator/schemas/identity-registry.schema.yaml` — a full JSON-Schema for a **non-secret** registry: `repos`, `accounts`, `apps`, `tokens`, `signing_keys`, `host_topology`, `authoring_review_matrix`. Every secret-bearing field is a **pointer** (`openbao_ref` pattern `^openbao-ref:...`, `openbao_pointer` object with `mount/path/policy/rotation_owner`, or `TODO_VERIFY`) — never a value. This schema exists in *this* repo even though the SSOT instance itself (per the user's memory) lives in the separate `ce-ops` repo at `infra/identity-registry.yaml`. **Design implication:** the standup script/runbook should validate any registry instance it reads against this schema, and should refuse (fail-closed) if a field that should be a pointer contains something that looks like a live secret (there is already a `_looks_like_inline_secret_value` guard pattern in `secret_identity.py:398`).
- `validators/creator_engine_validator/secret_identity.py` provides `SecretRef`, `SecretRequest`, `SecretGrant`, `SecretZeroRequest/Grant/Payload`, and `OpenBaoSecretIdentityBackend` (line 1007) with `kv_mount="ce-kv"` default (line 262, 887) — this is the existing value-free credential-resolution primitive the standup script should call rather than reinvent. It already has a guard rejecting refs that name the controller key (`_ref_names_controller_key`, line 393).
- `docs/decisions/ADR-0012-openbao-micro-unit-standup.md` is direct precedent: a prior ADR already designed a "stand-up" procedure for a security-sensitive subsystem (OpenBao itself), citing ADR-0005 and the secret-zero broker contract. Phase A's runbook should follow the same evidence-and-precondition discipline this ADR models, and should explicitly cite it as a sibling artifact, not a dependency.
- The **ce-root-v1 offline key** (Operator custody, `~/.ce-keys/ce-root-v1{,.pass,.pub}` per the user's memory) is correctly out of scope for automated standup — it is the one non-delegable act per the user's own `ce-release-spec-signing-procedure` note, and the D1 action-taxonomy in ADR-0013 lists "sign" under **Reserved**.

### 1.4 The knowledge gap (input to #166 D1b migration)

By diffing "what a fresh `ce launch` + repo-read gets" against "what the operating practice implies is needed" (per `docs/design/ce-orchestrator-agent.md:61-76` "Important gaps remain" section, which already names several of these), the categories a replacement controller cannot get from the repo today are:

1. **Seat-drive mechanics per substrate** — herdr socket paths (`HERDR_SOCKET_PATH=/run/creator-engine/herdr/herdr.sock`), `docker exec` container names per dev seat, tmux pane addressing conventions. `playbooks/controller/harness.md` documents *that* you probe via `docker exec`, but not the concrete container names, socket paths, or per-seat addressing — those live only in the Operator's memory file.
2. **Host topology and reachability** — which host is CE-DEV-1 vs DGX vs laptop, SSH aliases (`ssh dev1`), tailnet addressing. `identity-registry.schema.yaml`'s `host_topology` section is the intended home, but the *instance* is in the separate `ce-ops` repo, not readable from this checkout.
3. **Gate-evidence standards beyond the one-line briefs** — the pre-dispatch territory-check sequence, the two-strikes rule, the G5 body-line rule, model/effort routing table — all exist only in the **preview-only** `controller-bootstrap-ssot.json`'s `controller_knowledge_overlay`, never promoted to a ratified/live bootstrap file.
4. **Cadence/cron duty inventory** — seat-check/poll-devs/conveyor-tend timings exist only as prose in the orchestrator design doc, not as a runnable, health-checkable artifact.
5. **Daemon inventory and restart procedures** — merge-queue daemon, approval-wall daemon: no manifest entry, no health-check command, no restart command in-tree (only in the Operator's memory: "restart via launcher `bash ~/ce-wall-daemon-launch.sh`").
6. **Credential *instance* resolution** — the registry *schema* is in-repo; the registry *data* and the OpenBao per-seat KV paths are not (by design, correctly, since they're pointers into a system outside this repo).
7. **The org/product-level "why"** — arc mandates, doctrine (energy-efficiency, no-MVP, positioning), Operator-ratification history — this is squarely what a "brain"/knowledge-substrate migration (the #166 D1b input) should absorb; it is currently 100% in the Operator's personal `MEMORY.md`, unreadable by a fresh non-Operator seat.

## 2. Duty Manifest Draft

Proposed path: `playbooks/controller/duties.yaml` (co-located with the existing `workflow.ce.yml`/`envelope.template.yml`/briefs, consistent with how `playbooks/controller/` already models controller-scoped machine-readable records — not `.ce/` because `.ce/` is working state, and this is a tracked, ratified artifact like `workflow.ce.yml`).

```yaml
kind: ce-controller-duty-manifest
schema_version: "1"
metadata:
  owner_issue: ce-ops#398
  status: draft
  generated_by: manual   # future: scripts/gen-controller-duties.py
duties:
  # --- watchers (session-level, must be re-armed on every controller resume) ---
  - id: pr-board-monitor
    kind: watcher
    description: >-
      Monitor open PR board for review/CI/mergeability state changes.
    owner_process: controller-session
    survives_controller_death: false
    re_arm:
      procedure_ref: playbooks/controller/briefs/merge-gate.md
      command: null   # session-level; re-armed by controller re-reading this manifest on resume
    health_check:
      kind: manual
      description: "Controller must confirm it is actively polling; no independent process to probe."
    criticality: high

  - id: seat-stall-watcher
    kind: watcher
    description: >-
      Monitor dispatched seats (dev-1/3/4) for stall/liveness/context-pressure.
    owner_process: controller-session
    survives_controller_death: false
    re_arm:
      procedure_ref: playbooks/controller/briefs/seat-refresh.md
      command: null
    health_check:
      kind: manual
    criticality: high

  # --- host crons (survive controller death; controller must confirm they are armed) ---
  - id: seat-check-cron
    kind: cron
    description: "Per-seat context/pane/stall check."
    schedule: "0 * * * *"          # :00 hourly per seed context; TODO_VERIFY exact cadence
    owner_process: host-cron
    survives_controller_death: true
    re_arm:
      procedure_ref: null          # TODO: needs a tracked runbook; currently host-crontab only
      command: null
    health_check:
      kind: process
      probe: "TODO_VERIFY: crontab -l | grep seat-check"
    criticality: medium

  - id: poll-devs-cron
    kind: cron
    description: "Collect seat liveness, stop lines, blockers from dev-1/3/4."
    schedule: "5 * * * *"
    owner_process: host-cron
    survives_controller_death: true
    re_arm:
      procedure_ref: null
      command: null
    health_check:
      kind: process
      probe: "TODO_VERIFY: crontab -l | grep poll-devs"
    criticality: medium

  - id: conveyor-tend-cron
    kind: cron
    description: "Move ready harvested work through review/gate/next-lane."
    schedule: "30 * * * *"
    owner_process: host-cron
    survives_controller_death: true
    re_arm:
      procedure_ref: null
      command: null
    health_check:
      kind: process
      probe: "TODO_VERIFY: crontab -l | grep conveyor-tend"
    criticality: medium

  # --- daemons (independent long-lived processes) ---
  - id: merge-queue-daemon
    kind: daemon
    description: >-
      Auto-merges any ce-dev-2-approved + green PR (~120s cadence).
      Survives controller death by design.
    owner_process: queue-daemon
    survives_controller_death: true
    re_arm:
      procedure_ref: null   # TODO: promote from operator memory to a tracked runbook
      command: "TODO_VERIFY: pgrep queue-daemon"
    health_check:
      kind: process
      probe: "pgrep queue-daemon"
    credential_dependency: "approval-wall-token (OpenBao ce-kv ref; bakes GH token at launch, 401 fail-closed on rotation)"
    criticality: critical

  - id: approval-wall-daemon
    kind: daemon
    description: "OpenBao-backed approval wall; gates merge trigger."
    owner_process: wall-daemon
    survives_controller_death: true
    re_arm:
      procedure_ref: docs/devops/openbao-approval-wall-arming.md
      command: "TODO_VERIFY: bash ~/ce-wall-daemon-launch.sh"
    health_check:
      kind: process
      probe: "TODO_VERIFY: pgrep queue-daemon (shared health surface?)"
    criticality: critical

  # --- procedures (codified, in-tree, no independent process — controller executes on demand) ---
  - id: dispatch
    kind: procedure
    description: "Create governed-seat brief; verify work claim before start."
    procedure_ref: playbooks/controller/briefs/dispatch.md
    workflow_stage_ref: playbooks/controller/workflow.ce.yml#stages.dispatch
    criticality: high

  - id: harvest
    kind: procedure
    description: "Collect worker output at READY; stage; regen carriers; enqueue for review."
    procedure_ref: playbooks/controller/briefs/harvest.md
    criticality: high

  - id: merge-gate
    kind: procedure
    description: "Confirm independent review + green checks + ratification before merge."
    procedure_ref: playbooks/controller/briefs/merge-gate.md
    workflow_stage_ref: playbooks/controller/workflow.ce.yml#stages.merge-gate
    criticality: critical

  - id: seat-refresh
    kind: procedure
    description: "Save resume state, clear context, resume from precise state file."
    procedure_ref: playbooks/controller/briefs/seat-refresh.md
    criticality: medium

  - id: courier-forge-op
    kind: procedure
    description: "ADR-0007 model-b bridge for contained seats needing a forge op."
    procedure_ref: playbooks/controller/briefs/courier-forge-op.md
    sunset_condition: "ADR-0007 egress gateway / publish broker lands"
    criticality: medium

  - id: resume-state-checkpointing
    kind: procedure
    description: >-
      Emit .ce/state/research/RESUME_STATE_* on checkpoint; newest-by-mtime
      pickup on resume; dual-write to CE-DEV-1 host.
    procedure_ref: docs/design/controller-bootstrap-ssot.json#controller_knowledge_overlay.startup_sequence
    status: "codified in preview-only SSOT; not ratified/live; not runtime-enforced"
    criticality: critical

  - id: queue-stocking
    kind: procedure
    description: "Controller keeps conveyor queue populated with ready, unblocked work."
    procedure_ref: docs/contracts/orchestrator.md#nine-step-lifecycle
    criticality: medium
```

## 3. Runbook Outline

Proposed path: `playbooks/controller/runbooks/controller-standup.md` (parallel to `playbooks/controller/runbooks/arad-pilot.md`, which already establishes `playbooks/controller/runbooks/` as the location for procedural runbooks distinct from action briefs).

Structure (self-verifying, PASS/FAIL per step, modeled on `docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md`'s clause-table style and `doctor_runtime.py`'s report shape):

1. **Preconditions** — replacement host has repo checkout at known commit, model-provider credential available by name, no live controller claim held (see §6 lock).
2. **Step 1 — Knowledge hydration.** Read this runbook top-to-bottom; read `docs/contracts/orchestrator.md`, `playbooks/controller/workflow.ce.yml` + briefs, `playbooks/controller/duties.yaml`. Self-test: PASS iff all listed paths exist and parse.
3. **Step 2 — Resume-state pickup.** Glob `.ce/state/research/RESUME_STATE_*` (and CE-DEV-1 dual-write mirror), pick newest by mtime, surface any `AWAITING-OPERATOR` markers first. Self-test: PASS iff at least one resume file found OR explicit "cold start, no resume state" is logged.
4. **Step 3 — Brain bootstrap.** Run `ce launch --harness <h> --claim-ticket <standup-ticket> --controller-id <replacement-id> --host-id <host> --dry-run --json` to materialize `brain-bootstrap.json` without side effects; verify `operating_mode.foreman_charter` and `foreman_dispatch_contract` are present (per `brain_bootstrap.py`). Self-test: PASS iff dry-run exits 0 and payload validates.
5. **Step 4 — Duty manifest read + health probes.** For every entry in `playbooks/controller/duties.yaml` with `survives_controller_death: true`, run its `health_check.probe`. Self-test: PASS iff merge-queue-daemon and approval-wall-daemon both report alive (they must survive the original controller's death — if they're down, standup should HALT and page Operator, not silently re-arm a gate-authority process).
6. **Step 5 — Credential pointer resolution.** For each credential the controller needs by name (model-provider key, ce-dev-2 PAT pointer, reviewer-token pointer — NOT ce-root-v1), resolve via `secret_identity.py`'s backend against the identity-registry pointer, never printing values. Self-test: PASS iff every named credential resolves to a grant/ref, FAIL closed on any TODO_VERIFY or inline-secret-shaped value (reuse `_looks_like_inline_secret_value` pattern).
7. **Step 6 — Gate-authority claim/lock check (see §6).** Verify no other live controller holds the standup/gate lock; if the original controller is still alive, refuse to arm merge-gate/approval-wall duties (read-only shadow mode only).
8. **Step 7 — One benign governed action.** Execute a read-only-adjacent, reversible action (e.g., `ce doctor`, or a dry-run `ce validate-pr` on a clean checkout, or reading the PR board) as the acceptance drill for "reached operational parity." Self-test: PASS iff the action's evidence matches the expected shape from the relevant brief.
9. **Step 8 — Emit standup evidence record + checkpoint.** Write a checkpoint using the `Checkpoint` record shape already specified in `docs/contracts/orchestrator.md:202-221`, marked `standup_drill: true`.
10. **Overall verdict** — PASS only if every step's self-test passed; otherwise print the first FAILing step and refuse to claim controller duties.

## 4. Standup Script Design

Proposed path: `scripts/controller-standup.sh` (or `.py` — see below), following the `scripts/clean-room-rehearsal.sh` precedent: `--dry-run` fail-closed default, `--live` explicit opt-in, `--list-stages`, per-stage selectability, zero secret defaults, `set -euo pipefail`, `trap cleanup`.

Recommended: **Python**, not bash, because it needs to call `brain_bootstrap`, `secret_identity`, and JSON-Schema validation against `duties.yaml`/`identity-registry.schema.yaml` — bash would just shell out to the same Python anyway. Put it at `scripts/controller-standup.py` invoked via the repo's existing `PYTHONPATH=validators python3 -m ...` convention (matches how `ce_cli.py` is invoked in `SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md:37-38`), with a thin `scripts/controller-standup.sh` wrapper for operator ergonomics (the "one-liner"), mirroring the bash-wraps-python pattern already visible in `scripts/ce-preflight.sh` (calls into the validator suite).

Shape:
```
scripts/controller-standup.sh [--dry-run|--live] [--stage NAME] [--list-stages] [--json]
```
Stages: `read-runbook`, `resume-pickup`, `brain-bootstrap`, `duty-health`, `credential-resolve`, `gate-lock-check`, `benign-drill`, `checkpoint-emit` — one-to-one with the runbook steps above, each idempotent and independently re-runnable (so a partially-failed standup can resume from the failing stage, per the `--stage` pattern in `clean-room-rehearsal.sh`).

Idempotency/fail-closed requirements:
- No stage performs a write with side effects (branch push, PR action, daemon restart) unless `--live` is passed AND step 6 (gate-lock) passes.
- Every stage prints `CE_STANDUP status=PASS|FAIL stage=<id> msg=...` to stderr (same convention as `clean-room-rehearsal.sh`'s `log()`), never a secret value.
- Script refuses (exit 1) if invoked with any environment variable that looks like an inline secret matching `_looks_like_inline_secret_value`-style heuristics, defensively, even though it shouldn't need any.

## 5. Drill Protocol

1. **Sandbox target**: a scratch worktree or ephemeral container (reuse `clean-room-rehearsal.sh`'s docker-container pattern), never the live `.ce/state/active-work-ledger` or the live approval-wall daemon.
2. **Cold-standup rehearsal**: run `scripts/controller-standup.sh --live` in the sandbox with the original controller session presumed dead (simulate by not holding any lock); confirm it reaches step 7 and executes one benign action end-to-end, then halts (does not proceed to claim live gate authority) since this is a *drill*, not a real failover.
3. **Warm-shadow rehearsal**: run the same standup with the original controller *alive*, to prove step 6 (gate-lock check) correctly refuses to arm merge-gate/approval-wall duties and stays in read-only shadow mode — this is the safety-critical negative test.
4. **Gap capture**: every `TODO_VERIFY` or manual `health_check.kind: manual` entry hit during the drill is logged as a gap item; feed these into the #166 D1b knowledge-migration backlog (§1.4 above is the seed list).
5. **Evidence**: drill run emits a checkpoint record (per `docs/contracts/orchestrator.md` Checkpoint shape) tagged `standup_drill: true`, stored under `.ce/` (untracked, consistent with existing resume-state convention) — not committed to git.

## 6. Risks / Gotchas

- **Double-hold of the merge gate.** This is the sharpest risk. Propose a **standup claim/lock**, reusing the existing `work_claims.py` machinery (`work_claims.acquire`, referenced at `ce_cli.py:4340-4344`) as a `controller-standup` claim type, or a dedicated lock file under `.ce/state/active-work-ledger` that both the original and replacement controller check before arming `merge-queue-daemon`/`approval-wall-daemon` duties. The drill protocol's step 3 above is the acceptance test for this. Until this lock exists, Phase A standup must default to **read-only shadow mode** for gate-authority duties (safe default; matches the repo's fail-closed posture throughout `secret_identity.py`, `brain_bootstrap.py`, `devops_privileged_action_broker.py`).
- **Codex-vs-Claude harness differences.** `launch_runtime.launch()` supports `claude|codex|hermes|openclaw` (`SUPPORTED_HARNESSES`, line 52) with materially different Ring-0 governed-command construction (`claude_launch_spec.py` vs `codex_launch_spec.py`). The task explicitly allows a codex-based replacement — the standup runbook/script must be harness-parametric from the start, not claude-only, and should reuse `docs/design/controller-bootstrap-ssot.json`'s existing codex/claude vocabulary mapping rather than reinvent role naming.
- **Preview-only SSOT is not live.** A large fraction of the "duty knowledge" this ticket wants to codify (`controller_knowledge_overlay` in `controller-bootstrap-ssot.json`) is explicitly marked non-ratified for live injection. Phase A's runbook can *read* it as a reference, but should not claim it as an enforced bootstrap contract until a separate ratified promotion step lands — call this out in the runbook's own status header, mirroring the "Preview-only... do not install" warning already in the SSOT metadata (line 7).
- **ce-root-v1 stays Operator-only.** Confirm this explicitly in the manifest/runbook (already reflected in the duty manifest by omission — no duty entry references it) and in the script (never attempt to resolve it as a credential pointer).
- **Identity-registry instance is out-of-repo.** The schema lives here; the ratified instance lives in `ce-ops/infra/identity-registry.yaml`. The standup script must accept an external path/pointer to that file rather than assume it is checked into `creator-engine`, and must validate whatever it's given against `identity-registry.schema.yaml` before trusting it.
- **Duty manifest drift.** A hand-maintained `duties.yaml` will rot. Recommend a follow-on ticket (not Phase A) to add a `scripts/gen-controller-duties.py` cross-check against actual crontab/systemd state, similar to how `gen-controller-bootstrap.py` cross-checks the bootstrap SSOT — flag this as an explicit Phase B dependency rather than scope-creep Phase A.
- **`ce launch` claim-ticket gating.** Because brain bootstrap only fires when `--claim-ticket` is supplied (`ce_cli.py:4304-4306`), the standup script must always pass a (standup-scoped) claim ticket, or it will silently skip the one hydration mechanism that exists — easy to get wrong.

## 7. Per-Slice Work Classes (Phase A)

All sized to stay S/M per the repo's declared-work-class discipline (`ce-ops#303`, `G5` gate):

| Slice | Deliverable | Proposed class |
|---|---|---|
| A1 | `playbooks/controller/duties.yaml` (schema + populated draft above, with explicit `TODO_VERIFY` markers for unknowns) | S |
| A2 | `playbooks/controller/runbooks/controller-standup.md` (outline in §3, self-verifying steps) | S |
| A3 | `scripts/controller-standup.py` + `scripts/controller-standup.sh` wrapper, `--dry-run` stages only (no `--live` execution yet) | M |
| A4 | Live `--live` execution path: duty health probes, credential-pointer resolution via `secret_identity.py`, benign-drill action | M |
| A5 | Standup claim/lock primitive (reuse `work_claims.py`) to prevent double-hold of merge-gate authority | M |
| A6 | Drill protocol write-up + first sandbox rehearsal evidence (cold + warm-shadow runs) | S |

Suggested order: A1 → A2 → A3 → A5 → A4 → A6 (lock primitive before the live execution path that needs it).

## 8. Open Questions for the Controller/Operator

1. Should `duties.yaml` be hand-authored (Phase A) with a generator deferred to Phase B, or is a minimal generator in-scope now given `gen-controller-bootstrap.py` precedent?
2. Is the standup-claim lock a new `work_claims.py` ticket type, or should it reuse the existing Active-Work-Ledger seat-lifecycle claim machinery directly?
3. Does Phase A need to support a **codex-based** replacement controller end-to-end (full harness parity), or is Phase A allowed to ship claude-only with codex marked `TODO_VERIFY` in the manifest?
4. Where should the *ratified instance* pointer for `identity-registry.yaml` be declared inside `creator-engine` (a stub/pointer file, or purely runbook prose citing the `ce-ops` path)?
5. Should the "one benign governed action" acceptance test in the drill be `ce doctor`, a dry-run `ce validate-pr`, or something with forge read-egress (e.g., listing the PR board) to also prove source-host read reachability?

## Sources Consulted (repository paths)

- `/home/cedev2/creator-engine/validators/creator_engine_validator/brain_bootstrap.py`
- `/home/cedev2/creator-engine/validators/creator_engine_validator/launch_runtime.py`
- `/home/cedev2/creator-engine/validators/creator_engine_validator/ce_cli.py` (lines ~3537-3750, ~4300-4345)
- `/home/cedev2/creator-engine/validators/creator_engine_validator/secret_identity.py`
- `/home/cedev2/creator-engine/validators/creator_engine_validator/doctor_runtime.py`
- `/home/cedev2/creator-engine/validators/creator_engine_validator/devops_privileged_action_broker.py`
- `/home/cedev2/creator-engine/validators/creator_engine_validator/schemas/identity-registry.schema.yaml`
- `/home/cedev2/creator-engine/playbooks/controller/README.md`, `harness.md`, `workflow.ce.yml`, `envelope.template.yml`
- `/home/cedev2/creator-engine/playbooks/controller/briefs/{dispatch,harvest,merge-gate,seat-refresh,courier-forge-op}.md`
- `/home/cedev2/creator-engine/playbooks/controller/runbooks/arad-pilot.md` (location precedent)
- `/home/cedev2/creator-engine/docs/contracts/orchestrator.md`
- `/home/cedev2/creator-engine/docs/design/ce-orchestrator-agent.md`
- `/home/cedev2/creator-engine/docs/design/controller-bootstrap-ssot.json`
- `/home/cedev2/creator-engine/docs/design/controller-bootstrap-injection.md`
- `/home/cedev2/creator-engine/docs/decisions/ADR-0013-substrate-independent-authority.md`
- `/home/cedev2/creator-engine/docs/decisions/ADR-0012-openbao-micro-unit-standup.md`
- `/home/cedev2/creator-engine/docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md`
- `/home/cedev2/creator-engine/scripts/clean-room-rehearsal.sh` (standup-script precedent)
- `/home/cedev2/creator-engine/scripts/gen-controller-bootstrap.py`, `scripts/ce-preflight.sh`
- `/home/cedev2/creator-engine/surfaces/manifest.yaml` (confirmed `scripts/` not `surfaces/` is the right location)

**Note on prior art**: `docs/design/ce-orchestrator-agent.md`'s epic table (lines 549-561, items 5 and 9) already proposes "Specify Orchestrator checkpoint record" and a "read-only Orchestrator cockpit" that substantially overlap with #398's duty-manifest/standup goals. Recommend the controller explicitly cross-reference #398 against that epic to avoid parallel, divergent designs — Phase A as scoped here is a legitimate, narrower slice (standup mechanics + duty data) that can feed the broader orchestrator epic rather than compete with it.