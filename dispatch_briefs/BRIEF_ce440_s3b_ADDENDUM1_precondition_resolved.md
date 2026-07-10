# ADDENDUM 1 — ce-440-s3b — precondition RESOLVED, proceed (supplements BRIEF_ce440_s3b_systemd_exec_migration.md)

Your BLOCKED signal was correct discipline — and the root cause is now diagnosed: you tested the
HOST-INSTALLED `ce` (0.3.1 wheelset, which predates the ce-ops#440 S1 shim). The precondition is
about the ROUTABILITY OF THE VERBS AT MAIN VINTAGE, and it holds:

- Controller evidence (2026-07-04 ~19:20Z, canonical runtime image `creator-engine/ce-validator:0.3.1`
  built from origin/main@3a930d05 — the intended runtime substrate for these units per two-plane):
  `ce queue-daemon --help` rc=0, usage byte-equivalent to cev3's (modulo the cev3 deprecation
  warning line); `ce review-pickup --help` rc=0. V3_FORWARDING_SHIMS on origin/main contains both
  ("queue-daemon" ce_cli.py:241, "review-pickup" :225).

## Amended instructions
1. Re-run the parity check yourself against MAIN-VINTAGE CODE, not the installed binary, from your
   branch worktree: `PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli queue-daemon --help`
   (and review-pickup) — expect rc=0. Record rc + first usage line as evidence in your PR body.
2. Proceed with the original brief unchanged (two ExecStart lines + test_gate_daemons_systemd.py:39
   prefix + changelog + carrier; work class tiny).
3. ADD one line to the PR body (after the work-class line): "Vintage coupling: units invoking `ce`
   require installed CE >= the #440-S1 shim or the canonical runtime image; pre-shim wheelsets
   (<=0.3.1 signed release) route these verbs via cev3 only."
4. All original constraints, preflight, signal format, and stop lines stand.
