# Feature 005 — Slice 2I: Worker Isolation Runtime (Spec Amendment)

**Spec parent**: [`spec.md`](./spec.md)
**Slice id**: `Slice 2I` (Worker Isolation Runtime)
**Status**: Draft (spec authoring only; no runtime implementation)
**Created**: 2026-05-21
**Source-of-truth relationship**: This document is an **additive
amendment** to the Feature 005 PCO spec. It does NOT modify any prior
PCO functional requirement (`PCO-001` through `PCO-032`), and it does
NOT subsume Slice 2.5 (Controller Identity Substrate) or Slice 2R
(Worktree Allocator Runtime). It introduces Slice 2I, a sibling /
bridge slice positioned between the Slice 2.5 + 2R authoring gate and
the Slice 2.5 + 2R *implementation* gate, and it makes the worker
container substrate a load-bearing precondition for Slices 3, 4, 5,
6, and team-mode workstreams (Features 007 / 008 / 009).

**Input** (rationale and threat analysis): visible-architect report
`/home/nefarious/projects/creator-engine/.hermes/research/pco-containerization-roadmap-20260521T054959Z/ARCHITECT_REPORT.md`
(SHA256 `2b85e2e5198881c6a4a1dc7d99e2cf4009677a937e0f07aa4027e1b1a1fb18be`).

**Authoring boundary**: Spec/design documentation only. This amendment
authors no schema, validator, test, example, image, package metadata,
runtime code, Hermes runtime/config/profile/hook surface, MCP/model
provider config, secret, token, credential, runtime record, or
container image. No Docker / Podman / firejail / nsjail / bubblewrap
command is run by this gate. No `pco-allocate` or `pco-release`
implementation is produced by this gate.

---

## a. Why Slice 2I exists

Source identified that the current local execution model — Controller
/ Hermes and Architect / Implementer Claude Code / Codex panes running
in tmux with direct host OS / filesystem / network / credential access
— is unsafe as a long-term Creator Engine posture and risks expensive
retrofit debt if ignored during design. The visible-architect report
(§§1–3) confirmed the concern and recommended a sibling **Slice 2I —
Worker Isolation Runtime** authored before Slice 2.5 + 2R
implementation proceeds.

Slice 2.5 + 2R as authored is forward-compatible with worker
containerization: it constrains record shape and atomic-write order
without baking "runs on the host" into any predicate. Slice 2I
therefore lands as an additive substrate (`PCO-040` through
`PCO-045`), not as an amendment to `PCO-024` through `PCO-032`.

Slice 2I follows the same **substrate-before-automation** discipline
as every other PCO slice. This amendment authors only the substrate
(record shapes, refusal predicates, kernel/syscall verb set, safety
defaults). It does NOT author the corresponding runtime
implementation (image, engine wiring, broker, allocator extension).
Runtime implementation is the separately ratified **Slice 2I-R** gate
that this amendment names but does not authorize.

## b. Slice 2I scope and boundary

**Slice 2I-S (this amendment) introduces**:

* the *contract* for a tracked worker-container policy record;
* the *contract* for a tracked container-instance record;
* the *contract* for a tracked mount manifest, secret-grant manifest
  (without secret values), network policy record, and artifact
  collection manifest;
* the *contract* for tracked termination / garbage-collection event
  records;
* the kernel / syscall verb set the runtime engine MUST expose
  (`allocate_worker`, `mount_workspace`, `grant_path_capability`,
  `inject_secret`, `set_network_policy`, `run_command`,
  `collect_artifacts`, `terminate_worker`, `garbage_collect_worker`);
* substrate-level **refusal predicates** `PCO-040` through `PCO-045`,
  each substrate-only (no runtime mutation) and each carrying a
  backward-compatibility floor so trees without Slice 2I substrate
  preserve Slice 2A / 2.5 / 2R behavior unchanged;
* the safety defaults the runtime engine MUST honor (read-only
  mounts by default; explicit per-path write grants; no host home
  mount; no host credential mount by default; no container engine
  socket inside a worker container; role-specific egress;
  redaction/revocation for secrets);
* the Open Source Decisions (OSDs) that block Slice 2I-R
  implementation.

**Slice 2I-S explicitly does NOT introduce**:

* any container image build, pull, push, or inspection;
* any Docker / Podman / firejail / nsjail / bubblewrap invocation;
* any runtime engine selection (Podman vs. rootless Docker is OSD-I-1
  per §i);
* any credential broker implementation;
* any egress enforcement primitive implementation (Pasta vs.
  Slirp4netns vs. iptables is OSD-I-5 per §i);
* any extension of `pco-allocate` / `pco-release` runtime code (the
  *contract* extension is named here as a Slice 2I-R deliverable; the
  runtime change is not in this gate);
* any Hermes runtime / profile / hook / config / MCP / model provider
  mutation;
* any controller containerization (Controller stays on host through
  at least Slice 6; OSD-I-3 per §i);
* any amendment to `PCO-024` through `PCO-032`;
* any expansion of Phase 1 / Phase 2 autonomy (per Feature 002
  FR-027/FR-028; PCO-032 remains in force).

**Slice 2I-R (deferred, separately ratified)** will: ship a worker
container engine wiring; extend `PCO-027`'s atomic transaction with a
container-start step between steps 5 and 6 and a container-stop step
ahead of `pco-release` step 4; implement the credential broker;
implement the egress enforcement primitive; and emit the
`container_started` / `container_stopped` / `container_force_reaped`
events as runtime side effects of the syscalls defined in §e.

## c. Threat model for the current tmux-hosted host-access panes

Slice 2I-S is authored against the threat surface the *current*
execution model exposes. The threats below are not hypothetical; each
is reachable today from a malicious or merely careless prompt because
every Architect / Implementer / Verifier pane runs as the same
unprivileged host user with the host filesystem, host network, host
SSH/GitHub credentials, host package managers, and host model-provider
keys directly addressable.

