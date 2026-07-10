# BRIEF — dev-1 — 2026-07-08 — P1: complete .hermes → .ce/state retirement (ce-ops#507)

Role: **implementer**. NON-contained seat (self-push + self-PR). Fresh worktree off
`origin/main` (fetch first). Branch `ce-hermes-retirement`. Full egress available.
Open your own PR when preflight is green. No venv activation needed; use the installed `ce`.

## U1 — branch `ce-hermes-retirement` (work class: story)

OPERATOR MANDATE (P1, ce-ops#507, verbatim intent): "cut the crutches while we
have no active users." COMPLETE the `.hermes/` → `.ce/state` retirement. The
migration is partially done: `ce launch` state moved in ce149, and RED-G-4 doctor
guidance was improved in ce-onboard-state-path-bootstrap. What remains: `ce onboard`
still HARD-REQUIRES `.hermes/` to be gitignored as a PRECONDITION (lines 81-82 and
540 of `ce_onboard.py`); several deployed scripts and hooks still default paths into
`.hermes/`; several user-facing docs still instruct users to create the `.hermes/`
gitignore entry before running CE.

This unit completes the retirement. **Do NOT rename `templates/hermes/` or touch
v1 schema constants — those are BLOCKED by v1 coexistence doctrine (see §Governance
Ambiguities below).**

---

## Kill list — every `.hermes` hit on `origin/main`

Run `git grep -n "hermes" $(git rev-parse origin/main) -- ':!*.lock'` to verify
this list against the live tree before touching anything. Disposition for each file:

### MIGRATE — functional code, MUST change

**1. `validators/creator_engine_validator/ce_onboard.py` — CORE CHANGE**

Lines 81-82: `STATE_PATH_GUIDANCE` constant requires `.hermes/` to be gitignored
and instructs `ce init --repo-root`:
```
".hermes/ must be git-ignored before CE writes local governed state. "
"Add a .gitignore line containing `.hermes/`, run `ce init --repo-root {repo_root}`, "
```
Line 540: `_state_path_guidance()` returns `next_steps` including `"Add '.hermes/' to .gitignore"`.

Required change: `ce onboard` must check that `.ce/state` layout exists (via prior
`ce init` run) rather than requiring a `.hermes/` gitignore entry. The gitignore
entry is no longer the precondition. Updated guidance must direct users to run
`ce init --repo-root {repo_root}` to bootstrap `.ce/state/`, then re-run
`ce onboard`. Do NOT remove the gitignore check entirely — if `.hermes/` is NOT
already in `.gitignore` and an existing `.hermes/` directory is present on disk,
emit an advisory (not a hard refusal) noting that `.hermes/` remains on disk and
should stay ignored to avoid accidental commits of legacy state.

Update `validators/tests/unit/test_ce_onboard.py` and
`validators/tests/unit/test_ce_onboard_cli.py` to cover: (a) onboard succeeds with
`.ce/state` layout and no `.hermes/` gitignore entry; (b) onboard emits advisory
(not refusal) when `.hermes/` directory exists but is already gitignored;
(c) existing RED-G-4 path still produces correct guidance for the old flow.

Verify: what exactly does the RED-G-4 doctor clause check? Read the doctor check
source for RED-G-4 before editing the handler at `ce_onboard.py:595`. If RED-G-4 is
checking for `.hermes/` gitignore specifically, the clause's semantics must change
or the clause must be retired. Flag this as BLOCKED if the doctor check definition
is ambiguous.

**2. `validators/creator_engine_validator/ce_cli.py` — help-string cleanup**

These help strings are the SOURCE for `.ce/reference/cli.generated.md` (which is
auto-generated; do NOT edit the generated file directly):

- Line ~532: `--ledger-root` help: `"path to .hermes/active-work-ledger"` →
  `"path to .ce/state/active-work-ledger"`
- Line ~552: `--mcp-config` help: `"inside the repo / .hermes"` →
  `"inside the repo / .ce/state"`
- Line ~752, ~824, ~1417: `--active-work-ledger-root` help: `"path to .hermes/active-work-ledger"` →
  `"path to .ce/state/active-work-ledger"`
- Line ~903: `--packet-root` help: `"e.g. .hermes/fan-in/"` →
  `"e.g. .ce/state/fan-in/"`
- Line ~946: `--preview-root` help: `"e.g. .hermes/integration-queue/"` →
  `"e.g. .ce/state/integration-queue/"`
- Line ~1040: `--repo-root` help note about `.hermes/`: reword to `.ce/state`

After editing ce_cli.py: run `ce validate-pr` and confirm the generated CLI
reference doc regeneration is handled by the CI gate (or manually regenerate and
include in the diff). If the regeneration is a manual step, add
`.ce/reference/cli.generated.md` to the stop line and regenerate it.

**3. `deploy/dgx-runsc/run-codex-runsc.sh` — default ledger path**

Line ~297:
```bash
ledger_root="${CE_LEDGER_ROOT:-${CE_DGX_REPO}/.hermes/active-work-ledger}"
```
Change to:
```bash
ledger_root="${CE_LEDGER_ROOT:-${CE_DGX_REPO}/.ce/state/active-work-ledger}"
```

**4. `deploy/vps-runsc/run-vps-runsc.sh` — default ledger path**

Line ~394:
```bash
ledger_root="${CE_LEDGER_ROOT:-${CE_VPS_REPO}/.hermes/active-work-ledger}"
```
Change to:
```bash
ledger_root="${CE_LEDGER_ROOT:-${CE_VPS_REPO}/.ce/state/active-work-ledger}"
```

**5. `.claude/hooks/ce-hook-common.sh` — observability root**

Line ~98: `_obs_dir="$_obs_root/.hermes/cc-g-c-hook-observations"` →
`_obs_dir="$_obs_root/.ce/state/cc-g-c-hook-observations"`

Comments at lines ~86 and ~93 that reference `.hermes/` as the evidence root:
reword to `.ce/state`.

Note: this is a NON-BLOCKING hook (the comment at line 93 already says it
never blocks). The directory will be auto-created if absent. Safe to change.

**6. `.claude/hooks/ce-pretooluse.sh` — evidence root flag**

Line ~24: `--evidence-root .hermes` → `--evidence-root .ce/state`

Comment at line ~9 referencing `.hermes` as the ignored instance root: reword.

Verify first: confirm `ce doctor --evidence-root .ce/state` (or whichever
underlying check uses this flag) accepts `.ce/state` as the evidence root without
erroring. Read the flag's handler before changing. If the flag value is constrained
to a fixed set that does not include `.ce/state`, signal BLOCKED with the specific
flag name and its constraint.

**7. `.claude/hooks/ce-stop.sh` — evidence root**

Lines ~10, ~26: references to `.hermes/` as the evidence root for best-effort
observability. Reword to `.ce/state`.

---

### REWORD — docs with functional references (not historical archives)

**8. `docs/contracts/v3-naming-hygiene.md`**

This document defines the naming hygiene contract. Update to reflect the retirement
is now COMPLETE rather than in-progress. Specifically:
- Lines ~16,18: "v1 keeps `.hermes/` — frozen, retained for coexistence" — update
  to note this is the historical migration record; the retirement of v3's `.hermes/`
  hard-requirement is complete.
- Line ~31: the `.hermes/`→`.ce/` rename section — update status to reflect
  ce-hermes-retirement (this PR) completes the user-facing surface.
- Preserve the v1 coexistence statement intact.

**9. `docs/architecture/agent-interaction-model.md`**

Line ~28: "CE CLI / `.hermes/` toolchain / seat-launch substrate" →
"CE CLI / `.ce/state` toolchain / seat-launch substrate"

**10. `docs/architecture/parallel-controller-orchestration.md`**

Lines ~109, ~210: replace `.hermes/active-work-ledger/` with `.ce/state/active-work-ledger/`.

**11. `CONTRIBUTING.md`**

Lines ~95-96: "anything under `.hermes/` that is intended to be ignored, filled-in
copies of `templates/hermes/session-state/STATE.template.md`" — reword: the
`.hermes/` runtime root is legacy state kept gitignored for backward compatibility;
point to `.ce/state/` as the current instance state root.

**12. `docs/delivery/NEXT_TASK_PROTOCOL.md`**

Line ~122: "`.hermes/session-state/STATE.md` in deployed instances" → reword to
`.ce/state/session-state/STATE.md` (or remove the specific path reference if it is
no longer used).

**13. `docs/contracts/forge-claim.md`**

Line ~9: "A PCO claim today lives instance-local (`.hermes/active-work-ledger/` on
v1...)" — reword: note `.hermes/active-work-ledger/` is the v1-frozen layout; the
v3 canonical path is `.ce/state/active-work-ledger/`.

