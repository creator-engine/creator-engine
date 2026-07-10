# WORK CLAIM — ce-ops#295 · Annoyance→tool reflex + agent-self-authored AGENTS.md

**Seat:** dev-1 (Hetzner VPS, non-contained, self-push capable).
**Role:** implementer.
**This is a BOUNDED slice — build only what is described here.**

---

## Branch

```
git fetch origin && git checkout -b ce-295-annoyance-tool-reflex origin/main
```

---

## Ticket + Embedded Context

**Parent lane:** ce-ops#295 — Annoyance→tool reflex + agent-self-authored AGENTS.md (Wave 3.1).

**You cannot read ce-ops, so all context is embedded here.**

### Why this work exists

Peter Steinberger's #1 habit is "felt friction → build the tool immediately."
CE's controller currently absorbs two recurring costs silently:

1. **Annoyance→tool is undocumented.** Every time a controller hits recurring toil
   (a manual PR body edit, a repeated dispatch incantation, a step that fires three
   times a week), there is no governing playbook entry that says "stop, file a
   ticket, build the tool." The habit exists in practice but is nowhere codified.
   Result: each controller session rediscovers the posture from scratch.

2. **AGENTS.md is an empty stub.** The root `AGENTS.md` contains only a 4-line
   SPECKIT comment. Every session startup and every dispatch brief must repeat the
   same policy bootstraps: "read `.claude/agents/` for role definitions; consult
   `playbooks/controller/briefs/dispatch.md` for dispatch discipline; workers must
   never approve, merge, or enqueue." Because this is not in AGENTS.md, it is
   manual controller toil on every brief.

The fix is two files — one new playbook brief, one real AGENTS.md — authored by
this agent (not hand-written by the controller), demonstrating the agent-self-authored
AGENTS.md capability that is the stated goal of ce-ops#295.

### DoD / Stop-Line

(a) Annoyance→tool reflex codified as a playbook brief:
    `playbooks/controller/briefs/annoyance-to-tool.md`
    (adds a stage to `playbooks/controller/workflow.ce.yml` and a `briefs/` entry;
    the controller playbook index does NOT need updating — the stage references the
    brief, and the brief file must exist).

(b) Root `AGENTS.md` authored by this agent (not a human) with a concrete session-
    bootstrap block: role pointer, dispatch discipline pointer, and the three hard-stop
    rules that currently repeat in every brief. The commit message must record
    "agent-authored" to satisfy the ce-ops#295 agent-self-authoring requirement.

(c) Carrier, changelog, and declared-work-class body line in place.
    `ce validate-pr` GREEN in one pass.

---

## Role

Implementer. Self-push capable (dev-1 can `git push` and open a PR via `gh pr create`).
Do NOT approve, merge, or enqueue the PR — controller holds the merge gate.

---

## Allowed Paths (CLOSED LIST — nothing else)

```
AGENTS.md
playbooks/controller/briefs/annoyance-to-tool.md
playbooks/controller/workflow.ce.yml
.ce/pr-manifests/ce-295-annoyance-tool-reflex.md
.ce/changelog/ce-295-annoyance-tool-reflex.md
```

