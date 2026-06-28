---
slug: release-0-3-0-staging
date: 2026-06-27
kind: changed
scope: release version bump + vendored wheelhouse refresh + CHANGELOG
issue: ce-ops#315
---

**bump 0.2.0 to 0.3.0 + refresh wheelhouse for the clean-install cut.**

Bump the Creator Engine version 0.2.0 → 0.3.0 and stage the clean-install release.

## What

- Version SSOT bumped to 0.3.0: `validators/pyproject.toml`, `version.py:__version__`, baked `_version.py` (build SHA = origin/main HEAD 9b8a51d9).
- `CHANGELOG.md` brought current with the 0.3.0 "clean-install milestone" notes, led by the user-facing install-blocker fixes (ce-ops#331 schemas-in-wheel, #332 tmux pane-parse, #328 brownfield forge-identity, #323 install `| sh`→`| bash`).
- Vendored offline wheelhouse refreshed: added the missing `uv-0.11.21` x86_64 wheel (sha-pinned to the published install spec `b9ecdefa…`) + regenerated `SHA256SUMS`, so the cross-platform offline install is complete.

## Why

The Arad onboarding proved the published 0.2.0 wheel was broken for real users. All blockers are fixed in main; 0.3.0 is what turns onboarding from "works only with dev-2 hand-holding" into "just works." Verified by a clean-wheel repro: built the wheel from fresh origin/main, installed into a fresh venv, and ran `ce brain init` from a non-repo CWD — succeeds (the exact ce-ops#331 repro).

## Not in this PR

Signing + publish is Phase B (Operator-reserved, ce-root-v1). The placeholder-signed 0.3.0 Pages mirror is staged separately; this PR only bumps the sources + refreshes the wheelhouse. No tags pushed.

Refs ce-ops#315 (autonomous release Phase A).
