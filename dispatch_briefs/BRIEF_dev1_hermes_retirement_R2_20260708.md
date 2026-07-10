# BRIEF — dev-1 — 2026-07-08 — P1: .hermes → .ce/state retirement RESUME R2 (ce-ops#507)

**PRECONDITION (dispatch blocker):** Do NOT begin work until `ce-readme-overhaul` has
merged into `origin/main`. Before starting, run:
```bash
git fetch origin
git log origin/main --oneline | head -5
```
Confirm the README overhaul commit appears. The README unit holds the brain ledger tail
(its merge adds the assertion that brings the active count to 97); brain-touching units
serialize on the ledger head. If the README PR is not yet merged, set this brief to
BLOCKED and stop.

---

Role: **implementer**. SELF-PUSH seat (dev-1 is non-contained): on green preflight, push
branch `ce-hermes-retirement` and open the PR yourself — **NOT a draft** (the born-draft
template defect stalled #905; open ready-for-review). Signal READY with the PR number.
No venv activation needed; use the
installed `ce`. Self-contained brief: do not attempt to read ce-ops issues.

## RESUME STATE

dev-1 parked WIP at commit `01bb16fa` on branch `ce-hermes-retirement`. The v1 kill-list
items **1–16 are DONE** and committed. Completed scope:

| Item | File |
|------|------|
| 1 | `validators/creator_engine_validator/ce_onboard.py` |
| 2 | `validators/creator_engine_validator/ce_cli.py` |
| 3 | `deploy/dgx-runsc/run-codex-runsc.sh` |
| 4 | `deploy/vps-runsc/run-vps-runsc.sh` |
| 5 | `.claude/hooks/ce-hook-common.sh` |
| 6 | `.claude/hooks/ce-pretooluse.sh` |
| 7 | `.claude/hooks/ce-stop.sh` |
| 8 | `docs/contracts/v3-naming-hygiene.md` |
| 9 | `docs/architecture/agent-interaction-model.md` |
| 10 | `docs/architecture/parallel-controller-orchestration.md` |
| 11 | `CONTRIBUTING.md` |
| 12 | `docs/delivery/NEXT_TASK_PROTOCOL.md` |
| 13 | `docs/contracts/forge-claim.md` |
| 14 | `docs/decisions/0005-openbao-secret-identity-backend.md` |
| 15 | `docs/delivery/WORKTREE_RUNTIME_PROTOCOL.md` |
| 16 | `.gitignore` |

**First action — fetch and rebase onto post-merge main:**
```bash
git fetch origin
git checkout ce-hermes-retirement
git rebase origin/main
```

Rebase conflict guidance: the README PR's merge touches `.ce/brain/assertions.yaml` (it
appends a new assertion, bringing the active count from 96 to 97). If there is a conflict
on that file, accept origin/main's version of the file header and existing records as the
base, then re-apply any local changes on top. Do NOT discard the README PR's assertion
record. For all other conflicts arising from unrelated main-branch churn: take origin/main's
version of any file outside the items-1–16 scope; take your version for items-1–16 files.

After a clean rebase, confirm the ledger baseline:
```bash
grep -c "status: active" .ce/brain/assertions.yaml
```
This MUST return **97**. If it returns 96 or lower, the README PR has not merged yet —
stop, signal BLOCKED.

---

## Remaining work — three tasks

### R-A: `.ce/brain/assertions.yaml` — append hermes-retirement assertions

The hermes-retirement changes committed in the parked WIP (items 1–16) need brain-assertion
attestations recording the governance decisions. Append new records to
`.ce/brain/assertions.yaml` following the hash-chained ledger format.

The ledger lives at `.ce/brain/assertions.yaml`. Each new record must:
- Have `kind: brain-assertion` and `record_type: brain_assertion`
- Have a unique `id` matching `^brain-assertion-[a-z0-9][a-z0-9-]{3,96}$`; use the
  pattern `brain-assertion-hermes-retirement-<slug>` where slug describes the decision
