# BRIEF — dev-3 — 2026-07-09 — BATCH: xdist copytree fix + autoclose slice 2

Role: **implementer**. Contained COMMIT-ONLY seat (ce-vps-codex). No venv activation needed;
use the installed `ce`.

---

## BORN-A-FOREMAN EXECUTION MODEL

You drive two tickets concurrently: **one git worktree + background subagent-thread per
ticket**. Both threads may run simultaneously — the two units are FILE-DISJOINT (see
disjointness analysis below). Report **PER-TICKET**: one READY or BLOCKED signal per unit
before your session ends. A unit that is BLOCKED does not block the other unit from
signaling READY. Never merge unit work across branches or worktrees.

Signal format per unit:

```
READY <branch> <40-char-sha> <carrier-path>
BLOCKED <branch> <one-line reason>
```

---

## PREFLIGHT PRECONDITION — fetch first

Before starting either thread, run:

```bash
git fetch origin
git log origin/main --oneline | head -5
```

Confirm the head commit is `db07e6dc0638a8edfc72ace7fcc73a8d8b7d8060` (Add
Acceptance-Evidence autoclose gate, #916) or a later commit. If a newer commit has landed
since this brief was composed, proceed — use the actual current `origin/main` HEAD as the
base for both branches.

**Do not touch `.ce/brain/assertions.yaml` in either unit.** The brain-ledger tail is
serialized. If any gate in either unit demands a ledger append, write BLOCKED immediately
and stop that thread.

---

## CANDIDATE DROP LOG (controller pre-verification, 2026-07-09)

- **ce-ops#473** (adoption workflow template lacks `merge_group` trigger): DROPPED — already
  landed on `origin/main` via PR #859 (merged 2026-07-07T06:01:40Z). Verified:
  `validators/creator_engine_validator/onboard_apply.py` on `origin/main` contains
  `merge_group:\n  types: [checks_requested]`. No work remaining.

---

## DISJOINTNESS ANALYSIS (read before starting any thread)

**Unit A files** (xdist copytree fix):
- `validators/tests/integration/test_release_finalize_integration.py` (modify)
- `.ce/changelog/ce-515-xdist-copytree-fix.md` (new)
- `.ce/pr-manifests/ce-515-xdist-copytree-fix.md` (new)
- `.ce/wt-515/READY` or `.ce/wt-515/BLOCKED` (signal)

**Unit B files** (autoclose slice 2):
- `.github/scripts/ceops_autoclose.py` (modify)
- `.github/workflows/ce-ops-autoclose.yml` (modify: comment only)
- `validators/tests/unit/test_p2_acceptance_evidence.py` (extend)
- `.ce/changelog/ce-516-autoclose-s2.md` (new)
- `.ce/pr-manifests/ce-516-autoclose-s2.md` (new)
- `.ce/wt-516/READY` or `.ce/wt-516/BLOCKED` (signal)

**Cross-batch Batch B (dev-4) in-flight paths** (BRIEF_dev4_restock_batch_20260709.md):
`validators/creator_engine_validator/forge/integrator_belt.py`,
`validators/tests/unit/test_integrator_belt.py`,
`deploy/daemons/smoke-daemon-container.sh`,
`validators/tests/integration/test_adoption_merge_group_e2e.py`

**Collision verdict:**
- Unit A vs Unit B: **CLEAR** — no shared files.
- Unit A vs dev-4 batch: **CLEAR** — no shared files.
- Unit B vs dev-4 batch: **CLEAR** — no shared files.
- `assertions.yaml` is out-of-bounds for both units.

**Brain ledger gate (pre-authorized):**
`validators/tests/integration/test_release_finalize_integration.py` appears as an
evidence_ref path prefix under `validators/tests` in `.ce/brain/assertions.yaml` (item 39:
full-validator-long-running). The relevant assertion is that the test directory CONTAINS
slow integration tests — adding copytree ignore patterns does not remove any test or
invalidate that assertion. No brain ledger append is required. Gate clear.

`.github/workflows/ce-ops-autoclose.yml` is an explicit evidence_ref (item 16:
cross-repo-closes-bot). The assertion is that the cross-repo autoclose bot mechanism
EXISTS — adding dedup/alerting and refreshing a comment does not remove or contradict the
bot. No brain ledger append required. Gate clear.

---

## STANDING OBLIGATIONS BLOCK — read this before writing any file

Every unit in this brief MUST deliver ALL of the following. Missing any one item is a
harvest blocker.

1. **Changelog fragment**: `.ce/changelog/<branch>.md` — one short paragraph describing
   what changed and why. No ce-ops# references in the text body (product lens).

2. **Carrier / path-manifest**: `.ce/pr-manifests/<branch>.md` — lists every changed path
   (including the changelog fragment itself). Must contain exactly **one** line of the form:
   ```
   - **Declared work class:** <XS|S|M|L>
   ```
   The carrier slug (filename stem) MUST equal the branch name exactly. Zero ce-ops# refs.

3. **Targeted in-seat tests only**: run only the test files touched by your unit (see each
   unit's acceptance criteria). Full suite execution is prohibited in the seat environment
   (resource limits). The controller preflight on `origin/main` is authoritative for the
   full suite.

4. **Signal file**: write `.ce/wt-<ticket>/READY` or `.ce/wt-<ticket>/BLOCKED` as the
   FINAL commit on your branch before stopping.

**Pre-authorized false-RED classes** (proven in this seat environment — if the ONLY
failures are these gates on files you did NOT touch, note them verbatim and signal READY):
- `control-plane portability` gate on paths outside your diff
- `check-examples` gate failures on paths outside your diff
- `libsodium` gate failures on paths outside your diff

Any failure touching YOUR changed files = fix or BLOCKED. Do not suppress or ignore errors
in your own diff.

---

## UNIT A — xdist copytree race fix

**Branch:** `ce-515-xdist-copytree-fix`
**Worktree:** `/var/tmp/wt-515`
**Work class:** XS
**Carrier slug must match branch exactly:** `ce-515-xdist-copytree-fix`

### Ticket body (ce-ops#515 — embedded for offline access)

```
Title: flaky: test_release_finalize_docs_copy_passes_release_guards — xdist copytree
       race on validators/build

State: OPEN | Labels: triage:ready, wc:S

## Symptom

`test_release_finalize_docs_copy_passes_release_guards` fails intermittently when run
under `pytest -n` (xdist parallel workers). The failure class is `FileNotFoundError` /
broken-symlink errors during a `shutil.copytree(REPO_ROOT, ...)` call that does not
exclude build artifact directories.

## Evidence

1. 2026-07-08 — ce-readme-overhaul harvest preflight died on dangling symlinks under
   `validators/build/` during `copytree`. Preflight had to be re-run (cost: 1 full
   round-trip).
2. 2026-07-09 — ce-conveyor-intake-s1 re-harvest preflight went RED on exactly this test
   (`baseline=1 failure, head=2`). Control run (isolation, single worker): passes clean.
   This confirms the failure is a concurrency artifact, not a logic regression.

## Root Cause

The test calls `shutil.copytree(REPO_ROOT, ...)` without a sufficient `ignore=` filter.
Under xdist, concurrent workers mutate `validators/build/` (compiled extensions, `.egg-
info`, `__pycache__`, temp symlinks) DURING the directory enumeration pass of `copytree`,
producing `FileNotFoundError`-class races.

Introduced at commit `745838b21` (release 0.3.4).

## Impact

- Flaky preflight failures block harvests and force full re-runs (~15–30 min round-trip
  each occurrence).
- Cost so far: 2 wasted preflight round-trips on 2026-07-08/09.

## Proposed Fix

Pass `ignore=shutil.ignore_patterns('build', 'dist', '__pycache__', '*.egg-info')` (or
equivalent) to the `copytree` call, or extend the existing `_ignore_copy_noise` helper
to cover `build` and `dist`. Alternatively, use `git ls-files` to enumerate only
tracked files.

## Refs

- Affected path: `validators/tests/integration/test_release_finalize_integration.py`
  (function `_ignore_copy_noise` and `_copy_repo_fixture`)
```

### Problem statement (grounded in code on origin/main)

The failing test lives in
`validators/tests/integration/test_release_finalize_integration.py`. The relevant code
path (confirmed on `origin/main:db07e6dc0`):

```python
def _ignore_copy_noise(_directory: str, names: list[str]) -> set[str]:
    ignored = {
        ".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox",
        ".venv", "__pycache__", "htmlcov", "node_modules",
    }
    return {name for name in names if name in ignored or name.endswith((".pyc", ".pyo"))}

def _copy_repo_fixture(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    shutil.copytree(REPO_ROOT, repo, symlinks=True, ignore=_ignore_copy_noise)
    ...
```

The `_ignore_copy_noise` filter does NOT include `build` or `dist`. Under xdist parallel
runs, `validators/build/` (compiled C extensions, `.egg-info`, dangling symlinks during
editable install) can be mutated while `copytree` is enumerating, producing a
`FileNotFoundError` mid-copy.

### Probe before editing

```bash
git show origin/main:validators/tests/integration/test_release_finalize_integration.py | \
  grep -n 'build\|dist\|egg-info'
# Expect: zero hits in _ignore_copy_noise — confirms the gap is still present.
```

If the probe shows `build` already in the ignore set, note `PROBE_A: already_resolved`
in the READY signal and deliver any remaining gap patterns only.

### Deliverable

Extend `_ignore_copy_noise` in
`validators/tests/integration/test_release_finalize_integration.py` to include build
artifact directories:

```python
def _ignore_copy_noise(_directory: str, names: list[str]) -> set[str]:
    ignored = {
        ".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox",
        ".venv", "__pycache__", "htmlcov", "node_modules",
        "build", "dist",                      # <-- ADD: compiled extension artifacts
    }
    return {
        name for name in names
        if name in ignored
        or name.endswith((".pyc", ".pyo", ".egg-info"))  # <-- ADD: .egg-info pattern
    }
```

No other files need changes. The test itself does not need modification — the copytree
fix eliminates the race.

### Acceptance criteria

1. `grep -n 'build' validators/tests/integration/test_release_finalize_integration.py`
   returns a hit inside `_ignore_copy_noise`.
2. `pytest validators/tests/integration/test_release_finalize_integration.py -v` passes
   cleanly (single-worker, no xdist needed in-seat).
3. `ce validate-pr --profile contained-seat` green on the diff.

### Hard constraints

- Do NOT touch `validators/tests/integration/test_install_bootstrap.py` — the ticket
  incorrectly names that file; the actual file is `test_release_finalize_integration.py`.
- Do NOT touch `.ce/brain/assertions.yaml`.
- Do NOT remove any existing ignore pattern.

### STOP LINE (Unit A)

No pushes, no PRs, no gate acts. Only these paths:

```
validators/tests/integration/test_release_finalize_integration.py
.ce/changelog/ce-515-xdist-copytree-fix.md
.ce/pr-manifests/ce-515-xdist-copytree-fix.md
.ce/wt-515/READY
.ce/wt-515/BLOCKED
```

Carrier: slug `ce-515-xdist-copytree-fix` exactly; every changed path listed; exactly
ONE `- **Declared work class:** XS` line.

### READY / BLOCKED signals (Unit A)

**When DONE — write `.ce/wt-515/READY` then emit:**
```
STATUS: READY
BRANCH: ce-515-xdist-copytree-fix
COMMIT: <HEAD SHA after final commit>
CARRIER: .ce/pr-manifests/ce-515-xdist-copytree-fix.md
PROBE_A: <open|already_resolved>
VALIDATE_PR: GREEN
GATE_NOISE: <"none" or verbatim text of false-RED gates on untouched files>
READY ce-515-xdist-copytree-fix <sha> .ce/pr-manifests/ce-515-xdist-copytree-fix.md
```
Commit the signal file as the FINAL commit on the branch before stopping.

**When BLOCKED — write `.ce/wt-515/BLOCKED` then emit:**
```
STATUS: BLOCKED
BRANCH: ce-515-xdist-copytree-fix
BLOCKER: <one-sentence description>
CONTEXT: <full context, file/line/error>
BLOCKED ce-515-xdist-copytree-fix <reason>
```

---

## UNIT B — autoclose Acceptance-Evidence slice 2

**Branch:** `ce-516-autoclose-s2`
**Worktree:** `/var/tmp/wt-516`
**Work class:** S
**Carrier slug must match branch exactly:** `ce-516-autoclose-s2`

### Ticket body (ce-ops#516 — embedded for offline access)

```
Title: autoclose Acceptance-Evidence slice 2: warn-comment dedup, alerting hook,
       workflow-comment refresh, POST-failure test

State: OPEN | Labels: triage:ready, wc:S

## Context

Slice 1 (creator-engine PR #916, merged 2026-07-09) implemented the ratified evidence-
gated closure rule: directive-labeled issues without an `Acceptance-Evidence:` field get
a warning comment instead of closing; token-absent now exits 1 fail-closed.

Review-accepted slice-2 items follow.

## Items

### (1) IDEMPOTENCY — warn-comment dedup
The warn POST has no dedup guard. Every merged PR that references the same evidence-less
directive issue will re-comment with the identical warning. Before posting, the bot should
check existing comments for its own marker and skip if already present.

### (2) ALERTING — exit-1 invisible under dual continue-on-error
`exit 1` on token-absent is fail-closed but invisible: the workflow runs with
`continue-on-error: true` on both the step and the job, so the job stays green and no
human is alerted. Wire an alert hook — e.g. a `repository-dispatch` to the operator-
alerting consumer, consistent with the seat-watch/alerting lineage — for governance-class
failures so they surface to the operator.

### (3) WORKFLOW COMMENT REFRESH
The workflow YAML's inline comment (lines ~17-18) still describes the old fail-open
behavior. That comment was out of slice-1 scope. Refresh it to accurately describe the
current fail-closed, evidence-gated semantics.

### (4) TEST — API failure during warn POST
The case where the GitHub API call to post the warning comment fails (network error,
4xx/5xx) is untested. The correct behavior is: comment silently omitted, issue correctly
stays open (not closed). Add a unit/integration test covering this path.

## Cross-links

- Slice 1 implementation: creator-engine PR #916.
```

### Problem statement (grounded in code on origin/main)

All four items are open on `origin/main:db07e6dc0`. Verified:

**Item 1 (dedup):** `.github/scripts/ceops_autoclose.py` — `close_issue_if_open()` posts
the warn comment with no prior check for existing comments. Confirmed by grep:
`git show origin/main:.github/scripts/ceops_autoclose.py | grep -n "dedup\|marker\|html.*comment"` → zero hits.

**Item 2 (alerting):** `exit 1` on token-absent (the `main()` function now returns 1),
but there is no `repository-dispatch` or equivalent alert for governance-class failures.

**Item 3 (comment):** `.github/workflows/ce-ops-autoclose.yml` — the inline comment at
lines ~17-18 still says `"Fail-open: if the secret is absent/empty the step logs a
warning and exits 0"`. This is stale since PR #916 made the script fail-closed.

**Item 4 (test):** `validators/tests/unit/test_p2_acceptance_evidence.py` has no test for
API failure during the warn POST. Confirmed: `grep -n "fail\|POST.*fail\|4xx\|5xx\|network" …/test_p2_acceptance_evidence.py` → zero hits.

### Probe before editing each item

```bash
# Item 1:
git show origin/main:.github/scripts/ceops_autoclose.py | \
  grep -n "existing_comments\|already_warned\|dedup\|html.*comment\|bot.*marker"
# Expect: zero hits

# Item 2:
git show origin/main:.github/scripts/ceops_autoclose.py | \
  grep -n "repository.dispatch\|alert\|alerting"
# Expect: zero hits

# Item 3:
git show origin/main:.github/workflows/ce-ops-autoclose.yml | \
  grep -n "Fail-open\|Fail-closed" | head -5
# Expect: "Fail-open:" hit — confirms stale comment

# Item 4:
git show origin/main:validators/tests/unit/test_p2_acceptance_evidence.py | \
  grep -n "def test.*fail\|def test.*error\|def test.*post"
# Expect: zero hits for POST-failure test
```

For any item where the probe shows it was already resolved, note
`PROBE_ITEM<N>: already_resolved` in the READY signal.

### Deliverable — four items in two files

#### Item 1: Dedup guard in `.github/scripts/ceops_autoclose.py`

Before calling `_api_json("POST", ...)` to post the warn comment in
`close_issue_if_open()`, fetch existing comments and check for the bot's own marker.
The dedup marker is the first line of `_acceptance_evidence_required_comment()` output:
`"**Autoclose blocked — Acceptance-Evidence required.**"`. If any existing comment body
starts with that text, skip the POST and log a dedup-skip line instead.

```python
def _has_existing_warn_comment(issue_number: int, token: str) -> bool:
    """Return True if we already posted the Acceptance-Evidence required warning."""
    comments_path = f"/repos/{CE_OPS_REPO}/issues/{issue_number}/comments"
    try:
        comments = _api_json("GET", comments_path, token)
        marker = "**Autoclose blocked — Acceptance-Evidence required.**"
        return any(
            isinstance(c, dict) and c.get("body", "").startswith(marker)
            for c in (comments if isinstance(comments, list) else [])
        )
    except Exception:
        return False  # fail-open on dedup check: better to re-warn than to silently skip

# In close_issue_if_open(), before the POST:
if _is_directive_issue(issue) and not _parse_acceptance_evidence(context.get("body") or ""):
    if not _has_existing_warn_comment(issue_number, token):
        _api_json("POST", f"{issue_path}/comments", token,
                  {"body": _acceptance_evidence_required_comment(context)})
    else:
        print(f"ce-ops#{issue_number}: Acceptance-Evidence warn already posted, skipping dedup")
    print(f"ce-ops#{issue_number}: Acceptance-Evidence required, leaving open")
    return
```

#### Item 2: Alerting hook in `.github/scripts/ceops_autoclose.py`

When the token is absent, after emitting `::error::`, attempt a `repository-dispatch`
to surface the governance failure to the operator-alerting consumer. Use the existing
`_api_json` helper. Add a helper that emits the dispatch but is a no-op (logs a skip) if
`GITHUB_TOKEN` is also absent (the dispatch needs at minimum `GITHUB_TOKEN` or another
token with `repo` scope):

```python
def _alert_governance_failure(reason: str) -> None:
    """Emit a repository-dispatch alert for governance-class failures."""
    alert_token = os.environ.get("GITHUB_TOKEN", "")
    if not alert_token:
        print("governance-alert: no GITHUB_TOKEN available for dispatch, skipping alert")
        return
    try:
        _api_json(
            "POST",
            f"/repos/{CE_OPS_REPO.split('/')[0]}/creator-engine/dispatches",
            alert_token,
            {
                "event_type": "governance-alert",
                "client_payload": {
                    "source": "ceops_autoclose",
                    "reason": reason,
                },
            },
        )
        print(f"governance-alert dispatched: {reason}")
    except Exception as exc:
        print(f"governance-alert dispatch failed (non-blocking): {exc}")
```

Call `_alert_governance_failure("token_absent")` in `main()` immediately after emitting
the `::error::` line.

#### Item 3: Comment refresh in `.github/workflows/ce-ops-autoclose.yml`

Find the inline comment block (around lines 17-18) that contains `"Fail-open:"` and
update it to reflect the current fail-closed semantics introduced by PR #916:

Before:
```yaml
# Fail-open: if the secret is absent/empty the step logs a warning and exits 0,
# so this workflow never blocks a merge.
```

After:
```yaml
# Fail-closed: if the secret is absent/empty the step emits a ::error:: annotation
# and exits nonzero. The step is configured continue-on-error so merges are not
# silently blocked, but a governance alert is dispatched to the operator.
```

This is a COMMENT-ONLY change. No logic change in the YAML.

#### Item 4: POST-failure test in `validators/tests/unit/test_p2_acceptance_evidence.py`

Extend the existing test module. Add:

```python
def test_warn_comment_post_failure_leaves_issue_open(monkeypatch):
    """API failure during the warn comment POST must leave the issue open (not closed)."""
    import importlib.util, json
    from pathlib import Path
    script = Path(__file__).resolve().parents[3] / ".github" / "scripts" / "ceops_autoclose.py"
    spec = importlib.util.spec_from_file_location("ceops_autoclose", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    calls = []

    def fake_api(method, path, token, body=None):
        calls.append((method, path))
        # GET for issue data — return a directive issue without acceptance evidence
        if method == "GET" and path.endswith("/issues/42"):
            return {"state": "open", "labels": [{"name": "directive"}]}
        # GET for existing comments — return empty (no prior warn)
        if method == "GET" and "/comments" in path and body is None:
            return []
        # POST for the warn comment — simulate failure
        if method == "POST" and "/comments" in path:
            raise RuntimeError("simulated API failure: 503 Service Unavailable")
        # POST for close (must NOT be called)
        if method == "POST" and path.endswith("/state"):
            raise AssertionError("close must not be called when warn POST fails")
        return {}

    monkeypatch.setattr(mod, "_api_json", fake_api)
    context = {
        "body": "No Acceptance-Evidence field here.",
        "merge_commit_sha": "abc123",
        "number": "42",
        "repository": "creator-engine/creator-engine",
        "title": "feat: some directive work",
        "url": "https://github.com/creator-engine/creator-engine/pull/42",
    }
    # Should not raise; comment POST failure is silently absorbed.
    mod.close_issue_if_open(42, "fake-token", context)
    # The issue must NOT have been closed.
    assert not any(
        m == "PATCH" and "42" in p for m, p in calls
    ), "close was called despite warn POST failure"
```

Adjust the test structure to match the actual `close_issue_if_open` signature and
`_api_json` mock point in the live module.

### Acceptance criteria

1. `grep -n "existing_comments\|already_warned\|dedup" .github/scripts/ceops_autoclose.py`
   returns at least one hit inside a dedup guard (or `PROBE_ITEM1: already_resolved`).
2. `grep -n "governance.alert\|alert_governance\|repository.dispatch" .github/scripts/ceops_autoclose.py`
   returns a hit (or `PROBE_ITEM2: already_resolved`).
3. `grep -n "Fail-closed" .github/workflows/ce-ops-autoclose.yml` returns a hit at the
   refreshed comment (or `PROBE_ITEM3: already_resolved`).
4. `pytest validators/tests/unit/test_p2_acceptance_evidence.py -v` passes including the
   new POST-failure test.
5. `ce validate-pr --profile contained-seat` green on the diff.

### Hard constraints

- Do NOT touch `.ce/brain/assertions.yaml`.
- Do NOT touch `validators/tests/unit/test_ceops_autoclose.py` — that file is adjacent
  but NOT in scope; this unit extends `test_p2_acceptance_evidence.py` only.
- Do NOT alter the existing `_acceptance_evidence_required_comment()` text (the dedup
  marker depends on its exact first line).
- Do NOT change the fail-closed exit behavior in `main()` — only ADD the alert call
  alongside it.
- ZERO ce-ops# references in changelog or carrier body text.

### STOP LINE (Unit B)

No pushes, no PRs, no gate acts. Only these paths:

```
.github/scripts/ceops_autoclose.py
.github/workflows/ce-ops-autoclose.yml
validators/tests/unit/test_p2_acceptance_evidence.py
.ce/changelog/ce-516-autoclose-s2.md
.ce/pr-manifests/ce-516-autoclose-s2.md
.ce/wt-516/READY
.ce/wt-516/BLOCKED
```

Carrier: slug `ce-516-autoclose-s2` exactly; every changed path listed; exactly ONE
`- **Declared work class:** S` line.

### READY / BLOCKED signals (Unit B)

**When DONE — write `.ce/wt-516/READY` then emit:**
```
STATUS: READY
BRANCH: ce-516-autoclose-s2
COMMIT: <HEAD SHA after final commit>
CARRIER: .ce/pr-manifests/ce-516-autoclose-s2.md
PROBE_ITEM1: <open|already_resolved>
PROBE_ITEM2: <open|already_resolved>
PROBE_ITEM3: <open|already_resolved>
PROBE_ITEM4: <open|already_resolved>
ITEMS_ADDRESSED: <count of items actually changed>
VALIDATE_PR: GREEN
GATE_NOISE: <"none" or verbatim text of false-RED gates on untouched files>
READY ce-516-autoclose-s2 <sha> .ce/pr-manifests/ce-516-autoclose-s2.md
```
Commit the signal file as the FINAL commit on the branch before stopping.

**When BLOCKED — write `.ce/wt-516/BLOCKED` then emit:**
```
STATUS: BLOCKED
BRANCH: ce-516-autoclose-s2
BLOCKER: <one-sentence description>
CONTEXT: <full context, file/line/error>
BLOCKED ce-516-autoclose-s2 <reason>
```
