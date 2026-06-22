# Contract: DevOps Privileged-Action Broker

Gate: ce-ops#185, design/schema only
Schema: `schemas/devops-privileged-action-broker.schema.yaml`
Decision: `docs/decisions/ADR-0011-devops-privileged-action-broker.md`

## Purpose

The DevOps privileged-action broker is the deterministic trust boundary for
root, deploy-adjacent, provider-admin, and other high-blast operational actions.
It lets a contained or governed DevOps agent request privileged work without
holding long-lived secrets or receiving secret material in LLM context.

The core split is:

- **Authority**: a value-free `privileged_action_envelope` records a ratified,
  scoped grant for one task, target, capability, TTL, execution mode, and audit
  plan.
- **Custody**: the broker and OpenBao hold or mint the capability; the agent
  never holds static root/admin secrets.
- **Execution**: the broker proxies high-blast actions and only hands off
  ephemeral capabilities for benign or low-blast work.

This contract is prose plus schema. It does not implement the runtime broker.

## Envelope Fields

The envelope wrapper is `privileged_action_envelope`. Required fields:

| Field | Rule |
| --- | --- |
| `envelope_id` | Stable `pae-*` id. |
| `schema_version` | Current value `"1"`. |
| `task_id` | Governing task, for example `ce-ops#184`. |
| `requester` | CE seat, role, and non-secret actor reference. |
| `capability` | Engine, operation, mount, mode, and value-free capability ref. |
| `target` | Closed target type and non-secret target reference; path/principal when needed. |
| `scope` | Allowed actions, resource refs, constraints, max uses, and egress posture. |
| `ttl_seconds` / `expires_at` | Explicit lifetime. Default design posture is minutes, not hours. |
| `ratification_ref` | Ref plus 64-hex ratified prompt digest and human ratifier role class. |
| `execution` | Custody mode, execution mode, blast radius, irreversibility, and reason. |
| `audit_hooks` | Side-Effect Ledger, OpenBao audit, lease revocation, broker audit, or supervisor audit refs. |
| `lease` | Optional OpenBao lease/accessor/revocation metadata. Values are refs only. |
| `metadata` | Optional non-authority notes. Closed to a fixed allow-list of descriptive keys (`note`, `design_ref`, `openbao_version_basis`, `tool_ref`, `labels`); arbitrary keys such as `password` or `token` are schema-rejected. Secret-shaped values remain prohibited. |

Forbidden anywhere in the envelope: passwords, private keys, SSH private keys,
OpenBao tokens, wrapping tokens, OTP values, dynamic usernames/passwords,
service-account token values, decrypted plaintext, recovery codes, cookies, and
provider API credentials.

### Schema enforcement boundary

The envelope schema enforces these structurally:

- **Closed object shapes.** Every object uses `additionalProperties: false`,
  including `metadata`, which is restricted to the descriptive allow-list above.
  An arbitrary key such as `metadata.password` is rejected. This makes the
  value-free claim structural for envelope shape, not prose-only.
- **High/irreversible work is proxied.** A cross-field rule in `execution`
  forbids `execution_mode: capability-handoff` whenever `blast_radius` is `high`
  or `irreversible`, or whenever `irreversible` is `true`. Such combinations are
  schema-invalid; high or irreversible work must use `broker-proxies`.

The schema is **structural only** for two checks that a deterministic broker
policy MUST run before treating any envelope as broker-valid:

- **Capability coherence.** The `capability.engine`, `capability.operation`, and
  `capability.mode` fields are independent enums, so structurally incoherent
  tuples (for example `engine: openbao_ssh` with `operation: transit_decrypt` and
  `mode: service_account_token`) still pass the schema. Encoding every valid
  engine/operation/mode tuple in JSON Schema would be large and brittle, so the
  broker policy core validates capability coherence before acceptance and denies
  incoherent tuples.
- **Semantic secret scanning.** The closed `metadata` allow-list still permits
  free-form scalar values under descriptive keys, so a semantic secret-scanner
  validator MUST run before broker-acceptance to reject secret-shaped values that
  the schema cannot detect by shape alone.

These two policy checks are the "Envelope validator slice" and "Policy core
slice" listed under Implementation Slices.

## Broker Architecture

The broker runs in its own container and trust domain. The DevOps agent may
submit a request and receive evidence, but does not share the broker's OpenBao
token, SSH key material, tmpfs secret file, or execution environment.

Request/validate/mint/execute/return flow:

1. **Request**: a governed agent or controller submits a
   `privileged_action_envelope` reference and value-free task inputs.
2. **Validate**: the broker validates the schema, ratification ref, task binding,
   target, TTL, blast-radius grade, custody mode, execution mode, and audit hooks.
   Any missing or mismatched field is a denial before OpenBao I/O.
