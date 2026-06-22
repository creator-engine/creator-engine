# Contract: GitHub Issue Intake Role

**Status:** Draft contract for `creator-engine/creator-engine#83`.
Documentation-only slice; this document does not add runtime enforcement,
GitHub mutation tooling, workflow wiring, or validator behavior.

## Purpose

The GitHub Issue intake role converts an Operator-approved intent into a
bounded GitHub issue-opening mutation. The role may gather candidate issue
content, search for duplicates, select existing labels, and prepare an issue
body for approval. It MUST NOT create, edit, label, assign, close, reopen, or
otherwise mutate a GitHub issue until the Operator explicitly authorizes the
exact mutation.

GitHub issues coordinate intent, discussion, and queue visibility. An opened
issue does not authorize implementation. Implementation still requires the
normal governed work claim, scoped handoff or task authority, review path, and
merge gate for the relevant work class and mutation class.

## Role Boundary

The intake role is a sub-agent or seat acting on behalf of an Operator. It is
permitted to perform read-only repository and issue discovery before approval:

- inspect the target repository's existing issues, labels, and issue template
  conventions;
- draft a title, body, and label set;
- compute the candidate body hash;
- report duplicate candidates and missing information.

The role is not an implementer authority. It MUST NOT start a branch, edit
tracked source, open a pull request, assign implementation work, or treat the
new issue as permission to begin implementation.

## Required Intake Flow

Every issue-opening attempt MUST follow this order.

1. **Capture intent.** Record the target repository, requested issue purpose,
   proposed title, proposed body, desired labels, and any requested assignee or
   milestone. If intent is incomplete, stop and ask the Operator before any
   mutation.
2. **Search for duplicates.** Search open and recently closed issues in the
   target repository using the proposed title, domain keywords, and any named
   component or error text. Report candidate duplicates by URL, issue number,
   title, state, and why they may match.
3. **Select existing labels only.** Read the target repository's current label
   set and choose labels from that set. The intake role MUST NOT create,
   rename, recolor, or delete labels as part of issue intake. If an intended
   label does not exist, report it as unavailable and ask the Operator whether
   to proceed without it or use an existing alternative.
4. **Prepare the mutation preview.** Present the exact target repository,
   operation, title, body, labels, assignees, milestone, duplicate-search
   evidence, and candidate body hash.
5. **Obtain explicit Operator authority.** The Operator must approve the exact
   mutation after seeing the preview. Authority must name the target repository
   and issue-opening action. A broad instruction such as "track this" or "make
   an issue if needed" is insufficient authority to mutate GitHub state.
6. **Perform only the approved mutation.** The mutation must match the approved
   preview. If any field changes after approval, return to step 4.
7. **Return mutation evidence.** After a successful mutation, return the issue
   URL, issue number, final body hash, final title, final labels, mutation time,
   actor identity when available, and the command or API surface used with
   credentials redacted.

## Duplicate Search Evidence

The duplicate search is required even when the Operator supplies a specific
new issue title. Evidence SHOULD include:

- the query strings or search terms used;
- whether open issues, closed issues, or both were searched;
- the top matching issue URLs and numbers, or an explicit "no duplicate
  candidates found" statement;
- the intake role's reason for opening a new issue despite any candidates.

Duplicate evidence is advisory. The Operator decides whether a candidate is a
true duplicate, but the intake role MUST surface the evidence before mutation.

## Body Hash

The returned body hash binds the reviewed body to the mutated issue. The hash is
the SHA256 of the exact UTF-8 issue body submitted to GitHub, after any final
template rendering and before transport. The evidence line uses this shape:

```text
ISSUE_BODY_SHA256=<64 lowercase hex chars>
```

If GitHub normalizes display formatting after submission, the intake role still
reports the submitted-body hash and may additionally report a fetched-body hash
when it can retrieve the resulting issue body.

## Refusal Conditions

The intake role MUST refuse or stop before mutation when:

- explicit Operator authority for the exact issue-opening mutation is absent;
- duplicate-search evidence has not been produced;
- the selected labels are not existing labels in the target repository;
- the proposed mutation includes implementation authorization language;
- the requested action would require runtime tooling or repository mutation
  outside issue creation.

## Non-Goals

This contract does not define an implementation API, a CLI, a GitHub App
permission set, automation for issue mutation, or a validator check. Those may
be designed in later slices only after separate authority and scope are granted.
