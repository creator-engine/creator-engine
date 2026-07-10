# BRIEF — dev-1 — installer trust-boundary + UX fixes (ce-ops#358)

Non-contained, SELF-PUSH as ce-dev-1. Fresh branch `ce-358-installer-trust-fixes` off CURRENT origin/main (`git fetch origin main` first; you are currently on the #359 branch — switch off it). Drive to a GREEN PR.

> NOTE: the cron handed you a #350 envelope-carrier brief — STAND DOWN on that; the controller is reassigning #350. Your lane is ce-ops#358.

## Two install.sh bugs (found by a real-installer smoke test)

### Bug 1 — SECURITY (primary): uv fetched without hash verification
`ensure_uv_available()` fetches uv from the live Astral endpoint (`astral.sh/uv/install.sh`) and executes it WITHOUT hash verification, even though the signed manifest's `python_acquisition` provides a pinned `UV_URL` + `UV_SHA256`. Today `UV_URL`/`UV_SHA` are read but never used to fetch/verify (only `UV_SHA` is format-checked). Result: installed uv (0.11.25 live) ≠ manifest-pinned (0.11.21), and the uv→CPython chain is OUTSIDE the hash-verified trust boundary.
**Fix:** fetch uv via the manifest-pinned `UV_URL`, verify the downloaded binary against `UV_SHA` BEFORE execution, install the versioned binary under `$BOOTSTRAP_ROOT/bin`. Keep a clear fail-closed error if the hash mismatches (never run an unverified uv). The `uv-*.whl` in the artifact cache is a Python wheel, unrelated — don't confuse it with the uv CLI binary.

### Bug 2 — UX: printed next-step references deleted temp files
`cleanup()` deletes `$TMPDIR_CE` (incl. verified `llms-install.md`, trust-root, trust-anchor, answers-schema) on exit, but the final printed next-step says to run `cev3 onboard --spec <verified-spec> --trust-root <...> --answers-schema <...> --plan` against those now-gone paths.
**Fix:** EITHER persist the four verified artifacts to a durable `$BOOTSTRAP_ROOT` location so the printed command is executable, OR replace the printed next-step with the `ce onboard --offline` form that works from the persisted `install-state` hashes. Pick the cleaner one; state your choice in the PR body.

## CRITICAL — install.sh is the highest-blast-radius file
- Do NOT break the install path. After your change, RUN THE INSTALLER END-TO-END in a fresh `ubuntu:24.04` linux/amd64 container (reuse your prior Mac-container smoke harness / the steps in `/tmp/ce-mac-smoke-dev1-*`) and confirm: (a) it still installs GREEN, (b) uv is now the pinned version + hash-verified, (c) the printed next-step is actually followable. Include this end-to-end smoke evidence in your PR body — not just unit tests.

## Gates
- Add tests for both fixes (hash-mismatch → fail-closed; next-step path exists/works). FULL `ce validate-pr` GREEN. Carriers (manifest + changelog; regen manifest via carrier_gen API, rm build/egg-info first). One work-class line. PR body references ce-ops#358 + the smoke evidence. Self-push, open PR, report PR# + SHA.
