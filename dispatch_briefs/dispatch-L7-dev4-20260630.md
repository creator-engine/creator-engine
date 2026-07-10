# DISPATCH — L7 Automatic-Release CI — dev-4 (foreman)

LANE: L7 — make a CE release require EXACTLY ONE manual act (the offline ce-root-v1 signature); CI-drive everything else. Build in a worktree under **/var/tmp** off **origin/main** (NOT /workspace). venv has no activate → use `.venv/bin/python -m pytest`. **STOP before push**; commit + `echo <SHA>` per slice; controller harvests. Run `TMPDIR=/var/tmp .venv/bin/python -m creator_engine_validator.ce_cli validate-pr` GREEN before declaring a slice done. One branch per cohesive slice-group; add carrier+changelog via `carrier_gen.write_carriers` + a `- **Declared work class:** <tiny|story>` line in the carrier.

## Verified ground truth (origin/main)
- **Pages = `docs/` on main, served directly** (docs/CNAME=creator-engine.dev, docs/.nojekyll; no gh-pages, no deploy-pages workflow). A commit to `docs/` on main → live in ~1-5 min.
- `release.yml` already: triggers on `release/v*` tag → `python -m creator_engine_validator release --tag` (orchestrate: bump→changelog→stage_signed_release) → draft GH release + AWAITING-OPERATOR issue. PLACEHOLDER_SIGNATURE used.
- `release-finalize` CLI EXISTS (`cli.py` ~line 827, accepts `--signature-file`) → `release_publish.finalize_signed_release()` verifies SSHSIG (via install_spec_signature_guard against docs/keys/ce-root-v1), replaces placeholder, parity-checks (verify_stage_hashes + _verify_stage_install_parity) — fail-closed.
- Version SoT: `validators/creator_engine_validator/version.py:__version__` (coupled to validators/pyproject.toml by packaging guard).
- `update.resolve_latest_signed_release()` fetches live + verifies — reuse for parity.
- validate.yml permissions-audit only inspects validate.yml itself (new write-perm workflows won't trip it).

## Target flow
bump-merge → [AUTO auto-tag] → [AUTO release.yml stage+draft+issue] → [MANUAL: offline `ssh-keygen -Y sign -n ce-spec-v1` of llms-install.canonical; signature_base64 is PUBLIC] → [AUTO release-finalize.yml: re-stage at tag, embed sig, create release-publish PR with carrier+changelog, commit docs/] → merge → Pages live → [AUTO release-parity.yml: verify live vs signed manifest, promote draft→latest, close issue].

## Slices (build in order; each its own branch+PR-ready commit)
- **L7-a (XS)** `.github/workflows/release-auto-tag.yml` + `validators/tests/unit/test_release_auto_tag_workflow.py`. push→main reads version.py via `ast.parse` (NOT import), creates annotated tag `release/v{ver}` ONLY if semver `^[0-9]+\.[0-9]+\.[0-9]+$` (skip pre-release) AND tag absent (`git ls-remote --exit-code`). perms contents:write. **Branch: ce-l7a-auto-tag.**
- **L7-b (S)** `.github/workflows/release-finalize.yml` + test. workflow_dispatch(version, signature_base64, dry_run). Checkout tag, re-run orchestrator, write sig to RUNNER_TEMP, run `release-finalize --signature-file`, create branch `release-publish/v{ver}`, copy finalized files into docs/, gen carrier+changelog, push, open PR (body has Declared work class: tiny). perms contents:write, pull-requests:write, issues:write. **Branch: ce-l7b-finalize.**
- **L7-c** add the PR-approval step to release-finalize.yml using secret `CE_RELEASE_REVIEWER_TOKEN` (author github-actions[bot] ≠ approver) + `gh pr merge --auto --merge`. The secret is NOT yet provisioned (Operator) → build the step but guard it so absence fails visibly (continue-on-error:false) without breaking earlier steps; document the secret in the PR. Fold into L7-b branch or a follow-up.
- **L7-e (S)** `.github/workflows/release-parity.yml` + test. workflow_run post-finalize: sleep 300s, `resolve_latest_signed_release()` vs live, assert version + SHA chain, gate `gh release edit --draft=false --latest` + close AWAITING-OPERATOR issue on pass. **Branch: ce-l7e-parity.**
- **L7-f (M)** `validators/tests/integration/test_release_finalize_integration.py` — full orchestrate→sign(test key, reuse `test_install_bootstrap.py:_sign_with_test_key`)→finalize→docs-copy produces a tree passing release_artifact_parity_guard + install_spec_signature_guard. Mark slow.

## Guardrails
- NEVER put the private key in CI. signature_base64 input = base64 of the detached .sig (public). 
- Reuse existing funcs (orchestrate_release, stage_signed_release, finalize_signed_release, release_bump, aggregate_changelog, release_artifact_parity_guard, carrier_gen.write_carriers, resolve_latest_signed_release, install_spec_signature_guard) — do NOT reinvent.
- ⚠️ The local `ce-release-0.3.1-rc2` branch carries a DIVERGENT 0.3.1 wheel (1d291268 vs origin/main signed 19310eda) — L7-e parity is exactly what prevents that class of drift from publishing. Do NOT base work on rc2.
- Report each slice: branch, commit SHA, validate-pr PASS line.
