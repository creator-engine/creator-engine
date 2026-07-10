# Brief: ce-ops#344 slice 2 — checklist-content hardening (SSOT overlay expansion)

**Seat**: dev-3 (ce-vps-codex, CONTAINED — no egress, no self-push)
**Role**: implementer (Spec 005 §d.2)
**Ticket**: ce-ops#344 prong 2
**Branch**: `ce-344-slice2-checklist` (create from `origin/main`)

```
git checkout -b ce-344-slice2-checklist origin/main
```

When done: commit, then report `READY-FOR-HARVEST` with the full commit SHA.
Do NOT push. Controller harvests via git-bundle.

---

## Ticket context (fully embedded — no egress, no ce-ops access)

ce-ops#344 = "Controller knowledge-load: deterministic startup/dispatch/harvest
checklist + bootstrap wiring + harvest/territory-check skill-ification."

**Problem.** CE controller sessions do not deterministically load the full set of
high-frequency operating checklists on startup or after `/clear`. Knowledge exists
but rides on recall rather than enforcement.

**Slice 1 (already MERGED as PR #609 into origin/main)** shipped:
- `docs/design/controller-bootstrap-ssot.json` — added a `controller_knowledge_overlay`
  section with: startup_sequence, pre_dispatch_checklist, harvest_sequence,
  subagent_model_routing, preflight_discipline, g5_body_line_rule,
  new_ce_group_coupling.
- `scripts/gen-controller-bootstrap.py` — extended to validate and render the
  overlay section via `render_knowledge_overlay()`.
- `validators/tests/unit/test_gen_controller_bootstrap.py` — tests that the
  overlay section is present and its content appears in rendered output.

**Prong 2 remaining work (this slice).** Slice 1 put the mechanical overlay data
into the SSOT. What is still missing:

1. **Merge-gate checklist** — the overlay currently has no `merge_gate_checklist`
   key. The issue specifies the controller needs: verify reviewDecision==APPROVED on
   current head (dismissed != approved), every required check passing, ratification
   standing grant or Operator confirm, then stop (never self-merge). Add this key
   to the SSOT JSON + validate + render it.

2. **Territory-check assertion** — the pre_dispatch_checklist mentions checking
   worktrees but does not name the exact artefacts to inspect (`.ce/pr-manifests/`,
   `.ce/briefs/`, active `.claude/worktrees/`, `.ce/wt-*/`). Tighten this entry in
   the JSON to be maximally deterministic (exact paths named) rather than generic
   prose.

3. **Verify-not-already-landed step** — `pre_dispatch_checklist` does not currently
   include the "verify the work hasn't already landed (check git log + PR state
   before re-dispatching)" check. Add it as an explicit item.

4. **REQUIRED_SECTIONS / validate_ssot** — the generator's `validate_ssot` already
   requires `controller_knowledge_overlay`; no schema version bump needed. But the
   required inner keys check should add `merge_gate_checklist` so a missing key
   fails closed (rather than silently passing).

5. **Tests** — extend `validators/tests/unit/test_gen_controller_bootstrap.py`:
   - Assert `merge_gate_checklist` in the required keys set.
   - Assert rendered output contains a merge-gate section heading (e.g.,
     `"### Merge-Gate Checklist"` or `"Merge-Gate Checklist"`).
   - Assert the rendered output includes the "dismissed" keyword (to pin the
     "dismissed != approved" invariant).

6. **Renderer** — extend `render_knowledge_overlay()` in the generator to include
   a "Merge-Gate Checklist" section rendered from the new SSOT key.

---

## Allowed paths (CLOSED LIST — do not touch anything outside this list)

```
docs/design/controller-bootstrap-ssot.json
scripts/gen-controller-bootstrap.py
validators/tests/unit/test_gen_controller_bootstrap.py
.ce/changelog/ce344-slice2-checklist.md
.ce/pr-manifests/ce344-slice2-checklist.md
```

