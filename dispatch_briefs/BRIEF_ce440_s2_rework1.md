# REWORK 1 — ce-440-s2-cev3-deprecation (PR #782) — one blocking gap

Your S2 implementation passed review on all points except ONE blocking gap found by the
independent reviewer and controller-verified in source:

**ce_cli.py:2695-2712 — `_dequeue` forwards to v3_cli WITHOUT the sentinel.**
`ce dequeue <PR>` routes to `_dequeue` (dispatcher ~:5041), which runs
`python -m creator_engine_validator.v3_cli queue-dequeue ...` via
`subprocess.run(argv, check=False)` with the INHERITED env. `dequeue` is not in
V3_FORWARDING_SHIMS, so your shim-path sentinel never applies. Result: every `ce dequeue`
prints the cev3 deprecation notice — the exact regression the sentinel prevents.

## Required
1. Fix: in `_dequeue`, `env = os.environ.copy(); env[_V3_FORWARDED_ENV] = "1";
   subprocess.run(argv, check=False, env=env)`.
2. Coverage: add a test that exercises the `ce dequeue` forwarding path (stubbed subprocess is
   fine) asserting the notice is ABSENT from stderr — this closes the hole that let the gap slip.
3. Audit: confirm no OTHER non-shim subprocess call into v3_cli exists in ce_cli.py beyond the
   three known (:2691 integrator_belt = not v3; :2711 _dequeue = fixing now; :2726
   _forward_v3_argv = correct). State the audit result in your done-report.

## Mechanics
Work in your existing /var/tmp/ce-440-s2 worktree ON TOP of your commit 709b99e0 (the PR head
25fa7b76 is 709b99e0 + a harvest fixup touching ONLY the carrier work-class token — do not
recreate it; the controller reconciles at harvest). Allowed paths unchanged (ce_cli.py +
test_ce_cli_v3_shim.py; changelog/carrier only if the path set changes — it does not).
Focused tests green (test_ce_cli_v3_shim.py), commit
`ce-ops#440 s2 rework: set forward sentinel on ce dequeue path`, then signal EXACTLY:
`READY-FOR-HARVEST ce-440-s2-cev3-deprecation <full-40-hex-sha> REWORK1`
