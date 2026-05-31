# Creator Engine

## Status and stability

Creator Engine's v1.0 governed runtime is **runtime-complete and
pre-release** — landed on `main` but not yet cut or tagged (version
`0.1.0`; the G0–G9 delivery gates are ready for Operator ratification).
The v0.1 file-only substrate (see "v0.1 scope" below) composes beneath
it, and v1.0 remains the integration target: an end-to-end governed
agentic SDLC loop with every privileged gate human-ratified.
Spec/plan/tasks artifacts, schemas, templates, and the offline validator
may change without backward-compatibility guarantees until v1.0 is
released. Privileged operations (deploys, governance amendments,
identity/security/attestation/redaction changes, repo settings, branch
protection, visibility flips) remain Operator-ratified regardless of
release stage — see [`GOVERNANCE.md`](./GOVERNANCE.md).

Release surface pointers: `v0.1.0` is the first public product tag direction,
with `creator-engine-validator` kept at `0.1.0` for the initial public cut. See
[`CHANGELOG.md`](./CHANGELOG.md) and
[`docs/delivery/VERSIONING_AND_RELEASE_POLICY.md`](./docs/delivery/VERSIONING_AND_RELEASE_POLICY.md)
for the changelog and versioning policy. G2.* identifiers remain internal gate
numbers, and draft v2 substrate remains roadmap material rather than shipped v2
runtime.

LIMITLESS is the named public dogfood tenant; generic paths in the
substrate must not hardcode it (enforced by the offline validator's
`scan-no-limitless` check).

## What Creator Engine is

Creator Engine is a repo-native agentic SDLC governance substrate. It
makes agent-authored software work auditable, spec-driven,
identity-aware, mutation-class governed, verified by evidence, and
ratified by explicit authority rules. The **Operator** — the apex human
authority — ratifies every privileged gate; review, CI, fan-in, and
harness output inform the Operator but never ratify on the Operator's
behalf. v1.0 is the integration target: an end-to-end governed agentic
SDLC loop with every privileged gate human-ratified.

## v1.0 command-line runtime (`ce`)

v1.0 adds a daemonless, repo-native, local command-line runtime, `ce`. It runs
on demand against repository-local `.hermes/` state and tracked substrate
artifacts, then exits — no long-running daemon and no web server. `ce` does not
rename or replace the validator distribution: it is added as a second console
script to `creator-engine-validator` (DP-1 = A), and `ce check` wraps the
retained `creator-engine-validator` conformance checks.

The as-built v1.0 `ce` command surface is exactly these groups:

| Command | Purpose |
|---|---|
| `ce check` | run the `creator-engine-validator` conformance checks (wraps the validator) |
| `ce doctor` | governed-environment guard preflight; refuses ungoverned host drift (DP-3 = B) |
| `ce init` | idempotently initialize local `.hermes/` kernel state; refuses ungoverned state |
| `ce launch` | open/attach the visible Controller-seat tmux launcher (DP-2 = B) |
| `ce hud` | alias/seam label for `ce launch` — **not** a CE-native TUI |
| `ce lane` | governed visible lane-launch primitive (`launch`/`status`/`verify`/`archive`) |
| `ce worker` | worker isolation runtime over rootless Podman + credential broker |
| `ce ledger` | Side-Effect Ledger runtime (append-only hash chain: `record`/`verify`) |
| `ce fanin` | build/inspect a local read-only evidence fan-in packet (no authority) |
| `ce queue` | Integration Queue **dry-run** landing preview (`dry-run`/`inspect`); no authority |
| `ce event` | CE-event runtime: local append-only signed-block chains (`append`/`verify`/`sign`/`replay`/`index`); no authority |

`ce launch` opens or attaches a visible Controller seat through the chosen
Controller harness; the active agent occupying that seat is the Controller
agent. The launcher is part of the Controller harness surface and is not a
CE-native TUI (see
[`docs/governance/V1_CANONICAL_TERMINOLOGY.md`](./docs/governance/V1_CANONICAL_TERMINOLOGY.md)
for the Controller agent / Controller harness distinction).

There is **no `ce dev` command in v1.0**. The `ce dev …` namespace is reserved
for the deferred project-dev container (`ce dev shell` / `ce dev run`), which is
a v1.1 / post-v1 seam — deferred, not rejected (see
[`docs/governance/V1_DEV_CONTAINER_SEAM_CONTRACT.md`](./docs/governance/V1_DEV_CONTAINER_SEAM_CONTRACT.md)).
The Integration Queue is a local serialized **dry-run** landing preview only in
v1.0; live landing is POST-V1 (see
[`docs/operations/INTEGRATION_QUEUE_DRY_RUN.md`](./docs/operations/INTEGRATION_QUEUE_DRY_RUN.md)).

The v1.0 `ce` runtime is **runtime-complete and pre-release**: every gate
(G0–G9) is landed on `main` and ready for Operator ratification, but no
release has been cut or tagged. The pinned package version is `0.1.0`.

### Install (Option B packaging)

