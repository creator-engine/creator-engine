# SEED BRIEF — L10: work-class tiny/story/feature/epic → XS/S/M/L (back-compat) — SEAT: dev-1

**Lane:** arc L10 (work-management canon). **Branch:** `ce-workclass-xsml` (off origin/main). **Role:** implementer. **Work class:** declare by floor.

## Goal (self-contained)
Rename CE's work-class size vocabulary from `tiny/story/feature/epic` to **`XS/S/M/L`** to end the collision where size names reused issue-type words (story/feature/epic). **The LOC thresholds and the gate behavior do NOT change — only the labels.** Operator-ratified canon: `.ce/briefs/work-management-ssot-DRAFT.md` §4.

Mapping (identical thresholds): `tiny`→**XS** (<400), `story`→**S** (400-799), `feature`→**M** (800-1000), `epic`→**L** (>1000).

## Scope
1. **Rename the enum** to XS/S/M/L in `validators/creator_engine_validator/work_sizing.py` + `checks/work_sizing_floor.py` (and wherever the work-class set is defined/validated). Thresholds unchanged.
2. **Back-compat alias (REQUIRED):** the PR-body parser + the gate MUST accept BOTH the new `XS/S/M/L` AND the legacy `tiny/story/feature/epic` (mapped to the new ones) during the migration window — so in-flight PRs, old briefs, and existing changelog/carrier files don't break. Legacy values are accepted silently (optionally emit a soft deprecation note, not an error).
3. **PR-body convention:** canonical line is now `- **Declared work class:** <XS|S|M|L>`. Update the docs/templates that describe it; keep accepting the legacy line.
4. **Docs/reference:** update `.ce/reference/*.generated.md` (if it names the classes), the work-sizing docs, and any `docs/` references to the old vocabulary. Run the autogen-sync regen if applicable.
5. Do NOT change the diff-size METRIC (stays included-diff-LOC; the diff-token-count metric is a SEPARATE later task — out of scope).

## Evidence / DoD
- Tests: new `XS/S/M/L` declarations pass the floor gate at the same thresholds; **legacy `tiny/story/feature/epic` still pass (alias)**; below-floor still fails; the gate's LOC computation is unchanged.
- A test proving a PR body with the legacy line is still accepted.
- Per-PR `.ce/changelog/<slug>.md` + carrier (`carrier_gen.write_carriers(base=<merge-base>)`) + correct work-class line in the PR body (you may use either vocab thanks to the alias).

## Stop line
FULL `ce validate-pr` GREEN locally (CI-parity, one pass) BEFORE self-push. Then `git commit && echo <SHA>`, push + open PR as dev-1, report branch/SHA/PR#/preflight line. Controller holds the gate. Foreman mode — drive via subagent threads, do not inline.
