# RELEASE LANE (RECUT) — cut 0.3.1 off CURRENT origin/main — HOST worker

**Why recut:** The prior `ce-release-0.3.1` branch was cut from `dd629ec1a` (#674) — BEFORE #678 (test-coupling gate) and #680 (v3_report fix) merged. Merging it as-is would REVERT ~400 lines incl. the test-coupling gate. It also never emitted bytes-to-sign and has no PR. **Discard it and recut cleanly.**

**Controller (ce-dev-2) performs the ce-root-v1 signing — non-delegable. You STOP at bytes-to-sign.**

## PRECONDITION
`git fetch origin` then verify `origin/main` HEAD == `d6c275816` (or newer) and that `git log origin/main --oneline -10` shows #678 and #680 merged. If main moved further, branch off whatever the current `origin/main` is.

## Tasks (NEW branch `ce-release-0.3.1-rc2` off CURRENT origin/main)
1. `git fetch origin && git branch -D ce-release-0.3.1 2>/dev/null; git checkout -b ce-release-0.3.1-rc2 origin/main`.
2. Bump version 0.3.0 → 0.3.1 in every spot the 0.3.0 bump touched: `validators/pyproject.toml`, `validators/creator_engine_validator/_version.py`, `validators/creator_engine_validator/version.py`, and any docs/site version refs the docs-reconciliation test checks. `grep -rn '0\.3\.0' --include=*.py --include=*.toml --include=*.md` to find them; mirror the 0.3.0 commit pattern exactly.
3. Assemble the 0.3.1 CHANGELOG from merged per-PR `.ce/changelog/*.md` since 0.3.0 using the documented release-changelog assembly tool (`release_changelog.py`) — do NOT hand-curate if the tool exists. Retirement entries (constitution Principle X, .specify removal, skills removal, onboarding docs) AND #678/#680 must appear.
4. Stage via the release-staging finalize seam (#669 / `.ce/release-staging/`) — mirror `.ce/release-staging/0.3.0/` structure into `.ce/release-staging/0.3.1/`.
5. **Re-sign install spec — STOP HERE for controller:** produce the exact bytes-to-be-signed for the 0.3.1 install spec (SSHSIG, PINNED_KEYS) and write them to `.ce/release-staging/0.3.1/INSTALL_SPEC_TO_SIGN`. Report the path + `sha256sum` of the bytes. DO NOT sign (you lack ce-root-v1).
6. Carrier + this-PR changelog as usual; regen carriers via `carrier_gen.write_carriers(base=<merge-base>)`; declare work class by floor. Run FULL `ce validate-pr` GREEN (host venv, TMPDIR=/var/tmp).
7. Open the release PR (base main). DO NOT tag/publish.

## Stop line
Release PR open + version bumped + changelog assembled + `.ce/release-staging/0.3.1/INSTALL_SPEC_TO_SIGN` emitted + preflight GREEN. Report: PR#, version-bump file list, changelog summary, bytes-to-sign path + sha256, preflight result. Controller then signs with ce-root-v1 → approve → tag → GitHub Release.
