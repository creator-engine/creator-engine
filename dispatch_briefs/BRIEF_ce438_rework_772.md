# BRIEF — REWORK PR #772 (docs: Complete Walkthrough, ce-ops#438) against the unified `ce` surface
Role: implementer. Claim: ce-438-rework-772. Worktree: new, under /var/tmp, branched off the LIVE PR head `dc71cd0c` (branch ce-438-complete-walkthrough). Your origin/main is current (verify `git rev-parse origin/main` == b71d032f4eb4a748c617aa50603cf8bc774c3852 — that includes the just-merged #776 CLI unification).

## Direction (settled — no Operator wait)
The prior review's open scope question (fix-doc-to-current-truth vs hold-for-verb-promotion) was resolved by the ce-ops#440 ratification: ONE user-facing `ce` command, cev3 retired as a user-facing name, and PR #776 (merged to main today) landed the first slice — v3 forwarding shims under `ce`, `onboard`→`install` rename (with one-cycle legacy alias), `ce dispatch` journey verb. Rework the walkthrough AGAINST WHAT IS NOW REAL ON MAIN. Never show `cev3` to the user; if a verb is not reachable via `ce`, restructure that step around what IS reachable (or clearly mark the gap) — do not advertise fiction.

## Review findings to fix (embedded; 4 blocking + 1 non-blocking)
1. Walkthrough verbs (`scope`/`shape`/`ratify`/`drive`/`report`/`artifacts`/`merge`) previously didn't exist under `ce`. #776's shims may have fixed much of this: AUTHORITATIVELY verify EVERY command in the doc against the merged surface — read `ce_cli.py` V3_FORWARDING_SHIMS inventory + `.ce/reference/cli.generated.md` + run `.venv/bin/python -m creator_engine_validator.ce_cli <verb> --help` per command. Every "What you do" line must parse for real.
2. `ce ratify <slug>` requires `--approver-ref` (HEX64, required=True) — show it correctly (sibling docs have the correct form to copy).
3. `--budget` is type=float — remove the `--budget S` work-class-letter conflation; show a numeric budget.
4. `ce ask` was presented as the safety net but is INTERNAL-gated (refuses without operator model config). Replace the safety-net advice with what a real new user can do (e.g. docs pointers / `--help` / the support path that actually exists on main today). If nothing real exists, say so plainly in the doc's own voice ("ask your operator") — no fictional commands. (Product gap already ticketed; your job is doc truth.)
5. Non-blocking: the completion-report block is stylized vs v3_report.py's actual box render — either match the real render or add an "illustrative output" caveat.

## Constraints
- Files: only the PR's own set (docs/guide/complete-walkthrough.{md,html}, getting-started-step-by-step.md, solo-ceo-onboarding.{md,html}, welcome.md, docs/index.html, test_site_index_docs_nav.py) + changelog append + carrier regen. If a sibling doc needs the same verb fix to stay consistent, fix it ONLY if it's already in the PR file set; otherwise note it in the done-report.
- Public-docs product lens: ecosystem-labeled-or-omit for internals, ZERO ce-ops# references in any tracked doc text.
- Extend-don't-weaken on test_site_index_docs_nav.py.
- Do NOT touch: any validators/*.py CLI source, docs/install.sh, docs/downloads/**, anything outside the PR set.

## Preflight + signal (standing, ce-ops#303)
FULL `ce validate-pr` GREEN one pass before commit-for-harvest; if the full suite is not green IN YOUR ENVIRONMENT for environmental reasons (known container gap), run the focused set (site-index/docs tests + path manifest) green, commit, and signal BLOCKED with the exact failure class as you did today — the controller re-runs the authoritative preflight at harvest. Signal exactly:
`READY-FOR-HARVEST ce-438-complete-walkthrough <full-40-hex-sha> REWORK` (or `BLOCKED ce-438-rework-772 <reason>`).
