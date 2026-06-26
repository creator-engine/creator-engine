# Assignment Envelope Dry Run (Slice E, Non-Authorizing)

**Status**: Slice E authored draft. This document is a **non-authorizing
dry run** of the manual Assignment Envelope contract defined in
[`./ASSIGNMENT_ENVELOPE_TEMPLATE.md`](./ASSIGNMENT_ENVELOPE_TEMPLATE.md)
and the runtime protocol defined in
[`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md).
It rehearses the contract using the Slice E authoring batch itself as
the worked example, and it produces evidence that a Source-validated
review can act on.

**Dry-run marker (load-bearing)**:

> This document does **NOT** execute a real downstream assignment.
> It does **NOT** create a downstream branch, worktree, PR, commit,
> staged change, or merged change. It does **NOT** assign a real
> implementation task. It does **NOT** authorize any mechanics.
> Consumption of this rehearsal **stops at Source validation**; the
> stop line below is the terminal action.

In plain prose: **no staging, no commit, no push, no merge** occurs
under this dry run. The consumer does not run `git add`, does not
run `git commit`, does not run `git push`, does not open or merge
a pull request, and does not delete or rename any branch.
Mechanics — staging, commit, push, PR, merge, branch deletion,
worktree removal, repository-setting mutation — are a separately
ratifiable action that this document does not authorize.

Part of the **minimum repo-native delivery control plane** and
**not a Jira clone**. A fresh clone is sufficient to inspect this
dry run; no external tracker credential or network state is required.

## a. Purpose

The dry run answers one question from a fresh clone:

> If a Source-ratified Assignment Envelope using this template were
> consumed in a single isolated worktree by exactly one visible
> Claude Code pane, what would the filled envelope look like, what
> commands would the consumer run, and at what stop line would the
> consumer halt?

The rehearsal makes the contract concrete and auditable without
exercising any downstream mechanics. It is a Slice-E-internal
artifact and does **not** propagate authority to any downstream
batch.

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| [`./ASSIGNMENT_ENVELOPE_TEMPLATE.md`](./ASSIGNMENT_ENVELOPE_TEMPLATE.md) | The template this dry run fills in. |
| [`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md) | The runtime protocol the dry-run worktree obeys. |
| [`./ENVELOPE_CONSUMPTION_CHECKLIST.md`](./ENVELOPE_CONSUMPTION_CHECKLIST.md) | The consumer-side checklist whose application is rehearsed. |
| [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) | The verifier-side checklist whose application is rehearsed. |
| [`./REVIEW_GATE.md`](./REVIEW_GATE.md) | The review gate the dry-run evidence feeds (with the named waiver in §c.2). |
| Feature 001 FR-007 / FR-008 / FR-016 | Author/approver separation; privileged-class enumeration; ratification flow. |
| Feature 002 FR-005 through FR-011 | Hermes-authored envelope contract. |

## c. Sample filled envelope (Slice E worked example)

The fields below populate the template in
[`./ASSIGNMENT_ENVELOPE_TEMPLATE.md`](./ASSIGNMENT_ENVELOPE_TEMPLATE.md)
§c against the Slice E authoring batch itself.

### c.1 Header

| Field | Value |
|---|---|
| `envelope_id` | `sprint-0/slice-e-assignment-runtime-protocol` |
| `envelope_title` | "Sprint 0 Slice E — Manual Assignment Envelope and worktree runtime protocol" |
| `envelope_date` | `2026-05-14` |
| `repo` | `creator-engine` |
| `base_branch` | `main` |
| `base_commit` | `fef41c4 docs: reconcile Slice D delivery state` |
| `local_branch` | `docs/sprint0-slice-e-assignment-runtime-protocol` |
| `local_worktree_path` | An isolated worktree under the workstation's `<repo-parent>/creator-engine-worktrees/sprint0-slice-e-assignment-runtime-protocol` shape, treated as an instance-local fact per [`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md) §c.1. |

### c.2 Source ratification / authority record

