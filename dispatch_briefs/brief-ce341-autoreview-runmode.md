# WORK CLAIM — ce-ops#341: AutoReview never-APPROVE guard: parameterize by run_mode

**Seat:** dev-3 (contained, `ce-vps-codex`, no network egress). **Role:** implementer.
**Born implementer** — stay strictly within the allowed paths below; do NOT inline new features or broaden scope.

## Branch
Branch from your local main (origin may be stale in your container; do not fetch):

```
git checkout -b ce-341-autoreview-runmode main
```

The controller will rebase at harvest time if origin/main has advanced. Do NOT attempt
`git fetch` or `git pull` (no egress).

## Ticket + embedded context (self-contained — do NOT read ce-ops)

### Problem statement

The AutoReview self-trigger (implemented in ce-ops#292 / PR #592, with the never-APPROVE
mechanical enforcement added in PR #596) hard-refuses to emit `APPROVE`. This is correct
for the current `dev` run-mode: author and approver must be distinct (no self-approval).
The guard is currently a **hardcoded constant** in the egress broker:

**File:** `tools/egress-broker/ce_egress_self_review_broker.py`

- Line 59: `ALLOWED_EVENTS = frozenset({"COMMENT", "REQUEST_CHANGES"})`
  This is the never-APPROVE constant. `APPROVE` is absent from `ALLOWED_EVENTS`.
- Lines 170-173 in `parse_request()`: explicit check `if event == "APPROVE": raise SelfReviewRefused(...)`
- Lines 225-226 in `submit_self_review()`: defense-in-depth re-check `if request.event == "APPROVE" or request.event not in ALLOWED_EVENTS: raise SelfReviewRefused(...)`

ce-ops#341 requires the guard to be **parameterized by the active governance run_mode**
so that a future fully-autonomous `strangeLoop` run-mode can deliberately decide the
never-APPROVE property per-mode, rather than having it frozen in a constant.

### Run mode infrastructure (already in the codebase — no new enum needed)

`validators/creator_engine_validator/grading_policy.py` already defines:

```python
class RunMode(str, Enum):
    DEV = "dev"
    STRANGE_LOOP = "strangeLoop"
```

Use this enum; do NOT define a new one or import a different run_mode source.

### Design requirements

1. **Fail-closed default.** When `run_mode` is not supplied (e.g., `None`), treat it as
   `RunMode.DEV` and keep `APPROVE` forbidden. Never-APPROVE stays ON unless explicitly
   opted out of by an explicit `strangeLoop` run_mode argument.

2. **`parse_request()` signature change.** Add an optional `run_mode: str | None = None`
   parameter. When `run_mode == RunMode.STRANGE_LOOP.value` (i.e. the string `"strangeLoop"`),
   allow `APPROVE` to pass through `parse_request()` without raising. All other modes
   (including `None` / `"dev"`) keep the refusal.

3. **`submit_self_review()` signature change.** Add the same `run_mode: str | None = None`
   parameter and propagate it into the event guard on lines 225-226.

4. **Do NOT expose `run_mode` on `SelfReviewRequest`.** The value-only request struct comes
   from the contained seat (untrusted). The `run_mode` is a host-side policy parameter
   injected by the operator/controller when spinning the broker; it must NOT be readable
   from the request payload. Pass it as an explicit keyword arg at the call site only.

5. **`ALLOWED_EVENTS` constant stays.** Keep it as the base allowed set for
   non-strangeLoop modes. Optionally add a `STRANGELOOP_ALLOWED_EVENTS` that adds
   `"APPROVE"`, or compute allowed events per-mode inline in the guard functions.

6. **The socket-server `serve()` / `_ReviewHandler` path.** The `serve()` function
   currently calls `submit_self_review(request, config=config, ...)`. If you expose
   `run_mode` there, it must come from config or a new optional `serve()` parameter.
   Scope this minimally: the unit tests do NOT require end-to-end socket exercising of
   `run_mode`; passing `run_mode` into the call-site in `_ReviewHandler.handle()` via
   the server's `submitter` closure is fine. Do NOT wire run_mode into the broker config
   JSON schema — that is out of scope.

### Tests required

Extend `validators/tests/unit/test_egress_self_review_broker.py` with:

1. `test_approve_refused_in_dev_mode` — `parse_request` with `run_mode="dev"` still refuses APPROVE.
2. `test_approve_refused_when_run_mode_none` — `parse_request` with `run_mode=None` still refuses APPROVE (default fail-closed).
3. `test_approve_allowed_in_strangeloop_mode` — `parse_request` with `run_mode="strangeLoop"` allows APPROVE to pass (no exception).
4. `test_submit_self_review_approve_refused_in_dev_mode` — `submit_self_review` with `run_mode="dev"` and `request.event="APPROVE"` raises `SelfReviewRefused`; no resolve/mint/spawn called.
5. `test_submit_self_review_approve_allowed_in_strangeloop_mode` — `submit_self_review` with `run_mode="strangeLoop"` and `request.event="APPROVE"` does NOT raise before the resolve/mint/spawn stage (use the existing injectable fakes to stub further execution).

For test 5: you will need a `SelfReviewRequest` with `event="APPROVE"`. Because `parse_request()` will now allow it for `strangeLoop`, you can construct the request directly (bypassing `parse_request`) OR call `parse_request(payload, run_mode="strangeLoop")`. Either approach is fine; prefer whichever is less brittle.

The existing test `test_approve_is_refused_before_resolve_mint_or_transport` (which uses no
`run_mode` arg) MUST continue to pass unchanged — it exercises the default fail-closed
behavior.

### Imports in the broker

At the top of `ce_egress_self_review_broker.py`, the broker already adds `validators/` to
`sys.path` conditionally. Import `RunMode` from there:

```python
# near the top, after the existing sys.path manipulation:
try:
    from creator_engine_validator.grading_policy import RunMode as _RunMode
except ImportError:
    _RunMode = None  # type: ignore[assignment,misc]

def _is_strangeloop(run_mode: str | None) -> bool:
    """Return True only when run_mode is explicitly the strangeLoop value."""
    if run_mode is None:
        return False
    if _RunMode is not None:
        return run_mode == _RunMode.STRANGE_LOOP.value
    return run_mode == "strangeLoop"
```

This keeps the import safe if the validators package is absent at runtime; the guard always
fails closed when `_RunMode` is not available because `None` is never `"strangeLoop"`.

## Allowed paths (closed list — touch NOTHING else)

```
tools/egress-broker/ce_egress_self_review_broker.py
validators/tests/unit/test_egress_self_review_broker.py
.ce/changelog/ce341-autoreview-runmode.md
.ce/pr-manifests/ce341-autoreview-runmode.md
```

If your change requires touching any file outside this list, STOP and report it to the
controller before proceeding. Do NOT modify any `.github/workflows/` file, any other
validator source, any `docs/` file, any `scripts/` file, or any `ce_cli.py`.

## Required work (checklist)

- [ ] Parameterize `parse_request()` with `run_mode: str | None = None`.
- [ ] Parameterize `submit_self_review()` with `run_mode: str | None = None`.
- [ ] The `_is_strangeloop()` helper (or equivalent inline guard) correctly maps
      `None` / `"dev"` to APPROVE-refused and `"strangeLoop"` to APPROVE-allowed.
- [ ] `ALLOWED_EVENTS` constant unchanged.
- [ ] Existing tests all still pass (especially `test_approve_is_refused_before_resolve_mint_or_transport`).
- [ ] Five new tests listed above, all passing.
- [ ] `.ce/changelog/ce341-autoreview-runmode.md` front matter:
      `slug: ce341-autoreview-runmode`, `date: 2026-06-28`, `kind: tiny`,
      `issue: ce-ops#341`. Body must include exactly one line:
      `- **Declared work class:** tiny`
- [ ] `.ce/pr-manifests/ce341-autoreview-runmode.md` — generated via
      `carrier_gen.write_carriers(base=<merge-base>)` API (do NOT hand-edit paths;
      if `carrier_gen` is unavailable in the container, hand-list the exact 4 paths
      from the closed list above with their diff status A/M). The carrier must list
      all 4 paths in the closed list and no others.

## Expected evidence (DoD)

Run the FULL preflight in ONE pass (not `-m "not slow"` fast-lane):

```
PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli validate-pr \
    --base origin/main --declared-work-class tiny
```

Must exit green. If the container's `origin/main` is stale, run against your local `main`
branch tip (the branch you checked out from) instead:

```
PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli validate-pr \
    --base main --declared-work-class tiny
```

The G5 declared work class line in the PR body (and in the changelog) must be:
`- **Declared work class:** tiny`

This change touches exactly 2 source files (1 broker module + 1 test file) plus 2 carrier
files = 4 paths total. This is unambiguously `tiny` (no new `ce` CLI group, no schema, no
workflow plumbing, no spec signing, no egress policy changes).

There is NO new `ce` top-level CLI group in this change, so the 3-file docs-coupling
test (`test_v1_docs_reconciliation`) does NOT apply.

This change does NOT touch:
- `.github/workflows/validate.yml`
- `docs/design/controller-bootstrap-ssot.json`
- `scripts/gen-controller-bootstrap.py`

## Stop-line

- Preflight GREEN, no self-push capability → STOP and report:
  `READY-FOR-HARVEST: branch ce-341-autoreview-runmode, <N> commits, preflight GREEN, SHA <commit-sha>`
  The controller harvests. Do NOT attempt to push.
- Preflight RED → STOP immediately and report the failing gate name and test. Do NOT
  thrash or try to patch unrelated failures.
- Any file outside the closed list is required → STOP and report the needed path to the
  controller.
- Do NOT self-approve, merge, or enqueue. The controller holds the gate.
