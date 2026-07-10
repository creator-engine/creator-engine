# L7 Automatic-Release CI — Design + Build Spec — 2026-06-30

> From architect a4cf752a (full design in its task output). Grounded in origin/main. Goal: reduce a release to **exactly ONE manual act** (the offline ce-root-v1 signature); everything else CI-driven.

## Key findings
- **Pages = `docs/` on main, served directly** (`docs/CNAME=creator-engine.dev`, `docs/.nojekyll`, no gh-pages branch, no deploy-pages workflow). Any commit to `docs/` on main → live in ~1-5 min. **This unblocks N1b** (merge a signed `docs/llms-install.md` = live redeploy).
- 3 manual acts today: (1) create annotated tag, (2) offline sign, (3) finalize+commit-to-docs. Target: collapse to just (2).
- `release.yml` already: triggers on `release/v*` tag → orchestrate (bump→changelog→stage) → draft release + AWAITING-OPERATOR issue. `release-finalize` CLI exists (`cli.py:827`, accepts `--signature-file`). `finalize_signed_release()` verifies SSHSIG, replaces placeholder, parity-checks — fail-closed.

## Automated flow target
bump-merge → **[AUTO] auto-tag** → **[AUTO] release.yml** stage+draft+issue → **[MANUAL: offline sign]** → **[AUTO] release-finalize.yml** (re-stage at tag, embed sig, create release-publish PR, approve via CE_RELEASE_REVIEWER_TOKEN, enqueue) → merge → Pages live → **[AUTO] release-parity.yml** (verify live site vs signed manifest, promote draft→latest, close issue).

## Slices (build order)
- **L7-a (XS)** `release-auto-tag.yml` + test — push-to-main reads version.py, creates annotated `release/v{ver}` tag if new (semver-only, skip pre-release). **Land first, no deps.**
- **L7-b (S)** `release-finalize.yml` + test — workflow_dispatch(version, signature_base64, dry_run); re-stage at tag, finalize CLI, create release-publish branch+carrier+changelog, commit docs/, push, open PR. Dep: L7-a.
- **L7-c (S)** approval+merge-queue step using `CE_RELEASE_REVIEWER_TOKEN` (author github-actions[bot] ≠ approver). Dep: L7-b. **Needs new secret.**
- **L7-d (XS)** promote draft→`--latest` + close AWAITING-OPERATOR issue. Dep: L7-c.
- **L7-e (S)** `release-parity.yml` (workflow_run post-finalize) — sleep 300s, `resolve_latest_signed_release()` vs live, gate promotion on parity. Dep: L7-d.
- **L7-f (M)** integration test of full finalize path (test signing key, `_sign_with_test_key` pattern).

## Reuse (no change): orchestrate_release, stage_signed_release, finalize_signed_release, release_bump, aggregate_changelog, release_artifact_parity_guard, carrier_gen.write_carriers, update.resolve_latest_signed_release, install_spec_signature_guard.
## New: 3 workflows + 3 tests + `CE_RELEASE_REVIEWER_TOKEN` secret.
## Risk flagged: signature_base64 is PUBLIC (safe in CI); private key never enters CI. validate.yml permissions audit only checks itself (new write-perm workflows won't trip it).

## ⚠️ rc2-divergence landmine (separate, urgent for release-hygiene): the local `ce-release-0.3.1-rc2` branch carries a DIVERGENT 0.3.1 wheel (sha 1d291268 vs origin/main's signed 19310eda). It must NOT publish without re-sign + parity — exactly what L7-e prevents.