| Field | Value |
|---|---|
| `ratifier` | `source` |
| `ratification_record_ref` | "Source ratifies this bounded Assignment Envelope for Sprint 0 Slice E — Manual Assignment Envelope and worktree runtime protocol," recorded in the Hermes handoff under the worktree's `.hermes/` directory and quoted into the consumer's session at envelope-author time. The handoff artifact itself is runtime-local per [`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md) §g and is referenced, not embedded. |
| `ratification_scope` | Author docs-only governance/delivery content in the isolated local worktree and branch named above; touch only the five new files and the seven minimal-coherence update files enumerated in §c.5; perform no staging, commit, push, PR, merge, branch deletion, worktree removal, or repository-setting mutation under this envelope. |
| `waivers_named` | Source explicitly waives the formal ratified-reviewer-identity requirement for this named Slice E batch only, because Feature 004 has not yet instantiated a governed reviewer identity. The waiver is bounded to this batch; it does NOT generalize. The consumer's work and the controller's verification are independent **review/verification evidence only**; they are not Source ratification. |

The `ratifier` field is intentionally distinct from any review or
verification evidence: review evidence is not ratification per
[`./REVIEW_GATE.md`](./REVIEW_GATE.md) §m.1.

### c.3 Mutation classes

| Field | Value |
|---|---|
| `anticipated_mutation_classes` | `governance`, `docs`. Slice E shaping is the privileged governance/docs envelope Feature 001 FR-008 contemplates. |
| `dominant_class` | `governance` (privileged). |

### c.4 Authorized actor / role / pane

| Field | Value |
|---|---|
| `authorized_actor` | Visible Claude Code architect/implementer in the named worktree's pane. Concrete tool / model / host / account bindings are deployment-time overlay decisions and are not hard-coded as upstream constants per [`./REVIEWER_IDENTITY_REQUIREMENTS.md`](./REVIEWER_IDENTITY_REQUIREMENTS.md) §c. |
| `role_category` | `implementer` (with `architect` framing for delivery-view documentation). |
| `pane_identity` | The visible Claude Code pane operating on the named worktree. Runtime-local context. |
| `controller` | Nefarious (with Hermes coordination). The controller is the independent verifier and is **not** the ratifier. |

Author/approver separation (Feature 001 FR-007) is preserved: the
visible pane authoring Slice E is not Source and is not the
independent verifier of its own batch.

### c.5 Exact allowed files and allowed operations

`allowed_create_paths` (new files):

1. `docs/delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md`
2. `docs/delivery/WORKTREE_RUNTIME_PROTOCOL.md`
3. `docs/delivery/ENVELOPE_CONSUMPTION_CHECKLIST.md`
4. `docs/delivery/SCOPE_AUDIT_CHECKLIST.md`
5. `docs/delivery/ASSIGNMENT_ENVELOPE_DRY_RUN.md`

`allowed_update_paths` (minimal coherence updates only if directly
needed):

1. `docs/delivery/README.md`
2. `docs/delivery/BACKLOG.md`
3. `docs/delivery/KANBAN.md`
4. `docs/delivery/DEPENDENCIES.md`
5. `docs/delivery/DEFINITION_OF_READY.md`
6. `docs/delivery/DEFINITION_OF_DONE.md`
7. `docs/delivery/REVIEW_GATE.md`

`allowed_operations`: `author`, `update`, `add cross-reference`.
Anything outside the union of the two path sets is out of scope and
MUST be refused per
[`./ENVELOPE_CONSUMPTION_CHECKLIST.md`](./ENVELOPE_CONSUMPTION_CHECKLIST.md)
§d.

### c.6 Explicitly prohibited surfaces and forbidden operations

Restated by name for mechanical scope audit per
[`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) §d:

- `.github/`
- `CODEOWNERS`
- live GitHub settings, PR metadata, labels, branch protection,
  repository settings, external tracker state
- deploy automation
- `specs/`, `schemas/`, `validators/`, `templates/`, `examples/`,
  `tenants/`
- `docs/contracts/`, `docs/product/`, `docs/architecture/`,
  `docs/governance/`, `docs/quality/`, `docs/devops/`,
  `docs/security/`
- unrelated branches, unrelated stash entries (including
  `stash@{0}` — no apply, drop, or content inspection without
  explicit Source ratification)
- any non-allowed file

