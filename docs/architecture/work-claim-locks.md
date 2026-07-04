# Work-Claim Locks (ce-ops#38)

> Per-ticket compose/dispatch claims — hub-visible and machine-checked. Extends
> CE's claim discipline from *repo lanes* (the PCO lease/active-work primitive)
> to *work items* (compose / implement / research / review tasks), which until
> now had **zero contention control**.

## Why

At 6+ concurrent workstreams across two hosts, two controllers can fire seats at
the *same ticket* and duplicate work. This happened twice (the #16 spec
near-miss; the #174/#175 duplicated site PRs) and was caught only by a human
reading the other controller's pane. Eyeballs do not scale; claims do. The
interim mitigation was a standing ops rule (post a `🔒 in-compose <host>` comment
before dispatching, check for an existing one first). This gate makes that rule
**first-class and machine-checked** at the dispatch path.

## Authority: a structured GitHub issue comment

The authoritative work claim is an **append-only, structured GitHub issue
comment** on the target work item. The fork was adjudicated against labels and
assignees:

- **Comment (chosen).** Carries holder / host / timestamp / stale-policy /
  release / takeover / idempotency in one machine-readable record; append-only,
  so release and takeover history stay auditable; no dependency on Project field
  ids; does not collide with human assignment/review semantics.
- **Label (rejected as authority).** Cannot encode holder/host/timestamp without
  unbounded label churn; loses release/takeover history. May be added later as a
  *search accelerator* (e.g. `ce-claimed`) — never as authority.
- **Assignee (rejected as authority).** Already used by `forge/backlog.py` as an
  *advisory* projection; means ownership/review in normal GitHub workflows.

### Marker format

A claim comment carries the sentinel `<!-- ce-work-claim:v1 -->` followed by a
JSON record. Three actions: `acquire`, `release`, `takeover` (required-field sets
in `work_claims._REQUIRED_FIELDS`). The canonical **work key** is
`<owner>/<repo>:issue:<number>`.

The legacy interim human lock — a comment whose first non-whitespace line begins
with `🔒 in-compose` — is recognized exactly and treated as a **foreign active
claim** until an explicit structured release/takeover appears, or a recognized
`📦` deliverable-release comment posted *after* it supersedes it.

## Honest posture — NOT a hard lock

GitHub issue comments have **no server-side compare-and-swap** and a ~1–3s API
consistency window. Two hosts can both post-acquire and both read themselves as
winner inside that window. This is the same advisory posture already documented
for `forge/backlog.py` (`NOT a hard lock`). The MVP therefore implements an
**atomic dispatch posture**, not a database mutex:

1. Read all issue comments for the work key.
2. If a foreign **active non-stale** claim exists → refuse before posting anything.
3. If a **stale** foreign claim exists → refuse unless `--takeover`.
4. Post the structured acquire/takeover with a unique `claim_id` + `idempotency_key`.
5. Re-read after a short bounded backoff.
6. Recompute the active holder with the deterministic state machine.
7. Proceed only if the just-posted claim is the active holder.
8. If it lost, post a structured void-release for it, then fail closed.

**Deterministic winner:** earliest live `claimed_at`, tie-broken by GitHub comment
id, then `claim_id`. **Staleness** (`stale_after_seconds`, default 4h) is a status
+ takeover-eligibility threshold — it **never** auto-releases a claim.

### Residual risk (deliberately accepted)

The deterministic tie-breaker guarantees *eventual* correctness but **not**
in-window exclusion: a false-proceed is possible inside the consistency window.
This is accepted for the zero-new-infrastructure trade, consistent with
`forge/backlog.py`'s own advisory-lock posture. Mitigations: Cockpit surfacing,
the stale fence, and the standing ops rule.

## Code shape

- **`work_claims.py`** — the shared, version-neutral runtime: ticket parser,
  marker parser, the pure deterministic state machine (`compute_state`), and the
  `acquire` / `release` / `status` operations over an injectable `GhRunner`. It
  imports **no v1, no v3, and not `forge.*`** — it mirrors the
  `forge/github_repo_config.py` `GhRunner` / `gh api` seam with its own private
  copy so the version boundary stays intact (it is `shared` by classification).
- **`ce claim acquire|release|status <ticket>`** (in `ce_cli.py`) — the
  user-facing MVP. Exit `0` success, `1` refused (foreign/invalid/drift), `2` bad
  local input / ambiguous ticket / unavailable `gh`.
- **Dispatch enforcement.** `ce drive --spawn` and `ce review --spawn` take a
  required `--ticket`; the claim is acquired + verified **before** any dispatch
  side effect (`materialize_dispatch` / `materialize_review_dispatch` / pane /
  tmux). v1 `ce launch` / `ce lane launch` take an optional `--claim-ticket` for
  work-bound manual use. On a refusal after a claim was acquired but before a
  seat spawned, a best-effort structured release (`spawn-refused-before-side-effect`)
  is posted.

## Cockpit feed (read-model, L2-pure)

`ce claim status --write-cache <state-root>` writes an atomic, **view-only** cache
under `<state-root>/claims/claims.json`. The Cockpit read-model
(`runner/cockpit_readmodel.py`) loads it through the narrow `load_claims()` seam
and folds it in `fold_snapshot()` → `snapshot["claims"]` (`entries`,
`active_count`, `stale_count`, `foreign_count`, `invalid_count`, `availability`,
`cache_fetched_at`). The fold stays **pure** (no disk/process/network/clock/rng);
`v3_cockpit.py` renders the precomputed band only.

**The cache is display data only.** Dispatch enforcement **never** reads it — it
always reads the live forge issue comments. An unreachable cache degrades
honestly to `unavailable`, never guessed data.

## Manual-dispatch gap

A human can still launch a seat with no ticket context. The MVP mitigates (not
eliminates) this: `--ticket` is required for v3 `--spawn`; `--claim-ticket` covers
work-bound v1 manual use; Cockpit renders all live claims; the standing rule
remains defense-in-depth.

## Rollback

Append-only at the forge layer: revert the PR, post structured `release`
comments (`release_reason: rollback`) for any live claims, delete local
`<state-root>/claims/` caches (no governance data lost — the issue comments are
authoritative), and rebuild the wheelhouse if wheel-shipped modules changed.
