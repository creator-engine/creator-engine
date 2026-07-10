# BRIEF — dev-1 — fix(doctor): gate RED-G-6 packaging check to CE source-tree context (ce-ops#359)

Non-contained, SELF-PUSH as ce-dev-1. Fresh branch `ce-359-doctor-packaging-context` off CURRENT origin/main (`git fetch origin main` first). Drive to a GREEN PR; do NOT merge/approve (controller gates).

## The bug (confirmed by verification in a real user git repo)
`ce onboard` fails for EVERY first-time user running it in their own project repo. `ce doctor`'s RED-G-6 packaging check fires UNCONDITIONALLY and looks for CE SOURCE-TREE developer artifacts relative to CWD: `validators/pyproject.toml`, `validators/wheelhouse`, `validators/uv.lock`. A normal user project has none → doctor refuses: reason "doctor refused (ungoverned host)", refused_clauses `["RED-G-6"]`, `applicable: true` → `ce onboard` returns `ok:false`. Blocks all onboarding. (Workaround users currently need: `ce brain init` + `ce launch`.)

## The fix
Gate the RED-G-6 packaging check so it is **applicable ONLY in CE-developer / CE-source-tree context** (i.e., when run against the creator-engine repo itself), and is **not-applicable (does not refuse)** when run in a user's own project directory.

### CRITICAL — do NOT weaken the check where it belongs
RED-G-6 exists to catch CE's own packaging-contract drift (missing pyproject/wheelhouse/uv.lock in the CE source tree). Your change must PRESERVE that: in CE source-tree context the check must still fire on real drift. You are only making it **not applicable outside the CE source tree** — not removing or softening it. Pick a robust CE-source-tree signal (e.g. a CE-repo marker / the expected CE packaging layout / repo identity), not a fragile heuristic that a user repo could accidentally trip or that disables the check for CE.

## Where
Grep the doctor code under `validators/creator_engine_validator/` for `RED-G-6`, the packaging/wheelhouse check, and the `applicable` determination. Understand the clause's intent before editing.

## Tests (required)
- User-repo-like context (no `validators/pyproject.toml` etc., not the CE source tree): RED-G-6 packaging check is NOT applicable / does NOT refuse; `ce onboard`/`ce doctor` proceeds.
- CE source-tree context with induced packaging drift: RED-G-6 STILL fires (regression guard — proves you didn't gut it).

## Gates
- FULL `ce validate-pr` GREEN in one pass (TMPDIR=/var/tmp). Carriers: `.ce/pr-manifests/<slug>.md` (regen via carrier_gen API; rm build/egg-info first) + `.ce/changelog/<slug>.md`. Exactly one work-class line (`- **Declared work class:** story` likely).
- PR body references ce-ops#359. Self-push as ce-dev-1; open the PR; STOP. Report PR number + SHA + green evidence.
