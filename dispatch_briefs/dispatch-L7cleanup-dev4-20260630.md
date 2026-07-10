# DISPATCH — L7 injection-cleanup follow-on — dev-4

LANE: the L7 review (non-blocking) flagged a CI-injection ANTI-PATTERN: `${{ ... }}` GitHub-expression values interpolated DIRECTLY inside `run:` shell blocks. Currently regex-constrained so not exploitable, but it's the wrong pattern — move every such value to **env-var indirection** (`env: FOO: ${{ ... }}` then use `"$FOO"` in the run block). Defense-in-depth hardening.

WORKTREE under **/var/tmp** off **CURRENT origin/main** (includes the just-merged #699 release-finalize.yml). Branch **ce-l7-injection-cleanup**. For validate-pr use `/workspace/creator-engine/.venv/bin/python` with `PYTHONPATH=$PWD/validators` (NOT a worktree venv — that trap cost two seats hours). STOP before push; commit + `echo SHA`.

## Scope
1. `.github/workflows/release-finalize.yml` — line ~61 `tag_name="${{ steps.release-inputs.outputs.tag_name }}"` and ANY other `${{ }}` inside `run:` blocks → convert to `env:`-block indirection.
2. `.github/workflows/release.yml` — the same pre-existing pattern (e.g. line ~68 `tag_name="${{ ... }}"`) → same fix.
3. Sweep the OTHER L7 workflows (release-auto-tag.yml, release-parity.yml) + any workflow you touch for the same anti-pattern; fix consistently. (release-auto-tag/parity were already clean per review — verify.)
4. Do NOT change behavior — pure refactor (expression value flows via env instead of direct interpolation). Keep the existing input-validation/regex guards.

## Evidence
- grep proof: no `${{ ` remains inside any `run:` block in the touched workflows (only in `env:`/`if:`/`with:`).
- If a workflow-shape test asserts the run-block content, update it to match.
- `TMPDIR=/var/tmp .venv/bin/python -m creator_engine_validator.ce_cli validate-pr` GREEN (run on /workspace venv).
- Carrier+changelog (carrier_gen.write_carriers head_ref=ce-l7-injection-cleanup, issue=ce-ops#0 or omit, kind=ci, scope=release) + `- **Declared work class:** tiny` in the carrier.
- ⚠️ Verify vs origin/main; do NOT base on ce-release-0.3.1-rc2. Do NOT touch docs/install.sh or docs/downloads (signed-release coupling).
Report: branch, SHA, validate-pr PASS line, grep proof.
