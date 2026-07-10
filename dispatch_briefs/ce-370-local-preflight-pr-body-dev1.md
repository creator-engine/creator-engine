# SEED BRIEF — ce-ops#370: local `ce validate-pr` honors CE-TEST-COUPLING-EXEMPT — SEAT: dev-1

**Ticket:** ce-ops#370. **Branch:** `ce-370-local-preflight-pr-body` (off origin/main). **Role:** implementer. **Work class:** `story` (declare by floor; likely tiny→story).

## Goal (self-contained — embed, do not rely on reading the private ticket)
CI (`.github/workflows/validate.yml`) passes `--pr-body-file` to the test-coupling gate, so the `CE-TEST-COUPLING-EXEMPT` opt-out marker in a PR body is honored in CI. Local `ce validate-pr` (`validators/creator_engine_validator/pr_preflight.py`, ~lines 731–757) does NOT pass a PR body, so the marker has **no effect locally** — local is conservatively stricter than CI. This is a real ergonomics gap: it just bit a release PR (local preflight passed, CI failed on the missing-marker because the gate couldn't see the exemption). Make local preflight read a PR body when one is available so local behavior matches CI.

## Scope
1. In `pr_preflight.py`, when running the test-coupling check locally, source a PR body if available and pass it through (mirror how CI feeds `--pr-body-file`). Reasonable sources, in order: an explicit `--pr-body-file` / `--pr-body` flag on `ce validate-pr` if one exists or should be added; else best-effort read of the current PR body via the open PR for the branch (only if egress/gh available — must DEGRADE GRACEFULLY to today's stricter behavior when no body is resolvable, never hard-fail).
2. Keep the default conservative: if no body is resolvable, behavior is unchanged (stricter) — this is a convenience, not a loosening of the gate.
3. (Optional, only if trivially in the same diff) the internal-coupling note: `test_coupling.py` imports private `_repo_root_for`/`_run_git` from `work_sizing_floor`. If you can promote those to a shared helper without scope creep, do it; otherwise leave it and note it. Do NOT expand scope for this.

## Evidence / DoD
- Test: with a PR body containing `CE-TEST-COUPLING-EXEMPT`, local `ce validate-pr` does NOT flag a code-without-tests PR (matches CI); without the marker it still flags; with no body resolvable, behavior is unchanged.
- Per-PR `.ce/changelog/<slug>.md` + carrier (`carrier_gen.write_carriers(base=<merge-base>)`) + correct work-class line in PR body.

## Stop line
FULL `ce validate-pr` GREEN locally (CI-parity, one pass) BEFORE self-push. Then `git commit && echo <SHA>`, push branch + open PR as dev-1. Report branch, SHA, PR#, preflight line. Do NOT approve/merge — controller holds the gate.