**NEVER touch:**
- `validators/creator_engine_validator/checks/path_manifest_fidelity.py` or its test
  (dev-1 / ce-ops#345 owns those files — collision forbidden)
- `.claude/skills/` (that is slice 3 / dev-4's territory)
- `playbooks/` (slice 3 territory)
- Any file not in the closed list above

---

## Required work (step by step)

### Step 0 — orient from origin/main

```bash
git fetch origin
git checkout -b ce-344-slice2-checklist origin/main
```

Read the current state of ALL three slice-1 files before editing:
- `docs/design/controller-bootstrap-ssot.json`
- `scripts/gen-controller-bootstrap.py`
- `validators/tests/unit/test_gen_controller_bootstrap.py`

### Step 1 — extend the SSOT JSON

In `docs/design/controller-bootstrap-ssot.json`, inside
`controller_knowledge_overlay`, make the following changes:

**a. Tighten `pre_dispatch_checklist`** — replace the generic worktree item with a
precise artefact list:

Old item (approximate):
```
"Check the live in-flight territory map: consult .ce/pr-manifests/, .ce/briefs/, active worktrees under .claude/worktrees/, and .ce/wt-*/.",
```
New item:
```
"Check the live in-flight territory map: read .ce/pr-manifests/ for open carrier slugs, .ce/briefs/ for active briefs, git worktree list for live branches, and .ce/wt-*/ for harvest staging; intersect every candidate path against ALL of these.",
```

**b. Add verify-not-already-landed item** to `pre_dispatch_checklist`:
```
"Verify-not-already-landed: before re-dispatching or re-deciding, check git log origin/main and the PR list for the ticket; if the work or Operator decision already landed, do not re-dispatch.",
```

**c. Add `merge_gate_checklist` key** to `controller_knowledge_overlay` (a new
top-level array inside the overlay object):
```json
"merge_gate_checklist": [
  "Confirm reviewDecision == APPROVED on the current head from a non-author seat; a dismissed changes-request does not satisfy this.",
  "Confirm every required CI check on the current head is passing.",
  "Confirm ratification: a standing merge grant or explicit Operator confirmation is in scope.",
  "If any gate is missing: report which gate failed and do not merge.",
  "If all three gates pass: report gates GREEN then STOP; the merge itself is a separate explicit step."
]
```

### Step 2 — extend the generator validator

In `scripts/gen-controller-bootstrap.py`, in `validate_ssot()`, add
`"merge_gate_checklist"` to the for-loop that calls `require_list` on overlay keys:

```python
for key in (
    "startup_sequence",
    "pre_dispatch_checklist",
    "harvest_sequence",
    "preflight_discipline",
    "g5_body_line_rule",
    "new_ce_group_coupling",
    "merge_gate_checklist",   # NEW
):
    require_list(overlay.get(key), f"$.controller_knowledge_overlay.{key}")
```

### Step 3 — extend the renderer

In `scripts/gen-controller-bootstrap.py`, in `render_knowledge_overlay()`, add a
"Merge-Gate Checklist" section (append after the existing sections):

```python
("Merge-Gate Checklist", bullet_lines(overlay["merge_gate_checklist"])),
```

(Match the existing pattern for startup_sequence, harvest_sequence, etc.)

### Step 4 — extend the tests

In `validators/tests/unit/test_gen_controller_bootstrap.py`:

**a.** In `test_required_overlay_keys`, add `"merge_gate_checklist"` to the set:
```python
assert set(overlay) >= {
    "startup_sequence",
    "pre_dispatch_checklist",
    "harvest_sequence",
    "subagent_model_routing",
    "preflight_discipline",
    "g5_body_line_rule",
    "new_ce_group_coupling",
    "merge_gate_checklist",   # NEW
}
```

**b.** Add a new test `test_merge_gate_checklist_rendered`:
```python
def test_merge_gate_checklist_rendered():
    ssot, ssot_path, ssot_hash = _load_ssot()
    files = gen_controller_bootstrap.build_files(ssot, "all", ssot_path, ssot_hash)
    for rel_path in (Path("codex/AGENTS.md"), Path("claude/CLAUDE.md")):
        content = files[rel_path]
        assert "Merge-Gate Checklist" in content
        assert "dismissed" in content.lower()
        assert "APPROVED" in content
```

**c.** Add a test `test_missing_merge_gate_checklist_fails_closed`:
```python
def test_missing_merge_gate_checklist_fails_closed():
    ssot, _ssot_path, _ssot_hash = _load_ssot()
    missing = copy.deepcopy(ssot)
    del missing["controller_knowledge_overlay"]["merge_gate_checklist"]
    with pytest.raises(SystemExit):
        gen_controller_bootstrap.validate_ssot(missing)
```

### Step 5 — validate

Run the test suite focused on the changed files:

```bash
cd <repo_root>
# Install validator in editable mode if not already
pip install -e validators/ --quiet

# Run just the unit test for the generator
python -m pytest validators/tests/unit/test_gen_controller_bootstrap.py -v

# Smoke-run the generator itself
python scripts/gen-controller-bootstrap.py --harness all | head -60

# Run full preflight (one pass, must be GREEN)
PATH="$PWD/validators/.venv/bin:$PATH" scripts/ce-preflight.sh \
  --base origin/main \
  --head-ref ce-344-slice2-checklist \
  --declared-work-class story
```

If ce-preflight.sh is not available directly, run:
```bash
python -m creator_engine_validator validate-pr \
  --base origin/main \
  --head-ref ce-344-slice2-checklist \
  --declared-work-class story
```

The preflight MUST be GREEN in one pass before committing. Two-strikes rule: if the
same gate fails twice, stop and report the failure to the controller rather than
continuing to iterate.

### Step 6 — carrier and changelog

**Changelog** — create `.ce/changelog/ce344-slice2-checklist.md`:
```markdown
## ce-ops#344 slice 2 — checklist-content hardening

- Extended `controller_knowledge_overlay` in SSOT JSON with `merge_gate_checklist`
  key: 5 deterministic gate-assertion items.
- Tightened `pre_dispatch_checklist` with exact artefact paths for territory-map
  inspection.
- Added verify-not-already-landed step to `pre_dispatch_checklist`.
- Hardened `validate_ssot()` to require `merge_gate_checklist`; fails closed on
  missing key.
- Extended renderer to emit "Merge-Gate Checklist" section in all harness previews.
- Added tests: `test_merge_gate_checklist_rendered` and
  `test_missing_merge_gate_checklist_fails_closed`.
```

**Carrier** — generate the PR manifest using the `carrier_gen` API (NOT by hand):

```python
from creator_engine_validator.carrier_gen import write_carriers
write_carriers(base="origin/main")
```

Or via the CLI if available:
```bash
python -m creator_engine_validator carrier-gen --base origin/main
```

The manifest slug must match the branch slug `ce344-slice2-checklist`.

**Do NOT hand-list carrier filenames.** Use the API.

### Step 7 — commit

```bash
git add docs/design/controller-bootstrap-ssot.json
git add scripts/gen-controller-bootstrap.py
git add validators/tests/unit/test_gen_controller_bootstrap.py
git add .ce/changelog/ce344-slice2-checklist.md
git add .ce/pr-manifests/ce344-slice2-checklist.md

git commit -m "feat(ce-ops#344): checklist overlay hardening — merge-gate checklist + territory precision (slice 2)"
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
is not triggered. The generator and SSOT are not part of the public CLI surface.
No README.md update is required for this slice.

---

## Stop line

Stop after: commit + SHA recorded + preflight GREEN report sent to controller.

Do NOT push to any remote.
Do NOT open a PR.
Do NOT touch any file outside the closed list.
Do NOT approve or merge anything.

Report: `READY-FOR-HARVEST` with the commit SHA and the preflight evidence (pass/fail summary).
