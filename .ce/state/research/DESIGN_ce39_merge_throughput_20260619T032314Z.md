# DESIGN - ce-ops#39 merge-throughput current prior-art refresh

Date: 2026-06-19T03:23:14Z
Seat: dev-3
Scope: research only; no GitHub mutation; no source-host configuration change.

## Access notes

- `gh issue view 39 --repo creator-engine/ce-ops` and REST issue reads are still blocked from this seat by PAT permissions.
- The private ce-ops file tree is readable. This note refreshes the existing ce-ops#39 artifacts from `/tmp/ce-ops-wave3`:
  - `designs/ce-merge-throughput-prior-art-20260612.md`
  - `designs/ce-f6-merge-concurrency-design-DRAFT-20260612.md`
- Current web/documentation checks were performed on 2026-06-19.

## Current prior art, June 2026

### GitHub native merge queue

GitHub merge queue remains the best forge-native fit for CE once the trigger is reached.

Current GitHub docs say merge queues are available for organization-owned public repos and private organization repos on GitHub Enterprise Cloud. The queue gives the same protection as "require branches to be up to date" without making authors update branches and wait for PR-branch checks again. A PR enters after required branch-protection checks pass; GitHub then tests the change on the latest target branch plus earlier queued PRs before merging.

Operationally, GitHub creates temporary `merge_group` branches; required workflows must trigger on `merge_group`, otherwise required checks will not report and queue merges fail. Third-party CI has to watch `gh-readonly-queue/{base_branch}` branches, whose SHA differs from the PR head. The queue is FIFO, can group PRs, has build concurrency and merge limits, and removes/rebuilds groups when a queued PR fails CI or conflicts.

Source links:
- https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/merging-a-pull-request-with-a-merge-queue
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue

### GitLab merge trains

GitLab merge trains are a parallel confirmation of the same model: queued merge requests are tested as combined future target-branch states, and later train entries include earlier queued entries. If one train pipeline fails, that MR is removed and later pipelines are recreated without it. This reinforces the industrial invariant: test the integrated future state, not only each stale PR head.

Source link:
- https://docs.gitlab.com/ci/pipelines/merge_trains/

### Zuul dependent pipelines

Zuul's dependent pipeline manager is the open, infrastructure-heavy version of the same idea. It performs speculative execution: changes are queued in order, jobs for each later change include the changes ahead of it, and if an earlier change fails, dependent later changes are retested without the failed change. This is strong prior art for correctness, but it is too much operational surface for CE's current GitHub-native pipe.

Source link:
- https://zuul-ci.org/docs/zuul/latest/gating.html

### Chromium CQ and flaky-test handling

Chromium CQ highlights the part GitHub native queue does not solve by itself: flaky failures become a throughput problem. Chromium docs describe retries as CQ's mitigation, including the tradeoff that retries reduce false-negative impact on unrelated CLs while still letting some flaky tests land. The important CE lesson is not "copy Chromium"; it is that queue adoption should budget explicit retry/quarantine policy once suites become flaky.

Source link:
- https://chromium.googlesource.com/chromium/src/+/HEAD/docs/infra/cq.md

### Uber SubmitQueue and large-scale speculation

Uber's SubmitQueue remains active as open-source prior art and still describes the high-scale model: speculative rebases validate multiple predicted future `HEAD` states in parallel; passing changes land automatically, and failures isolate the offending change and retry the rest. The original paper/blog framing remains useful for CE's long horizon, but the system is aimed at large monorepos and is not the near-term fit.

Source links:
- https://github.com/uber/submitqueue
- https://blog.acolyer.org/2019/04/18/keeping-master-green-at-scale/

### Third-party queues: Mergify/Trunk class

Current Mergify docs are useful as productized evidence for speculative checks, batching, scoped queues, and tuning throughput/cost/reliability. They also confirm the cost of leaving GitHub-native governance: another SaaS actor becomes part of the merge authority path. For CE, this is only a Phase 2 option if GitHub native merge queue hits a throughput/flakiness ceiling.

Source links:
- https://docs.mergify.com/merge-queue/
- https://docs.mergify.com/merge-queue/performance/
- https://trunk.io/blog/stop-flaky-tests-from-sabotaging-your-merge-queue

## ce-ops#131 addendum - centralized merger-agent vs author-merge

Addendum prompt read from `/home/ce-dev-3/dev3-131-addendum.md` on 2026-06-19. Direct issue reads for ce-ops#131 were not attempted here; previous ce-ops issue API access from this seat was blocked, and the local addendum provides the adjudication question.

Question answered: should CE keep the current model where the authoring controller merges its own PR after independent review and approval, or introduce a centralized merger agent? Is separated or centralized merge authority standard at large software companies?

### Who or what performs the merge

