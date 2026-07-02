# From Agile/SCRUM to Creator Engine SDLC

> **DRAFT — pending Operator sign-off.**
>
> This public draft is for review only. Do not link it from the public site
> navigation until sign-off confirms the terminology, examples, and product
> positioning.

Agile and SCRUM give teams a familiar language for deciding what to build,
sequencing the work, and proving that an increment is done. Creator Engine
(CE) keeps those product instincts, but moves the center of gravity from
ceremony and timeboxes to **spec-driven artifacts, governed execution, and
explicit ratification**.

If you already think in sprints, backlog items, acceptance criteria, reviews,
and Definition of Done, this guide maps that muscle memory onto CE's SDLC. The
short version: CE turns intent into a spec, plan, task set, reviewed change,
carrier, changelog, and ratified delivery record. CI is part of the proof, but
CI does not authorize the work by itself.

---

## The Mental Model

SCRUM is usually organized around a team cadence. CE is organized around a
governed unit of change.

In SCRUM, a team takes items from a backlog into a sprint, coordinates daily,
reviews the increment, and decides whether it satisfies the Definition of Done.
In CE, a contributor or governed agent moves a scoped change through durable
artifacts:

**spec -> plan -> tasks -> implementation -> independent review -> ratification
-> changelog + carrier -> ship**

The artifacts matter because they survive context loss. A chat transcript can
help explain a decision, but it is not the source of truth. The spec says what
is being built, the plan says how, the task list gives execution order, the
pull request carries the diff, the changelog records the user-facing result,
and the carrier declares the exact path set the change is allowed to touch.

---

## SCRUM to CE Mapping

| SCRUM concept | CE equivalent | What changes |
| --- | --- | --- |
| Sprint | Arc or wave | Work is grouped by outcome and dependency order, not only by calendar time. |
| Product backlog | Projects board and task queue | Ready work is tracked as ordered issues or tasks, with dependencies and ownership visible. |
| User story | Scoped task from a spec | The unit of work is tied back to a written spec, plan, and done criteria. |
| Story points | Work class: `XS`, `S`, `M`, `L` | Size is declared as an execution and review floor, not a velocity accounting unit. |
| Sprint planning | Spec and plan review | The team shapes intent before implementation and checks that scope, budget, risk, and dependencies are explicit. |
| Backlog refinement | Spec clarification and task decomposition | Ambiguity is resolved in the artifact, then reflected in plan and tasks. |
| Daily standup | Async controller and seat flow | Progress is reported through issue comments, PR state, CI, review evidence, and handoff notes rather than synchronous status meetings. |
| Pull request review | Independent governed review plus ratification | A separate reviewer inspects the artifacts; authorization remains a ratification act, not a rubber stamp from green CI. |
| Definition of Done | CI gates plus envelope authority | Tests, validation, path scope, review, and ratification must all fit the authorized envelope. |
| Sprint review | Completion evidence | The useful demo artifact is the merged or reviewed change plus its evidence chain. |
| Retrospective | Changelog and process feedback | Lessons become durable docs, specs, checks, or follow-up tasks. |

---

## From Sprint to Arc or Wave

A sprint is a timebox. An arc or wave is an outcome slice.

An arc describes a coherent product or platform objective: for example,
"make first-run onboarding reliable" or "ship governed PR review for external
contributors." A wave is a smaller batch inside that arc, usually chosen
because the tasks share dependencies or can land together cleanly.

The practical difference is that CE does not ask work to wait for the next
ceremony if the artifacts and gates are ready. A small `XS` docs fix can move
through quickly. A larger `M` or `L` feature can be split into smaller tasks
inside the same arc so each PR remains reviewable and governed.

---

## From Backlog to Projects Board

A SCRUM backlog is the ordered list of future work. In CE, the equivalent is
the Projects board and issue/task queue, backed by specs and plans.

Good CE backlog items are not just titles. They should point to the artifact
that explains why the work exists:

- A spec for the user need and acceptance criteria.
- A plan for the technical approach and known constraints.
- Tasks that can be claimed, reviewed, and shipped independently.
- Dependencies that make sequencing clear.

This keeps product intent and implementation work aligned. A task without a
spec is easy to misunderstand. A spec without tasks is hard to execute. CE
expects both sides to stay connected.

---

## From Story Points to Work Class

Story points estimate relative effort for planning. CE work class declares the
minimum governance floor for a change.

