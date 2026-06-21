# Creator Engine

Creator Engine (CE) is a governed-SDLC automation layer for agent-authored
software work. It turns coding agents into auditable participants in a software
delivery loop: scoped work, explicit identity, contained runtime execution,
evidence capture, independent review, and human-ratified privileged gates.

The current direction is v3.5: make CE usable by solo and small teams while
moving toward the "every agent contained" security posture for the NVIDIA pitch
arc. The forward plan lives in
[`docs/v3.5-roadmap.md`](./docs/v3.5-roadmap.md). The historical v3 gate map is
kept in [`docs/v3-roadmap.md`](./docs/v3-roadmap.md).

## Current Status

As of June 19, 2026:

- v3.1 is pilot-ready: the repo contains the v3 Scope-to-PR-to-review-to-merge
  substrate, the product CLI surface, cockpit/read-model work, and the two-mode
  installer substrate.
- v3.5 is the active program plan. Its critical workstreams are containment,
  team-mode throughput, install/pilot readiness, secret and identity custody,
  release integrity, and documentation/product surface currency.
- The package artifacts are at `creator-engine-validator` version `0.2.0`.
  There is no public product tag or GitHub release yet; release publication is
  still a separate governed workstream. See
  [`docs/delivery/VERSIONING_AND_RELEASE_POLICY.md`](./docs/delivery/VERSIONING_AND_RELEASE_POLICY.md).
- Linux x86_64 and aarch64 cp314 wheelhouses are in-tree for the runtime and
  developer/test dependency sets. This unblocks DGX/Grace class hosts for the
  offline validator/test path.
- The v8 "Factory Floor" website is live at `creator-engine.dev`; this README is
  the repo orientation, not the website source.

## What CE Does

CE coordinates agentic development around these invariants:

- **Scope before work.** Work is framed as explicit Scopes and governed
  manifests. PRs carry per-branch path-manifest carriers under
  `.ce/pr-manifests/`; CI checks that the diff matches the declared closed set.
- **Identity before authority.** Agent, developer, reviewer, controller, and
  forge identities are explicit records or install-time bindings, not ambient
  assumptions.
- **Containment before autonomy.** Runtime policies, gVisor/runsc wrappers,
  worker-container records, and Controller runtime contracts define what a seat
  may access before it performs work.
- **Evidence before claims.** Runs emit structured evidence: runtime policy,
  spend, action decisions, run outcomes, change refs, review/merge state, and
  completion reports.
- **Human ratification for privileged gates.** Agents can propose, author,
  inspect, and attest; privileged classes such as deploy, governance, identity,
  security, release, and trust-root changes still require the Operator or another
  ratified human authority.

The highest-authority governance text is
[`.specify/memory/constitution.md`](./.specify/memory/constitution.md).
Operational governance is summarized in [`GOVERNANCE.md`](./GOVERNANCE.md).

## The Runtime Surfaces

The repository intentionally carries more than one runtime surface while the
platform evolves:

- **`ce`** is the retained v1 command-line runtime. It wraps the validator and
  provides local repo-native operations such as `check`, `doctor`, `init`,
  `launch`, `lane`, `worker`, `ledger`, `fanin`, `queue`, `event`, `pcl`,
  `brain`, `connector`, `reviewer-triage`, and `claim`.
  The as-built v1 command groups are `ce check`, `ce doctor`, `ce init`,
  `ce launch`, `ce hud`, `ce lane`, `ce worker`, `ce ledger`, `ce fanin`,
  `ce queue`, `ce event`, `ce pcl`, `ce brain`, `ce connector`,
  `ce reviewer-triage`, and `ce claim`. `ce hud` is an alias for the visible `ce launch` Controller-seat
  tmux launcher, not a CE-native TUI rename. There is no `ce dev` command in
  v1.
- **`cev3`** is the v3 work-driving entry point in this repository. It covers the
  v3 product surface: session framing, Scope/drive/review/merge flows,
  onboard/install planning, cockpit/read-model commands, notification feed, and
  pilot-facing guide/report surfaces.
