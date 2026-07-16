# Worker-Container Protocol

**Slice**: PCO Slice 2I-S (Worker Isolation Runtime — Substrate)
**Status**: Substrate-only (record contracts, refusal predicates, safety
defaults). Runtime implementation is deferred to Slice 2I-R.
**Spec companion**:
`specs/005-pco-parallel-controller-orchestration/worker-isolation-runtime.md`
**Architectural companion**:
`docs/architecture/parallel-controller-orchestration.md`

---

## 1. Purpose

Slice 2I-S authors the substrate contracts for worker-container
isolation in the Creator Engine. Every subsequent PCO slice (Slices 3,
4, 5, 6) and every team-mode workstream (Features 007, 008, 009) is
authored against this substrate.

This protocol documents:

1. The two tracked record kinds added by Slice 2I-S: **Worker-Container
   Policy** and **Container-Instance**.
2. The additive extension to the Active-Work Ledger schema
   (`schema_version: "3"`, three new event kinds).
3. The six refusal predicates (`PCO-040` through `PCO-045`), with the
   validator check that enforces each.
4. The OSD decisions binding this implementation.
5. Explicit non-goals.

---

## 2. Record Kinds

### 2a. Worker-Container Policy Record

**Schema**: `schemas/worker-container-policy.schema.yaml`
**Validator check**: `validators/creator_engine_validator/checks/worker_container_policy.py`
**Kind discriminator**: `kind: worker-container-policy-record`
**Predicate codes**: `PCO-040` (schema), `PCO-045` (forbidden mount / secret)

A Worker-Container Policy record declares the isolation posture for one
named worker role. It is a tracked, Source-ratified artifact — not a
deployment secret or a runtime config file.

**Required fields**:

| Field | Purpose |
|---|---|
| `policy_id` | Stable slug identifier for this policy version. |
| `policy_sha` | SHA256 hex of the canonical policy record. Bound into container-instance records. |
| `role` | One of `architect_research`, `implementer`, `verification`. |
| `runtime_engine` | `podman-rootless` (canonical v1) or `docker-rootless` (deployment overlay). |
| `image_ref.name` | OCI image name (shape only; deployment overlay). |
| `image_ref.sha` | Content-addressable image digest (`sha256:<hex64>`). Used by `PCO-044`. |
| `mount_manifest` | Ordered list of paths to bind into the container. Default-deny. |
| `egress_allowlist` | Per-rule egress shape. Empty array = no egress. |
| `secret_allowlist` | Secret names (no values) allowed for injection. |
| `grant_extensible` | Whether runtime mount extensions are permitted. |
| `grant_authority` | `controller` or `source` per OSD-I-7. |

**Per-role defaults** (from spec §d.2):

| Role | Mount default | Egress default | Credential default |
|---|---|---|---|
| `architect_research` | Read-only allocated worktree + read-only `governance/` | Model-provider + documentation/web + source-host read API | Model-provider key; no write tokens; no SSH; no controller-key |
| `implementer` | Read-write one allocated worktree + read-only `governance/` | Model-provider + dependency-registry + source-host write API (per-task PAT) | Model-provider key; per-task scoped PAT; no SSH; no controller-key |
| `verification` | Read-only allocated worktree + read-only `governance/` | None by default | None by default |

### 2b. Container-Instance Record

**Schema**: `schemas/container-instance.schema.yaml`
**Validator check**: `validators/creator_engine_validator/checks/container_instance.py`
**Kind discriminator**: `kind: container-instance-record`
**Predicate codes**: `PCO-041` (schema), `PCO-043` (outlives claim), `PCO-044` (image SHA mismatch)

A Container-Instance record captures the runtime state of one allocated
worker container. It is written by `allocate_worker` (Slice 2I-R) and
updated by `terminate_worker` / `garbage_collect_worker`.

**Required fields**:

