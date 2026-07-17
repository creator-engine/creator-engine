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

#### d.2.1 Governed Codex one-shot role envelope

The policy-bound Codex one-shot launcher applies
`CE-GOVERNED-ROLE-ENVELOPE-V1` to the closed leaf set
`architect_research | implementer | reviewer | verification`. `reviewer`
is the read-only review specialization of the read-only worker posture;
this launcher contract does not widen the worker-container role enum,
mounts, egress, credentials, or runtime authority described above.

The launcher MUST read and SHA-256-bind the canonical tracked role policy
and the canonical governed brief before planning. It MUST pass only the
exact verified brief bytes on ordinary stdin. Role-policy bytes, ambient
bootstrap prose, ticket content, credential values, and secret values MUST
NOT enter stdin or the role envelope.

The deterministic developer-role envelope contains only:

* its schema/version and one closed leaf role;
* `seat_class: worker` and disabled nested delegation;
* canonical worktree-relative role-policy and brief paths with their
  SHA-256 digests;
* the closed role capability and sandbox posture;
* prohibitions on controller or foreman authority, nested spawn, role
  switching, credential expansion, approval, enqueue, merge, signing, and
  every reserved act; and
* parent lineage as provenance only, with no inherited authority.

The launcher MUST supply that instruction through a bounded, deterministic,
round-trip-verified TOML string in
`codex exec --strict-config -c developer_instructions=<TOML-string>`.
`features.multi_agent=false` remains mandatory. The launcher MUST refuse,
before runner invocation, an unknown or malformed role, digest or envelope
mismatch, noncanonical or control-bearing path, unsafe TOML encoding,
oversized envelope, missing or reordered strict configuration, authority
or sandbox escalation, nested delegation, or any prompt-only, foreman, or
unguarded fallback. `model_instructions_file`, mutable ambient role prose,
and role-policy framing on stdin are not permitted substitutes.

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

---

# Slice 2I-R — Worker Isolation Runtime Mechanics (Spec Authoring, Deferred Gate)

**Slice id**: `Slice 2I-R` (Worker Isolation Runtime — runtime gate)
**Status**: Spec authoring only; no runtime implementation, image build,
container execution, or credential issuance is produced by this gate.
**Created**: 2026-05-22
**Source-of-truth relationship**: This section is an **additive
amendment** to the Slice 2I-S substrate above (§§a–k). It does NOT
modify any prior PCO functional requirement (`PCO-001` through
`PCO-043`). It authors the runtime mechanics that Slice 2I-R will
implement, at prose/spec level only, making the extension points
in §h.1 and §g.3 concrete enough to serve as an implementation
specification. No runtime code, schema implementation, or container
engine invocation is produced here.

**Authoring boundary**: This gate edits only the two authorized
tracked write surfaces listed in the ARCHITECT_HANDOFF:
`specs/005-pco-parallel-controller-orchestration/worker-isolation-runtime.md`
(this file) and
`docs/architecture/parallel-controller-orchestration.md`.
No `pco-allocate` / `pco-release` source, no schema YAML, no
validator Python, no Dockerfile, no Hermes hook, no CI configuration,
and no credential is touched.

---

## l. Runtime entry point contracts (Slice 2I-R)

Slice 2I-S named two extension points (§h.1): PCO-027 step 5.b for
`pco-allocate` and PCO-028 step 3.b for `pco-release`. This section
authors those extension contracts in full. Both extensions are
**conditional**: they execute only when at least one worker-container
policy record is present in the scanned governance tree. Trees without
any policy record preserve the existing PCO-027 / PCO-028 step
sequences unchanged, providing the same backward-compatibility floor
as the Slice 2A predicates.

### l.1 `pco-allocate` extension (PCO-027 step 5.b, Slice 2I-R)

After PCO-027 step 5 (worktree add + lease write + claim write +
`claim_created` event) and before the lane lock is released, Slice
2I-R inserts the following sub-sequence under the **same** advisory
lane lock already held at step 3. Every sub-step must succeed before
the next sub-step begins; failure at any sub-step triggers the
extended rollback described in sub-step 10.

