# BRIEF — dev-3 — 2026-07-08 — BATCH: CEO onboarding rewrite + seat-preflight parity + README-review minors

Role: **implementer**. Contained COMMIT-ONLY seat (ce-vps-codex, x86_64 VPS). SELF-PUSH proven
(canary green, PR #903). On green preflight: push branch, open a NON-DRAFT PR yourself, then
signal per unit below. No venv activation needed; use the installed `ce`.

---

## BORN-A-FOREMAN EXECUTION MODEL

Drive multiple tickets concurrently: **one git worktree + background subagent-thread per
ticket**. Never merge unit work across branches or worktrees. A BLOCKED unit does not block
the other units from signaling READY.

Serialize on same-file conflicts: Units A / B / C are file-disjoint (see Disjointness section).
All three may run simultaneously EXCEPT that Unit C has a merge precondition that must be
verified before its thread starts.

Report **PER-TICKET**. Before your session ends, emit for each unit:

```
READY <branch> <40-char-sha> PR#<number>
BLOCKED <branch> <one-line reason>
```

If any unit's preflight raises a gate on a file OUTSIDE that unit's diff, do NOT touch the
out-of-scope file. Note the gate verbatim in the signal and mark the unit READY if the gate
is one of the known seat-env false-reds described in each unit below.

---

## PREFLIGHT PRECONDITION — fetch first (all three threads share this step)

Before starting any thread, run once:

```bash
git fetch origin main
git log origin/main --oneline | head -5
```

Confirm origin/main is current. Use the live HEAD as the base for all three branches.

**Do NOT touch `.ce/brain/assertions.yaml` in any unit.** The ledger tail is reserved for the
dev-1 hermes-retirement unit. If any gate demands a ledger append, write `BLOCKED` immediately
and stop that thread.

---

## DISJOINTNESS ANALYSIS (read before starting any thread)

**Unit A files:**
- `docs/guide/solo-ceo-onboarding.md`
- `.ce/changelog/ce-solo-ceo-onboarding-fix.md`
- `.ce/pr-manifests/ce-solo-ceo-onboarding-fix.md`

**Unit B files:**
- `validators/creator_engine_validator/pr_preflight.py`
- `validators/tests/unit/test_pr_preflight.py`
- `.ce/changelog/ce-seat-preflight-parity.md`
- `.ce/pr-manifests/ce-seat-preflight-parity.md`

**Unit C files** (only accessible after `ce-readme-overhaul` merges into origin/main):
- `validators/creator_engine_validator/checks/version_drift.py`
- `validators/tests/unit/test_version_drift.py`
- `validators/tests/unit/test_v1_docs_reconciliation.py`
- `docs/reference/cli.md`
- `.ce/changelog/ce-readme-review-minors.md`
- `.ce/pr-manifests/ce-readme-review-minors.md`

**Collision verdicts:**
- Unit A vs Unit B: **CLEAR** — no shared files.
- Unit A vs Unit C: **CLEAR** — no shared files.
- Unit B vs Unit C: **CLEAR** — no shared files.
- Unit A vs dev-1 hermes (ce-hermes-retirement): **CLEAR** — dev-1 claims `ce_onboard.py`,
  `ce_cli.py`, `.claude/hooks/*`, `docs/delivery/*`, `docs/architecture/*`, `CONTRIBUTING.md`,
  `docs/contracts/*`, `docs/decisions/*`, `.gitignore`, runsc tests, `assertions.yaml`.
  `docs/guide/solo-ceo-onboarding.md` is NOT in dev-1's stop line.
- Unit B vs dev-4 materializer pre-arming (ce-491-prearming): **POTENTIAL COLLISION** on
  `validators/creator_engine_validator/pr_preflight.py` and `validators/tests/unit/test_pr_preflight.py`.
  Dev-4's pre-arming batch lists these as possibly-modified. Before pushing `ce-seat-preflight-parity`,
  run `git fetch origin` and check whether `origin/ce-491-prearming` exists. If it does and
  has commits to those two files, rebase `ce-seat-preflight-parity` onto it (or onto main if
  ce-491-prearming has already merged). If the branch does not exist yet, push as normal.
- Unit C vs PR #907 (ce-readme-overhaul): **TEMPORAL ONLY** — C's precondition is that #907 is
  merged; after merge those files are available. No concurrent conflict.
- Unit C vs dev-1 hermes: **CLEAR** — dev-1 does not claim version_drift.py, test_version_drift.py,
  test_v1_docs_reconciliation.py, or docs/reference/cli.md.
- Unit A vs dev-4 conveyor batch: **CLEAR** — dev-4 claims conveyor_daemon_runner.py, conveyor_intake_queue.py, deploy/conveyor-daemon paths; no overlap with any unit here.

---

## UNIT A — CEO onboarding guide rewrite

Branch: `ce-solo-ceo-onboarding-fix`
Worktree: `/var/tmp/wt-ceo-onboarding`
Declared work class: task (T)

### Problem statement (embedded — no external issue tracker needed)

`docs/guide/solo-ceo-onboarding.md` on origin/main instructs default-mode users to type `ce ratify
--approver-ref`, `ce merge --apply`, and `ce inbox --repo <owner/repo>` as direct terminal commands.
This inverts the ratified product model: users in the default guided mode state their intent and
authorization in natural language; the governed agent invokes the verbs on their behalf. Additionally,
`ce inbox` is not present in the shipped binary (confirmed by inspection of `main()` in
`validators/creator_engine_validator/ce_cli.py` and `V3_FORWARDING_SHIMS`) and must be removed.

This issue was discovered by the welcome-pack quality check, which enforces that CEO-mode flows
must not instruct the user to type bare `ce <verb>` commands. The #906 parity sweep (which closed
a prior docs-parity issue) fixed verb-existence mismatches but did not evaluate the paradigm-level
interaction model in the CEO flow sections. This brief closes that paradigm gap.

