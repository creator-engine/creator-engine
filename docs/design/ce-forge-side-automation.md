# CE Forge-Side Automation Design

Status: design pass. This document proposes the Layer 3
forge-side automation posture; it does not authorize product code, live
repository settings changes, credential creation, workflow installation, or
merge/deploy operations.

## Doctrine Grounding

This design is grounded in existing CE doctrine and uses those documents as
constraints rather than replacing them:

- `docs/architecture/stage-vocabulary.md` defines the user-facing
  `Frame→Shape→Build→Review→Ship` pipeline over the conserved
  mechanical state machine.
- `docs/architecture/v3-spec.md` defines the `ce-install.yaml` direction for
  repo setup, branch protection/rulesets, CODEOWNERS, GitHub App token minting,
  reviewer identity, and the plan-tier wall for enforceable review.
- `docs/operations/GITHUB_NATIVE_COORDINATION_PROTOCOL.md` defines GitHub as
  the rented coordination/review/merge plane, branch-protection desired state,
  required checks, CODEOWNERS, and the distinction between CI evidence and
  ratification.
- `docs/operations/ONBOARD_APPLY_PROTOCOL.md` defines signed-spec onboarding,
  plan/apply separation, ordered apply legs, append-only evidence, and
  brownfield adoption gates.
- `validators/creator_engine_validator/ce_onboard.py` defines the first-run
  onboarding phase table and consequence-class/reversibility framing that a
  forge-side setup plan should reuse instead of inventing a second risk model.
- `docs/contracts/brownfield-adoption.md` defines the non-destructive join-PR
  posture, dual live-forge escalation, two-token read/write split, and
  fail-closed secret scrub.
- `docs/operations/WORKTREE_LEASE_PROTOCOL.md`,
  `docs/architecture/parallel-controller-orchestration.md`,
  `docs/architecture/work-claim-locks.md`, and `docs/contracts/forge-claim.md`
  define current local worktree leases, active-work claims, forge-visible
  advisory claims, and the honest limit that those projections are not database
  mutexes.
- `docs/governance/AUTHORITY_AND_RATIFICATION_MODEL.md`,
  `docs/contracts/authority-matrix.md`, and
  `.github/BRANCH_PROTECTION_POLICY.md` define author/approver separation,
  privileged mutation classes, and the invariant that CI, agents, and GitHub do
  not ratify.
- `playbooks/controller/workflow.ce.yml`,
  `playbooks/controller/briefs/merge-gate.md`, and
  `playbooks/controller/briefs/courier-forge-op.md` define controller work
  claims, merge/preflight gates, and the current courier-forge-op stopgap.
- `docs/decisions/ADR-0007-egress-gateway-publish-broker.md` and
  `docs/architecture/egress-broker.md` define brokered forge egress: author,
  transport, and merge stay separated, and a deterministic gateway holds forge
  egress instead of an agent.
- `docs/delivery/REVIEW_GATE.md`, `playbooks/reviewer/*`, and
  `.claude/agents/reviewer.md` define distinct read-only reviewer evidence and
  the reviewer persona boundary.
- `.claude/agents/implementer.md` and `docs/operations/HARNESS_SEAT_CONTRACT.md`
  define role-shaped tool absence, least privilege, and no self-approval/merge
  authority.
- `docs/contracts/devops-privileged-action-broker.md` defines the
  authority/custody/execution split for high-blast actions and the requirement
  for value-free, ratified envelopes.
- `.github/CODEOWNERS` and `.github/workflows/validate.yml` are current
  forge-side setup examples: CODEOWNERS names the current reviewer set, while
  Validate runs read-only required evidence including playbook checks,
  manifest fidelity, and merge-group CI.
- `docs/contracts/authoring-a-governed-pr.md` defines carrier discipline:
  governed PRs carry one changelog carrier and one path-manifest carrier, and
  the manifest is generated from the committed diff rather than hand-edited.

## Layer Role

Forge-side automation is CE Layer 3: the automation that lives at the forge
boundary and moves work through triage, CI, workflow orchestration, review
routing, queueing, and delivery. It is not the CE spine. The spine remains the
repo-native governance/audit model: Scope, tasks, ratification records,
review evidence, runtime evidence, carriers, changelog fragments, and
completion reports.

The layer's job is to configure and operate external moving parts:

- GitHub App installation and short-lived permission envelopes.
- Branch protection, required checks, CODEOWNERS, merge queue/ruleset posture,
  and workflow installation.