**EXCLUDED — do NOT touch:**
- `tools/egress-broker/ce_egress_self_review_broker.py` (dev-3 is editing this)
- `tools/egress-broker/egress_broker/orchestrator.py`
- `.github/workflows/validate.yml` (dev-4 is editing this)
- `validators/creator_engine_validator/forge/` (PR #610 is live here)
- `ce_cli.py`
- `playbooks/README.md` (adding a brief to an existing playbook does NOT require
  index update — the `ce_playbook_format` validator only checks that each
  `workflow.ce.yml` stage references an existing brief file, not that every
  brief file is a stage)
- Any other file not in the closed list above

---

## Required Work — Concrete and Specific

### 1. `playbooks/controller/briefs/annoyance-to-tool.md` (NEW)

Create this file. It is a controller playbook brief codifying the annoyance→tool
reflex as a governed action. Required content (write it, do not just summarize):

```markdown
# Annoyance → Tool

When the controller encounters recurring toil — a step that fires more than once
per week, a manual edit that a seat always requires, or a check that is done by
reading a doc and re-typing the same output — stop and follow this loop:

1. **Name the annoyance.** State what action you are doing manually and how often.
2. **File a ticket.** Open a ce-ops issue with title "Annoyance: <short name>".
   Label it `toil`. Link to the session or PR where you first noticed it.
3. **Scope the tool.** In the ticket, describe the minimal automated form: a
   playbook brief, a `ce` command, a skill, or a validator check. Keep it bounded
   (tiny or story class).
4. **Dispatch the implementation.** Route the ticket to the correct worker role
   (implementer for code, architect_research for scoping). Do not inline the
   implementation in the controller session.
5. **Verify the loop closed.** After the tool lands, confirm the manual step is
   gone. If the same annoyance recurs after the tool lands, it is a regression
   ticket.

## Examples of Annoyances That Become Tools

- Manual PR body edit to add `- **Declared work class:** story` → became the G5
  body-line auto-emit (ce-ops#340, W5 slice of ce-ops#295).
- Repeating dispatch guard rails in every brief → became a populated `AGENTS.md`
  (ce-ops#295 Wave 3.1).
- Checking whether a PR is already landed before dispatch → became the
  `ce-verify-not-already-landed` memory doctrine and a pre-dispatch checklist.

## Halt Conditions

- Do not file an annoyance ticket during a time-critical merge window. Note it in
  memory and file it at the next natural break.
- Do not scope the tool as an epic. If the fix is larger than a story, break it
  into slices and file each slice.
```

### 2. `playbooks/controller/workflow.ce.yml` (MODIFY)

Add the `annoyance-to-tool` stage and a matching gate to the existing file.
Read the current file first (it is at `playbooks/controller/workflow.ce.yml`).
Add:

Under `gates:`, append:
```yaml
  - id: annoyance-filed
    type: dor
    description: "Recurring toil is named, ticketed, and dispatched before continuing."
    required: false
```

Under `stages:`, append:
```yaml
  - id: annoyance-to-tool
    title: "Annoyance → Tool"
    brief: briefs/annoyance-to-tool.md
    dispatch_target: controller-seat
    gates: [annoyance-filed]
```

The validator (`ce_playbook_format`) checks that a stage's `brief:` field points
to an existing `briefs/<stage-id>.md` file. Since you are creating both the stage
entry AND the brief file, both sides must be present for the validator to pass.

### 3. `AGENTS.md` (MODIFY — agent-authored)

Replace the current SPECKIT stub (the 4 lines starting with `<!-- SPECKIT START -->`)
with a real session-bootstrap policy block. This is the agent-self-authored change
required by ce-ops#295. Write it yourself — do not ask the controller to hand-write it.

Required content:

```markdown
# Creator Engine — Agent Bootstrap Policy

Any agent (controller, foreman, or worker) opening a session in this repository
MUST read these pointers before doing any substantive work.

## Role Definitions

Worker role policies are in `.claude/agents/`:
- `architect_research.md` — read-only research; returns findings only.
- `implementer.md` — write-capable; one worktree; scoped PAT only.
- `verification.md` — read-only test execution; no egress by default.
- `reviewer.md` — read-only review; returns verdict for controller submission.

Controllers MUST spawn one of these roles when dispatching workers.
Controllers MUST NOT improvise ad hoc roles or broaden a role's boundaries.

## Dispatch Discipline

Before dispatching any worker:
1. Read `playbooks/controller/briefs/dispatch.md` — the SSOT for what a brief must name.
2. Check the in-flight territory map (memory: `ce-dispatch-territory-map-before-dispatch`).
3. Write the seed brief to `.ce/briefs/<slug>.md`, compute `sha256sum`, and send
   the worker the file pointer plus hash — never inline the brief.
4. Record the work claim before the worker starts.

## Hard-Stop Rules (applies to ALL agents)

- NEVER approve a pull request.
- NEVER merge a pull request.
- NEVER self-merge or enqueue without controller confirmation.
- NEVER edit outside the allocated worktree or assigned task scope.
- NEVER use controller-key material, broad host credentials, or SSH keys from
  a worker role.

If a task requires authority outside these limits, STOP and report the missing
authority to the controller. Do not expand scope.

## Where to Find More

- Spec 005 §d.2 (worker isolation runtime): `specs/005-pco-parallel-controller-orchestration/worker-isolation-runtime.md`
- Playbooks index: `playbooks/README.md`
- Skills index: `.claude/skills/`
```

The commit for this file MUST include the phrase "agent-authored AGENTS.md" in the
commit message to satisfy the ce-ops#295 agent-self-authoring DoD.

### 4. `.ce/pr-manifests/ce-295-annoyance-tool-reflex.md` (NEW — REQUIRED)

Generate this carrier via:
```
python -c "
from creator_engine_validator.checks.carrier_gen import write_carriers
import subprocess
base = subprocess.check_output(['git', 'merge-base', 'HEAD', 'origin/main']).strip().decode()
write_carriers(base=base)
"
```

If `carrier_gen.write_carriers` is not importable from that path, locate the
carrier_gen module with `find . -name 'carrier_gen.py'` and adjust the import.
Do NOT hand-edit the `AUTHORIZED_PATHS_SHA256` or `AUTHORIZED_PATHS_COUNT` — let
the API compute them.

The carrier must list exactly these 5 paths (and itself):
```
.ce/changelog/ce-295-annoyance-tool-reflex.md
.ce/pr-manifests/ce-295-annoyance-tool-reflex.md
AGENTS.md
playbooks/controller/briefs/annoyance-to-tool.md
playbooks/controller/workflow.ce.yml
```

The carrier must include exactly one line:
```
- **Declared work class:** tiny
```

(5 files including the carrier itself; all are docs/config; this is a `tiny`-class
change by the work-sizing floor.)

### 5. `.ce/changelog/ce-295-annoyance-tool-reflex.md` (NEW — REQUIRED)

```markdown
---
slug: ce-295-annoyance-tool-reflex
date: 2026-06-28
kind: added
scope: controller playbook / session bootstrap
issue: ce-ops#295
---

**Codify the annoyance→tool reflex and replace the empty AGENTS.md stub with an
agent-authored session-bootstrap policy block.**

- Added `playbooks/controller/briefs/annoyance-to-tool.md`: controller runbook
  entry that governs the loop from felt friction to filed ticket to dispatched tool.
- Added `annoyance-to-tool` stage + `annoyance-filed` gate to
  `playbooks/controller/workflow.ce.yml`.
- Replaced the SPECKIT stub in `AGENTS.md` with a real session-bootstrap policy
  block covering role definitions, dispatch discipline, and hard-stop rules —
  authored by this agent (ce-ops#295 agent-self-authoring DoD).
- Declared work class: tiny.
```

---

## Expected Evidence (return ALL of the following)

1. Full output of:
   ```
   ce validate-pr --base origin/main --head-ref ce-295-annoyance-tool-reflex
   ```
   Must show GREEN / all PASS, including `ce_playbook_format` (stage references
   existing brief), `path_manifest_fidelity` (carrier matches diff), and
   `work_sizing_floor` (tiny declared and satisfied).

2. `git log --oneline origin/main..HEAD` — commit list.

3. `git diff --stat origin/main..HEAD` — files changed and counts.

4. Confirmation that the `annoyance-to-tool` stage in `workflow.ce.yml` references
   `briefs/annoyance-to-tool.md` and that file exists.

5. Confirmation that `AGENTS.md` no longer contains only the SPECKIT stub (show
   first 5 lines of the new file).

6. PR number after `gh pr create` referencing ce-ops#295, with body containing:
   ```
   - **Declared work class:** tiny
   ```

---

## Preflight Command

```bash
ce validate-pr --base origin/main --head-ref ce-295-annoyance-tool-reflex
```

Alternative form if `ce` is not on PATH:
```bash
python -m creator_engine_validator.ce_cli validate-pr \
  --repo-root . \
  --base origin/main \
  --head-ref ce-295-annoyance-tool-reflex
```

Use `ce validate-pr`, NOT raw `pytest`. The host `/tmp/.git` false-fail trap means
raw pytest can pass while `ce validate-pr` fails (it runs in a hermetic tempdir
worktree with `TMPDIR=/var/tmp`).

---

## PR Body Template

When opening the PR, use this body (fill `<SHA>` and adjust as needed):

```
feat(ce-ops#295): annoyance→tool reflex + agent-self-authored AGENTS.md

Codifies the annoyance→tool controller habit as a governed playbook brief
(`playbooks/controller/briefs/annoyance-to-tool.md`) and replaces the empty
AGENTS.md stub with an agent-authored session-bootstrap policy block covering
role definitions, dispatch discipline, and hard-stop rules.

References ce-ops#295.

- **Declared work class:** tiny
```

---

## Stop Line

Stop and report to the controller (do NOT proceed or expand scope) if:

- You need to modify a file NOT in the closed allowed-paths list above.
- `ce validate-pr` is RED on `ce_playbook_format` and the fix requires changing
  a file outside the allowed list (e.g. `playbooks/README.md` — if this check
  fails, report the exact error; do NOT add a playbook index entry without
  controller authorization, because the `ce_playbook_format` index check only
  fires when a NEW playbook directory is added, not for a new stage in an
  existing playbook).
- `ce validate-pr` is RED on any other gate and the fix would touch an excluded
  path.
- The `workflow.ce.yml` schema rejects the new stage or gate structure.

---

## Hard Rules

1. Run `ce validate-pr` GREEN before any push.
2. PR body MUST carry exactly `- **Declared work class:** tiny`.
3. Do NOT push until `ce validate-pr` is GREEN.
4. Do NOT approve, merge, or enqueue your own PR.
5. Do NOT touch files outside the allowed path list.
6. Commit message for the AGENTS.md change MUST include "agent-authored AGENTS.md".
7. After push + PR open, report READY-TO-PUSH with commit SHA + preflight result.
   The controller confirms before any merge action.
