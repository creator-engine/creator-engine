# CORRECTION 1 — dev-3 — ce-503-refresh-guard — REQUEST_CHANGES remediation (PR #899)

Independent review confirmed your guard restructure is sound and the foreign-file refusal
holds, BUT the controller verified empirically that the fix does NOT cover the actual
trigger generation: `_workflow_content_looks_ce` returns False on the real affected
workflow. Your G0 fixture (signed-download era: CE_APP_WHEEL + `ce check .ce/ --json`) is a
DIFFERENT, newer generation than the true oldest deployed one.

## The missing generation (markers verified against the live trigger file; all of these
## lines come from CE's own shipped template of that era — version-parameterized where noted)

The pre-signed-download ADVISORY generation is characterized by ALL of:
1. `name: Validate governance artifacts` (workflow/job name — same as later gens)
2. The hash-pinned requirements line, version-independent prefix:
   `creator-engine-validator @ https://creator-engine.dev/downloads/` (followed by
   `<ver>/creator_engine_validator-<ver>-py3-none-any.whl --hash=sha256:…` — marker must
   NOT pin the version; match the stable prefix, and separately require the substring
   `--hash=sha256:` to keep it structural)
3. Exact installer line: `python -m pip install --require-hashes --only-binary :all: -r /tmp/ce-requirements.txt`
4. Exact invocation: `ce check .ce/ | tee /tmp/ce-check.out || true`

## Required changes (same branch `ce-503-refresh-guard`, same worktree
## /var/tmp/ce-503-refresh-guard — REBASE onto fresh origin/main first)

C1 — Add this generation's marker set to `generation_markers` in
`validators/creator_engine_validator/onboard_apply.py` using the 4 markers above (with the
version-independent treatment of marker 2). Keep the existing G0/G1 sets unchanged.

C2 — Add an inline fixture reproducing this generation faithfully (derive it from the
actual template of that era in git history if present — search history of the workflow
template/renderer for the `| tee /tmp/ce-check.out` line; if history doesn't contain it,
construct the fixture from the four markers embedded in a realistic minimal workflow). The
fixture must contain NO tenant-identifying content — only CE template lines.

C3 — Extend the parametrized recognition test to include the new fixture; extend the
negative test if needed so a foreign workflow containing ONLY marker 1 (a common job name)
plus a comment mention still fails (it must lack markers 2-4).

C4 — ALSO fix the reviewer's INFO note in the changelog text if trivial: note that G1-era
repos with a renamed job heading are deliberately refused (policy: modified CE workflows =
foreign).

Recommit (amend or new commit), rerun what preflight you can in-container
(`ce validate-pr --profile contained-seat` — the ssh-keygen guards will fail on the known
seat-image gap; everything ELSE must be green), then emit
`READY ce-503-refresh-guard <new-commit-sha> .ce/pr-manifests/ce-503-refresh-guard.md`.
Controller re-verifies against the live trigger file before updating PR #899.
Stop line unchanged: same 4 authorized files, no pushes, no PRs.
