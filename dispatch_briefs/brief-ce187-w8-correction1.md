# W8 CORRECTION 1 — ce-ops#187/#42 · expand allowed paths for the autogen CLI reference

You correctly STOPPED on `VAL-AUTOGEN-STALE-CLI` (.ce/reference/cli.generated.md stale, out-of-scope). That was the right call. Here is the controller's authorized scope expansion to finish the lane.

## Root cause
Adding the new `ce dispatch` command group changes the `ce` argparse tree, so the **auto-generated CLI reference** `.ce/reference/cli.generated.md` is now stale. It is a CHECKED ARTIFACT (gate `VAL-AUTOGEN-STALE-CLI` in `cli_reference_autogen_sync.py`) and must be regenerated + committed. This is the same docs-coupling class as the inventory test + README — I missed it in the original brief.

## Authorized additional path (ADD to your allowed set)
- `.ce/reference/cli.generated.md` (MODIFY — regenerate, do NOT hand-edit)

Everything else in the original brief (`brief-ce187-w8.md`) stays in force. No OTHER new paths are authorized — if validate-pr surfaces yet another out-of-scope required file, STOP and report again.

## Steps
1. `git checkout ce187-42-w8-dispatch-plan` (your 2 commits b09d09c + f57c675 are intact).
2. Regenerate the CLI reference from repo root:
   ```
   python scripts/gen_cli_reference.py --write
   ```
   (verify with `python scripts/gen_cli_reference.py --check` → must exit 0 / "fresh".)
3. **Update the path-manifest carrier** `.ce/pr-manifests/ce187-42-w8-dispatch-plan.md` to include `.ce/reference/cli.generated.md` in its path set, and recompute `AUTHORIZED_PATHS_COUNT` + `AUTHORIZED_PATHS_SHA256` — regenerate via the `carrier_gen.write_carriers(base=<merge-base-sha>)` Python API (do NOT hand-edit the hash). Remove any stray `validators/build/` / egg-info first.
4. Commit the regenerated reference + updated carrier (e.g. `chore(ce-ops#42): regenerate CLI reference for ce dispatch group`).
5. Re-run FULL `ce validate-pr --base origin/main --head-ref ce187-42-w8-dispatch-plan` → must be GREEN across ALL gates in ONE pass.
6. PR body still carries exactly `- **Declared work class:** story`.

## HARD RULES (unchanged)
- Use `ce validate-pr` (not raw pytest) — host /tmp/.git trap.
- HOLD — do NOT push/PR/merge until controller confirms. When green, report:
  `READY-FOR-HARVEST: branch ce187-42-w8-dispatch-plan, <N> commits, preflight GREEN`.
- If validate-pr is RED on any OTHER out-of-scope required file → STOP + report (do not expand scope yourself).