- Issue/PR/CI trigger ingestion, deduplication, and queueing.
- Cloud triage and CI-agent dispatch surfaces.
- Resource locks and operations board read models.
- Workflow catalog publication and workflow-memory proposals.

## Audit-Independence Constraint

CE may design, set up, deploy, and interface with the forge-side automation
layer, but the layer must stay structurally outside the spine. Audit
independence lives in two facts:

1. Where the automation runs: in the forge, CI, cloud triage worker, broker, or
   other runtime outside the governed authoring seat.
2. Who can mutate it: only an Operator-ratified mechanism may mutate live forge
   settings, App grants, workflow files, privileged broker policy, or
   branch-protection/ruleset posture.

CE must not pretend forge automation is absent. Instead, CE binds it at the
boundary and records evidence. This preserves the grader-outside-the-agent
thesis already present in `docs/architecture/stage-vocabulary.md` and
`docs/operations/GITHUB_NATIVE_COORDINATION_PROTOCOL.md`: the agent authors,
but the boundary grader enforces path scope, review, required checks, and merge
eligibility.

Practical constraints:

- No agent, CI job, GitHub App, or workflow may ratify. They emit evidence only.
- Live forge setting mutation is a privileged operation and requires explicit
  Operator ratification, consistent with `.github/BRANCH_PROTECTION_POLICY.md`.
- Product code must treat forge-side automation outputs as external evidence,
  not as self-authenticating authority.
- Any automation that can affect merge/deploy/repo settings must have a
  separate audit trail, rollback evidence, and a value-free authority record.

## Import Adoption Map

| Import item | CE mechanism | Governance posture |
| --- | --- | --- |
| 1. Trigger taxonomy | Add a CE trigger vocabulary for forge events: issue opened/edited/labeled, PR opened/synchronized/reviewed, required-check state, merge-queue state, schedules, webhook deliveries, @mention/slash commands, and delay/dedup windows. Map each trigger to current CE surfaces such as `docs/contracts/github-issue-intake.md`, `docs/operations/CE_EVENT_PROTOCOL.md`, work claims, and future cloud triage/CI-agent queues. | Vocabulary first, runtime later. Triggers may enqueue or propose work; they never authorize mutation. Dedup must use deterministic evidence, following `docs/contracts/forge-claim.md`, not unevidenced model judgment. |
| 2. Workflow-as-ratifiable-artifact | Define an in-repo workflow graph artifact, for example `workflow.json`, plus sibling step-prompt Markdown files. Treat the graph as a ratifiable artifact and publish approved graphs into a template catalog. The existing `.specify/workflows/workflow-registry.json`, playbook `workflow.ce.yml` files, and `docs/contracts/playbook-format.md` are local precedent. | Workflow changes are docs/governance by default and can become privileged when they alter authority, tools, CI, deploy, or live forge posture. Catalog entries are proposed, reviewed, versioned, and Operator-ratified before active use. |
| 3. Per-artifact resource locks and priority queues | Extend current worktree-centered leases and claims from `docs/operations/WORKTREE_LEASE_PROTOCOL.md`, `docs/architecture/parallel-controller-orchestration.md`, and `docs/architecture/work-claim-locks.md` to forge-artifact keys such as `owner/repo:issue:123`, `owner/repo:pr:456`, `owner/repo:branch:feature`, and `owner/repo:workflow:validate`. Surface active locks and queues in an ops board read model. | Locks are advisory unless backed by an atomic service. The design must keep the honest no-hard-lock posture, deterministic winner rules, staleness policy, and append-only release/takeover history. Dispatch may refuse without a held claim. This is an extension because current locks are worktree-centered, not forge-artifact-centered. |
| 4. Role-scoped agents with physically absent tools | Adopt role-scoped persona definitions that physically omit tools: reviewer/verification has no write/comment/approve/merge credential, implementer has one scoped branch write token, triage has read/comment-only authority, CI agent has no ratification authority. Use `docs/delivery/REVIEW_GATE.md`, `playbooks/reviewer/*`, `.claude/agents/reviewer.md`, `.claude/agents/implementer.md`, and `docs/operations/HARNESS_SEAT_CONTRACT.md` as precedent. | Tool absence is preferred over prompt-only prohibition. Persona catalog entries are governed artifacts; privileged tool grants require ratification and short TTL envelopes. Author/reviewer separation is mandatory; read-only reviewer evidence is not ratification. |
| 5. Retrospective-fed workflow memory | Allow retrospectives to propose workflow memory: trigger improvements, prompt amendments, runbook updates, catalog variants, and guardrail changes. Feed proposals into the Operator ratification queue instead of applying them automatically. | CE explicitly rejects self-mutating workflows. Memory proposals are evidence and draft patches only. They become active only after human ratification and normal PR review. |
| 6. Session override grammar | Adopt a closed command grammar for governed sessions, including `/done`, `/quit`, `/blocked`, `/escalate`, and `/handoff` class commands. Map commands to completion reports, CE-event blocks, dispatch state, and no-op/refusal paths. | Overrides are control intents, not authority grants. `/done` can request closeout evidence; it cannot approve, merge, ratify, or bypass required checks. `/quit` must preserve audit state and avoid partial hidden side effects. |

