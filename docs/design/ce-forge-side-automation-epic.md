# Proposed Epic: Forge-Side Automation Layer

Status: proposed epic for Operator ratification. Do not file these tickets
automatically. This is a dependency-ordered slice plan for the forge-side
automation epic proposal.

## Epic Goal

Productize CE's forge-side automation layer as the external boundary where CE
sets up, observes, and governs GitHub/CI/App/workflow automation without moving
authority into an agent runtime or weakening audit independence.

## Slices

| Order | Slice | One-line scope | Dependencies |
| --- | --- | --- | --- |
| 1 | Forge-side setup onboarding | Productize `ce-install.yaml`/plan/apply setup for branch protection or rulesets, required checks, GitHub App provisioning, workflow wiring, CODEOWNERS, reviewer identity, broker/courier posture, readback, rollback, and completion evidence as a `Frame→Shape→Build→Review→Ship` onboarding capability. | `docs/architecture/v3-spec.md`, `docs/operations/ONBOARD_APPLY_PROTOCOL.md`, `validators/creator_engine_validator/ce_onboard.py`, `.github/CODEOWNERS`, `.github/workflows/validate.yml`, Operator ratification for live forge mutation. |
| 2 | Trigger taxonomy | Define the cross-forge trigger vocabulary for issue, PR, CI, schedule, webhook, @mention/slash, delay, and dedup events; map each trigger to CE triage/CI-agent surfaces. | Slice 1 setup model so installed repos know which events are safe to subscribe to; CE-event, forge-claim, and brokered-egress doctrine. |
| 3 | Workflow-as-artifact catalog | Define ratifiable `workflow.json` plus sibling step-prompt Markdown artifact shape and publish a reviewed template catalog seeded from existing playbook workflows. | Slice 2 trigger taxonomy; existing `workflow.ce.yml` concept, playbook format, and workflow registry precedent; Operator ratification path for active workflows. |
| 4 | Resource locks and ops board | Extend current worktree-centered lease/claim doctrine to forge-artifact resource keys and render locks, priority queues, staleness, and takeovers in an ops board read model. | Slice 2 trigger taxonomy; `WORKTREE_LEASE_PROTOCOL`, `parallel-controller-orchestration`, work-claim locks, forge-claim contracts; no-hard-lock honesty retained. |
| 5 | Persona catalog with absent tools | Catalog role-scoped forge/triage/CI/review personas with physically absent tools and credential ceilings, including read-only reviewer, implementer, triage, CI-agent, setup-agent, courier, and broker-adjacent profiles. | Slice 1 setup permissions and Slice 3 workflow catalog; `REVIEW_GATE`, reviewer playbooks, harness-seat contract, and `.claude/agents/*` role boundaries. |
| 6 | Ratification-gated workflow memory | Route retrospectives and run outcomes into workflow-memory proposals that can amend triggers, workflows, prompts, and personas only after Operator ratification. | Slices 3 and 5; authority/ratification model; completion-report and review evidence feeds. |

## Out-of-Scope For This Epic

- Vendor-resident authority or vendor runtime as the CE source of truth.
- Broad standing App credentials or unbounded `administration:write`.
- Auto-applied self-improving workflows.
- UI-only state, hidden queue state, or non-auditable setup mutations.
- Product code implementation in the design slice.
