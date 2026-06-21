# Merge-queue enablement runbook (ce-ops#39, F6 Phase-1)

Status: **READY — gated controller/Operator action.** This runbook is the
procedure to turn GitHub's native merge queue ON for
`creator-engine/creator-engine`'s `main`. The CI prerequisite (the `merge_group`
trigger) ships ahead of it as ordinary code (see slice plan §6); flipping the
queue + re-tightening protection are the only gated steps and they are **not**
executed by this document.

Companion: `GITHUB_NATIVE_COORDINATION_PROTOCOL.md` §g (the F6 design + authority
semantics). Read that first.

---

## 0. Why (the live tax this retires)

Strict up-to-date protection makes every merge move `main`, leaving every other
open PR behind base. With `dismiss_stale_reviews` + `require_last_push_approval`,
the **author's rebase force-push dismisses the human approval**, so a serial
merge train pays a fresh code-owner review per step (this blocked #297/#296
live). GitHub's native merge queue removes the tax: on enqueue GitHub builds a
`merge_group` (base + queued PRs on a temporary `gh-readonly-queue/{base}`
branch), runs the required checks **there**, and fast-forwards `main`. The
queue's rebase is a **server-side `merge_group` event, not an author push**, so
the stale-review / last-push-approval machinery (which keys off pushes to the PR
head) does not fire — the approval attaches to the reviewed change and survives.

---

## 1. Prerequisite (MUST be live on `main` before enabling) — VERIFIED in code

Every **required** status-check workflow must trigger on `merge_group`, or the
queue stalls forever (the required check never reports on the merge group, and
GitHub waits on a status that never arrives).

