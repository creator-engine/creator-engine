# Creator Engine CLI Reference

This page is the public inventory for the `ce` command. It is grounded in the shipped CLI registry and describes the public command groups that appear in the current `ce` surface.

The `ce` command is installed by the `creator-engine-validator` package. The package name remains `creator-engine-validator`; the public command is `ce`.

There is no `ce dev` command in the v1.0 public CLI.

## First-Run And Daily Commands

| Command | Use it for |
| --- | --- |
| `ce onboard` | Verify the local install, initialize CE state, check prerequisites, and open the first governed session unless launch is skipped. |
| `ce launch` | Open or attach the visible Controller-seat launcher. |
| `ce hud` | Use the HUD alias for `ce launch`; it is an alias label, not a separate CE-native TUI. |
| `ce guide` | Print the in-product guide for the CE stages. |
| `ce cockpit` | Open the governed fleet cockpit as a read-only board and governance view. |
| `ce session` | Launch the governed session frame and status line. |

## Core Governed Workflow

| Command | Use it for |
| --- | --- |
| `ce brain` | Manage the local assertion ledger and recall surface, including `ce brain init`, assert, check, correct, sync, ingest, recall, verify, probe, and bootstrap. |
| `ce shape` | Turn an initial draft into a sharper Scope by finding gaps and asking the next questions. |
| `ce scope` | File a Scope with Goal, Done-when, and Change-type. |
| `ce ratify` | Approve a ready Scope at the human front gate. |
| `ce drive` | Assemble the governed dispatch; `ce drive --spawn` launches the seat. |
| `ce collect` | Fold a completed run transcript and outcome into evidence. |
| `ce report` | Render the per-run CE Completion Report. |
| `ce artifacts` | Enumerate Scope and run artifacts. |
| `ce status` | List Scopes by projected stage. |
| `ce show` | Show one Scope with canonical labels and projection. |

## Project And PR Commands

| Command | Use it for |
| --- | --- |
| `ce init` | Run CE-native project scaffolding with local templates. The scaffolded governance flow includes path-manifest carriers, declared work-class lines, and `ce validate-pr` preflight evidence. |
| `ce carrier` | Write, stage, and verify PR path-manifest carrier files. |
| `ce validate-pr` | Run the local PR preflight gate set against committed base-to-head state. |
| `ce pr` | Push a governed run branch and open its pull request through the forge flow. |
| `ce review` | Dispatch a distinct governed reviewer venue for an opened pull request. |
| `ce review-submit` | Submit the separate reviewer approval for a run's opened pull request. |
| `ce review-pickup` | Route awaiting-review pull requests to distinct non-author seats. |
| `ce review-spawn-provider` | Default-OFF governed reviewer spawn-provider policy seam. |
| `ce ratifier-queue` | Persist and surface controller-supplied ratifier proposals; it never approves, enqueues, merges, signs, or ratifies. |
| `ce reviewer-triage` | Plan reviewer assignment without mutating the source host. |
| `ce merge` | Read or apply the gated squash-merge decision for a run's opened pull request. |
| `ce auto-merge` | Plan or apply per-PR auto-merge for a run's opened pull request. |
| `ce configure-repo` | Plan or apply repository branch-protection and auto-merge settings. |
| `ce ruleset` | Plan or apply repository rulesets used by the governed flow. |
| `ce publish-branch` | Publish a contained seat's committed branch through the host-side gate. |

## Local Runtime And Evidence

| Command | Use it for |
| --- | --- |
| `ce lane` | Launch, inspect, verify, and archive governed visible lanes. |
| `ce ledger` | Record and verify the append-only Side-Effect Ledger hash chain. |
| `ce worker` | Allocate, run, spawn, inspect, and retire governed worker runtimes. |
| `ce fanin` | Build or inspect a local read-only evidence fan-in packet. |
| `ce event` | Append, verify, sign, replay, and index local CE-event chains. |
| `ce pcl` | Append, verify, replay, index, and merge local coordination ledgers. |
| `ce connector` | Verify connector descriptors, build read plans, fetch read-only data, and submit bounded tracker-mirror writes. |
| `ce containment-probe` | Probe live-runtime containment of a process from the operating system view. |
| `ce containment-status` | Probe fleet-seat containment from live process and runtime evidence. |
| `ce posture` | Print the read-only Controller posture banner. |
| `ce takeover` | Produce a read-only controller-continuity takeover plan and evidence packet. |
| `ce continuity-drill` | Run the scheduled benign controller-continuity drill proof. |
| `ce checkpoint` | Save a validated resume point at a clean handoff, so the next session can continue with clear, trustworthy context. |

## Queue And Coordination

| Command | Use it for |
| --- | --- |
| `ce claim` | Manage visible work-claim locks. |
| `ce pickup` | Poll for autonomous forge work pickup in read-only mode. |
| `ce dispatch` | Dispatch governed work to an execution venue. |
| `ce queue` | Preview or inspect Integration Queue state, or run the bounded integrator poll belt. |
| `ce queue-poll` | Run a bounded, witnessable merge-queue repair poll. |
| `ce queue-daemon` | Run the autonomous merge-queue daemon. |
| `ce conveyor` | Repair the merge queue by enqueuing approved, CI-green pull requests that were stranded. Use `ce conveyor sweep`. |
| `ce dequeue` | Dequeue one pull request from the GitHub merge queue through the forge bridge. |
| `ce emergency-stop` | Emergency merge-queue stop for one queued pull request. |
| `ce queue-dequeue` | Alias for `ce emergency-stop`. |
| `ce inbox` | Read the controller awaiting-decision inbox. |
| `ce controller-inbox` | Alias for `ce inbox`. |
| `ce escalation` | Manage local awaiting-operator escalation records. |
| `ce notify` | Read the operator-notify feed for awaiting-operator entry and exit. |
| `ce reap` | Retire seats and venues after terminal sentinel events. |
| `ce approval-capability` | Use controller-only approval-capability wall utilities. |

## Install, Update, And Environment

| Command | Use it for |
| --- | --- |
| `ce install` | Verify the signed install spec, plan installation, and apply only when explicitly requested. |
| `ce verify-install` | Verify post-install CE release virtual-environment provenance. |
| `ce update` | Run a signed release update or a verified main-head source build with `--track main`. |
| `ce clean-main-install` | Build and install verified `origin/main` from source while refusing hash mismatches. |
| `ce bootstrap` | Provision a source-clone controller or seat virtual environment offline. |
| `ce doctor` | Run governed-environment preflight checks and refuse host drift. |
| `ce check` | Run `creator-engine-validator` conformance checks through the `ce` wrapper. |
| `ce harness-matrix` | Emit the probed harness-support capability matrix. |
| `ce surfaces` | Inspect surface metadata, including update checks and fleet rollout planning. |

Environment variables recognized by this install/update surface:

| Variable | Use it for |
| --- | --- |
| `CE_INSTALL_ROOT` | Override the CE bootstrap install root used by the one-liner bootstrap and by validator install-provenance commands when `--install-root` is not supplied. If unset, the default root is `${CE_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}/creator-engine}/bootstrap`. |

## Fleet And Orchestration

| Command | Use it for |
| --- | --- |
| `ce seats` | List governed seat liveness from CE state. |
| `ce fleet` | Show aggregated fleet status. |
| `ce orchestrator` | Inspect orchestrator runtime records in read-only mode. |
| `ce playbook` | Discover, inspect, and run governed CE playbooks. |
| `ce automerge-decide` | Classify a pull request's mutation class and emit a dry-run auto-merge decision. |
| `ce automerge-status` | Read dry-run auto-merge decision logs. |
