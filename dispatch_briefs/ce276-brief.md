TICKET ce-ops#276 — Rented-surface governance Phase 3: `ce surfaces check-updates` — READ-ONLY upstream version detection (never auto-applies). WORK CLASS: feature. SEAT: dev-4 (commit-only — implement + commit + preflight, then STOP; do NOT push).
WORKTREE: `git worktree add /tmp/wt-ce276 -b ce276-surfaces-check-updates origin/main` (use /tmp if /workspace perms block in-tree worktrees).
SCOPE (all new except the CLI registration):
- `validators/creator_engine_validator/surfaces/__init__.py` (new)
- `validators/creator_engine_validator/surfaces/check_updates.py` (new) — read-only detection of available upstream versions for the manifest's rented surfaces, with 4 adapters: npm registry (`@openai/codex`), GitHub releases (herdr fork upstream), Zig (`https://ziglang.org/download/index.json`), PyPI (per Python dep). It READS surfaces/manifest.yaml (live on main) and reports current-vs-available; it NEVER mutates the manifest or applies updates.
- `validators/tests/unit/test_surfaces_check_updates.py` (new) — per-adapter unit tests with MOCKED HTTP (no real network in tests).
- `validators/creator_engine_validator/ce_cli.py` — register a `ce surfaces check-updates` subparser (one addition).
HARD EXCLUSIONS: do NOT add a @register'd validator CHECK / touch checks/__init__.py (this is a CLI subcommand, not a gate check). Do NOT modify surfaces/manifest.yaml, the Dockerfiles, tools/egress-broker/**, .github/**, AGENTS.md.
GOVERNANCE: carriers `.ce/changelog/ce276-*.md` + `.ce/pr-manifests/ce276-*.md` (issue: ce-ops#276). Put `- **Declared work class:** feature` in a PR_BODY.md for the controller's intake-push.
PREFLIGHT (FULL): `PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli validate-pr --base origin/main --declared-work-class feature`. COMMIT-ONLY: commit + preflight green, then STOP and report DONE. Do NOT push.