| Field | Purpose |
|---|---|
| `instance_id` | Stable slug per container instance. |
| `policy_ref.policy_id` | Policy that governs this instance. |
| `policy_ref.policy_sha` | Exact policy version in force at `allocate_worker`. |
| `policy_ref.image_sha` | Image SHA from the policy at allocation time. Used by `PCO-044`. |
| `image_sha` | Actual image SHA used at container start. |
| `claim_id` | Bound Active-Work Ledger claim. |
| `lease_id` | Worktree Lease live at allocation. |
| `started_at` | Container start timestamp. |
| `stopped_at` | Container stop timestamp, or `null` while running. Used by `PCO-043`. |
| `exit_code` | Main process exit code, or `null` while running. |
| `mount_manifest_applied` | Applied mount entries (path, mode, source). |
| `secret_grants` | Injected secrets: names, modes, broker-grant ids, TTLs. **No values.** |
| `egress_allowlist_applied` | Applied egress rules. |
| `enforcement_primitive` | `pasta`, `slirp4netns`, `iptables`, `none`, or `unknown`. |
| `policy_sha` | Top-level policy SHA for fast audit lookups (= `policy_ref.policy_sha`). |

**Optional fields**:

| Field | Purpose |
|---|---|
| `claim_released_at` | Claim release timestamp; when set with `stopped_at: null` triggers `PCO-043`. |
| `note` | Advisory text. No secrets. |

**Secret-grant entries** (`secret_grants` array) MUST NOT contain a
`secret_value` or equivalent field. The schema enforces this via
`unevaluatedProperties: false` on each entry.

### 2c. Active-Work Ledger Extension (Slice 2I-S, schema_version "3")

**Schema**: `schemas/active-work-ledger.schema.yaml`
**Validator check**: `validators/creator_engine_validator/checks/active_work_ledger_schema.py`

Three container event kinds are added additively:

| Event kind | Emitted by | Details fields |
|---|---|---|
| `container_started` | `allocate_worker` | `instance_id`, `claim_id`, `summary` |
| `container_stopped` | `terminate_worker` | `instance_id`, `claim_id`, `exit_code`, `reason`, `summary` |
| `container_force_reaped` | `garbage_collect_worker` | `instance_id`, `claim_id`, `reason`, `elapsed_since_release_seconds`, `summary` |

`reason` enum for `container_stopped` and `container_force_reaped`:
`normal_release`, `claim_lapsed`, `validator_refusal`, `operator_abort`,
`force_reap`.

Prior `schema_version: "1"` and `"2"` records continue to validate
unchanged. Container event kinds require `schema_version: "3"`.

---

## 3. Refusal Predicates

### PCO-040 — Worker-Container Policy Schema

**Check**: `worker_container_policy` (`CODE_SCHEMA = "PCO-040"`)
**Surface**: every file with `kind: worker-container-policy-record`

Every Worker-Container Policy record MUST validate against
`schemas/worker-container-policy.schema.yaml`. Failures cite `PCO-040`
and name the violated field.

### PCO-041 — Container-Instance Record Schema

**Check**: `container_instance` (`CODE_SCHEMA = "PCO-041"`)
**Surface**: every file with `kind: container-instance-record`

Every Container-Instance record MUST validate against
`schemas/container-instance.schema.yaml`. Structural failures (not a
YAML mapping) are distinguished from schema failures. Failures cite
`PCO-041` and name the violated field.

### PCO-042 — Container Required for Claim (Slice 2I-R, SHIPPED)

**Check**: `active_work_ledger_conflicts` (`CODE_CONTAINER_REQUIRED = "PCO-042"`)
**Surface**: cross-record (claims × policies × container-instances)

Shipped by Slice 2I-R (this gate). PCO-042 refuses a **live** claim
record (one whose `released_at` is null) that has no paired **running**
container-instance record — a container-instance whose `claim_id`
equals the claim's `lane_id` and whose `stopped_at` is null.

