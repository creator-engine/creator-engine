# Role-Boundary Failsafe Stage 1 Design

**Status**: Stage 1 design / policy amendment proposal for
`creator-engine/creator-engine#9`. This document is non-enforcing: it
does not amend runtime hooks, validators, schemas, CI, live repository
settings, or any ratification rule by itself.

## a. Purpose

`creator-engine/creator-engine#9` records a Sprint 0 governance failure
class: a controller / PM / tech-lead seat can still author tracked files
directly, then present that work as though it came from a delegated
architect or implementer pane. Existing policy already forbids that
behavior in [`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md)
and records the standing risk as R-011 in
`../delivery/RISK_REGISTER.md`. This Stage 1
design narrows the next change:

- recommend the backlog placement;
- propose policy text and R-011 wording;
- outline the boundary-failure runbook;
- compare enforcement architectures;
- define exact follow-on engineer envelopes;
- stop before implementation.

## b. Recommended Sprint 0 placement

Recommended placement: treat `sprint-0/boundary-failsafe` as a
cross-cutting Sprint 0 blocker on any new governance-sensitive Slice C/D/E
expansion, with this Stage 1 design as the small architect batch already
requested by `creator-engine/creator-engine#9`.

Rationale:

- The issue affects Slice C PR governance, Slice D review / identity
  evidence, and Slice E assignment-envelope / dispatcher enforcement.
- It should not reopen already-ratified Slice B2 work or retroactively
  block work that received independent review.
- The first binding implementation should be small enough to land before
  the next broad governance or runtime expansion.

Sequencing recommendation:

1. Land Stage 1 as design only.
2. Ask Source / Operator to decide whether the first binding follow-on is
   policy-document amendment, local PR-diff enforcement, or earlier
   author-time write blocking.
3. Implement the chosen follow-on under a distinct engineer envelope.

## c. Proposed role-boundary policy text

The following text is intended as an amendment candidate for
[`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md) or a
successor governance surface. It is not active policy until a later
ratified PR lands it.

```text
For any governed Creator Engine batch, the controller seat coordinates,
relays, archives, verifies, and performs separately-authorized mechanics.
The controller seat MUST NOT author, edit, regenerate, or "touch up"
tracked repository content that belongs to an architect, implementer, or
reviewer envelope.

Architect seats MAY author design, research, policy-option, and envelope-
shaping artifacts only when they are the named consumer of an architect
envelope. Architect seats MUST NOT execute the follow-on implementation
unless a later Source / Operator-ratified envelope explicitly re-roles that
seat as implementer for a closed path manifest.

Implementer seats author only the paths named in their envelope's closed
path manifest, stop at the declared stop line, and surrender evidence for
independent verification. Implementers MUST NOT ratify their own work.

Review / verifier seats inspect and reproduce. They MUST NOT repair the
work they are reviewing inside the reviewed envelope. If a repair is
needed, the reviewer records the finding and routes the change back through
the controller to a distinct implementer envelope.

Rare senior-dev override is an emergency exception, not a role. It requires
explicit Source / Operator authorization before mutation, names the exact
paths and expiry, records why delegation is insufficient, and requires
post-action independent review before ratification. Absence of an override
record means the controller-seat mutation is unauthorized even when the
diff is technically correct.
```

Operator decision point: whether the emergency override authority is named
`Source`, `Operator`, or both in canonical policy. This design uses
`Source / Operator` only as a placeholder and does not bind the final term.

## d. Proposed R-011 wording

The current R-011 row already covers controller-seat boundary breach. A
later policy PR should replace or extend its description with wording that
covers controller, architect, implementer, and reviewer boundaries:

```text
The controller, architect, reviewer, or ratifying seat performs tracked
authoring outside the role and envelope that govern the batch. The highest
risk case is the controller seat silently editing tracked files inside an
implementer's envelope and then verifying its own edit, but the same failure
class includes architects implementing their own design without re-role
authorization, reviewers repairing reviewed work, and ratifiers authoring
content under the same ratification they later approve. The result is a
loss of author/approver separation, incomplete transcript evidence, and
diffs whose actual producer cannot be reconstructed from the ratification
packet.
```

Recommended row deltas:

- Keep likelihood `Medium`.
- Raise impact from `High` to `Severe` when the breached batch touches a
  privileged mutation class (`governance`, `identity`, `security`,
  `attestation`, `redaction`, or `deploy`), because the breach can corrupt
  the substrate rather than only a local artifact.
- Add early warnings for "reviewer pushed fix", "architect amended
  implementation", and "senior-dev override mentioned but no override
  record exists".
- Add mitigation references to the eventual boundary-failure runbook and
  selected enforcement gate.

## e. Boundary-failure runbook outline

A later runbook should be a short operational document under
`docs/operations/` and should use this sequence:

1. **Freeze mutation**: stop tracked-file authoring, staging, commit, push,
   PR update, and merge mechanics for the affected lane.
2. **Record the breach**: capture issue / PR / branch, base and head SHAs,
   claim id, envelope ref, changed paths, suspected authoring role, and the
   first observed boundary violation.
3. **Preserve evidence**: archive visible-pane transcript references,
   controller notes, `git diff --name-status`, `git diff --numstat`, and
   path-manifest verification output. Do not edit tracked files to clean up
   evidence.
4. **Dispatch independent review**: use a reviewer / architect who did not
   author the suspect diff and is not the controller who observed it.
5. **Classify recovery**: choose one of `scrap-and-redo`,
   `ratify-after-independent-review`, or `explicit-re-attribution`.
6. **Escalate privileged classes**: if the changed paths affect governance,
   identity, security, attestation, redaction, deploy, schemas, validators,
   `.github/`, or runtime hooks, require explicit Source / Operator ruling
   before any continuation.
7. **Close the record**: update the risk / lessons-learned surface and name
   the follow-on prevention change, or explicitly record why no follow-on is
   authorized.

## f. Enforcement architecture options

### Option 1: PR-diff attribution gate

Compare `origin/main..HEAD` against a PR-carried manifest and an
attribution record that names the producing role / lane for every changed
path. Refuse merge when a changed path lacks an authorized producer or when
producer role conflicts with the envelope.

Pros: aligns with existing path-manifest and work-sizing PR-diff gates; does
not block legitimate authoring while a manifest is being amended; works in
CI and local verification.

Cons: detects at PR time, not at first write; requires an attribution record
format or extension to an existing evidence packet.

### Option 2: Claude Code `PreToolUse` protected-path guard

Intercept write/edit tool calls on protected tracked paths and require a
valid lane / envelope / actor context before the write proceeds.

Pros: earliest feedback; prevents many accidental edits before they enter
the worktree.

Cons: local and harness-specific unless paired with a PR gate; must avoid
hardcoding one tmux layout, provider, OS user, or filesystem path.

### Option 3: Git pre-commit / prepare-commit-msg guard

Block commits unless the staged paths match a current envelope and an
author/consumer attestation exists.

Pros: simple to prototype; catches local mechanics before a commit is
published.

Cons: client hooks are bypassable and not distributed reliably; still
allows the wrong actor to author files until commit time.

### Option 4: Dispatcher / lane runtime identity binding

Make lane launch write an ignored runtime record binding claim id, role,
pane, worktree, branch, envelope, and authorized path manifest. Later
checks consume that record.

Pros: durable direction for Phase 1 visible panes and Phase 2 automation;
fits existing lane / active-work-ledger / pane-registry protocols.

Cons: broader runtime work; should not be the first binding mitigation
unless Source / Operator chooses a runtime-first path.

### Option 5: Filesystem or container isolation

Give controller, architect, implementer, and reviewer seats different
filesystem write boundaries, or run workers in containers with mounted path
sets.

Pros: strongest class of control once mature.

Cons: too large for the immediate issue; may require OS/container policy
and credential-boundary decisions outside this Stage 1 scope.

## g. Recommendation

Use a layered plan:

1. **First binding follow-on**: add repo-visible policy amendments and the
   boundary-failure runbook. This closes the governance text gap with no
   runtime coupling.
2. **First technical guard**: implement a PR-diff attribution gate that
   complements the existing path-manifest carrier and work-sizing floor. It
   should fail closed for governance-sensitive changed paths when the PR
   cannot prove the authorized producer role.
3. **Author-time defense**: add a local `PreToolUse` warning / block only
   after the PR-diff gate exists, so local guard drift cannot become the
   sole boundary.
4. **Runtime hardening**: fold identity binding into lane launch and future
   isolation work after the minimal gate proves the evidence shape.

This keeps the first enforceable unit small, repo-native, and reviewable
while preserving the stronger runtime direction for later work.

## h. Follow-on engineer envelopes

### Envelope E1: policy and runbook amendment

- **Issue**: `creator-engine/creator-engine#9`.
- **Owner role**: implementer in visible governed lane.
- **Mutation class**: `governance`.
- **Authorized paths**:
  - `docs/operations/CONTROLLER_BOUNDARY_POLICY.md`
  - `docs/operations/BOUNDARY_FAILURE_RUNBOOK.md`
  - `docs/delivery/RISK_REGISTER.md`
  - `.ce/changelog/ce9-role-boundary-policy.md`
  - `.ce/pr-manifests/ce9-role-boundary-policy.md`
- **Required content**: policy text from §c, R-011 delta from §d,
  runbook from §e, and explicit senior-dev override record fields.
- **Forbidden work**: hooks, validators, schemas, CI, runtime code, live
  GitHub settings, or automation.
- **Validation**: `ce check` on changed docs, `git diff --check`, path
  manifest verifier, and work-sizing-floor verifier.
- **Stop line**: `CE9_E1_POLICY_RUNBOOK_READY_FOR_REVIEW`.

### Envelope E2: PR-diff attribution design-to-code spike

- **Issue**: `creator-engine/creator-engine#9`.
- **Owner role**: implementer in visible governed lane.
- **Mutation class**: `governance` plus `code` for validator-only logic.
- **Authorized paths**:
  - `schemas/role-boundary-attribution.schema.yaml`
  - `validators/creator_engine_validator/checks/role_boundary_attribution.py`
  - `validators/creator_engine_validator/checks/__init__.py`
  - `validators/creator_engine_validator/cli.py`
  - `validators/tests/unit/test_role_boundary_attribution.py`
  - `validators/tests/unit/test_change_status.py`
  - `validators/tests/unit/test_version_boundary.py`
  - `docs/operations/CONTROLLER_BOUNDARY_POLICY.md`
  - `.ce/changelog/ce9-role-boundary-attribution-gate.md`
  - `.ce/pr-manifests/ce9-role-boundary-attribution-gate.md`
- **Required behavior**: compare `base..HEAD` changed paths to an
  attribution record; report missing producer role, controller-authored
  protected path, reviewer-authored reviewed path, and absent override record.
- **Forbidden work**: `.github/` wiring, live branch protection, container
  isolation, tmux launcher mutation, or hook hard-deny behavior.
- **Validation**: focused unit tests, `ce check`, `git diff --check`, path
  manifest verifier, and work-sizing-floor verifier.
- **Stop line**: `CE9_E2_ATTRIBUTION_GATE_SPIKE_READY_FOR_REVIEW`.

### Envelope E3: CI and PR-template wiring

- **Issue**: `creator-engine/creator-engine#9`.
- **Prerequisite**: E2 merged or explicitly superseded.
- **Owner role**: implementer in visible governed lane.
- **Mutation class**: `governance`.
- **Authorized paths**:
  - `.github/pull_request_template.md`
  - `.github/workflows/validate.yml`
  - `docs/operations/CONTROLLER_BOUNDARY_POLICY.md`
  - `docs/delivery/DEFINITION_OF_DONE.md`
  - `.ce/changelog/ce9-role-boundary-ci-gate.md`
  - `.ce/pr-manifests/ce9-role-boundary-ci-gate.md`
- **Required behavior**: make the attribution gate a required PR-diff check
  source, document the PR body field or carrier file used to supply
  attribution, and preserve the "CI verifies; Source / Operator ratifies"
  invariant.
- **Forbidden work**: live repository settings mutation unless separately
  ratified; merge queue mutation; container isolation.
- **Validation**: workflow wiring tests if present, `ce check`, `git diff
  --check`, path manifest verifier, and work-sizing-floor verifier.
- **Stop line**: `CE9_E3_CI_GATE_READY_FOR_REVIEW`.

### Envelope E4: author-time guard

- **Issue**: `creator-engine/creator-engine#9`.
- **Prerequisite**: E2 merged and E3 either merged or explicitly deferred by
  Source / Operator.
- **Owner role**: implementer in visible governed lane.
- **Mutation class**: `governance` plus `code` for local hook logic.
- **Authorized paths**:
  - `.claude/hooks/ce-pretooluse.sh`
  - `.claude/hooks/ce-hook-common.sh`
  - `validators/creator_engine_validator/hook_check.py`
  - `validators/tests/unit/test_hook_check.py`
  - `docs/operations/CONTROLLER_BOUNDARY_POLICY.md`
  - `.ce/changelog/ce9-role-boundary-pretooluse.md`
  - `.ce/pr-manifests/ce9-role-boundary-pretooluse.md`
- **Required behavior**: warn or block controller-seat writes to protected
  tracked paths only when the local event context can prove actor role and
  envelope mismatch. Fail closed only for dangerous mechanics and
  governance-sensitive paths that have an unambiguous invalid context.
- **Forbidden work**: provider-specific account binding, OS-user binding,
  hardcoded tmux layout assumptions, or treating local hook success as
  ratification.
- **Validation**: hook unit tests, `ce check`, `git diff --check`, path
  manifest verifier, and work-sizing-floor verifier.
- **Stop line**: `CE9_E4_AUTHOR_TIME_GUARD_READY_FOR_REVIEW`.

## i. Non-implementation statement

This PR intentionally implements none of the follow-on envelopes. It does
not edit enforcement code, hooks, validators, runtime launch behavior,
schemas, `.github/` workflows, branch protection, CI policy, or live
GitHub settings. Any binding change requires a later ratified envelope.
