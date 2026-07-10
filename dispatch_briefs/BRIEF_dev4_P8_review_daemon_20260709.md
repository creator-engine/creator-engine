# BRIEF — dev-4 — 2026-07-09 — P8: Review-Pickup Daemon Slice 1 — DRY-RUN/advisory (STRANGELOOP-1 pool)

Role: **implementer** (story unit — new dry-run module + operator-held gate + WOULD_ASSIGN
JSONL feed + tests + design doc; no live GitHub writes). Contained COMMIT-ONLY seat.
Fresh worktree `/var/tmp/wt-p8-review` off `origin/main` (fetch first).
Branch `ce-p8-review-daemon-s1`.
Signal: `READY ce-p8-review-daemon-s1 <sha> .ce/pr-manifests/ce-p8-review-daemon-s1.md`
or `BLOCKED ce-p8-review-daemon-s1 <reason>`.
Declared work class: **story**.
NO `.ce/brain/assertions.yaml` edits. Standing preflight directive: FULL `ce validate-pr` before READY.

---

## Authorizing decision

Decision 17 (STRANGELOOP-1 pool P8); ratified 2026-07-09.
Evidence: tonight's arc (2026-07-08 → 09) required six manual reviewer-assignment
interventions — the human controller polled open PRs, identified the reviewer gap,
and dispatched the appropriate seat by hand each time. The existing
`ce-review-pickup-daemon.service` runs `cev3 review-pickup --apply` and is capable
of closing this gap autonomously, but the controller has no advisory/dry-run feed
to inspect before enabling live writes. Slice 1 produces the read-only observation
layer: a JSONL feed of `WOULD_ASSIGN` decisions, with the Operator-held gate, so
the controller can validate routing logic before promoting to `--apply`.

---

## Grounding — what already ships (read this before writing any code)

### `deploy/systemd/ce-review-pickup-daemon.service` — EXISTS

The unit file at `deploy/systemd/ce-review-pickup-daemon.service` is present on
`origin/main` and already registered in `deploy/systemd/install-gate-daemons-systemd.sh`
(line 104). Its `ExecStart` is:

```
/usr/bin/env cev3 review-pickup \
  --identity ce-dev-2 \
  --repo "$CE_GATE_REPO" \
  --seat ce-dev-1,ce-dev-3,ce-dev-4 \
  --loop --interval 120 --apply \
  --inbox-path .ce/state/controller-inbox/awaiting-review.json \
  --json
```

`WorkingDirectory=/workspace/creator-engine`,
`EnvironmentFile=%h/.config/creator-engine/gate-daemons.env`.

Conclusion: **the service already points somewhere** (`cev3 review-pickup` via
`v3_cli.py`). Do NOT create `deploy/review-daemon/`. All new code lives under
`validators/creator_engine_validator/forge/` (module) and
`validators/tests/unit/` (tests). The design doc goes at
`validators/creator_engine_validator/forge/review_dry_run_DESIGN.md`.

### `validators/creator_engine_validator/forge/review_pickup.py` — EXISTS, 967 lines

