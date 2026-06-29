# Creator Engine

Creator Engine (CE) is a governed-SDLC automation layer for agent-authored
software work. It turns coding agents into auditable participants in a software
delivery loop: scoped work, explicit identity, contained runtime execution,
evidence capture, independent review, and human-ratified privileged gates.

CE is **terminal-first**. You run `ce launch` and your own coding agent
(Claude Code or Codex) opens in its native terminal UI — CE is the invisible
governance wrapper around it, not a replacement editor or chat window.

## What You Install

CE ships in three tiers. Most users only need the first.

**The Engine — the whole product for one user.** The public installer gives a
single developer a governed CLI that wraps their own coding agent. It runs
uncontained, as a single controller, under the user's own credentials, and adds:

- **Governance hooks** — a per-tool deny gate that classifies each action the
  agent attempts (deploy, governance, identity, security, release, trust-root)
  and refuses privileged classes until a human ratifies them.
- **The external grader** — the offline `creator-engine-validator` enforces
  schema, protocol, packaging, terminology, version-boundary, path-manifest, and
  runtime-policy conformance from *outside* the agent, so correctness does not
  depend on the agent grading itself.
- **Envelope, spine, and ledger** — every run frames an explicit Scope, captures
  structured evidence (runtime policy, spend, action decisions, change refs,
  review/merge state), and records side effects to an auditable ledger.

Together these wire your own agent through a **Frame → Shape → Build → Review →
Ship** loop on your repository, with the privileged gates held for a human.

**Ecosystem add-ons — optional.** These are clearly-labeled, opt-in capabilities
layered on top of the Engine; none are required to use CE:

- **forge-automation (the belt)** — an optional, one-command add-on that watches
  for approved-and-green PRs and merges them on your behalf under a human merge
  gate. It is the first add-on, not core CLI behavior.
- **cockpit** — an optional, read-only terminal dashboard, available behind the
  `textual` extra. No desktop or web app ships; the journey cockpit and web
  control UI are designed ([`ADR-0008`](./docs/decisions/ADR-0008-web-control-ui.md))
  but are not the shipped surface.
- **containment** — optional gVisor/runsc and PTY isolation for teams that want
  to run agents (including the controller) in a sandbox.
- **secret-identity / transport-deputy** — an optional governed secret plane
  (OpenBao behind `SecretIdentityBackend`, with a `LocalSecretIdentityBackend`
  for offline development) and a credential-injection seam, for teams that want
  per-identity custody and zero-credential contained workers.

**Internal-only.** Fleet operations and deployment machinery used to develop CE
itself are not part of the product and are not documented here.

## Current Status

As of June 25, 2026:

- The Engine is pilot-ready: the Scope-to-PR-to-review-to-merge loop, the product
  CLI surface, the read-model/cockpit surface, and the two install paths are in
  tree and dogfooded.
- The optional add-ons above (forge-automation, cockpit, containment,
  secret-identity) are in active development at varying maturity. The
  `LocalSecretIdentityBackend` covers offline development without any external
  secret store.
- The package artifacts are at `creator-engine-validator` version `0.3.0`. There
  is no public product tag or GitHub release yet; release publication is a
  separate governed workstream. See
  [`docs/delivery/VERSIONING_AND_RELEASE_POLICY.md`](./docs/delivery/VERSIONING_AND_RELEASE_POLICY.md).
- Linux x86_64 and aarch64 cp314 wheelhouses are in-tree for the runtime and
  developer/test dependency sets, enabling the offline validator/test path on
  both architectures.