1. **Select policy.** Resolve the ratified worker-container policy
   record for the target worker role. The selector matches
   `(controller_id, lane_id, worktree_path)` against each policy's
   `lane_binding` field, preferring the most recently ratified
   policy with a matching `role`. If no matching policy is found,
   `pco-allocate` MUST exit non-zero with a typed error citing
   `PCO-042` and the absence of a policy record for the role; it
   MUST NOT leave the worktree in a partially allocated state without
   a paired container instance.

2. **Validate policy schema (PCO-040 pre-start check).** Run the
   `PCO-040` worker-container policy schema check against the
   selected policy record. Refuse on any schema violation; cite the
   violated field, the violated invariant, and `PCO-040`.

3. **Validate image SHA (PCO-044 pre-start check).** Confirm that
   the policy's `image_ref.sha` resolves to a locally available
   image and matches the policy's `image_sha` field exactly. Refuse
   on mismatch; cite the policy's recorded SHA versus the observed
   SHA and `PCO-044`. No image pull is triggered by this step; a
   missing image is a pre-start failure.

4. **Start container.** Invoke the runtime engine's container-start
   primitive with `(policy_ref, image_sha, claim_id, lease_id)`.
   The runtime engine is identified by the selected policy's
   `runtime_engine` field (rootless Podman or rootless Docker per
   OSD-I-1; §i.1). `pco-allocate` MUST NOT hard-code the engine
   name; it reads the engine identifier from the policy record.
   The container MUST start in a paused or network-isolated state
   until `set_network_policy` completes (sub-step 6 below).

5. **Mount worktree (invoke `mount_workspace`).** Call
   `mount_workspace(claim_id, worktree_path, mode)` where `mode` is
   read from the policy's `mount_manifest` for the worktree mount
   class (typically `rw` for the implementer role, `ro` for
   architect/research and verification). The runtime engine MUST
   refuse to mount any path outside the allocated worktree, the
   tmpfs scratch, or the read-only governance tree, without an
   explicit `grant_path_capability`. The `mount_manifest_applied`
   field of the container-instance record is populated by this step.

6. **Apply network policy (invoke `set_network_policy`).** Call
   `set_network_policy(instance_id, allowlist_ref)` where
   `allowlist_ref` resolves to the policy's `egress_allowlist` for
   the target role. The enforcement primitive (Pasta by default per
   §o.1; Slirp4netns with custom configuration per §o.2 as acceptable
   equivalent) MUST be fully configured on the container's network
   namespace before sub-step 7 or any model / tool process starts.
   The `egress_allowlist_applied` and `enforcement_primitive` fields
   of the container-instance record are populated here.

7. **Issue credentials (invoke `inject_secret` per name).** For each
   `secret_name` in the policy's `secret_allowlist` for the target
   role: call the host-side credential broker (§n) to mint a
   claim-scoped, TTL-bounded credential; then call
   `inject_secret(instance_id, secret_name)` to expose it inside the
   container via the broker-declared injection mode (env or file).
   The host operator's `GH_TOKEN` MUST NOT be passed; only a
   per-task fine-grained GitHub PAT or GitHub App installation token,
   scoped to the single branch and repository declared by the claim,
   is acceptable for GitHub access. Secret values MUST NOT appear in
   any tracked record; only `secret_name`, `broker_grant_id`,
   injection mode, and `ttl_seconds` are recorded.

8. **Write container-instance record.** Write one container-instance
   record of the shape declared in §e.10 and validated by `PCO-041`,
   under the same advisory lane lock. The record MUST include:
   `instance_id`, `policy_ref` (policy id + policy SHA),
   `image_sha`, `claim_id`, `lease_id`, `started_at`,
   `mount_manifest_applied` (from sub-step 5),
   `egress_allowlist_applied` (from sub-step 6),
   `enforcement_primitive` (from sub-step 6). Fields `stopped_at`
   and `exit_code` are null at this point.