**Arming gate (governance path).** PCO-042 only fires when the scanned
tree contains at least one `PCO-040`-valid worker-container policy
record under the **ratified governance path**
`governance/policies/worker-container/` (§g.1). Trees without such a
policy preserve Slice 2R behavior unchanged (the same
backward-compatibility floor pattern as `PCO-026`). Worker-container
policy records that live elsewhere — notably the illustrative
`examples/…` fixtures — do **not** arm PCO-042; this is exactly why
`check examples/well-formed` stays green even though it bundles policies
and unpaired live claims in one scanned tree.

Each violation names the offending `claim_id`, `lane_id`, and
`controller_id` and exits `active_work_ledger_conflicts` non-zero. The
allocate-time refusal (no matching policy for the role) is enforced by
the `allocate_worker` runtime; the static cross-record refusal here is
the auditable surface.

### PCO-043 — Container Outlives Claim

**Check**: `container_instance` (`CODE_OUTLIVES_CLAIM = "PCO-043"`)
**Surface**: every Container-Instance record

Refuses a container-instance record where:
- `claim_released_at` is present (the bound claim was released), AND
- `stopped_at` is `null` (the container is still running).

This is the static substrate surface that backs the
`garbage_collect_worker` sweeper (spec §e.9). When PCO-043 fires the
sweeper MUST call `terminate_worker` on the identified instance.

### PCO-044 — Image SHA Matches Policy

**Check**: `container_instance` (`CODE_IMAGE_SHA_MISMATCH = "PCO-044"`)
**Surface**: every Container-Instance record

Refuses a container-instance record where `image_sha` ≠
`policy_ref.image_sha`. The allocator MUST NOT substitute a different
image after the policy was ratified; a mismatch proves substitution
occurred.

### PCO-045 — Forbidden Mount Refusal

**Check**: `worker_container_policy` (`CODE_FORBIDDEN_MOUNT = "PCO-045"`)
**Surface**: every Worker-Container Policy record

Refuses any policy whose mount manifest or secret allowlist violates
the Slice 2I-S safety floor:

**Forbidden mount paths**:
- `$HOME`-prefixed or `~/`-prefixed paths (host home directory; spec §f.2)
- `/var/run/docker.sock`, `/run/docker.sock` (Docker socket)
- `/run/podman/podman.sock`, `/var/run/podman/podman.sock` (Podman socket)
- Any path whose basename matches `podman.sock` (covers `XDG_RUNTIME_DIR`
  variants; spec §f.4)

**Forbidden secret names**:
- Any name matching `controller.{0,10}key` (case-insensitive) — covers
  `controller-private-key`, `hermes-controller-key`, etc. (spec §f.3)

`PCO-045` is the single schema-level boundary against the most-violated
container anti-patterns. It is a defense-in-depth predicate: the
runtime engine MUST enforce the same rules at allocation time; the
schema check catches mis-authored policies before they reach the
allocator.

---

## 4. OSD Decisions Binding This Implementation

The following OSD decisions from the architect report and Slice 2I-S
spec are binding for this substrate implementation:

| Decision | Binding choice | Spec ref |
|---|---|---|
| OSD-I-1 Runtime engine | `podman-rootless` canonical; `docker-rootless` overlay | §i.1 |
| OSD-I-3 Controller containerization | Deferred; Controller stays on host | §i.3 |
| OSD-I-7 Mount-grant authority | Per-grant rule in policy; governance-class requires Source (FR-008) | §i.7 |
| Non-negotiable | Controller-key private key MUST NOT be injected into any worker | §f.3 |

Decisions OSD-I-2 (image baseline), OSD-I-4 (credential broker),
OSD-I-5 (egress enforcement primitive), OSD-I-6 (image separation by
role), and OSD-1 (per-container ephemeral controller-key candidate) are
not yet resolved and are deferred to Slice 2I-R / Slice 2.5+2R.

---

## 5. Non-Goals

The following are explicitly NOT implemented by Slice 2I-S:

- **No container runtime**: no `podman run`, `docker run`, `systemd-nspawn`,
  or equivalent command is issued by this substrate.
- **No image authoring**: no Dockerfile, Containerfile, image build,
  push, pull, or registry interaction.
