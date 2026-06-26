# CE CLI Reference

Status: SSOT reference for Controllers.
Source date: 2026-06-26.
Generation inputs:

| Command | Result | Notes |
| --- | --- | --- |
| `ce --help 2>/dev/null || PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli --help` | succeeded with repository CPython-3.14 venv fallback | `ce` was not installed on `PATH`; fallback used `/workspace/creator-engine/validators/.venv/bin/python` because system Python 3.11 lacks runtime deps. |
| `ce lane --help 2>/dev/null` | succeeded with repository CPython-3.14 venv equivalent | `ce` was not installed on `PATH`; fallback used `PYTHONPATH=validators ... -m creator_engine_validator.ce_cli lane --help`. |
| `PYTHONPATH=validators python3 -m creator_engine_validator --help` | succeeded after switching to repository CPython-3.14 venv | System Python 3.11 lacks runtime deps; venv help output was live. |
| `PYTHONPATH=validators python3 -m creator_engine_validator.v3_cli --help 2>/dev/null \| head -80` | succeeded after switching to repository CPython-3.14 venv | Help output identifies the user-facing program name as `ce`; this reference names the monorepo entry point `cev3` to avoid collision with the v1 `ce` surface. |

## Command Group: `ce`

Purpose: v1 kernel CLI for governed lane launch, side-effect ledgers, worker runtime, local PR preflight, controller-seat launch, queue operations, event/PCL ledgers, brain assertions, connectors, and install/update flows.

Entry point:

```bash
ce --help
PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli --help
```

Top-level flags:

| Flag | Purpose |
| --- | --- |
| `--version` | Print derived CE version token and exit. |
| `-h`, `--help` | Print command help. |

Main subcommands:

| Subcommand | Purpose |
| --- | --- |
| `ce lane <cmd>` | Governed visible lane-launch primitive. |
| `ce ledger <cmd>` | Append and verify Side-Effect Ledger records. |
| `ce worker <cmd>` | Allocate, spawn, run, inspect, terminate, or reap governed worker containers/seats. |
| `ce fanin <cmd>` | Build or inspect deterministic evidence fan-in packets. |
| `ce queue <cmd>` | Preview, inspect, or poll Integration Queue state. |
| `ce event <cmd>` | Append, verify, sign, replay, or index CE-event chains. |
| `ce pcl <cmd>` | Append, verify, replay, index, or merge PCL ledgers. |
| `ce brain <cmd>` | Manage local brain assertion ledger and recall store. |
| `ce connector <cmd>` | Verify connector descriptors, plan/fetch reads, plan/submit bounded writes. |
| `ce playbook <cmd>` | List, show, or run governed CE playbooks. |
| `ce reviewer-triage plan` | Emit a reviewer-triage decision record. |
| `ce check` | Run a named local check surface. |
| `ce doctor` | Run local readiness/diagnostic checks. |
| `ce containment-probe` | Probe live-runtime containment of a pid from `/proc`. |
| `ce containment-status` | Probe fleet seat containment from live pids and runtime evidence. |
| `ce validate-pr` | Run local PR preflight against committed `base..HEAD` state. |
| `ce launch` / `ce hud` | Visible Controller-seat launcher seam. |
| `ce verify-install` | Verify post-install CE release venv provenance. |
| `ce update` | Signed in-place CE update; `--check` is read-only. |
| `ce onboard` | First-run one-shot: verify/install, brain init, first governed launch. |
| `ce bootstrap` | Provision a source-clone controller/seat venv offline. |
| `ce publish-branch` | Host-side publish gate for contained seats' committed branches. |
| `ce dequeue` | Dequeue one GitHub merge-queue PR through the v3 forge bridge. |
| `ce init` | Initialize local v1 kernel state. |
| `ce claim <cmd>` | Acquire, release, or inspect advisory work claims. |
| `ce pickup <cmd>` | Triage or poll claimable pickup work. |
| `ce harness-matrix` | Print harness support matrix. |
| `ce herdr remote-attach` | Internal-only authenticated herdr remote reach attach. |

### `ce lane`

Purpose: spawn/attach visible lanes, inspect lane registry state, verify closeout, and archive transcripts.

Subcommands:

| Subcommand | Required flags | Key optional flags | Purpose |
| --- | --- | --- | --- |
| `ce lane launch` | `--controller-id`, `--lane-id`, `--role`, `--prompt`, `--prompt-sha`, `--repo-root`, `--ledger-root` | `--command`, `--claude-arg`, `--mcp-config`, `--completion-report-ref`, `--closeout-file`, `--operating-mode`, `--autonomy-class`, `--lane-kind`, `--tenant-policy`, `--runtime-policy`, `--backend`, `--reviewer-authority-ref`, `--seat-env-file`, `--claim-ticket`, `--purpose`, `--no-tmux`, `--terminal-kind`, `--json` | Spawn or attach a visible tmux/headless/herdr lane bound to a live claim. |
| `ce lane status` | `--controller-id`, `--lane-id`, `--ledger-root` | `--json` | Read the live Pane Registry record. |
| `ce lane verify` | `--controller-id`, `--lane-id`, `--ledger-root`, `--transcript`, `--stop-line` | `--completion-report`, `--json` | Verify stop line and optional completion report. |
| `ce lane archive` | `--transcript`, `--archive-root`, `--batch-slug`, `--role` | `--repo-root`, `--json` | Archive and hash a transcript under an ignored root. |

Controller launch pattern:

```bash
ce lane launch \
  --controller-id <controller-id> \
  --lane-id <lane-id> \
  --role <controller|implementer|reviewer|architect> \
  --prompt <prompt-file> \
  --prompt-sha <sha256> \
  --repo-root <repo-root> \
  --ledger-root <active-work-ledger-root> \
  --json
```

### `ce validate-pr`

Purpose: run local PR preflight against committed `base..HEAD` state.

Flags:

| Flag | Required | Purpose |
| --- | --- | --- |
| `--repo-root` | no | PR worktree root; default `.`. |
| `--base` | no | Base branch/ref; default `origin/main`. |
| `--declared-work-class` | no | One of the work classes known to the preflight gate; omitted means read exactly one declared-work-class line from the carrier/body. |
| `--head-ref` | no | PR head branch name for carrier slug; default current branch. |
| `--allow-dirty` | no | Continue despite working-tree changes; committed `base..HEAD` still defines validation. |
| `--test-command` | no | Test command to compare at base and HEAD. |

Example:

```bash
ce validate-pr \
  --repo-root . \
  --base origin/main \
  --head-ref <branch> \
  --declared-work-class feature
```

## Command Group: `cev3`

Purpose: v3 work-driving CLI for Scope lifecycle, dispatch, evidence collection, forge PR/review/merge flows, onboarding, fleet/seat status, and governed playbooks. In a v3-only install the user-facing binary may be exposed as `ce`; in this monorepo the internal console script is `cev3`.

Entry point:

```bash
cev3 --help
PYTHONPATH=validators python3 -m creator_engine_validator.v3_cli --help
```

Top-level flags:

| Flag | Purpose |
| --- | --- |
| `--version` | Print derived CE version token and exit. |
| `-h`, `--help` | Print command help. |

Main subcommands:

| Subcommand | Purpose |
| --- | --- |
| `cev3 scope` | File a Scope card with Goal, Done-when, Budget, and Change-type. |
| `cev3 ratify` | Place the human bet on a Ready Scope. |
| `cev3 drive` | Assemble a governed dispatch; `--spawn` launches the author seat. |
| `cev3 dispatch worktree` | Create a governed dispatch worktree for a claimed work item. |
| `cev3 collect` | Fold finished seat transcript/outcome into evidence. |
| `cev3 pr` | Plan or apply push + PR open through the v3 forge. |
| `cev3 review` | Dispatch a distinct governed reviewer venue; `--spawn` launches it. |
| `cev3 merge` | Gate-read or apply squash merge of a run's opened PR. |
| `cev3 seats ls` | List governed seat liveness from CE state. |
| `cev3 fleet status` | Show aggregated fleet status. |
| `cev3 playbook <cmd>` | Discover, inspect, and run governed playbooks. |
| `cev3 configure-repo` | Plan/apply GitHub repo branch protection or auto-merge settings. |
| `cev3 ruleset` | Plan/apply repo ruleset with pull-request bypass actor. |
| `cev3 review-submit` | Submit separate reviewer App approval for a run's opened PR. |
| `cev3 auto-merge` | Plan/apply per-PR auto-merge for a run's opened PR. |
| `cev3 review-pickup` | Route awaiting-review PRs to distinct non-author seats. |
| `cev3 escalation` | Manage local `AWAITING-OPERATOR` escalation records. |
| `cev3 notify` | Operator-notify feed for escalation entry/exit. |
| `cev3 reap` | Seat/venue retirement reaper. |
| `cev3 status` | List Scopes by projected stage. |
| `cev3 show` | Show one Scope with canon labels and projection. |
| `cev3 artifacts` | Enumerate Scope and run artifacts. |
| `cev3 report` | Render per-run CE Completion Report. |
| `cev3 shape` | Run Frame-to-Shape gap/question flow on a partial draft. |
| `cev3 onboard` | Verify/plan/apply install/onboard flow. |
| `cev3 carrier` | Write, stage, and verify PR path-manifest carrier files. |
| `cev3 guide` | Print in-product CE guide. |
| `cev3 cockpit` | Read-only fleet Cockpit board/governance view. |
| `cev3 session` | Launch governed session frame and status line. |
| `cev3 queue-poll` | Run bounded Integrator merge-queue repair poll. |
| `cev3 inbox` / `cev3 controller-inbox` | Read-only awaiting-decision controller inbox. |
| `cev3 queue-daemon` | Run autonomous Integrator merge-queue daemon. |
| `cev3 emergency-stop` / `cev3 queue-dequeue` | Dequeue one queued PR through emergency stop surface. |
| `cev3 approval-capability` | Controller-only approval capability wall utilities. |