9. **Emit `container_started` event.** Append a `container_started`
   event to the Active-Work Ledger event log under the same lane
   lock. The event MUST include `instance_id`, `claim_id`,
   `policy_ref`, and `started_at`. It MUST NOT include secret
   values, injected credential content, or the broker grant values.
   After this event is durably written, the lane lock may be
   released and the container may be unpaused.

10. **Extended rollback surface.** If any sub-step 1 through 9 fails,
    `pco-allocate`'s existing step-6 rollback (which undoes the
    worktree, lease, claim, and `claim_created` event) MUST
    additionally: terminate the container if it was started (sub-step
    4 succeeded); invoke the credential broker's revoke path for any
    tokens minted in sub-step 7; and delete the container-instance
    record if it was written in sub-step 8. After full rollback the
    tree MUST be observably indistinguishable from the pre-allocate
    state. `pco-allocate` MUST exit non-zero and MUST emit a
    `gate_blocked` event citing the failing sub-step and predicate.

The pane spawn (OSD-4; §i of the parent spec) MUST NOT proceed until
PCO-027 step 5.b completes fully and the lane lock has been released
from sub-step 9.

### l.2 `pco-release` extension (PCO-028 step 3.b, Slice 2I-R)

Before PCO-028 step 3 (`git worktree remove`) and while the advisory
lane lock is held, Slice 2I-R inserts the following sub-sequence.
The extension is conditional: if the released claim has no paired
container-instance record (a claim from a pre-Slice-2I-R tree),
the sub-sequence is skipped entirely and PCO-028 degrades gracefully
to its existing five-step sequence.

1. **Locate container instance.** Read the container-instance record
   whose `claim_id` matches the released claim. If no such record
   exists (pre-Slice-2I-R claim), skip sub-steps 2 through 6 and
   proceed directly to PCO-028 step 3 (`git worktree remove`).

2. **Verify terminal state.** Check whether the container instance is
   already in a terminal state: `stopped_at` is set and at least one
   of `container_stopped` or `container_force_reaped` event records
   exists for `instance_id`. If already terminal, skip sub-steps 3
   through 5 and proceed directly to sub-step 6 (credential
   revocation).

3. **Terminate container (invoke `terminate_worker`).** Call
   `terminate_worker(instance_id, reason=normal_release)`. The
   runtime engine MUST deliver `SIGTERM` to the container's init
   process and wait for an orderly shutdown; after a configured grace
   period it MUST deliver `SIGKILL` and reap the full process group.
   If the runtime engine cannot confirm that the process tree is
   reaped within the total configured timeout, `pco-release` MUST
   fail immediately: it MUST NOT proceed to sub-step 4, 5, or 6, and
   MUST NOT call `git worktree remove`. It MUST emit a `gate_blocked`
   event citing `PCO-043` and the reason the terminal state could not
   be established (engine error, timeout, or process-tree reap
   failure). The operator may re-invoke `pco-release` once the
   obstruction is cleared; the periodic sweeper handles permanently
   unreachable instances via `garbage_collect_worker` (§e.9, §m.2).

4. **Record exit status.** Write `stopped_at` and `exit_code` to the
   container-instance record under the same lane lock. These fields
   MUST be populated before the `container_stopped` event is emitted.

5. **Emit `container_stopped` event.** Append a `container_stopped`
   event to the Active-Work Ledger event log with `instance_id`,
   `claim_id`, `stopped_at`, `exit_code`, and
   `reason=normal_release`. After this event is durably written the
   container instance is in a terminal state and the worktree can
   safely be removed.

6. **Revoke credentials.** Signal the credential broker (§n) to
   revoke every token minted for the claim, identified by `claim_id`.
   The broker MUST complete revocation synchronously before
   acknowledging the call. The secret-grant manifest's `revoked_at`
   field MUST be written as part of this step, before
   `claim_released` is written in PCO-028 step 3.