- **The validator** is the offline conformance tool shipped as the
  `creator-engine-validator` package. It enforces schema, protocol, packaging,
  terminology, version-boundary, path-manifest, runtime-policy, and other
  substrate checks.

The v1/v3 boundary is intentional and checked by
[`docs/architecture/VERSION_BOUNDARY.md`](./docs/architecture/VERSION_BOUNDARY.md)
and the `version_boundary` validator check.

## Install Story

CE currently has two supported install paths, both documented by
[`docs/contracts/installer.md`](./docs/contracts/installer.md).

1. **Public one-liner.**

   ```bash
   curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash
   ```

   The script fetches the signed agent-native spec, verifies it against the
   pinned `ce-root-v1` OpenSSH trust root, verifies the wheelhouse manifest and
   every artifact hash, obtains Python 3.14 through the pinned `uv` artifact if
   needed, installs `creator-engine-validator==0.2.0` offline, proves `cev3`,
   and runs authenticated inventory. This E1 bootstrap does **not** run sudo,
   automate the GitHub App click, mutate branch protection, or create/adopt a
   project.

2. **Clone plus offline wheelhouse.**

   ```bash
   git clone https://github.com/creator-engine/creator-engine.git
   cd creator-engine
   python3.14 -m venv .venv
   . .venv/bin/activate
   pip install --no-index --find-links validators/wheelhouse -r validators/requirements.txt
   PYTHONPATH=validators python -m creator_engine_validator --list-checks
   ```

   The runtime wheelhouse is cp314 and dual-arch for Linux x86_64/aarch64 where
   native wheels are needed. Developer/test dependencies live separately under
   `validators/wheelhouse-dev/`. See
   [`validators/README.md`](./validators/README.md) for the full offline runtime
   and test install commands.

The agent-native install spec is served as
[`docs/llms-install.md`](./docs/llms-install.md) and must be verified before
execution. That file and the served installer are trust-root surfaces; ordinary
documentation edits must not mutate them.

## Identity Model

CE does not treat a shell account, local `git config`, or ambient `gh auth`
state as an authority source.

