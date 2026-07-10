# BRIEF — dev-1 — 2026-07-07 — journey program R2: fix review findings on #876/#877/#878
# QUEUE AFTER your P0 units (#874 rechain, #859 rebase+fix). Full verdicts are on each PR.

All three journey PRs got independent REQUEST_CHANGES verdicts. Vocabulary/product-lens bars
were CLEAN on all three — the blockers are correctness/copy-pasteability. Self-push allowed
(your PRs). Signal `READY <branch> <sha>` per PR.

## U3 — PR #876 (next-step hints)
1. BLOCKING: v3_cli.py `_cmd_scope` — gate `journey_guidance.scope_next(...)` AND the JSON
   `"next"` key behind `if ready:` (mirror `_cmd_shape`'s pattern). Add a not-ready-path test.
2. ADVISORY: `--controller-id` default change `cev3-review`→`ce-review` — either justify in the
   changelog fragment (one line: why) or revert and split out.
3. ADVISORY (your call): add the setup path (`ce brain init`, `ce launch --backend host`) as a
   first line in the `ce init` stage-map hint.

## U4 — PR #877 (journey doc pair) — gates the Arad send, prioritize within this batch
1. BLOCKING: quickstart step 3 — `ce shape` won't paste (scope_id is a required positional).
   Use `ce shape login-empty-state` (works pre-scope-file) or drop the step.
2. BLOCKING: quickstart step 5 — `ce ratify login-empty-state` won't paste (--approver-ref
   required). Show the full form with a placeholder HEX64 + one line on how the user gets/
   substitutes their own digest (complete-walkthrough already shows the correct form).
3. ADVISORY: complete-walkthrough "Get Running" — drop or annotate the redundant `ce brain init`
   after `ce onboard` (onboard already runs brain_init).
4. ADVISORY: solo-dev/solo-ceo onboarding docs show bare `ce launch`; align with
   `--backend host` or cross-link the quickstart.
After fixing, RE-PASTE-TEST every command block in quickstart.md top to bottom.

## U5 — PR #878 (shape --from)
1. BLOCKING: v3_cli.py:2701 — add a `source_path.stat().st_size` guard before `read_text()`
   (e.g. 512 KB) with an exit-2 teaching message (trim/split guidance) + test.
2. ADVISORY: add tests for the binary/non-UTF-8 PRD path (`prd_read_failed`) and the reachable
   `invalid_scope_id` path in `--from --confirm`.

Standard stop lines. Changelog fragments: extend existing per-branch fragments only if behavior
notes change (876's controller-id justification if kept).