- `validate.yml` now carries `merge_group: { types: [checks_requested] }`
  alongside `pull_request` / `push` (this branch, ce-ops#39). The
  `path-manifest PR-diff gate (G-ii)` step stays `pull_request`-only on purpose:
  there is no per-PR carrier diff to check on the synthetic merge commit, and the
  carrier was already validated on the PR.
- `ce-ops-autoclose.yml` is **not** a required check and triggers on
  `pull_request: closed`; it has no merge-group role — leave it unchanged.
- Guard test: `validators/tests/unit/test_workflow_merge_group_trigger.py` fails
  if any required-check workflow loses the `merge_group` trigger.

> Do not enable the queue until this prerequisite commit is merged to `main`.
> Enabling first = guaranteed stall.

---

## 2. The enable flip (gated — DO NOT run unattended)

The queue is configured through a **repository Ruleset** (consistent with the
rulesets-fallback path; classic branch protection cannot express a merge queue).
Two equivalent paths:

### 2a. Via the CE forge adapter (preferred — auditable, idempotent, plan-first)

`RulesetPolicy` now carries an opt-in `merge_queue` rule (ce-ops#39). Plan first,
inspect, then apply:

```python
from creator_engine_validator.forge import RulesetPolicy, upsert_ruleset
from creator_engine_validator.forge.ruleset import CE_PROTECTION_RULESET_NAME

policy = RulesetPolicy(
    name=CE_PROTECTION_RULESET_NAME,
    branch="main",
    required_status_check_contexts=("Validate governance artifacts",),
    require_last_push_approval=True,      # survives the queue (see §4) — KEEP it on
    dismiss_stale_reviews_on_push=True,   # KEEP it on
    allowed_merge_methods=("squash",),    # the squash-only floor
    require_merge_queue=True,             # the flip
    merge_queue_merge_method="SQUASH",    # must agree with allowed_merge_methods
    merge_queue_grouping_strategy="ALLGREEN",  # require every entry to pass (safest)
    merge_queue_max_entries_to_build=5,
    merge_queue_max_entries_to_merge=5,
    merge_queue_min_entries_to_merge=1,
    merge_queue_min_entries_to_merge_wait_minutes=5,
    merge_queue_check_response_timeout_minutes=60,
)
# PLAN (mutates nothing):
print(upsert_ruleset("creator-engine/creator-engine", policy, apply=False).to_dict())
# APPLY (gated):
# upsert_ruleset("creator-engine/creator-engine", policy, apply=True)
```

The adapter reads current state, computes the diff, and only writes on drift;
`apply=True` re-reads to verify.

### 2b. Via the GitHub UI (equivalent, for a human checker)

Settings → Rules → Rulesets → the `ce-reference-protection-floor` ruleset → add
rule **"Require merge queue"**. Set: merge method **Squash**; grouping strategy
**ALLGREEN** ("Require all queue entries to pass required checks"); build limit
**5**; min/max merge entries **1 / 5**; min-entries wait **5 min**; status-check
timeout **60 min**. Keep the existing "Require status checks to pass"
(`Validate governance artifacts`, strict) and the pull_request rule
(≥1 approval, dismiss-stale, last-push-approval, conversation resolution).

### Settings rationale (tune later by observed load)

| Setting | Value | Why |
| --- | --- | --- |
| merge method | SQUASH | matches the squash-only floor; `runtime_merge_audit` already proves squash tree-equivalence |
| grouping_strategy | ALLGREEN | every PR in the group must pass — safest; HEADGREEN only batches faster at the cost of which-PR-broke ambiguity |
| max_entries_to_build | 5 | caps concurrent CI builds (the expensive shared-wheelhouse rebuild); raise if CI is cheap and queue is deep |
| max_entries_to_merge | 5 | batch ceiling; amortizes the rebuild across queued PRs |
| min_entries_to_merge / wait | 1 / 5 min | at 2-host volume, don't wait to batch — merge a single ready PR after 5 min |
| check_response_timeout | 60 min | > the Validate job's worst-case wall time; below it GitHub assumes failure |

---

## 3. Re-tighten the surgical bridge (do this AS the queue goes live)

The current settings were loosened as a **surgical bridge** to let the serial
train make progress despite the re-review tax. Once the queue is live, approval
survives the queue's rebase (§4), so re-tighten:

- **Keep `dismiss_stale_reviews` ON** and **`require_last_push_approval` ON.**
  These are CE's separation-of-duties floor; the queue no longer fights them
  because the rebase is a `merge_group` event, not an author push. (If either
  was temporarily relaxed during the bridge, restore it in the same ruleset
  apply as §2.)
- **Keep `enforce_admins` / no bypass actors.** The queue runs *after* the
  independent approval; admins still cannot merge past the gate.
- **Stop forcing author rebases.** Authors no longer update-branch-and-wait; the
  queue rebases server-side. Remove any "update branch" step from the controller
  merge flow.
- **`strict` (up-to-date) required checks:** the queue subsumes the up-to-date
  guarantee (it tests the integrated future state). Leaving `strict` on is
  harmless with the queue; it is no longer the bottleneck.

---

## 4. The approval-survival caveat — VERIFY EMPIRICALLY before trusting the train

GitHub's docs state the queue gives the same benefit as up-to-date without author
rebases, and that approvals attach to the reviewed change. **But GitHub hedges**
("in most situations") on approval-preservation under merge-base motion, and
there are open community reports of "merge-base changed after approval"
dismissals. This is INFERRED-with-risk, not VERIFIED for our exact ruleset.

**Acceptance test (run once, on enable, before draining a real train):**

1. Open two trivial PRs (A, B) off the same base; get each a non-author approval.
2. Enqueue A, let it merge (moves `main`).
3. Enqueue B. Confirm B's approval is **still present** after the queue rebases
   B onto the new `main` and that the `merge_group` Validate check runs and
   reports green on `gh-readonly-queue/main`.
4. Confirm B merges **without** a fresh review.

If step 3/4 shows a re-dismissal, the queue alone does not fully retire the tax
for our settings → fall back to keeping the Phase-0 re-stamp as the merge path
and open a GitHub support thread; do not re-tighten further until resolved.

---

## 5. Sequencing vs the live merge train

1. Land the §1 prerequisite (`merge_group` trigger) to `main` through the
   **current** serial path. It is an ordinary PR; it does not need the queue.
2. **Drain the in-flight train to empty** (or to a clean stopping point) under
   the current serial process. Do not flip mid-train — a half-queued train mixes
   two merge regimes.
3. Apply the §2 ruleset flip (queue ON) + §3 re-tighten, in one ruleset apply.
4. Run the §4 acceptance test on two throwaway PRs.
5. Switch `cev3 merge --apply` from direct squash PUT to enqueue (slice §6 F),
   appending `pr_enqueued` then `pr_merged` only after GitHub reports the queue
   merge; keep the post-merge `runtime_merge_audit` (now auditing the queue
   result).

---

## 6. Rollback

The flip is a single ruleset rule. To disable: re-apply the §2 policy with
`require_merge_queue=False` (or delete the "Require merge queue" rule in the UI).
CE's merge path reverts to the Phase-0 direct squash + re-stamp, which remains
fully functional and is never removed. No data migration; the evidence chain is
append-only and unaffected.