**Refusal on unverifiable terminal state.** PCO-028 MUST refuse to
call `git worktree remove` (step 3) if the paired container instance
is not in a terminal state and sub-step 3 has failed to establish
one. The refusal MUST be expressed as a non-zero exit with a typed
error citing `PCO-043`. Refusing the release and leaving the worktree
allocated is the safer failure mode; orphan worktrees can be manually
reviewed and re-released; prematurely removing a worktree with a live
container process cannot be undone.

## m. Runtime predicate refinement (PCO-042, PCO-043)

Substrate declarations appear in §g.3 and §g.4. This section authors
the validator implementation contract at the resolution the Slice
2I-R implementation gate requires.

### m.1 PCO-042 — Container Required for Claim (runtime validator, Slice 2I-R)

PCO-042 is declared in §g.3 as a runtime-gate predicate whose
substrate is ratified by Slice 2I-S and whose validator check lands
with Slice 2I-R. The validator implementation MUST follow this
cross-record traversal:

1. Scan the scanned tree for at least one file under the ratified
   governance path for worker-container policies that validates
   against `PCO-040`.

2. If no valid policy record exists: PCO-042 produces no violations.
   Every active claim passes regardless of container state. This is
   the backward-compatibility floor (pre-Slice-2I-R operation,
   matching the floor in §g.3).

3. If at least one valid policy record exists: for every claim record
   in the scanned tree whose `released_at` field is null (a live
   claim), the validator MUST assert that at least one
   container-instance record exists with a matching `claim_id` and
   a null `stopped_at` field (a running instance). Any live claim
   without a paired running container-instance record is a PCO-042
   violation.

4. Each PCO-042 violation MUST include in its structured output:
   `claim_id`, `lane_id`, `controller_id`, the predicate code
   `PCO-042`, and the human-readable message
   `"live claim has no paired running container instance"`. Violations
   MUST cause `active_work_ledger_conflicts` to exit non-zero.

5. PCO-042 is additionally enforced proactively at:
   - `pco-allocate` sub-step 1 (refusal if no matching policy exists,
     before container start); and
   - the PCO-030 pre-launch gate (pane spawn is gated on the conflict
     validator passing, which includes PCO-042 from the moment a
     policy record is present in the tree).

**As-built (Slice 2I-R implementation).** The "ratified governance
path for worker-container policies" of step 1 is selected as
`governance/policies/worker-container/` (the §g.1 default location).
The validator (`active_work_ledger_conflicts`,
`CODE_CONTAINER_REQUIRED = "PCO-042"`) arms only on a `PCO-040`-valid
policy under that path; a policy elsewhere in the tree (e.g. an
`examples/…` fixture) does not arm the gate, preserving the Slice 2R
floor for the bundled example bundle while still failing a real
governed tree. Matching is `container_instance.claim_id ==
claim.lane_id` with `stopped_at` null (claims carry no separate
`claim_id` field; the lane id is the claim identity). The runtime
entry point `worker_runtime.allocate_worker` is the proactive
`pco-allocate` sub-step 1 surface.

### m.2 PCO-043 — Container Outlives Claim (sweeper runtime, Slice 2I-R)

PCO-043 is declared in §g.4 as a substrate-only static predicate
(Slice 2I-S). Slice 2I-R adds the periodic sweeper that acts on
PCO-043 hits:

1. The periodic sweeper MUST invoke the PCO-043 cross-record scan
   at a configurable interval (default: every heartbeat period, or
   at a minimum once per `claim_lapsed` event). The scan is the
   same as §g.4: container-instance records with a released claim
   and no terminal event.

2. For each hit, the sweeper MUST invoke
   `garbage_collect_worker(claim_id)` (§e.9). `garbage_collect_worker`
   MUST: deliver `SIGKILL` to the container's process group; wait for
   the OS to confirm process-group exit; then write a
   `container_force_reaped` event.