- Have `status: active`
- Have `sequence` = (previous record's sequence + 1), incremented per record
- Have `prev_hash` = `content_hash` of the immediately preceding record
- Have `schema_version: '1'`
- Have `scope: global` and `type: decision` (or `convention` for naming conventions)
- Have `verification_method: {type: manual-attested}` — these are governance decisions,
  not probe-verifiable artifacts
- Have a `claim` with `subject`, `predicate`, `object` fields describing the decision
- Have a `statement` field (human-readable one-liner)
- Have a `content_hash` computed by the canonical algorithm:
  `canonical_content_hash(record)` from `brain_runtime.runtime_evidence_spine`

Use `ce brain assert` if the CLI surface supports it, or call
`brain_runtime.assert_claim(...)` programmatically, or append records manually with the
correct hash chain. Verify the ledger parses cleanly after each append:
```bash
ce brain verify --ledger .ce/brain/assertions.yaml
```

Required assertions — at minimum one per logical decision boundary:

1. **`brain-assertion-hermes-retirement-onboard-precondition`**
   Claim: `ce onboard` requires `.ce/state` layout (from prior `ce init` run) as the hard
   precondition; `.hermes/` gitignore entry is no longer a hard PRECONDITION for onboard.

2. **`brain-assertion-hermes-retirement-hermes-check-advisory`**
   Claim: `.hermes/` directory presence without a gitignore entry is demoted to an
   advisory-only warning in `ce onboard`; it is not a blocking refusal.

3. **`brain-assertion-hermes-retirement-launcher-ledger-path`**
   Claim: `run-codex-runsc.sh` and `run-vps-runsc.sh` default ledger path changed from
   `.hermes/active-work-ledger` to `.ce/state/active-work-ledger`.

4. **`brain-assertion-hermes-retirement-hook-evidence-root`**
   Claim: `ce-hook-common.sh`, `ce-pretooluse.sh`, and `ce-stop.sh` reference
   `.ce/state` as the CE evidence root (retired `.hermes/`).

5. **`brain-assertion-hermes-retirement-docs-updated`**
   Claim: user-facing v3 docs (`v3-naming-hygiene.md`, `agent-interaction-model.md`,
   `parallel-controller-orchestration.md`, `CONTRIBUTING.md`, `NEXT_TASK_PROTOCOL.md`,
   `forge-claim.md`, `0005-openbao-secret-identity-backend.md`,
   `WORKTREE_RUNTIME_PROTOCOL.md`) updated; `.hermes/` references demoted to legacy /
   advisory; `.ce/state/` is canonical.

6. **`brain-assertion-hermes-retirement-gitignore-annotation`**
   Claim: `.gitignore` comment for `.hermes/` entry updated to note legacy v1 status;
   `.ce/state/` entry confirmed present (added if absent).

If you discover additional distinct decision boundaries during the work (e.g., a
RED-G-4 clause change that needed its own record), add an assertion for it. More
assertions is better than fewer — n must account for every record you append.

**Record n = the count of new `status: active` records you append.** Write n down before
proceeding to R-B.

### R-B: Brain count ratchet verification — 97 + n

After R-A completes and `ce brain verify` passes:

```bash
grep -c "status: active" .ce/brain/assertions.yaml
```

The result MUST equal `97 + n` where n is the count of assertions you appended in R-A.
If it does not match, you miscounted or a supersession changed the active total — recount
and reconcile before committing.

The ratchet IS the active count in the authoritative ledger — no separate constant needs
updating. The gate will verify the ledger is valid and all active assertions pass their
verification method. `ce brain verify` (or `ce validate-pr`) is the gate.

### R-C: Test expectation updates — `test_dgx_runsc` + `test_vps_runsc_launcher`

Kill-list items 3 and 4 changed the default ledger paths in the launcher scripts from
`.hermes/active-work-ledger` to `.ce/state/active-work-ledger`. Two test files
hard-code the old paths in module-level constants and expected-output strings. Update
both files before running the suite.

**File 1: `validators/tests/unit/test_dgx_runsc.py`**

Line 23 — `HOOK_COMMAND` module-level constant (the default hook command string that the
script embeds in the generated codex config when no explicit ledger root is provided):
```python
# BEFORE:
"CE_LEDGER_ROOT=/workspace/creator-engine/.hermes/active-work-ledger "
# AFTER:
"CE_LEDGER_ROOT=/workspace/creator-engine/.ce/state/active-work-ledger "
```

Lines 387–388 — local fixture variables in
`test_codex_config_embeds_container_visible_governance_refs`:
```python
# BEFORE:
host_ledger = "/repo/creator-engine/.hermes/active-work-ledger"
host_ref = "/repo/creator-engine/.hermes/reviewer-authority.ce.yml"
# AFTER:
host_ledger = "/repo/creator-engine/.ce/state/active-work-ledger"
host_ref = "/repo/creator-engine/.ce/state/reviewer-authority.ce.yml"
```

Lines 400–401 — expected-output substring in the same test:
```python
# BEFORE:
"CE_LEDGER_ROOT=/workspace/creator-engine/.hermes/active-work-ledger "
"CE_REVIEWER_AUTHORITY_REF=/workspace/creator-engine/.hermes/reviewer-authority.ce.yml "
# AFTER:
"CE_LEDGER_ROOT=/workspace/creator-engine/.ce/state/active-work-ledger "
"CE_REVIEWER_AUTHORITY_REF=/workspace/creator-engine/.ce/state/reviewer-authority.ce.yml "
```

After editing, scan the whole file for any remaining `.hermes/` hits:
```bash
grep -n "hermes" validators/tests/unit/test_dgx_runsc.py
```
There must be zero hits after your edits.

**File 2: `validators/tests/unit/test_vps_runsc_launcher.py`**

Line 21 — `HOOK_COMMAND` module-level constant:
```python
# BEFORE:
"CE_LEDGER_ROOT=/workspace/creator-engine/.hermes/active-work-ledger "
# AFTER:
"CE_LEDGER_ROOT=/workspace/creator-engine/.ce/state/active-work-ledger "
```

Lines 269–270 — local fixture variables in
`test_codex_config_embeds_container_visible_governance_refs`:
```python
# BEFORE:
host_ledger = "/repo/creator-engine/.hermes/active-work-ledger"
host_ref = "/repo/creator-engine/.hermes/reviewer-authority.ce.yml"
# AFTER:
host_ledger = "/repo/creator-engine/.ce/state/active-work-ledger"
host_ref = "/repo/creator-engine/.ce/state/reviewer-authority.ce.yml"
```

Lines 282–283 — expected-output substring in the same test:
```python
# BEFORE:
"CE_LEDGER_ROOT=/workspace/creator-engine/.hermes/active-work-ledger "
"CE_REVIEWER_AUTHORITY_REF=/workspace/creator-engine/.hermes/reviewer-authority.ce.yml "
# AFTER:
"CE_LEDGER_ROOT=/workspace/creator-engine/.ce/state/active-work-ledger "
"CE_REVIEWER_AUTHORITY_REF=/workspace/creator-engine/.ce/state/reviewer-authority.ce.yml "
```

After editing, scan the whole file:
```bash
grep -n "hermes" validators/tests/unit/test_vps_runsc_launcher.py
```
Zero hits required.

Verify both test files pass:
```bash
pytest validators/tests/unit/test_dgx_runsc.py \
       validators/tests/unit/test_vps_runsc_launcher.py -v
```

---

## PRE-AUTHORIZED GATES

The following gates are fully IN SCOPE and pre-authorized. Do NOT stop-line at any of
them for controller approval — proceed through them without pause:

| Gate / question | Pre-authorization |
|-----------------|-------------------|
| Launcher-config test expectation updates (`test_dgx_runsc.py`, `test_vps_runsc_launcher.py`) | IN SCOPE — R-C above |
| Brain ratchet bump: active count 97 → 97+n | IN SCOPE — R-B above |
| Brain-ledger supersession append (superseding stale active assertions) | IN SCOPE — see below |
| New `brain-assertion-hermes-retirement-*` assertion IDs in `.ce/brain/assertions.yaml` | IN SCOPE — R-A above |
| `manual-attested` verification_method for governance-decision assertions | IN SCOPE — R-A above |
| Appending more than the six suggested assertions if additional decision boundaries found | IN SCOPE — use judgment |

**Brain-ledger supersession pre-authorization:** If, while running `ce brain verify` or
`ce validate-pr`, you discover that an existing ACTIVE assertion is now stale or directly
contradicted by the hermes-retirement changes (e.g., a claim that `.hermes/` is the v3
evidence root), you MUST supersede it per the brain_runtime protocol rather than leaving
the ledger inconsistent:
1. Set the old record's `status: superseded` and add `superseded_by: <new-assertion-id>`
   — recalculate its `content_hash` after the status field change
2. Append the new assertion record that replaces it
3. Adjust n accordingly (only count new ACTIVE records in R-B)
This is pre-authorized. Do not skip supersession to avoid touching the ledger.

BLOCKED-eligible — stop and write `.ce/wt-hermes-r2/BLOCKED` for:
- Any G-1 through G-5 governance ambiguity (see §Governance Ambiguities below)
- Any `hermes` reference discovered during preflight in a file outside the STOP LINE
  that is not on the ACCEPT list from v1 (historical changelogs, ADRs, v1 schema
  constants, `templates/hermes/`, `.gitignore` entry itself, `valid-hermes-seat.ce.yml`)
- Any rebase conflict not resolvable by "take origin/main's version for non-items-1-16
  files; take our version for items-1-16 files"
- Any validator gate that requires touching a file outside the STOP LINE

---

## U1 scope reference (unchanged from v1)

Branch: `ce-hermes-retirement`. Work class: story (S). This unit completes the
`.hermes/` → `.ce/state` retirement. OPERATOR MANDATE (P1, ce-ops#507, verbatim intent):
"cut the crutches while we have no active users."

---

## Governance ambiguities — BLOCKED-worthy, carry verbatim from v1

Do NOT rename, delete, or schema-modify the following. Note them in the PR body as
product follow-up tickets.

**G-1: `templates/hermes/` directory.** v1-frozen surface. Renaming requires a
separate ratification. OUT OF SCOPE.

**G-2: v1 schema constants in `schemas.generated.md`.** The v1 schema has
`state_root: const ".hermes/"`, `hermes_write_freeze` field, `kind: hermes-handoff`,
`kind: hermes-recommended-prompt`, `authority_class: hermes` enum. v1-frozen. OUT OF SCOPE.

**G-3: `validators/examples/harness-seat-contract/valid-hermes-seat.ce.yml`.** This
example's `authority_class: hermes` is v1-frozen. OUT OF SCOPE.

**G-4: RED-G-4 doctor clause semantics.** If reading the RED-G-4 clause definition
reveals it is hard-coded to check for `.hermes/` gitignore and cannot be updated without
breaking v1 doctor semantics, signal BLOCKED with the specific clause reference.

**G-5: `--evidence-root .hermes` flag in `ce-pretooluse.sh`.** If the validator
underlying this flag only accepts `.hermes` as a valid evidence root value (not
`.ce/state`), signal BLOCKED with the constraint.

---

## Migration/compat note (carried from v1)

Before: `ce onboard` required `.hermes/` in `.gitignore` as a hard PRECONDITION
(RED-G-4 triggered if missing, refusing to proceed).

After: `ce onboard` requires `.ce/state` layout (from prior `ce init` run) as the
precondition. A missing `.hermes/` gitignore entry is NO LONGER a hard refusal. Repos
with an existing `.hermes/` directory on disk are tolerated (the ignore entry should
remain, but its absence is not blocking). Both `.hermes/` gitignored AND `.ce/state/`
present is a valid state for repos migrating from v1 to v3 — do NOT break it.

---

## Acceptance criteria

The R2 unit is complete when ALL of the following hold:

1. `git rebase origin/main` completed cleanly on `ce-hermes-retirement`.
2. `grep -c "status: active" .ce/brain/assertions.yaml` returns **97+n** (n >= 6).
3. `ce brain verify --ledger .ce/brain/assertions.yaml` exits 0.
4. `grep -n "hermes" validators/tests/unit/test_dgx_runsc.py` returns zero hits.
5. `grep -n "hermes" validators/tests/unit/test_vps_runsc_launcher.py` returns zero hits.
6. `pytest validators/tests/unit/test_dgx_runsc.py validators/tests/unit/test_vps_runsc_launcher.py -v` passes.
7. Full `ce validate-pr` green on the working tree.
8. Signal file `.ce/wt-hermes-r2/READY` exists with the READY payload (see below).

Post-rebase grep across the full diff must return `.hermes/` ONLY in:
- Historical changelog entries (`.ce/changelog/ce149-*`, `ce82-*`, etc.)
- Historical ADRs (`docs/adr/ADR-0001`, `ADR-0002`)
- Historical architecture research refs (`docs/architecture/v3-*.md`)
- Historical dry-run exercise (`docs/delivery/ASSIGNMENT_ENVELOPE_DRY_RUN.md`)
- v1 schema constants (`schemas.generated.md` enum values, `state_root: const`)
- `templates/hermes/` directory contents (v1-frozen, out of scope)
- Historical PR carrier docs in `.ce/pr-manifests/` (historical, frozen)
- The `.gitignore` entry itself (kept for backward compat; comment updated)
- `validators/examples/harness-seat-contract/valid-hermes-seat.ce.yml` (out of scope)
- Auto-generated binary `.whl` files (not source)

Every other hit = a gap. Fix before committing.

---

## Hard constraints

- Do NOT touch `README.md` — claimed by ce-readme-overhaul.
- Do NOT touch `docs/guide/welcome.md` — assigned to ce-docs-cli-parity (dev-3).
- Do NOT touch version-drift gate module or its test — claimed by ce-readme-overhaul.
- Do NOT rename `templates/hermes/` or modify v1 schema constants (G-1 through G-3).
- Preserve all v1 functionality (v1 keeps `.hermes/` frozen; v3/shared surfaces must
  not inherit the residue but v1's own checks legitimately reference it).
- No pushes, no PRs, no work beyond the STOP LINE below.

---

## Standing preflight directive (ce-ops#303)

Full `ce validate-pr` green before signaling READY. Fast iteration:
`pytest -m "not slow"`; full suite + validate-pr gates the final signal.

If `ce validate-pr` raises a gate on a file OUTSIDE your diff, do NOT touch that file
to silence it. Report the gate verbatim in the READY signal file under `GATE_NOISE`.

---

## STOP LINE

No pushes, no PRs, no edits outside these paths:

```
# Items 1–16 (already committed at 01bb16fa — do NOT re-edit unless fixing rebase
# conflicts; if a rebase conflict forces a re-edit, note it in the READY signal):
validators/creator_engine_validator/ce_onboard.py
validators/creator_engine_validator/ce_cli.py
validators/tests/unit/test_ce_onboard.py
validators/tests/unit/test_ce_onboard_cli.py
deploy/dgx-runsc/run-codex-runsc.sh
deploy/vps-runsc/run-vps-runsc.sh
.claude/hooks/ce-hook-common.sh
.claude/hooks/ce-pretooluse.sh
.claude/hooks/ce-stop.sh
docs/contracts/v3-naming-hygiene.md
docs/architecture/agent-interaction-model.md
docs/architecture/parallel-controller-orchestration.md
CONTRIBUTING.md
docs/delivery/NEXT_TASK_PROTOCOL.md
docs/contracts/forge-claim.md
docs/decisions/0005-openbao-secret-identity-backend.md
docs/delivery/WORKTREE_RUNTIME_PROTOCOL.md
.gitignore
.ce/changelog/ce-hermes-retirement.md
.ce/pr-manifests/ce-hermes-retirement.md

# R2 additions (new work in this unit):
.ce/brain/assertions.yaml
validators/tests/unit/test_dgx_runsc.py
validators/tests/unit/test_vps_runsc_launcher.py
.ce/wt-hermes-r2/READY
.ce/wt-hermes-r2/BLOCKED
```

Optional addition if the CLI reference doc requires manual regeneration:
```
.ce/reference/cli.generated.md
```

Carrier: slug == `ce-hermes-retirement` exactly (same as v1). Update the path manifest
in `.ce/pr-manifests/ce-hermes-retirement.md` to include R2 additions:
`.ce/brain/assertions.yaml`, `validators/tests/unit/test_dgx_runsc.py`,
`validators/tests/unit/test_vps_runsc_launcher.py`. Exactly ONE
`- **Declared work class:** S` line.

PR body evidence must include:
1. `grep -c "status: active" .ce/brain/assertions.yaml` output (must be 97+n)
2. The assertion IDs appended (list all `brain-assertion-hermes-retirement-*` IDs)
3. `pytest validators/tests/unit/test_dgx_runsc.py validators/tests/unit/test_vps_runsc_launcher.py` result
4. G-1 through G-5 noted as PRODUCT FOLLOW-UP items (do not resolve)

---

## READY / BLOCKED signals

**When DONE — write `.ce/wt-hermes-r2/READY`:**
```
STATUS: READY
COMMIT: <HEAD SHA after final commit on ce-hermes-retirement>
ACTIVE_ASSERTIONS: <97+n>
N_APPENDED: <n>
LEDGER_HEAD_SEQUENCE: <sequence number of final appended record>
LEDGER_HEAD_HASH: <content_hash of final ledger record>
TEST_DGX_HERMES_HITS: 0
TEST_VPS_HERMES_HITS: 0
VALIDATE_PR: GREEN
GATE_NOISE: <"none" or verbatim text of any external gate raised by validate-pr>
```
Commit the signal file as the FINAL commit on the branch before stopping.

**When BLOCKED — write `.ce/wt-hermes-r2/BLOCKED` then stop immediately:**
```
STATUS: BLOCKED
BLOCKER: <one-sentence description>
GATE: <G-1|G-2|G-3|G-4|G-5|REBASE|PRECONDITION|OTHER>
CONTEXT: <full context needed for controller resolution, including file/line/error>
```
Do NOT commit partial R-A/R-B/R-C work if blocked on an unresolved ambiguity.
Commit completed sub-tasks (e.g., if R-C is done but R-A is blocked, commit R-C) so
the orchestrator can harvest partial progress.