### `cev3 scope`

Required arguments/flags:

| Argument or flag | Purpose |
| --- | --- |
| `ID` | Stable Scope slug. |
| `--goal` | Goal / framed problem. |
| `--done-when` | Acceptance criterion; repeatable. |
| `--change-type` | Mutation class risk tier. |

Key optional flags:

| Flag | Purpose |
| --- | --- |
| `--budget` | Fixed cap, not an estimate. |
| `--budget-unit` | `$` or `%`. |
| `--budget-window` | Accounting window. |
| `--note` | Advisory note with no secrets. |
| `--root` | Override `.ce/state` root. |

### `cev3 drive`

Required argument: `ID`.

Key flags:

| Flag | Purpose |
| --- | --- |
| `--policy` | Runtime-policy YAML to merge into run envelope. |
| `--spawn` | Materialize dispatch and spawn a governed seat. |
| `--harness` | Seat harness; `claude` default, `codex` explicit/risk-guarded. |
| `--codex-risk-override` | Value-free ratification digest accepting weaker Codex in-band boundary for high-risk Scope. |
| `--no-unattended` | Opt spawned seat back into interactive approval modals. |
| `--ticket` | Work item claim key/URL; with `--spawn`, claim lock is acquired before side effects. |
| `--root` | Override `.ce/state` root. |

### `cev3 review`

Required arguments/flags:

| Argument or flag | Purpose |
| --- | --- |
| `ID` | Scope id delivered by author run. |
| `--run` | Author run id whose opened PR is reviewed. |
| `--reviewer-actor` | Host-bound reviewer login; data only, never a token. |

Key optional flags:

| Flag | Purpose |
| --- | --- |
| `--spawn` | Provision and launch the governed reviewer venue. |
| `--venue-root` | Out-of-repo worktree zone; required with `--spawn`. |
| `--ledger-root` | Active-Work ledger root; required with `--spawn`. |
| `--controller-id` | Venue lane controller id; default `cev3-review`. |
| `--no-unattended` | Opt venue into interactive approval modals. |
| `--seat-env-file` | Owner-only env file path for reviewer credential contract; value never goes on argv. |
| `--harness` | Reviewer harness; `claude` default, `codex` currently deferred/refused. |
| `--ticket` | Work item claim key/URL; with `--spawn`, claim lock is acquired before side effects. |
| `--root` | Override `.ce/state` root. |

Example:

```bash
cev3 review <scope-id> \
  --run <author-run-id> \
  --reviewer-actor <reviewer-login> \
  --spawn \
  --venue-root <out-of-repo-venue-root> \
  --ledger-root <active-work-ledger-root>
```

## Command Group: `creator-engine-validator`

Purpose: validation and governance utility CLI. This help surface ran live in the container.

Entry point:

```bash
PYTHONPATH=validators python3 -m creator_engine_validator --help
```

Top-level flags:

| Flag | Purpose |
| --- | --- |
| `--json` | Emit machine-readable JSON where supported. |
| `--tenant TENANT` | Restrict cross-artifact checks to one tenant. |
| `--list-checks` | List enabled checks and FR references. |
| `-h`, `--help` | Print help. |

Main subcommands:

