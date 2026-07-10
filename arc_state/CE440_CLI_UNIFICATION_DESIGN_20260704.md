# CE440 — `ce`/`cev3` CLI Unification Design (2026-07-04)
> Operator-ratified decision: ONE user-facing `ce` command; binaries never encode versions;
> cev3 retired as a user-facing name. Design by architect_research (read-only). Posted to
> ce-ops#440. Scope: the ce/cev3 pair only (`creator-engine-validator` console-script is a
> distinct tool, out of scope).

## Load-bearing finding
The v1⊥v3 boundary (docs/architecture/VERSION_BOUNDARY.md, VAL-VERBND-CROSS, no allowlist) is a
**Python-import-graph** invariant: ce_cli.py is v1, v3_cli.py is v3, and importing across is
forbidden. Therefore parser-mount and full-merge are RULED OUT. The proven crossing mechanism is
subprocess + argv/JSON — already load-bearing in ce_cli today: `ce dequeue` → subprocess
`python -m creator_engine_validator.v3_cli queue-dequeue`, and `ce conveyor sweep` →
`python -m ...forge.integrator_belt`. v3_cli even sets `CE_CMD="ce"` as its own prog. The
unification shape is the generalization of that pattern.

## Collision map (exact; 35 groups each side, only 3 collide)
| name | ce | cev3 | disposition |
|---|---|---|---|
| playbook | ce_cli:1169 | v3_cli:4036 | IDENTICAL — both call playbook_runtime.run_cli; keep one native registration |
| dispatch | `dispatch plan` (offline plan emitter) | `dispatch worktree` (governed worktree materialization) | DIFFERENT — nest ce's under `ce pickup dispatch-plan`; bare `dispatch` goes to the v3 user-journey verb |
| onboard | first-run one-shot (doctor→install→launch) | the signed-install adoption flow (--inventory/--plan/--apply) | DIFFERENT — rename v3's to `install`. **Fixes a LIVE doc bug**: README:215 + welcome.md:107 teach `ce onboard --plan/--apply`, flags that exist only on cev3 onboard |

No other exact collisions (ce's names are compound: containment-status, automerge-status; ce's
`queue` group has only dry-run/inspect — the ce_cli.py:29 docstring's `ce queue poll` is stale,
fix independently).

## Recommended shape: (a) thin dispatch shim (reject mount (b) and merge (c))
1. Register each of the 32 non-colliding v3 verbs as a NATIVE argparse subparser on ce's own
   parser (own help/args mirroring v3's) — one coherent `ce --help`, native argparse errors.
   Duplicate parser definitions generated from one declarative table where feasible (drift risk
   → parity test per command: `ce <cmd> --help` ≡ `cev3 <cmd> --help` modulo prog).
2. Handlers subprocess-forward to `[sys.executable, -m, creator_engine_validator.v3_cli, <cmd>,
   *args]`, check=False, propagate rc, never reformat stdout/stderr.
3. Global flags: both parsers share only `--version` (identical shared helper) — zero divergence.
   Bare `ce` keeps exit-2+usage (cev3 bare defaults to `session`) — whether bare `ce` should
   become `ce session` is a SEPARATE product decision, punted deliberately.
4. INTERNAL_COMMAND_GROUPS hiding (ask/support/herdr, argparse.SUPPRESS) unaffected;
   unification ≠ ask graduation (ce-ops#311 gate stays).

## cev3 deprecation path
Keep cev3 installed + byte-identical for ~2 releases; add ONE stderr deprecation line (bare +
--help paths only; never pollutes --json stdout). Do NOT remove the pyproject console-script in
slice 1. Direct callers today: deploy/systemd/ce-integrator-daemon.service:11 and
ce-review-pickup-daemon.service:11 (`ExecStart=... cev3 ...`), E1 bootstrap (absolute venv path,
internal, may stay), INSTALLED_CE_DOGFOOD_MIGRATION.md:42,66 reference snippets. The
deploy/queue-daemon/ launcher package (in-flight worktrees, NOT confirmed at HEAD) is already
name-resilient (falls back to python -m v3_cli).

## Docs blast radius (slice 3 sweep list)
Machine-enforced: test_v1_docs_reconciliation.py inventory assertion; test_v3_cli.py /
test_support_agent_p0.py for renames. Signed (do NOT edit; next-release signing event only):
docs/install.sh + docs/downloads/*/install.sh (installs BOTH shims today, proves cev3 --help).
User-facing docs teaching cev3 verbs: README.md (~150-217, incl. the onboard bug),
llms-install.md, contracts/installer.md ("ce exposure" section — strengthen), guide/
pilot-runbook.md (heaviest), first-value-mythos.md, zero-to-governed-seat-quickstart.md,
welcome.md, onboarding-macos-container.md, operations/GREENFIELD_FIRST_PROJECT_PROTOCOL.md,
GITHUB_NATIVE_COORDINATION_PROTOCOL.md, SEAT_REAPER_PROTOCOL.md, INSTALLED_CE_DOGFOOD_MIGRATION.md,
AGENT_NATIVE_BOOTSTRAP.md, architecture/cockpit.md, session-status-line.md,
tasks-handoff-contract.md (NOTE: references nonexistent `cev3 tasks bind` — separate
doc-accuracy ticket, NOT this scope), work-claim-locks.md, decisions/ADR-0008,
playbooks/controller/runbooks/arad-pilot.md.

## Slicing
- **S1 (S)**: rename v3 onboard→install; nest ce dispatch-plan under pickup; shim for 32 verbs;
  inventory-test updates; parity tests. Acceptance: one coherent ce --help; per-command parity
  (rc/stdout/stderr ≡ cev3); version_boundary green; full validate-pr green.
- **S2 (S)**: cev3 stderr deprecation notice; INTERNAL groups assertion; file the bare-`ce`
  product-question ticket. Acceptance: cev3 byte-identical except one stderr line.
- **S3 (M)**: docs sweep per blast-radius list + migrate the two systemd ExecStart lines.
  Acceptance: `grep -rn cev3 docs/ playbooks/ deploy/` clean except sanctioned
  (downloads snapshots + installer.md internal note). PRECONDITION: verify deploy/queue-daemon/
  landing status on main first (risk 4).
- **S4 (S, at next signed release)**: install.sh stops advertising cev3 (signing event).

## Risks (with resolutions)
1 parser-copy drift → declarative table + per-command --help parity CI test. 2 rename blast →
cev3 unchanged in S1, grep confirms no CI/systemd calls cev3 onboard/dispatch; Operator should
check personal aliases. 3 bare-ce mismatch → punted to explicit product decision. 4
deploy/queue-daemon not-at-HEAD → verify before S3. 5 `cev3 tasks bind` doc drift → separate
ticket, do not "fix" by inventing the command.