v1.0 targets **Python `>=3.14`** (target 3.14.x). The install surface is a source
checkout (`git clone`) plus an **offline, uv-first** install with a pip
`--no-index` fallback against the checked-in cp314 wheelhouse — the `uvx`
one-line operator install is POST-V1 (B3). `validators/uv.lock` is the primary
lock; `validators/requirements.txt` is the lockstep `uv export` fallback;
runtime dependencies are pinned at **PyYAML 6.0.3** and **jsonschema 4.26.0**.
See [`validators/README.md`](./validators/README.md) for the full offline
install and the `ce` / validator quickstart.

## v0.1 scope

v0.1 ships only files inside a git repository. Two layers compose it:

- **Feature 001 — governance substrate** (merged). Identity schema,
  mutation-class taxonomy with nine baseline classes, reserved-action
  vocabulary, authority matrix, attestation / ratification / redaction
  record formats, Spec Kit wrapper sidecars, Definition of Ready and
  Definition of Done, redaction gate policy, and an offline validator
  runnable from a fresh `git clone`.
- **Feature 002 — operating model**. The 25-state SDLC machine with
  24 transitions, the Assignment Envelope contract, the
  `/speckit-implement` policy, the actor/tool ownership matrix, the
  parallel-agent development model, the conflict taxonomy, and the
  Phase 1 / Phase 2 boundary. Feature 002 specifies the canonical
  document set; the bodies below are authored in Sprint 0 Execution
  Slice A.

Phase 2 autonomy (low-risk auto-merge, autonomous batch-pulling) and
v1.0 end-to-end automation are integration targets, not v0.1
deliverables.

## Next horizon: v2.0 foundation substrate (Draft, spec-only)

Work has begun on the **Creator Engine v2.0 foundation substrate**. It is
currently a **Draft, spec-authoring-only direction** — tracked specification,
schema, and governance documentation with **no v2 runtime shipped**. It does
not change the v1.0 `ce` runtime described above. The foundation spec
([`specs/v2/001-v2-foundation-substrate/spec.md`](./specs/v2/001-v2-foundation-substrate/spec.md),
its [`spec.ce.yml`](./specs/v2/001-v2-foundation-substrate/spec.ce.yml) sidecar,
the [`specs/v2/_crosswalk.yml`](./specs/v2/_crosswalk.yml) register, and
[`ADR-V2-001`](./specs/v2/adrs/ADR-V2-001-v2-foundation-substrate.md)) frames a
clean v2 foundation:

- a canonical `.ce/` active-state and governance namespace with an enforceable
  tracked-vs-instance boundary, replacing wholesale-ignored `.hermes/` for v2
  flows;
- a hard `.hermes/` write-freeze for v2 flows (`.hermes/` stays readable only as
  legacy/import/archive context);
- a **read-only**, dry-run-capable v1→v2 importer contract that never mutates
  `.hermes/`;
- the authoritative v1→v2 crosswalk register;
- operating modes `strict` / `auto` / `transcendence`, with migrated v1 tenants
  defaulting to `strict`;
- an `agent_reviewer` role (active, advisory/evidence-bearing, non-ratifying)
  and an `agent_ratifier` role (reserved-inactive, validator-rejected for any
  active authority binding).

The **Operator-only privileged floor is preserved in every v2 mode**:
privileged-class ratification and emergency governed override route only to the
Operator, never to any agent role. v2 introduces no destructive removal of v1
artifacts; legacy `source` values and `.hermes/` material remain readable for
import, crosswalk, archive, and history. Treat v2 as the next horizon, not as
shipped runtime.

## Repository layout

- `.specify/memory/constitution.md` — highest-authority governance
  document.
- `specs/` — Spec Kit feature specifications, including Feature 001
  (governance substrate), Feature 002 (canonical docs and operating
  model), the Sprint 0 minimum viable delivery system note, and the
  `specs/v2/` v2.0 foundation specifications (Draft).
- `docs/contracts/` — Feature 001 governance contract documents.
- `docs/adr/` — architecture decision records, including
  `ADR-0002-operator-terminology-reconciliation.md` (Operator
  terminology policy).
- `docs/product/`, `docs/architecture/`, `docs/governance/`,
  `docs/quality/`, `docs/devops/`, `docs/security/` — the canonical
  Creator Engine document set indexed below.
- `docs/operations/` — operational protocol documentation (e.g.,
  `docs/operations/session-continuity-protocol.md`). These are
  operational protocols, not part of the 17-document canonical set
  indexed below.
- `schemas/`, `templates/`, `validators/`, `examples/`, `tenants/` —
  Feature 001 substrate artifacts and tenant fixtures.
- `.hermes/` — Session continuity protocol and state for the Operator.
- `validators/README.md` — substrate validator quickstart.

See [`validators/README.md`](./validators/README.md) for the offline
install and validator quickstart.

## Canonical document index

The canonical document index — the canonical Creator Engine document
set — is exactly these 17 documents (Feature 002 FR-022):

