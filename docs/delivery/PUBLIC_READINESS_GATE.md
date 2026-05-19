# Public-readiness gate

**Status**: Post-Sprint-0 delivery-view gate artifact. Part of the
**minimum repo-native delivery control plane** and **not a Jira
clone**. Layered onto, and subordinate to, the Feature 001 substrate,
the Feature 002 operating model, the landed open-source / public-
launch readiness substrate (PR #20 / `35bf85f` and PR #21 /
`5b762f9`), the workflow-hardening protocol set (PR #22 / `d892cd3`,
PR #23 / `3dc45a1`, and PR #44 / `30327aa`), and the
[`./RELEASE_DEPLOY_GOVERNANCE.md`](./RELEASE_DEPLOY_GOVERNANCE.md)
release / merge / deploy policy. A fresh clone is sufficient to read
this gate; no external tracker credential, GitHub setting, or
instance-local runtime is required.

## a. Purpose

This document is the canonical delivery-view artifact for the
**public-readiness gate**. Its job is to let a fresh clone answer
two questions from repo-visible state alone:

> What public-readiness substrate has already landed on the canonical
> branch, and what residual privileged work remains before any future
> Source-ratified decision to flip the repository to public could be
> executed?

and

> What is this gate *not* authorizing, so that landing this artifact
> does not — directly or by implication — change the repository's
> visibility, its live GitHub settings, or any other privileged
> external surface?

The public-readiness gate is **docs-only**. It records readiness
posture; it does not execute, schedule, or authorize a visibility
change or any other live GitHub mutation. The actual visibility flip
is a separately-Source-ratified privileged envelope; see §f.

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) | Apex governance authority. Conflicts resolve in favor of the constitution. |
| Feature 001 substrate (`specs/001-v0-1-governance-substrate/`, `docs/contracts/`, `schemas/`, `validators/`, `examples/`, `tenants/`) | Privileged-class rule (FR-008), author/approver separation (FR-007), ratification flow (FR-016). |
| Feature 002 spec at `specs/002-canonical-docs-and-operating-model/spec.md` | Operating-model invariants. |
| [`./BACKLOG.md`](./BACKLOG.md) | Authoritative carrier of backlog rows; the public-readiness gate row and its residual deferred items are recorded there. |
| [`./RELEASE_DEPLOY_GOVERNANCE.md`](./RELEASE_DEPLOY_GOVERNANCE.md) and the four Slice F content docs ([`./RELEASE_CANDIDATE_CHECKLIST.md`](./RELEASE_CANDIDATE_CHECKLIST.md), [`./MERGE_APPROVAL_CHECKLIST.md`](./MERGE_APPROVAL_CHECKLIST.md), [`./DEPLOYMENT_APPROVAL_POLICY.md`](./DEPLOYMENT_APPROVAL_POLICY.md), [`./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md`](./ROLLBACK_AND_POST_RELEASE_EVIDENCE.md)) | Release / merge / deploy governance policy already landed under Slice F (PR #16 / `cb7f94a`). Public-readiness is a sibling policy gate, not an amendment to Slice F. |
| Workflow-hardening protocol set ([`../operations/CONTROLLER_BOUNDARY_POLICY.md`](../operations/CONTROLLER_BOUNDARY_POLICY.md), [`../operations/NO_COPY_PASTE_PATTERN.md`](../operations/NO_COPY_PASTE_PATTERN.md), [`../operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`](../operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md), [`../operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md`](../operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md), [`../operations/ROOT_WORKTREE_INVARIANT.md`](../operations/ROOT_WORKTREE_INVARIANT.md)) | Post-Sprint-0 substrate; durable landed evidence PR #22 / `d892cd3`, PR #23 / `3dc45a1`, and PR #44 / `30327aa`. Provides the controller-seat, pointer-only-relay, path-manifest-fidelity, transcript-archive, and root-worktree-invariant controls that any future privileged envelope (including the visibility flip) must observe. |

Where this gate and any upstream source of truth disagree, the
upstream source of truth wins until Source ratifies a correction.

## c. Public-readiness gate semantics

The **public-readiness gate** is the named delivery-view checkpoint
that separates two distinct activities:

1. **Public-readiness substrate / documentation** — the policy,
   documentation, and governance artifacts a fresh clone needs in
   order to *be readable* by an external contributor without
   exposing the repository to the public network. This activity is
   `docs` / `governance`-class and has already substantially landed
   on the canonical branch under PR #20 (`35bf85f docs: add
   open-source readiness materials (#20)`) and PR #21 (`5b762f9
   fix: remediate public launch readiness blockers (#21)`); see
   [`./BACKLOG.md`](./BACKLOG.md) §e.8. This artifact records that
   landed state and the residual substrate-side work, and it is
   itself a substrate-side artifact.
2. **Public visibility / live GitHub settings flip** — the
   privileged external mutation that would change the repository
   from private to public, apply branch-protection rulesets to the
   live remote, ratify any CODEOWNERS file, or otherwise mutate the
   live GitHub surface. This activity is privileged (`governance` /
   `security` / `deploy`-class per Feature 001 FR-008) and is
   **not** authorized by this gate. See §f for the named owning
   future privileged envelope.

The gate's load-bearing rule is:

> Landing this gate artifact, and any §d / §e items shaped under
> docs-only envelopes, MUST NOT flip the repository to public, MUST
> NOT apply live branch-protection / ruleset settings, MUST NOT
> ratify CODEOWNERS, MUST NOT execute any future redaction-gate
> corpus, and MUST NOT perform any other live GitHub-settings
> mutation.

The distinction between substrate / documentation work (this gate)
and the privileged visibility / settings flip (§f) is preserved
throughout this document and is preserved by every downstream gate
that consumes it.

## d. Landed public-readiness substrate

The following substrate has already landed on the canonical branch
and is durable evidence under [`./BACKLOG.md`](./BACKLOG.md) §e.8:

| Substrate | Durable evidence | Role |
|---|---|---|
| Open-source readiness materials | PR #20 / `35bf85f docs: add open-source readiness materials (#20)` | Repository-readable open-source posture artifacts authored under the post-Sprint-0 `post-sprint-0/oss-readiness` work item. |
| Public-launch readiness blocker remediation | PR #21 / `5b762f9 fix: remediate public launch readiness blockers (#21)` | Remediations to substrate-side public-launch readiness blockers identified during the OSS-readiness landing. |

Per [`./BACKLOG.md`](./BACKLOG.md) §e.8, both items are `Done` on
the delivery view. They are substrate / documentation-class work
that did **not** mutate live GitHub settings, did **not** flip the
repository to public, and did **not** apply live branch-protection
rulesets.

The workflow-hardening protocol set (PR #22 / `d892cd3`, PR #23 /
`3dc45a1`, and PR #44 / `30327aa`; see
[`./BACKLOG.md`](./BACKLOG.md) §e.9 and §e.20) is a parallel
post-Sprint-0 substrate landing. It is not itself a public-
readiness item, but the controller-seat-boundary, pointer-only-
relay, path-manifest-fidelity, transcript-archive, and root-
worktree-invariant controls it codifies are upstream sources of
truth that any future privileged envelope under §f MUST observe.

## e. Residual checklist for future separate ratification

The following items remain `Deferred` on the delivery view. Each
one is itself a privileged-class mutation per Feature 001 FR-008
and MUST NOT be consumed except under its own separately-Source-
ratified envelope. Landing this gate artifact does NOT advance any
of the items below past `Deferred`.

1. **Repository visibility flip.** Changing the canonical
   repository from private to public on the remote (a `governance`
   / `security`-class live GitHub mutation). Owning future
   privileged envelope: §f.
2. **Live branch-protection / ruleset application.** Applying any
   branch-protection rules or rulesets to the live `main` branch on
   the remote, beyond the file-based policy already authored under
   `.github/BRANCH_PROTECTION_POLICY.md` (landed under Slice C as
   PR #12 / `1cfb955`). The file-based policy and the live remote
   setting are explicitly two separate things; this checklist names
   only the live remote setting, which remains unimplemented. Owning
   future privileged envelope: Feature 003 (`feature-003`) under a
   separately Source-ratified privileged `governance` envelope per
   [`./BACKLOG.md`](./BACKLOG.md) §e.3.
3. **Any CODEOWNERS decision.** Authoring, ratifying, applying, or
   removing a `CODEOWNERS` file. CODEOWNERS was deliberately
   excluded under the Slice C "as applicable" qualifier (see
   [`./BACKLOG.md`](./BACKLOG.md) §c.3) and remains an open
   privileged decision. Owning future privileged envelope: Feature
   003 (`feature-003`) under a separately Source-ratified privileged
   `governance` envelope.
4. **Any future redaction-gate corpus.** Authoring or executing a
   redaction-gate corpus over the tracked tree for public-readiness
   purposes (a `redaction`-class privileged mutation per Feature
   001 FR-008). No redaction-gate corpus is shaped, authorized, or
   executed by this gate. Owning future privileged envelope: a
   separately Source-ratified privileged `redaction` envelope,
   independent of this gate and independent of §f.
5. **Any future GitHub settings mutation.** Mutating any live
   GitHub repository setting — repository visibility, topics,
   homepage, description, branch protection, rulesets, Actions
   secrets, environments, deploy targets, repository labels,
   milestones, projects, issue / PR templates beyond the
   file-based PR template already landed under Slice C, or any
   other live remote configuration surface. Owning future
   privileged envelope: §f for the visibility flip itself;
   Feature 003 (`feature-003`) for the broader GitHub-settings
   surface beyond visibility; Feature 006 (`feature-006`) for any
   `deploy`-class settings surface.

Each item above is itself a privileged mutation under Feature 001
FR-008; CI passing, an agent review verdict, or any non-Source
"go ahead" on a non-designated surface MUST NOT substitute for
Source ratification of the envelope that consumes it (cf.
[`./RISK_REGISTER.md`](./RISK_REGISTER.md) §c.3, §c.13).

## f. Named owning future privileged envelope for the visibility flip

The actual flip of the canonical repository from private to public
on the remote — together with any concurrently-Source-ratified
application of live branch-protection / ruleset settings to the
live `main` branch — is the responsibility of a single named
future privileged envelope:

- **id**: `post-sprint-0/public-readiness/visibility-flip`
  (placeholder id for backlog use once Source ratifies the
  envelope; see [`./BACKLOG.md`](./BACKLOG.md) §e for current
  recording).
- **mutation class**: privileged (`governance` / `security`,
  potentially also `deploy` if the envelope ratifies live
  branch-protection / ruleset application in the same batch) per
  Feature 001 FR-008.
- **ratifier role**: `source` (sole; FR-008).
- **author / implementer role**: a separately-named implementer
  under the Source-ratified envelope; the controller / reviewer
  seat (Nefarious) MUST NOT author the tracked-file change that
  records the flip, per
  [`../operations/CONTROLLER_BOUNDARY_POLICY.md`](../operations/CONTROLLER_BOUNDARY_POLICY.md)
  §d and
  [`./RISK_REGISTER.md`](./RISK_REGISTER.md) §c.11.
- **upstream constraints the envelope MUST observe**:
  - the workflow-hardening protocol set
    ([`../operations/CONTROLLER_BOUNDARY_POLICY.md`](../operations/CONTROLLER_BOUNDARY_POLICY.md),
    [`../operations/NO_COPY_PASTE_PATTERN.md`](../operations/NO_COPY_PASTE_PATTERN.md),
    [`../operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md`](../operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md),
    [`../operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md`](../operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md),
    [`../operations/ROOT_WORKTREE_INVARIANT.md`](../operations/ROOT_WORKTREE_INVARIANT.md));
  - the release / merge / deploy policy in
    [`./RELEASE_DEPLOY_GOVERNANCE.md`](./RELEASE_DEPLOY_GOVERNANCE.md)
    and the four Slice F content docs;
  - this gate's §c distinction between substrate / documentation
    work and the privileged visibility / settings flip.

Per Feature 001 FR-007, the visibility-flip envelope's author MUST
NOT be its ratifier. Per
[`../operations/CONTROLLER_BOUNDARY_POLICY.md`](../operations/CONTROLLER_BOUNDARY_POLICY.md)
§d–§e, the controller seat MUST NOT silently author the tracked-
file change that records the flip. Per Feature 002 FR-008, the
envelope itself MUST be Source-ratified before consumption — a
green CI run, an agent review, or a "go ahead" on a non-designated
surface MUST NOT substitute for ratification.

The §e residual items other than the visibility flip itself (live
branch-protection / ruleset application, any CODEOWNERS decision,
any future redaction-gate corpus, any other future GitHub-settings
mutation) MAY be ratified under separate envelopes from the
visibility flip, and they MAY be ratified before, after, or
independently of the visibility flip. This gate does not impose a
specific sequencing between them beyond the rule that each is its
own privileged envelope.

## g. Explicit non-authorization statement

This gate is a delivery-view documentation artifact. **Landing
this gate does NOT authorize making the repository public.** It
does NOT mutate any live GitHub setting. It does NOT apply any
live branch-protection or ruleset. It does NOT ratify any
CODEOWNERS file. It does NOT execute or shape any redaction-gate
corpus. It does NOT advance any §e residual item past `Deferred`.

Any tool, agent, controller, implementer, or external reader that
interprets this gate as authorization for the visibility flip, for
a live GitHub-settings mutation, or for any other privileged
external action MUST hard-stop and escalate to Source per Feature
002 FR-018.

The Source-ratification record for the eventual visibility-flip
envelope (and for each §e residual item) is a separate artifact
that MUST be created under the rules in
[`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md)
and recorded in the relevant envelope's
`repo_ratification_record` per Feature 001 FR-016. This gate is
not, and never becomes, that record.

## h. Acceptance posture

This document satisfies the public-readiness gate artifact
requirements:

- §a names the purpose and the two questions the gate lets a
  fresh-clone reader answer.
- §b records the source-of-truth relationships.
- §c hardcodes the gate semantics and the rule separating
  substrate / documentation work from the privileged visibility /
  settings flip.
- §d records the substrate already landed on the canonical branch,
  citing PR #20 / `35bf85f` and PR #21 / `5b762f9` and naming the
  parallel workflow-hardening landings (PR #22 / `d892cd3`, PR #23
  / `3dc45a1`, PR #44 / `30327aa`) as upstream controls.
- §e enumerates the residual checklist for future separate
  ratification: repository visibility flip; live branch-protection
  / ruleset application; any CODEOWNERS decision; any future
  redaction-gate corpus; any future GitHub-settings mutation.
- §f names the owning future privileged envelope for the
  visibility flip and the upstream constraints it must observe.
- §g states explicitly that this gate does not authorize making
  the repository public.
- The Source / Nefarious controller boundary, author / approver
  separation, and repo-private posture are preserved throughout.
