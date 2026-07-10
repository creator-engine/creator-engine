# BRIEF — dev-1 — Confidentiality burndown (public-repo internal-identity + ce-ops# scrub)

Born-foreman, non-contained (SELF-PUSH your PR as ce-dev-1). Public-repo permanent history must carry ZERO internal identities/topology and ZERO private ce-ops# refs in product/docs files. Scrub the known leaks below into descriptive/generic text, preserving meaning.

## Branch
`ce-confidentiality-burndown` off current `origin/main`. Fresh worktree.

## Targets (grep to confirm exact lines; there may be a few more occurrences nearby — scrub all in these files)
1. `validators/creator_engine_validator/v3_cli.py` (~line 4001): help/comment text names real internal identities + hosts (`ubuntuaws745-cmyk`, `cedev1vps-cmd`, CE-DEV-1, laptop). Replace with generic role/placeholder text (e.g. "your reviewer account", "a peer host") — keep the help readable, drop the real handles/topology.
2. `validators/examples/reviewer-authority-envelope/invalid-unknown-mechanic.ce.yml` and `invalid-missing-binding.ce.yml`: `actor: ubuntuaws745-cmyk` → a generic fixture handle (e.g. `example-reviewer`). Check the other *.ce.yml example files in that dir for the same handle and scrub those too.
3. `docs/design/controller-bootstrap-injection.md` (~line 3): `ce-ops#244` (and any other ce-ops# refs in this file) → abstract to descriptive prose (no private ticket pointer). Then REMOVE this file from the `KNOWN_PENDING` allowlist in `validators/creator_engine_validator/public_docs_confidentiality.py` (the ratchet may only shrink — this strengthens the gate).

## Allowed paths
The files named above + `.ce/changelog/ce-confidentiality-burndown.md` + `.ce/pr-manifests/ce-confidentiality-burndown.md`. If a grep finds the same internal handles in OTHER public files, you MAY add them (note which) — but do not touch unrelated logic.

## Evidence
- FULL preflight GREEN: `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-confidentiality-burndown` (the hardened confidentiality gate must PASS with controller-bootstrap-injection.md no longer allowlisted).
- Carriers via carrier_gen (dashed slug); manifest + body carry `- **Declared work class:** tiny` (or story if the diff floor requires).
- SELF-PUSH as ce-dev-1, open the PR, report PR# + head SHA. Do NOT approve/merge.