### c.1 Accidental filesystem damage

* An Architect or Implementer pane can `rm -rf` anywhere the host
  user has write access — outside the worktree, into the root
  checkout, into `.hermes/`, into `~/.ssh/`, into other repositories
  on the same disk. `git worktree add` followed by an errant
  `git clean -fdx ..` from the wrong cwd is sufficient.
* A long-running Implementer can hold a file open or leak a process
  group that survives pane death, blocking subsequent
  `git worktree remove` and leaving stale state Slice 2R's rollback
  path cannot reconcile.
* The `ROOT_WORKTREE_INVARIANT` is prose; the OS does not enforce it.
  `PCO-031` will refuse `pco-allocate` from root, but a freeform
  shell command from a pane that simply ignores the allocator can
  still mutate root checkout state.

Slice 2I-S addresses these via *substrate*: the mount manifest
contract (§e, §f) defaults every worker to a tight, role-shaped
filesystem namespace with no host paths outside the allocated
worktree and the read-only governance tree; runtime enforcement is
Slice 2I-R's job.

### c.2 Prompt-injection / tool misuse

* A model that ingests attacker-controlled content (PR body, issue
  comment, downloaded README, MCP server response, fetched web page)
  can be coerced to run arbitrary shell commands. With host-level
  shell access this is a full host compromise.
* Tools whose schemas allow arbitrary `bash -c` (the Bash tool;
  certain MCP servers) become unconstrained command channels. The
  PCO validator is post-hoc; it cannot refuse a `curl … | bash`.
* Architect / research workers are the highest-risk vector because
  they routinely read attacker-controlled web content. Slice 2A's
  refusal predicates do not address content-level threats.

Slice 2I-S addresses these via *role-shaped policies* (§d): the
architect/research role gets a read-only repo mount and broad egress;
the implementer role gets read-write only on its allocated worktree
and a narrow egress allowlist; the verification role gets no model
provider access and (default) no egress at all.

### c.3 Dependency / script compromise

* `pip install`, `npm install`, `cargo build`, `make`, `pre-commit`,
  `pytest` invoked from a pane run third-party code as the host user.
  A typosquatted or upstream-compromised dependency obtains the same
  host privileges the user does.
* Build scripts have read access to `~/.ssh/`, `~/.gnupg/`,
  `~/.aws/credentials`, the host browser cookie jar, the GitHub CLI
  token (`~/.config/gh/hosts.yml`), tokens in shell rc files, and
  any kept-warm `ssh-agent` / `gpg-agent` sockets.
* The repo's own `bin/` / `scripts/` (and the future `pco-allocate`)
  are themselves attack surface if an Architect / Implementer
  modifies them mid-session.

Slice 2I-S addresses these via *withhold-by-default credential
policy* (§f.3) and *egress allowlist contract* (§f.4): host
credential surfaces are not exposed to the container; egress is
constrained to a per-role allowlist that does NOT include attacker-
controlled hosts.

### c.4 Credential / secret exposure

* Anthropic / OpenAI / model-provider keys, GitHub PATs, deploy
  tokens, signed-commit GPG keys, SSH keys, browser cookies,
  Claude Code config (`~/.claude/`), Codex config — all are readable
  by every pane today. There is no least-privilege-per-role
  enforcement.
* The forthcoming Slice 2.5 controller-key private key would inherit
  this same exposure surface unless a custody mode that binds the key
  to an isolated execution boundary is ratified (OSD-1).

Slice 2I-S addresses these via the **secret-grant manifest** contract
(§e.4) and the explicit rule (§f.3) that the Slice 2.5 controller-key
private key MUST NOT be injected into any worker container; only the
Controller signs leases. This is the strongest available enforcement
of "controller identity is bound outside the worker."

### c.5 Cross-lane contamination

* Two panes editing two different worktrees nevertheless share: the
  same host `git config` (`user.email`, `signingkey`, hooks path,
  global filters), the same global Git hooks (`core.hooksPath`), the
  same `pre-commit` cache, the same shell environment, the same
  `/tmp`, the same package manager caches, and the same in-memory
  daemon state (`tsc --watch`, language servers, file watchers).
* The Active-Work Ledger and Worktree Lease records assume
  controllers are honest about their `controller_id`. On a single
  host this is enforced by directory convention today, not by the
  OS; a pane running under any of the existing roles can write a
  record under another `controller_id` because nothing in the
  filesystem layer cares.

Slice 2I-S addresses these via *per-worker filesystem namespace and
per-worker network namespace* (§d, §e): each worker sees only its
mount manifest and its egress allowlist; cross-worker observation
through shared `/tmp`, shared package caches, or shared daemons is
not possible without an explicit grant.

### c.6 Cleanup / zombie process risk

* Pane crashes leave: heartbeats still ticking from supervisor
  processes; file handles held against worktrees; advisory locks
  (`flock(LOCK_EX)`) held against `.hermes/active-work-ledger/locks/`
  that survive the pane and block `pco-allocate` permanently;
  half-allocated worktrees that the Slice 2R rollback path cannot
  remove because the OS still treats them as in-use; stale
  Claude Code / Codex agent processes that may continue calling
  tools.
* The current model has no process-group reaper. Slice 2R's
  `PCO-027` step 6 rollback operates on filesystem state, not
  process tree state.

Slice 2I-S addresses these via the `terminate_worker` and
`garbage_collect_worker` syscall contract (§e.8, §e.9) and the
`PCO-043` *container outlives claim* refusal predicate (§g): a
container's lifetime is bound to its claim; the runtime engine MUST
reap the process tree on `terminate_worker`; the periodic sweeper
MUST garbage-collect any container instance whose claim has been
released, and MUST emit a `container_force_reaped` event.

## d. Target isolation model

