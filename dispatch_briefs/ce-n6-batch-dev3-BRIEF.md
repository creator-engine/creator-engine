# Seed Brief: N6 batch — two file-disjoint fixes (ce-386-xdist-wheelbuild, ce-391-triage-advisory-text)

- Role: implementer. Contained seat — ticket content EMBEDDED below (you cannot read ce-ops).
- TWO independent tickets, TWO separate branches/worktrees off origin/main, TWO separate deliverables. Do them sequentially or in parallel subagent threads — they share no files.
- Contained-seat mechanics: worktrees under /var/tmp; venv has no activate → `.venv/bin/python -m pytest`.
- Standing preflight directive (ce-ops#303): FULL `ce validate-pr` GREEN one pass per branch before commit-for-harvest. Known exception: ssh-keygen install-spec gap — report as known exception if the ONLY failure.
- Each branch needs `.ce/changelog/<slug>.md` + carrier `.ce/pr-manifests/<slug>.md` via carrier_gen API (never hand-edit).
- Stop line (both): no pushes, no PR actions, no approvals, no merges, no gate/daemon config changes, no toolchain self-update. Do NOT touch .ce/brain/assertions.yaml.

## Ticket A (ce-ops#386) — branch `ce-386-xdist-wheelbuild` — work class XS
test_wheelhouse_built_surface.py:41 calls `build_app_wheel_from_source(repo_root, tmp_path)` WITHOUT the `@pytest.mark.xdist_group("wheel-build")` marker that test_wheel_bake.py's wheel-build tests use. Under xdist parallelism it races the real worktree's `validators/build` / `validators/creator_engine_validator.egg-info`, intermittently failing `test_build_app_wheel_from_source_is_surface_deterministic` — intermittent false-RED in ce validate-pr, undermining clean autonomous auto-gating.
Fix: add `@pytest.mark.xdist_group("wheel-build")` to the wheel-build test(s) in `validators/tests/unit/test_wheelhouse_built_surface.py` so they serialize with the other wheel-build tests (mirror test_wheel_bake.py's usage exactly). Allowed paths: that test file + changelog + carrier.

## Ticket B (ce-ops#391) — branch `ce-391-triage-advisory-text` — work class XS
`_pickup_triage` (validators/creator_engine_validator/ce_cli.py ~3565-3578): the plain-text branch prints only `result.items` and never surfaces `result.commissioned_unscheduled` or its count — default non-JSON invocation gives zero visibility into that governance signal (--json already surfaces it). Fix: wire the advisory section (+ count) into text-mode output, matching the JSON payload's information. Minor (same review, include): `_has_milestone` final `return True` fallback treats odd scalar shapes as "has milestone" — add an explicit branch for non-dict/list scalar shapes instead of blanket True. Add/extend unit tests for both (find the existing `_pickup_triage` text-mode tests via grep). Allowed paths: `validators/creator_engine_validator/ce_cli.py` (those two functions only) + its test file(s) + changelog + carrier.
NOTE: ce_cli.py is a shared hot file — keep the diff surgical; if you find the functions materially different from the line hints, adapt but stay within the two named functions.

## Evidence (per ticket)
Targeted tests green + full preflight GREEN one pass (paste summary line), `git commit && echo SHA`, then emit exactly:
`READY-FOR-HARVEST ce-386-xdist-wheelbuild <full-sha>` and/or `READY-FOR-HARVEST ce-391-triage-advisory-text <full-sha>` (one line per completed ticket, as each completes).