- The website is live at `creator-engine.dev`; this README is the repo
  orientation, not the website source.

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
  `launch`, `lane`, `worker`, `ledger`, `fanin`, `queue`, `dequeue`, `event`, `pcl`,
  `brain`, `orchestrator`, `connector`, `containment-probe`, `reviewer-triage`, `claim`,
  `pickup`, `dispatch`, `playbook`, `surfaces`, `bootstrap`, `verify-install`, `update`, `onboard`, `publish-branch`,
  `harness-matrix`, `containment-status`, `validate-pr`, `automerge-decide`, and `automerge-status`.
  The as-built v1 command groups are `ce check`, `ce doctor`, `ce init`,
  `ce launch`, `ce hud`, `ce lane`, `ce worker`, `ce ledger`, `ce fanin`,
  `ce queue`, `ce dequeue`, `ce event`, `ce pcl`, `ce brain`, `ce orchestrator`, `ce connector`,
  `ce containment-probe`, `ce reviewer-triage`, `ce claim`, `ce pickup`,
  `ce dispatch`, `ce playbook`, `ce surfaces`, `ce bootstrap`
  (offline provisioning for a source-clone controller/seat venv),
  `ce verify-install` (post-install provenance verification for a pinned CE
  release venv), `ce update` (signed in-place CE release updates, with
  `ce update --check` as the read-only installed-vs-available data source),
  `ce surfaces check-updates` (read-only upstream availability reporting for
  entries in `surfaces/manifest.yaml`),
  `ce publish-branch` (host-side publish gate for contained
  seats' commit-only branches), and `ce onboard` (the first-run one-shot
  orchestrator: it sequences the
  preflight doctor, install detection/acquisition, the `ce verify-install`
  provenance gate, the managed profile PATH block, `ce init` + `ce brain init`,
  and exactly one governed first launch — idempotent, resumable, and gracefully
  degrading; `ce onboard --emit-manifest` emits a machine-readable description of
  each phase's blast-radius and consequence-class so a user's own agent can plan
  and gate the install under the governed-install rail). `ce pickup`
  is a read-only, Search-API-backed autonomous forge
  work-pickup poller for fine-grained PAT compatibility. `ce playbook`
  lists, shows, and plans `run --dry-run` for public dual-use `PLAYBOOK.md`
  files by projecting them into the internal playbook descriptor without
  executing side effects. `ce publish-branch`
  verifies attribution and fast-forward/no-force policy, pushes through
  host-side git credentials, and records the publish to the Side-Effect Ledger.
  `ce harness-matrix`
  is the PROBED harness-support capability matrix: it derives the
  harness x {Ring-0, Ring-1, Ring-2, containment} support table by inspecting
  the live adapter specs / committed config at runtime (never hand-asserted in
  prose), emitting Markdown by default or `--json`. `ce containment-status`
  is the fleet-wide containment attestation: it probes each requested
  seat's live PID with `ce containment-probe` semantics and reports
  `{seat, contained, backend, herdr_session, ring1}` as JSON or a table, failing
  closed for unprobeable seats and never deriving containment from config or
  prose. `ce validate-pr` runs the governed PR preflight locally against the
  committed `base..HEAD` state — the same gates CI enforces (check-examples,
  work-sizing, path-manifest, changelog, and the offline test suite) with a
  clean, scrubbed environment — so an author can confirm a PR is governance-valid
  before pushing instead of discovering it in CI. `ce automerge-decide`
  classifies a PR's changed paths into a mutation class (fail-closed: unknown
  or privileged paths map to the most-privileged GESTURE class) and emits an
  `AUTO` or `GESTURE_REQUIRED` decision and rationale by composing the existing
  `size_ceremony` ceremony table with the path classifier — dry-run only,
  never merges, never mints a capability marker. `ce automerge-status`
  is the read-only companion reader: it loads and displays the dry-run
  decision log records emitted by `ce automerge-decide` runs — never
  merges, never arms, never mutates state. `ce orchestrator status`
  reads and validates Orchestrator runtime records under local state and renders
  a human or JSON cockpit summary; it is observe-only and has no dispatch,
  merge, gate, approval, arm, or mutation behavior. `ce dequeue` removes one queued
  PR from GitHub's merge queue through the governed v3 forge bridge. `ce hud` is an alias for the
  visible `ce launch` Controller-seat
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

For an end-to-end first host path, use the
[`zero to governed seat quickstart`](./docs/guide/zero-to-governed-seat-quickstart.md).

Bootstrap prerequisites: the host must already have stock OpenSSH `ssh-keygen`
and the basic shell tools named by the installer. If any are missing, the
installer refuses before fetching artifacts and prints one remediation block
with exact Debian/Ubuntu, Fedora/RHEL/CentOS, and Alpine package commands.
Install them only after reviewing the package action; the E1 installer will not
run `sudo` before it has verified the signed spec. Python 3.14 and `uv` are not
host prerequisites for the one-liner: after verification, E1 fetches the
manifest-pinned `uv` tarball, verifies it, and installs CPython 3.14 in user
space if needed.