Forbidden operations under this envelope (per
[`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md)
§i): `git add`, `git commit`, `git push`, `gh pr` (create / edit /
comment / merge), `git branch -d` / `-D`, `git worktree remove`,
`git config` mutations, `--no-verify` / signing bypass, force-push,
and any repository-setting mutation on any host.

### c.7 Dependencies and prerequisites

| Field | Value |
|---|---|
| `predecessor_items` | `sprint-0/slice-d` (delivery-view predecessor edge). |
| `predecessor_status_observed` | `Done` on the canonical branch (commit `6058661 docs: define reviewer evidence gate for Slice D`). |
| `readiness_evidence` | The Slice E backlog row in `./BACKLOG.md` §c.5 satisfies the Ready criteria in [`./DEFINITION_OF_READY.md`](./DEFINITION_OF_READY.md) §b for shaping; the privileged-class rule in §c is satisfied by this bounded Source-ratified envelope. |
| `external_tracker_references` | None. A fresh clone is sufficient per [`./README.md`](./README.md) §d. |

### c.8 Implementation instructions

1. Create the five new files in `allowed_create_paths` (§c.5) with
   content satisfying the smoke criteria in the Slice E envelope.
2. Apply minimal coherence updates only to the seven files in
   `allowed_update_paths` where directly needed for status,
   discoverability, and stale-language removal.
3. Use careful wording for in-flight work ("this Slice E batch
   authors..."); do not declare canonical Done before merge.
4. Remove stale `DEFINITION_OF_READY.md` language that names
   `sprint-0/slice-d` as the next candidate envelope; after this
   batch, Slice D is `Done` and Slice E is the active envelope
   under Source ratification.
5. Halt at the envelope's stop line (§c.13) before any mechanics.

### c.9 Validation commands and expected results

The consumer runs the following commands locally; none stage,
commit, push, merge, delete branches, or mutate repository
settings.

| Command | Expected result |
|---|---|
| `git status --short --branch --untracked-files=all` | Branch line shows `docs/sprint0-slice-e-assignment-runtime-protocol`; only the allowed new files appear as untracked, only the allowed-update files appear as modified (or no modifications where coherence updates are not directly needed). |
| `git branch --show-current` | Exactly `docs/sprint0-slice-e-assignment-runtime-protocol`. |
| `git log -1 --oneline` | `fef41c4 docs: reconcile Slice D delivery state`. |
| `git diff --name-only` | Only paths under `docs/delivery/` and only those in the `allowed_create_paths` / `allowed_update_paths` union. |
| `git diff --check` | No output, exit 0. |
| `PYTHONPATH=validators <python> -m creator_engine_validator check-examples` | Exit 0 OR a baseline failure unrelated to this docs-only batch, in which case the exact output and rationale are recorded per [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.2. The consumer MUST NOT patch validators or non-allowed files. |
| `PYTHONPATH=validators <python> -m creator_engine_validator scan-no-limitless` | Same expectation. |
| `grep -RInE 'Slice D is (the )?next candidate\|sprint-0/slice-d\` is the next candidate\|same pattern now applies to \`sprint-0/slice-d\`\|Slice D is cleared and Slice D is \`Ready\` as the next candidate' docs/delivery \|\| true` | No matches after Slice E coherence updates. |

### c.10 Scope-audit commands

The independent verifier (the controller, Nefarious / Hermes) runs:

| Command | Expected result |
|---|---|
| `git diff --name-only \| sort` | Sorted output equals the sorted union of `allowed_create_paths` and any actually-applied `allowed_update_paths`. |
| `git diff --check` | No output, exit 0. |
| prohibited-surface grep over the diff | No path under any of the prohibited surfaces in §c.6. |
| validator runs (when applicable) per §c.9 | Same expectation. |
| stale-language scan per §c.9 | No matches. |
| markdown link sanity over the changed files | Repo-relative cross-references resolve in the worktree. |
| `git worktree list` / `git stash list` (read-only) | No unexpected worktrees on this branch; no interaction with unrelated stash entries. |

### c.11 Review / verification evidence fields

| Field | Value for this dry run |
|---|---|
| `consumer_self_report` | The visible Claude Code pane's report-back per [`./ENVELOPE_CONSUMPTION_CHECKLIST.md`](./ENVELOPE_CONSUMPTION_CHECKLIST.md) §g, captured at the stop line. Counts as **verification evidence**, not Source ratification. |
| `independent_verifier_record` | Nefarious's scope-audit record per [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) §l, delivered to Source. Counts as **verification evidence**, not Source ratification. |
| `independent_review_evidence_ref` | Not applicable for this batch; covered by the explicit Source-ratified named waiver in §c.2. The waiver is bounded to this batch and does not generalize. |
| `review_gate_state` | Cleared under the named waiver per [`./REVIEW_GATE.md`](./REVIEW_GATE.md) §c.4. |

### c.12 Dry-run marker

| Field | Value |
|---|---|
| `dry_run_marker` | True. This document is a non-authorizing rehearsal. It does NOT execute a real downstream assignment, does NOT create a downstream branch / worktree / PR / commit / stage / merge, and does NOT assign a real implementation task. |
| `dry_run_evidence_ref` | This document, repo-relative path `docs/delivery/ASSIGNMENT_ENVELOPE_DRY_RUN.md`. |
| `handoff_artifact_ref` | The Hermes handoff under the worktree's `.hermes/` directory authored at `2026-05-14`. Runtime-local per [`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md) §g; referenced, not embedded. |

### c.13 Stop condition

The consumer's terminal action under this envelope is the exact
wording:

> End of Sprint 0 Slice E authoring batch. Awaiting Nefarious
> independent verification and Source validation before staging,
> commit, push, PR, merge, or branch deletion.

The consumer MUST NOT cross this stop line. Mechanics are a
separately ratifiable action that this envelope does **not**
authorize.

## d. Commands marked observed vs. hypothetical

Because this dry run is itself the Slice E docs-only batch, the
commands fall into two groups:

### d.1 Observed in this Slice E batch

The following commands were run (or are expected to be run) locally
by the consumer or the verifier against this worktree, with their
results recorded in the consumer's report-back per
[`./ENVELOPE_CONSUMPTION_CHECKLIST.md`](./ENVELOPE_CONSUMPTION_CHECKLIST.md)
§g and the verifier's report-back per
[`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md) §l:

- `git status --short --branch --untracked-files=all`
- `git branch --show-current`
- `git log -1 --oneline`
- `git diff --name-only`
- `git diff --check`
- the stale-language scan in §c.9
- the validator runs in §c.9, when locally available; their exit
  statuses and any baseline failures are recorded with rationale

### d.2 Hypothetical for any future real assignment

The following commands are described **only** as the contract a
future downstream batch would obey under a separately Source-
ratified envelope. They are **not** executed under this dry run:

- `git add`, `git commit`, `git push`, `gh pr create`, `gh pr
  merge` — none occur under this batch.
- `git branch -d` / `-D` against any branch — none occurs.
- `git worktree remove` against any worktree — none occurs.
- Any `gh api` / `gh repo edit` / live source-host mutation —
  none occurs.
- Any deploy-automation invocation — none occurs.

These commands are part of the **mechanics** the stop line in
§c.13 defers to a separately ratified envelope.

## e. Evidence that dry-run consumption stops at Source validation

The dry run is **consumed only up to Source validation**. The chain
of evidence is:

1. The consumer authors the five new files and any minimal coherence
   updates under the allowed-paths set in §c.5.
2. The consumer runs the validation commands in §c.9, captures
   results, and assembles a report-back per
   [`./ENVELOPE_CONSUMPTION_CHECKLIST.md`](./ENVELOPE_CONSUMPTION_CHECKLIST.md)
   §g.
3. The consumer halts at the stop line in §c.13. No staging,
   commit, push, PR, merge, branch deletion, worktree removal, or
   repository-setting mutation occurs under the consumer's
   authorship.
4. The controller (Nefarious / Hermes) runs the scope-audit
   commands in §c.10 against the worktree per
   [`./SCOPE_AUDIT_CHECKLIST.md`](./SCOPE_AUDIT_CHECKLIST.md).
5. The controller delivers the audit's report-back to Source as
   verification evidence. Author/approver separation is preserved:
   the controller is not the ratifier.
6. **Source then validates** the envelope's outcome. Source's
   validation is the only authority that decides what happens next
   (mechanics, scrap/redo, amendment under the same envelope, or
   no-op).

The dry run does **not** proceed beyond step 6. No subsequent
mechanics are authorized by this document.

## f. Non-authorizing scope statement

For completeness, the dry run restates its non-authorizing scope:

1. No downstream branch is created.
2. No downstream worktree is created.
3. No downstream PR is opened, edited, or merged.
4. No downstream commit is created.
5. No file outside the Slice E `allowed_create_paths` /
   `allowed_update_paths` set is staged or committed.
6. No real implementation task is handed to a downstream consumer
   under this document. Any future implementation task requires its
   own Source-ratified envelope under
   [`./ASSIGNMENT_ENVELOPE_TEMPLATE.md`](./ASSIGNMENT_ENVELOPE_TEMPLATE.md).
7. The Slice E branch and worktree are preserved per
   [`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md)
   §k until Source separately approves cleanup.

## g. Acceptance posture for Slice E

This document satisfies the Slice E envelope's
`ASSIGNMENT_ENVELOPE_DRY_RUN.md` requirements:

- Provides a sample filled envelope using this exact Slice E
  worktree / branch (§c).
- Lists the commands that would be used to verify scope, marked as
  either observed in this Slice E doc batch (§d.1) or explicitly
  marked as hypothetical for a future task (§d.2).
- Performs no real downstream assignment, no new worktree / branch
  execution, no PR / commit / stage / merge (§f).
- Names evidence that dry-run consumption stops at Source
  validation (§e), with the explicit stop line in §c.13 as the
  terminal action.
