# BRIEF — ce-onboard-relaunch-ux — onboarding re-run idempotency + launch-failure diagnosis (QUEUED UNIT, dev-4)

Role: implementer (dev-4, contained, foreman mode). START after your ce-s1c-launch-default-policy
unit signals (same-file: launch_runtime.py). Branch `ce-onboard-relaunch-ux` off freshly-fetched
origin/main (must contain s1c's merge — poll fetch for it). Worktree /var/tmp; venv
`.venv/bin/python -m pytest`, PYTHONPATH=validators, TMPDIR=/var/tmp.

## Bugs (live canary evidence, 2026-07-05, clean-env one-liner install)
1. IDEMPOTENCY: welcome.md promises `ce onboard` re-run safety, but after a failed launch attempt
   the sentinel refuses: `SeatSurfaceReuseRefused: seat surface '...' already has a launched
   sentinel event; refusing to reuse it before spawn` (launch_runtime.py:679) — no remediation
   text, no CLI to clear it; canary recovered only by hand-deleting .ce/state/dispatches/<seat> +
   .ce/state/active-work-ledger/seats/<host>. Deliver a SAFE, governed re-run path: when the prior
   sentinel's process is verifiably dead (no live pid/tmux session), `ce onboard`/`ce launch`
   re-run should archive the stale seat surface (state preserved, e.g. dispatches/<seat>.archived-
   <ts>) and proceed; when liveness is ambiguous, keep refusing but with exact remediation text
   naming the supported recovery command. Keep it fail-closed — never silently reuse a surface
   that might be live.
2. DIAGNOSIS: when the launched harness dies instantly (e.g. exit 127 command-not-found), the
   top-level error is only `[refused] launch: single-controller assertion failed: 0 live
   controller(s)` (ce_onboard.py:678-725) while the true cause sits in
   .ce/state/dispatches/<seat>/events.jsonl (`"exit_code":127`). Surface the tail event (exit
   code + command) in the refusal message with remediation ("<harness> CLI not found on PATH —
   install Claude Code/Codex or fix PATH").
3. PRE-CHECK: `ce doctor` (RED-G checks) never verifies the harness CLI exists before launch —
   add a doctor check: configured harness binary resolvable on PATH, with actionable message.

## STOP lines
- ⛔ Fail-closed posture is inviolable: no path may auto-reuse a possibly-live seat surface.
- ⛔ Do NOT touch runner/*, runtime_backend_bridge.py, onboard_apply.py provision_runtime (s1c
  owns that seam and merges before you), ce_profile_path.py (another unit).
- ⛔ Never sign anything; no review/approve/merge/enqueue; don't revert others' edits.

Tests: behavioral — dead-sentinel re-run archives+proceeds; ambiguous-liveness still refuses w/
remediation; exit-127 surfacing; doctor harness check both ways. Hermetic.
Evidence: full validate-pr GREEN one pass (carrier-only failure = known contained-seat gap, say
so). Changelog + carrier. Work class story.
Signal: `READY-FOR-HARVEST ce-onboard-relaunch-ux <40-hex sha>`.
