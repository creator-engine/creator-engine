# Public-readiness gate

**Status**: Post-Sprint-0 delivery-view gate artifact. Part of the
**minimum repo-native delivery control plane** and **not a Jira
clone**. Layered onto, and subordinate to, the Feature 001 substrate,
the Feature 002 operating model, the landed open-source / public-
launch readiness substrate (PR #20 / `35bf85f` and PR #21 /
`5b762f9`), the workflow-hardening protocol set (PR #22 / `d892cd3`,
PR #23 / `3dc45a1`, and PR #44 / `30327aa`), and the
[`./RELEASE_DEPLOY_GOVERNANCE.md`](./RELEASE_DEPLOY_GOVERNANCE.md)
release / merge / deploy policy. The named owning future privileged
envelope cited by this gate for the actual repository visibility
flip — `post-sprint-0/public-readiness/visibility-flip`
([`./BACKLOG.md`](./BACKLOG.md) §e.21.2) — has since been consumed
under its own separately-Source-ratified privileged envelope; the
canonical repository is now public on the remote at live main SHA
`4db2a222c15d33b5d5d8e04b07db2d8b3a661459` (`docs: reconcile public
readiness ledger watermark (#48)`), verified under the post-flight
read-only verification archive
`ce-public-launch-post-flight-read-only-verification-20260519T092126Z`.
The §e residual items other than the visibility flip — any
CODEOWNERS decision, any future redaction-gate corpus, any future
release / deploy execution automation, and any future GitHub-
settings mutation beyond the verified live launch posture — remain
separately Source-ratified and unimplemented. A fresh clone is
sufficient to read this gate; no external tracker credential or
instance-local runtime is required.

## a. Purpose

This document is the canonical delivery-view artifact for the
**public-readiness gate**. Its job is to let a fresh clone answer
two questions from repo-visible state alone:

> What public-readiness substrate has landed on the canonical
> branch (including the verified live visibility flip), and what
> residual privileged work remains separately Source-ratified and
> unimplemented beyond the verified launch posture?

and

> What is this gate *not* authorizing, so that landing this artifact
> does not — directly or by implication — change the repository's
> visibility, its live GitHub settings, or any other privileged
> external surface?

The public-readiness gate is **docs-only**. It records readiness
posture; it does not itself execute, schedule, or authorize a
visibility change or any other live GitHub mutation. The actual
visibility flip was a separately-Source-ratified privileged envelope
which has since landed on the live remote (see §d and §f); this
gate artifact is the substrate-side record that named that envelope
and recorded its residual checklist, not the artifact that performed
the flip.

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
   privileged external mutation that changes the repository from
   private to public, applies branch-protection rulesets to the
   live remote, ratifies any CODEOWNERS file, or otherwise mutates
   the live GitHub surface. This activity is privileged
   (`governance` / `security` / `deploy`-class per Feature 001
   FR-008) and is **not** authorized by this gate artifact itself.
   The actual visibility flip and the launch-time live branch-
   protection / ruleset posture were ratified and executed under
   the separately-Source-ratified
   `post-sprint-0/public-readiness/visibility-flip` privileged
   envelope ([`./BACKLOG.md`](./BACKLOG.md) §e.21.2; durable
   evidence in §d and §f below). Any further live GitHub-settings
   mutation beyond that verified launch posture (further branch-
   protection / ruleset changes, any CODEOWNERS decision, any
   future redaction-gate corpus, or any other live GitHub-settings
   surface) remains separately Source-ratified and unimplemented.

The gate's load-bearing rule is:

> Landing this gate artifact, and any §d / §e items shaped under
> docs-only envelopes, MUST NOT itself flip the repository to
> public, MUST NOT itself apply live branch-protection / ruleset
> settings, MUST NOT itself ratify CODEOWNERS, MUST NOT itself
> execute any future redaction-gate corpus, and MUST NOT itself
> perform any other live GitHub-settings mutation. The
> separately-Source-ratified visibility-flip envelope which
> performed the actual flip is recorded under §d and §f below; it
> is a distinct envelope from this gate artifact.

The distinction between substrate / documentation work (this gate)
and the privileged visibility / settings flip (§f) is preserved
throughout this document and is preserved by every downstream gate
that consumes it.

## d. Landed public-readiness substrate

The following substrate has already landed on the canonical branch
and is durable evidence under [`./BACKLOG.md`](./BACKLOG.md) §e.8
and §e.21:

| Substrate | Durable evidence | Role |
|---|---|---|
| Open-source readiness materials | PR #20 / `35bf85f docs: add open-source readiness materials (#20)` | Repository-readable open-source posture artifacts authored under the post-Sprint-0 `post-sprint-0/oss-readiness` work item. |
| Public-launch readiness blocker remediation | PR #21 / `5b762f9 fix: remediate public launch readiness blockers (#21)` | Remediations to substrate-side public-launch readiness blockers identified during the OSS-readiness landing. |
| Public-readiness gate artifact (this document) | PR #46 / `2ee63ddde7608c1bb7c9dc52dab2eadb097d2233 docs: add public readiness continuation gate (#46)` | Substrate-side delivery-view gate artifact authored under the `post-sprint-0/public-readiness/gate-artifact` envelope ([`./BACKLOG.md`](./BACKLOG.md) §e.21.1). |
| Live repository visibility flip and launch-time branch-protection / ruleset application | Live remote state on the canonical repository (public visibility) at live main SHA `4db2a222c15d33b5d5d8e04b07db2d8b3a661459` (`docs: reconcile public readiness ledger watermark (#48)`), verified under the post-flight read-only verification archive `ce-public-launch-post-flight-read-only-verification-20260519T092126Z`. The visibility-flip envelope itself is a live remote / settings mutation; its durable evidence is the live GitHub state plus the post-flight verification archive, not a tracked-file commit. | Executed under the separately-Source-ratified `post-sprint-0/public-readiness/visibility-flip` privileged envelope ([`./BACKLOG.md`](./BACKLOG.md) §e.21.2). Not authorized by, and not performed by, this gate artifact. |

Items 1–3 above are substrate / documentation-class work that did
**not** themselves mutate live GitHub settings, did **not** flip the
repository to public, and did **not** apply live branch-protection
rulesets. Item 4 is the privileged live-GitHub mutation itself,
executed under its own separately-Source-ratified envelope and
verified by the post-flight read-only verification gate; this gate
artifact is the substrate-side record that named that envelope and
recorded its residual checklist, not the artifact that performed
the flip.

The workflow-hardening protocol set (PR #22 / `d892cd3`, PR #23 /
`3dc45a1`, and PR #44 / `30327aa`; see
[`./BACKLOG.md`](./BACKLOG.md) §e.9 and §e.20) is a parallel
post-Sprint-0 substrate landing. It is not itself a public-
readiness item, but the controller-seat-boundary, pointer-only-
relay, path-manifest-fidelity, transcript-archive, and root-
worktree-invariant controls it codifies are upstream sources of
truth that any future privileged envelope under §f MUST observe.

## e. Residual checklist after the live launch

The original residual checklist authored under PR #46 named five
items as `Deferred` on the delivery view at the time this gate
artifact landed. Item 1 — the repository visibility flip — has
since been ratified and executed under its own separately-Source-
ratified privileged envelope; the remaining items continue to be
privileged-class mutations per Feature 001 FR-008 and MUST NOT be
consumed except under their own separately-Source-ratified
envelopes. Landing this gate artifact did not advance any item;
items 2–5 below are not advanced by the §d item 4 visibility-flip
landing either.

1. **Repository visibility flip.** *Status: landed.* Changing the
   canonical repository from private to public on the remote, and
   the launch-time live branch-protection / ruleset posture
   ratified concurrently in the same batch (a `governance` /
   `security` / `deploy`-class live GitHub mutation per Feature 001
   FR-008). Owning privileged envelope:
   `post-sprint-0/public-readiness/visibility-flip`
   ([`./BACKLOG.md`](./BACKLOG.md) §e.21.2); see §d row 4 and §f.
   Durable evidence: live remote state at live main SHA
   `4db2a222c15d33b5d5d8e04b07db2d8b3a661459` and the post-flight
   read-only verification archive
   `ce-public-launch-post-flight-read-only-verification-20260519T092126Z`.
2. **Further live branch-protection / ruleset application.**
   *Status: deferred.* Applying further branch-protection rules or
   rulesets to the live `main` branch on the remote beyond the
   launch-time posture verified under item 1 and beyond the file-
   based policy already authored under
   `.github/BRANCH_PROTECTION_POLICY.md` (landed under Slice C as
   PR #12 / `1cfb955`). The file-based policy, the verified
   launch-time live posture, and any further live-remote
   tightening are three distinct things; this checklist names only
   the further live-remote tightening, which remains unimplemented.
   Owning future privileged envelope: Feature 003 (`feature-003`)
   under a separately Source-ratified privileged `governance`
   envelope per [`./BACKLOG.md`](./BACKLOG.md) §e.3.
3. **Any CODEOWNERS decision.** *Status: deferred.* Authoring,
   ratifying, applying, or removing a `CODEOWNERS` file. CODEOWNERS
   was deliberately excluded under the Slice C "as applicable"
   qualifier (see [`./BACKLOG.md`](./BACKLOG.md) §c.3) and remains
   an open privileged decision; it was explicitly not ratified
   under the §d item 4 visibility-flip envelope. Owning future
   privileged envelope: Feature 003 (`feature-003`) under a
   separately Source-ratified privileged `governance` envelope.
4. **Any future redaction-gate corpus.** *Status: deferred.*
   Authoring or executing a redaction-gate corpus over the tracked
   tree for public-readiness purposes (a `redaction`-class
   privileged mutation per Feature 001 FR-008). No redaction-gate
   corpus is shaped, authorized, or executed by this gate or by
   the §d item 4 visibility-flip envelope. Owning future privileged
   envelope: a separately Source-ratified privileged `redaction`
   envelope, independent of this gate and independent of §f.
5. **Any future GitHub settings mutation beyond the verified
   launch posture.** *Status: deferred.* Mutating any live GitHub
   repository setting — repository visibility (further changes),
   topics, homepage, description, further branch protection,
   further rulesets, Actions secrets, environments, deploy targets,
   repository labels, milestones, projects, issue / PR templates
   beyond the file-based PR template already landed under Slice C,
   or any other live remote configuration surface — beyond the
   launch-time posture verified under item 1. Owning future
   privileged envelopes: Feature 003 (`feature-003`) for the
   broader GitHub-settings surface beyond visibility; Feature 006
   (`feature-006`) for any `deploy`-class settings surface (live
   deploy automation, GitHub environments, deploy gates, rollback
   automation per
   [`./RELEASE_DEPLOY_GOVERNANCE.md`](./RELEASE_DEPLOY_GOVERNANCE.md)).
   Bot-originated dependency / security follow-up PRs (e.g.,
   Dependabot PRs raised against the now-public canonical
   repository) are triaged under separate `docs` / `code` envelopes
   per the merge-approval and definition-of-done gates and are not
   themselves a GitHub-settings mutation surface.

Each `deferred` item above is itself a privileged mutation under
Feature 001 FR-008; CI passing, an agent review verdict, or any
non-Source "go ahead" on a non-designated surface MUST NOT
substitute for Source ratification of the envelope that consumes
it (cf. [`./RISK_REGISTER.md`](./RISK_REGISTER.md) §c.3, §c.13).
The same rule applied at full force to the now-landed item 1
visibility flip and applies at full force to any further live-
GitHub-settings change beyond the verified launch posture.

## f. Owning privileged envelope for the visibility flip — landed

The actual flip of the canonical repository from private to public
on the remote — together with the concurrently-Source-ratified
launch-time application of live branch-protection / ruleset
settings to the live `main` branch — was the responsibility of a
single named privileged envelope, which has since been ratified and
consumed:

- **id**: `post-sprint-0/public-readiness/visibility-flip`
  ([`./BACKLOG.md`](./BACKLOG.md) §e.21.2).
- **mutation class**: privileged (`governance` / `security`, and
  `deploy` for the launch-time live branch-protection / ruleset
  posture ratified concurrently in the same batch) per Feature 001
  FR-008.
- **ratifier role**: `source` (sole; FR-008).
- **author / implementer role**: separately-named implementer under
  the Source-ratified envelope; the controller / reviewer seat
  (Nefarious) did not, and per
  [`../operations/CONTROLLER_BOUNDARY_POLICY.md`](../operations/CONTROLLER_BOUNDARY_POLICY.md)
  §d and [`./RISK_REGISTER.md`](./RISK_REGISTER.md) §c.11 MUST NOT,
  silently author the tracked-file changes that record the flip.
- **upstream constraints observed**:
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
- **durable evidence**: live remote state on the canonical
  repository (public visibility) at live main SHA
  `4db2a222c15d33b5d5d8e04b07db2d8b3a661459` (`docs: reconcile
  public readiness ledger watermark (#48)`); post-flight read-only
  verification archive
  `ce-public-launch-post-flight-read-only-verification-20260519T092126Z`.
  The visibility-flip envelope's durable evidence is the live
  GitHub state plus the post-flight verification gate, not a
  tracked-file commit.

Per Feature 001 FR-007, the visibility-flip envelope's author was
not its ratifier. Per
[`../operations/CONTROLLER_BOUNDARY_POLICY.md`](../operations/CONTROLLER_BOUNDARY_POLICY.md)
§d–§e, the controller seat did not silently author the tracked-
file changes that record the flip. Per Feature 002 FR-008, the
envelope itself was Source-ratified before consumption; CI status,
an agent review, or a "go ahead" on a non-designated surface did
not substitute for ratification.

The §e residual items other than the visibility flip itself
(further live branch-protection / ruleset application beyond the
verified launch posture, any CODEOWNERS decision, any future
redaction-gate corpus, any other future GitHub-settings mutation
beyond the verified launch posture, and any release / deploy
execution automation under Feature 006) remain `Deferred` and MAY
be ratified under separate envelopes from the visibility flip,
either before, after, or independently of each other. This gate
does not impose a specific sequencing between them beyond the rule
that each is its own privileged envelope. Bot-originated
dependency / security follow-up PRs (e.g., Dependabot PRs raised
against the now-public canonical repository) are not themselves a
§e residual item and are triaged under separate `docs` / `code`
envelopes per the merge-approval and definition-of-done gates.

## g. Explicit non-authorization statement

This gate is a delivery-view documentation artifact. **Landing
this gate did NOT itself authorize making the repository public**,
did NOT itself mutate any live GitHub setting, did NOT itself
apply any live branch-protection or ruleset, did NOT itself
ratify any CODEOWNERS file, did NOT itself execute or shape any
redaction-gate corpus, and did NOT itself advance any §e residual
item past `Deferred`. The visibility flip recorded under §d row 4
and §f was authorized by, and executed under, a distinct
separately-Source-ratified privileged envelope; this gate
artifact is not, and never becomes, that envelope's ratification
record.

Any tool, agent, controller, implementer, or external reader that
interprets this gate as authorization for any further live GitHub-
settings mutation beyond the verified launch posture, for further
branch-protection / ruleset application, for a CODEOWNERS
decision, for a redaction-gate corpus, or for any release / deploy
execution automation MUST hard-stop and escalate to Source per
Feature 002 FR-018.

The Source-ratification record for each remaining `Deferred` §e
residual item is a separate artifact that MUST be created under
the rules in
[`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md)
and recorded in the relevant envelope's
`repo_ratification_record` per Feature 001 FR-016. This gate is
not, and never becomes, any of those records.

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
  citing PR #20 / `35bf85f`, PR #21 / `5b762f9`, and PR #46 /
  `2ee63dd`, naming the parallel workflow-hardening landings
  (PR #22 / `d892cd3`, PR #23 / `3dc45a1`, PR #44 / `30327aa`) as
  upstream controls, and recording the live visibility-flip
  landing (live main SHA `4db2a222c15d33b5d5d8e04b07db2d8b3a661459`
  with post-flight verification archive
  `ce-public-launch-post-flight-read-only-verification-20260519T092126Z`).
- §e enumerates the residual checklist: the repository visibility
  flip is now `landed` under its own separately-Source-ratified
  envelope; further live branch-protection / ruleset application
  beyond the verified launch posture, any CODEOWNERS decision, any
  future redaction-gate corpus, and any future GitHub-settings
  mutation beyond the verified launch posture remain `Deferred`.
- §f records the owning privileged envelope for the visibility
  flip as ratified and consumed, with durable evidence in the
  live remote state and the post-flight verification archive, and
  preserves the rule that each remaining `Deferred` §e item is
  its own privileged envelope.
- §g states explicitly that this gate did not itself authorize the
  visibility flip, that the visibility flip was authorized by a
  distinct separately-Source-ratified envelope, and that this gate
  does not authorize any further live GitHub-settings mutation
  beyond the verified launch posture.
- The Source / Nefarious controller boundary, author / approver
  separation, and repo-private posture are preserved throughout.
