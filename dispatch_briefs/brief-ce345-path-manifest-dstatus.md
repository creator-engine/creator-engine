# Brief: ce-ops#345 — path-manifest gate counts D-status carriers → blocks orphan cleanup

**Seat**: dev-1 (VPS, non-contained codex, self-push capable)
**Role**: implementer
**Ticket**: ce-ops#345
**Branch**: `ce-345-path-manifest-dstatus` (create from origin/main; dev-1 CAN fetch)

```
git checkout -b ce-345-path-manifest-dstatus origin/main
```

---

## Ticket context (embedded — no egress required)

The per-PR carrier gate (`_run_with_base_per_pr` in
`validators/creator_engine_validator/checks/path_manifest_fidelity.py`)
builds its carrier count from ALL paths touched under `.ce/pr-manifests/`
in the `git diff --name-status base..HEAD`, regardless of git status.
This means a PR that DELETES an orphan carrier (status `D`) and ADDS its
own carrier (status `A`) produces `carrier_paths` with 2 entries and
hard-fails with `path_manifest_multiple_carriers`.

**Root cause — exact line (L740):**

```python
carrier_paths = sorted(p for p in changed if p.startswith(prefix))
```

`changed` is the full set of all diff paths (A + M + D).  The multiple-
carrier guard at L762 fires on `len(carrier_paths) > 1` before any
status check, so a legitimately deleted orphan is counted as a second
carrier.

**Required fix:**  Exclude D-status paths from `carrier_paths`.  Only
`A` and `M` carriers count as "the PR's carrier."  Deleted carriers are
housekeeping, not a new or modified PR-ownership claim.

**Orphan on main:**  `ce291a-automerge-classifier-dryrun.md` was written
during the ce-ops#291 W1a build but PR #610 landed using the correct
`ce-291-automerge-classifier-dryrun` slug.  The orphan carrier AND its
companion changelog are both on `origin/main`:

- `.ce/pr-manifests/ce291a-automerge-classifier-dryrun.md`
- `.ce/changelog/ce291a-automerge-classifier-dryrun.md`

Once the D-status filter lands, a PR that deletes these two orphan files
while adding its own carrier will pass cleanly.  Include the deletion
**in this PR** (cleaner than a separate follow-up; the fix directly
enables it).

---

## Parallel-safety check (pre-verified — no intersection)

In-flight PRs as of dispatch:

| PR  | Branch                       | Paths touched |
|-----|------------------------------|---------------|
| 612 | `ce-342-ci-retrigger`        | `.github/workflows/validate.yml`, `.ce/brain/assertions.yaml`, `.ce/changelog/ce-342-ci-retrigger.md`, `.ce/pr-manifests/ce-342-ci-retrigger.md` |
| 613 | `ce-341-autoreview-runmode`  | `tools/egress-broker/ce_egress_self_review_broker.py`, `validators/tests/unit/test_egress_self_review_broker.py`, `.ce/changelog/ce-341-autoreview-runmode.md`, `.ce/pr-manifests/ce-341-autoreview-runmode.md` |

This PR's allowed paths (see closed list below) have **zero intersection**
with both in-flight PRs.  Safe to dispatch immediately.

---

## Allowed paths (closed list — exact)

```
validators/creator_engine_validator/checks/path_manifest_fidelity.py
validators/tests/unit/test_path_manifest_fidelity.py
.ce/pr-manifests/ce291a-automerge-classifier-dryrun.md
.ce/changelog/ce291a-automerge-classifier-dryrun.md
.ce/pr-manifests/<branch-slug>.md
.ce/changelog/<branch-slug>.md
```

Note: the last two entries (`<branch-slug>`) are the carrier and
changelog for THIS PR.  Their exact filenames are derived by
`branch_slug("ce-345-path-manifest-dstatus")` — do NOT hand-invent the
filename; use `carrier_gen.write_carriers(base=<merge-base>)` to
generate them.  Do not edit any other file.

---

## Required work

### 1. Fix `_run_with_base_per_pr` — D-status filter