The main controller review-pickup module (ce-ops#188, ce-ops#411). Key surface:

- `poll_review_pickup(*, token, reviewer_seats, gh_runner, transport=None, repo=None,
  org=None, per_page=..., apply=False, dry_run=False, log_sink=None, ...)
  -> ReviewPickupResult` — one Search API pass. When `dry_run=True`, skips all
  mutations; items in result carry `dry_run=True`.
- `run_review_pickup_loop(...)` — wraps `poll_review_pickup` in a daemon loop
  (`iterations=None` for unbounded).
- `ReviewPickupResult(items, awaiting_decisions, skipped, rate_limit, incomplete)`.
- `ReviewPickupSkip` — raised per-PR with a typed `reason` string.
- `JsonLineLogger(stream)` — writes JSONL to a stream (stderr in the service).
- `DEFAULT_CONTROLLER_REVIEWER = "ce-dev-2"`.

**Already handles**: draft skip (`draft is True` → `ReviewPickupSkip("draft_pull_request")`),
draft-unknown fail-closed, CI-failed skip, author≠reviewer (non-author seat selection
via `_choose_reviewer`), unscoped-query fail-closed. The `dry_run` flag propagates
through all item-building helpers.

**Does NOT have**: Operator-held label/held-list-file skip; `WOULD_ASSIGN` JSONL
file writer (current logging goes to a stream only, no named output file).

Do NOT modify `review_pickup.py`. Import from it.

### `validators/creator_engine_validator/pickup_search.py` — EXISTS

Boundary-neutral Search API primitives shared by v1 (`pickup.py`) and v3
(`forge/review_pickup.py`). Has `PickupError`, `PickupRateLimited`, `GhRunner`,
`Transport`, `resolve_token`, `_search_once`, `build_scoped_search_query`. Import
`PickupError` / `PickupRateLimited` from here.

### `validators/creator_engine_validator/pickup.py` — EXISTS (v1 per-seat belt)

The per-seat conveyor belt (S1 poll / S2 claim / S3 lane launch). NOT the
controller review leg. Do not modify.

### `validators/creator_engine_validator/reviewer_triage.py` — EXISTS

Plan-only offline triage; consumes explicit PR facts and policy data; never polls.
Provides `plan_reviewer_triage(...)`. Independent of the review-pickup poller.
Do not modify.

### `validators/tests/unit/test_review_pickup.py` — EXISTS

Offline unit tests for `forge.review_pickup`. Do not modify. Your new test file
must not conflict.

### `deploy/review-daemon/` — DOES NOT EXIST

Do not create it.

### In-flight branch check

Remote branches as of this dispatch: no `ce-p8-review-daemon-s1`. The only
STRANGELOOP branch visible on remote is `bundle/ce-p3-rehearsal-s1` (rehearsal
harness). Territories to avoid touching: `deploy/queue-daemon/`,
`deploy/singleton-redeploy/`, `deploy/seat-watch/` (in-flight for P5),
`deploy/rehearsal-harness/` (in-flight for P3), `.github/scripts/ceops_autoclose.py`
(in-flight for P2), `.ce/brain/assertions.yaml` (always forbidden).

---

## U1 — Review-pickup dry-run daemon, slice 1

### New module: `validators/creator_engine_validator/forge/review_dry_run.py`

A **stdlib-only** module (no third-party imports beyond what `review_pickup.py`
already uses). Imports from `forge.review_pickup` and `pickup_search` only.

#### 1. `is_operator_held(repo, pr_number, gh_runner, *, held_label="awaiting-operator", held_list_path=None) -> bool`

Returns `True` if the PR should be skipped by the Operator-held gate.

Two independent checks (either is sufficient to hold):

**Label check** — call `gh api repos/{repo}/issues/{pr_number}/labels` via
`gh_runner`. Parse the JSON list; if any label object has `"name"` equal to
`held_label` (exact string match, case-sensitive), return `True`. If the API call
fails (non-zero exit or non-JSON response), treat as NOT held (fail-open on label
read, fail-closed on actual assignment is the caller's concern). Log a warning to
`log_sink` when the label read fails.

**Held-list file check** — if `held_list_path` is provided and the file exists,
read it as UTF-8 text; each non-empty, non-comment line is either `owner/repo#N`
or bare `N` (integer). A bare integer is matched against `pr_number` regardless of
repo (all-repo held list); a `owner/repo#N` form is matched by both repo slug and
PR number. Return `True` on any match.

#### 2. `WouldAssignDecision` (a `TypedDict` or plain dict contract)

Two event shapes emitted to the JSONL feed:

```python
# WOULD_ASSIGN: PR would receive a reviewer assignment in apply mode
{
    "event": "WOULD_ASSIGN",
    "repo": str,           # "owner/repo"
    "pr": int,             # PR number
    "head_sha": str,       # current head commit SHA
    "assigned_reviewer": str,   # the seat that would be requested
    "reason": str,         # from review_pickup item["reason"] e.g. "awaiting_review"
    "ts": str,             # ISO-8601 UTC e.g. "2026-07-09T04:00:00Z"
}

# WOULD_SKIP: PR present in search results but excluded from routing
{
    "event": "WOULD_SKIP",
    "repo": str,
    "pr": int,
    "head_sha": str | None,   # None when head_sha not yet known (skipped before read)
    "skip_reason": str,   # "operator_held" | "draft" | "ci_failed" | "no_candidate" |
                          # "already_reviewed" | "pickup_refused" | other reason string
    "ts": str,
}
```

#### 3. `append_dry_run_decision(path, decision)` (private helper)

Atomic append of one JSON line to the JSONL feed file. Create parent dirs if
needed. The append is NOT transactional (single-process daemon; POSIX append
semantics are sufficient). Write `json.dumps(decision, sort_keys=True) + "\n"` in
UTF-8.

#### 4. `run_dry_run_pass(*, token, reviewer_seats, gh_runner, transport=None, repo=None, org=None, per_page=DEFAULT_REVIEW_PICKUP_PER_PAGE, held_label="awaiting-operator", held_list_path=None, feed_path=None, log_sink=None, rate_limiter=None, sleep=time.sleep, clock=None) -> tuple[list[dict], list[dict]]`

Returns `(would_assign, would_skip)` lists of decision dicts.

Algorithm:

1. Call `poll_review_pickup(token=token, reviewer_seats=reviewer_seats,
   gh_runner=gh_runner, transport=transport, repo=repo, org=org,
   per_page=per_page, apply=False, dry_run=True, log_sink=log_sink,
   rate_limiter=rate_limiter, sleep=sleep)` — this returns a `ReviewPickupResult`.

2. For each item in `result.items` (these are the PRs that poll determined need a
   reviewer): check `is_operator_held(item["repo"], item["number"], gh_runner,
   held_label=held_label, held_list_path=held_list_path, log_sink=log_sink)`.
   - If held → emit `WOULD_SKIP` with `skip_reason="operator_held"`.
   - Otherwise → emit `WOULD_ASSIGN` from `item["repo"]`, `item["number"]`,
     `item["head_sha"]`, `item.get("assigned_reviewer")`, `item["reason"]`.

3. For each entry in `result.skipped` (these are PRs that `poll_review_pickup`
   already skipped internally for its own reasons — draft, CI fail, etc.): emit
   `WOULD_SKIP` with `skip_reason=entry.get("reason", "pickup_refused")`.
   Include `head_sha=entry.get("head_sha")` (may be `None` for early-skipped entries).

4. Append all decisions to `feed_path` if provided (one JSON line each, in order:
   WOULD_ASSIGN entries first, then WOULD_SKIP entries).

5. Return `(would_assign, would_skip)`.

Timestamp all decisions using `clock() if clock else datetime.now(timezone.utc)`.
Format as `datetime.isoformat() + "Z"` if a `datetime` object.

#### 5. `run_dry_run_loop(*, token, reviewer_seats, gh_runner, transport=None, repo=None, org=None, per_page=DEFAULT_REVIEW_PICKUP_PER_PAGE, held_label="awaiting-operator", held_list_path=None, feed_path=None, log_sink=None, rate_limiter=None, interval=120.0, iterations=None, sleep=time.sleep, clock=None) -> list[tuple[list[dict], list[dict]]]`

Daemon loop; same `iterations` semantics as `run_review_pickup_loop` (None =
unbounded, integer = bounded). Each iteration calls `run_dry_run_pass`, sleeps
`interval` seconds between iterations. Returns list of `(would_assign, would_skip)`
pairs. Catches `PickupRateLimited` and logs via `log_sink` (same pattern as
`review_pickup.py` loop); does not abort.

### New design doc: `validators/creator_engine_validator/forge/review_dry_run_DESIGN.md`

Keep under 40 lines. Cover:

- **Purpose**: observation layer that bridges "PR opened" → "reviewer detected"
  without GitHub writes; allows controller to validate routing logic pre-`--apply`.
- **Architecture**: wraps `forge.review_pickup.poll_review_pickup(dry_run=True)`;
  adds the Operator-held gate and the named JSONL feed.
- **Operator-held gate**: label check (`awaiting-operator` default) + held-list
  file; fail-open on label-read error (label read is advisory; the dry-run itself
  never writes).
- **JSONL feed**: two event types (`WOULD_ASSIGN`, `WOULD_SKIP`); one line per PR
  per pass; append-only; consumer is the controller reading the feed offline.
- **Slice 2 hook** (one sentence): slice 2 will add a `cev3 review-dry-run`
  subcommand that drives `run_dry_run_loop` from the CLI and connects to the
  existing `gate-daemons.env` token path.
- No references to internal ticket numbers; no external dependencies.

### New tests: `validators/tests/unit/test_p8_review_daemon_s1.py`

All tests offline — zero live network or subprocess calls. Use the fake transport
and fake `gh_runner` patterns already established in `test_review_pickup.py`.

Required test cases:

1. **`is_operator_held` — label match** — fake `gh_runner` returning a JSON list
   containing `{"name": "awaiting-operator"}`; assert returns `True`.

2. **`is_operator_held` — label absent** — fake `gh_runner` returning `[]`; assert
   returns `False`.

3. **`is_operator_held` — custom held_label** — fake runner returning
   `[{"name": "on-hold"}]`, called with `held_label="on-hold"`; assert `True`.

4. **`is_operator_held` — held-list file match** — write a tmp file with
   `"owner/repo#42"`, call with `repo="owner/repo"`, `pr_number=42`; assert `True`
   even when label check returns `False` (fake runner returns `[]`).

5. **`is_operator_held` — held-list bare number match** — file contains `"42"`;
   assert `True` for pr_number=42.

6. **`is_operator_held` — held-list miss** — file contains `"99"`, pr_number=42;
   assert `False`.

7. **`is_operator_held` — label API failure (fail-open)** — fake runner returns
   non-zero exit; assert returns `False` (not a raised exception).

8. **`run_dry_run_pass` — WOULD_ASSIGN emitted** — fake `poll_review_pickup` result
   with one item (dry_run=True, assigned_reviewer set); is_operator_held returns
   False; assert one `WOULD_ASSIGN` decision returned with correct fields.

9. **`run_dry_run_pass` — operator-held item becomes WOULD_SKIP** — same as above
   but `is_operator_held` returns True; assert one `WOULD_SKIP` with
   `skip_reason="operator_held"` and zero `WOULD_ASSIGN`.

10. **`run_dry_run_pass` — internally-skipped items become WOULD_SKIP** — fake
    `poll_review_pickup` with empty `items` but non-empty `skipped` list
    (reason="draft_pull_request"); assert one `WOULD_SKIP` with
    `skip_reason="draft_pull_request"`.

11. **`run_dry_run_pass` — JSONL feed written** — provide a tmp `feed_path`; after
    pass, read lines and verify each line parses as valid JSON with the correct
    `"event"` field.

12. **`run_dry_run_pass` — feed appended across passes** — call `run_dry_run_pass`
    twice with one item each time; verify feed file has two lines (append semantics).

13. **`run_dry_run_loop` — bounded iterations** — inject `iterations=2`, no-op sleep,
    fake pass that returns one WOULD_ASSIGN each time; assert loop result has length 2.

14. **`run_dry_run_loop` — rate-limited pass is logged, loop continues** — inject a
    pass that raises `PickupRateLimited` on first call, succeeds on second; assert
    loop completes without raising and log_sink received a rate_limited event.

### What NOT to touch

- Do not modify `forge/review_pickup.py`, `pickup.py`, `pickup_search.py`,
  `reviewer_triage.py`.
- Do not modify `deploy/systemd/ce-review-pickup-daemon.service` or any other
  systemd unit.
- Do not edit `.ce/brain/assertions.yaml`.
- Do not modify any existing test files.
- Do not create `deploy/review-daemon/`.
- Do not touch `deploy/queue-daemon/`, `deploy/singleton-redeploy/`,
  `deploy/seat-watch/` (P5 in-flight), `deploy/rehearsal-harness/` (P3 in-flight),
  `.github/scripts/ceops_autoclose.py` (P2 in-flight).
- No actual GitHub writes (no `POST`, no `PATCH`, no `PUT` via `gh_runner` in
  production paths — label reads via `GET` are permitted).
- No `v3_cli.py` changes in slice 1 (CLI wiring is slice 2).

### Acceptance evidence for THIS slice

The closing PR body must carry:

```
Acceptance-Evidence: validators/tests/unit/test_p8_review_daemon_s1.py
```

This file must exist in the PR and must contain at minimum the fourteen test cases
enumerated above. `pytest validators/tests/unit/test_p8_review_daemon_s1.py -v`
must pass in the worktree before READY is signaled.

---

## Standing obligations (every P8 PR — do not omit)

### Carrier manifest (required)

Produce the carrier manifest at
`.ce/pr-manifests/ce-p8-review-daemon-s1.md` before signaling READY.

Declared paths (exactly these — no omissions, no additions beyond what you actually
touch):

```
validators/creator_engine_validator/forge/review_dry_run.py
validators/creator_engine_validator/forge/review_dry_run_DESIGN.md
validators/tests/unit/test_p8_review_daemon_s1.py
CHANGELOG.md
.ce/pr-manifests/ce-p8-review-daemon-s1.md
```

Declared work class line (exactly one, verbatim):

```
declared_work_class: story
```

### CHANGELOG fragment (required)

Add a new entry under `## Unreleased` in `CHANGELOG.md`:

```markdown
### Added
- Review-pickup dry-run daemon slice 1: `forge.review_dry_run` module adds
  `run_dry_run_pass` / `run_dry_run_loop` (wrapping `forge.review_pickup` with
  `dry_run=True`), the Operator-held gate (label + held-list file), and a named
  WOULD_ASSIGN / WOULD_SKIP JSONL feed. Read-only; no GitHub writes. Slice 2 will
  add the `cev3 review-dry-run` CLI surface.
```

---

## Preflight sequence (mandatory before READY)

```bash
git fetch origin
git checkout -b ce-p8-review-daemon-s1 origin/main
# implement all files listed above
pytest validators/tests/unit/test_p8_review_daemon_s1.py -v
pytest validators/tests/unit/test_review_pickup.py -v  # must stay GREEN
ce validate-pr   # must be fully GREEN
```

Only signal READY after `ce validate-pr` is fully GREEN.