Slice 2I-S ratifies a **layered, role-shaped** isolation model.
Isolation primitive selection is *not* one-size-fits-all: the
Controller has different requirements from ephemeral workers; the
architect/research worker has different requirements from the
implementer worker; the verifier worker has different requirements
from both.

### d.1 Worker containers below visible panes

The visible pane substrate (tmux) is preserved. A worker container
sits **below** a visible pane: the operator continues to see and
interact with a tmux pane; the model process, the tool processes,
and the per-task filesystem / network namespace live inside a
container that the pane attaches to. Slice 3 (Pane Registry) records
the binding from pane to container instance; Slice 2I-S authors the
container side of that binding.

### d.2 Role-shaped worker policies

Slice 2I-S ratifies three worker roles, each with a *distinct* default
policy. The role is a first-class field of the worker-container
policy record (§e.1). Conflating roles would produce either over-
broad implementer credentials (security regression) or under-capable
architect/research (capability regression).

| Role | Mount default | Egress default | Credential default |
|---|---|---|---|
| `architect_research` | read-only on allocated worktree; tmpfs scratch; read-only `governance/` | model-provider hosts + ratified documentation/web domain allowlist + source-host read API | model-provider key by name; no write tokens; no SSH key; no controller-key |
| `implementer` | read-write on exactly one allocated worktree; tmpfs scratch; read-only `governance/` | model-provider hosts + ratified dependency-registry allowlist + source-host write API for the *one* branch granted by a per-task fine-grained PAT | model-provider key by name; per-task scoped PAT (claim-lifetime TTL); no SSH key; no controller-key |
| `verification` | read-only on allocated worktree; tmpfs scratch; read-only `governance/` + writable build-output tmpfs | none by default (offline-cached deps) OR ratified dependency-registry-only allowlist | none by default; the principle is "tests should not need the internet" |

The verification role's "no egress by default" posture removes the
dominant dependency-compromise channel. Architect/research's broad
egress is bounded by its read-only mount and absence of write tokens.
Implementer's write capability is bounded by its narrow egress and
per-task PAT.

The role enum is normative for Slice 2I-S. Additional roles (e.g.,
connector-only workers per Feature 008) MUST be ratified as additive
schema changes; this amendment fixes only the three above.

### d.3 Runtime engine selection is an OSD, not hardcoded

Rootless **Podman** and rootless **Docker** are both acceptable v1
runtime engines. Both run unmodified OCI images. Both support a
rootless / user-namespace mode that avoids a long-running root
daemon. Podman is rootless-first and is the architect report's
slightly stronger recommendation; rootless Docker is acceptable and
in some environments operationally simpler. The choice is recorded
as **OSD-I-1** (§i.1) and is a Source-ratified decision separate from
this amendment.

`firejail`, `bwrap`, `nsjail`, and Firecracker / Kata microVMs are
**not** Slice 2I-S v1 primitives:

* Bare `firejail` / `bwrap` / `nsjail` impose a custom-policy
  authoring burden Creator Engine cannot afford in v1; they are
  acceptable as in-container defense-in-depth wrappers around
  high-risk tools (e.g., `bwrap` around a fetch step inside the
  architect/research container) but not as the primary boundary.
* Full VMs / microVMs are appropriate for hosted team-mode operation
  (Feature 007 territory), overkill for the local prototype.
* MacOS-only `sandbox-exec` is insufficient for the Linux production
  target.

### d.4 Controller containerization is deferred

The Controller (Hermes) is **not** containerized in Slice 2I. The
Controller mutates Hermes profile / config / runtime hooks, panes,
and the tmux session itself; containerizing it forces those concerns
into the container contract before the Hermes contract is stable.
The Controller is the only legitimate process that spawns workers;
running it inside a container would either require Docker-socket
access from within the container (an unacceptable boundary
violation per §f.5) or a privileged shim outside the container that
weakens the boundary.

Controller containerization is recorded as **OSD-I-3** (§i.3) and is
explicitly deferred to a later gate (no earlier than after Slice 6).
Slice 2I-S authors *only* the worker-side substrate.

## e. Kernel / syscall model

Translating isolation into the Creator Engine OS metaphor: Creator
Engine is the deterministic syscall layer over probabilistic agents.
Slice 2I-S adds nine syscalls. Each MUST have a tracked substrate
record (defined in §e.10) and a typed runtime entry point (deferred
to Slice 2I-R). Each MUST cite the policy SHA the syscall was
executed under so policy-change audits can identify exactly which
instances ran under which policy.

### e.1 `allocate_worker`

**Verb**: start a container instance bound to a claim under a
ratified worker-container policy.

**Inputs**: `(policy_ref, claim_id, lease_id, image_sha)` where
`policy_ref` resolves to a tracked worker-container policy record and
`claim_id` / `lease_id` resolve to the active claim and lease the
caller already holds under `PCO-027`.

**Records emitted (substrate)**: one container-instance record (§e.10)
and one `container_started` event in the Active-Work Ledger.

**Refusal predicates that gate the call**:

* `PCO-022` (lease contention);
* `PCO-024` (forged controller identity);
* `PCO-040` (worker-container policy schema);
* `PCO-041` (container-instance schema);
* `PCO-044` (image SHA does not match policy);
* Slice 2I-R policy-required gate (introduced by the runtime gate,
  not by this amendment).

### e.2 `mount_workspace`

**Verb**: bind the allocated worktree (and only that worktree) into
the container's filesystem namespace at the mode declared by the
policy.

**Inputs**: `(claim_id, worktree_path, mode={ro,rw})`.

**Records emitted (substrate)**: the mount manifest field on the
container-instance record (§e.10).

**Refusal predicates**:

* `PCO-021` (no live lease ⇒ no mount);
* `PCO-030` (conflict validator gate);
* Slice 2I-R mount-scope check (the runtime engine MUST refuse to
  mount any path outside the allocated worktree, the tmpfs scratch,
  or the read-only governance tree, without an explicit
  `grant_path_capability`).