- **No credential broker implementation**: `inject_secret` is defined as
  a syscall contract; the broker is a Slice 2I-R deliverable.
- **No `PCO-042` enforcement** *(superseded — shipped in Slice 2I-R)*: the
  "container required for claim" predicate is shipped in the
  `active_work_ledger_conflicts` check by Slice 2I-R (governance-path-armed,
  §m.1). Slice 2I-S itself ships no such check.
- **No Slice 2.5 controller-key schema/checks**: those remain in the
  separately authorized Slice 2.5 gate.
- **No Slice 2R allocator changes**: `pco-allocate` and `pco-release`
  runtime code is unchanged; the allocator extension is Slice 2I-R.
- **No Hermes runtime mutation**: no profile, hook, config, plugin, MCP,
  model, or provider state is modified.
- **No runtime Active-Work Ledger records**: this substrate validates
  record shapes; it does not write `.hermes/active-work-ledger/` records.
- **No deployment host inventory in egress rules**: the `egress_allowlist`
  records rule shape only; concrete hosts are deployment-time overlay.

---

## 6. Predicate Mapping

| Predicate | Validator check | FR/code | Scope |
|---|---|---|---|
| Worker-container policy schema | `worker_container_policy` | PCO-040 | Single policy record |
| Container-instance record schema | `container_instance` | PCO-041 | Single instance record |
| Container required for claim | `active_work_ledger_conflicts` | PCO-042 | Cross-record (governance-path-armed) |
| Container outlives claim | `container_instance` | PCO-043 | Single instance record |
| Image SHA matches policy | `container_instance` | PCO-044 | Single instance record |
| Forbidden mount refusal | `worker_container_policy` | PCO-045 | Single policy record |
| Secret value leak (runtime refusal) | `worker_runtime` (`G5-SECRET-REFUSED`) | runtime | Runtime allocate/terminate |

## 7. `ce worker` runtime surface (Slice 2I-R)

The `worker_runtime` module + `ce worker` command family turn the substrate
above into a local runtime:

| Command | Entry point | Behavior |
|---|---|---|
| `ce worker allocate` | `allocate_worker` (§e.1) | bind a live claim + lease under a ratified policy; rootless `podman run --detach` via an injectable runner; write a `PCO-041/043/044`-valid container-instance record after start; record a `container_started` side effect |
| `ce worker terminate` | `terminate_worker` (§e.8) | revoke broker grants, stop the container, write the stopped record, record a `container_stopped` side effect |
| `ce worker gc` | `garbage_collect_worker` (§e.9) | reap container-instance records that hit the PCO-043 condition; update them deterministically |
| `ce worker status` | local read | read a single container-instance record (read-only) |
| `ce worker spawn` | `worker_spawn.spawn_worker` | spawn a harness-agnostic governed worker seat under a scrubbed environment, recording only prompt refs/hashes and value-free launch metadata |
| `ce worker run --role <role> --brief <file>` | `worker_run.run_worker_role` | sanctioned one-call role-brief path: resolve `.claude/agents/<role>.md`, compose `worker_spawn`, wait for the declared findings artifact, and return structured findings |
| `ce worker launch` | `codex_worker_launcher.build_launch_plan` | load the strict checked-in one-shot policy and construct a deterministic external Codex argv; `--dry-run` emits JSON and never invokes a runner |

Runtime invariants: the container engine and credential broker are reached
**only** through injectable seams (`PodmanCommandRunner`, `NullCredentialBroker`);
the live CLI fails closed when `podman` is unavailable (`G5-PODMAN-UNAVAILABLE`);
secret values never enter argv, records, side-effect details, or broker metadata
(names/ids/TTLs only); the controller-key private key is refused
(`G5-CONTROLLER-KEY-REFUSED`); a non-empty egress allowlist with no proven
enforcement primitive is refused before container start (`G5-EGRESS-UNENFORCEABLE`);
and every refusal raises before any side effect.

### 7.1 Policy-bound external Codex one-shots

