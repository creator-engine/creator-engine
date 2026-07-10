# CE Dark-Factory Guide — Operator Reference
**Audience**: Operator of CE's own internal fleet deployment
**Date**: 2026-07-08
**Status**: Internal definitive reference — living document, anchored to TODAY 2026-07-08

---

## 1. Executive Summary

The CE dark factory is the end-state in which Creator Engine builds its own software
autonomously: Operator and controller co-frame ideas in natural language, the controller
produces a ratified arc and tickets, governed seats pick up work autonomously, local and
forge-level automation handles PR mechanics and review assignment, and the merge gate
materializes committed intents — all without manual git operations by the Operator.

The Operator's role shifts from "hands-on developer" to "CEO-mode": ratify arcs,
arm new authorities, handle escalations, hold root-key custody, and manage external
relationships. Every other delivery action is either autonomous (when predicates hold) or
surface-visible and queued for the Operator (AWAITING-OPERATOR state).

**Endgame picture (target state, not yet current)**:
- Forge events spawn ephemeral NanoClaw controllers from content-addressed mandate pointers
- A pickup conveyor feeds seats with ready tickets from the ratified arc
- A containerized review daemon assigns reviewers and spawns review lanes automatically
- A triage daemon processes seat-filed tickets via belt-feed polling
- ce-queue-daemon (containerized singleton) is the merge gate and Option A materializer
- The host-ops broker mediates all host-level operations from within contained contexts
- Controllers themselves are contained and IaC-reprovisioned (T1 Aug 11 / T2 Aug 31)

---

## 2. The Five Layers

### Layer 1: Operator + Controller Framing and Shaping Loop

**What it is**: The conversational and governance loop where ideas become ratified arcs.

**Frame stage**: The Operator describes objectives in natural language to the controller.
The controller classifies the request, maps it to CE governance vocabulary (arc, lane,
ticket, work class), checks against active claims and in-flight work, and proposes a
Frame artifact.

**Shape stage**: The controller produces:
- A short-term arc (ordered lanes with dependencies)
- Roadmap update candidates (mid/long-term)
- Tickets in ce-ops with correct work-class labels (XS/S/M/L)
- Carrier manifests for governed PRs
- Per-PR changelog fragments

**TODAY (2026-07-08)**: The controller (CE-DEV-2, non-contained, Claude Code Ring 0/1/2
green, gate-capable) hand-authors briefs, dispatches via file+SHA pointer, and manually
maintains the arc in resume state files (`.ce/state/research/RESUME_STATE_CE_DEV2_*`).
Decisions are in `.ce/state/decisions/DECISIONS_20260708.md`. The conveyor intake is
manual: the controller creates briefs, places them in `.ce/briefs/`, and dispatches seats
by sending the pointer + SHA.

**TARGET**: Controller bootstrap SSOT (`docs/design/controller-bootstrap-ssot.json`) is
the live injection source. The orchestrator agent (`docs/design/ce-orchestrator-agent.md`)
is a shipped product artifact running the full lifecycle from intake through gate.

#### Framing Guarantee: How CE Enforces Governed Framing Without `/ce frame`

The Operator's question is answered here explicitly. Today, the persistent controller
on CE-DEV-2 operates without an explicit `/ce frame` verb invocation, and governed seats
on other hosts also operate without a user invoking `/ce` commands.

CE guarantees governed framing through **harness-enforcement at the seam**, not through
explicit verb invocation. The mechanism has three layers:

1. **Launch wiring**: `ce launch --harness codex` (or `claude`) is the canonical
   entry verb. The governed command builder in `validators/creator_engine_validator/
   claude_launch_spec.py` / `codex_launch_spec.py` wraps every seat launch with:
   - Ring 0: scrubbed ambient repo credentials, controlled environment
   - Ring 1: PreToolUse hook (`/.claude/hooks/ce-pretooluse.sh`) registered before harness start
   - Ring 2: Stop hook registered (Claude Code only; green Ring 2)
   The hooks enforce governance at every tool call — the seat cannot bypass checks by
   omitting a command prefix.

2. **PreToolUse checks**: `.claude/hooks/ce-pretooluse.sh` runs `hook_check.py`
   (`validators/creator_engine_validator/hook_check.py`) on every tool invocation.
   This is the harness seam: governance attaches here regardless of whether the session
   started with `/ce frame` or a blank prompt. The check enforces path scope, reviewer
   authority envelopes, role-shaped tool absence, and work-claim binding.

3. **`ce takeover` as the entry verb for succession**: When a controller resumes, `ce
   takeover` ingests evidence packets and reconstructs governance context. Framing becomes
   a natural precondition of any subsequent action — the controller cannot proceed to
   dispatch without a ratified claim and brief.

**Soft intent recognition, hard enforcement**: A user (or the Operator) can describe an
objective in any phrasing. Intent recognition is soft (model-level). But enforcement is
hard: the harness validates every mutation against ratified claims, path manifests, and
evidence requirements before allowing it. The grader sits outside the agent
(`docs/architecture/stage-vocabulary.md`; see also `docs/operations/HARNESS_SEAT_CONTRACT.md`).

