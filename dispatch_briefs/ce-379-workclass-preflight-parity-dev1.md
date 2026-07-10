# SEED BRIEF — ce-ops#379: work-class name parity in pr_preflight (local↔CI) — SEAT: dev-1

**Context:** #686 renamed work classes to **XS/S/M/L** (legacy tiny/story/feature/epic as
aliases) and updated the FORGE CI G5 gate (`.github/workflows/validate.yml`: expects
`<XS|S|M|L>` and has an `aliases` map) — but it **missed the local branch validator**.
`validators/creator_engine_validator/pr_preflight.py:23` still hardcodes
`WORK_CLASSES = ("tiny", "story", "feature", "epic")` and its error message (line ~253)
says `<tiny|story|feature|epic>`. Result: local `ce validate-pr` REJECTS the new XS/S/M/L
names that CI accepts — every harvest of a brief that (correctly) declares XS/S/M/L has to
translate back to legacy names to pass local preflight. This is the live version-skew in
ce-ops#379. Fix it so local validate-pr and the FORGE gate accept the SAME set on any base.

**Branch:** `ce-379-workclass-preflight-parity` (off `origin/main`).
**Role:** implementer. **Work class:** declare by diff floor (likely S — declare it in
XS/S/M/L; if your own local preflight rejects that pre-fix, that IS the bug you're fixing —
you may need `git show origin/main:.github/workflows/validate.yml` for the canonical alias map).

## Goal
Make `pr_preflight.py` treat **XS/S/M/L as the canonical work classes** and accept the
legacy **tiny/story/feature/epic as aliases** (normalize to the canonical), MIRRORING the
FORGE G5 gate's alias map in `.github/workflows/validate.yml` (read it — do NOT invent a
different mapping; the two MUST agree). Specifically:
- Update `WORK_CLASSES` + the `_extract_declared_work_classes` / `_resolve_declared_work_class`
  parsing so both new and legacy names resolve to the same canonical class + the same LOC floor.
- Update the human-facing error/help strings to say `<XS|S|M|L>` (mention legacy aliases accepted).
- Ensure the LOC-floor thresholds match the ratified canon (XS/S/M/L bands per the
  work-management SSOT — read `process/work-management.md` on origin/main if present, else
  mirror the FORGE gate's floors). Do not change the floors' numeric behavior, only the naming.
- Reuse the shared `normalize_work_class` helper if one already exists in the codebase
  (grep for it — the actuator/CLI already use one) rather than duplicating the alias map.

## Scope — exactly these
- `validators/creator_engine_validator/pr_preflight.py`
- its unit tests under `validators/tests/` (add: XS/S/M/L accepted, legacy aliases still
  accepted + normalized, an unknown class rejected, floor mapping correct for both namings)
- `.ce/pr-manifests/ce-379-workclass-preflight-parity.md` + `.ce/changelog/ce-379-workclass-preflight-parity.md`
Do NOT touch the FORGE workflow (it's already correct), ce_cli.py, or anything else.

## Evidence / DoD
- FULL `ce validate-pr` GREEN in one pass — and demonstrate your OWN PR's XS/S/M/L
  work-class line now passes local preflight (the proof the skew is closed). Use
  `TMPDIR=/var/tmp PYTHONPATH=validators` (host /tmp/.git trap; PYTHONPATH picks up source).
  If the brain-drift false-RED recurs: `git show origin/main:.ce/brain/assertions.yaml > .ce/state/brain/assertions.yaml`.
- Carrier stem == branch slug; regen after final commit; `rm -rf validators/build` before `git add`.
- `git commit && echo <SHA>`; push; open PR with the declared-work-class line (XS/S/M/L) in the body. Do NOT approve/merge.