### Required rewrite

Rewrite `docs/guide/solo-ceo-onboarding.md` so that:

1. **CEO flow sections are intent-and-authorization dialogue.** The user's role is to state their
   goal in natural language ("I want to review and approve the authentication change") and supply
   authorization ("go ahead, this looks right"). The governed agent confirms scope, surfaces
   awaiting-decision items, and executes verbs on the user's behalf. No bare `ce <verb>` line
   appears in a user-facing instruction in the CEO flow.

2. **Technical asides are clearly labeled and collapsed.** If a command is referenced at all (for
   reference readers who want to know what runs under the hood), it MUST be in a clearly-labeled
   collapsed block such as:
   ```
   <details><summary>Under the hood — what the agent does</summary>

   The agent runs `ce ratify --approver-ref` against your recorded authorization...
   </details>
   ```
   Or in a clearly-labeled "for technical readers" note. Under-the-hood content is never in the
   main instruction flow.

3. **Remove all `ce inbox` references.** `ce inbox` does not exist in the shipped `ce` binary as
   of 0.3.1. Replace any reference to it with its real mechanism: the awaiting-operator queue is
   surfaced through the forge (GitHub) UI where the agent posts items for human review and
   decision. Rewrite the surrounding prose to describe this mechanism without referencing an
   unshipped verb.

4. **Vocabulary rules (public-facing content):**
   - No "bet", "appetite", or internal program names.
   - No ce-ops# ticket references.
   - No seat, host, topology, or fleet internal names.
   - No `.hermes/` mentions in any instruction context.
   - Goal/Done-when/Change-type trio where applicable.
   - Budget appears at most as an opt-in aside.

### Probe before editing

Confirm the issue is not already resolved:
```bash
git show origin/main:docs/guide/solo-ceo-onboarding.md | grep -n "ce inbox\|ce ratify\|ce merge"
```
If no output: the doc has already been fixed — write `BLOCKED ce-solo-ceo-onboarding-fix already-resolved-on-main`.

### Known seat-env false-reds

The control-plane portability gate and check-examples/libsodium gate may emit a false-RED in this
seat's image on paths OUTSIDE your diff. If the ONLY failures are those two gates on files you did
not touch, note them verbatim in the PR body evidence section and signal READY. Any failure on
`docs/guide/solo-ceo-onboarding.md` itself = fix it or signal BLOCKED.

### Signal

```
READY ce-solo-ceo-onboarding-fix <40-char-sha> PR#<number>
BLOCKED ce-solo-ceo-onboarding-fix <one-line reason>
```