Reference: `docs/operations/GOVERNED_LANE_LAUNCH_PROTOCOL.md` §d (operating-mode floor,
prompt pointer + SHA, visibility, live claim binding), `docs/operations/
HARNESS_SUPPORT_CAPABILITY_MATRIX.md` (Ring 0/1/2 green for claude_code and codex Ring 0).

---

### Layer 2: Intake Conveyor — Arc to Tickets to Pickup Queue to Seats

**What it is**: The pipeline from ratified arc to seats picking up work units.

**Arc**: A short-term plan (ordered lanes A-1..A-N) with dependencies, evidence gates,
and rollback stories. Ratified by the Operator (e.g. DAY-ARC 2026-07-08 in
`DECISIONS_20260708.md` decision 8).

**Tickets**: Filed in ce-ops GitHub repository with work-class labels (XS/S/M/L).
Each ticket maps to one or more bounded PRs. Carrier manifests (`carriers/` directory in
each PR) declare the path set and work class.

**Pickup model (TARGET)**: Seats self-select ready tickets from the arc queue, claim
them via work-claim lock, implement, self-verify (`ce validate-pr`), self-push, and open
a PR. The controller does not push-dispatch individual work items.

**TODAY**: Pickup is semi-manual. The controller creates individual briefs per seat,
sends pointer+SHA via herdr PTY to each contained seat, and monitors for READY stop-lines.
Contained seats (dev-3, dev-4) receive briefs, implement in their gVisor worktrees
(`/var/tmp/`), and push via egress broker or App-mint credential helper.

**Work sizing discipline**: XS/S/M/L classes with PR body line `- **Declared work class:**
tiny|story|feature|epic`. G5 gate in CI enforces exactly one such line per governed PR.

