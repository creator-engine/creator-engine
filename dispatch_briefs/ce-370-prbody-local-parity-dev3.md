# SEED BRIEF — ce-ops#370: test-coupling gate — local `ce validate-pr` must pass --pr-body-file (CI parity) — SEAT: dev-3

**Context (self-contained — do not fetch any ticket):** The test-coupling gate (shipped in PR #678)
supports a `CE-TEST-COUPLING-EXEMPT` opt-out marker read from the PR body. CI (validate.yml) writes
the PR body to a file and passes `--pr-body-file`, so the marker works in CI. Local
`ce validate-pr` (validators/creator_engine_validator/pr_preflight.py ~lines 731-757) does NOT pass
it, so the marker has no effect locally — local is conservatively STRICTER than CI (annoying, not
unsafe). Fix: have the local preflight supply a PR body when one is available so local == CI.

**Task:**
1. In pr_preflight.py's local test-coupling invocation, accept/resolve a PR body source: an explicit
   `--pr-body-file` passed through `ce validate-pr`, plus a sensible local fallback (e.g. read the
   body from an open PR for the current branch is NOT available offline — so: explicit flag, else a
   conventional local file if the repo defines one, else current behavior). Keep it fail-closed:
   absent body == today's strict behavior.
2. Secondary cleanup (same PR, small): test_coupling.py imports private `_repo_root_for`/`_run_git`
   from work_sizing_floor — lift these into a shared non-private helper or re-export properly.
3. Unit tests for both: marker honored locally when body provided; strict when absent; helper import.

**Branch:** `ce-370-prbody-local-parity` (off `origin/main`, worktree under /var/tmp — NOT /workspace).
**Role:** implementer. **Work class:** by floor (likely S).
**Obligations:** `.ce/changelog/ce-370-prbody-local-parity.md` + `.ce/pr-manifests/ce-370-prbody-local-parity.md`
(carrier slug == branch; carrier covers ALL changed paths). Venv has no activate — use
`.venv/bin/python -m pytest`. Run the FULL local validator preflight (`ce validate-pr`, CI-parity)
before commit-for-harvest; if the full run hits stale-environment failures unrelated to your diff,
run the targeted tests + note the discrepancy in your done-report. Commit (do NOT push — controller
harvests) and echo the commit SHA. Done-report = branch, SHA, files, test evidence.