`ce worker launch` is a narrow, pure-plan-first external Codex seam. Callers provide
`--brief <path> --brief-sha256 <64-lowerhex>` but cannot override policy, binary,
stdin, output, flags, or add-dirs. It loads only `governance/policies/codex-one-shot-launch-v1.yaml`
from the allocated worktree and fails closed on unknown keys, symlinks, escapes, or unreadable non-files.

The same containment rule resolves `.claude/agents/<role>.md` and a regular brief
beneath `.ce/briefs`, whose exact bytes must match the supplied SHA-256. The runner
receives a length-delimited frame of canonical role-policy then exact brief bytes. Plan JSON stores
only canonical paths and digests, never either prompt body.

Production execution never inherits the controller environment wholesale. Each invocation
uses fresh, cleanup-bound `HOME`, `CODEX_HOME`, XDG, and temporary directories; preserves
only the small non-secret runtime allowlist; and admits only provider credential names
explicitly listed for the role by the canonical policy. GitHub, cloud, SSH/GPG agent,
controller/seat socket, and host configuration variables are absent. An execution exception
or nonzero Codex exit is reported as failed/refused; completion is emitted only for zero.

The policy pins Codex `0.145.0-alpha.9`, model, reasoning effort, canonical add-dirs, and this complete matrix:

| Venue | `architect_research` | `implementer` | `reviewer` | `verification` |
|---|---|---|---|---|
| `dgx-relay` | `read-only` | `workspace-write` | `read-only` | `read-only` |
| `dev1-local` | `read-only` | `workspace-write` | `read-only` | `read-only` |
| `vps-tmux` | refused | refused | refused | refused |
| `in-seat` | refused | refused | refused | refused |

Contained `vps-tmux` and `in-seat` cannot prove the required mount/scratch contract,
so every role fails closed pending separately reviewed, machine-verifiable outer-isolation
attestation. Neither `danger-full-access` for read-only roles nor unusable nested
`read-only` for implementers is allowed; this is enforced rather than trusted to prose.

Every plan has this fixed argv order:

```text
<pinned-binary> exec --ephemeral -m <pinned-model> -c model_reasoning_effort=<pinned-effort> \
  -c features.multi_agent=false -c features.multi_agent_v2=false -s <venue-sandbox> -C <worktree> \
  [canonical --add-dir values] -o <deterministic-output> -
```

Before runner construction, the worktree, canonical add-dirs, and `.ce/state` must
be existing real directories without symlink or `..` traversal. The venue-owned
absolute binary must be a regular executable whose final symlink target remains
under its `0.145.0-alpha.9` root; an injectable probe verifies that version, and
deterministic output remains inside the real worktree state root.

This source slice neither starts a container nor performs a live relaunch. Source
validation and merge must precede a separately authorized real-evidence post-land relaunch, which may not be simulated.

### 7.2 `ce worker run` design note and deferrals

`ce worker run --role <role> --brief <file>` is the sanctioned replacement for
ad hoc harness fallback when a controller needs a governed role to answer a
bounded brief. The command resolves only checked-in role files under
`.claude/agents/`, fails closed for missing or unknown roles, composes the
existing `worker_spawn` launch primitive, writes a deterministic prompt under
`.ce/state/worker-runs/<run-id>/prompt.md`, seeds the launched pane with a
pointer-only instruction to read that prompt and write the declared findings
artifact, and collects the worker's YAML/JSON findings artifact. Prompt seeding
and findings collection are injectable, so unit tests exercise the
launch-to-findings round trip offline without a live model, tmux, or network.

Deferred follow-up slices:

- Egress-allowed research lane for `architect_research`: the role definition
  declares `WebFetch`/`WebSearch`, but the governed runtime still needs an
  explicit research-lane egress policy before live web research is enabled.
- Declared-tools-vs-runtime capability probe/reconciliation: the role front
  matter lists tool intent, but this slice records and surfaces it only. A later
  capability probe must compare declared tools against the actual runtime
  harness/tool boundary and fail closed or downgrade when they diverge.