---

## UNIT B — seat-preflight divergence: portability invocation parity

Branch: `ce-seat-preflight-parity`
Worktree: `/var/tmp/wt-seat-preflight`
Declared work class: task (T)

### Evidence (embedded from controller state ledgers, 2026-07-08)

**Source 1 — night arc mandate 2026-07-07:**
> SEAT-IMAGE PARITY: libsodium missing in dev-4 (dgx aarch64) image — breaks check-examples signed
> worktree-lease verification in-seat → false-RED preflight. Add to image build; audit dev-3 image too.
>
> PORTABILITY-GATE seat-side false-RED PATTERN: BOTH dev-3 (canary, x86_64) and dev-4 (slice 2, aarch64)
> hit control-plane portability gate red in-seat while main CI is green. dev-4 red points at
> in-seat `scan-portability-plane .` and CI's pr_preflight path; fix so seat-ready profile matches CI.

**Source 2 — day arc checkpoint 2026-07-08 (DAYARC2E):**
> PATTERN TICKET-WORTHY: seat-side preflight diverges from CI on portability gate (both archs,
> proven environmental via clean-main controls) + libsodium — the seat-ready profile (#896) can't
> be trusted RED until fixed. Ledger has evidence.

**Source 3 — day arc 2026-07-08 (DAYARC2F):**
> dev-3: seat-preflight divergence validator-side fix (portability invocation parity
> in seat-ready profile; evidence in ledger). Image/libsodium half = controller host op.

**Source 4 — release engineering gap analysis 2026-07-08:**
> Seat preflight false-REDs: seat images diverge from CI env (libsodium absent; portability
> scan invocation differs). → hermeticity defect. Distinct layer, same discipline family.

**Conclusion from ledger:** Two proven false-reds exist:
- **False-red 1 — "Control-plane portability guard"** (check name in pr_preflight.py):
  runs `scan-portability-plane .` via `[sys.executable, "-m", "creator_engine_validator",
  "scan-portability-plane", "."]`. Fails in both seat images (dev-3 VPS x86_64 and dev-4 DGX
  aarch64) on clean main. CI (`validate.yml`) does NOT have a `scan-portability-plane` step.
  The `seat-ready` profile was introduced by PR #896 and does not add any profile-specific
  handling for this check — it inherits the default behavior which fails in-seat.
  **This is the validator-side fix scope.**
- **False-red 2 — check-examples/libsodium gate**: requires libsodium in the seat image for
  signed worktree-lease verification. Missing from seat images.
  **OUT OF SCOPE — image rebuild is a controller host op.**

### Profile code ground truth (on origin/main)

File: `validators/creator_engine_validator/pr_preflight.py`
- Line 32: `SEAT_READY_PROFILE = "seat-ready"`
- Line 34: `SEAT_READY_TEST_COMMAND = DEFAULT_TEST_COMMAND.replace("-n auto", f"-n {SEAT_READY_PYTEST_WORKER_CAP}", 1)`
- Line 57: `VALIDATE_PR_PROFILES = ("contained-seat", SEAT_READY_PROFILE)`
- Lines ~1188–1204: "Control-plane portability guard" check —
  ```python
  checks.append(
      _run_check(
          "Control-plane portability guard",
          lambda: (
              _run_checked(
                  "Control-plane portability guard",
                  [py, "-m", "creator_engine_validator", "scan-portability-plane", "."],
                  config.repo_root,
                  runner=runner,
                  env=py_env,
                  out=out,
                  err=err,
              ),
              "no undeclared Linux runtime-plane assumptions",
          )[1],
          out,
          err,
      )
  )
  ```
  This check runs identically for ALL profiles, including `seat-ready`. CI (`validate.yml`)
  does not have a `scan-portability-plane` step — portability is validated only through the
  pytest suite, and there is no `test_portability_plane.py` integration test.

### Required fix

Make the seat-ready profile's portability gate invocation match CI's behavior (CI does not
invoke `scan-portability-plane` outside of `run_preflight`; it IS green at CI). Add
profile-specific handling so that when `config.profile == SEAT_READY_PROFILE`, the
"Control-plane portability guard" check returns a graceful skip or ENV-SKIP outcome rather
than a hard failure on environmental false-reds.

Two acceptable implementation patterns:

**Pattern A — Profile-level skip** (highest parity with CI since CI does not run this check):
```python
if config.profile == SEAT_READY_PROFILE:
    return "not applicable; portability gate is CI-validated, not seat-validated"
```
Applied inside the portability guard lambda before the `_run_checked` call.

**Pattern B — ENV-SKIP wrapping** (matches the existing autogen gate pattern in this file):
Wrap the `_run_checked` call in a try/except RuntimeError; if the error output contains
`_looks_like_missing_environment` indicators, return `f"ENV-SKIP portability guard: {detail}"`
rather than re-raising. Also accept any non-zero returncode from `scan-portability-plane` when
the stderr/stdout contains environment-diagnostic markers as a seat-env skip.

Choose whichever pattern is cleaner given the code; Pattern A is preferred because it achieves
perfect parity with CI behavior (CI skips this check).

### Test requirement

Add a test to `validators/tests/unit/test_pr_preflight.py` proving the seat-ready profile
skips or ENV-SKIPs the portability guard. The existing `FakeRunner` returns `CommandResult(0, "ok\n", "")`
for unrecognized argv by default; you may need to add a `portability_returncode` parameter
and a test that passes `portability_returncode=1` (simulating the in-seat failure) and asserts
the seat-ready preflight still returns 0 (PASS) with a skip/ENV-SKIP note in the output.

### Probe before editing

Confirm the fix is not already on main:
```bash
git show origin/main:validators/creator_engine_validator/pr_preflight.py | \
  grep -A5 "portability guard" | grep -i "seat.ready\|SEAT_READY\|not applicable\|env.skip"
```
If this returns output showing a skip/ENV-SKIP for the seat-ready profile: write
`BLOCKED ce-seat-preflight-parity already-resolved-on-main`.

### Collision guard

Before pushing, run:
```bash
git fetch origin
git ls-remote origin "ce-491-prearming" | head -3
```
If `ce-491-prearming` exists remotely, inspect its `pr_preflight.py` diff and rebase onto it
or onto the post-merge main before pushing `ce-seat-preflight-parity`.

### Known seat-env false-reds

After your fix, the portability gate should no longer be a false-red for the seat-ready profile.
The check-examples/libsodium gate may still emit a false-RED on paths OUTSIDE your diff. If that
is the ONLY failure, note it verbatim and signal READY. Any failure on `pr_preflight.py` or
`test_pr_preflight.py` = fix it or signal BLOCKED.

### Signal

```
READY ce-seat-preflight-parity <40-char-sha> PR#<number>
BLOCKED ce-seat-preflight-parity <one-line reason>
```

---

## UNIT C — README-review minors follow-up

Branch: `ce-readme-review-minors`
Worktree: `/var/tmp/wt-readme-minors`
Declared work class: task (T)

### PRECONDITION (start this thread ONLY after verifying ce-readme-overhaul is merged)

Before starting this thread, run:
```bash
git fetch origin main
git log origin/main --oneline | grep "readme\|cli.md\|version.drift" | head -3
```
Confirm a commit merging `ce-readme-overhaul` (PR #907) appears in origin/main history, AND that
`docs/reference/cli.md` exists on main:
```bash
git show origin/main:docs/reference/cli.md 2>/dev/null | head -5
```
If no output: PR #907 has not merged yet. Wait and re-fetch, or signal
`BLOCKED ce-readme-review-minors precondition-not-met-readme-overhaul-not-merged`.

Create the worktree only after the precondition passes.

### Context

PR #907 (ce-readme-overhaul) introduced two accepted-but-deferred findings in its review.
Both are confirmed not fixed in that PR. This unit closes them.

### Finding 1 — `README_CE_VERSION_TEXT` regex false-positive risk

**Where:** `validators/creator_engine_validator/checks/version_drift.py`

After PR #907 merges, `version_drift.py` contains a new constant:
```python
README_CE_VERSION_TEXT = _pattern(
    "README CE version text",
    rf"(?i)\b(?:current\s+release|version|(?:ce|creator\s+engine)"
    rf"(?:\s+(?:v(?:ersion)?|release|current\s+release))?)"
    rf"\s*(?::|=|\bis\b)?\s*v?{SEMVER_RE}\b(?:\s+is\s+current)?",
)
```

The standalone `version` alternative in this regex can match prose like
"Python version 3.14.0" or "requires Python version 3.12.0 or later",
producing false-positive drift alerts for non-CE version mentions in README.md.

**Required fix:** Add a CE-context prefix guard so the bare `version` alternative only
matches when preceded by a CE-context word. Acceptable approaches:

- Replace the standalone `version` alternative with `(?:ce|creator\s+engine)\s+v?ersion` (requires
  explicit CE product context before "version").
- OR: add a negative lookbehind for common non-CE words:
  `(?<!Python\s)(?<!python\s)(?<!Node\s)(?<!node\s)(?<!Go\s)version`.
- OR: restructure the alternation so that bare `version` is never a standalone match — it must
  always be preceded by `ce`, `creator engine`, `creator-engine`, or `current release`.

After the fix, the pattern must still match:
- `CE version 0.3.1` → MATCH
- `creator engine version 0.3.1` → MATCH
- `current release 0.3.1` → MATCH
- `version 0.3.1` preceded by a CE-context noun → MATCH (or SKIP — either is acceptable
  as long as the guard prevents false-positives)

And must NOT match:
- `Python version 3.14.0` → NO MATCH
- `requires Python version 3.12.0` → NO MATCH
- `Node version 20.0.0` → NO MATCH

**Extend test coverage:** Add tests to `validators/tests/unit/test_version_drift.py` covering:
1. A README.md containing `Python version 3.14.0` passes without a drift error.
2. A README.md containing `CE version 0.3.1` (matching current) passes.
3. A README.md containing `CE version 0.2.9` (stale) fails with `CODE_STALE`.

Ground the tests in the existing `_write_repo` helper and `_surface` helper pattern already in
that file; add a surface that includes `README_CE_VERSION_TEXT` alongside `PACKAGE_PIN` where needed.

### Finding 2 — `ce conveyor` undocumented; test silent

**Where (docs):** `docs/reference/cli.md`

After PR #907 merges, `docs/reference/cli.md` lists public `ce` command groups but omits
`ce conveyor`. Confirm:
```bash
git show origin/main:docs/reference/cli.md | grep "conveyor"
```
If output shows conveyor is already documented: skip Finding 2's docs change (but still
strengthen the test).

`ce conveyor` is a working, shipped command group:
- Dispatched pre-argparse in `ce_cli.py` `main()` at ~line 5755:
  ```python
  if argv and argv[0] == "conveyor":
      return _conveyor_bridge(argv[1:])
  ```
- Subcommand: `sweep` — enqueues approved, CI-green creator-engine PRs stranded outside the
  merge queue.
- The `_ce_command_groups()` helper in `test_v1_docs_reconciliation.py` reads only
  `ce_cli._build_parser()` (the argparse tree) and therefore misses `conveyor`.
  `test_cli_reference_documents_every_ce_command_group` passes silently.

**Required doc fix:** Add `ce conveyor` to `docs/reference/cli.md` in the "Queue And
Coordination" section (or a clearly-labeled pre-argparse dispatch section):

```markdown
| `ce conveyor sweep` | Enqueue approved, CI-green PRs that are stranded outside the merge queue. |
```

or as a group-level entry:
```markdown
| `ce conveyor` | Repair the merge queue by enqueuing approved, CI-green PRs that were stranded. Use `ce conveyor sweep`. |
```

**Required test strengthening:** Modify `validators/tests/unit/test_v1_docs_reconciliation.py`
to also catch pre-argparse dispatch groups. Approach:

1. Add a constant to `validators/creator_engine_validator/ce_cli.py`:
   ```python
   PRE_ARGPARSE_DISPATCH_GROUPS: frozenset[str] = frozenset({"conveyor", "press-merge-evidence"})
   ```
   (These are the groups dispatched before `_build_parser()` in `main()`.)

2. Add a test in `test_v1_docs_reconciliation.py`:
   ```python
   def test_cli_reference_documents_every_pre_argparse_dispatch_group():
       text = _cli_reference_text()
       # Groups dispatched before argparse in main() are not in _ce_command_groups().
       # They must be checked separately so they cannot silently drop out of the docs.
       public_pre_argparse = ce_cli.PRE_ARGPARSE_DISPATCH_GROUPS - ce_cli.INTERNAL_COMMAND_GROUPS
       missing = [g for g in public_pre_argparse if not re.search(rf"\bce {re.escape(g)}\b", text)]
       assert not missing, (
           f"docs/reference/cli.md does not document pre-argparse ce command group(s): {missing}"
       )
   ```

If `press-merge-evidence` is internal-only (not a public-facing command), add it to
`ce_cli.INTERNAL_COMMAND_GROUPS` or define a `PRE_ARGPARSE_INTERNAL_GROUPS` constant and
exclude it from the doc-coverage requirement. Check the existing INTERNAL_COMMAND_GROUPS constant
to decide.

### Probe before editing

```bash
# Finding 1 probe:
git show origin/main:validators/creator_engine_validator/checks/version_drift.py | \
  grep -A5 "README_CE_VERSION_TEXT"

# Finding 2 probe:
git show origin/main:docs/reference/cli.md | grep -i "conveyor"
git show origin/main:validators/creator_engine_validator/ce_cli.py | \
  grep -n "PRE_ARGPARSE_DISPATCH_GROUPS"
```

If Finding 1 is already guarded and Finding 2 is already documented with a strengthened test:
`BLOCKED ce-readme-review-minors already-resolved-on-main`.

### Hard constraints

- Do NOT touch `README.md` — not in this unit's scope.
- Do NOT touch `.ce/brain/assertions.yaml`.
- Do NOT add argparse groups to ce_cli.py — this is a docs+test unit only (plus the
  `PRE_ARGPARSE_DISPATCH_GROUPS` constant which is purely declarative).
- Do NOT remove or weaken existing tests in `test_v1_docs_reconciliation.py` or
  `test_version_drift.py`.
- Vocabulary rules apply throughout: no internal names, no ce-ops# refs in docs.

### Known seat-env false-reds

The control-plane portability gate and check-examples/libsodium gate may emit false-REDs on
paths OUTSIDE your diff. If those are the ONLY failures, note them verbatim and signal READY.

### Signal

```
READY ce-readme-review-minors <40-char-sha> PR#<number>
BLOCKED ce-readme-review-minors <one-line reason>
```

---

## Standing preflight directive

Run `ce validate-pr --profile seat-ready` before committing for each unit. A PASS on seat-ready
profile is the target (including after Unit B's fix, which should make the portability gate
behave correctly for seat-ready). While Unit B is not yet merged:

- For Units A and C: if the ONLY failures are "Control-plane portability guard" and/or
  "Creator Engine validator - check-examples aggregate gate" on files OUTSIDE your diff,
  note them verbatim and proceed.
- For Unit B specifically: after your fix, the portability gate failure should become a SKIP
  or ENV-SKIP in the seat-ready profile — if it still hard-fails after your fix, that is a
  real failure to debug.

---

## Carrier and changelog requirements (all units)

Each unit needs:
- `.ce/changelog/<branch-slug>.md` — one-paragraph changelog fragment, public lens.
- `.ce/pr-manifests/<branch-slug>.md` — carrier with every changed path enumerated,
  `AUTHORIZED_PATHS_COUNT` and `AUTHORIZED_PATHS_SHA256` correct, exactly ONE
  `- **Declared work class:** T` line.

Carrier slug MUST equal the branch name exactly.

---

## PR body requirements (all units)

Each PR body must include:
1. **Goal / Done-when / Change-type** trio.
2. **Preflight evidence** — output of `ce validate-pr --profile seat-ready` (or the relevant
   profile), noting any seat-env false-reds verbatim.
3. **Probe result** — confirming the issue was not already resolved on main before editing.
4. For Unit B: include the evidence section showing the two false-reds and stating the
   image/libsodium half is OUT OF SCOPE.
5. For Unit C: include the `git show origin/main:docs/reference/cli.md | grep "conveyor"`
   probe result and the `README_CE_VERSION_TEXT` regex before and after.
6. **Declared work class: T** (one line, exactly, in the PR body).

PRs are NON-DRAFT (the born-draft defect is known; open as ready-for-review directly).
