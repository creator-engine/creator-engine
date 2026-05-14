# Scope Audit Checklist (Verifier-Side)

**Status**: Slice E authored draft. This is the **independent
verifier-side** checklist run after a consumer reaches the stop line
of an Assignment Envelope per
[`./ASSIGNMENT_ENVELOPE_TEMPLATE.md`](./ASSIGNMENT_ENVELOPE_TEMPLATE.md)
and
[`./ENVELOPE_CONSUMPTION_CHECKLIST.md`](./ENVELOPE_CONSUMPTION_CHECKLIST.md).

Part of the **minimum repo-native delivery control plane** and
**not a Jira clone**. Layered onto, and subordinate to, the Feature
001 substrate and the Feature 002 operating model. A fresh clone is
sufficient to apply this checklist; no external tracker credential
or network state is required.

## a. Purpose

The scope-audit checklist makes one operational fact answerable from
a fresh clone:

> Did the consumer mutate only what the Source-ratified envelope
> authorized, leave every prohibited surface untouched, perform no
> mechanics beyond the stop line, and produce verification evidence
> that a Source review can act on?

The scope audit is **verification evidence**, never Source
ratification per
[`./REVIEW_GATE.md`](./REVIEW_GATE.md) §m.1.

## b. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| [`./ASSIGNMENT_ENVELOPE_TEMPLATE.md`](./ASSIGNMENT_ENVELOPE_TEMPLATE.md) | The envelope the audit is conducted against. |
| [`./ENVELOPE_CONSUMPTION_CHECKLIST.md`](./ENVELOPE_CONSUMPTION_CHECKLIST.md) | The consumer-side checklist whose report-back the auditor consumes. |
| [`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md) | Runtime conditions the audit confirms. |
| [`./REVIEW_GATE.md`](./REVIEW_GATE.md) | Review gate the audit's findings feed. |
| [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.3 | Scope-audit Done criterion. |
| [`./NEXT_TASK_PROTOCOL.md`](./NEXT_TASK_PROTOCOL.md) §b.5 | Post-merge completion-report scope-audit field. |
| Feature 001 FR-007 / FR-008 | Author/approver separation; privileged-class enumeration. |
| Feature 002 FR-013, FR-017 | Verifies-not-ratifies invariant. |

## c. Changed-file boundary comparison

The auditor lists the changed files and compares them against the
envelope's allowed-paths set:

1. `git diff --name-only` lists every changed file relative to the
   envelope's `base_commit`.
2. The auditor sorts the output (`git diff --name-only | sort`) and
   compares element-by-element against the union of the envelope's
   `allowed_create_paths` and `allowed_update_paths`.
3. Any path in the diff that is **not** in the allowed set is a
   boundary failure. The auditor records it explicitly and either
   the consumer reverts the file or Source ratifies an envelope
   amendment naming the file.
4. Any path in the allowed set that is **not** in the diff is
   acceptable when the envelope marks it as conditional (e.g., a
   "minimal coherence update only if directly needed" file); the
   auditor confirms the conditional logic from the envelope text.

## d. Prohibited-surface check

The auditor runs a prohibited-surface scan against the diff and the
working tree:

1. Confirm `git diff --name-only` does not list any path under
   `.github/`, `CODEOWNERS`, `specs/`, `schemas/`, `validators/`,
   `templates/`, `examples/`, `tenants/`, `docs/contracts/`,
   `docs/product/`, `docs/architecture/`, `docs/governance/`,
   `docs/quality/`, `docs/devops/`, `docs/security/`, or any
   deploy-automation path, unless the envelope explicitly ratifies
   that surface.
2. Confirm no live source-host mutation occurred: branch protection,
   environments, secrets, labels, PR/issue/assignment metadata, or
   repository settings remain untouched. (Verified by absence of
   evidence in the consumer's report-back per
   [`./ENVELOPE_CONSUMPTION_CHECKLIST.md`](./ENVELOPE_CONSUMPTION_CHECKLIST.md)
   §g.5.)
3. Confirm no `CODEOWNERS` file exists in the diff and no
   `.github/` workflow / template / policy file was added or
   modified.
4. Confirm no secrets, tokens, credentials, or accounts appear in
   the diff (grep for typical patterns such as `BEGIN PRIVATE KEY`,
   `api_key`, `Bearer `, `password:`; absence is the expected
   signal).

## e. No-mechanics check

The auditor confirms that the consumer did **not** cross the
envelope's stop line by performing any of the following mechanics
under the envelope:

1. **Staging**: `git status --short` shows no staged changes (`M `,
   `A `, etc. in the index column) under the envelope's authorship
   unless staging was explicitly ratified.
2. **Commit**: `git log` shows no new commit on the envelope's
   branch beyond the envelope's `base_commit` unless commit
   mechanics were explicitly ratified.
3. **Push**: no remote ref has been updated for the envelope's
   branch under the consumer's authorship. (Verified by the absence
   of any `git push` invocation in the consumer's report-back.)
4. **PR**: no PR has been created, modified, or commented for the
   envelope's branch. (Verified by the absence of any `gh pr`
   invocation in the consumer's report-back.)
5. **Merge / fast-forward**: no merge into `main` (or another base
   branch) has occurred.
6. **Branch deletion**: the envelope's `local_branch` still exists
   locally; no other branch has been deleted under the envelope.
7. **Repo-setting / branch-protection / hook bypass**: no `gh api`,
   `gh repo edit`, `git config`, `--no-verify`, or signing-bypass
   invocation appears in the consumer's report-back.

A "no-mechanics" finding does **not** authorize subsequent mechanics
on its own; mechanics remain a separately ratifiable action under
[`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md)
§i and §j.