**14. `docs/decisions/0005-openbao-secret-identity-backend.md`**

Line ~63: `~/.hermes/.env` reference — reword to the current canonical location
for CE credential material (check `ce-ops` infra registry or existing docs for the
correct path; do NOT invent a path).

**15. `docs/delivery/WORKTREE_RUNTIME_PROTOCOL.md`**

Lines ~158, ~161, ~280, ~301: "No mixing of `.hermes` live state" / no-leakage
rules — reword to "no mixing of `.ce/state` live state or legacy `.hermes/`
artifacts" (the prohibition extends to both, with `.hermes/` noted as legacy).

**16. `.gitignore`**

Lines 1-5: the comment block above `.hermes/` says "`.hermes/` is instance-local
runtime/session state for a deployed Creator Engine instance." Update the comment
to note that `.hermes/` is LEGACY v1 instance state; the current canonical instance
state root is `.ce/state/` (also gitignored). KEEP the `.hermes/` ignore entry
itself — existing installs may have `.hermes/` directories on disk that must remain
untracked. Add `.ce/state/` to the gitignore if it is not already there (check
first; do not duplicate).

---

### ACCEPT — historical / archival references (no change)

These references are in historical records, ADRs, or research archives. Do NOT
modify them. A post-retirement grep for `hermes` will hit these; that is expected.