## Non-Import Guardrails

CE must not import the following patterns:

- Vendor-resident authority. A vendor runtime may execute a step, but CE
  authority stays in repo-governed artifacts, Operator ratification, and
  external boundary gates.
- Code-leaves-premises by default. External cloud triage or CI must be an
  explicit posture with scope, data class, and approval; local/on-prem/default
  containment remains available.
- Consumption-credit billing as the governance model. CE should preserve
  subscription-headroom honesty and resource envelopes rather than hiding cost
  inside per-action credits.
- Auto-applied self-mutation. Workflow memory, prompt improvement, and policy
  changes require ratified PRs or equivalent governed artifacts.
- UI-as-source-of-truth. UI may render status, queues, and controls; the source
  of truth remains forge/repo artifacts, evidence records, and signed or
  hash-bound state.
- Broad standing App credentials. CE uses per-dev Apps, per-task or
  per-operation permission ceilings, short TTL tokens, and explicit revoke or
  expiry evidence. This follows `docs/contracts/brownfield-adoption.md` and
  `docs/contracts/devops-privileged-action-broker.md`.

## Slice 1 Capability: Forge-Side Setup Onboarding

Slice 1 productizes CE's own forge-side setup as an onboarding capability. The
goal is to make `ce-install.yaml` plus an onboarding plan/apply surface set up
branch protection or rulesets, CI gate wiring, GitHub App provisioning,
CODEOWNERS, required checks, reviewer identity, and evidence capture as a
repeatable CE onboarding flow instead of hand-built repo administration.

This capability is a sibling of the existing infra onboarding lane. It extends,
not replaces, the `ce onboard` consequence-class model in
`validators/creator_engine_validator/ce_onboard.py` and the E2/E3 posture in
`docs/operations/ONBOARD_APPLY_PROTOCOL.md` and
`docs/contracts/brownfield-adoption.md`.

### Inputs

The onboarding plan needs value-free inputs:

- Target forge and repo: `owner/repo`, default branch, project visibility, and
  whether the repo is greenfield, already CE-governed, or brownfield adoption.
- `ce-install.yaml` or equivalent install contract version, plus the desired
  setup profile and plan-tier evidence from `docs/architecture/v3-spec.md`.
- Operator identity and ratification reference for live forge mutations.
- Desired branch-protection profile: required checks, review count,
  CODEOWNERS posture, conversation resolution, linear history, force-push and
  deletion policy, admin enforcement, and merge queue/ruleset intent.
- CI profile: validation workflow source, required context names, Python/tooling
  versions, offline wheelhouse posture, and `merge_group` trigger posture.
- GitHub App model: per-dev App or org App, requested permission ceiling,
  webhook events, callback URLs if any, installation target, and token TTL.
- Reviewer model: individual CODEOWNERS entries or team target, plus evidence
  that reviewer identities are distinct from author identities. Current dogfood
  inputs include `.github/CODEOWNERS`.
- Brownfield preservation facts: existing workflows, required checks,
  protections, CODEOWNERS, branch conventions, and secret-scrub posture.
- Brokered forge-egress posture: current courier stopgap, ADR-0007 gateway
  readiness, egress-broker config refs, and whether the setup may publish by
  join PR or must stop at a plan.
- Rollback target: current protection/ruleset/workflow/App-state snapshot
  references, never secret values.

### Preconditions

The capability must fail closed before any live mutation unless:

- The install spec is signed or otherwise accepted by the same trust path used
  by `docs/operations/ONBOARD_APPLY_PROTOCOL.md`.