1. [`README.md`](./README.md) — this orientation document.
2. [`docs/product/PRD.md`](./docs/product/PRD.md) — product vision,
   target tenants, problem statement, value proposition, primary use
   cases, non-goals, success metrics, version-scope summaries.
3. [`docs/product/ROADMAP.md`](./docs/product/ROADMAP.md) — Features
   001–006 scope summaries and v1.0 integration target.
4. [`docs/product/REQUIREMENTS.md`](./docs/product/REQUIREMENTS.md) —
   product requirements catalog with traceability to Feature 001/002.
5. [`docs/architecture/SAD.md`](./docs/architecture/SAD.md) — system
   architecture: components, data flows, storage, trust boundaries,
   extension points.
6. [`docs/architecture/agentic-sdlc-operating-model.md`](./docs/architecture/agentic-sdlc-operating-model.md)
   — the 25-state SDLC machine, transition matrix, Phase 1/2 boundary,
   `/speckit-implement` policy, and Assignment Envelope linkage.
7. [`docs/architecture/integration-map.md`](./docs/architecture/integration-map.md)
   — boundaries with Spec Kit, GitHub, CI, and trackers.
8. [`docs/architecture/agent-interaction-model.md`](./docs/architecture/agent-interaction-model.md)
   — actor-to-actor interaction patterns, envelope handoff sequence,
   escalation paths.
9. [`docs/architecture/parallel-agent-development-model.md`](./docs/architecture/parallel-agent-development-model.md)
   — one-driver-per-worktree rule, parallel-pair pattern, conflict
   taxonomy.
10. [`docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](./docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md)
    — authority matrix summary, ratifier taxonomy, SDLC transition →
    ratifier link table.
11. [`docs/governance/MUTATION_CLASS_MODEL.md`](./docs/governance/MUTATION_CLASS_MODEL.md)
    — baseline classes, reserved-action vocabulary, privileged-class
    rules.
12. [`docs/governance/ATTESTATION_MODEL.md`](./docs/governance/ATTESTATION_MODEL.md)
    — attestation record fields, storage, SDLC linkage, bootstrap
    grandfathering.
13. [`docs/quality/QA_STRATEGY.md`](./docs/quality/QA_STRATEGY.md) —
    testing levels per mutation class; QA agent role; deferrals.
14. [`docs/quality/TESTING_STRATEGY.md`](./docs/quality/TESTING_STRATEGY.md)
    — engineering testing practices, validator self-tests, evidence
    capture, self-claim rejection invariant.
15. [`docs/devops/CI_CD_STRATEGY.md`](./docs/devops/CI_CD_STRATEGY.md)
    — verifies-not-ratifies invariant, required CI checks, branch
    protection policy summary, Feature 003 deferral.
16. [`docs/devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md`](./docs/devops/RELEASE_AND_DEPLOYMENT_STRATEGY.md)
    — environment taxonomy, deploy-as-privileged-class rule, rollback
    evidence, Feature 006 deferral.
17. [`docs/security/SECURITY_MODEL.md`](./docs/security/SECURITY_MODEL.md)
    — security as design constraint, redaction gate summary, secrets
    and rotation policy, escalation paths.

## Source of truth notice

The constitution at
[`.specify/memory/constitution.md`](./.specify/memory/constitution.md)
is the highest-authority document for agent-authored work.

The
[Feature 002 source-of-truth hierarchy](./specs/002-canonical-docs-and-operating-model/spec.md#fr-019)
(FR-019) is:
constitution > Feature 001 governance substrate (ratified) >
Feature 002 canonical docs (above) > tenant fixtures
(`tenants/<name>/`) > working notes and handoffs.

Amendments to the constitution, the Feature 001 substrate, or the
Feature 002 operating model are themselves Creator-Engine-governed
mutations: a spec/plan/tasks triple under explicit Operator approval,
versioned per the constitution's Governance section.

## License

Creator Engine is licensed under the Apache License, Version 2.0.
The full text is in [`LICENSE`](./LICENSE); attribution and vendored
wheelhouse notices are in [`NOTICE`](./NOTICE).

## Community and contribution

- Contribution workflow and local validation commands:
  [`CONTRIBUTING.md`](./CONTRIBUTING.md).
- Governance, authority, and ratification on-ramp:
  [`GOVERNANCE.md`](./GOVERNANCE.md).
- Security policy and private vulnerability reporting:
  [`SECURITY.md`](./SECURITY.md).
- Code of conduct: [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md).

## Contact

For general, non-security, non-conduct project, community, or
governance inquiries, email
[`ubuntuaws745@gmail.com`](mailto:ubuntuaws745@gmail.com). This is the
primary public contact for general project correspondence only; it
does not replace the dedicated reporting channels above:

- Vulnerabilities and other security-sensitive reports must go
  privately to
  [`ubuntuaws745+security@gmail.com`](mailto:ubuntuaws745+security@gmail.com)
  per [`SECURITY.md`](./SECURITY.md).
- Code of conduct reports must go privately to
  [`ubuntuaws745+conduct@gmail.com`](mailto:ubuntuaws745+conduct@gmail.com)
  per [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md).