## f. `git diff --check` whitespace / hunk-marker check

The auditor runs `git diff --check` against the working tree. The
expected result is **no output and exit status 0**: no trailing
whitespace introduced, no conflict markers left in files, no
new whitespace errors. Any failure is recorded and either remediated
by the consumer or surfaced as a blocking finding to the controller
and Source.

## g. Validator runs (when applicable)

When the envelope or the Definition of Done names Creator Engine
validator runs, the auditor runs them locally without mutating any
file:

```
PYTHONPATH=validators python -m creator_engine_validator check-examples
PYTHONPATH=validators python -m creator_engine_validator scan-no-limitless
```

(Concrete python interpreter path is a workstation-local fact and
MUST NOT propagate into governed artifacts beyond reproduction
instructions.)

The auditor records exit statuses and any failure output. If the
failures are baseline failures unrelated to the docs-only batch
under audit, the auditor records the exact output and the rationale
for not patching validators or non-allowed files under this
envelope. The auditor MUST NOT silently broaden scope to "fix" a
validator finding outside the envelope's allowed paths.

A check that is intentionally skipped is named explicitly with a
rationale, per
[`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §b.2.

## h. Stale-language scans

The auditor scans for stale language carried over from prior slices.
At minimum, the auditor confirms there is no remaining claim that a
predecessor slice is the next candidate envelope after this batch
has cleared its predecessor edge. For Slice E, the auditor scans
for stale Slice-D-next-candidate phrasing:

```
grep -RInE --exclude=SCOPE_AUDIT_CHECKLIST.md 'Slice D is (the )?next candidate|sprint-0/slice-d` is the next candidate|same pattern now applies to `sprint-0/slice-d`|Slice D is cleared and Slice D is `Ready` as the next candidate' docs/delivery || true
```

The `--exclude=SCOPE_AUDIT_CHECKLIST.md` flag excludes this audit
checklist itself, which is the regex's documented home; the
audit is concerned with stale prose elsewhere, not with the
regex documented here. The expected result for a successful
Slice E batch is **no matches**. Other stale-language scans appropriate to a given batch
(e.g., for canonical-document subtrees a batch did not touch) may
be added to the audit; absence of a relevant scan with a recorded
rationale is itself a scope-audit data point.

## i. Markdown link / reference sanity

The auditor performs a lightweight markdown link sanity pass over
the changed files:

1. New cross-references between Slice E docs resolve to existing
   files in the worktree (e.g., `[../REVIEW_GATE.md]` points at a
   file that exists).
2. Links to upstream sources of truth (e.g.,
   `../governance/AUTHORITY_AND_RATIFICATION_MODEL.md`,
   `../../specs/002-canonical-docs-and-operating-model/spec.md`)
   are repo-relative and target real files under the canonical
   branch's tree.
3. No `http(s)://` link is introduced into a governed artifact
   except to a Source-ratified domain, and no link relies on a
   tracker credential or network state.

Broken links are recorded as findings; the consumer remediates them
under the envelope's authorship or Source ratifies an amendment.

## j. Local hygiene and branch / worktree isolation

The auditor confirms runtime hygiene per
[`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md):

1. `git branch --show-current` reports the envelope's `local_branch`
   and only that branch is under the consumer's authorship.
2. `git worktree list` shows the worktrees Source authorized; no
   unexpected worktrees exist on this branch.
3. `git stash list` is read-only; unrelated stash entries
   (e.g., `stash@{0}` not authorized by this envelope) have NOT been
   applied, dropped, or inspected.
4. No state from another project or tenant has leaked into this
   worktree per
   [`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md)
   §h.
5. The one-driver-per-worktree invariant per
   [`./WORKTREE_RUNTIME_PROTOCOL.md`](./WORKTREE_RUNTIME_PROTOCOL.md)
   §d was preserved for the duration of the consumer's authorship.

## k. Review evidence is not Source ratification

The auditor records, explicitly, that the scope audit itself is
**verification evidence** and not Source ratification. Specifically:

1. A passing scope audit does **not** authorize staging, commit,
   push, PR, merge, branch deletion, or any repository-setting
   mutation. Those remain separately ratifiable actions.
2. A `no_blocking_findings` reviewer verdict, where one is recorded,
   is similarly not ratification per
   [`./REVIEW_GATE.md`](./REVIEW_GATE.md) §m.1.
3. Privileged-class mutations remain Source-only per Feature 001
   FR-008 regardless of audit findings.
4. The author/approver separation contract is preserved: the
   auditor is not the author of the batch and is not the ratifier of
   the underlying change (Feature 001 FR-007).
5. CI green, an external tracker green check, or an agent
   commentary verdict MUST NOT substitute for Source ratification
   per
   [`./DEFINITION_OF_DONE.md`](./DEFINITION_OF_DONE.md) §c.

## l. Auditor report-back

The auditor's report-back (delivered to the controller and to
Source) includes:

