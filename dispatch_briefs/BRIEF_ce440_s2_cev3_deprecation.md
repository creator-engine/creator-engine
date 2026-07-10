# BRIEF — ce-ops#440 Slice 2: cev3 deprecation notice + INTERNAL-groups lock-in (Lane E)

Role: implementer. Ticket: ce-ops#440 slice S2 (design excerpt embedded below — do NOT go
looking for host-side design files or private tickets; everything you need is in this brief).
Branch: `ce-440-s2-cev3-deprecation` off CURRENT `origin/main` (fetch first; verify
`git log --oneline -3 origin/main` includes the #776 CLI-unification merge b71d032f).
Worktree: create under `/var/tmp/ce-440-s2` (NOT /workspace). The repo venv has no activate
script — use `.venv/bin/python -m pytest`.

## Design excerpt (S2 of the ratified ce-ops#440 CLI-unification design)
ONE user-facing `ce` command; cev3 retired as a user-facing name. S1 (merged, #776) renamed
v3 `onboard`→`install`, nested `dispatch plan` under `pickup dispatch-plan`, and registered 32
non-colliding v3 verbs as native `ce` shims that subprocess-forward to v3_cli
(`V3_FORWARDING_SHIMS` in ce_cli.py). S2 = deprecation notice + guardrail test + one punted
product question. Acceptance: `cev3` output byte-identical except one stderr line.

## Scope
1. Add ONE stderr deprecation line to the `cev3` invocation path ONLY — shown when a user runs
   `cev3` directly (bare invocation and `--help`), NEVER when `ce` subprocess-forwards to
   `python -m creator_engine_validator.v3_cli …` (see `_forward_v3_argv`/`_forward_v3_command`
   in ce_cli.py ~line 2713-2727), and NEVER polluting `--json` stdout on any command.
   Discriminator design choice you must resolve and document in your done-report: today both the
   `cev3` console script and ce's forwarder reach the same `v3_cli.main()`. PREFER an internal
   env-var sentinel set by ce's forwarder (e.g. `CE_V3_FORWARDED=1`) over `sys.argv[0]` basename
   sniffing (argv[0] varies across pipx/uv/editable installs). State your choice + reasoning.
2. Add a regression test locking in
   `set(ce_cli.V3_FORWARDING_SHIMS) & ce_cli.INTERNAL_COMMAND_GROUPS == set()` — protects against
   a future verb sweep exposing internal groups through the `ce` shim mechanism. Also assert the
   deprecation notice is not emitted in a way that leaks internal command names.
3. DRAFT (do NOT file — you have no issue-write authority; return the text in your done-report)
   the bare-`ce` product-question ticket body: should bare `ce` (today: exit-2 + usage, see
   `test_bare_ce_keeps_usage_exit_2` in test_ce_cli_v3_shim.py) become `ce session` (cev3's bare
   default)? UX decision, separate from unification mechanics. Include current-behavior evidence.

## Allowed paths
- validators/creator_engine_validator/ce_cli.py
- validators/creator_engine_validator/v3_cli.py
- validators/tests/unit/test_ce_cli_v3_shim.py (extend; never weaken existing assertions)
- validators/tests/unit/test_v1_docs_reconciliation.py + test_support_agent_p0.py ONLY if the new
  assertion requires; never weaken existing INTERNAL_COMMAND_GROUPS checks
- .ce/changelog/ce-440-s2-cev3-deprecation.md (new; required — changelog is a workflow obligation)
- .ce/pr-manifests/ce-440-s2-cev3-deprecation.md via carrier_gen API
  (`write_carriers(base="origin/main")`) — never hand-list; rm any build/ + *.egg-info dirs first

## Do NOT touch
docs/install.sh + docs/downloads/** (signed-release-coupled) · anything under deploy/** (that is
S3, precondition-gated — NOT this slice) · docs/guide/** (in-flight #772 territory) ·
conveyor_daemon.py and sandbox wiring (8c/dev-1 territory) · no new top-level `ce` command group
(that would trip docs-reconciliation; S2 adds no new groups).

## Novelty check (FIRST, before writing code)
Grep ce_cli.py + v3_cli.py for `deprecat` (must be zero hits) and confirm test_ce_cli_v3_shim.py
has no INTERNAL_COMMAND_GROUPS reference yet. If either exists, STOP and signal
`BLOCKED ce-440-s2-cev3-deprecation already-landed <citation>`.

## Preflight + signal (standing directive, ce-ops#303)
Run the FULL local preflight (`ce validate-pr`, CI-parity, TMPDIR=/var/tmp) GREEN in ONE pass
before commit-for-harvest. KNOWN CONTAINER LIMITATION: full validate-pr may fail on the Python
3.11-out-of-contract environment issue in this container — if and ONLY if that is the failure,
run the focused set green instead (test_ce_cli_v3_shim.py + test_v1_docs_reconciliation.py +
test_support_agent_p0.py + carrier/changelog checks), commit, and still signal READY with the
env caveat; the controller re-runs the authoritative preflight host-side at harvest.
Commit message: `ce-ops#440 slice 2: cev3 deprecation notice + INTERNAL-groups lock-in`.
Then `git rev-parse HEAD` and signal EXACTLY:
`READY-FOR-HARVEST ce-440-s2-cev3-deprecation <full-40-hex-sha>` (+ env caveat if applicable)
or `BLOCKED ce-440-s2-cev3-deprecation <reason>`.

## Stop line
No S3 scope (docs sweep, systemd ExecStart migration). No pushing (controller harvests). No
issue filing. No review/approve/merge actions. If reality diverges from this brief, signal
BLOCKED with specifics rather than improvising.
