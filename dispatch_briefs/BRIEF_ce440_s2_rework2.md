# REWORK 2 — ce-440-s2-cev3-deprecation — one-line mock fix + carrier regen

Your REWORK1 fix is CORRECT and verified (env-copy sentinel in _dequeue + the new
test_dequeue_forwarder_sets_v3_sentinel_and_keeps_stderr_quiet). Host preflight caught ONE
head-only failure your container env could not surface:

`validators/tests/unit/test_integrator_belt.py::test_ce_cli_dequeue_bridges_to_v3_module_without_importing_forge`
— its local `fake_run(argv, check=False)` mock (at ~:2645) does not accept the `env=` kwarg
your _dequeue fix now passes. TypeError at call time.

## Required (in /var/tmp/ce-440-s2, on top of d45fdc1b)
1. `def fake_run(argv, check=False, env=None):` — one line at test_integrator_belt.py:~2645.
   Keep its existing assertions; OPTIONALLY strengthen: assert env is not None and
   env.get(ce_cli._V3_FORWARDED_ENV) == "1" (matches the fix's contract; do not weaken anything).
2. test_integrator_belt.py is NEW to the diff path set → regenerate the carrier via the
   carrier_gen API (write_carriers(base="origin/main"); rm build/ + *.egg-info dirs first).
   The changelog does not need changes.
3. Focused green: test_ce_cli_v3_shim.py + test_integrator_belt.py. Commit
   `ce-ops#440 s2 rework2: accept env kwarg in integrator_belt dequeue mock`, signal EXACTLY:
   `READY-FOR-HARVEST ce-440-s2-cev3-deprecation <full-40-hex-sha> REWORK2`