3. The `container_force_reaped` event MUST include: `instance_id`,
   `claim_id`, `force_reaped_at` (wall-clock timestamp of confirmed
   reap), and `elapsed_since_release_seconds` (duration from the
   `claim_released` or `claim_lapsed` event timestamp to
   `force_reaped_at`).

4. The static validator and the sweeper report different states:
   a validator hit (`PCO-043_condition_present`) means the orphan
   condition exists and the sweeper has not yet acted (or has failed).
   A `container_force_reaped` event (`PCO-043_force_reaped`) means
   the sweeper has acted. These MUST be distinguishable in validator
   output.

5. If `garbage_collect_worker` cannot deliver a confirmed kill (e.g.,
   the runtime engine is unreachable), the sweeper MUST record the
   failure as a `container_reap_failed` event (a new event kind,
   additive to the event log schema) with the error reason and retry
   count, and MUST retry on the next sweep interval. It MUST NOT
   silence the PCO-043 validator hit.

## n. Credential broker contract (spec level, Slice 2I-R)

The credential broker is a host-side process or service that issues,
manages, and revokes per-task credentials. Its concrete implementation
technology is OSD-I-4 (§i.4): in-host process, dedicated service,
GitHub App, or third-party secrets manager. This section specifies
the behavioral contract the broker MUST honor regardless of
technology choice. No broker is implemented by this spec authoring
gate.

### n.1 Broker responsibilities

**Mint on demand.** When `inject_secret(instance_id, secret_name)`
is called, the broker mints a credential for `secret_name` bounded
to the current claim's `(repo, branch, claim_id)` context. The TTL
MUST NOT exceed the claim's `expected_lifetime_seconds`; the broker
SHOULD set the TTL to 90% of the remaining claim lifetime to leave
a revocation window.

**Supported credential types** (minimum set for Slice 2I-R):

- **Per-task fine-grained GitHub PAT**: scoped to read/write exactly
  the single repository and branch declared by the claim, no
  additional scopes, claim-lifetime TTL. This MUST NOT be the
  operator's long-lived `GH_TOKEN`.
- **GitHub App installation token** (acceptable equivalent to the
  fine-grained PAT): the same scoping and TTL contract applies.
  Preferred over a PAT for team-mode operation because App tokens
  are not tied to a personal account.
- **Model-provider API key**: the broker surfaces the key identified
  by `secret_name` from a local secrets store. Model-provider keys
  are long-lived by nature; the broker's role is access-control
  (gating which instances get the key), not rotation, for this type.

**Withhold by default.** The broker MUST refuse any `inject_secret`
call where `secret_name` is not listed in the worker-container
policy's `secret_allowlist` for the target role. Even if the policy
allowlist is broad, the broker MUST additionally refuse any call that
requests the Slice 2.5 controller-key private key by any name; this
is the defense-in-depth enforcement of §f.3 (the controller-key MUST
NOT enter any worker container).

**Host `GH_TOKEN` never enters a container.** The broker MUST NOT
read from or pass the host operator's `GH_TOKEN` environment
variable to any worker container, directly or indirectly. The
per-task PAT or App installation token is the only GitHub credential
the broker injects.

**Revoke on release.** When signaled by `pco-release` sub-step 3.b.6,
the broker MUST revoke every token minted for `claim_id`
synchronously, before returning to the caller. Revocation MUST
precede the `claim_released` event write in PCO-028 step 3. The
secret-grant manifest's `revoked_at` field is set as part of this
step.

**Secret values never recorded.** Broker logs, broker database
records, Active-Work Ledger records, container-instance records,
secret-grant manifests, side-effect records, and any archived
transcript file MUST NOT contain secret values (PAT strings, API key
values, App token strings). The broker records only: `secret_name`,
`broker_grant_id`, injection mode (`env` or `file`), `granted_at`,
`ttl_seconds`, and (after revocation) `revoked_at`. A
`secret_value_leak` predicate hit (§f.6) on any of these surfaces is
a critical validator failure.

### n.2 Broker integration points

The following table maps each `pco-allocate` / `pco-release`
sub-step to the broker call and the record updated.

