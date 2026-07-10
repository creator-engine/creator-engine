# WORK CLAIM — ce-ops#335 make work-sizing-floor + path-manifest gates rename-aware

**Seat:** dev-4 (DGX build seat). **Role:** implementer-foreman. **Born foreman** — fan out.

## Branch
```
git fetch origin && git checkout -b ce-335-rename-aware-gates origin/main
```

## Why (self-contained)
The G5 work-sizing-floor PR-diff gate classifies the diff using `git diff --numstat --no-renames <base>..HEAD`. Because of `--no-renames`, a content-preserving file **relocation** is counted as a full delete + a full add — doubling the measured line count and forcing mechanically-trivial moves into a higher tier (epic). This bit PR #591 (67 schema relocations → forced epic) and PR #593 tonight. The same rename-blindness likely affects the path-manifest fidelity check.

The gate's git invocation lives in BOTH places — keep them consistent:
- the inline work-sizing step in `.github/workflows/validate.yml`, AND
- the `work_sizing_floor` subcommand path (`validators/creator_engine_validator/cli.py` + the module it calls).

## Task
1. Make the work-sizing-floor gate **rename-aware**: use git rename detection (`git diff --numstat --find-renames` / `-M`) so a pure relocation counts as its true small delta, not delete+add. Keep tier thresholds unchanged. Fix in BOTH the validate.yml inline step and the cli.py/module path.
2. Audit the **path-manifest** fidelity check for the same rename-blindness; make it rename-aware/consistent.
3. Tests: a pure-relocation diff stays at its true small tier (no uplift); a genuine large change still derives the correct higher tier.

## Allowed paths (nothing else)
`.github/workflows/validate.yml` (the work-sizing inline step ONLY), `validators/creator_engine_validator/cli.py` + the work-sizing/path-manifest gate modules, `validators/tests/**`, `.ce/changelog/**`, `.ce/pr-manifests/**`.
**Do NOT touch:** `hook_check.py` (just landed via #596), onboarding code, or release/_version files.

## Evidence (DoD)
Full `ce validate-pr` GREEN; declare the G5-derived work-class.

## Stop-line
- Green + self-push works → push + open PR referencing ce-ops#335. Do NOT approve/merge.
- ⚠️ Your container has a **libsodium gap** that fails the `check-examples`/`well-formed examples` gate on an UNRELATED signed-lease fixture, regardless of your diff. If your ONLY preflight failure is that pre-existing libsodium/check-examples gate (zero NEW failures from your diff per baseline-diff), that is EXPECTED — report `READY-FOR-HARVEST: branch ce-335-rename-aware-gates, <N> commits, preflight green-except-libsodium` and the controller re-validates on the host.
- If push auth-fails (self-push gap #337) → report `READY-FOR-HARVEST` the same way.
- Preflight RED on a NEW gate caused by YOUR change → STOP + report the gate.