### e.3 `grant_path_capability`

**Verb**: extend a default-deny mount manifest with exactly one
additional path, recorded append-only and citing a justification.

**Inputs**: `(instance_id, path, mode, justification_ref)` where
`justification_ref` cites a ratified record (an envelope, an OSD
resolution, or a Source ratification message).

**Records emitted (substrate)**: an additive mount-grant record
(one record per path), appended to the container-instance record's
mount manifest.

**Refusal predicates**:

* refused if the policy does not declare grant-extensibility for this
  role;
* refused if the `path` escapes the worktree root (e.g., contains
  `..` after normalization, or resolves outside the worktree's
  realpath);
* refused if `justification_ref` does not resolve.

`grant_path_capability` is the *only* way the implementer's mount
manifest can be extended beyond its allocated worktree at runtime.
Bulk pre-grants in the policy are also legitimate; runtime
extension is the audited path.

### e.4 `inject_secret`

**Verb**: expose a named secret into the container by environment
variable or mounted file, drawing the secret from the host-side
credential broker.

**Inputs**: `(instance_id, secret_name)`.

**Records emitted (substrate)**: one secret-grant record naming
`secret_name`, `instance_id`, injection mode (env vs. file), and the
broker-issued grant id. **The secret value is NEVER recorded.** The
secret-grant manifest (§e.10) is the substrate boundary against the
secret value leaking into tracked records.

**Refusal predicates**:

* refused unless `secret_name` is on the worker-container policy's
  allowlist for the role;
* refused if the broker cannot mint the secret with a TTL no greater
  than the claim's expected lifetime;
* refused if the broker is asked to inject the Slice 2.5
  controller-key private key (a defense-in-depth refusal that
  enforces the §f.3 rule even if a policy accidentally allowlists
  it).

### e.5 `set_network_policy`

**Verb**: install the role's egress allowlist on the worker's
network namespace before any model / tool process starts.

**Inputs**: `(instance_id, allowlist_ref)` where `allowlist_ref`
resolves to the egress allowlist field on the worker-container
policy.

**Records emitted (substrate)**: a network policy record (§e.10) on
the container-instance record naming the allowlist SHA and the
enforcement primitive identifier (Pasta / Slirp4netns / iptables —
the choice is OSD-I-5).

**Refusal predicates**:

* refused if the allowlist for the role is empty *and* the role's
  policy does not declare `egress: none` explicitly (a defense
  against "empty by accident" misconfigurations);
* refused if the enforcement primitive cannot reify the allowlist
  shape (e.g., wildcard hosts the runtime cannot bound).

### e.6 `run_command`

**Verb**: execute a command inside the container.

**Inputs**: `(instance_id, argv)`.

**Records emitted (substrate)**: OPTIONAL command-evidence record
for ratified-replay scenarios (reviewer reproduction of a controlled
mutation); NOT required for ordinary in-pane interactive use.
Recording every keystroke is hostile to operability; recording every
ratified replay is required for auditability.

**Refusal predicates**:

* refused if the container is not in a `running` state;
* refused if a mid-run egress violation is detected by the
  enforcement primitive (the runtime engine MUST surface egress
  violations as a typed refusal, not as a silent drop).

### e.7 `collect_artifacts`

**Verb**: copy a named artifact out of the container's tmpfs into a
tracked or evidence location.

**Inputs**: `(instance_id, src, dst)`.

**Records emitted (substrate)**: an artifact-evidence record naming
`src`, `dst`, and the artifact SHA256.

**Refusal predicates**:

* refused if `dst` is outside the per-claim `evidence/` tree;
* refused if `src` escapes the container's scratch / output tmpfs.

### e.8 `terminate_worker`

**Verb**: stop the container and reap its process tree.

**Inputs**: `(instance_id, reason)` where `reason ∈
{normal_release, claim_lapsed, validator_refusal, operator_abort,
force_reap}`.

**Records emitted (substrate)**: one `container_stopped` event with
the exit code and `reason`.

**Refusal predicates**: `terminate_worker` is required before
`pco-release` step 4 (`git worktree remove`); a Slice 2I-R refusal
gate MUST refuse `pco-release` if the bound container instance is
still in `running` state and no `terminate_worker` event has been
recorded.

### e.9 `garbage_collect_worker`

**Verb**: reclaim a container instance that outlived its claim.

**Inputs**: `(claim_id)`.

**Records emitted (substrate)**: one `container_force_reaped` event
naming the offending `instance_id` and the elapsed-since-release
duration.

**Refusal predicates**: invoked by a periodic sweeper. `PCO-043`
(§g.4) detects the *condition* statically across the tracked record
set so the sweeper's behavior is auditable from records alone.

### e.10 Records emitted by the syscalls

The syscall set is grounded in a small, tracked record set. Slice 2I-S
ratifies the *shape* and the *predicate-bearing fields* of each
record; the concrete JSON Schema artifacts (and the corresponding
validator checks) are Slice 2I-R / Slice 2I-S' implementation gate
deliverables, not in this amendment.