| Entry point | Broker call | Broker action | Record updated |
|---|---|---|---|
| `pco-allocate` sub-step 7 | `broker.mint(claim_id, secret_name, role, ttl)` | Mint credential; return `(broker_grant_id, injected_value)` | Secret-grant record: `secret_name`, `broker_grant_id`, mode, `granted_at`, `ttl_seconds` |
| `inject_secret` (runtime engine) | `broker.inject(instance_id, broker_grant_id)` | Expose value via env or file inside container | No new record; the existing secret-grant record is the full substrate trace |
| `pco-release` sub-step 3.b.6 | `broker.revoke(claim_id)` | Revoke all tokens for claim; return `revoked_at` per token | Secret-grant record: `revoked_at` |

The injected value is the only moment the credential value crosses
the broker→runtime boundary. It is never returned to the caller of
`inject_secret`, never written to disk by the runtime engine, and
never included in any event record.

## o. Egress enforcement primitive (spec level, Slice 2I-R)

The egress enforcement primitive confines a worker container's
outbound network traffic to its policy's `egress_allowlist`. The
concrete technology choice is OSD-I-5 (§i.5). This section authors
the behavioral contract all acceptable primitives MUST honor and
names the Slice 2I-R default. No egress primitive is configured or
tested by this spec authoring gate.

### o.1 Default primitive: Pasta

Slice 2I-R designates **Pasta** as the default egress enforcement
primitive. Pasta is a user-space network stack that does not require
`root` or `CAP_NET_ADMIN`; it wraps the container's network namespace
at start time and enforces a forwarding policy before the container's
first packet. Pasta's allowlist is derived from the policy's
`egress_allowlist` field, one forwarding rule per
`(host, port, protocol)` tuple. Rules for the `verification` role's
default empty allowlist result in zero forwarded connections (no
outbound traffic).

Pasta is selected because it is rootless-first, aligns with the
rootless-Podman / rootless-Docker posture of OSD-I-1, and makes the
allowlist observable at the process level without requiring iptables
rules that require elevated privilege.

### o.2 Acceptable equivalent: Slirp4netns with custom configuration

Slirp4netns with a per-deployment outbound filter script is an
acceptable equivalent to Pasta. When Slirp4netns is selected (a
deployment overlay decision recorded in the policy's
`runtime_engine_overlay` field, not a per-policy decision), the
outbound filter script MUST implement the same
`(host, port, protocol)` allowlist semantics as Pasta's forwarding
policy. The filter script path MUST be recorded in the
container-instance record's `enforcement_primitive` field under the
identifier `slirp4netns-allowlist-v1` (or a versioned successor).

### o.3 Invariants regardless of primitive

The following invariants apply to every acceptable primitive:

1. **No hidden flags.** The enforcement primitive MUST NOT be
   configured with undocumented flags or environment variables that
   alter allowlist behavior beyond what the policy's
   `egress_allowlist` declares. Any such deviation is auditable from
   the container-instance record and constitutes a `PCO-040` policy
   violation.

2. **No unrecorded engine flags.** Every non-default flag passed to
   the enforcement primitive at container-start time MUST be recorded
   in the container-instance record's `enforcement_primitive_flags`
   field (an optional string list appended to the network policy
   record). The absence of this field means only default flags were
   used.

3. **Pre-process enforcement.** The allowlist MUST be installed on
   the container's network namespace before any model or tool process
   is exec'd inside the container. `set_network_policy` (§e.5) is the
   syscall that records completion of this step. The runtime engine
   MUST refuse `run_command` for any instance whose
   `set_network_policy` has not yet completed successfully.

4. **Egress violations surfaced as typed events.** When the
   enforcement primitive intercepts a connection attempt to a host
   not on the allowlist, it MUST surface the violation as a typed
   runtime error — not a silent packet drop — that the runtime engine
   records as an `egress_violation` event. The event MUST include
   `instance_id`, `attempted_host`, `attempted_port`, `protocol`,
   and `timestamp`.