- `.ce/changelog/ce149-launcher-hermes-to-ce.md` — historical changelog
- `.ce/changelog/ce82-lane-venv-docs.md` — historical changelog
- `.ce/changelog/ce-onboard-state-path-bootstrap.md` — historical changelog
- `CHANGELOG.md` lines containing historical entries — historical log
- `docs/adr/ADR-0001-v1-baseline-and-product-form.md` — ratified ADR, frozen
- `docs/adr/ADR-0002-operator-terminology-reconciliation.md` — ratified ADR, frozen
- `docs/architecture/v3-product-brief.md` — research archive references
- `docs/architecture/v3-secure-runtime.md` — research archive references
- `docs/architecture/v3-spec.md` — research archive references
- `docs/architecture/session-status-line.md:77` — already says `.ce/state` is
  canonical; ACCEPT as already correct
- `docs/delivery/ASSIGNMENT_ENVELOPE_DRY_RUN.md` — historical dry-run exercise
- `.ce/pr-manifests/*.md` — historical PR carriers, frozen
- `.ce/reference/cli.generated.md` — auto-generated from ce_cli.py; covered
  by ce_cli.py source edits above (do not hand-edit)
- All `.ce/release-staging/*/` binary wheels — binary artifacts, no action

### TERRITORY NOTE: `docs/guide/welcome.md`

