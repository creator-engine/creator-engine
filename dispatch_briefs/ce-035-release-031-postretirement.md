# RELEASE LANE — cut 0.3.1 (post spec-kit-retirement) — HOST worker (egress + controller signs)

**Goal:** Cut release **0.3.1** so the OFFICIAL signed channel reflects the spec-kit retirement (Arad/pilot-user channel). **Owner:** host implementer. **Controller (ce-dev-2) performs the ce-root-v1 signing — non-delegable.**

## PRECONDITION (verify before doing anything)
`git fetch origin && git log origin/main --oneline -8` MUST show ALL FOUR retirement PRs merged: #676 (Phase 4 constitution), #675 (Phase 2 .specify), #677 (Phase 1 skills), #674 (Phase 0 docs). If any is missing → STOP and report "retirement not fully merged"; do not cut a partial release.

## Tasks (branch `ce-release-0.3.1` off latest origin/main)
1. Bump version 0.3.0 → 0.3.1 wherever the version is declared (validators/pyproject.toml, any `__version__`, the docs/site version refs the docs-reconciliation test checks). Grep for `0.3.0` to find all the spots; mirror exactly what the 0.3.0 bump touched (look at the 0.3.0 release commit/PR for the pattern).
2. Assemble the 0.3.1 changelog from the merged per-PR `.ce/changelog/*.md` entries since 0.3.0 (use `release_changelog.py` / the documented release-changelog assembly — do NOT hand-curate if the tool exists). The retirement entries (constitution Principle X, .specify removal, skills removal, onboarding docs) must appear.
3. Stage the release via the release-staging finalize seam (#669 / `.ce/release-staging/`) — mirror the structure of `.ce/release-staging/0.3.0/`.
4. **Re-sign the install spec:** the `llms-install.md` / install spec must be re-signed for 0.3.1 with **ce-root-v1** (SSHSIG, PINNED_KEYS). YOU DO NOT HAVE THE KEY. Instead: produce the exact bytes-to-be-signed and write them to `.ce/release-staging/0.3.1/INSTALL_SPEC_TO_SIGN` (or the canonical path the signing procedure expects), and STOP at that point reporting "ready for controller signing" with the path + sha256 of the bytes. The controller signs offline with ce-root-v1 and completes the tag/publish.
5. Run FULL `ce validate-pr` GREEN (host venv, TMPDIR=/var/tmp). Carrier + this-PR changelog as usual; declare work class by floor.
6. Open the release PR (do NOT tag/publish — the controller tags + creates the GitHub Release after signing). STOP and report: PR#, version-bump file list, changelog summary, the bytes-to-sign path+sha, preflight result.

## Stop line
Release PR open + version bumped + changelog assembled + bytes-to-sign emitted for controller + preflight GREEN. Controller does: sign with ce-root-v1 → approve → tag 0.3.1 → GitHub Release. NOTHING signed/tagged/published by the worker.