- The plan is explicit about greenfield, plain-join, or brownfield adoption.
- The plan's phase records carry consequence class, reversibility, and decision
  posture consistent with `ce_onboard.py` rather than a setup-specific risk
  vocabulary.
- Existing branch protection, checks, workflows, CODEOWNERS, and App grants
  have been inventoried and will not be weakened.
- The target plan tier can enforce the requested review and protection posture;
  an unenforceable free-private plan refuses before mutation, as described in
  `docs/architecture/v3-spec.md`.
- Required scanners and scanner pins are present for brownfield adoption, as in
  `docs/contracts/brownfield-adoption.md`.
- The Operator has ratified the live forge setup operation and its target repo.
- Credential grants are scoped, time-limited, and separated by read/write
  posture. Broad standing `administration:write` is not granted to an agent.
- Brokered forge egress is explicit: either the run is plan/join-PR only, uses
  the current courier-forge-op stopgap, or routes through a deterministic broker
  consistent with ADR-0007.
- A rollback/readback plan exists for each live setting class.
- A work/resource claim exists for the target setup item when competing
  controllers could dispatch the same onboarding run.

### Pipeline

| Stage | Capability behavior | Evidence |
| --- | --- | --- |
| Frame | Classify the target repo and setup goal. Detect current forge posture, existing workflows, CODEOWNERS, App grants, branch protection/rulesets, required checks, default branch, merge queue state, reviewer identity, and plan-tier enforceability. Identify whether this is greenfield, plain-join, or brownfield adoption. | Inventory JSON with hashes, value-free setting summaries, consequence-class candidates, detected gaps, conflict/refusal list, and source paths cited back to the plan. |
| Shape | Produce a ratifiable setup plan. The plan states desired state, non-destructive unions, exact live mutations, permission envelopes, rollback snapshots, acceptance criteria, broker/courier posture, and per-phase consequence class. It maps the plan to CE mutation classes and names all non-import guardrails. | Ratifiable `ce-install.yaml`/plan artifact, Operator prompt digest/ref, closed path set for generated repo files, carrier-generation instruction, and a no-weaken proof for preserved checks/protections. |
| Build | Execute only the ratified plan. For plan-only runs, write no live settings. For apply runs, configure App/protection/workflows/CODEOWNERS through idempotent desired-state operations with readback after each step. Brownfield repos use a join PR where possible and do not direct-push the default branch. Brokered forge egress is used where the plan requires publish/PR transport from a contained context. | Append-only setup ledger entries, API readback snapshots, generated PR refs if join-PR mode, token grant/revocation refs, broker/courier audit refs, and rollback references. |
| Review | Grade the setup result outside the agent. Confirm required checks exist, branch protection or ruleset posture matches desired state, CODEOWNERS covers protected paths, App permissions equal the ceiling, reviewer identity is distinct/read-only, and CI remains evidence-only. | Review evidence packet, diff between desired and observed forge state, CI dry-run/readback evidence, independent reviewer verdict, and explicit no-ratification statement. |
| Ship | Deliver the configured repo or a join PR. For live setup, produce a completion report and handoff. For deferred or refused setup, ship the explicit refusal/no-change result with remediation. | Completion report, final setup manifest, open PR link or live-setting readback refs, generated carrier refs where a PR exists, rollback instructions, and residual-risk notes. |

### Productization Gaps

- No productized forge-side setup onboarding artifact exists. `docs/architecture/v3-spec.md`
  names `ce-install.yaml`, and `ONBOARD_APPLY_PROTOCOL.md` defines executor
  legs, but there is no single forge-side setup contract that a customer repo
  can review, ratify, apply, and re-run.
- Current docs describe CODEOWNERS and protection policy, but the onboarding
  capability needs a structured desired-state profile for customer repos.
- Locks are worktree-centered or broad work-item-centered today. They do not yet
  model forge-artifact-centered resources such as one issue, PR, branch,
  workflow, or App installation as first-class queue keys.
- GitHub App provisioning needs a value-free setup model that distinguishes
  per-dev Apps, org/team Apps, callback/webhook settings, and token mint
  ceilings without storing private keys or broad standing credentials.
- Workflow-as-artifact exists conceptually through `workflow.ce.yml` and
  `.specify/workflows/workflow-registry.json`, but not as a ratifiable
  `workflow.json` plus sibling step-prompt catalog.
- Workflow memory and persona catalog imports should remain later slices. Slice
  1 should not create a general automation platform before the setup path is
  productized.
