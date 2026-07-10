# Seed Brief: ce-404 — wall re-mint on head_mismatch (queue-daemon deadlock fix)

- Role: implementer. Branch: `ce-404-wall-remint-on-head-mismatch` (NEW, off origin/main — fetch
  first; main must contain the merge of PR #740, verify `git log origin/main --oneline -5` shows
  "conveyor payload-as-data-only" merged before you start; if not, STOP and report BLOCKED-ON-PRECURSOR).
- Worktree: create under /var/tmp (NOT /workspace). Venv has no activate — use `.venv/bin/python -m pytest`.

## Bug (embedded ticket content — tracker unreachable from your seat)
When a PR head changes after ce-dev-2 approval (routine: reconcile push + re-approve), the
approval-capability marker in the PR body stays bound to the OLD head. The queue-daemon verifies
it, gets `head_mismatch`, and silently, permanently skips the PR — even though a fresh valid
approval exists on the current head. Root cause: `_approval_marker_mint_needed` in
`validators/creator_engine_validator/forge/integrator_belt.py` only mints when the verify reason
is `approval_capability_missing`; `head_mismatch` is a hard skip, never a mint trigger, no
operator-visible signal. Confirmed live twice on 2026-07-02 (PRs #737/#738; manual recovery =
strip the marker line, forcing reason back to approval_capability_missing).

## Fix (scope = exactly this)
1. In the verify-then-mint branch of integrator_belt.py: treat `head_mismatch` as mint-needed
   ONLY when a fresh, valid approval by the authorized reviewer identity exists on the CURRENT
   head — re-run the same trusted-approval check the `approval_capability_missing` path already
   performs (live re-verify: review decision APPROVED + approving witness commit == current head
   + authorized reviewer). On success: strip/replace the stale marker and mint for the new head.
2. Keep strict fail-closed (skip, NO mint) for `signature_mismatch`, `policy_mismatch`, and any
   unauthorized-reviewer reason. Do not widen the mint trigger beyond head_mismatch-with-live-
   valid-approval.
3. Visibility: when a marker verify fails with `head_mismatch` and no re-mint occurs (no valid
   current-head approval), emit an explicit daemon_decision reason (e.g.
   `head_mismatch_no_current_approval`) instead of a silent skip, so the deadlock is observable.
4. OUT OF SCOPE: the secondary friction (marker body-edit re-triggering full validation). Do not
   attempt it. If you see a trivial hook for it, note it in your done-report only.

## Tests
- Unit tests in the existing integrator-belt test module covering: (a) stale marker + valid
  current-head approval → re-mint + enqueue path proceeds; (b) stale marker + NO current-head
  approval → skip with the new explicit reason, no mint; (c) signature/policy mismatch → skip,
  no mint (unchanged); (d) missing marker path unchanged.
- Assertions must exercise the decision reason strings and the mint call, not just "no exception".

## Ceremony (all required before commit)
- `.ce/changelog/ce-404-wall-remint-on-head-mismatch.md` fragment.
- `.ce/pr-manifests/ce-404-wall-remint-on-head-mismatch.md` carrier regenerated via the
  carrier_gen.write_carriers API with base=<merge-base vs origin/main> (never hand-edit), and a
  `- **Declared work class:** S` line.
- FULL local preflight GREEN in one pass before commit-for-harvest: `ce validate-pr` (CI parity).
  If the brain drift gate fails, check for a stale gitignored .ce/state/brain projection
  (known false-RED) before assuming breakage. Do NOT append anything to .ce/brain/assertions.yaml
  in this PR — the ledger lane is serialized elsewhere; if a gate demands a ledger change, STOP
  and report BLOCKED-ON-PRECURSOR with the gate output.

## Evidence + stop line
- Commit with a clear message, then report (single line):
  `READY-FOR-HARVEST branch=ce-404-wall-remint-on-head-mismatch sha=<git rev-parse HEAD> preflight=PASS`
- NO push (you have no push auth), NO PR, NO approvals, NO gate/wall/daemon config changes, NO
  toolchain updates. Stop after the done-report.
