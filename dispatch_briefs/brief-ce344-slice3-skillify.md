# Brief: ce-ops#344 slice 3 — skill-ify ce-dispatch + ce-harvest

**Seat**: dev-4 (ce-dgx-codex, CONTAINED — no egress, no self-push)
**Role**: implementer (Spec 005 §d.2)
**Ticket**: ce-ops#344 prong 3
**Branch**: `ce-344-slice3-skillify` (create from `origin/main`)

```
git checkout -b ce-344-slice3-skillify origin/main
```

When done: commit, then report `READY-FOR-HARVEST` with the full commit SHA.
Do NOT push. Controller harvests via git-bundle.

---

## Ticket context (fully embedded — no egress, no ce-ops access)

ce-ops#344 = "Controller knowledge-load: deterministic startup/dispatch/harvest
checklist + bootstrap wiring + harvest/territory-check skill-ification."

**Problem.** High-frequency controller actions (dispatch, harvest) lack
"discipline-as-code": territory-check and preflight are prose guidance, not
enforced steps inside the action invocation. The result is recurring omissions
after every `/clear`.

**Slice 1 (already MERGED as PR #609 into origin/main)** shipped the overlay data
in `docs/design/controller-bootstrap-ssot.json` and the generator. It is done.

**Playbooks→Skills pilot (already MERGED as PR #578 into origin/main)** shipped:
- `.claude/skills/ce-dispatch/SKILL.md` — thin pointer to
  `playbooks/controller/briefs/dispatch.md`; references territory-map check but
  does not enforce it as a mandatory numbered step.
- `.claude/skills/ce-merge-gate/SKILL.md` — checklist-only, no mutating command.
- `validators/creator_engine_validator/checks/skill_antidrift_guard.py` — CI check
  asserting every `ce-` skill (a) references an in-tree SSOT and (b) embeds no
  mutating forge command.
- `validators/tests/unit/test_skill_antidrift_guard.py` — tests for the guard.

**Prong 3 remaining work (this slice):**

1. **Tighten `ce-dispatch` skill** — the territory-check must be a REQUIRED,
   numbered step (not just a reference mention). The step must name the exact
   artefacts to inspect and state that failing to intersect paths is a hard stop
   before dispatch. The skill must remain a thin pointer (no procedure re-authoring)
   and must pass the antidrift guard.

2. **Add `ce-harvest` skill** — new file `.claude/skills/ce-harvest/SKILL.md`.
   The skill is a thin pointer to a new in-tree SSOT brief
   `playbooks/controller/briefs/harvest.md`. It must assert: preflight GREEN before
   touch, changelog collected, manifest cleanup via carrier_gen API, controller
   holds merge gate (seat never merges). It must pass the antidrift guard
   (no mutating forge command, references a `playbooks/` path).

3. **Add `playbooks/controller/briefs/harvest.md`** — new SSOT brief for the
   harvest procedure (the thin pointer target). Concise, 5-8 sentences covering:
   verify READY-FOR-HARVEST signal, run preflight on branch, harvest to staging
   worktree, collect changelogs, carrier_gen, enqueue only after independent
   review + green checks.

4. **Update `validators/tests/unit/test_skill_antidrift_guard.py`** — add explicit
   assertion that `ce-harvest` exists on disk (matching the existing pattern for
   `ce-dispatch` and `ce-merge-gate`); verify the shipped skills (all three) pass
   the guard in one `run([repo_root])` call.

---

## Allowed paths (CLOSED LIST — do not touch anything outside this list)

```
.claude/skills/ce-dispatch/SKILL.md
.claude/skills/ce-harvest/SKILL.md
playbooks/controller/briefs/harvest.md
validators/tests/unit/test_skill_antidrift_guard.py
.ce/changelog/ce344-slice3-skillify.md
.ce/pr-manifests/ce344-slice3-skillify.md
```

**NEVER touch:**
- `docs/design/controller-bootstrap-ssot.json` (slice 2 / dev-3 territory)
- `scripts/gen-controller-bootstrap.py` (slice 2 / dev-3 territory)
- `validators/tests/unit/test_gen_controller_bootstrap.py` (slice 2 / dev-3 territory)
- `validators/creator_engine_validator/checks/path_manifest_fidelity.py` or its test
  (dev-1 / ce-ops#345 owns those — collision forbidden)
- Any file not in the closed list above

---

## Required work (step by step)

### Step 0 — orient from origin/main

```bash
git fetch origin
git checkout -b ce-344-slice3-skillify origin/main
```

Read before editing:
- `.claude/skills/ce-dispatch/SKILL.md`
- `.claude/skills/ce-merge-gate/SKILL.md` (reference for skill shape)
- `validators/tests/unit/test_skill_antidrift_guard.py`
- `validators/creator_engine_validator/checks/skill_antidrift_guard.py` (understand
  the SSOT-pointer and mutating-command rules)

### Step 1 — create `playbooks/controller/briefs/harvest.md`

This is the in-tree SSOT that the `ce-harvest` skill will point at. Write a concise
harvest procedure brief (follow the style of `dispatch.md` and `merge-gate.md`):

```markdown
# Harvest

Check the seat output for the READY-FOR-HARVEST signal and the commit SHA before
starting. Verify `ce validate-pr` (or `scripts/ce-preflight.sh`) is GREEN on the
branch in one pass before touching the staging area. Harvest the branch to a
staging worktree under `.ce/wt-<slug>-harvest/`. Collect changelogs from
`.ce/changelog/<slug>.md`. Regenerate the PR manifest via the `carrier_gen` API
(`write_carriers(base="origin/main")`) — do not hand-list carrier filenames.
Enqueue for merge only after independent non-author review and green required CI
checks pass. The controller holds the merge gate; the seat that authored the work
never merges or self-approves.
```

### Step 2 — create `.claude/skills/ce-harvest/SKILL.md`

The skill must be a thin pointer to `playbooks/controller/briefs/harvest.md`.
It must satisfy the antidrift guard: (a) contain a reference to a `playbooks/`
path, and (b) contain no mutating forge command (`gh pr merge`, `git push`, etc.).

Use `ce-merge-gate` as the shape reference. Required frontmatter fields:
```yaml
---
name: "ce-harvest"
description: "Harvest-sequence assertion: verify READY-FOR-HARVEST signal, confirm preflight GREEN, collect changelogs and carrier, then STOP. Internal controller ergonomics only. Use when the controller is about to harvest a seat's completed work."
argument-hint: "Optional branch slug or seat name"
ce-internal: true
ce-skill-class: "action"
ce-mutating: false
user-invocable: true
disable-model-invocation: false
---
```

Body (thin pointer — follow the ce-dispatch pattern exactly):

```markdown
> INTERNAL controller ergonomics. This skill is a **thin pointer** into the
> in-tree harvest SSOT — it does **not** restate the procedure. The action
> SSOT is the brief in-tree; this skill only removes rediscovery friction.

## SSOT

- Procedure SSOT (in-tree): `playbooks/controller/briefs/harvest.md`
- Preflight doctrine: `scripts/ce-preflight.sh` or `ce validate-pr`; GREEN
  one-pass required ([[ce-run-full-preflight-before-push]]).
- Carrier mechanic: `carrier_gen` API (`write_carriers(base="origin/main")`) — never
  hand-list filenames ([[ce-pr-path-manifest-carrier-required]]).

## What to do

1. Read `playbooks/controller/briefs/harvest.md` and follow it verbatim. It is
   the source of truth for the harvest sequence.
2. Verify the READY-FOR-HARVEST signal + commit SHA from the seat before starting.
3. Run `ce validate-pr` (or `scripts/ce-preflight.sh`) on the branch and confirm
   GREEN before any staging or PR action.
4. Collect `.ce/changelog/<slug>.md` and regenerate the PR manifest via the
   `carrier_gen` API.
5. Enqueue for merge only after independent review and green required checks. The
   controller never self-merges authored work.

This skill carries no authority and grants no gate. Governance rides on CE's
`PreToolUse` hook-check seam, never on this skill.
```

### Step 3 — tighten `.claude/skills/ce-dispatch/SKILL.md`

Open the existing file. The current "What to do" section references territory-map
as step 3 but does not make it a hard stop. Update the file so territory-check is
explicitly a REQUIRED numbered step with a hard-stop consequence and exact artefact
names.

Required change to the "What to do" section (replace step 3 with a tightened
version and add the hard-stop language):

```markdown
## What to do

1. Read `playbooks/controller/briefs/dispatch.md` and follow it verbatim. It is
   the source of truth for what a dispatch brief must name.
2. Apply the pointer + SHA mechanic per [[ce-seat-dispatch-prompt-pointer-sha]]:
   write the seed brief to a file, compute its `sha256sum`, and send the worker
   only the file pointer and the hash.
3. **REQUIRED territory-check (hard stop before dispatch):** Check the live
   in-flight territory map per [[ce-dispatch-territory-map-before-dispatch]].
   Inspect ALL of: `.ce/pr-manifests/` (open carrier slugs), `.ce/briefs/`
   (active briefs), `git worktree list` output (live worktree branches), and
   `.ce/wt-*/` staging directories. Intersect EVERY candidate path against ALL
   in-flight files. If any path collision is found, do not dispatch; report the
   collision to the controller and stop.
4. Record or verify the work claim before the target seat starts.

This skill carries no authority and grants no gate. Any forge mutation that a
dispatch produces still rides on CE's `PreToolUse` hook-check seam. Do not embed
forge commands here.
```

The file must still pass the antidrift guard (no mutating forge command; still
references `playbooks/controller/briefs/dispatch.md`).

### Step 4 — update `test_skill_antidrift_guard.py`

In `validators/tests/unit/test_skill_antidrift_guard.py`, find the test
`test_shipped_pilot_skills_pass_the_guard` and extend it to also assert
`ce-harvest` is present:

```python
def test_shipped_pilot_skills_pass_the_guard():
    # The three pilot skills shipped in THIS repo must satisfy the guard.
    repo_root = Path(__file__).resolve().parents[3]
    skills_root = repo_root / ".claude" / "skills"
    assert (skills_root / "ce-dispatch" / "SKILL.md").is_file()
    assert (skills_root / "ce-merge-gate" / "SKILL.md").is_file()
    assert (skills_root / "ce-harvest" / "SKILL.md").is_file()   # NEW

    result = run([repo_root])

    assert result.ok, [e.format() for e in result.errors]
```

No other test in that file needs to change. The antidrift guard's `run([repo_root])`
call already scans all `ce-` skills automatically, so the new `ce-harvest` skill
is covered without further test additions.

Do NOT change the registered-check count assertions in any other test file —
this slice adds no new CI check (`@register` entry).

### Step 5 — validate

```bash
cd <repo_root>

# Install validator in editable mode if not already present
pip install -e validators/ --quiet

# Run just the antidrift guard tests
python -m pytest validators/tests/unit/test_skill_antidrift_guard.py -v

# Verify the new ce-harvest skill passes the guard directly
python -c "
from pathlib import Path
from creator_engine_validator.checks.skill_antidrift_guard import run
result = run([Path('.')])
if result.ok:
    print('PASS: antidrift guard clean')
else:
    for e in result.errors:
        print('FAIL:', e.format())
"

# Run full preflight (ONE pass, must be GREEN)
PATH="$PWD/validators/.venv/bin:$PATH" scripts/ce-preflight.sh \
  --base origin/main \
  --head-ref ce-344-slice3-skillify \
  --declared-work-class story
```

If ce-preflight.sh is not in PATH, use:
```bash
python -m creator_engine_validator validate-pr \
  --base origin/main \
  --head-ref ce-344-slice3-skillify \
  --declared-work-class story
```

Preflight MUST be GREEN in one pass. Two-strikes rule: if the same gate fails twice,
stop and report to the controller rather than continuing to iterate.

### Step 6 — carrier and changelog

**Changelog** — create `.ce/changelog/ce344-slice3-skillify.md`:
```markdown
## ce-ops#344 slice 3 — skill-ify ce-dispatch + ce-harvest

- Added `playbooks/controller/briefs/harvest.md` — in-tree SSOT for harvest
  sequence; thin-pointer target for the new `ce-harvest` skill.
- Added `.claude/skills/ce-harvest/SKILL.md` — thin-pointer CE action-skill
  asserting preflight-GREEN, changelog-collect, carrier-gen, and
  controller-holds-merge-gate; passes antidrift guard.
- Tightened `.claude/skills/ce-dispatch/SKILL.md` — territory-check is now a
  REQUIRED hard-stop step with exact artefact paths named; still a thin pointer.
- Extended `test_shipped_pilot_skills_pass_the_guard` to assert `ce-harvest`
  exists and is antidrift-clean.
```

**Carrier** — generate the PR manifest using the `carrier_gen` API (NOT by hand):

```python
from creator_engine_validator.carrier_gen import write_carriers
write_carriers(base="origin/main")
```

Or via CLI if available:
```bash
python -m creator_engine_validator carrier-gen --base origin/main
```

The manifest slug must match the branch slug `ce344-slice3-skillify`.

### Step 7 — commit

```bash
git add playbooks/controller/briefs/harvest.md
git add .claude/skills/ce-harvest/SKILL.md
git add .claude/skills/ce-dispatch/SKILL.md
git add validators/tests/unit/test_skill_antidrift_guard.py
git add .ce/changelog/ce344-slice3-skillify.md
git add .ce/pr-manifests/ce344-slice3-skillify.md

git commit -m "feat(ce-ops#344): skill-ify ce-dispatch (territory hard-stop) + add ce-harvest skill (slice 3)"
```

Record the full commit SHA and report it to the controller.

---

## PR body line (required — CI gate reads this)

Every PR for this slice must contain EXACTLY ONE of these lines in the PR body:

```
- **Declared work class:** story
```

---

## Docs-coupling warning

This slice does NOT add a new `ce` CLI group, so `test_v1_docs_reconciliation.py`
is not triggered by a CLI change. However: the antidrift guard (`skill_antidrift_guard`)
is a REGISTERED CI check — verify the registered check count in the following files
remains at 66 (no new `@register` entry is added by this slice, so no count change):
- `validators/tests/unit/test_open_change.py`
- `validators/tests/unit/test_redact.py`
- `validators/tests/unit/test_evidence_sink.py`
- `validators/tests/unit/test_app_jwt_runner.py`
- `validators/tests/unit/test_credential_runner.py`
- `validators/tests/unit/test_merge.py`
- `validators/tests/unit/test_change_status.py`

You do NOT need to edit any of those files. They are outside your allowed paths.
If preflight reports a count mismatch, stop and report to the controller.

---

## Stop line

Stop after: commit + SHA recorded + preflight GREEN report sent to controller.

Do NOT push to any remote.
Do NOT open a PR.
Do NOT touch any file outside the closed list.
Do NOT approve or merge anything.

Report: `READY-FOR-HARVEST` with the commit SHA and the preflight evidence (pass/fail summary).
