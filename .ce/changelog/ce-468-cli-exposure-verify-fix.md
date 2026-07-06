## fix: verify_cli predicate tolerates onboard→install verb rename (ce-ops#468)

`verify_cli()` in `onboard_apply.ApplyDriver` previously ran
`ce onboard --help` and required the string `"onboard"` to appear in
stdout.  The 0.3.2 onboard→install verb rename caused that invocation to
print `usage: ce install ...`, so `"onboard"` matched 0 times and every
`onboard --apply` died at the `cli_exposure` leg with all downstream forge
legs dependency-skipped.

The fix:

- Invocation changed to `ce --help` (top-level help; no verb dependency).
- Predicate changed to `rc == 0 AND "usage: <command>" in stdout.lower()`,
  which is verb-rename-safe and still asserts the shim produces CE-shaped
  output.
- `onboard_apply_live.py` does not override `verify_cli`; the base-class
  fix covers the live driver.

Regression tests added to `validators/tests/unit/test_onboard_apply.py`:
`test_verify_cli_tolerates_install_verb_rename`,
`test_verify_cli_old_predicate_would_have_failed_on_032_help`,
`test_verify_cli_fails_closed_when_shim_missing`,
`test_verify_cli_fails_closed_on_nonzero_rc`.