5. **Empty allowlist means zero outbound.** The verification role's
   `egress_allowlist` is empty by default (§d.2, §f.5). When the
   allowlist is empty, the primitive MUST configure the network
   namespace for zero outbound connections. An empty allowlist is not
   the same as an unconfigured primitive; the runtime engine MUST
   still call `set_network_policy` and still record the network
   policy record with `egress_allowlist: []`.

## p. Runtime syscall table (Slice 2I-R implementation map)

The table below maps every substrate syscall (§e) to its runtime
engine action, its tracked record, and its gating predicates. Slice
2I-R MUST implement this mapping 1:1. A syscall that completes without
emitting its corresponding tracked record is a runtime contract
violation auditable by the PCO validator.

| Syscall (§e ref) | Runtime engine action | Record emitted | Predicate gating |
|---|---|---|---|
| `allocate_worker` (§e.1) | Container-start under selected policy (rootless Podman or Docker per OSD-I-1; engine read from `policy.runtime_engine`) | Container-instance record (`PCO-041`); `container_started` event | PCO-040 (policy schema); PCO-041 (instance schema); PCO-044 (image SHA); PCO-042 (refusal if no policy matches role) |
| `mount_workspace` (§e.2) | Bind-mount `worktree_path` at declared `mode` (`ro`/`rw`) into container filesystem namespace before process start | `mount_manifest_applied` field on container-instance record | PCO-021 (live lease required); PCO-030 (conflict gate); runtime mount-scope check (no path outside worktree/scratch/governance without `grant_path_capability`) |
| `grant_path_capability` (§e.3) | Extend live container filesystem namespace with one additional bind-mount at declared `mode` | Mount-grant record (one per path, appended to `mount_manifest_applied`; includes `path`, `mode`, `source=grant`, `grant_ref`) | Policy `grant_extensible` field for this mount class; path-escape check (no `..` after normalization; must resolve within worktree realpath); `justification_ref` must resolve |
| `inject_secret` (§e.4) | Call broker `mint` then `inject`; expose value as env var or file inside container | Secret-grant record (one per injection: `secret_name`, `broker_grant_id`, `mode`, `granted_at`, `ttl_seconds`; **value never recorded**) | Policy `secret_allowlist` membership; broker TTL ≤ claim remaining lifetime; hard refusal for controller-key private key regardless of allowlist |
| `set_network_policy` (§e.5) | Configure Pasta (default) or Slirp4netns (§o.2) on container network namespace before first exec | Network policy record (embedded on container-instance record: `allowlist_sha`, `enforcement_primitive` identifier, `enforcement_primitive_flags`); `egress_allowlist_applied` field | Allowlist non-empty OR `egress: none` declared explicitly; primitive must reify every allowlist rule; `run_command` blocked until this call succeeds |
| `run_command` (§e.6) | `exec` argv inside running container via runtime engine API | Command-evidence record (optional; ONLY for ratified-replay scenarios; NOT for ordinary interactive use) | Container in `running` state; `set_network_policy` previously completed; egress violation surfaced as `egress_violation` event on policy miss |
| `collect_artifacts` (§e.7) | Copy `src` from container tmpfs / output bind to `dst` evidence path on host | Artifact-evidence record (one per copy: `instance_id`, `src`, `dst`, `artifact_sha256`) | `dst` within per-claim `evidence/` tree; `src` within container scratch or output tmpfs only |
| `terminate_worker` (§e.8) | Deliver SIGTERM; wait grace period; deliver SIGKILL; reap process group; confirm exit | `container_stopped` event (`instance_id`, `claim_id`, `stopped_at`, `exit_code`, `reason`) | Required before PCO-028 step 3 (`git worktree remove`); `pco-release` refuses to proceed if this call fails to confirm terminal state |
| `garbage_collect_worker` (§e.9) | Deliver SIGKILL to process group of orphaned instance; confirm exit | `container_force_reaped` event (`instance_id`, `claim_id`, `force_reaped_at`, `elapsed_since_release_seconds`) | PCO-043 condition (container-instance record for released claim, no terminal event); invoked by periodic sweeper only |

