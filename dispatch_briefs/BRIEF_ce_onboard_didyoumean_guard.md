# BRIEF — ce-onboard-didyoumean-guard — friendly guard when installer flags hit native `ce onboard` (INTERIM TINY, dev-4)

Role: implementer (dev-4, contained, foreman mode). INTERIM TINY — run NOW while your s1c unit
waits for its s1a-merged condition; file-disjoint from s1c (ce_cli.py native-onboard region only).
Branch `ce-onboard-didyoumean-guard` off freshly-fetched origin/main. Worktree /var/tmp; venv
`.venv/bin/python -m pytest`, PYTHONPATH=validators, TMPDIR=/var/tmp.

## Why (embedded)
`onboard` is deliberately excluded from the cev3 forwarding shims (native `ce onboard` = first-run
orchestrator; installer flow = `ce install`; see test_ce_cli_v3_shim.py:79-84). Stale docs in the
wild still say `ce onboard --spec ... --plan/--apply`; today that dies with a generic argparse
"unrecognized arguments" and no hint. Live canary hit exactly this.

## Deliverable
In ce_cli.py's native onboard entry path (region ~405-467): when the incoming onboard argv
contains any of --spec/--answers/--answers-schema/--plan/--apply/--inventory, print a clear
message to stderr — the installer flow is `ce install <same args>` — and exit 2 WITHOUT running
native onboard. Keep native onboard behavior byte-identical otherwise. Behavioral tests: guard
fires per flag (message names `ce install`, exit 2), native onboard unaffected without those
flags, forwarding shims untouched (test_ce_cli_v3_shim assertions still hold).

## STOP lines
⛔ ce_cli.py native-onboard region + its tests + changelog/carrier ONLY. Do NOT touch the
V3_FORWARDING_SHIMS dict, validate-pr region (your own ce-434 PR is in flight there — do not
collide), launch/onboard_apply/runner files. Never sign. No review/approve/merge.

Evidence: full validate-pr GREEN one pass (carrier-only failure = known gap, say so). Work class
tiny. Signal: `READY-FOR-HARVEST ce-onboard-didyoumean-guard <40-hex sha>`.