| System | Human intent actor | Final integration actor | Author self-merge after approval? |
|---|---|---|---|
| Google Critique + TAP | The author can trigger commit once LGTM, required approval, and unresolved-comment gates are satisfied. | Critique/TAP and presubmit tooling gate admission; TAP is the global CI gateway for most changes and allows the change into the codebase when associated tests pass. | Author-initiated submit is normal, but it is not ungated direct push. The author presses the intent button; tooling gates admission. |
| Meta Phabricator + Sandcastle/Landcastle | Public current docs say Phabricator helps developers review and submit stacks of diffs. Older public F8 notes describe a "Ship It" button and Landcastle handling landing, with developers not pushing directly to master. A 2026 Meta RADAR paper also frames low-risk automated review as landing qualifying diffs through layered gates. | Tool-mediated landing path: Phabricator/Sandcastle/Landcastle class, with automation around CI, review, and low-risk automation. Exact current internal landing authority is not fully public. | Best public read: developer-author can initiate, but direct author git push to trunk is not the standard path; landing is mediated by Meta tooling. |
| Chromium CQ | Author/committer triggers dry run or full run via Gerrit button or Commit-Queue label. | Chromium CQ runs the curated tests and submits the CL on full-run success. | No direct author merge to trunk in the successful CQ path. The author requests CQ submission; CQ lands. |
| GitHub native merge queue | A write-access user adds an already-protected PR to the queue. | GitHub creates merge-group branches, waits for required checks, and merges the passing group to the base branch. | With merge queue enabled, the author or maintainer enqueues; GitHub performs final integration. Plain GitHub without queue still supports author/self merge where repo policy allows it. |
| GitLab merge trains | A user with merge/push permission selects Merge or Set to auto-merge. | GitLab merge-train machinery runs merged-result pipelines and merges only after earlier train entries and its own pipeline pass. | The human starts or joins the train; GitLab performs final train integration. |
| bors/homu lineage | Reviewer/maintainer writes `bors r+` or equivalent after review. | bors bot creates a staging merge, runs CI, then fast-forwards main to the exact tested staging state if green. | No. bors explicitly replaces the green merge button with bot-mediated landing. |
| Zuul dependent pipelines | Reviewer approval/enqueue event admits changes to the gate. | Zuul speculatively tests queued future states and merges passing changes; it retests dependents after failures. | No. Zuul is the central submitter/gate. |
| Mergify | Rule conditions, labels, commands, or auto-merge configuration express merge intent. | Mergify app auto-queues or auto-merges once merge-protection conditions pass, and its queue tests PRs against latest main before merging. | Optional. Mergify can leave manual merge in place, but its value proposition is central app-mediated queue/merge. |
| Uber SubmitQueue | Changes enter a queue under local policy. | SubmitQueue speculatively rebases and validates predicted future HEAD states; passing changes land automatically and failures are isolated without human intervention. | No at scale. SubmitQueue is explicitly a centralized automated submitter. |

Current public evidence is nuanced. Google Critique is the counterexample to a blanket "big companies never let authors press submit": the author can trigger commit after review gates. But even there, the actual governance model is not "author has unilateral merge authority"; it is "author submits intent after reviewer/owner approval, automated presubmits/TAP gate admission, and post-submit TAP/build-cop/rollback systems police the trunk." The rest of the high-throughput queue systems converge more strongly on centralized automated submission.

Therefore the industry answer is:

- Centralized or automated final integration is standard for high-change-rate, trunk-sensitive systems.
- Centralized human mergers are not the standard pattern; they create a bottleneck and a new trust choke point.
- Author-initiated merge intent after approval is common, but direct author-as-final-integrator is mostly a lower-scale forge workflow, not the dominant big-monorepo answer.

### Separation-of-duties and governance angle

The common four-eyes split is between author and reviewer/owner approval, not necessarily between author and the person who clicks a UI button. Large systems then add a third role: an automated integrator that is allowed to move trunk only when objective gates pass on the integrated state.

This gives three separable authorities:

1. Authorship authority: produce the change.
2. Review/approval authority: certify the change is acceptable; usually at least one non-author reviewer or owner.
3. Integration authority: create the actual trunk state and prove `tested == merged`.

For CE, the important governance improvement is not "another human or controller must press merge." It is making the integration actor auditable, deterministic, and incapable of overriding review/ratification. A merger agent must be a submitter, not an approver. It may enqueue, restamp base-only movement, observe required checks, merge, and write evidence. It must not waive review, approve its own changes, mutate content, or override head pins without the ce-ops#39 change-block proof.

### Trade-offs: centralized merger agent vs author-merge

Centralized automated merger agent:

- Pros: clearer audit trail; one integration policy; easier `tested == merged` proof; queue ordering; batching/speculation; fewer stale-base/re-review loops; better separation between authoring controllers and final trunk mutation; simpler future support for many authoring controllers feeding a PR-opened gate.
- Cons: bottleneck/SPOF if a single service or credential stalls; priority/queue semantics become policy; agent bugs have broad trunk blast radius; extra observability and evidence records are needed; third-party queues add vendor trust; GitHub native queue is a black box that CE can only audit around; flaky tests can stop the queue.