- A local adoption commit made during install/apply is bound to the
  install-time forge identity resolved from the bootstrap token's `GET /user`.
  The installer writes local-only `user.name`, `user.email`, and
  `user.useConfigOnly=true`, then verifies the committed author. See
  [`docs/contracts/installer.md`](./docs/contracts/installer.md#the-github-leg-decomposed-pure-planners-injected-probes).
- Review identity is independent from author identity. Reviewer records and
  reviewer authority are evidence-authoring authority, not ratification
  authority. See
  [`docs/delivery/REVIEWER_IDENTITY_REQUIREMENTS.md`](./docs/delivery/REVIEWER_IDENTITY_REQUIREMENTS.md)
  and [`docs/operations/REVIEWER_TRIAGE.md`](./docs/operations/REVIEWER_TRIAGE.md).
- Controller identities have their own controller-key protocol for lease
  signatures and must not carry private keys or raw credentials in tracked
  records. See
  [`docs/operations/CONTROLLER_IDENTITY_PROTOCOL.md`](./docs/operations/CONTROLLER_IDENTITY_PROTOCOL.md).
- Per-developer identity custody is moving into the governed secret plane. The
  OpenBao decision record is
  [`docs/decisions/0005-openbao-secret-identity-backend.md`](./docs/decisions/0005-openbao-secret-identity-backend.md).

## Containment Direction

The v3.5 north star is "every agent contained", including the Controller. The
repo already contains the substrate and DGX-side artifacts for that direction,
but not every live supervisor piece is complete.

- Runtime policy and evidence contracts live in
  [`docs/contracts/runtime-policy.md`](./docs/contracts/runtime-policy.md) and
  [`docs/contracts/runtime-evidence.md`](./docs/contracts/runtime-evidence.md).
- Worker-container policy and container-instance records define worker isolation
  shape and refusal predicates. See
  [`docs/operations/WORKER_CONTAINER_PROTOCOL.md`](./docs/operations/WORKER_CONTAINER_PROTOCOL.md).
- Controller runtime contracts classify `role: controller`, containment posture,
  forbidden host surfaces, and credential-handle names. See
  [`docs/operations/CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md`](./docs/operations/CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md).
- DGX runsc/gVisor wrappers live under
  [`deploy/dgx-runsc/`](./deploy/dgx-runsc/README.md) for Codex seats and
  [`deploy/dgx-controller-runsc/`](./deploy/dgx-controller-runsc/README.md) for
  Controller seats. The Controller wrapper is a Gate 2 artifact; the Gate 3
  Controller Supervisor/OpenShell work remains a later containment workstream.

The current concrete posture is gVisor/runsc on DGX where available, with
OpenShell targeted behind the same adapter direction.

## Repository Map

- `.ce/` - CE state namespace, per-PR manifests, changelog fragments, and
  research/design records committed when they are durable repo artifacts.
- `.specify/` and `specs/` - Spec Kit substrate and historical feature specs.
- `docs/` - product, architecture, governance, operations, contracts, install,
  and roadmap documentation. Served trust-root files under `docs/` are handled
  by explicit release/install gates only.
- `schemas/` - JSON/YAML schemas for identity, runtime policy, Scope, evidence,
  install answers, controller contracts, worker containers, and related records.
- `validators/` - the Python package, CLI surfaces, tests, requirements, and
  offline wheelhouses.
- `deploy/` - DGX runsc/gVisor deployment wrappers and image notes.
- `examples/`, `templates/`, `tenants/` - validator examples, reusable templates,
  and tenant fixtures.

## Running Local Gates

Use Python 3.14. For normal runtime validation:

```bash
PYTHONPATH=validators python -m creator_engine_validator --list-checks
PYTHONPATH=validators python -m creator_engine_validator check examples/well-formed/
PYTHONPATH=validators python -m creator_engine_validator check-examples
```

For the full validator test suite, install both runtime and dev/test
wheelhouses, then run:

```bash
PYTHONPATH=validators python -m pytest validators/tests/ -q
```

CI also enforces per-PR path-manifest fidelity. New PRs should include a carrier
under `.ce/pr-manifests/<branch-slug>.md` whose path list exactly matches
`base..HEAD`.

## Roadmaps and Canonical Docs

- Forward v3.5 program plan:
  [`docs/v3.5-roadmap.md`](./docs/v3.5-roadmap.md).
- Historical v3 gate map:
  [`docs/v3-roadmap.md`](./docs/v3-roadmap.md).
- Architecture index:
  [`docs/architecture/README.md`](./docs/architecture/README.md).
- Installer contract:
  [`docs/contracts/installer.md`](./docs/contracts/installer.md).
- Pilot runbook:
  [`docs/guide/pilot-runbook.md`](./docs/guide/pilot-runbook.md).
- Contribution workflow:
  [`CONTRIBUTING.md`](./CONTRIBUTING.md).
- Governance overview:
  [`GOVERNANCE.md`](./GOVERNANCE.md).
- Security policy:
  [`SECURITY.md`](./SECURITY.md).

## Community and Contact

Creator Engine is licensed under the Apache License, Version 2.0. See
[`LICENSE`](./LICENSE) and [`NOTICE`](./NOTICE).

For general, non-security, non-conduct project or governance inquiries, email
[`ubuntuaws745@gmail.com`](mailto:ubuntuaws745@gmail.com).

Security-sensitive reports go to
[`ubuntuaws745+security@gmail.com`](mailto:ubuntuaws745+security@gmail.com) per
[`SECURITY.md`](./SECURITY.md). Code of conduct reports go to
[`ubuntuaws745+conduct@gmail.com`](mailto:ubuntuaws745+conduct@gmail.com) per
[`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md).