`docs/guide/welcome.md` contains a `.hermes/` gitignore instruction in its Day One
section (around line 75: "Make sure your repository ignores CE's local Hermes
state: `.hermes/`"). This path is **assigned to BRIEF_dev3_docs_cli_parity_20260708**,
which restructures welcome.md per the orientation-only rule and will remove the
Day One content block (including the `.hermes/` instruction) entirely. Do NOT touch
`docs/guide/welcome.md` in this unit. The two units must be merged in order (this
brief merges first if they run concurrently, or dev-3 rebases on top of this branch).

---

## Governance ambiguities — BLOCKED-worthy, do NOT resolve unilaterally

The following items are governance-ambiguous under the v1↔v3 coexistence doctrine
(`ce-v1-v3-coexistence-not-deletion`). Do NOT rename, delete, or schema-modify
these surfaces without explicit Operator authorization. Note them in the PR body
as product follow-up tickets:

**G-1: `templates/hermes/` directory.** These tracked templates are v1-frozen
surfaces (referenced in CONTRIBUTING.md and the delivery protocol). Renaming
`templates/hermes/` to `templates/v1/` or similar would be a v1 API break requiring
a separate ratification. OUT OF SCOPE for this unit.

**G-2: v1 schema constants in schemas (`.ce/reference/schemas.generated.md`).** The
v1 seat lifecycle record schema has `state_root: const ".hermes/"` (line ~2341),
`hermes_write_freeze` field (line ~2276), `kind: hermes-handoff` (line ~1051),
`kind: hermes-recommended-prompt` (line ~1710), and `authority_class: hermes` enum
(line ~629). These are v1-frozen schema constants. Changing them would break v1
schema validation. OUT OF SCOPE.

**G-3: `validators/examples/harness-seat-contract/valid-hermes-seat.ce.yml`.** This
example represents a hermes-harness seat with `authority_class: hermes`. Renaming
requires schema changes. OUT OF SCOPE.

**G-4: RED-G-4 doctor clause semantics.** If reading the RED-G-4 clause definition
reveals that it is hard-coded to check for `.hermes/` gitignore and the check
cannot be cleanly updated without breaking v1 doctor semantics, signal BLOCKED with
the specific clause reference rather than improvising a workaround.

**G-5: `--evidence-root .hermes` flag in ce-pretooluse.sh.** If the validator
underlying this flag only accepts `.hermes` as a valid evidence root value (not
`.ce/state`), this is a deeper schema/validator change that exceeds this unit's
scope. Signal BLOCKED with the constraint.

---

## Migration/compat note for existing installs

Before this change: `ce onboard` required `.hermes/` in `.gitignore` as a hard
PRECONDITION (RED-G-4 triggered if missing, refusing to proceed).

After this change: `ce onboard` requires `.ce/state` layout (from prior `ce init`
run) as the precondition. A missing `.hermes/` gitignore entry is NO LONGER a
hard refusal. Repos with an existing `.hermes/` directory on disk are tolerated
(the ignore entry should remain, but its absence is not a blocking error). Repos
with no `.hermes/` directory at all proceed without any `.hermes/`-related check.

Conservatively: do NOT remove backward compatibility for repos that have both
`.hermes/` gitignored AND `.ce/state/` present — that is a valid state for repos
migrating from v1 to v3.

---

## Acceptance criteria

Fresh `ce onboard --repo-root <clean-repo>` on a repo that has:
- NO `.hermes/` gitignore entry
- NO `.hermes/` directory on disk
- `.ce/state/` directory present (from prior `ce init` run)

...MUST succeed with zero `.hermes/` references in its output.

Post-PR grep for `hermes` in the repo must return ONLY:
- Historical changelog entries (`.ce/changelog/ce149-*`, `ce82-*`, etc.)
- Historical ADRs (`docs/adr/ADR-0001`, `ADR-0002`)
- Historical architecture research refs (`docs/architecture/v3-*.md`, provenance
  pointers to gitignored `.hermes/research/` archives)
- Historical dry-run exercise (`docs/delivery/ASSIGNMENT_ENVELOPE_DRY_RUN.md`)
- v1 schema constants (`schemas.generated.md` enum values, `state_root: const`)
- `templates/hermes/` directory contents (v1-frozen, out of scope)
- Historical PR carrier docs in `.ce/pr-manifests/`
- The `.gitignore` entry itself (kept for backward compat; comment updated)
- `validators/examples/harness-seat-contract/valid-hermes-seat.ce.yml` (out of scope)
- Auto-generated binary whl files (not source)

Every other hit = a gap this unit missed. Fix before pushing.

---

## Hard constraints

- Do NOT touch README.md — claimed by in-flight ce-readme-overhaul (dev-4).
- Do NOT touch `docs/guide/welcome.md` — assigned to ce-docs-cli-parity (dev-3).
- Do NOT touch version-drift gate module or its test — claimed by ce-readme-overhaul.
- Do NOT rename `templates/hermes/` or modify v1 schema constants — governance
  ambiguity G-1 through G-3.
- Preserve all v1 functionality (v1 keeps `.hermes/` frozen; v3/shared surfaces must
  not inherit the residue but v1's own checks legitimately reference it).
- No work beyond the stop line below.

---

## Standing preflight directive (ce-ops#303)

FULL `ce validate-pr` green before self-push. Fast iteration: `pytest -m "not slow"`;
full suite gates the push. If `ce validate-pr` raises a gate on a file outside your
diff, report it verbatim in the evidence section of the PR body.

---

## STOP LINE

No pushes, no PRs outside these paths:

```
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
```

Optional addition if the CLI reference doc requires manual regeneration:
```
.ce/reference/cli.generated.md
```

Carrier: slug == `ce-hermes-retirement` exactly; every changed path enumerated;
exactly ONE `- **Declared work class:** S` line. Evidence must include: (1) the
post-change `grep -rn "hermes"` output on the diff paths confirming all functional
references are gone; (2) the test matrix result showing the new onboard acceptance
criteria pass; (3) explicit enumeration of governance ambiguities noted in the PR
body as product follow-up.

PR body must list all G-1 through G-5 governance ambiguities as `PRODUCT FOLLOW-UP`
items so they are visible to product for scoping.
