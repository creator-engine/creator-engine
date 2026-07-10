# BRIEF — dev-3 — 2026-07-08 — 1 TINY/S unit: ce-ops#503 refresh-workflow recognition guard, generation-aware

Role: implementer. COMMIT-FOR-HARVEST: do not push; controller harvests. On green preflight
emit exactly `READY ce-503-refresh-guard <commit-sha> <carrier-path>`; if blocked emit
`BLOCKED ce-503-refresh-guard <one-line reason>`.

Worktree: `git fetch origin main` first, then fresh worktree at `/var/tmp/ce-503-refresh-guard`
off `origin/main`, branch `ce-503-refresh-guard`. No venv activate.

TICKET (ce-ops#503 unreachable from seat; summary embedded): `ce onboard --refresh-workflow`
(shipped #885, refusal pin #890) refuses to update the FIRST LIVE TENANT's workflow. The guard
`_looks_like_ce_workflow` in `validators/creator_engine_validator/onboard_apply.py` requires ALL
THREE markers — "creator-engine-validator", "CE signed spec content_sha256 mismatch",
"ce check .ce/ --json" — but repos onboarded from EARLIER template generations only contain the
first (their workflow runs `ce check .ce/ | tee /tmp/ce-check.out || true`, advisory-only, no
canonicalization step). The refresh verb therefore rejects exactly the already-onboarded repos it
exists to remediate. Fix: generation-aware recognition that accepts every CE-shipped template
generation while STILL refusing genuinely foreign/user-authored workflow files.

## U1 — branch `ce-503-refresh-guard`

I1 — Recover the shipped template generations from OUR OWN git history: `git log --follow -p`
over the onboarding workflow template file (find it: the template that renders
`.github/workflows/ce-validate.yml`; it lives with the onboard/installer surfaces — search for
`ce-validate.yml` producers under validators/). Identify each distinct shipped generation
(expect ~3: G0 advisory-only `ce check .ce/ | tee … || true`; G1 canonicalization era; G2
current post-#885). Capture each as a test fixture (sanitized template output, NO tenant
content, NO tenant names — render from OUR templates only).

I2 — Rework `_looks_like_ce_workflow` (and only it) into generation-aware recognition:
a file is a CE workflow iff it matches the marker profile of ANY shipped generation. Suggested
shape: a tuple of per-generation marker-sets (each generation = markers that ALL must be
present), file matches if any generation's set fully matches. G0's set will be small (e.g.
"creator-engine-validator" + the workflow-name/structure markers actually present in G0 —
derive from the real G0 template, do not guess); keep the current three-marker set as the
newest generation. The foreign-file refusal MUST survive: a hand-written workflow that merely
mentions creator-engine-validator in a comment should still be refused if it lacks the other
G0 structural markers — pick G0 markers accordingly (e.g. the exact `ce check .ce/ | tee`
invocation line and the CE-rendered header/name line).

I3 — Tests in the existing test module for onboard_apply (extend
`validators/tests/unit/test_onboard_apply.py`): every shipped generation fixture is recognized;
a foreign workflow (typical user CI yaml naming creator-engine-validator only in a comment) is
refused; the refusal message unchanged for foreign files; refresh proceeds (driver seam fake)
for a G0-generation file.

STOP LINE / allowed paths: `validators/creator_engine_validator/onboard_apply.py` (the
recognition guard only — do NOT touch refresh_ce_workflow flow, drivers, or apply paths),
`validators/tests/unit/test_onboard_apply.py`, fixture files under the test-fixture convention
that module already uses (if it embeds strings inline, embed inline), plus
`.ce/changelog/ce-503-refresh-guard.md` and `.ce/pr-manifests/ce-503-refresh-guard.md`
(slug == branch; exactly one `- **Declared work class:**` line; use `tiny` if the diff stays
small, `story` if fixtures push it over — declare honestly). Nothing else. No tenant
identifiers anywhere in code, fixtures, changelog, or carrier.

Preflight (ce-ops#303): FULL `ce validate-pr --profile contained-seat` (CI parity) before
commit-for-harvest; `-n 4`; TMPDIR=$HOME/tmp if writable else /var/tmp. Do not discover gates
via CI. No pushes, PRs, approvals, merges, signing.