1. **Public one-liner.**

   ```bash
   curl --proto '=https' --tlsv1.2 -fsSL https://creator-engine.dev/install.sh | bash
   ```

   The script fetches the signed agent-native spec, verifies it against the
   pinned `ce-root-v1` OpenSSH trust root, verifies the wheelhouse manifest and
   every artifact hash, obtains Python 3.14 through the pinned `uv` artifact if
   needed, installs `creator-engine-validator==0.3.0` offline, proves `cev3`,
   and runs authenticated inventory. This E1 bootstrap does **not** run sudo,
   automate the GitHub App click, mutate branch protection, or create/adopt a
   project. A successful E1 run is inventory-only; a full governed seat still
   needs host and GitHub answers, an explicit `ce onboard --plan`, and a later
   governed `ce onboard --apply`.

2. **Clone plus offline dependency wheelhouse.**

   ```bash
   git clone https://github.com/creator-engine/creator-engine.git
   cd creator-engine
   python3.14 -m venv .venv
   CE_VALIDATOR_PYTHON="${CE_VALIDATOR_PYTHON:-.venv/bin/python}"
   "$CE_VALIDATOR_PYTHON" -m pip install --no-index --find-links validators/wheelhouse -r validators/requirements.txt
   PYTHONPATH=validators "$CE_VALIDATOR_PYTHON" -m creator_engine_validator --list-checks
   ```

   The runtime wheelhouse carries dependencies only; first-party validator code
   runs from the checkout through `PYTHONPATH=validators`. See
   [`validators/README.md`](./validators/README.md) for the full offline runtime
   and test install commands.

The agent-native install spec is served as
[`docs/llms-install.md`](./docs/llms-install.md) and must be verified before
execution. That file and the served installer are trust-root surfaces; ordinary
documentation edits must not mutate them.

**Trust anchor (independent channel):** the `ce-root-v1` signing key fingerprint
is `SHA256:mkX7cRfHNrx6mtK8Ek30CcRn6fbfIPK/SU/6KKc0AOQ` (ed25519). This in-repo
record — served by GitHub, independent of `creator-engine.dev` — is the primary
out-of-band anchor. A matching DNS TXT record exists at
`_ce-root-v1.creator-engine.dev`. Verify the served key's fingerprint against
either anchor before trusting the signature. See
[`docs/security/trust-anchors.md`](./docs/security/trust-anchors.md) for the full
anchor table, both signing keys, and the trust model.

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
  [`docs/decisions/0005-openbao-secret-identity-backend.md`](./docs/decisions/0005-openbao-secret-identity-backend.md);
  the stand-up of the OpenBao micro-unit and `SecretIdentityBackend` is recorded
  in [`docs/decisions/ADR-0012-openbao-micro-unit-standup.md`](./docs/decisions/ADR-0012-openbao-micro-unit-standup.md).

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

Use Python 3.14 and the dependency venv for source-backed validation:

```bash
CE_VALIDATOR_PYTHON="${CE_VALIDATOR_PYTHON:-.venv/bin/python}"
PYTHONPATH=validators "$CE_VALIDATOR_PYTHON" -m creator_engine_validator --list-checks
PYTHONPATH=validators "$CE_VALIDATOR_PYTHON" -m creator_engine_validator check examples/well-formed/
PYTHONPATH=validators "$CE_VALIDATOR_PYTHON" -m creator_engine_validator check-examples
```

For the full validator test suite, install both runtime and dev/test
wheelhouses, then run:

```bash
CE_VALIDATOR_PYTHON="${CE_VALIDATOR_PYTHON:-.venv-test/bin/python}"
PYTHONPATH=validators "$CE_VALIDATOR_PYTHON" -m pytest validators/tests/ -q
```

CI also enforces per-PR path-manifest fidelity. New PRs should include a carrier
under `.ce/pr-manifests/<branch-slug>.md` whose path list exactly matches
`base..HEAD`.

## Canonical Docs

- Current execution status: the **Current Status** section above and the docs
  site. (Internal program roadmaps are tracked privately.)
- Architecture index:
  [`docs/architecture/README.md`](./docs/architecture/README.md).
- Approval-capability wall:
  [`docs/security/ce234-approval-capability-wall.md`](./docs/security/ce234-approval-capability-wall.md)
  and the arming runbook
  [`docs/devops/openbao-approval-wall-arming.md`](./docs/devops/openbao-approval-wall-arming.md).
- Web control UI direction (accepted, design):
  [`docs/decisions/ADR-0008-web-control-ui.md`](./docs/decisions/ADR-0008-web-control-ui.md).
- Installer contract:
  [`docs/contracts/installer.md`](./docs/contracts/installer.md).
- New here? Start with the welcome / onboarding front door:
  [`docs/guide/welcome.md`](./docs/guide/welcome.md).
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