## q. Non-goals (Slice 2I-R spec authoring gate)

This gate is spec authoring only. It explicitly does NOT produce:

* **No runtime implementation.** No `pco-allocate` / `pco-release`
  source code is written, modified, or authorized. The extension
  contracts in §l are behavioral specifications; their implementation
  is the separately ratified Slice 2I-R implementation gate.

* **No container image build.** No Dockerfile, Containerfile, image
  build pipeline, image registry push, or `podman pull` / `docker
  pull` is executed. Image SHA references in §p are illustrative of
  what the runtime engine will do at implementation time; no actual
  image exists at this gate.

* **No container execution.** No `podman run`, `docker run`, or
  equivalent container-start command is invoked. No container engine
  socket is contacted.

* **No credential issuance.** No PAT, GitHub App installation token,
  or API key is minted, stored, injected, or revoked. The credential
  broker contract in §n is behavioral specification; no broker process
  is started or called.

* **No schema implementation.** The record shapes cited in §e.10 and
  refined in §l–§p are prose-level contracts. The concrete JSON
  Schema / YAML Schema files, example records, and validator check
  implementations are Slice 2I-R implementation-gate deliverables.

* **No egress primitive configuration.** No Pasta process, no
  Slirp4netns configuration, no iptables rule, and no network
  namespace is created or modified.

* **No Hermes-side mutation.** This gate edits only the two
  authorized tracked write surfaces. No Hermes profile, hook,
  MCP server configuration, model-provider setting, or runtime
  config file is touched.

* **No autonomy expansion.** PCO-032 remains in force. Every future
  Slice 2I-R runtime mutation descends from a Source-ratified
  Assignment Envelope; the Controller remains the only process
  authorized to allocate or release workers; worker containers do
  not acquire Controller authority. This spec does not change those
  constraints.

* **No schema implementation edits to existing artifacts.** Existing
  `schemas/`, `validators/`, `examples/`, `tests/`, and `bin/` trees
  are untouched.

## r. Acceptance posture (Slice 2I-R spec)

A fresh-clone reviewer can verify the following from this Slice 2I-R
spec section together with the Slice 2I-S substrate above and the
parent spec:

1. §l.1 and §l.2 together name the exact insertion point in PCO-027
   and PCO-028 respectively, include a numbered sub-step sequence,
   and specify the failure mode (extended rollback in §l.1; refusal
   on unverifiable terminal state in §l.2). The extensions are
   conditional on the presence of policy records and do not break
   pre-Slice-2I-R trees.

2. §m.1 and §m.2 refine PCO-042 and PCO-043 to the level of a
   validator implementation spec: traversal order, backward-
   compatibility floor (§m.1 point 2), structured violation output
   (§m.1 point 4), and sweeper-vs-validator state distinction
   (§m.2 point 4).

3. §n specifies what the credential broker MUST do (mint, withhold,
   never pass `GH_TOKEN`, revoke synchronously, never record values)
   and what it MUST NOT do (pass the controller-key, pass
   `GH_TOKEN`, persist values), at a level that an OSD-I-4
   technology choice can be evaluated against.

4. §o specifies what the egress enforcement primitive MUST do (apply
   the allowlist before first exec, surface violations as typed
   events, treat empty allowlist as zero-outbound), names Pasta as
   the Slice 2I-R default, and names Slirp4netns with custom
   configuration as an acceptable equivalent. No Slirp4netns or
   Pasta binary is invoked by this gate.

5. §p maps each of the nine substrate syscalls (§e) to exactly one
   runtime engine action and exactly one tracked record. The mapping
   is 1:1; no syscall produces zero records.

6. §q confirms that this gate produces no runtime code, no container
   image, no container execution, no credential issuance, no schema
   implementation, no egress primitive configuration, no Hermes-side
   mutation, and no autonomy expansion.
