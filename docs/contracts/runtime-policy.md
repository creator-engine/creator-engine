# Contract: Runtime Policy Record

Gate: v3 **G-1.0** — the runtime-policy substrate (first slice of G-1,
plane C / runtime safety).
Validator check: `ce_runtime_policy`
Schema: `schemas/runtime-policy.schema.yaml`
Keep-and-translate provenance:
[`../operations/WORKER_CONTAINER_PROTOCOL.md`](../operations/WORKER_CONTAINER_PROTOCOL.md)
and `schemas/worker-container-policy.schema.yaml` (PCO Slice 2I-S).

## Purpose

A Runtime Policy Record is the machine-readable, declarative isolation
contract for one Creator Engine agent seat — the *plane-C* (runtime
safety) record shape. A reader with only a fresh clone must be able to
read this record and answer:

- which seat role the policy governs (`role`) and which runner backend
  it is provisioned under (`isolation_backend`);
- which exact image the runtime runs, bound by digest (`image_ref`);
- which paths are bound into the runtime and at what mode
  (`mount_manifest`, default-deny, read-only unless justified);
- what egress the seat is permitted, if any (`egress_allowlist`,
  deny-by-default, with a per-endpoint L4/L7 assurance axis);
- which secrets the runtime may inject, by name only
  (`secret_allowlist`); and
- whether and by whose authority the mount manifest may be extended at
  runtime (`grant_extensible`, `grant_authority`).

This contract is **defensive**: it hardens the Creator Engine's own
agent runtime. It is never an offensive capability.

## Relationship to v2 and the secure-runtime architect report

This schema is the v3 plane-C translation of the kept v2
worker-container contract. The secure-runtime architect report's seed
reconciliation directs: **adopt-and-drop** the v2 `worker_runtime.py`
runtime wiring, and **keep-and-translate** the v2
`worker-container-policy.schema.yaml` record shape into a v3
`ce_runtime_policy` dogfood check.

| Upstream source of truth | Role |
|---|---|
| [`../operations/WORKER_CONTAINER_PROTOCOL.md`](../operations/WORKER_CONTAINER_PROTOCOL.md) | v2 prose contract whose record shape this contract lifts (PCO Slice 2I-S, PCO-040 / PCO-045). |
| `schemas/worker-container-policy.schema.yaml` | v2 machine schema this schema translates. Left untouched here; its adopt-and-drop / deprecation is a later ordered step, NOT part of G-1.0. |
| `schemas/runtime-policy.schema.yaml` | The v3 machine schema this contract governs. |

### What is carried, dropped, and added

- **Carried** (lifted from worker-container): `policy_id` / `policy_sha`,
  `role`, the digest-pinned `image_ref`, the default-deny
  `mount_manifest` (read-only unless `rw` + `write_justification`), the
  deny-by-default `egress_allowlist`, the names-only `secret_allowlist`,
  and the `grant_extensible` / `grant_authority` surface.
- **Dropped** (adopt-and-drop): the v2 `runtime_engine`
  `[podman-rootless, docker-rootless]` axis is not carried.
- **Added** (v3 plane-C): the `isolation_backend`
  `[gvisor-proxy, docker, openshell, os-native]` selector (`docker` is
  the plain-Docker contained backend for tenant hosts without the DGX
  runsc runtime; `os-native` is the
  ce-ops#71 Tranche-1 unprivileged-default DIRECTION, shipped as a
  fail-closed scaffold; `default:` stays `gvisor-proxy`), and the
  per-endpoint egress
  `assurance` (L4 / L7) + optional `binary_identity` (calling-binary)
  axis and `tls_terminated` flag from the secure-runtime egress
  contract.

## Required fields

All required fields MUST be present. Stricter type rules below apply.

| Field | Type | Rule |
|---|---|---|
| `kind` | const | fixed to `runtime-policy-record`; the discriminator. Records without it are not governed by this contract. |
| `record_type` | const | fixed to `runtime_policy`. |
| `schema_version` | enum | `"1"` for G-1.0. |
| `policy_id` | string | slug `^[a-z][a-z0-9-]{2,63}$`. |
| `policy_sha` | string | 64 lowercase hex characters. |
| `role` | enum | one of `architect_research`, `implementer`, `verification`, `controller`. The `controller` addition is an additive governance-contract change for launch-default policy records. |
| `image_ref` | object | `name` required; `sha` (`sha256:<hex64>`) enforced as a digest pin by the check. |
| `mount_manifest` | array<object> | each entry `{path, mode}` with `write_justification` required when `mode: rw`. |
| `egress_allowlist` | array<object> | each entry `{host, ...}`; an empty array declares no egress (the safe floor). |
| `secret_allowlist` | array<string> | bare secret names only. |
| `grant_extensible` | boolean | whether the mount manifest may be extended at runtime. |
| `grant_authority` | enum | `controller` or `source`. |