| Subcommand | Purpose |
| --- | --- |
| `check` | Run all enabled checks. |
| `check-examples` | Validate bundled well-formed/malformed examples. |
| `scan-no-limitless` | Run only no-LIMITLESS generic-path scan. |
| `scan-handoffs` | Run handoff schema check against path. |
| `scan-path-manifest` | Run path-manifest fidelity check against path. |
| `scan-active-work-ledger` | Run Active-Work ledger schema check. |
| `scan-active-work-ledger-conflicts` | Run pre-launch Active-Work ledger conflict check. |
| `scan-worktree-leases` | Run worktree lease schema check. |
| `scan-controller-keys` | Run controller key schema check. |
| `scan-completion-reports` | Run completion report checks. |
| `scan-pane-registry` | Run Pane Registry check. |
| `scan-side-effect-ledger` | Run Side-Effect Ledger check. |
| `scan-controller-runtime-contract` | Run controller runtime contract check. |
| `scan-state-boundary-contract` | Run state boundary contract check. |
| `scan-state-version-record` | Run state version record check. |
| `scan-crosswalk-register` | Run crosswalk register check. |
| `scan-terminology-v2` | Run CE terminology v2 check. |
| `scan-runtime-policy` | Run CE runtime policy check. |
| `openbao-p3-plan` | Render value-free OpenBao Phase 3 deployment plan; executes no production steps. |
| `verify-attribution` | Compare `base..HEAD` against active handoff manifests. |
| `verify-path-manifest` | PR diff path-manifest gate. |
| `verify-work-sizing-floor` | PR diff work-sizing floor gate. |
| `pco-allocate` | Allocate a worktree lane. |
| `hook-check` | Evaluate a Claude hook event and emit allow/deny/block. |
| `pco-release` | Release a worktree lane. |
| `release-stage` | Stage deterministic signed-release Pages artifacts. |

### `creator-engine-validator verify-path-manifest`

Required flags:

| Flag | Purpose |
| --- | --- |
| `--base` | Base commit/ref, e.g. PR base SHA or `origin/main`. |

Key flags:

| Flag | Purpose |
| --- | --- |
| `--manifest` | Single PR-committed carrier; mutually exclusive with `--manifest-dir`. |
| `--manifest-dir` | Per-PR carrier directory such as `.ce/pr-manifests`; discovers `<branch-slug>.md`. |
| `--head-ref` | PR head branch name; required for `--manifest-dir` mode. |
| `--require-carrier` | Fail when per-PR carrier or changelog fragment is missing. |
| `paths` | Optional scope paths; default `.`. |

Example:

```bash
PYTHONPATH=validators python3 -m creator_engine_validator verify-path-manifest \
  --base origin/main \
  --manifest-dir .ce/pr-manifests \
  --head-ref <branch> \
  --require-carrier
```

### `creator-engine-validator verify-work-sizing-floor`

Required flags:

| Flag | Purpose |
| --- | --- |
| `--base` | Base commit/ref. |
| `--declared-work-class` | One of `tiny`, `story`, `feature`, `epic`. |

### `creator-engine-validator pco-allocate`

Required flags:

| Flag | Purpose |
| --- | --- |
| `--lane-id` | Lane identifier. |
| `--worktree-path` | Path for new git worktree. |
| `--branch` | New branch name in the worktree. |
| `--envelope-ref` | Repo-relative Assignment Envelope path, or `none`. |

Key optional flags:

| Flag | Purpose |
| --- | --- |
| `--no-write-authority` | Explicitly allow `--envelope-ref none`. |
| `--controller-id` | Override controller id. |
| `--ledger-root` | Active-Work ledger root; auto-resolved if omitted. |
| `--repo-root` | Repo root; default cwd. |
| `--lease-seconds` | Lease duration; default `3600`. |
| `--pane-label` | One of `architect`, `implementer`, `controller`, `reviewer`. |

### `creator-engine-validator pco-release`

Required flags:

| Flag | Purpose |
| --- | --- |
| `--lane-id` | Lane identifier to release. |

Key optional flags:

| Flag | Purpose |
| --- | --- |
| `--controller-id` | Override controller id. |
| `--ledger-root` | Active-Work ledger root; auto-resolved if omitted. |
| `--repo-root` | Repo root; default cwd. |
| `--release-reason` | `completed`, `aborted`, `lapsed`, or `handed_off`; default `completed`. |

### `creator-engine-validator hook-check`

Required source, exactly one:

| Source flag | Purpose |
| --- | --- |
| `--input-json` | Path to Claude hook event JSON. |
| `--stdin` | Read hook event JSON from stdin. |

Key flags:

| Flag | Purpose |
| --- | --- |
| `--posture` | `auto`, `governed`, or `ungoverned`; default `auto`. |
| `--format` | `raw` or `claude`; default `raw`. |
| `--posture-root` | Root for `.hermes` posture inputs. |
| `--ledger-root` | Launch-pinned Active-Work Ledger root. |
| `--manifest-doc` | Handoff/prompt doc carrying allowed paths. |
| `--evidence-root` | Ignored evidence root prefix writable by gate. |
| `--closeout-file` | Stop closeout text path. |
| `--completion-report` | Completion report artifact path. |
| `--reviewer-authority-ref` | Launch-pinned reviewer authority envelope ref. |