| Record | Purpose | Predicate-bearing fields (substrate-ratified) |
|---|---|---|
| **worker-container policy record** | A ratified policy naming a role's mount manifest, egress allowlist, secret-injection allowlist, runtime engine, image baseline reference, and grant-extensibility surface. | `policy_id`, `role` (`architect_research` \| `implementer` \| `verification`), `image_ref` (name + SHA), `mount_manifest` (per-path mode), `egress_allowlist`, `secret_allowlist` (names only), `runtime_engine`, `grant_extensible` (bool, per mount-class), `lane_binding` `(controller_id, lane_id, worktree_path)`, `policy_sha`. |
| **container-instance record** | One record per allocated container instance. Bound to exactly one claim. | `instance_id`, `policy_ref` (policy_id + policy_sha), `image_sha`, `claim_id`, `lease_id`, `started_at`, `stopped_at` (nullable until termination), `exit_code` (nullable), `mount_manifest_applied`, `egress_allowlist_applied`, `enforcement_primitive`. |
| **mount manifest** | The set of paths actually bound into the container, distinguishing policy-declared from runtime-granted. | embedded on the container-instance record (`mount_manifest_applied`); each entry has `path`, `mode`, `source` (`policy` \| `grant`), `grant_ref` (nullable). |
| **secret-grant manifest (no values)** | The set of secret names injected into the container, with broker-grant ids. **Values never appear.** | embedded on the container-instance record; each entry has `secret_name`, `mode` (`env` \| `file`), `broker_grant_id`, `granted_at`, `revoked_at` (nullable), `ttl_seconds`. |
| **network policy record** | The applied egress allowlist for the instance, including the enforcement primitive. | embedded on the container-instance record; the allowlist SHA and the per-rule shape (`host`, `port`, `protocol`, `rate_limit_class`). |
| **artifact collection manifest** | The set of artifacts copied out via `collect_artifacts`, with destination and SHA256. | one append-only record per artifact, keyed on `instance_id` + `src` + `dst`. |
| **termination event** | `container_stopped` event under the Active-Work Ledger event extension. | `instance_id`, `claim_id`, `stopped_at`, `exit_code`, `reason`. |
| **garbage-collection event** | `container_force_reaped` event. | `instance_id`, `claim_id`, `force_reaped_at`, `elapsed_since_release_seconds`. |

Every record carries a `policy_sha` field so that policy-change
audits can trivially identify which instances ran under which
policy version. The `policy_id` + `policy_sha` pair is the basis for
the Feature 007 (Project Coordination Ledger) reproducibility claim
referenced in §h.

## f. Safety defaults

Slice 2I-S ratifies a *default-deny* safety floor that every Slice
2I-R runtime engine MUST honor. These defaults are normative;
deviation requires explicit, ratified, recorded grants.

### f.1 Read-only mounts by default

Every mount in the policy schema MUST default to `mode: ro`.
Upgrading to `mode: rw` requires an explicit per-path declaration
plus a `write_justification` field on the policy. Implementer roles
will routinely declare `rw` on the allocated worktree (this is their
job); the discipline forces every other write surface to be
deliberate.

The `governance/`, `schemas/`, and `validators/` trees, and the
validator binary, MUST be read-only to **all** worker roles, including
implementer. Validator-source changes are themselves Source-ratified
mutations under Feature 001 (governance / security mutation class)
and belong in the root checkout under an envelope, not inside a
worker container.

### f.2 No host home mount

The default mount manifest for *every* worker MUST exclude every
path under the host user's home directory. Specifically:

* `$HOME` is NOT mounted;
* `~/.ssh/` is NOT mounted, NOT bind-readable, and NOT reachable via
  the SSH agent socket (`SSH_AUTH_SOCK` is unset inside the
  container);
* `~/.gnupg/` is NOT mounted; `gpg-agent` is NOT reachable;
* `~/.aws/`, `~/.config/gh/`, `~/.claude/`, Codex config, browser
  cookie jars, and shell rc files are NOT mounted;
* the host's shell history is NOT exposed.

Any worker-container policy whose mount manifest names a `$HOME`-
relative path or any of the specific paths above MUST fail policy
schema validation (`PCO-040`, §g.1) and MUST be refused by the
runtime engine.

### f.3 No SSH / GitHub / model-provider credentials by default

**Withhold by default**: no credential is injected into a worker
container unless the worker-container policy's `secret_allowlist`
names it.

**Inject named, scoped, time-bounded credentials only**:

* **Model-provider keys**: per-policy. Architect/research and
  implementer roles get model-provider access; verification (when
  its job is replay-from-fixture) does NOT.
* **GitHub access**: a per-task fine-grained PAT or GitHub App
  installation token, scoped to *exactly one branch on one repo*,
  issued by the host-side credential broker at `allocate_worker`
  time, with a TTL no greater than the claim's expected lifetime.
  **Never the host's long-lived PAT.**
* **The Slice 2.5 controller-key private key MUST NOT be injected
  into any worker container.** Workers never sign leases. Only the
  Controller signs. This is the cleanest mechanical enforcement of
  "controller identity is bound outside the worker": if the worker
  physically cannot read the key, it cannot forge a lease under
  another Controller's identity even if it is fully compromised.

This rule interacts with OSD-1 in the parent spec (§i.8 of this
amendment): any OSD-1 candidate that injects the controller-key
private key into a worker is incompatible with Slice 2I and MUST be
removed from OSD-1's candidate list when OSD-1 is ratified.

### f.4 No container engine socket inside worker containers

