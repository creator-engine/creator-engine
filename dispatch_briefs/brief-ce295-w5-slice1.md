# WORK CLAIM — ce-ops#295 W5 Slice 1 · G5 body-line auto-emit (ce-ops#340)

**Seat:** dev-4 (DGX contained). **Role:** implementer. This is a BOUNDED slice — build only what is described here.

## Branch
```
git fetch origin && git checkout -b ce-295-w5-g5-body-emit origin/main
```

## Lane / Ticket
- **Parent lane:** W5 (#295) — annoyance→tool + agent-self-authored AGENTS.md
- **This slice:** ce-ops#340 — G5 PR-body work-class line auto-emit
- **Explicitly OUT OF SCOPE in this slice:** ce-ops#341 (strangeLoop run_mode — file as follow-up only), ce-ops#342 (empty-commit CI retrigger — separate slice), AGENTS.md self-authoring (separate slice after this lands).

## Why (self-contained — you cannot read ce-ops)

Every seat-pushed PR (via the egress broker) currently fails the G5 gate in CI
because the broker's PR body does not carry the required work-class declaration
line. The G5 gate (`validate.yml` step "Creator Engine validator — work-sizing
floor PR-diff gate") requires the PR body to contain exactly one line matching:

```
- **Declared work class:** <tiny|story|feature|epic>
```

The regex (from validate.yml + pr_preflight.py:28-32) is:

```python
re.compile(
    r"^\s*(?:[-*]\s*)?(?:\*\*)?Declared work class(?:\*\*)?\s*:\s*(?:\*\*)?\s*"
    r"`?([A-Za-z][A-Za-z0-9_-]*)`?\s*(?:<!--.*-->)?\s*$",
    re.IGNORECASE | re.MULTILINE,
)
```

The broker's current `render_pr_body` (tools/egress-broker/egress_broker/orchestrator.py:125-139)
emits only attribution text. It has NO `declared_work_class` parameter. This
means every broker-pushed PR requires a manual PR body edit after push — a
papercut that fires multiple times per day.

The fix: add `--declared-work-class` to the broker CLI, thread it through the
`courier()` call chain, and emit the required line in `render_pr_body`. The
value should also be auto-discoverable from the per-PR carrier file at
`.ce/pr-manifests/<branch-slug>.md` when not supplied on the CLI.

**Background on the carrier/manifest convention:**
Each PR must carry a file `.ce/pr-manifests/<branch-slug>.md` that contains
the `- **Declared work class:** <tier>` line. The broker can read this file
from the repo to auto-discover the value (use `branch_slug(branch)` from
`creator_engine_validator.checks.path_manifest_fidelity`). If the carrier file
exists and contains exactly one such line → use it. If not found or ambiguous
→ require the `--declared-work-class` CLI arg. Fail-closed if neither resolves.

## Task (bounded)

### 1. `tools/egress-broker/egress_broker/orchestrator.py`

In `render_pr_body`:
- Add parameter `declared_work_class: str` (required).
- Append `\n- **Declared work class:** {declared_work_class}\n` to the returned body, BEFORE the `- head branch:` line (so the gate-required line appears in the body).

In `open_or_update_pr`:
- Accept `declared_work_class: str` and pass it to `render_pr_body`.

In `courier()`:
- Accept `declared_work_class: str | None = None`.
- If `None`, auto-discover from `.ce/pr-manifests/<branch-slug>.md` in the repo (import `creator_engine_validator.checks.path_manifest_fidelity.branch_slug`; read the file; extract exactly one `Declared work class:` line using the same regex as `pr_preflight.DECLARED_WORK_CLASS_PATTERN`). Fail-closed if not resolvable.
- Pass `declared_work_class` to `open_or_update_pr`.

### 2. `tools/egress-broker/ce_egress_broker.py`

Add `--declared-work-class` optional argument (choices: tiny/story/feature/epic, default: None).
Pass it as `declared_work_class=args.declared_work_class` into `run_courier(...)`.

### 3. `tools/egress-broker/ce_egress_self_push_broker.py`

Same: add `--declared-work-class` optional arg; thread it through if this broker also
opens/updates PRs. Read the file first to check if it calls `courier()` or
`open_or_update_pr()` directly — add the arg only where PRs are opened.

### 4. Tests

Add / extend tests in the existing egress-broker test suite (look for
`tests/` under `tools/egress-broker/` or in `validators/tests/`):

- `test_render_pr_body_carries_declared_work_class`: render a body with
  `declared_work_class="story"` and assert the output contains exactly one
  line matching `DECLARED_WORK_CLASS_PATTERN` (import the pattern from
  `creator_engine_validator.pr_preflight`).
- `test_courier_auto_discovers_work_class_from_carrier`: given a fake repo
  path with a carrier at `.ce/pr-manifests/<slug>.md` containing
  `- **Declared work class:** feature`, the courier resolves it without a
  CLI arg.
- `test_courier_fails_closed_no_work_class`: no CLI arg + no carrier file →
  courier refuses with a clear message (does NOT open a PR with a broken body).

### 5. `.ce/pr-manifests/ce-295-w5-g5-body-emit.md` (NEW carrier — REQUIRED)

Create this file (see carrier format below). It is REQUIRED by the G-ii
path-manifest gate and the `ce validate-pr` preflight. Without it the preflight
will fail "no carrier found".

### 6. `.ce/changelog/ce-295-w5-g5-body-emit.md` (NEW fragment — REQUIRED)

Create this file. Required by the path-manifest gate (the carrier must list it,
and the G-ii gate checks for a matching changelog fragment).

## Carrier file format (copy-edit for your branch)

`.ce/pr-manifests/ce-295-w5-g5-body-emit.md`:
```
# PR path manifest - ce-295-w5-g5-body-emit

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, ce-ops#21 convention).

- **Declared work class:** story
- **story:** ce-ops#295 W5 slice 1 — G5 body-line auto-emit (ce-ops#340)

Scope:
Add `--declared-work-class` to the egress broker CLI and thread it into
`render_pr_body` so broker-pushed PRs carry the required G5 work-class line.
Auto-discover from the carrier file when CLI arg is omitted; fail-closed if
neither resolves.

Per-file purpose:
- **`.ce/changelog/ce-295-w5-g5-body-emit.md`** *(A)* - changelog fragment.
- **`.ce/pr-manifests/ce-295-w5-g5-body-emit.md`** *(A)* - this closed path-set carrier.
- **`tools/egress-broker/egress_broker/orchestrator.py`** *(M)* - render_pr_body + open_or_update_pr + courier: accept + emit declared_work_class.
- **`tools/egress-broker/ce_egress_broker.py`** *(M)* - add --declared-work-class CLI arg.
- **`tools/egress-broker/ce_egress_self_push_broker.py`** *(M)* - same if it opens PRs.
- **`<test files>`** *(A/M)* - tests for auto-discover + fail-closed + body emission.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=<fill after finalizing>
AUTHORIZED_PATHS_SHA256=<fill after finalizing>

​```text
.ce/changelog/ce-295-w5-g5-body-emit.md
.ce/pr-manifests/ce-295-w5-g5-body-emit.md
tools/egress-broker/ce_egress_broker.py
tools/egress-broker/ce_egress_self_push_broker.py
tools/egress-broker/egress_broker/orchestrator.py
<test file path — add as you determine it>
​```
```

NOTE: When you finalize which test file(s) you add/modify, update this carrier to
list them, recompute `AUTHORIZED_PATHS_COUNT` and `AUTHORIZED_PATHS_SHA256`. The
authoritative way to (re)generate carriers is the Python API
`carrier_gen.write_carriers(base=<merge-base-sha>)` — do NOT hand-edit the
hash/count; regenerate. If you compute manually for a sanity check:
```
python - <<'EOF'
import hashlib
paths = sorted([
    ".ce/changelog/ce-295-w5-g5-body-emit.md",
    ".ce/pr-manifests/ce-295-w5-g5-body-emit.md",
    "tools/egress-broker/ce_egress_broker.py",
    "tools/egress-broker/ce_egress_self_push_broker.py",
    "tools/egress-broker/egress_broker/orchestrator.py",
    # add test file path here
])
content = "\n".join(paths) + "\n"
print(f"COUNT={len(paths)}")
print(f"SHA256={hashlib.sha256(content.encode()).hexdigest()}")
EOF
```

## Allowed paths (NOTHING else)

- `tools/egress-broker/egress_broker/orchestrator.py`
- `tools/egress-broker/ce_egress_broker.py`
- `tools/egress-broker/ce_egress_self_push_broker.py`  (only if it calls `open_or_update_pr`)
- Test file(s) under `tools/egress-broker/tests/` or `validators/tests/` (existing test module for the orchestrator, if any; or a new test module)
- `.ce/changelog/ce-295-w5-g5-body-emit.md`
- `.ce/pr-manifests/ce-295-w5-g5-body-emit.md`

**EXCLUDED — do NOT touch:**
- `validators/creator_engine_validator/pr_preflight.py` — read it for the regex; do not edit it
- `.github/pull_request_template.md`
- `.github/workflows/validate.yml`
- `ce_cli.py`, `v3_cli.py`
- `validators/creator_engine_validator/forge/approval_capability.py`
- `schemas/**`
- `tools/egress-broker/ce_egress_self_review_broker.py` (review broker, not PR broker — leave alone)
- Any other path not listed above

## Concrete Acceptance Criteria / DoD

1. `ce validate-pr` runs GREEN (full suite, no failures including G5 gate and G-ii path-manifest gate).
2. `render_pr_body(seat_id="dev-4", branch="ce-295-w5-g5-body-emit", head_sha="abc123", declared_work_class="story")` produces a body containing exactly one line matching `DECLARED_WORK_CLASS_PATTERN` from `pr_preflight.py`.
3. The carrier `.ce/pr-manifests/ce-295-w5-g5-body-emit.md` lists all and only the changed files; `AUTHORIZED_PATHS_COUNT` and `AUTHORIZED_PATHS_SHA256` are correct (regenerated via carrier_gen API).
4. Tests pass: auto-discover, fail-closed, body-emission.
5. PR body contains exactly ONE line: `- **Declared work class:** story` (this is a `code`-class mutation touching the broker; story size is appropriate for ~3-4 files + tests).

## STOP LINE

Stop and report to the controller (do NOT proceed/expand scope) if: you need a file
not in the allowed list; `ce validate-pr` is RED on a gate your change introduces and
the fix would touch an excluded path; or the broker's PR-open path turns out to be
materially different from what this brief describes.

## HARD RULES

1. **Run `ce validate-pr` GREEN before any push.** Use `ce validate-pr`, NOT raw `pytest` — the host `/tmp/.git` false-fail trap means raw pytest can pass while `ce validate-pr` fails (it runs in a hermetic tempdir worktree, TMPDIR=/var/tmp). Command:
   ```
   ce validate-pr --base origin/main --head-ref ce-295-w5-g5-body-emit
   ```
   (or `python -m creator_engine_validator.ce_cli validate-pr --repo-root . --base origin/main --head-ref ce-295-w5-g5-body-emit`)

2. **PR body MUST carry exactly:** `- **Declared work class:** story`
   (A `**Work class:**` header or a `[PASS]` log line does NOT match the gate regex.)

3. **Do NOT push until `ce validate-pr` is GREEN.** If it is RED on a gate your change introduces → STOP and report the failing gate to the controller.

4. **Do NOT approve, merge, or enqueue your own PR.** Do NOT run `gh pr merge`, do NOT enable GitHub auto-merge. The controller holds the merge gate.

5. **Do NOT touch files outside the allowed path list above.** Fail-closed.

6. **Report `READY-FOR-HARVEST` when done.** If self-push succeeds (push + open PR ref ce-ops#295 + ce-ops#340), report the PR number. If self-push fails (contained-seat push gap), report exactly:
   ```
   READY-FOR-HARVEST: branch ce-295-w5-g5-body-emit, <N> commits, preflight GREEN
   ```

## Expected Evidence to Report Back

- Output of `ce validate-pr` (full, or last 50 lines showing all PASS).
- `git log --oneline origin/main..HEAD` (commit list).
- `git diff --stat origin/main..HEAD` (changed files + counts).
- Confirmation that `render_pr_body(..., declared_work_class="story")` output passes `DECLARED_WORK_CLASS_PATTERN`.
- PR number (if self-push succeeded) OR `READY-FOR-HARVEST` line (if not).
- Whether `ce_egress_self_push_broker.py` also needed the change (yes/no + reasoning).