1. The envelope id and the consumer's stop-line text, repeated
   verbatim.
2. The output (or summary) of every check in §c–§j, with command
   lines repeated for reproducibility and exit statuses recorded.
3. Any **blocking findings** that prevent advancement past the
   review gate per
   [`./REVIEW_GATE.md`](./REVIEW_GATE.md) §i.
4. Any **skipped checks** with explicit rationale.
5. An explicit statement that the audit is verification evidence,
   not Source ratification (§k).

The auditor's report-back is the input to Source review; it is not a
substitute for it.

## m. Acceptance posture for Slice E

This document satisfies the Slice E envelope's
`SCOPE_AUDIT_CHECKLIST.md` requirements:

- Performs changed-file boundary comparison against allowed paths
  (§c).
- Confirms no prohibited surfaces touched (§d).
- Confirms no staging / commit / push / PR / merge / branch
  deletion / repository-settings mutation occurred (§e).
- Runs `git diff --check` for whitespace / hunk markers (§f).
- Runs validator `check-examples` and `scan-no-limitless` when
  applicable, or explicitly records a skipped-check rationale (§g).
- Scans for stale Slice-D-next-candidate language (§h).
- Performs a markdown link / reference sanity pass (§i).
- Confirms local hygiene and branch / worktree isolation (§j).
- States explicitly that review evidence is not Source ratification
  (§k).
