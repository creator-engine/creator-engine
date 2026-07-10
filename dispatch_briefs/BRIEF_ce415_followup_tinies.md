# BRIEF — ce-415-followup-tinies — brownfield-enabled review follow-ups (TINY, dev-3)

Role: implementer (dev-3, contained, foreman mode). START CONDITION: `git fetch origin` shows
origin/main contains a commit titled "installer: derive brownfield.enabled from real probe
signals" (PR #808) — poll until true. Branch `ce-415-followup-tinies` off that fresh origin/main.
Worktree /var/tmp; venv `.venv/bin/python -m pytest`, PYTHONPATH=validators, TMPDIR=/var/tmp.

## Mandate (embedded; from #808's independent review — both non-blocking follow-ups)
1. schemas/install-answers.schema.yaml (~448-450): `brownfield.enabled` still declares
   `default: true` — functionally inert (the detected layer always wins in merge_answers
   precedence) but now stale/misleading vs runtime behavior. Change the default to false OR
   remove it with a comment stating enabled is signal-derived (pick whichever the schema's own
   conventions support; the point is a future reader must not believe default-True is live).
   ⚠️ Schema edit → regenerate .ce/reference/schemas.generated.md via
   `python scripts/gen_schema_reference.py --write` and commit it (coupled-regen obligation).
2. Add the missing boundary test: a probe with git history present but ZERO CI workflows and
   ZERO test commands must yield enabled:True — one test in test_v3_cli.py (for
   _detect_brownfield_project) and/or test_v3_installer.py (for _brownfield_enabled_from_probe),
   matching the existing test style.

## STOP lines
⛔ Only: install-answers.schema.yaml, .ce/reference/schemas.generated.md, the two test files,
changelog + carrier. NO changes to v3_cli.py/v3_installer.py production code. Never sign. No
review/approve/merge.

## Evidence bar
Full `ce validate-pr --profile contained-seat` (now on main via #804) GREEN one pass — if the
profile flag is somehow absent on your fetched main, fall back to full validate-pr with the
carrier caveat noted. Changelog + carrier authored. Work class tiny.
Signal: `READY-FOR-HARVEST ce-415-followup-tinies <40-hex sha>`.