Author-controller merge after independent approval:

- Pros: minimal infrastructure; no new always-on actor; easy local debugging; low latency at current CE volume; no extra queue credential or service posture.
- Cons: weaker optics for author/merger separation; inconsistent merge identity across controllers; repeated stale-base churn under concurrency; no natural place for batching, priority, or cross-controller drain policy; harder to prove an integrated future state when several approved PRs race for trunk.

Centralized human merger:

- Pros: simple conceptual separation.
- Cons: worst of both sides for CE: human bottleneck, manual scheduling, unclear machine proof, and no throughput benefit. The surveyed systems automate the integrator instead of creating a human merge clerk.

### CE recommendation for ce-ops#131

Best fit: **hybrid, with a future centralized automated merger-agent role, not an immediate centralized human merger and not a broad replacement of ce-ops#39 Phase 0.**

Immediate Phase 0:

- Keep the current authoring-controller/operator merge act after independent review and approval while CE volume is low.
- Tighten the semantics through ce-ops#39: no head override; base-only motion requires machine-proven change-block equivalence and fresh checks; content drift requires full re-ratification.
- Record explicitly that the authoring controller is expressing merge intent under review/ratification, not self-approving.

Phase 1, at the same trigger as #39 GitHub merge queue adoption or when the post-automation factory has several controllers feeding PR-opened gates:

- Introduce `merger-agent` as an automated integration actor.
- Preferred implementation is GitHub native merge queue first: CE's merger-agent enqueues approved/restamped PRs, observes queue state, records `pr_enqueued`, records final `pr_merged`, and audits patch-id/tree-diff equivalence.
- If GitHub MQ is not enabled yet, a minimal CE merger-agent may drain a ready-to-merge queue serially with the same current squash API, but it must still use the latest attested/restamped head and must not approve, waive, or override.
- Keep a break-glass direct merge path for urgent repair only if it produces explicit evidence and remains subject to independent review/ratification policy.

Answer to "is it standard at big cos?": **yes, separated/tool-mediated final integration is standard at large scale; no, a centralized human merger is not the standard.** The standard pattern is author or reviewer expresses intent, independent approval gates the change, and a trusted automated submitter/queue performs final integration or admission.

Additional source links for #131:
- https://abseil.io/resources/swe-book/html/ch19.html
- https://abseil.io/resources/swe-book/html/ch23.html
- https://engineering.fb.com/2023/06/27/developer-tools/meta-developer-tools-open-source/
- https://engineering.fb.com/2012/07/06/web/under-the-hood-timeline-apps-behind-facebook-engineering/
- https://arxiv.org/abs/2605.30208
- https://github.com/bors-ng/bors-ng

## CE recommendation

Best fit for CE now: **keep ce-ops#39 Phase 0 as the active near-term design**.

Phase 0 should remain the two-tier change-block restamp:

1. Content changed, path-set changed, content pins changed, or equivalence cannot be proven -> full re-ratification.
2. Base-only motion with machine-proven equivalence -> automatic restamp, re-run checks, then merge the newly tested/restamped head.

This directly preserves CE's invariant:

> what-was-TESTED == what-MERGES

It also avoids inventing a human `--head-override`, which the surveyed systems do not support as a safe category. The authority shift is from "reviewed commit SHA" to "ratified change-block identity + attested integrated/tested state."

Best fit at the throughput trigger: **GitHub native merge queue**.

Adopt GitHub MQ when either recorded trigger is met:

- 3 or more concurrent ratified PRs more than once per week; or
- a third authoring host is onboarded; or
- an equivalent controller-observed merge tax appears, such as repeated wheelhouse/reviewer rebase serialization consuming reviewer venue capacity.

Implementation notes for that adoption:

- Add `merge_group` to required GitHub Actions workflows before enabling the queue.
- Keep required review, dismiss-stale, code-owner review, conversation resolution, and enforce-admins/ruleset protections.
- Change CE's merge leg from direct squash PUT to enqueue/observe/audit.
- Record `pr_enqueued` and final `pr_merged` evidence.
- Audit the queue result by patch-id/tree-diff equivalence to the ratified/restamped change-block, especially because CE currently uses squash merges.
- Treat flaky handling as an explicit queue-policy follow-up; GitHub native MQ evicts/rebuilds on failed required checks, so retries/quarantine are CE's responsibility if flakes grow.

Rejected for CE now:

- Immediate third-party queue: too much extra trust surface for the current repo volume.
- Self-hosted Zuul/SubmitQueue: correct model, wrong operational weight.
- Human/operator head override: unsafe authority framing; use machine-proven restamp or full re-ratification.

Bottom line: **Phase 0 restamp remains the correct immediate fix; GitHub native merge queue is the correct Phase 1 integrator when CE's observed concurrency crosses the trigger.**