**The Docker / Podman socket MUST NEVER be mounted into a worker
container.** Mounting it is functionally equivalent to giving the
worker root on the host. Any worker-container policy whose mount
manifest includes `/var/run/docker.sock`, `/run/podman/podman.sock`,
`/var/run/podman/podman.sock`, the user's `XDG_RUNTIME_DIR/
podman/podman.sock`, or any equivalent IPC socket MUST fail policy
schema validation (`PCO-045`, §g.6).

Workers that need to spawn child containers (the only legitimate
Creator Engine use case is the Controller and, in a later gate, a
dedicated "spawner" service — not workers) MUST do so through a
typed RPC to the host-side spawner, not by direct socket access.

### f.5 Role-specific network egress

The egress allowlist is per-role (§d.2) and MUST be enforced by the
runtime engine before any model / tool process inside the container
issues network I/O. The allowlist *shape* is substrate-ratified by
Slice 2I-S; the *concrete host list* is a deployment-time overlay
(architect-report §7.c, "tracked runtime contract" vs. "local
prototype" boundary).

Per role:

| Role | Egress shape |
|---|---|
| `architect_research` | model-provider hosts + ratified documentation/web domain allowlist + source-host read API (rate-limited) |
| `implementer` | model-provider hosts + ratified dependency-registry allowlist (npm, PyPI, crates.io, equivalents) + source-host write API for the *one* branch granted by the per-task PAT |
| `verification` | none by default; OR ratified dependency-registry-only allowlist when offline-cached deps are not viable |

Connector workers (Feature 008) get a separate egress shape (source-
host / tracker API hosts only; no model provider; no dependency
registries). Slice 2I-S records the architect/research /
implementer / verification triple normatively; the connector shape is
deferred to the Feature 008 amendment.

### f.6 Redaction and revocation expectations for secrets

**Redaction**: secret *names* appear in the secret-grant manifest
and in side-effect records; secret *values* never do. Slice 2I-R MUST
ship a `secret_value_leak` predicate that scans tracked records
(especially side-effect, container-instance, and CI evidence
records) for the substring or hash of any known injected secret
value, and MUST refuse on match. This is defense-in-depth, not a
primary boundary; the primary boundary is "the value is not in the
record in the first place."

**Revocation**: on `terminate_worker`, the runtime engine MUST signal
the credential broker to revoke every token issued for the released
claim **before** the `container_stopped` event is written. This is
the team-mode-clean default: tokens are claim-scoped, not session-
scoped. The secret-grant manifest's `revoked_at` field is set as
part of the same atomic step.

## g. Refusal predicates (PCO-040 → PCO-045)

Slice 2I-S adds six substrate-level refusal predicates. Each follows
the established PCO predicate pattern (substrate-only, citing the
prose contract, with a backward-compatibility floor so trees without
Slice 2I substrate preserve prior behavior). Each predicate is
*declared* in this amendment; the corresponding validator
implementation is a Slice 2I-R / Slice 2I-S-implementation gate
deliverable, not produced by this gate.

### g.1 PCO-040 — Worker-Container Policy Schema (substrate-only, Slice 2I-S)

A tracked file under `governance/policies/worker-container/` (or an
equivalent ratified location to be selected at implementation time)
declaring a worker-container policy MUST validate against the
worker-container policy schema declared in §e.10. Predicate failures
MUST cite the violated field, the violated invariant, and this
amendment.

### g.2 PCO-041 — Container-Instance Record Schema (substrate-only, Slice 2I-S)

A tracked container-instance record MUST validate against the
container-instance record schema declared in §e.10. The predicate
distinguishes structural violations (not a YAML mapping) from
schema violations (missing or malformed predicate-bearing field), so
later slices can build on the distinction.

### g.3 PCO-042 — Container Required for Claim (Slice 2I-R, gated)

When the scanned tree contains at least one worker-container policy
record, a live claim record MUST be paired with a container-instance
record that names it. Trees without any worker-container policy
record preserve Slice 2R behavior unchanged (same backward-
compatibility floor pattern as `PCO-026` for the Slice 2.5 key
substrate).

`PCO-042` is a runtime-gate predicate; the substrate is ratified in
this amendment, but the validator check lands with Slice 2I-R.

### g.4 PCO-043 — Container Outlives Claim (substrate-only, Slice 2I-S)

Refuses a tree where a container-instance record names a `claim_id`
that has been released (the corresponding `claim_released` or
`claim_lapsed` event exists) AND no `container_stopped` or
`container_force_reaped` event has been recorded for the instance.
This is the static surface that backs the `garbage_collect_worker`
sweeper (§e.9).

### g.5 PCO-044 — Image SHA Matches Policy (substrate-only, Slice 2I-S)

Refuses a container-instance record whose `image_sha` does not match
the policy in force at `started_at`. The policy SHA is recorded on
the instance record (§e.10); this predicate enforces that the
allocator did not silently substitute a different image after the
policy was ratified.

### g.6 PCO-045 — Forbidden Mount Refusal (substrate-only, Slice 2I-S)

Refuses any worker-container policy whose mount manifest names a
forbidden path. The forbidden-path set is normative:

* the container engine socket family (Docker / Podman; see §f.4);
* `$HOME`-relative paths (see §f.2);
* the host SSH agent socket (`$SSH_AUTH_SOCK`);
* the host GPG agent socket (`$GPG_AGENT_INFO` socket path);
* `/var/run/docker.sock`, `/run/docker.sock`,
  `/run/podman/podman.sock`, `/var/run/podman/podman.sock`,
  `$XDG_RUNTIME_DIR/podman/podman.sock`;
* the validator binary's source tree under `validators/` and the
  governance schema tree under `schemas/` — read-only is enforced
  by `f.1`; `PCO-045` additionally refuses any `rw` declaration on
  these trees.

`PCO-045` is the single schema-level boundary against the most-
violated container anti-pattern in the industry.

## h. Roadmap placement and slice relationships

Slice 2I is positioned as a **sibling / bridge slice** between the
Slice 2.5 + Slice 2R authoring gate (already complete) and the
Slice 2.5 + Slice 2R *implementation* gate (currently blocked, by
the architect report, pending Slice 2I and the OSD-1 resolution).

```
… Slice 2A (lease substrate) — landed
… Slice 2.5 (identity substrate) + Slice 2R (allocator runtime spec)
   ← spec authored; implementation gated on Slice 2I + OSD-1
… Slice 2I — Worker Isolation Runtime           ← THIS AMENDMENT
   ├── Slice 2I-S — substrate (records, syscalls, predicates,
   │                 safety defaults, OSDs)  ← this gate
   └── Slice 2I-R — runtime (engine wiring,
                    allocator extension, broker)  ← deferred,
                                                    separately ratified