3. **Mint or obtain**: the broker calls OpenBao for the requested ephemeral
   capability. Preferred operations are leaseable or operation-scoped and avoid
   returning private key material.
4. **Execute**: for high or irreversible blast radius, the broker proxies the
   operation itself. For benign or low blast radius, it may hand a short-lived
   capability to a deterministic sidecar or tool.
5. **Return**: the broker returns redaction-safe result metadata: effect status,
   evidence refs, lease refs, hashes, and audit record ids. It never returns
   secret values to the LLM.
6. **Revoke/audit**: the broker records Side-Effect Ledger evidence and lease
   revocation or expiry evidence. Revocation failure is itself a side-effect
   record and a follow-up blocker.

## Placement Against Existing Brokers

This broker is separate from the existing CE broker surfaces:

| Component | Holds or mediates | Not responsible for |
| --- | --- | --- |
| OpenBao SecretIdentityBackend / secret-zero broker | Per-seat OpenBao auth, response-wrapped SecretID delivery, value-free grants | Root action policy or execution |
| Mint-broker (ce-ops#157 / PR #300) | Bounded forge token minting after binding and permission-ceiling checks | Root host actions, deploys, OpenBao SSH certs, provider admin |
| Egress broker / ADR-0007 | Forge transport for signed commits and PR creation without agent egress | Runtime/root operation execution |
| DevOps privileged-action broker | Ratified privileged runtime actions with OpenBao ephemeral capabilities | General forge publishing, merge, or long-lived secret storage |

The containment boundary is intentional: an LLM can request and explain, while a
deterministic broker validates and acts.

## Design Forks

### Custody

Default: `broker-mints-ephemeral`.

The broker uses OpenBao to mint, sign, wrap, or operate with the minimum
capability needed for one envelope. Examples include SSH signed certificates,
one-time SSH passwords, Transit sign/verify/encrypt/decrypt operations, dynamic
database credentials, Kubernetes service-account tokens, RabbitMQ dynamic users,
and response-wrapped payload delivery.

Fallback: `sidecar-templates-real-secret-into-tmpfs`.

This is allowed only when a required tool cannot consume a dynamic capability or
broker-proxied operation. The sidecar runs in the broker trust domain, writes to
RAM-backed storage only, avoids argv and log exposure, makes the file readable
only to the exact tool process, and deletes it on completion or TTL expiry. The
agent receives only evidence refs.

### Execution

Default for high-blast work: `broker-proxies`.

The broker executes and returns evidence for root writes, irreversible config,
deploy or rollback, provider-admin mutation, destructive database operations,
Transit decrypt that could expose plaintext, and any action whose failure could
break a host, service, or security boundary.

Allowed for low-blast work: `capability-handoff`.

Capability handoff is limited to benign or low-blast operations where the
capability is short-lived, scope-bound, and safe to expose to a deterministic
tool or sidecar. It is not a path for putting secrets into prompts, transcripts,
issue comments, or general shell history.

Blast-radius grading:

| Grade | Examples | Execution default |
| --- | --- | --- |
| `benign` | Read-only status query, non-secret metadata lookup | `capability-handoff` allowed |
| `low` | Single scoped dynamic credential for a disposable test resource | `capability-handoff` allowed with audit |
| `medium` | Restart of non-critical service, bounded write to staging | `broker-proxies` preferred |
| `high` | Root host write, production config, deploy, broad provider mutation | `broker-proxies` required |
| `irreversible` | Destructive data/provider/security mutation, non-rollbackable action | `broker-proxies` plus separate ratification |

## Threat Model

Threat 1: secret exfiltration through LLM context, prompt injection, logs, argv,
memory persistence, transcripts, issue comments, or side-effect evidence.

Mitigations:

- Envelopes are value-free and schema-bounded.
- Default custody mints ephemeral capabilities in the broker domain.
- SSH uses signed public keys where possible, not returned private key material.
- Transit decrypt/plaintext operations are broker-proxied; plaintext is not
  returned to an LLM context.
- Response wrapping and cubbyhole are used for relay and tamper/lifetime
  controls when a payload must cross a boundary.
- Sidecar fallback writes real secrets only to tmpfs and only for tools that
  cannot consume dynamic capabilities.
- Audit records carry refs, hashes, leases, and redaction notes, not payloads.

Threat 2: over-broad standing privilege.

Mitigations:

- The envelope binds task id, target, scope, TTL, ratification ref, execution
  mode, and audit hooks.
- Broker validation fails before minting on any mismatch.
- Default execution mode for high blast radius is proxy-only, so the agent
  cannot reuse a capability beyond the exact action.
- OpenBao leases, TTLs, one-time passwords, short-lived SSH certs, and dynamic
  credentials narrow the useful lifetime.
- Side-Effect Ledger plus lease-revocation evidence makes every privileged
  action and cleanup step reconstructable.

## OpenBao Capability Basis

OpenBao facts below were verified against OpenBao 2.5.x docs on 2026-06-22.
OpenBao docs and API paths remain Vault-compatible in places, including
`X-Vault-Token`, `X-Vault-Wrap-TTL`, `/ssh/sign/:name`, and
`/transit/sign/:name`.

| Capability | Status | Use in this design | Sources |
| --- | --- | --- | --- |
| OpenBao docs version | VERIFIED, Version 2.5.x | Version basis for this table | https://openbao.org/docs/ |
| Secret engines overview | VERIFIED | OpenBao engines can store, generate, encrypt, issue dynamic credentials, certificates, and encryption-as-a-service operations | https://openbao.org/docs/secrets/ |
| SSH signed certificates | VERIFIED | Preferred for root SSH: broker/caller generates ephemeral public key, OpenBao signs it, broker uses short TTL cert | https://openbao.org/docs/secrets/ssh/ and https://openbao.org/docs/secrets/ssh/signed-ssh-certificates/ and https://openbao.org/api-docs/secret/ssh/ |
| SSH one-time passwords | VERIFIED | Fallback for per-attempt SSH where helper validation and deletion fit the host | https://openbao.org/docs/secrets/ssh/one-time-ssh-passwords/ |
| SSH issue key+certificate | VERIFIED but not preferred | `/ssh/issue/:name` can return private key material; avoid for agent-facing flows | https://openbao.org/api-docs/secret/ssh/ |
| Transit encrypt/sign/verify/hash/HMAC/random | VERIFIED | Broker can perform crypto without handing keys to agents; decrypted plaintext must stay out of LLM context | https://openbao.org/docs/secrets/transit/ and https://openbao.org/api-docs/secret/transit/ |
| Transit CSR signing with key kept in Transit | VERIFIED | Future cert/key custody pattern where key material stays within Transit | https://openbao.org/api-docs/secret/transit/ |
| Database dynamic credentials | VERIFIED | Broker can lease DB credentials for scoped operations | https://openbao.org/docs/secrets/databases/ |
| Kubernetes service-account tokens | VERIFIED | Broker can lease SA tokens and rely on deletion/expiry semantics | https://openbao.org/docs/secrets/kubernetes/ |
| RabbitMQ dynamic users | VERIFIED | Broker can lease dynamic RabbitMQ users and rely on revocation/deletion | https://openbao.org/docs/secrets/rabbitmq/ |
| Response wrapping and cubbyhole | VERIFIED | Trusted relay, single-use unwrap, tamper/lifetime checks, per-token storage destroyed with token | https://openbao.org/docs/concepts/response-wrapping/ and https://openbao.org/docs/secrets/cubbyhole/ |
| AppRole and Agent/Proxy | VERIFIED | Machine auth, response-wrapped SecretID workflow, Auto-Auth, caching, templates, API proxy, process supervisor | https://openbao.org/docs/auth/approle/ and https://openbao.org/docs/agent-and-proxy/ and https://openbao.org/docs/agent-and-proxy/agent/ and https://openbao.org/docs/agent-and-proxy/agent/template/ |
| Built-in cloud IAM engines | NOT VERIFIED AS BUILT-IN | Do not design as shipped OpenBao support; treat cloud IAM as external plugin or future slice | OpenBao builtin logical list checked via `gh api repos/openbao/openbao/contents/builtin/logical --jq '.[].name'`; current docs list no AWS/GCP/Azure engine |

The divergence from common Vault assumptions is important: OpenBao 2.5.x docs
and repo evidence do not verify built-in AWS, Azure, or GCP IAM dynamic secret
engines. This design must not claim built-in cloud IAM dynamic secrets until a
future slice verifies an external plugin or new OpenBao support.

## Worked Pilot: ce-ops#184 VPS `/tmp` Root Config

Goal: edit `/etc/tmpfiles.d` on a VPS to configure `/tmp` behavior without
placing a static root key in an agent environment.

Pilot sequence:

1. Operator ratifies a five-minute root action envelope for ce-ops#184.
2. Broker validates the envelope, target path, blast radius, and audit hooks.
3. Broker generates an ephemeral SSH keypair in broker memory or receives an
   ephemeral public key from a deterministic sidecar.
4. Broker asks OpenBao SSH `/ssh/sign/:name` to sign the public key for
   principal `root`, TTL 300 seconds, target host role `ce-vps-root-tmp`.
5. Broker opens SSH to the VPS with the signed cert and no static root key.
6. Broker writes the tmpfiles config under `/etc/tmpfiles.d`, reads it back,
   and optionally runs a validation command approved by the envelope.
7. Broker records Side-Effect Ledger evidence: envelope id, target ref, file
   path, command refs, before/after hashes where available, OpenBao lease refs,
   and redactions.
8. Broker revokes the lease or records expiry evidence; the signed cert becomes
   unusable after TTL.
9. Agent receives status, evidence refs, and hashes, not private key material,
   OTP values, root shell history, or secret payloads.

Concrete envelope instance:

```yaml
privileged_action_envelope:
  envelope_id: pae-ce185-vps-tmp-root-20260622
  schema_version: "1"
  task_id: ce-ops#184
  requester:
    seat_id: ce-dev-4
    role: implementer
    actor_ref: github:ce-dev-4
  capability:
    engine: openbao_ssh
    operation: ssh_sign_public_key
    capability_ref: openbao:ssh/sign/ce-vps-root-tmp
    openbao_mount: ssh
    mode: signed_ssh_certificate
  target:
    target_type: host
    target_ref: vps:ce-ops-184
    target_path: /etc/tmpfiles.d/ce-vps-tmp.conf
    target_principal: root
    environment_ref: ce-vps-pilot
  scope:
    allowed_actions:
      - edit_file
    resource_refs:
      - path:/etc/tmpfiles.d/ce-vps-tmp.conf
    filesystem_paths:
      - /etc/tmpfiles.d/ce-vps-tmp.conf
    command_refs:
      - install -m 0644 tmpfiles.d
      - systemd-tmpfiles --cat-config
    network_egress: target_only
    max_uses: 1
    constraints:
      - No shell beyond file write and verification readback.
      - No static root key material.
      - No secret value may enter LLM context, argv, ledger, or logs.
  ttl_seconds: 300
  expires_at: "2026-06-22T15:05:00Z"
  ratification_ref:
    kind: issue
    ref: ce-ops#184
    ratified_prompt_sha: 8a0f89fee53dc43c26dd8a3f2a3b50191e6564453aa6c19b05a1bc907fc88aac
    ratifier_role: operator
    ratified_by: operator
    ratified_at: "2026-06-22T15:00:00Z"
  execution:
    custody_mode: broker-mints-ephemeral
    execution_mode: broker-proxies
    blast_radius: high
    irreversible: true
    reason: Root write to /etc is high-blast, so the broker executes and returns evidence only.
  audit_hooks:
    - hook_type: side_effect_ledger
      hook_ref: side-effect-ledger:ce-ops-184:vps-tmp-root
      required: true
    - hook_type: lease_revocation
      hook_ref: openbao-lease:pending-runtime-id
      required: true
    - hook_type: openbao_audit
      hook_ref: openbao:audit:ssh/sign/ce-vps-root-tmp
      required: true
  lease:
    lease_id: openbao-lease:pending-runtime-id
    accessor_ref: accessor:pending-runtime-accessor
    issued_at: "2026-06-22T15:00:00Z"
    expires_at: "2026-06-22T15:05:00Z"
    revoke_ref: openbao:sys/leases/revoke/pending-runtime-id
    renewable: false
  metadata:
    openbao_version_basis: OpenBao 2.5.x docs verified 2026-06-22
```

## Implementation Slices

Future implementation should be split into G5-sized slices that are large enough
to carry tests and an honest work class, not tiny placeholder carriers:

1. **Envelope validator slice**: add examples, validator check, semantic
   no-secret scans, mechanic/target matching, and PR-diff coverage.
2. **Policy core slice**: pure broker policy over envelope, blast radius,
   custody mode, execution mode, TTL, target, and audit hooks.
3. **OpenBao SSH pilot slice**: implement signed-public-key root SSH for the
   ce-ops#184 VPS `/tmp` pilot with no `/ssh/issue` private-key return path.
4. **Audit and revocation slice**: Side-Effect Ledger writer integration,
   OpenBao lease refs, revocation evidence, and failure records.
5. **Sidecar fallback slice**: tmpfs templating for one tool that cannot consume
   dynamic capability, with wipe and log/argv redaction tests.
6. **Low-blast handoff slice**: capability-handoff allowlist for a benign target
   class, with explicit denial for high or irreversible blast radius.
7. **Supervisor/container slice**: broker container boundary, OpenBao auth path,
   process isolation, and no-agent-secret visibility checks.

Each live slice must include a ratified scope, tests, redaction evidence, and a
closed path manifest before any privileged runtime use.

## Non-Goals

This contract does not authorize live root access, deploys, provider
configuration changes, branch protection changes, OpenBao production mount
changes, secret migration, cloud IAM claims, or merge. It also does not create a
general shell escape for DevOps agents. Every privileged action remains bound to
one ratified envelope and one broker decision.
