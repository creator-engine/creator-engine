# BRIEF — ce-417-pilot-runbook-gaps — pilot-runbook brownfield/apply prerequisite gaps (UNIT 6)

Role: implementer (dev-1, self-push, foreman mode). UNIT 6 — ⚠️ SAME-FILE SERIALIZATION with your
UNIT 5 (both touch installer.md + pilot-runbook.md): start only AFTER your ce-414 PR is opened,
branch `ce-417-pilot-runbook-gaps` off freshly-fetched origin/main, and if ce-414 has not merged
by the time you finish, expect a rebase at review time (note it in the PR body).

## Mandate
Read ce-ops#417 directly (gh read). Four documented-flow gaps found in D1b prep (each with
file:line evidence in the ticket):
1. `docs/guide/pilot-runbook.md:49` worked example shows `host.sudo_grant: [runsc, proxy]`, but
   the pilot default `profile: solo-pilot` resolves to the os-native backend which never plans a
   privileged install — the example steers pilots to grant sudo CE will never use; line 24 also
   implies a sudo prompt always occurs. Fix the example + prose to match solo-pilot reality.
2. Brownfield `--apply` hard-requires `CE_FORGE_LIVE_FORGE=1` + `CE_FORGE_ADOPTION_WRITE=1` plus
   resolvable App credentials (CE_FORGE_APP_CLIENT_ID + installation id + PEM or mint-broker
   vars), else it refuses with `e2_brownfield_seam_unavailable`. Document these prerequisites
   pilot-facing (runbook §brownfield), including what the refusal error means and how to satisfy it.
3. Add the missing clone/cd step: adoption resolves project_root from process cwd — the runbook
   must say "clone the target repo and run onboard from inside it".
4. `docs/contracts/installer.md:143-157` describes existing-mode PAT needs as uniformly
   identity-only; add the nuance the ticket describes (read #417 item 4 in full for the missing
   scope note).

SEMANTIC NOVELTY CHECK FIRST per gap: verify each gap still exists on your fresh checkout
(post-ce-414 state); fix only the ones that remain, note any already-resolved in the PR body.

## Allowed paths
docs/guide/pilot-runbook.md · docs/contracts/installer.md · docs/contracts/brownfield-adoption.md
(only if a cross-reference fix is needed) · .ce/changelog/ce-417-pilot-runbook-gaps.md ·
.ce/pr-manifests/ce-417-pilot-runbook-gaps.md

## STOP lines
- ⛔ Do NOT touch `docs/install.sh` or anything under `docs/downloads/` (signed release surfaces).
- ⛔ Public-docs product lens: ZERO ce-ops#N references; product error names like
  `e2_brownfield_seam_unavailable` are fine (they are product-facing).
- ⛔ Docs-only unit: no code changes to v3_installer.py / onboard_apply*.py — if a doc fix reveals
  a code bug, signal it, don't fix it here.
- ⛔ Never sign anything with any key; if a step appears to need a signature → STOP, controller signs.

## Evidence bar
Full `ce validate-pr` GREEN locally in ONE pass before push. Changelog fragment + carrier matching
base..HEAD. PR body: exactly one `- **Declared work class:** <tiny|story>` (judge by diff floor).
Commit and report: `READY ce-417-pilot-runbook-gaps <40-hex sha> PR=<url>`.