In `validators/creator_engine_validator/checks/path_manifest_fidelity.py`,
function `_run_with_base_per_pr`, change the carrier discovery line so
that only non-deleted (status `A` or `M`) carrier paths under
`manifest_dir` are counted toward the multiple-carriers check.

Concretely, L740 currently reads:

```python
carrier_paths = sorted(p for p in changed if p.startswith(prefix))
```

After the fix it must exclude D-status entries:

```python
carrier_paths = sorted(
    p for p in changed
    if p.startswith(prefix) and status_by_path.get(p, "") != "D"
)
```

`status_by_path` is already populated above this line from the
`--name-status` diff output, so no additional git invocation is needed.

Update the docstring of `_run_with_base_per_pr` to reflect that D-status
carriers are excluded from the count (they are housekeeping deletions,
not new carrier claims).

### 2. Regression test in `test_path_manifest_fidelity.py`

Add a test (name it `test_per_pr_deleted_orphan_carrier_passes_alongside_own`)
that proves the fix:

- Start from a base commit that already contains a foreign/orphan carrier
  under `.ce/pr-manifests/` (status `D` in the PR diff — i.e., it
  existed on base and the PR deletes it).
- The PR also ADDS its own correctly-slugged carrier (status `A`).
- Assert `result.ok` is `True` and no `path_manifest_multiple_carriers`
  error appears.

The existing test helpers `_init_repo`, `_write_repo_file`, `_git`,
`_carrier_rel`, `_build_doc`, and `branch_slug` are all available in the
test file — follow their pattern exactly.

### 3. Delete the orphan carrier and its changelog

Delete both files from the worktree so they appear as `D` in the PR diff:

```
.ce/pr-manifests/ce291a-automerge-classifier-dryrun.md
.ce/changelog/ce291a-automerge-classifier-dryrun.md
```

These exist on `origin/main` and should be committed as deletions.  They
have no corresponding code — they are dead manifest/changelog fragments
from an abandoned branch slug.

### 4. Generate carriers via `carrier_gen.write_carriers`

Generate the per-PR carrier and changelog for this PR using the
`carrier_gen.write_carriers(base=<merge-base>)` API.  Do NOT hand-list
filenames or manually compute the slug.

After generating, the carrier must list ALL and ONLY the allowed paths
that are actually changed in `base..HEAD` (the deletions of the two
orphan files count as changed paths and must appear in the manifest).

### 5. PR body — G5 gate line

The PR body must contain exactly one line matching:

```
- **Declared work class:** tiny
```

This PR is well below the 400-line floor for `tiny`.  Do not declare a
higher work class.

---

## Expected evidence (preflight checklist)

Before pushing, run the full suite in ONE pass — two-strike rule applies,
no reactive whack-a-mole:

```
TMPDIR=/var/tmp ce validate-pr
```

All of the following must be GREEN:

1. `path_manifest_fidelity` — no `path_manifest_multiple_carriers` (and
   no other path-manifest errors on the carrier or changelog).
2. `verify-path-manifest --base <merge-base> --manifest-dir .ce/pr-manifests`
   — diff matches the carrier path-set exactly (no diff-outside-manifest,
   no unfulfilled-manifest-path).
3. All existing `test_path_manifest_fidelity.py` tests pass (the existing
   `test_per_pr_multiple_carriers_fails_reporting_each` and
   `test_per_pr_foreign_merged_carrier_edit_alongside_own_is_reported`
   tests must still pass — the fix only excludes D-status from the count).
4. The new regression test (`test_per_pr_deleted_orphan_carrier_passes_alongside_own`)
   passes.
5. Changelog fragment present (ADDED, slug matches branch).
6. Work-class line present in PR body.
7. Full `ce validate-pr` exits 0.

---

## Stop-line

Commit all changes, confirm `ce validate-pr` exits 0, then STOP.

Report back to controller:

```
READY-TO-PUSH
commit SHA: <sha>
preflight: ce validate-pr exit 0 (attach output or last 30 lines)
```

Do NOT self-push.  Do NOT open a PR.  Do NOT approve or merge anything.
Do NOT self-merge.  Wait for controller to confirm before any push.