**Fleet today (2026-07-08)**:
- dev-1: VPS (Hetzner 100.72.252.20), non-contained, self-push, ssh dev1
- dev-3: VPS gVisor contained (`ce-vps-codex`), egress-broker self-push, rebuilding (new amd64 image with ssh-keygen; #494/#899 path)
- dev-4: DGX gVisor contained (`ce-dgx-codex`), App-mint credential helper, strongest seat

---

### Layer 3: Build — Governed Seats, Containment, Self-Verify, Self-Push

**What it is**: How seats turn tickets into governed PRs.

**Containment ring (dev-3, dev-4)**: gVisor runsc isolation.
- No raw Docker/Podman socket inside the container
- Egress broker (`tools/egress-broker/`) mediates network access
- Host-ops broker (`tools/host-ops-broker/`, `docs/design/host-ops-broker-v1.md`)
  mediates any host-level repair operations via typed verbs (status, restart-daemon,
  prepare-owned-state-root, etc.) — no raw socket passthrough
- Worktrees in `/var/tmp/` (in-memory on DGX; OOM = total loss, harvest early)

**Identity / self-push**:
- dev-1: personal git config, ssh-based push to creator-engine remote
- dev-3: egress broker path; rebuilding for ssh-keygen parity (#899 merge unblocks Arad apply)
- dev-4: ce-materializer App 4244593 (contents:write, single-repo, ruleset always-bypass,
  arming gated), installed inst 145152358, PEM at `~/.ce-keys/ce-materializer.2026-07-07.private-key.pem`
- Per-seat GitHub Apps: dev-1/3/4 each have their own App identity (registry SSOT:
  `ce-ops:infra/identity-registry.yaml`)

**Self-verify (seat-ready profile, merged #896)**:
- Seats run `ce validate-pr` before READY stop-line
- Seat-side preflight design (`docs/design/seat-side-preflight.md`): validates generated
  reference freshness, carrier path set vs real diff, changelog fragment presence,
  declared work class line — catches failures before controller harvest

**Harvest (TODAY)**: Controller executes `docker exec ce-dgx-codex cat <bundle>` (exec-cat
pattern) to extract committed work from contained seats. `herdr pane read` used to check
READY. Bundle over exec-cat: `git bundle create - --all | base64` inside container,
pipe out.

**Carrier discipline**: Every governed PR carries:
- One changelog carrier (`.ce/changelog/<slug>.md`)
- One path-manifest carrier (generated from committed diff, not hand-edited)
- Carrier slug must match branch slug (`ce-harvest-carrier-slug-must-match-branch`)

---

### Layer 4: The Gate — Review Daemon, Approval, Merge Queue, Gate Daemon, Option A Materializer

**What it is**: The automated pipeline from PR open to brain ledger materialization.

#### Sub-layer 4a: Review Assignment

**Operator's question (c4)**: Is reviewer assignment local or forge level?

**Answer — Hybrid model (forge-as-hub, brains-local)**:

The assignment is a two-tier operation:
- **Forge events are the trigger and SSOT transport**: GitHub PR-opened / PR-synchronized
  webhooks deliver the canonical event. The forge is the hub that routes the signal.
- **Assignment decision + reviewer spawn is local**: A containerized CE daemon (the review
  daemon, TARGET state) applies the author/reviewer separation matrix
  (author ≠ reviewer, as per `docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md`),
  selects an authorized reviewer identity from CODEOWNERS / `CE_GATE_AUTHORIZED_REVIEWERS`,
  and spawns a local reviewer lane (`ce lane launch --role reviewer --lane-kind review`
  with a minted reviewer-authority envelope). The spawn happens on CE-DEV-2 or CE-DEV-1,
  not in GitHub Actions.

**TODAY**: The controller manually spawns reviewer subagents as restricted Claude Code
subagents (not forks), routes the PR branch + context, and submits the approval
(`GH_TOKEN=$(cat ~/.ce-keys/ce-dev-2.pat) gh pr review <n> --approve`) after
independent review evidence is assembled. Authorization: approval IS the merge trigger
(ce-dev-2 approval-wall daemon watches for approval + required checks green).

Reference: `playbooks/reviewer/`, `.claude/agents/reviewer.md`,
`docs/delivery/REVIEW_GATE.md`, `docs/operations/GOVERNED_LANE_LAUNCH_PROTOCOL.md` §0b
(reviewer-venue authority minting), `deploy/queue-daemon/RELOCATION.md` `CE_GATE_AUTHORIZED_REVIEWERS`.

#### Sub-layer 4b: Approval and Merge Queue

**Approval wall**: The queue daemon reads the approval-capability wall secret from
OpenBao (`ce-kv/forge/approval-capability/wall#signing_secret`) to verify approval
markers. Approval from an authorized reviewer (ce-dev-2 overwatch PAT or reviewer token)
with all required checks green triggers automatic merge queue enqueue.

**Merge queue**: ce-reference-protection-floor ruleset on main. Required: 1 review +
required check (`validate`) + merge queue. Squash merge. Classic protection retired
(2026-07-08, replaced 1:1 by the ruleset). The ce-materializer App 4244593 is the
sole always-bypass actor.

#### Sub-layer 4c: Containerized Merge Gate Daemon

**ce-queue-daemon** (C5 promoted, decision 3, 2026-07-08):
- Container: `creator-engine/ce-runtime:0.3.2-main`
- Worktree: `ce-daemon-main` @ origin/main (14b0c178 as of C5 cutover)
- State: `/var/lib/ce-queue-daemon/` host path → `/ce/state/` in container (uid-10001 ownership)
- Secrets: tmpfs custody, BAO token TTL ~24.5d
- Systemd unit: `ce-queue-daemon.service` (`Restart=always`, journald logging)
- Host daemon (DGX `~/ce-wall-daemon-launch.sh`): STOPPED, rollback-only
- Rollback command: `sudo docker stop ce-queue-daemon; bash ~/ce-wall-daemon-launch.sh`

The daemon is a strict singleton gated by filesystem lease `queue-daemon.lease`.
Singleton + IaC redeploy rule (decision 1): IaC redeploy precondition must be met
before arming any new singleton authority. #895 (IaC redeploy PR, approved) is the
precondition for arming the Option A materializer.

#### Sub-layer 4d: Option A Materializer (design/in-build)

Design: `docs/design/ce-491-optiona-merge-intent.md`
Implementation: dev-4 working ce-491-optiona-slice1 (ARMING_ENABLED=False hard invariant, dry-run only)

**What it does**: After a PR merges, the gate daemon detects intent files at
`.ce/brain/append-intents/<branch-slug>.yaml` and materializes them into
`.ce/brain/assertions.yaml` (the append-only hash-chain brain ledger) via a
direct-commit-to-main. Intent file is then removed. Evidence: PR comment +
daemon log + `CE-Materialization-Key:` commit trailer.

**Authority**: Narrow ce-materializer App 4244593 (decision 11): contents:write, single-repo,
PEM custody `ce-kv/forge/materializer#private_key` (OpenBao migration TODO). Branch-protection
bypass scoped to this App alone, independently revocable.

**Arming gates**: #895 IaC redeploy merge + Option A slice 2+ + Operator arming call.

**Failure modes**: HELD state with structured reason; quarantine artifacts in
`.ce/state/brain-intent-quarantine/<key>.json`; 30-minute closeout window before
hard gate failure.

---

### Layer 5: Host/Ops Substrate

**What it is**: The infrastructure that all layers run on.

#### Host-Ops Broker (design, partial impl)

Design: `docs/design/host-ops-broker-v1.md`
Merged slice: PR #898 (broker v1 slice 1, merged today)

Systemd-supervised host service. Typed verbs only — no raw socket passthrough:
- `status` — health of daemons, containers, systemd units, state roots, OpenBao
- `restart-daemon` — restart CE-owned daemon by configured name (3/15min rate limit)
- `prepare-owned-state-root` — create/repair CE-owned state root with correct ownership
- `rotate-attempt-log` — rotate CE subsystem logs
- `repair-systemd-unit` — reenable and restart failed CE-owned systemd unit
- `run-ephemeral-container` — CE-owned digest-pinned image only, no arbitrary pulls
- `prune-stopped-owned-containers` — CE namespace only
- `snapshot-openbao` / `restore-drill-openbao` — backup and drill

Request/response envelope: `ce.host_ops.request.v1` / `ce.host_ops.response.v1`.
Kill switch: broker-wide disable and per-verb disable. All refusals emit audit records.
Controllers and seats never receive raw runtime sockets.

#### IaC Singleton Redeploy (#895)

Policy: `ce-singleton-plus-iac-redeploy-rule` (decision 1). Every singleton authority
requires a one-click IaC redeploy path as precondition. PR #895 delivers this for
the queue daemon / future daemons.

#### OpenBao Secret Custody

OpenBao at 100.72.252.20:8200 (CE-DEV-1 VPS). Holds:
- Queue daemon approval-wall secret (`ce-kv/forge/approval-capability/wall#signing_secret`)
- Materializer PEM reference (`ce-kv/forge/materializer#private_key`, TODO migrated)
- BAO token in daemon container via tmpfs
- Admin recovery: controller has passphrase custody (decision 9, OpenBao passphrase)
- SSHSIG signing deputy design: `docs/design/sshsig-signing-deputy.md` (target: OpenBao transit `ce-transit/governance/signing/ce-root-v1`)

#### Herdr PTY Dispatch

`herdr` socket at `/run/creator-engine/herdr/herdr.sock`. Used to dispatch to
contained seats: `HERDR_SOCKET_PATH=... herdr agent send w1:p1 "<ptr>"` + `herdr pane send-keys`.
Read back: `herdr pane read w1:p1`.

#### Egress Brokers

`tools/egress-broker/`: mediates outbound network access from contained seats.
Dev-3 uses this path for git push. Dev-4 uses App-mint credential helper.

---

## 3. Master Diagram

See the companion HTML file `index.html` for the full interactive SVG diagram.
Below is the text-form representation of the complete flow:

```
NATURAL LANGUAGE IDEA
         |
         v
┌─────────────────────────────────────────────────────────────────┐
│  OPERATOR (human)                                               │
│  • Describes objective in natural language                      │
│  • Ratifies arc (DECISIONS_20260708.md)                        │
│  • Arms authorities (materializer, daemons, signing)            │
│  • Holds ce-root-v1 key + OpenBao passphrase                   │
│  • Handles escalations (AWAITING-OPERATOR queue)               │
└──────────────────────┬──────────────────────────────────────────┘
                       |  conversation / ratification
                       v
┌─────────────────────────────────────────────────────────────────┐
│  CONTROLLER (CE-DEV-2, persistent, non-contained today)        │
│  Frame: classify, check territory, propose arc                  │
│  Shape: produce arc + tickets + carriers + changelog fragments  │
│  Dispatch: brief→file→pointer+SHA → seat                       │
│  Watch: herdr pane read, CI, stop-lines                        │
│  Harvest: exec-cat bundle extraction                           │
│  Review: spawn reviewer subagent, collect evidence              │
│  Gate: submit approval → merge trigger                          │
│  Checkpoint: write resume state to .ce/state/research/          │
└──────────────────────┬──────────────────────────────────────────┘
                       |  dispatch brief pointer
              ┌────────┴───────────────────────────┐
              v                                     v
┌─────────────────────────┐         ┌───────────────────────────┐
│  SEAT dev-1 (VPS)       │  ...    │  SEAT dev-4 (DGX runsc)  │
│  non-contained          │         │  gVisor contained          │
│  self-push via ssh      │         │  App-mint credential       │
│  Rings 0/1/2 green      │         │  strongest seat            │
└───────────┬─────────────┘         └───────────┬───────────────┘
            |                                    |
            | ce validate-pr (seat-ready #896)  |
            | git push + PR open                |
            └────────────┬───────────────────────┘
                         |
                         v
┌─────────────────────────────────────────────────────────────────┐
│  FORGE (GitHub)                                                 │
│  PR opened → webhook event                                      │
│  Required check: validate (CI)                                  │
│  Merge queue: ce-reference-protection-floor ruleset             │
└─────────────────────────────────────────────────────────────────┘
                         |
         ┌───────────────┼────────────────────────┐
         v               v                        v
┌──────────────┐  ┌──────────────┐   ┌───────────────────────────┐
│  CI VALIDATE │  │  REVIEWER    │   │  QUEUE DAEMON             │
│  (GitHub     │  │  (local,     │   │  (containerized singleton) │
│  Actions)    │  │  subagent    │   │  ce-queue-daemon.service   │
│  evidence    │  │  today;      │   │  approval + CI green →    │
│  only, no    │  │  review      │   │  merge queue enqueue       │
│  ratify      │  │  daemon TGT) │   │  → squash merge            │
└──────┬───────┘  └──────┬───────┘   └──────────┬────────────────┘
       |                 | approval               | post-merge
       └─────────────────┴───────────────────────┘
                                                  |
                                                  v
┌─────────────────────────────────────────────────────────────────┐
│  OPTION A MATERIALIZER (gate daemon, TODAY: dry-run only)       │
│  Reads .ce/brain/append-intents/<slug>.yaml                     │
│  Appends to .ce/brain/assertions.yaml hash-chain ledger         │
│  Removes consumed intent, commits directly to main             │
│  Authority: ce-materializer App 4244593 (arming gated)         │
└─────────────────────────────────────────────────────────────────┘
                         |
                         v
              MERGED + MATERIALIZED CODE
              Release staging → ce-root-v1 sign → publish
```

---

## 4. Answers to the Operator's Three Questions

### Question 1: How does CE guarantee governed framing without an explicit `/ce frame` invocation?

**Full answer**:

CE does not rely on users typing `/ce frame` or any CE verb prefix. Governance attaches
at the HARNESS SEAM, not at a command parser.

The mechanism is: `ce launch --harness codex` (or `claude`) is the canonical entry point
for every seat. The `ce launch` command (wired in `validators/creator_engine_validator/
claude_launch_spec.py` and `codex_launch_spec.py`) constructs a governed command that:

1. Scrubs ambient credentials (Ring 0)
2. Registers PreToolUse hooks BEFORE the harness starts (Ring 1, `.claude/settings.json`)
3. Registers Stop hooks for closeout evidence (Ring 2, Claude Code)

The PreToolUse hook (`ce-pretooluse.sh` → `hook_check.py`) runs on EVERY tool call,
validating against the active work claim, path manifest, reviewer-authority envelope,
and role-shaped tool set. A seat that receives a brief and starts working cannot bypass
this — the hook fires at the tool boundary, not at conversation start.

For the persistent controller (CE-DEV-2), `ce takeover` is the succession entry verb.
It ingests the resume state, hydrates governance context (decisions, active claims,
in-flight PRs), and makes the controller's first subsequent action a governed Frame step
with full context.

For end-users on governed controllers (endgame), the same pattern applies: `ce launch`
or `ce takeover` wires the harness. Intent recognition (what the user wants to do) can
be soft and conversational. Enforcement of what the controller is allowed to do remains
hard and harness-enforced.

**The doctrine anchor**: "Grader-outside-the-agent" from `docs/architecture/stage-vocabulary.md`.
The harness boundary is the grader. The model's self-assessment of what it should do is
advisory input; the harness's check is the enforcement surface.

**References**: `docs/operations/GOVERNED_LANE_LAUNCH_PROTOCOL.md`, `docs/operations/
HARNESS_SUPPORT_CAPABILITY_MATRIX.md`, `.claude/hooks/ce-pretooluse.sh`,
`validators/creator_engine_validator/hook_check.py`.

---

### Question 2 (c4): Is reviewer assignment local or forge level?

**Answer: Hybrid — forge events trigger, local daemon decides and spawns.**

**Forge side (event transport, SSOT)**:
GitHub is the rented coordination plane (`docs/operations/GITHUB_NATIVE_COORDINATION_PROTOCOL.md`).
PR-opened and PR-synchronized webhooks are the canonical trigger events. The forge also
holds the authoritative PR state (head SHA, author identity, required check results,
CODEOWNERS), which serves as the SSOT for the assignment decision.

**Local side (decision + spawn)**:
The assignment DECISION and reviewer spawn happen in a local containerized CE daemon
(the "review daemon", TARGET state). This daemon:
- Reads forge event via webhook or belt-feed polling (Search-API polling = durable
  default; push webhook = premium, per `ce-belt-feed-polling-default-push-premium`)
- Applies the authoring/review matrix: author ≠ reviewer (mandatory; from
  `docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md`)
- Selects from `CE_GATE_AUTHORIZED_REVIEWERS` in the queue daemon env
- Mints a reviewer-authority envelope (single-use, short TTL, `capability:
  independent_review_venue`, `ce lane launch --mint-reviewer-authority`)
- Spawns a local reviewer lane on CE-DEV-2 or CE-DEV-1

**Why local, not forge**: Reviewer spawn requires access to CE's internal seat registry,
OpenBao-held authority, and the reviewer-authority minting capability. These must not
live in GitHub Actions (a forge-hosted runner cannot hold approval-wall secrets or
reviewer-authority signing capability). The decision is also non-delegable: author ≠
reviewer enforcement is a CE hard invariant, not a forge ruleset.

**TODAY**: Controller manually applies this matrix and spawns reviewer subagents. The
pattern is the same; the daemon automates the triggering.

**References**: `playbooks/reviewer/`, `docs/delivery/REVIEW_GATE.md`, `docs/operations/
GOVERNED_LANE_LAUNCH_PROTOCOL.md` §0b, `deploy/queue-daemon/RELOCATION.md`.

---

### Question 3 (c5): Is seat-filed ticket triage local or forge level?

**Answer: Same hybrid — forge is the SSOT for ticket state, triage decision is local.**

Seats file bug reports and feature requests as GitHub issues in ce-ops. The forge
(GitHub) is the canonical source of truth for issue state, labels, timestamps, and
assignees.

**Forge side (SSOT + belt)**: Issues land on GitHub. CE's belt-feed
(`ce triage queue scan` implemented in ce-conveyor; per changelog v0.3.2 `ce-l3-triage-ready-queue-p0`)
polls the GitHub Search API on a schedule (30-min default in CI dry-run mode). Push
webhooks are a premium path requiring explicit webhook subscription and forwarding
infrastructure. The polling belt is the durable default.

**Local side (classification + queuing)**:
The triage daemon (TARGET state):
- Ingests the polled feed from the belt
- Applies CE work-class inference (`_infer_work_class`, `_infer_mutation_class`,
  `readiness_blockers` in `forge_triage.py`)
- Deduplicates against the active arc and in-flight work claims
- Queues into the intake arc for controller consideration
- Labels issues with advisory classification labels (no auto-ratification)

The triage result is advisory only: it does not ratify, approve, merge, or dispatch.
Operator/controller ratifies queued items into the next arc.

**Why local**: Same reason as reviewer assignment — triage against the arc state, work
claims, and path-territory awareness requires local CE context not available on
GitHub-hosted runners. The forge is the communication channel; brains are local.

**References**: `deploy/queue-daemon/launch-queue-daemon.sh`, triage implementation
in changelog v0.3.2 `ce-l3-triage-ready-queue-p0`, `ce-belt-feed-polling-default-push-premium`
memory, `docs/design/ce-forge-side-automation.md` import item 1 (trigger taxonomy).

---

## 5. Autonomy Ladder

Each rung states: what the controller stops doing, what evidence gates the rung,
and the rollback story.

### Rung 0 — TODAY (2026-07-08)

**State**: Controller hand-dispatches; manual harvest; manual review spawn; manual approval.

**Controller does**: Everything except code implementation (no inline implementation
per foreman directive).

**Evidence**: Rings 0/1/2 green for claude_code (matrix), Codex Ring 0 green.
#896 seat-ready merged. C5 promotion executed.

**Rollback**: Inherent — controller manually overrides any step.

---

### Rung 1 — Seat Parity (~Jul 10-11)

**Gate evidence**: dev-3 rebuild complete with ssh-keygen (amd64 image); dev-3 self-push
canary re-proven; dev-4 Ring 1 smoke packet accepted (ticket 480).

**Controller stops doing**: Manual bundle-over-exec-cat harvest for dev-3. Dev-3 can
self-push cleanly.

**Harness matrix after**: Codex Ring 1 `launch-wired` yellow → green; `live-proven` red
→ green pending evidence packet.

**Rollback**: Stop the new dev-3 container; revert to old image.

---

### Rung 2 — IaC Singleton Redeploy Armed (~this week)

**Gate evidence**: #895 merged; IaC script tested end-to-end.

**Controller stops doing**: Manual queue-daemon restart on host outage.

**New capability**: One-click redeploy of ce-queue-daemon via IaC script.

**Rollback**: `sudo systemctl disable --now ce-queue-daemon.service; bash ~/ce-wall-daemon-launch.sh`

---

### Rung 3 — Daemon Wave (~1 week)

**Target daemons**: review daemon, triage daemon, broker v1 full deployment.

**Gate evidence**: Broker slice 2 arming (3 MAJORs from ce-ops#504 resolved); IaC
redeploy precondition (rung 2) met; each daemon passes green harness matrix rows.

**Controller stops doing**: Manually spawning reviewer lanes; manually polling triage.

**Rollback**: `sudo docker stop <daemon>; systemctl disable <daemon>.service`

---

### Rung 4 — Conveyor Pickup (after daemon wave)

**What changes**: Seats actively poll the pickup queue for ready tickets rather than
waiting for controller dispatch. Work claim is self-acquired.

**Gate evidence**: Pickup protocol implemented and validated; territory-map deduplication
proven against live claims; seat-ready profile green.

**Controller stops doing**: Authoring individual dispatch briefs. Controller moves to
arc-level direction only.

**Rollback**: Controller reassumes manual dispatch; no persistent state is lost because
work claims are forge-visible.

---

### Rung 5 — Materializer Armed (after #895 merge + Option A slice 2+)

**Gate evidence**: Operator arming call (non-delegable); ce-materializer App 4244593
PEM migrated to OpenBao; slice 1 dry-run evidence clean; Operator ratification
recorded in DECISIONS.md.

**Controller stops doing**: Manual brain ledger entries. Intent PRs self-materialize
post-merge.

**Rollback**: Set `ARMING_ENABLED=False`; materializer reverts to dry-run advisory mode.
Direct ledger edits still work via the #882 stale-tail gate path.

---

### Rung 6 — Contained Controllers T1 (Aug 11, #496 parity acceptance test)

**What changes**: CE-DEV-2 controller runs inside a gVisor container. The persistent
controller is itself contained and IaC-redeployable. The harness matrix row
`contained_controller_scaffold C1` goes green.

**Gate evidence**: #496 deploy lane + #488 hydration + #497 tooling absorption complete;
one governed worker unit end-to-end per harness (T1 bar); NanoClaw T0 matrix rows
(2026-07-21); ce-ops#498 milestones.

**Controller stops doing**: Relying on uncontained host access. Host-ops broker mediates
all host operations.

**Rollback**: Revert to non-contained controller launch; broker continues operating.

---

### Rung 7 — Ephemeral Controllers / NanoClaw (T2 Aug 31, #498 T2)

**What changes**: Forge events spawn NanoClaw ephemeral controllers from content-addressed
mandate pointers. Self-retiring after one bounded unit of work. Provider profile:
`self_hosted_webhook_v1` (design: `docs/design/ephemeral-controller-provider-seam.md`).

**Gate evidence**: T2 bar: first-class controller via #496 parity acceptance test;
NanoClaw ephemeral loop proof; mandate-pointer resolver operational; evidence packet
shape (`ce.ephemeral_controller.evidence.v1`) schema registered.

**Controller stops doing**: Session-level dispatch. The persistent controller becomes
primarily an arc-ratifier and escalation handler.

**What never becomes ephemeral**: Gate singleton custody, approval-wall signing,
ce-root-v1 signing, seat-relaunch (`ce launch`) authority. These stay with the
persistent controller (CE-DEV-2 or its IaC-reprovisioned successor).

**Rollback**: Disable webhook listener; revert to persistent-controller dispatch;
ephemeral evidence packets are forge-visible and reconstructable.

---

## 6. Authority and Safety Model

### What the Operator Always Holds

These actions are categorically non-autonomous and require Operator input:

| Action | Why non-delegable |
|---|---|
| Arc ratification | Sets the delivery direction; wrong arc = wrong product |
| Arming new daemon authorities | Each arming is a new attack surface |
| ce-root-v1 signing (releases) | Non-delegable per `ce-worker-must-not-sign-ce-root-v1`; scope: persistent controller only since decision 9 |
| OpenBao root/unseal/import | Credential plane; controller has passphrase custody (decision 9) but root ops stay explicit |
| External communications (Arad send, NVIDIA pitch) | Reputation + relationship risk |
| Cell flips (containment promotion) | Each flip = new attack surface; gate stays singleton |
| Reviewer-identity ratification | Author ≠ reviewer is the moat |
| Merge-gate singleton changes | Policy singleton; any second gate-authority holder splits policy |
| Operator-facing framing ratification | The controller proposes; Operator ratifies |

**Note on decision 9**: The persistent controller (CE-DEV-2) has been granted standing
ce-root-v1 signing authority for release/spec artifacts. Workers, seats, standby
controllers, and ephemeral controllers NEVER hold this authority. Takeover controllers
have non-delegable signing per #883 runbook.

### Stop-Lines

| Condition | Behavior |
|---|---|
| Reviewer-authority envelope missing | `ce lane launch` refuses with `G3-REVIEWER-AUTHORITY-INVALID`; no review proceeds |
| merge-gate singleton lease already held | Queue daemon refuses to start a second instance; stale lease requires manual operator removal |
| Broker-wide kill switch | All broker verbs return `disabled`; no host mutation |
| Option A materializer HELD | Hard gate failure after 30-min closeout window; no silent drop |
| Recursion bottom-out | 3 same-structure failures → `AWAITING-OPERATOR` circuit breaker (`docs/design/recursion-bottom-out-policy.md`) |
| Ephemeral controller requests gate/sign | Refused locally + evidence emitted; delegated to singleton path |

### Fail-Closed Patterns

- **Broker**: missing label / unknown unit / symlink escape / path traversal = refused
- **Queue daemon**: cannot write pre-mutation audit → returns `failed`, no mutation
- **Materializer**: unprovable live ledger tail → `HELD`, no write
- **Gate daemon**: cannot verify approval wall secret → refuses to process
- **PreToolUse hook**: validation error → tool call blocked before execution

### Kill Switches

- **Automerge kill switch**: `ce automerge-kill-switch off` (stores to live policy state;
  merged v0.3.2 `ce-automerge-kill-switch-cli`)
- **Host-ops broker**: broker-wide kill switch file in root-owned host config dir outside
  all containers; per-verb disable flags
- **Materializer**: `ARMING_ENABLED=False` hard invariant in env (TODAY state)
- **Ephemeral controller listener**: IaC-managed; disable by stopping webhook listener service

### Quarantine Paths

- Materializer: `.ce/state/brain-intent-quarantine/<materialization-key>.json`
- Materializer HELD: `.ce/state/brain-intent-materializer/held/<key>.json`
- Host-ops broker: failed partial mutation → `degraded` result + operator triage
- Recursion bottom-out: `AWAITING-OPERATOR` state persisted in daemon state root

### Audit Trails

- Every broker verb call: `ce.host_ops.audit.v1` JSON record (no secrets, no raw logs)
- Queue daemon: journald + daemon log
- Materializer: append-only JSON lines + PR closeout comment + commit trailer
- Ephemeral controller: `ce.ephemeral_controller.evidence.v1` takeover-compatible packet
- Reviewer lane: reviewer-authority envelope consumed + stamped with `consumed_at`

---

## 7. Glossary

| Term | Definition |
|---|---|
| **Arc** | Short-term ordered delivery plan (lanes A-1..A-N) ratified by the Operator |
| **Lane** | One work stream in an arc (e.g. A-1 = Arad apply, A-3 = broker v1 slice 1) |
| **Ticket** | GitHub issue in ce-ops with work-class label; maps to one or more bounded PRs |
| **Carrier** | PR artifact: path-manifest carrier (generated from diff) + changelog carrier per governed PR |
| **Work class** | XS/S/M/L sizing; declared in PR body as `- **Declared work class:** tiny|story|feature|epic` |
| **Harvest** | Controller extraction of completed seat output: exec-cat bundle (contained) or git push (non-contained) |
| **Seat** | A governed worker running a coding agent (Codex or Claude Code) in a managed environment |
| **Foreman** | Controller operating as a delivery orchestrator; delegates implementation, never inlines |
| **Gate** | The merge gate: ce-queue-daemon singleton that enforces review + CI + merge queue before merge |
| **Brain** | The append-only content-addressed assertion ledger (`.ce/brain/assertions.yaml`) |
| **Intent** | A data-only append intent file (`.ce/brain/append-intents/<slug>.yaml`) carried by a PR for merge-time materialization |
| **Materializer** | The Option A post-merge actor: gate daemon armed with direct-commit authority over brain ledger only |
| **Broker** | The host-ops broker: systemd-supervised host service exposing typed repair verbs to contained agents |
| **Containment ring** | gVisor runsc isolation (DGX/VPS); no raw runtime sockets inside containers |
| **Arc** | Also: `ce-arc://` — the content-addressed arc manifest fed to ephemeral controller mandates |
| **Mandate** | Content-addressed (`ce-mandate://sha256/<hex>`) work instruction for an ephemeral controller |
| **NanoClaw** | Reference implementation of ephemeral controller: event-spawn → mandate → post → self-retire |
| **Egress broker** | Network egress mediator for contained seats (`tools/egress-broker/`) |
| **AWAITING-OPERATOR** | Queue discipline: pending Operator input is forge-visible; surfaced first after /clear |
| **Approval wall** | The OpenBao-backed signing check that the queue daemon uses to verify reviewer approvals |
| **SSHSIG** | The OpenSSH signature format used by `docs/install.sh` to verify release canonical bytes |
| **ce-root-v1** | The persistent controller's ed25519 signing key; key at `~/.ce-keys/ce-root-v1` |
| **Pickup conveyor** | TARGET: automated arc-ticket queue from which seats self-select work |
| **Belt-feed** | CE's polling-based forge event ingestion (Search-API polling = durable default) |
| **Two-plane OS** | CE architecture: portable control plane + ONE container runtime per host |
| **Harness seam** | The hook/PreToolUse enforcement boundary where governance attaches regardless of invocation |

---

## 8. Reference Appendix

### Design Documents (main worktree: `.ce/wt-dayarc2-main/`)

| Document | Path |
|---|---|
| Host-ops broker v1 | `docs/design/host-ops-broker-v1.md` |
| Option A merge-time materializer | `docs/design/ce-491-optiona-merge-intent.md` |
| Option A ledger serialization slice 1 | `docs/design/ce-491-ledger-append-serialization-slice1.md` |
| Ephemeral controller provider seam | `docs/design/ephemeral-controller-provider-seam.md` |
| Orchestrator agent | `docs/design/ce-orchestrator-agent.md` |
| CE forge-side automation | `docs/design/ce-forge-side-automation.md` |
| CE forge-side automation epic | `docs/design/ce-forge-side-automation-epic.md` |
| Brain memory augmentation | `docs/design/ce-brain-memory-augmentation.md` |
| SSHSIG signing deputy | `docs/design/sshsig-signing-deputy.md` |
| Controller bootstrap injection | `docs/design/controller-bootstrap-injection.md` |
| Controller bootstrap SSOT | `docs/design/controller-bootstrap-ssot.json` |
| Recursion bottom-out policy | `docs/design/recursion-bottom-out-policy.md` |
| Seat-side preflight | `docs/design/seat-side-preflight.md` |

### Operations Documents

| Document | Path |
|---|---|
| Governed lane launch protocol | `docs/operations/GOVERNED_LANE_LAUNCH_PROTOCOL.md` |
| Worker container protocol | `docs/operations/WORKER_CONTAINER_PROTOCOL.md` |
| Harness support capability matrix | `docs/operations/HARNESS_SUPPORT_CAPABILITY_MATRIX.md` |
| Queue daemon relocation runbook | `deploy/queue-daemon/RELOCATION.md` |
| Forge housekeeping runbook | `docs/operations/FORGE_HOUSEKEEPING_RUNBOOK.md` |
| GitHub native coordination protocol | `docs/operations/GITHUB_NATIVE_COORDINATION_PROTOCOL.md` |
| Contained controller parity acceptance | `docs/operations/CONTAINED_CONTROLLER_PARITY_ACCEPTANCE.md` |

### Playbooks

| Document | Path |
|---|---|
| Controller duties | `playbooks/controller/duties.yaml` |
| Controller workflow | `playbooks/controller/workflow.ce.yml` |
| Reviewer playbooks | `playbooks/reviewer/` |
| Conveyor daemon stuck lease | `playbooks/controller/runbooks/conveyor-daemon-stuck-lease.md` |
| Dispatch brief | `playbooks/controller/briefs/dispatch.md` |

### Deploy / Infrastructure

| Artifact | Path |
|---|---|
| Queue daemon service + launcher | `deploy/queue-daemon/` |
| DGX runsc seat image | `deploy/dgx-runsc/` |
| VPS runsc seat image | `deploy/vps-runsc/` |
| DGX controller runsc | `deploy/dgx-controller-runsc/` |
| Egress broker | `tools/egress-broker/` |
| Host-ops broker (slice 1) | `tools/host-ops-broker/` |
| Systemd gate daemons install | `deploy/systemd/install-gate-daemons-systemd.sh` |

### Decision Records

| File | Contents |
|---|---|
| `.ce/state/decisions/DECISIONS_20260708.md` | 11 decisions: singleton+IaC, Option A, C5, Ring-1, Arad, 0.3.4, signing grant, VPS sudo |
| `.ce/state/decisions/DECISIONS_20260707.md` | 7 decisions: night arc, account switch, C5 cutover execution, NanoClaw T0/T1/T2 |
| `.ce/state/decisions/DECISIONS_20260706.md` | Prior day decisions |

### State Files

| File | Purpose |
|---|---|
| `.ce/state/research/RESUME_STATE_CE_DEV2_DAYARC2C_20260708.md` | Current controller posture |
| `.ce/state/research/FOLLOWUPS_DAYARC2_20260708.md` | Follow-ups ledger |
| `.ce/brain/assertions.yaml` | Append-only hash-chain brain ledger |
| `ce-ops:infra/identity-registry.yaml` | SSOT for all seat/App identities |
