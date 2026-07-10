# BRIEF — ce-compliance-doc-version-refs — stale release paths in compliance matrix (TINY, dev-3)

Role: implementer (dev-3, contained, foreman mode). Branch `ce-compliance-doc-version-refs` off
freshly-fetched origin/main. Worktree /var/tmp; venv `.venv/bin/python -m pytest`,
PYTHONPATH=validators, TMPDIR=/var/tmp.

## Mandate (embedded; found during an independent review 2026-07-05)
docs/compliance/ssdf-slsa-conformance.md cites a stale `docs/downloads/0.2.0/...` path in a
compliance-matrix evidence cell. Sweep THIS FILE for any hardcoded stale release-version paths
(0.2.0/0.3.0) and replace with the version-symbolic convention just established in
docs/contracts/installer.md (see its "downloads/<current-release>/" + signed-manifest-authority
phrasing on your fresh checkout — mirror that style). Do not change any other content claims.

SEMANTIC NOVELTY CHECK FIRST: confirm the stale citation still exists on fresh main.

## STOP lines
⛔ Only docs/compliance/ssdf-slsa-conformance.md + changelog + carrier. Do NOT touch
docs/install.sh, docs/downloads/**, llms-install.md, installer.md. Public-docs product lens:
zero ce-ops refs. Never sign. No review/approve/merge.

## Evidence bar
Full `ce validate-pr --profile contained-seat` if available on your fetched main (it merges today
— PR #804), else full validate-pr with the known carrier-gate caveat noted. Changelog + carrier
authored. Work class tiny. Signal: `READY-FOR-HARVEST ce-compliance-doc-version-refs <40-hex sha>`.
