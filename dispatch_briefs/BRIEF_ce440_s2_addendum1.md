# ADDENDUM 1 — ce-440-s2-cev3-deprecation — novelty-check refinement (controller-verified)

Your BLOCKED already-landed signal was a FALSE POSITIVE caused by an over-blunt check in the
original brief (controller's fault). Controller verified on origin/main: the only `deprecat`
hit in v3_cli.py is line 4499, a `--work-root` argparse help string
("deprecated and refused; use --runtime-root") — an unrelated per-flag deprecation, NOT the
cev3-binary deprecation notice. ce_cli.py has zero hits.

REFINED novelty check (replaces the original): S2 counts as already-landed ONLY if a
deprecation notice is emitted on the cev3 console-script INVOCATION path itself (a stderr line
in or reachable from v3_cli.py main()/entry when invoked as `cev3`), or if
test_ce_cli_v3_shim.py already references INTERNAL_COMMAND_GROUPS. Neither exists — verified.

Ignore flag-level help-string matches. Resume the original brief
(/var/tmp/BRIEF_ce440_s2_cev3_deprecation.md) from scope item 1 and execute fully. All other
terms unchanged, including the signal format.