… Slice 3 (Pane Registry; authored against Slice 2I-S)
… Slice 0.5R (completion-gate runtime)
… Slice 4 (Side-Effect Ledger; container-egress-aware)
… Slice 5 (pco-fanin)
… Slice 6 (Integration Queue)
… Features 007 / 008 / 009 (team-mode workstreams)
```

### h.1 Relationship to Slice 2R (Worktree Allocator Runtime)

Slice 2R's `pco-allocate` (PCO-027) is a 7-step atomic sequence. The
existing `PCO-032` boundary statement explicitly excludes container
orchestration from the Slice 2R gate; that boundary statement is
the seam Slice 2I-R later extends. The shape of the extension
(named here for completeness; not authored by this gate):

* **PCO-027 step 5.b (new, Slice 2I-R)**: after the lane lock is
  acquired (step 4) and the worktree is created and recorded (step
  5), `allocate_worker` starts the container under the ratified
  policy and writes the container-instance record + `container_
  started` event under the *same* lane lock. Rollback in step 6
  additionally tears down the container if it was started.
* **PCO-028 step 3.b (new, Slice 2I-R)**: before `pco-release` calls
  `git worktree remove`, `terminate_worker` stops the container and
  writes the `container_stopped` event under the same lane lock.

The Slice 2R atomic-transaction contract is sequence-additive, not
structure-tight; inserting the container start/stop steps does NOT
require amending PCO-027 or PCO-028. This is the architecturally
significant property that lets Slice 2I land additively.

### h.2 Relationship to Slice 3 (Pane Registry)

Pane identity (Slice 3) MUST bind to a container-instance id (when
present), not only to a tmux pane id on a host. Authoring Slice 3
*after* Slice 2I-S means the pane-identity record can carry an
optional `container_instance_id` field from the start and avoid a v2
migration. Slice 3 is therefore additionally blocked on this
amendment (Slice 2I-S) being ratified, but NOT on Slice 2I-R being
implemented.

### h.3 Relationship to Slice 4 (Side-Effect Ledger)

Container egress events — the set of hosts and the byte volumes the
container actually contacted via its allowlist — are exactly the
side-effect class Slice 4 must track. The Slice 2I-S `egress_
allowlist` is the *policy*; Slice 4 is the *evidence* of what
actually traversed the boundary. Authoring Slice 4 against
Slice 2I-S means the side-effect surface is bounded by the
allowlist; authoring it without Slice 2I would record only the
post-hoc CI / GitHub mutation surface, leaving the host's network
traffic unaudited.

### h.4 Relationship to Slice 5 (`pco-fanin`)

Fan-in already plans to reconstruct ground truth from tracked
artifacts rather than lane self-report; container-instance records
strengthen that reconstruction by binding each tracked artifact to
the policy SHA, image SHA, mount manifest, and egress allowlist
under which it was produced.

### h.5 Relationship to Slice 6 (Integration Queue)

Unaffected at the queue level (Slice 6 operates at the branch / PR
level, above the worker layer). However, the integration queue MAY
later choose to refuse a queued integration whose contributing
container-instance records reference a deprecated policy SHA. That
choice is a Slice 6 amendment, not a Slice 2I deliverable.

### h.6 Relationship to team-mode workstreams (Features 007 / 008 / 009)

Containerization does not delay team-mode; it strengthens it.

* **Project Coordination Ledger (Feature 007)**: PCL claim records
  SHOULD optionally name the worker-container policy under which the
  claim was executed. This gives team-mode a substrate-level way to
  say "developer A ran the implementation under policy X; the
  evidence is reproducible against policy X's image SHA, mount
  manifest, and egress allowlist."
* **Source-Host & Tracker Connectors (Feature 008)**: connectors
  SHOULD run in their own worker-container policy (a connector role,
  not in this amendment's three-role enum) with narrow egress to the
  source-host / tracker API only, no model-provider access, no
  worktree write. This is the cleanest place to make the "tracker is
  a mirror, not canonical" boundary mechanically enforceable.
* **Distributed Identity (Feature 009)**: the controller-key custody
  mode (OSD-1) gains a candidate once Slice 2I lands: *per-container
  ephemeral key* (key generated inside the container at start time,
  never written to host filesystem, public key surfaced into the
  container-instance record). This is the strongest available
  custody mode and is reachable only after Slice 2I.

The candidate is named in §i.8 (OSD-1 amendment) as a forward note.

## i. Open Source Decisions (OSDs)

Slice 2I-S leaves the following decisions explicitly open. Each is a
Source-ratified choice that blocks Slice 2I-R implementation. Each
preserves the substrate / contract of this amendment regardless of
resolution.

### i.1 OSD-I-1 — Runtime engine

Choice between **rootless Podman** and **rootless Docker** as the v1
worker runtime engine. Both run unmodified OCI images; both support
rootless / user-namespace operation. Podman is rootless-first and
the architect report's mild recommendation; rootless Docker is
acceptable. Source ratifies.

### i.2 OSD-I-2 — Image baseline

Choice between NanoClaw-derived baseline, clean-room per-role
images, or devcontainer-derived per-repo images. Each has different
maintenance and supply-chain properties. Source ratifies; OSD-I-6
(§i.6) interacts with this choice.

### i.3 OSD-I-3 — Controller containerization timeline

Confirm: Controller stays on host through at least Slice 6 (architect
report and this amendment recommend this), versus containerizing the
Controller earlier. Earlier Controller containerization requires a
stable Hermes contract, a privileged-but-tiny host-side spawner
service, and a secret-injection primitive for the controller-key. All
three are independently non-trivial.

### i.4 OSD-I-4 — Credential broker

In-host process versus dedicated service versus third-party
(GitHub App, HashiCorp Vault, cloud secret manager). The credential
broker is the integration point for §f.3 (named, scoped, time-bounded
credentials) and §f.6 (revocation on `terminate_worker`). The choice
affects team-mode posture.

### i.5 OSD-I-5 — Egress enforcement primitive

Choice between Slirp4netns + allowlist, Pasta, host-side iptables,
or a user-namespace network namespace with a forwarder. All work.
The choice affects observability (side-effect ledger fidelity per
Slice 4) and team-mode portability (per-workstation runtime engine
homogeneity).

### i.6 OSD-I-6 — Image separation by role

One image with role-conditional policy versus distinct images per
role. Distinct images are more secure (smaller per-role attack
surface) but double image-maintenance load. Source ratifies; OSD-I-2
interacts.

### i.7 OSD-I-7 — Mount-grant authority

When the implementer needs a path outside its worktree (e.g., to
read a sibling package the monorepo expects), who ratifies the grant
— the Controller alone, or Source? Recommendation: per-grant rule
recorded in policy, with `governance`-class records requiring Source
ratification (Feature 001 FR-008 inheritance). The
`grant_path_capability` syscall (§e.3) requires `justification_ref`;
this OSD chooses what `justification_ref` is allowed to resolve to.

### i.8 OSD-1 amendment — Per-container ephemeral controller-key

The existing Slice 2.5 + 2R OSD-1 candidate list (`per-host`,
`per-developer tenant`, `both`) is augmented by a fourth candidate
once Slice 2I lands: **per-container ephemeral key**, where the
controller-key is generated inside the Controller's *own* container
at start time, never written to host filesystem, and the public key
is surfaced into the container-instance record for verification.

This candidate is the strongest custody mode against host
compromise and worker compromise alike, and is reachable only after
Slice 2I-R lands. It is named here as a forward note; the OSD-1
resolution itself is the Slice 2.5 + 2R implementation gate's
concern, not Slice 2I-S's.

Independent of which OSD-1 candidate is chosen, this amendment
ratifies (§f.3) that **the controller-key private key MUST NOT be
injected into any worker container.** Any OSD-1 candidate that
violates this constraint MUST be removed from OSD-1's candidate
list at OSD-1 resolution time.

## j. Non-goals

Slice 2I-S explicitly does NOT introduce:

* **No container image implementation**. Image authoring (Dockerfile
  / Containerfile / build pipeline / image registry pushes) is a
  Slice 2I-R / Slice 2I-S-implementation gate deliverable, not
  produced by this amendment.
* **No Docker / Podman run, build, pull, or push**. This authoring
  gate does not invoke any container command and has not pulled any
  image. Any image-SHA reference in this amendment is illustrative,
  not a content claim against an actual image.
* **No credential broker implementation**. The credential broker is
  named as a §e.4 / §f.3 / §f.6 dependency and as OSD-I-4; its
  implementation is downstream.
* **No Hermes runtime / profile / config / hook / MCP / model
  provider mutation**. This amendment edits only the tracked spec
  surface (this file + ROADMAP + architecture cross-reference); it
  does not touch any Hermes-side surface.
* **No schema, validator, test, or example implementation unless
  separately ratified**. The records named in §e.10 and the
  predicates `PCO-040` through `PCO-045` are *declared* here; the
  concrete schema YAML, validator check Python, and example records
  are Slice 2I-S-implementation deliverables.
* **No autonomy expansion**. `PCO-032`'s Phase 1 / Phase 2 boundary
  remains in force. Every Slice 2I-R runtime mutation will continue
  to descend from a Source-ratified Assignment Envelope; every
  worker-container policy is itself a `governance`-class mutation
  under Feature 001 FR-008; the Controller continues to be the only
  process authorized to allocate or release workers.
* **No replacement of Assignment Envelopes, handoffs, or Source
  ratification**. Slice 2I-S is substrate; authority remains Source.
* **No tmux removal**. The visible-pane substrate (tmux) is
  preserved. Worker containers sit *below* visible panes; Slice 3
  records both.
* **No Controller containerization**. OSD-I-3 (§i.3) defers this
  decision.

## k. Acceptance posture

A fresh-clone reviewer can verify the following from this
amendment together with the parent spec and the architect report:

1. The threats in §c are derived from the *current* tmux-hosted
   execution model and are reachable from a freeform pane shell
   today.
2. The three worker roles in §d.2 (`architect_research`,
   `implementer`, `verification`) and their per-role defaults are
   distinct and non-interchangeable.
3. The nine syscalls in §e are each grounded in a substrate record
   from §e.10; no syscall in §e returns success without a tracked
   record emission, and `inject_secret` (§e.4) never records the
   secret value.
4. The safety defaults in §f are default-deny: read-only mounts, no
   host home mount, no host credentials by default, no engine socket
   inside a worker container, role-shaped egress, redaction +
   revocation.
5. The six refusal predicates `PCO-040` through `PCO-045` (§g) are
   substrate-only (no runtime mutation), follow the established PCO
   predicate pattern, and (where applicable) carry the same
   backward-compatibility floor as `PCO-026`.
6. The roadmap placement in §h positions Slice 2I as a sibling /
   bridge slice that Slices 3, 4, 5, 6 and Features 007 / 008 / 009
   should be authored against.
7. The eight OSDs in §i are explicitly open; this amendment makes no
   policy decision on engine, image baseline, controller
   containerization timeline, credential broker, egress enforcement
   primitive, image separation by role, mount-grant authority, or
   the OSD-1 per-container ephemeral controller-key candidate.
8. The §j non-goals confirm: no image authoring, no container
   command invocation, no credential broker implementation, no
   Hermes-side mutation, no schema / validator / test / example
   implementation, no autonomy expansion, no removal of Assignment
   Envelopes / handoffs / Source ratification, no tmux removal, no
   Controller containerization in this gate.
9. The amendment is forward-compatible with the existing Slice 2.5
   + 2R spec (PCO-024 through PCO-032 are NOT amended); Slice 2I-R
   extends `PCO-027` / `PCO-028` additively when it lands.
10. The amendment does not author runtime, image, credential, or
    Hermes-side artifacts; the changed-file set is bounded to this
    sub-spec, ROADMAP.md, and (where present) the parallel-
    controller-orchestration architecture cross-reference.