| Work class | Use it for | Typical expectation |
| --- | --- | --- |
| `XS` | Small, low-risk changes | Narrow diff, obvious review surface, limited validation burden. |
| `S` | Routine single-slice work | Clear scope, focused tests or docs evidence, independent review. |
| `M` | Multi-file or behavior-bearing work | Stronger explanation, broader validation, careful dependency handling. |
| `L` | Large or cross-cutting work | Split when possible; when not possible, expect explicit rationale and heavier review. |

The class is not a promise that the work was easy. It is a public declaration
of how much process and evidence the change must carry. CE validators can
compare the declared class against the actual PR diff and reject changes that
understate their size.

---

## From Standup to Async Controller and Seat Flow

SCRUM standup answers: What changed? What is next? What is blocked?

CE answers those questions through the work itself:

- The Projects board shows what is ready, claimed, blocked, or under review.
- The issue thread records the claim, context, and handoff notes.
- The branch and PR show the implementation state.
- CI and validation show whether the change is mechanically acceptable.
- Review comments show whether an independent reviewer accepts the artifacts.

That async flow matters because governed work may involve multiple seats:
one actor shapes or dispatches, another implements, and a distinct reviewer
checks the result. The process avoids relying on a meeting transcript as the
record of truth.

---

## From PR Review to Independent Review and Ratification

In many SCRUM teams, a PR review is both a quality check and an informal signal
that the work can merge. CE separates those concerns.

Independent review asks: Does this artifact satisfy the spec, plan, task, and
done criteria? Is the diff understandable? Are the tests or docs evidence
adequate? Did the work stay within the declared path set?

Ratification asks a different question: Is this authorized to proceed?

That distinction is central to CE. **CI verifies; it does not ratify.** A green
build proves that checks passed. It does not prove that the change was in scope,
that the right person authorized the risk, or that the delivery envelope was
respected. Ratification is the explicit authorization step that sits above the
mechanical checks.

---

## From Definition of Done to Envelope Authority

SCRUM Definition of Done is a shared agreement about what "done" means. CE
makes that agreement enforceable with gates and envelopes.

For a CE change to be done, the evidence should show:

- The spec, plan, and task are aligned.
- The implementation stays inside the authorized scope.
- The PR path carrier lists the exact files the change is allowed to touch.
- The changelog records the user-visible or operator-visible result.
- CI and local validation pass.
- Independent review has checked the artifact.
- Required ratification exists for the risk being shipped.

The envelope is the boundary around the change: what paths, budget, authority,
and risk class are allowed. A change can pass tests and still be refused if it
escapes that envelope.

---

## Carriers and Changelog

Two CE artifacts often feel new to SCRUM teams: the carrier and the changelog.

The **carrier** is a per-PR path manifest. It lists the closed set of files the
PR is authorized to change. Validators compare the PR diff against that list.
This turns "stay in scope" from review advice into a concrete check.

The **changelog** is the durable delivery note. It is not a standup update and
not a commit message replacement. It records what changed in a way future
operators and contributors can scan without reconstructing the whole PR.

Together, the carrier and changelog make a PR easier to audit: what was allowed
to change, what actually changed, and what the result means.

---

## A Familiar Day, Translated

In SCRUM terms, you might start the day with the top backlog item, clarify
acceptance criteria, implement it, open a PR, respond to review, and move the
story to done.

In CE terms, the same day looks like this:

1. Read the spec and plan for the next task in the arc.
2. Confirm the task is unblocked and claim it.
3. Implement only the scoped change.
4. Update or add tests, docs, changelog, and carrier evidence as appropriate.
5. Run validation locally before publishing.
6. Open a draft PR with a declared work class.
7. Route it to an independent governed review.
8. Wait for ratification before merge or enqueue.

The flow is meant to feel familiar, but with sharper boundaries. CE keeps the
product conversation and removes ambiguity about authority.

---

## Adoption Notes for SCRUM Teams

Start by translating your existing nouns rather than replacing everything at
once:

- Treat epics or initiatives as arcs.
- Treat sprint-sized batches as waves.
- Treat backlog items as tasks that must point back to a spec and plan.
- Treat acceptance criteria as done criteria that validators and reviewers can
check.
- Treat story points as work-class declarations.
- Treat PR review as evidence, not authorization.

The cultural shift is small but important: CE does not ask people to stop
thinking like product teams. It asks them to make intent, scope, evidence, and
authority explicit enough that governed agents can participate safely.

---

## Before This Guide Is Linked

This draft should stay unlinked until Operator sign-off confirms:

- The public terminology is correct.
- The SCRUM mapping is accurate enough for new contributors.
- The examples match the current CE command and artifact model.
- The rendered HTML sibling and site navigation are added intentionally, if the
  site publishing flow requires them.
