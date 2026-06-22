---
kind: decision-record
record_type: adr
schema_version: "1"
id: ADR-0011
title: "DevOps privileged-action broker - secret-free root ops via ratified envelope and OpenBao ephemeral capabilities"
status: proposed
date: "2026-06-22"
decision_makers: ["ce-dev-4"]
consulted: []
informed: []
review_by: "2026-12-22"
mutation_class: security
evidence_refs:
  - kind: issue
    ref: "ce-ops#185 - DevOps agent + privileged-action broker"
    tag: ce-ops-185
  - kind: doc
    ref: "Design brief sha256 8a0f89fee53dc43c26dd8a3f2a3b50191e6564453aa6c19b05a1bc907fc88aac"
    tag: design-brief
  - kind: adr
    ref: "docs/decisions/0005-openbao-secret-identity-backend.md"
    tag: openbao-backend
  - kind: adr
    ref: "docs/decisions/ADR-0007-egress-gateway-publish-broker.md"
    tag: egress-broker
  - kind: doc
    ref: "docs/contracts/devops-privileged-action-broker.md"
    tag: broker-contract
  - kind: schema
    ref: "schemas/devops-privileged-action-broker.schema.yaml"
    tag: envelope-schema
crosswalk:
  informs:
    - ce-ops#185
    - ce-ops#184
    - ce-ops#157
    - ce-ops#135
    - ce-ops#128
---

# DevOps privileged-action broker - secret-free root ops via ratified envelope and OpenBao ephemeral capabilities

## Context and Problem Statement

CE is moving toward contained seats and deterministic brokers. ADR-0007 removes
forge push authority from agents and places it behind an egress gateway.
ADR-0005 chooses OpenBao as the default secret and identity backend, and the
secret-zero and mint-broker work moves static identity material out of agent
custody. The remaining gap is privileged DevOps work: root host changes,
provider mutations, deploy-adjacent actions, and tool flows that normally need
standing administrative secrets or broad ambient shell authority.

The problem is not only "who has the secret." A prompt-injectable agent with a
root key, cloud admin token, long-lived kube token, or decrypted plaintext can
leak it through context, logs, memory, issue comments, command arguments, or
future tool output. The same agent can also use standing privilege beyond the
task that justified it. CE therefore needs a ratified, value-free authority
record and a deterministic broker that turns that record into one narrowly
scoped, short-lived capability.

## Decision Outcome

Choose a **secret-free DevOps agent with an authority/custody split**:

- The DevOps agent may request privileged work and may author a
  `privileged_action_envelope`, but it does not hold static root/admin secrets
  and does not receive secret payloads in LLM context.
- A privileged-action broker runs in its own container/trust domain. It validates
  the ratified envelope, mints or obtains the scoped capability, performs or
  hands off exactly the permitted action, records audit evidence, and revokes or
  lets the lease expire.
- OpenBao is the default capability backend for verified dynamic or ephemeral
  capability families: SSH signed certificates and OTP, Transit operations,
  database dynamic credentials, Kubernetes service-account tokens, RabbitMQ
  dynamic users, response wrapping, and cubbyhole delivery semantics.
- The envelope is the authority artifact: a ratified scoped grant bound to task,
  requester, capability, target, scope, TTL/expiry, ratification reference,
  execution mode, and audit hooks. It carries no secret value.

The detailed contract, envelope shape, threat model, OpenBao capability table,
and ce-ops#184 pilot sequence live in
[`docs/contracts/devops-privileged-action-broker.md`](../contracts/devops-privileged-action-broker.md).
The machine-readable schema lives at
[`schemas/devops-privileged-action-broker.schema.yaml`](../../schemas/devops-privileged-action-broker.schema.yaml).

## Design Forks and Defaults

### Custody fork

Default: **`broker-mints-ephemeral`**. The broker asks OpenBao for an
operation-scoped capability, preferably one that does not expose private key
material to the agent or broker process beyond the minimal execution boundary.
For SSH, that means signing a caller- or broker-generated ephemeral public key
with `/ssh/sign/:name` instead of using `/ssh/issue/:name`, because issue returns
private key material.

Fallback: **`sidecar-templates-real-secret-into-tmpfs`** only for tools that
cannot consume dynamic capabilities. The sidecar must run in the broker trust
domain, template the real secret into RAM-backed storage, keep it out of argv,
logs, transcripts, ledgers, and LLM context, and wipe it at action completion or
lease expiry.

### Execution fork

Default for irreversible, root, deploy, provider-admin, or otherwise
high-blast actions: **`broker-proxies`**. The broker performs the action and
returns redaction-safe evidence, not the capability.

Allowed only for benign or low-blast actions: **`capability-handoff`**. The
handoff may expose an ephemeral capability to a deterministic tool or tightly
bounded sidecar, never to free-form LLM context. The envelope records why the
blast radius qualifies.

Blast radius is graded by consequence, not by implementation convenience:
host-root writes, live deploys, destructive provider mutations, secret
decryption, and broad network access are high or irreversible and use
`broker-proxies`.

## Placement

This broker composes with, but does not replace, existing brokers:

- **Mint-broker (ce-ops#157 / PR #300)** mints bounded forge tokens after
  binding and ceiling checks. It does not perform root host or provider runtime
  actions.
- **Egress broker / ADR-0007** transports signed forge artifacts and opens PRs
  without giving agents forge egress.
- **Privileged-action broker (this ADR)** mediates root/runtime/provider
  privileged actions under a ratified envelope and OpenBao lease/audit controls.

Each broker keeps a smaller deterministic TCB than giving the same authority to
an agent.

## Consequences

- Good: removes standing root/admin secrets from DevOps agent context while
  preserving a path to real operational work.
- Good: makes privileged work reviewable before execution because the envelope
  is value-free and source-controlled or otherwise auditable.
- Good: aligns with OpenBao lease, response wrapping, cubbyhole, and audit
  semantics without claiming unverified cloud IAM support.
- Good: composes with the Side-Effect Ledger and lease revocation audit so
  privileged effects can be reconstructed without exposing payloads.
- Trade-off: the broker becomes a high-assurance component. Its container,
  policy core, OpenBao client path, audit writer, and sidecar fallback all need
  fail-closed tests before live use.
- Trade-off: some legacy tools will require the tmpfs sidecar fallback until
  they can consume dynamic credentials or broker-proxied operations.
- Trade-off: this ADR is design/schema only. It does not authorize live root
  access, deploys, OpenBao production mounts, or cloud-provider admin mutation.

## Non-Ratification Statement

This PR adds design artifacts and an envelope schema only. It does not implement
the broker, wire runtime hooks, deploy OpenBao mounts, create live roles, mint
real capabilities, alter branch protection, perform root operations, merge
anything, or authorize a live ce-ops#184 execution. Live use requires a later
ratified implementation slice with tests, operator-held OpenBao configuration,
and redaction-safe audit evidence.