`unevaluatedProperties: false` applies at every object level; any field
not listed in the schema is a contract violation.

`isolation_backend` is **optional** (ce-ops#71 MINOR-A): one of
`gvisor-proxy` (the conservative default), `docker`, `openshell`, `local-noop`
(the inert registered backend for dry-run/foundation wiring), or
`os-native` (the unprivileged-default scaffold, fail-closed). `docker`
uses the policy's digest-pinned `image_ref`, adds no Docker `--runtime=`
flag, and only bind-mounts paths from `mount_manifest`. A Draft 2020-12
validator does not inject the schema `default`, so the field is *not*
required — an omitted field validates clean and
the runtime resolver supplies the fail-closed default (`gvisor-proxy`),
which is what actually keeps a pre-#71 record on today's backend.

## Safety predicates

Beyond schema validation, the `ce_runtime_policy` check enforces the
runtime-policy safety predicates with explicit, contract-cited error
classes. Each translates a v2 PCO-040 / PCO-045 safety default into the
v3 plane-C contract:

| Error class | Condition refused |
|---|---|
| `runtime_policy_image_not_digest_pinned` | `image_ref.sha` is absent or is not a `sha256:<hex64>` digest. An unpinned image is refused — the runtime MUST run an exact, content-addressed image. |
| `runtime_policy_image_name_carries_credential` | `image_ref.name` carries userinfo / an embedded `@` / token-shaped credential material. |
| `runtime_policy_forbidden_mount` | a mount path under the host home directory (`~` / `$HOME`), a container-engine socket (`docker.sock` / `podman.sock`), or an SSH/GPG agent socket (`.ssh` / `.gnupg` / `*-agent`). *(translates PCO-045)* |
| `runtime_policy_rw_mount_without_justification` | a `mode: rw` mount without a `write_justification`. |
| `runtime_policy_secret_names_only_violation` | a `secret_allowlist` entry that is a path or value, or that names the controller-key private key or any private-key-shaped secret. *(translates PCO-045)* |
| `runtime_policy_egress_not_deny_by_default` | an egress rule missing `host`, or an `l7`-assured rule that does not set `tls_terminated: true`. |

Every failure cites the offending error class, the field/path that
violated it, and this contract document.

### Non-negotiable invariants

- **Controller-key prohibition.** The controller-key private key MUST
  NOT appear in `secret_allowlist` and MUST NOT be injected into any
  runtime. Agent seats never sign leases; only the Controller signs.
  This is the strongest mechanical binding of controller identity
  outside the seat.
- **Deny-by-default egress.** Egress is denied unless explicitly
  allowlisted. An empty `egress_allowlist` is valid and means *no
  egress*. An `l7`-assured endpoint MUST terminate TLS at the egress
  proxy (`tls_terminated: true`).
- **Default-deny mounts, read-only floor.** Only listed paths are
  bound; write access is the justified exception, never the default.
- **Digest-pinned images.** The runtime runs an exact, content-
  addressed image — never a mutable tag alone.

These invariants are never weakened. They harden the agent runtime
against exfiltration and host-credential capture; they are defensive
safeguards, not offensive capabilities.

## G-1.0 boundary and the G-1 roadmap

G-1.0 defines the *record shape and its validation* only. It does NOT
allocate a container, invoke gVisor / Podman / Docker / OpenShell,
build or push images, open a network socket, or implement an egress
proxy or a credential broker. It mirrors the original Slice 2I-S
"record-shape-only" boundary.

The remaining G-1 slices ship as separately ratified batch-strict-mode
steps:

- **G-1.1 — runner-backend adapter interface.** The `RunnerBackend`
  abstraction + provision/run/collect/teardown data model + registry +
  a no-op/local test backend. Pure interface; no live container.
- **G-1.2 — first live backend.** A hardened gVisor container paired
  with a capability-separation egress proxy; translates a runtime
  policy into backend configuration.
- **G-1.3 — classifier/audit overlay + evidence spine.** An advisory
  classifier/audit overlay plus hash-chained evidence-spine
  integration. An OpenShell backend is a later fast-follow behind the
  same adapter.

## Validator behavior

The `ce_runtime_policy` check discovers candidate records by file shape
(`.yml` / `.yaml`, not under `schemas/` or `templates/`, not an
atomic-write temp file) and `kind == runtime-policy-record`, then
validates each candidate against `schemas/runtime-policy.schema.yaml`
and applies the safety predicates above. Records carrying any other
`kind` are ignored (no-op). The check is reachable discretely via the
`scan-runtime-policy` CLI subcommand and runs as part of the full
`check` sweep.

## v3 G-4 — agent-action gate fields (additive, optional)

G-4 adds two OPTIONAL plane-C fields the audit-overlay
classifier/control-point consume at runtime. Both are additive: a record
that omits them is a valid G-1.0 policy (the runtime simply grants no
agent-action cells and falls back to the safe `ask` gate mode). The
`ce_runtime_policy` check validates their **shape** only; the gate
*semantics* live in `runner.audit_overlay` (`classify` / `decide`) — see
[`docs/architecture/agent-interaction-model.md`](../architecture/agent-interaction-model.md).

- **`action_class_allowlist`** — a list of `{op, mutation_class}` grants.
  Each grant authorizes one `(op, mutation_class)` cell: the cells a
  *faithfully-observed* mutating agent action may perform without
  escalation. Deny-by-default — a mutating op whose cell is absent is
  denied; reads are never gated. `op` is the capability axis
  (`read`/`write`/`exec`/`egress`/`secret`/`vcs`); `mutation_class` is the
  shared planning-layer taxonomy plus `none`. Shape only — never a host,
  path, credential, or account identifier.
- **`gate_mode_ladder`** — the gate-mode ladder `decide()` resolves:
  `default_mode` (`deny`/`allowlist`/`ask`/`auto`/`full`), optional
  per-cell `cells` overrides, and `always_*` precedence `rules`
  (`always_deny` > `always_confirm` > `always_allow`, all beaten by the
  hard-coded built-in deny tier). `auto` is advisory-only — it may
  downgrade an escalate→allow but never authorizes a deny-class action.
  Rules carry the Lobster separation-of-duties fields
  (`require_different_approver` / `initiated_by` / `approved_by`) as shape
  only.

## v3 G-5 — tokenomics spend fields (additive, optional)

G-5 adds OPTIONAL plane-C spend-governance fields. All are additive: a record
that omits them is a valid G-1.0/G-4 policy (no spend governance). The
`ce_runtime_policy` check validates their **shape**; the cross-envelope
*semantics* are enforced by `ce_spend_envelope` and the gate runtime lives in
`runner.spend_gate` — see [`docs/contracts/spend-envelope.md`](spend-envelope.md).

- **`spend_envelopes`** — the nested deny-by-default envelopes (`global` ->
  `fleet` -> `run`, most-restrictive-wins). Each is `{scope, amount, unit, window}`
  (+ optional `reset_anchor` / `fleet_id`). A `global` `$` ceiling is mandatory
  whenever any `$` envelope is declared (the anti-catastrophe backstop). Two
  regimes: `$` = API-USD (fleet); `%` = single-seat subscription meter (`run`-scoped
  only, never a fleet). Shape only — never a host / credential / account identifier.
- **`max_concurrent_runs`** — the concurrency envelope dimension (a semaphore
  ceiling). Over-limit admission yields `throttle` (retry), distinct from
  `budget_exhausted` (no retry).
- **`model_rates`** — the per-model API-USD rate table the `$` regime meters
  against. **Read live, never hardcoded** — prices live in policy (re-read each run)
  because vendor rates/caps drift.
- **`spend_cap_enforcement`** (`enforce` | `off`, default `enforce`) +
  **`spend_cap_optout`** — the cost-enforcement opt-out: a ratified-HUMAN-only
  choice (an agent can never set it). `off` disables the sub-allocated CAPS but never
  the runaway-DETECTION net (the mandatory global ceiling + anomaly → escalate), and
  REQUIRES a `spend_cap_optout` `{ratified_prompt_sha, approver_ref}` binding.

## v3.5-F - resource envelopes and §4.4 host classes

v3.5-F adds optional `resource_envelopes`, `resource_enforcement`, and
`resource_optout` fields. These fields are materialized into the runtime policy
by the installer / `ce doctor`; launch paths read the policy fragment and never
compute host caps silently.

The §4.4 default materialization is a pure function of `MemTotal`:

| Host class | Boundary | Seat envelope | Fleet envelope |
|---|---:|---|---|
| `large-host-30g` | `MemTotal >= 24 GiB` | `memory_high: 5500M`, `memory_max: 6G`, `memory_swap_max: 256M`, `tasks_max: 512`, `cpu_weight: 100`, `cpu_quota: "400%"` | `memory_max: 20G` |
| `desktop-14g` | `12 GiB <= MemTotal < 24 GiB` | `memory_high: 3500M`, `memory_max: 4G`, `memory_swap_max: 256M`, `tasks_max: 512`, `cpu_weight: 100` | `memory_max: 9G` |
| `small-host-8g` | `MemTotal < 12 GiB` | `memory_high: 2G`, `memory_max: 2500M`, `memory_swap_max: 128M`, `tasks_max: 512`, `cpu_weight: 100` | `memory_max: 5500M` |

The `large-host-30g` class is for a headless 30 GiB development host: a 6G
seat ceiling leaves room for several bounded seats and full-suite headroom,
while the 20G fleet cap leaves at least 10G for page cache and host services.
`cpu_quota: "400%"` caps one seat at four CPU cores so a runaway seat cannot
starve the fleet.
