# Controller / Implementer Boundary Policy

**Status**: Workflow-hardening normative protocol. Part of the
**minimum repo-native delivery control plane** and **not a Jira
clone**. Layered onto, and subordinate to, the Feature 001 substrate
and the Feature 002 operating model. A fresh clone is sufficient to
apply this policy; no external tracker credential or network state is
required.

## a. Purpose

Many Creator Engine batches are authored across at least three
distinct identities: a Source-ratifying authority that delegates a
scope; a controlling identity that relays the envelope, archives
transcripts, and verifies completion; and one or more implementing
identities that perform the substantive authoring inside an isolated
worktree. When those identities collapse into one another — when the
controller is treated as an implementer, when an implementer ratifies
its own batch, or when Source is treated as a reviewer — the
[`./AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md)
invariants and Feature 001 FR-007 author/approver separation collapse
with them.

This policy makes one operational fact answerable from a fresh clone:

> Under any governed batch, which identity is allowed to perform which
> action, and what does the controller do when an implementer asks
> the controller to author tracked files inside the implementer's
> envelope?

This policy is **normative**. Where it overlaps with the Feature 002
verifies-not-ratifies invariant or with the Feature 001
author/approver separation contract, the upstream contract controls.
This policy does not redefine those contracts; it restates the
operating consequences for the controller / implementer split.

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| Feature 001 FR-007 / FR-008 / FR-016 / FR-020a | Author/approver separation; privileged-class enumeration; ratification flow. |
| Feature 002 FR-005 through FR-011, FR-013, FR-017, FR-018 | Assignment-Envelope contract; verifies-not-ratifies; authority-conflict halt path. |
| [`../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`](../governance/AUTHORITY_AND_RATIFICATION_MODEL.md) | Role-category definitions; ratifier identification. |
| [`../delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md`](../delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md) §c.2, §c.4 | Envelope ratifier and authorized-actor fields; the controller / consumer split. |
| [`../delivery/ENVELOPE_CONSUMPTION_CHECKLIST.md`](../delivery/ENVELOPE_CONSUMPTION_CHECKLIST.md) | Consumer-side checks the implementer runs. |
| [`../delivery/SCOPE_AUDIT_CHECKLIST.md`](../delivery/SCOPE_AUDIT_CHECKLIST.md) | Verifier-side scope audit the controller runs after the stop line. |
| [`./NO_COPY_PASTE_PATTERN.md`](./NO_COPY_PASTE_PATTERN.md) | Pointer-only relay shape the controller MUST use to hand an envelope to the implementer. |
| [`./PATH_MANIFEST_FIDELITY_PROTOCOL.md`](./PATH_MANIFEST_FIDELITY_PROTOCOL.md) | Manifest count/hash preflight that the controller and the implementer both run. |
| [`./TRANSCRIPT_ARCHIVE_PROTOCOL.md`](./TRANSCRIPT_ARCHIVE_PROTOCOL.md) | Archive/hash protocol for the implementer pane's transcript. |
| [`./ROOT_WORKTREE_INVARIANT.md`](./ROOT_WORKTREE_INVARIANT.md) | Navigation/orchestration-only invariant on the root checkout and dirty-root remediation posture; a separate filesystem-state concern from this role-boundary policy and from the per-gate worktree lifecycle. |
| `docs/delivery/RISK_REGISTER.md` R-011 | Controller-seat boundary breach as a standing risk. |

## c. Roles in scope

For the boundary purposes of this policy, the four roles are:

| Role | Substance | Examples |
|---|---|---|
| **Source** | Sole ratifier for privileged classes per Feature 001 FR-008. Authorizes envelopes; never authors tracked-file content under an envelope they ratify. | The human Source authority for the Creator Engine batch. |
| **Controller** | Coordinates the envelope between Source and the implementer. Archives transcripts, hashes prompts/transcripts, runs preflight, runs scope audit, and relays artifacts. The controller is a *verifier*, not an author. The controller is not the ratifier unless they *are* Source for that batch. | Nefarious (and Hermes where Hermes acts as a non-author coordinator). |
| **Architect** | A pre-implementation research / shaping identity. Produces findings, options, and recommended envelope shapes. The architect does NOT author the implementation. | The architect pane that produced the workflow-hardening research handoff. |
| **Implementer** | The visible pane that performs the substantive tracked-file authoring inside an isolated worktree, under a Source-ratified envelope, against an exact authorized path manifest. The implementer is the *only* role permitted to mutate tracked files under the envelope. | The visible Claude Code engineer pane consuming this batch. |

The roles are defined by **action under the envelope**, not by tool /
model / host / account binding. Tool, model, host, and account
bindings are deployment-time overlay decisions and MUST NOT be
hard-coded as upstream constants per
[`../delivery/REVIEWER_IDENTITY_REQUIREMENTS.md`](../delivery/REVIEWER_IDENTITY_REQUIREMENTS.md)
§c.

A controller's runtime statefulness — persistent controller process versus
stateless-per-invocation instance — is likewise not a role binding.
Stateless-per-invocation controllers operate under additional session-start
discipline declared in
[`./session-continuity-protocol.md`](./session-continuity-protocol.md)
`## Stateless-per-invocation controllers`; that discipline supplements the
role definition without re-binding it to a specific tool or model.

## d. Hardcoded boundary

The boundary MUST hold absolutely for every governed batch:

1. **Source ratifies, never authors under that ratification.** A
   Source operator MAY author content under a separate envelope
   ratified by a separate Source act; Source MUST NOT author under
   the same envelope they ratified for an implementer.
2. **Controller verifies, never authors tracked files inside the
   implementer's envelope.** The controller MAY:
   - relay the envelope (pointer-only, per
     [`./NO_COPY_PASTE_PATTERN.md`](./NO_COPY_PASTE_PATTERN.md));
   - recompute the path manifest count/hash;
   - archive and hash the implementer pane's transcript;
   - run independent scope-audit commands;
   - reject or accept the implementer's report-back;
   - escalate to Source when ambiguous;
   - perform mechanics (staging / commit / push / PR / merge) only
     when a separate Source ratification of the mechanics is in force.
   The controller MUST NOT edit any tracked file inside the
   implementer's envelope path manifest. If an in-envelope correction
   is required, the controller routes the correction back to the
   implementer.
3. **Architect proposes, never executes the implementation.** The
   architect MAY produce research, options, recommended envelope
   shapes, and recommended path manifests. The architect MUST NOT
   author the implementation under the resulting envelope unless a
   separate Source-ratified envelope explicitly re-roles the
   architect as the implementer.
4. **Implementer authors, never ratifies their own batch.** The
   implementer authors exactly the paths named in the envelope's
   manifest, halts at the stop line, and surrenders evidence to the
   controller. The implementer MUST NOT perform mechanics under the
   envelope and MUST NOT broaden scope to "fix" anything outside the
   manifest. The implementer MUST NOT ratify, sign, or otherwise
   approve their own work.

These four bullets are the **hardcoded boundary**. A batch whose
relayed envelope, transcript, or completion evidence violates any of
them is a governance violation per Feature 001 FR-007 and Feature 002
FR-018, and MUST be halted before mechanics regardless of mechanical
convenience.

### d.1 Deterministic no-inlining refusal

Governed controller harnesses MUST lack execution-plane primitives in
controller context. The Claude PreToolUse hook path and the Codex/FACE
governed exec wrapper refuse these command primitive families before execution:

- worktree mutation;
- full local PR preflight (`ce validate-pr` / `ce-preflight.sh`);
- path-manifest carrier regeneration;
- harvest or press-merge bundle extraction;
- harvest-shaped branch push.

The refusal reason is stable and actionable:
`execution-plane primitive (<primitive>) denied for controller/unpinned context;
dispatch through a launch-pinned governed worker: ce worker run --role
implementer --brief <brief> --worktree <allocated-worktree> (or ce lane launch
--role implementer ...)`.

Documentation is not the enforcement. The capability-bearing route is a
launch-pinned governed worker record under `.ce/state/workers/<worker>/worker.yaml`
whose role and worktree binding match the current context. Missing, malformed,
stale, or unpinned worker context fails closed to the same refusal.
Tracked-file writes remain denied by the foreman-delegation rule, which carries
the same `ce worker run --role implementer ...` dispatch hint.

## e. The controller-seat-edit anti-pattern

The single highest-likelihood violation of §d is the controller
"helpfully" editing tracked files from the controller seat — for
example, because a Markdown link is obviously broken or because a
small whitespace fix would save a round-trip. This is forbidden:

1. The controller's edit collapses author/approver separation: the
   controller subsequently verifies their own edit.
2. The controller's edit is outside the implementer's envelope, so it
   has no Source ratification of its own.
3. The controller's edit leaves no implementer-pane evidence in the
   archived transcript, breaking the
   [`./TRANSCRIPT_ARCHIVE_PROTOCOL.md`](./TRANSCRIPT_ARCHIVE_PROTOCOL.md)
   reproducibility property.
4. The fix often masks a more serious issue (e.g., a path-manifest
   fidelity problem per
   [`./PATH_MANIFEST_FIDELITY_PROTOCOL.md`](./PATH_MANIFEST_FIDELITY_PROTOCOL.md))
   that the implementer would have surfaced.

If the controller observes a needed correction inside the implementer's
manifest, the only authorized responses are:

- relay a corrected pointer-only prompt to the implementer, or
- escalate to Source if the correction requires manifest amendment.

The controller MUST NOT silently patch tracked files.

## f. Preflight and verifier boundary checks

Before any of the following the controller and the implementer MUST
each perform the boundary checks named in their respective checklists:

| Action | Required boundary check |
|---|---|
| Handoff consumption | Implementer recomputes the envelope's path-manifest count/hash per [`./PATH_MANIFEST_FIDELITY_PROTOCOL.md`](./PATH_MANIFEST_FIDELITY_PROTOCOL.md); verifies the controller's pointer-only relay shape per [`./NO_COPY_PASTE_PATTERN.md`](./NO_COPY_PASTE_PATTERN.md). |
| Tracked-file mutation | Implementer restates allowed paths and prohibited surfaces per [`../delivery/ENVELOPE_CONSUMPTION_CHECKLIST.md`](../delivery/ENVELOPE_CONSUMPTION_CHECKLIST.md) §d. |
| Staging | A Source-ratified mechanics envelope MUST exist; controller confirms its scope; implementer pane MUST NOT stage. |
| Commit | Source-ratified mechanics envelope MUST authorize commit; controller performs the commit only after independent scope audit per [`../delivery/SCOPE_AUDIT_CHECKLIST.md`](../delivery/SCOPE_AUDIT_CHECKLIST.md). |
| Push | Source-ratified mechanics envelope MUST authorize push; controller confirms remote ref state before and after. |
| PR creation | Source-ratified mechanics envelope MUST authorize PR; controller authors the PR body from repository evidence, not from chat history. |
| Merge | Source-ratified merge approval MUST exist per [`../delivery/MERGE_APPROVAL_CHECKLIST.md`](../delivery/MERGE_APPROVAL_CHECKLIST.md); controller confirms the merge governance evidence chain. |

A boundary check that cannot be performed (missing ratification, no
controller available, no archived transcript) is a halt condition.

### f.1 The `role_boundary_attribution` verifier check — scope and limits

The repository-local `role_boundary_attribution` validator check is a
Phase-1 audit aid for this policy and the R-011 risk row. It does NOT
ratify a batch, and its modes have explicit limits that controllers
and ratifiers MUST understand before relying on its output:

- **Default whole-tree mode** (run by `python -m creator_engine_validator
  check <paths>` and `check-examples`) is *advisory*. It emits warnings,
  not errors, when a `role: controller` document carries a fenced path
  manifest. A clean whole-tree run is not by itself proof of boundary
  compliance; a warning is a signal to investigate, not a CI failure.
- **`verify-attribution --base <commit>` mode** compares changed files
  between `<base>..HEAD` against active handoff manifests under
  `.hermes/handoffs/`. This mode is best-effort and requires that
  directory to be present and readable. A fresh clone of the public
  repository does NOT include `.hermes/`; in that environment the mode
  reports `role_boundary_no_active_handoff` and cannot be used as
  attribution evidence. Controllers operating outside an environment
  with `.hermes/` populated MUST use a separate attribution record
  (transcript archive plus `git log` evidence) and MUST NOT treat
  absence of the check as proof of compliance.

The detailed contract for both modes lives in `validators/README.md`
and in the docstring of
`validators/creator_engine_validator/checks/role_boundary_attribution.py`.

## g. Cross-cutting prohibitions

- The implementer pane MUST NOT consume an envelope relayed by paste;
  pointer-only relay is mandatory per
  [`./NO_COPY_PASTE_PATTERN.md`](./NO_COPY_PASTE_PATTERN.md).
- The implementer pane's transcript MUST be archived and hashed per
  [`./TRANSCRIPT_ARCHIVE_PROTOCOL.md`](./TRANSCRIPT_ARCHIVE_PROTOCOL.md)
  before mechanics.
- A privileged-class envelope (Feature 001 FR-008) MUST NOT be
  ratified by anyone other than Source, regardless of how convenient
  the controller's involvement appears.
- An external tracker entry, a CI green check, an agent commentary
  verdict, or a "go ahead" on a non-designated surface MUST NOT
  substitute for Source ratification per
  [`../delivery/DEFINITION_OF_DONE.md`](../delivery/DEFINITION_OF_DONE.md)
  §c.
- The filesystem state of the root checkout (branch, remote parity,
  cleanliness, absence of in-flight authoring) is a separate concern
  governed by
  [`./ROOT_WORKTREE_INVARIANT.md`](./ROOT_WORKTREE_INVARIANT.md). That
  policy does not redefine the role boundary in §c–§e, and this
  policy does not redefine the root-state invariant; the two are
  applied together at session start and at merge-close.

## h. Acceptance posture

This document satisfies the workflow-hardening requirement to
hardcode the Source / controller / architect / implementer boundary:

- Names the four roles in §c.
- Hardcodes the four-bullet boundary in §d.
- Names the controller-seat-edit anti-pattern in §e.
- Names the preflight and verifier boundary checks before handoff
  consumption, tracked-file mutation, staging, commit, push, PR
  creation, and merge in §f.
- Restates the cross-cutting prohibitions in §g, including the
  pointer-only relay rule and the transcript archive rule.
- Defers tool / model / host / account bindings to deployment-time
  overlay decisions; the policy stays generic to Creator Engine.
