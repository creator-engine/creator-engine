"""``ce`` kernel CLI — governed lane-launch + Side-Effect Ledger runtime.

Exposes the v1.0 ``ce`` entrypoint with two command families:

```text
ce lane launch       # spawn/attach a visible tmux lane bound to a live claim
ce lane status       # read live lane state
ce lane verify       # check stop line + optional completion report
ce lane archive      # hash/archive a transcript per TRANSCRIPT_ARCHIVE_PROTOCOL.md
ce ledger record     # append one redaction-safe Side-Effect Ledger record (RV1-040/041)
ce ledger verify     # validate the hash chain + replay deterministically (RV1-041)
ce worker allocate   # start a rootless-Podman worker container bound to a live claim
ce worker terminate  # revoke broker grants, stop the container, write a stopped record
ce worker gc         # reap container-instance records that outlived a released claim
ce worker status     # read a local container-instance record
ce worker spawn      # spawn a harness-agnostic CE worker seat under a scrubbed environment
ce worker run        # resolve a role definition, launch a governed worker, return findings
ce worker worktree-prune # report/apply fail-safe stale git worktree pruning
ce bootstrap         # provision a source-clone controller/seat venv offline
ce verify-install    # verify a post-install CE release venv provenance
ce update            # signed in-place CE update; --check is read-only
ce clean-main-install # build/install verified origin/main from source, no release signature
ce onboard           # first-run one-shot: verify/install + brain-init + first governed launch
ce publish-branch   # host-side publish gate for contained seats' committed branches
ce herdr remote-attach # attach through authenticated herdr remote reach, not docker exec
ce fanin build       # aggregate local evidence into a deterministic fan-in packet (RV1-070/071)
ce fanin inspect     # verify a fan-in packet's content hash + shape, read-only
ce queue dry-run     # preview a serialized canonical-branch landing order, no authority (RV1-082)
ce queue inspect     # verify a dry-run landing preview's content hash + shape, read-only
ce queue poll        # run a bounded Integrator merge-queue repair poll
ce conveyor sweep    # enqueue approved+green creator-engine PRs stranded outside merge queue
ce dequeue           # dequeue one PR from GitHub's merge queue through the v3 forge bridge
ce event append      # append a shape-only-signed CE-event block to a local chain (G2.003.1)
ce event verify      # validate an on-disk CE-event chain + head manifest, read-only
ce event sign        # refresh a draft block's shape-only signature + content hash (no crypto)
ce event replay      # deterministic ordered read-only projection of a CE-event chain
ce event index       # deterministic content-hashed read-only index of a CE-event chain
ce pcl append        # append a shape-only-signed PCL record to a tracked local ledger (G2.004.1)
ce pcl verify        # validate an on-disk PCL ledger + head manifest, read-only
ce pcl replay        # deterministic ordered read-only projection of a PCL ledger
ce pcl index         # deterministic content-hashed index of a PCL ledger (written to the ignored cache)
ce pcl merge         # deterministic conflict-detecting merge projection of >=2 ledgers (read-only)
ce brain init        # idempotently bootstrap a valid genesis brain assertion ledger
ce brain assert      # append a structured Knowledge-SSOT assertion under .ce/state
ce brain check       # deterministically return the active assertion or unknown
ce brain correct     # append a supersession marker plus corrected assertion
ce brain sync        # reconcile ignored local brain runtime state from tracked canonical brain sources
ce brain ingest      # derive/update the local rebuildable recall vector store
ce brain recall      # hybrid (semantic+keyword) recall: SSOT-precedence, tier-tagged pointers
ce brain verify      # validate the local brain assertion ledger
ce brain probe       # freshly interrogate named Knowledge-SSOT capability probes
ce brain bootstrap   # emit the deterministic injection bootstrap payload
ce orchestrator status # read Orchestrator runtime records (read-only)
ce connector verify     # validate a connector descriptor + Mission-Brief pair (offline) (G2.005.1)
ce connector plan       # build + validate a read-only read plan (offline)
ce connector fetch      # execute one read-only GET via an injectable client; --provider github|jira|gitlab (G2.005.3); credential by reference; offline fails closed
ce connector write-plan # build + validate a strict-mode tracker_mirror write plan (offline) (G2.005.2)
ce connector submit     # execute one bounded tracker_mirror write; credential REQUIRED by reference; offline fails closed
ce surfaces check-updates # read-only upstream version detection from surfaces/manifest.yaml
ce surfaces fleet-rollout # seat-by-seat fleet rollout of updated surface versions
ce init              # scaffold a CE-governed project with local templates
ce containment-status   # probe fleet seat containment from live pids and runtime evidence
ce posture          # print a deterministic read-only Controller posture banner
ce validate-pr          # run local PR preflight against committed base..HEAD state
ce automerge-decide     # classify a PR's mutation class + emit AUTO/GESTURE decision (dry-run only; no merge)
ce automerge-status     # read dry-run automerge decision logs (read-only; no merge)
ce automerge-kill-switch # read or toggle durable live-policy automerge kill-switch
ce takeover             # read-only controller continuity takeover evidence packet
ce continuity-drill     # scheduled benign Controller continuity drill proof
```

This kernel also wires ``ce launch`` / ``ce hud`` (Gate 6, RV1-063) — the
deterministic visible Controller-seat launcher — and the CC-G-D Ring 0 governed
Claude surfaces (``--claude-arg``/``--mcp-config``/``--completion-report-ref``/
``--closeout-file`` on ``launch`` and ``lane launch``) that refuse prohibited
Claude flags and pin ``--setting-sources project`` + strict MCP before any side
effect. It does NOT implement image build/pull/push or any provider/credential
setup, and CC-G-D launches no MCP server (config-posture only). The worker
runtime reaches the container engine and credential broker only via injectable
seams and fails closed when ``podman`` is unavailable. It never prints secrets
or environment variables.

Prose contracts: ``docs/operations/GOVERNED_LANE_LAUNCH_PROTOCOL.md``,
``docs/operations/SIDE_EFFECT_LEDGER_PROTOCOL.md``, and
``docs/operations/WORKER_CONTAINER_PROTOCOL.md``.
"""
from __future__ import annotations

import argparse
import importlib
from importlib import metadata as importlib_metadata
import json
import os
import re
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Sequence

from . import (
    brain_bootstrap,
    brain_reconcile,
    brain_probe,
    brain_runtime,
    containment_probe,
    containment_status,
    brain_ingest_runtime,
    brain_recall,
    brain_recall_surface,
    bootstrap_runtime,
    check_profiles,
    ce_ops_triage_queue,
    ce_event_runtime,
    ce_onboard,
    ce_provenance,
    checkpoint_runtime,
    connector_runtime,
    continuity_drill_runtime,
    controller_posture,
    dependency_unlock,
    dispatch_plan,
    doctor_runtime,
    fanin_runtime,
    forge_triage,
    hook_check,
    init_runtime,
    integration_queue_dry_run,
    journey_guidance,
    lane_runtime,
    launch_runtime,
    main_head_install,
    onboard_connection_status,
    orchestrator_status,
    pcl_runtime,
    playbook_runtime,
    project_init,
    publish_gate,
    pr_preflight,
    reviewer_triage,
    seat_lifecycle,
    support_runtime,
    side_effect_ledger_runtime,
    takeover_runtime,
    transcript_archive,
    update as update_runtime,
    version,
    work_claims,
    worker_run,
    worker_spawn,
    worker_runtime,
    worktree_prune,
)
from ._versions import V3_LOCAL_STATE_ROOT
from .daemon_heartbeat import DaemonHeartbeatEmitter
from . import daemon_heartbeat_alarm
from .checks.side_effect_ledger import EFFECT_KINDS, EFFECT_STATUSES
from .checks import ce_runtime_policy
from .checks import ce_brain_assertions
from .checks import ce_brain_drift
from .surfaces import check_updates as surfaces_check_updates
from .surfaces import fleet_rollout as surfaces_fleet_rollout
from .tmux_adapter import TmuxAdapter


def _make_tmux_adapter():
    """Factory for the tmux adapter (monkeypatchable in tests)."""
    return TmuxAdapter()


def _make_worker_runner():
    """Factory for the worker container-engine runner (monkeypatchable in tests)."""
    return worker_runtime.PodmanCommandRunner()


def _make_worker_broker():
    """Factory for the worker credential broker (monkeypatchable in tests)."""
    return worker_runtime.NullCredentialBroker()


def _make_worker_spawn_launcher():
    """Factory for the worker-spawn launcher seam (monkeypatchable in tests)."""
    return worker_spawn.LaunchRuntimeWorkerLauncher()


def _make_worker_run_launcher():
    """Factory for worker-run launch (monkeypatchable in tests)."""
    return worker_spawn.LaunchRuntimeWorkerLauncher()


def _make_worker_run_seeder():
    """Factory for worker-run prompt delivery (monkeypatchable in tests)."""
    return worker_run.TmuxPromptSeeder()


def _make_worker_run_collector(timeout_seconds: float):
    """Factory for worker-run findings collection (monkeypatchable in tests)."""
    return worker_run.FileFindingsCollector(timeout_seconds=timeout_seconds)


def _make_herdr_attach_runner():
    """Factory for interactive herdr remote attach (monkeypatchable in tests)."""
    herdr_session = _herdr_session_module()
    return herdr_session.SubprocessHerdrAttachRunner()


def _herdr_session_module():
    """Load the v3 herdr runner only inside the explicit herdr command seam."""
    return importlib.import_module("creator_engine_validator.runner.herdr_session")


# Command groups shipped INTERNAL-only for now: present in the `ce` CLI (for
# fleet/dev use) but intentionally kept OFF the public product surface. They are
# hidden from `ce --help` and are EXEMPT from the public-README "documents every
# command group" requirement (the inventory guard still tracks them so additions
# are never silent). `herdr` (authenticated remote reach-plane) is internal pending
# internal testing and GRADUATES to a public product command in a later release
# (ce-ops#237).
INTERNAL_COMMAND_GROUPS = frozenset(
    {"herdr", "ask", "support", "triage", "automerge-kill-switch", "dependency-unlock"}
)

PRE_ARGPARSE_DISPATCH_GROUPS: frozenset[str] = frozenset({"conveyor", "press-merge-evidence"})
PRE_ARGPARSE_INTERNAL_GROUPS: frozenset[str] = frozenset({"press-merge-evidence"})

_V3_FORWARDED_ENV = "CE_V3_FORWARDED"

_NATIVE_ONBOARD_INSTALLER_FLAGS = frozenset(
    {"--spec", "--answers", "--answers-schema", "--plan", "--apply", "--inventory"}
)

CLAIM_LIFECYCLE_STATES = ("claimed", "in-build", "ready", "harvested", "landed", "released", "abandoned")


def _maybe_refuse_native_onboard_installer_flags(argv: Sequence[str]) -> int | None:
    if not argv or argv[0] != "onboard":
        return None
    matched = []
    for token in argv[1:]:
        flag = token.split("=", 1)[0]
        if flag in _NATIVE_ONBOARD_INSTALLER_FLAGS and flag not in matched:
            matched.append(flag)
    if not matched:
        return None
    print(
        "ce onboard: installer-only flag(s) "
        + ", ".join(matched)
        + " belong to the installer flow; use `ce install <same args>`.",
        file=sys.stderr,
    )
    return 2


V3_FORWARDING_SHIMS: dict[str, tuple[str, str]] = {
    "seats": ("list governed seat liveness from CE state", "seats"),
    "fleet": ("aggregated fleet status", "fleet"),
    "scope": ("file a Scope (Goal/Done-when/Change-type)", "scope"),
    "shape": ("run the Frame->Shape grill-me on a partial draft (gaps + questions)", "shape"),
    "ratify": ("approve a Ready Scope (human-only front gate)", "ratify"),
    "drive": ("assemble the governed dispatch (front gate); --spawn launches the seat", "drive"),
    "dispatch": ("dispatch governed work to an execution venue", "dispatch"),
    "collect": ("fold a finished seat run's transcript + outcome into evidence", "collect"),
    "pr": ("push the seat's authored branch + open its PR through the v3 forge", "pr"),
    "review": ("dispatch a distinct CE-governed reviewer venue for a run's opened PR", "review"),
    "merge": ("gate-read (or apply) a squash-merge of a run's opened PR", "merge"),
    "configure-repo": ("plan/apply GitHub repo branch-protection or repo auto-merge setting", "configure-repo"),
    "ruleset": ("plan/apply a repo ruleset with pull_request bypass actor", "ruleset"),
    "review-submit": ("submit the separate reviewer App's APPROVE for a run's opened PR", "review-submit"),
    "auto-merge": ("plan/apply GraphQL per-PR auto-merge for a run's opened PR", "auto-merge"),
    "review-pickup": ("controller review-pickup: route awaiting-review PRs to distinct non-author seats", "review-pickup"),
    "review-spawn-provider": ("default-OFF governed reviewer spawn-provider policy seam", "review-spawn-provider"),
    "ratifier-queue": ("persist and surface caller-supplied ratifier proposals; never ratifies or acts", "ratifier-queue"),
    "escalation": ("manage local AWAITING-OPERATOR escalation records", "escalation"),
    "notify": ("Operator-notify feed for AWAITING-OPERATOR entry/exit", "notify"),
    "reap": ("seat/venue retirement reaper for terminal sentinel events", "reap"),
    "status": ("list Scopes by projected stage", "status"),
    "show": ("show one Scope (canon labels + projection)", "show"),
    "artifacts": ("enumerate a Scope's (and a run's) artifacts", "artifacts"),
    "report": ("render the per-run CE Completion Report", "report"),
    "install": ("two-mode install: verify the signed spec, plan, and explicitly apply", "install"),
    "carrier": ("write, stage, and verify the PR path-manifest carrier files", "carrier"),
    "guide": ("print the in-product CE guide (what CE is + the five stages)", "guide"),
    "cockpit": ("the governed fleet Cockpit - read-only board + governance view", "cockpit"),
    "session": ("launch the governed session frame + status line", "session"),
    "queue-poll": ("run a bounded, witnessable Integrator merge-queue repair poll", "queue-poll"),
    "inbox": ("read-only controller awaiting-decision inbox", "inbox"),
    "controller-inbox": ("alias for inbox; read-only controller awaiting-decision inbox", "controller-inbox"),
    "queue-daemon": ("run the autonomous Integrator merge-queue daemon", "queue-daemon"),
    "emergency-stop": ("emergency merge-queue stop: dequeue one queued PR", "emergency-stop"),
    "queue-dequeue": ("alias for emergency-stop; dequeue one queued PR", "queue-dequeue"),
    "approval-capability": ("controller-only approval capability wall utilities", "approval-capability"),
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ce",
        description="Creator Engine kernel (v1.0 Gate 3 lane-launch surface)",
        epilog=journey_guidance.stage_map_text(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # ce-ops#25: top-level ``ce --version`` prints the derived CE token
    # (``<semver>+<short-sha>``) to stdout and exits (lazy — git resolves only
    # when the flag is passed, never on every command).
    version.add_version_flag(parser)
    groups = parser.add_subparsers(dest="group")

    dequeue = groups.add_parser(
        "dequeue",
        help="dequeue one GitHub merge-queue PR through the v3 forge bridge",
    )
    dequeue.add_argument("pr_number", type=int, metavar="PR", help="pull request number")
    dequeue.add_argument("--repo", required=True, help="owner/name repository scope")
    dequeue.add_argument("--token-env", default="GH_TOKEN", help="env var containing the GitHub token")
    dequeue.add_argument(
        "--convert-to-draft",
        action="store_true",
        help="also convert the PR back to draft after dequeue",
    )
    dequeue.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    verify_install = groups.add_parser(
        "verify-install",
        help="verify a post-install CE release venv provenance",
    )
    verify_install.add_argument(
        "--install-root",
        default=None,
        help="CE bootstrap install root (default: CE_INSTALL_ROOT or the installer default)",
    )
    verify_install.add_argument(
        "--offline",
        action="store_true",
        help="local-only verification; skip live SHA256SUMS comparison",
    )
    verify_install.add_argument("--json", action="store_true", dest="json_output")

    update = groups.add_parser(
        "update",
        help="signed release update, or verified main-HEAD source build with --track main",
    )
    update.add_argument(
        "--track",
        default="release",
        choices=("release", "main"),
        help="update track: signed release mirror, or verified origin/main source build",
    )
    update.add_argument(
        "--check",
        action="store_true",
        help="resolve and verify without mutating",
    )
    update.add_argument(
        "--install-root",
        default=None,
        help="CE bootstrap install root (default: CE_INSTALL_ROOT or installer default)",
    )
    update.add_argument(
        "--site",
        default=update_runtime.DEFAULT_SITE,
        help="CE mirror site (default: https://creator-engine.dev)",
    )
    update.add_argument(
        "--trust-anchor-url",
        default=update_runtime.DEFAULT_TRUST_ANCHOR_URL,
        help="out-of-band ce-root-v1 DNS TXT resolver URL",
    )
    update.add_argument(
        "--repo-root",
        default=".",
        help="source checkout root for --track main (default: cwd)",
    )
    update.add_argument(
        "--remote",
        default=main_head_install.REMOTE,
        help="git remote for --track main (must be origin)",
    )
    update.add_argument(
        "--branch",
        default=main_head_install.BRANCH,
        help="git branch for --track main (must be main)",
    )
    update.add_argument("--json", action="store_true", dest="json_output")

    clean_main = groups.add_parser(
        "clean-main-install",
        help="build and install verified origin/main from source, refusing on any hash mismatch",
    )
    clean_main.add_argument("--repo-root", default=".", help="source checkout root (default: cwd)")
    clean_main.add_argument(
        "--install-root",
        default=None,
        help="CE bootstrap install root (default: CE_INSTALL_ROOT or installer default)",
    )
    clean_main.add_argument(
        "--remote",
        default=main_head_install.REMOTE,
        help="git remote to resolve (must be origin)",
    )
    clean_main.add_argument(
        "--branch",
        default=main_head_install.BRANCH,
        help="git branch to resolve (must be main)",
    )
    clean_main.add_argument(
        "--check",
        action="store_true",
        help="resolve, build, and verify without installing",
    )
    clean_main.add_argument("--json", action="store_true", dest="json_output")

    surfaces = groups.add_parser(
        "surfaces",
        help="inspect rented surface metadata",
    )
    surfaces_sub = surfaces.add_subparsers(dest="surfaces_cmd")
    surfaces_check = surfaces_sub.add_parser(
        "check-updates",
        help="read-only upstream version detection from surfaces/manifest.yaml",
    )
    surfaces_check.add_argument("--repo-root", default=".", help="repo root (default: cwd)")
    surfaces_check.add_argument(
        "--manifest",
        default=None,
        help="surface manifest path (default: <repo-root>/surfaces/manifest.yaml)",
    )
    surfaces_check.add_argument("--json", action="store_true", dest="json_output")
    surfaces_rollout = surfaces_sub.add_parser(
        "fleet-rollout",
        help="seat-by-seat fleet rollout of updated surface versions",
    )
    surfaces_rollout.add_argument(
        "--manifest",
        default=None,
        help="path to surfaces/manifest.yaml",
    )
    surfaces_rollout.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="herdr readiness timeout per seat (seconds)",
    )
    surfaces_rollout.add_argument(
        "--dry-run",
        action="store_true",
        help="show plan without executing",
    )

    # ce onboard — the ce-ops#197 first-run one-shot orchestrator. Sequences the
    # six phases (doctor → install → verify-install → fix-path → bootstrap →
    # first governed launch), idempotent + resumable + gracefully degrading.
    onboard = groups.add_parser(
        "onboard",
        help="first-run one-shot: verify/install + brain-init + first governed launch (ce-ops#197)",
    )
    onboard.add_argument("--repo-root", default=".", help="repo root to onboard (default: cwd)")
    onboard.add_argument(
        "--state-root",
        default=V3_LOCAL_STATE_ROOT,
        help=f"CE local state root for brain-init (default: {V3_LOCAL_STATE_ROOT})",
    )
    onboard.add_argument(
        "--ledger-root",
        default=None,
        help="path to the active-work-ledger for first-launch lifecycle registration",
    )
    onboard.add_argument(
        "--install-mode",
        default=None,
        choices=list(ce_onboard.INSTALL_MODES),
        help=(
            "install mode (default: auto per §A.5 — hybrid when an agent is present, "
            "else guided; NEVER print). print = manual fallback; skip = dev override"
        ),
    )
    onboard.add_argument(
        "--install-root",
        default=None,
        help="CE bootstrap install root passed to the verify-install provenance gate",
    )
    onboard.add_argument(
        "--harness",
        default="claude",
        help="first-launch Controller-seat harness (default: claude)",
    )
    onboard.add_argument(
        "--no-launch",
        action="store_true",
        help="do everything up to (not including) the first governed launch",
    )
    onboard.add_argument(
        "--no-fix-path",
        action="store_true",
        help="opt out of the managed CE-marked profile PATH block (Decision 4 default-on)",
    )
    onboard.add_argument(
        "--offline",
        action="store_true",
        help="verify provenance against local install-state only (no live SHA256SUMS)",
    )
    onboard.add_argument(
        "--yes",
        action="store_true",
        dest="assume_yes",
        help="non-interactive: refuse with the missing list rather than silently proceed",
    )
    onboard.add_argument(
        "--emit-manifest",
        action="store_true",
        dest="emit_manifest",
        help="emit the machine-readable phase manifest (consequence-class + reversibility) and exit",
    )
    onboard.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    bootstrap = groups.add_parser(
        "bootstrap",
        help="provision a source-clone controller/seat venv offline",
    )
    bootstrap.add_argument("--repo-root", default=".", help="source checkout root (default: cwd)")
    bootstrap.add_argument("--venv", default=None, help="target venv directory (default: .venv)")
    bootstrap.add_argument(
        "--python",
        dest="target_python",
        default=None,
        help="target interpreter path (overrides --venv)",
    )
    bootstrap.add_argument("--json", action="store_true", dest="json_output")

    checkpoint = groups.add_parser(
        "checkpoint",
        help="persist a validated, local-only resume checkpoint; never grants authority",
    )
    checkpoint.add_argument("--facts", required=True, type=Path, help="JSON facts document matching checkpoint-input.schema.yaml")
    checkpoint.add_argument("--clean-boundary", required=True, help="why this is a clean handoff boundary")
    checkpoint.add_argument("--prior-checkpoint", default=None, help="optional prior checkpoint path; it is recorded, not read")
    checkpoint.add_argument("--repo-root", default=".", help="repository root containing the untracked .ce/state/research root")
    checkpoint.add_argument("--as-of", default=None, help="optional injected UTC RFC3339 timestamp for deterministic output")
    checkpoint.add_argument("--json", action="store_true", dest="json_output", help="emit the same result fields as JSON")

    lane = groups.add_parser("lane", help="governed visible lane-launch primitive")
    lane_sub = lane.add_subparsers(dest="lane_cmd")

    launch = lane_sub.add_parser("launch", help="spawn/attach a visible tmux lane bound to a live claim")
    launch.add_argument("--controller-id", required=True)
    launch.add_argument("--lane-id", required=True)
    launch.add_argument(
        "--role", required=True, choices=sorted(lane_runtime.VISIBILITY_REQUIRED_ROLES)
    )
    launch.add_argument("--prompt", required=True, help="path to the consumed prompt pointer")
    launch.add_argument("--prompt-sha", required=True, help="expected byte-level SHA256 of --prompt")
    launch.add_argument("--repo-root", required=True)
    launch.add_argument("--ledger-root", required=True, help="path to .ce/state/active-work-ledger")
    launch.add_argument("--handoff", default=None, help="optional consumed handoff pointer path")
    launch.add_argument("--handoff-sha", default=None, help="expected byte-level SHA256 of --handoff")
    launch.add_argument(
        "--command",
        default=None,
        help="optional local command to run in the pane (defaults to a safe inert placeholder)",
    )
    # CC-G-D Ring 0 governed-Claude surfaces for a lane whose --command is `claude`.
    launch.add_argument(
        "--claude-arg",
        action="append",
        dest="claude_arg",
        default=None,
        help="repeatable extra arg appended to a claude --command (use --claude-arg=<value> for dashed values)",
    )
    launch.add_argument(
        "--mcp-config",
        dest="mcp_config",
        default=None,
        help="CE-owned MCP config path inside the repo for strict MCP pinning",
    )
    launch.add_argument(
        "--completion-report-ref",
        dest="completion_report_ref",
        default=None,
        help="deterministic completion-report pointer for Ring 0 closeout verification",
    )
    launch.add_argument(
        "--closeout-file",
        dest="closeout_file",
        default=None,
        help="deterministic closeout file pointer for Ring 0 closeout verification",
    )
    # G2.002.1 operating-mode runtime carriers. `strict` is the default; elevated
    # modes are refused without an Operator-ratified tenant policy.
    launch.add_argument(
        "--operating-mode",
        dest="operating_mode",
        default="strict",
        choices=sorted(lane_runtime.OPERATING_MODES),
        help="lane operating mode (default: strict); auto/transcendence require --tenant-policy",
    )
    launch.add_argument(
        "--autonomy-class",
        dest="autonomy_class",
        default=None,
        help="optional autonomy class carrier (G2.002.0 enum)",
    )
    launch.add_argument(
        "--lane-kind",
        dest="lane_kind",
        default=None,
        choices=sorted(lane_runtime.LANE_KINDS),
        help="optional lane kind carrier (read-only/implementation/review/approval/merge/audit)",
    )
    launch.add_argument(
        "--tenant-policy",
        dest="tenant_policy",
        default=None,
        help="path to an Operator-ratified operating-mode-policy sidecar that ratifies an elevated mode",
    )
    launch.add_argument(
        "--runtime-policy",
        dest="runtime_policy",
        default=None,
        help="v3.5-F: path to the ratified runtime policy whose resource_envelopes "
        "bound this seat (systemd-run --user wrap); enforce refuses loudly on an "
        "unsupported host; advisory/off require a resource_optout ratification binding",
    )
    launch.add_argument(
        "--backend",
        choices=ce_runtime_policy.CLI_BACKEND_CHOICES,
        default=None,
        help="runtime backend selector carried by --runtime-policy (gvisor aliases to gvisor-proxy)",
    )
    launch.add_argument(
        "--ratification-evidence",
        dest="ratification_evidence_ref",
        default=None,
        help="inherited ratification-evidence pointer carried for elevated modes / privileged lane kinds",
    )
    launch.add_argument(
        "--reviewer-authority-ref",
        dest="reviewer_authority_ref",
        default=None,
        help="G2.007.3: reviewer-authority envelope ref for a distinct reviewer venue "
        "(role=reviewer + --lane-kind review); validated then exported to the pane env "
        "as CE_REVIEWER_AUTHORITY_REF for the in-band hook",
    )
    launch.add_argument(
        "--mint-reviewer-authority",
        action="store_true",
        help="G11: mint a lane-scoped reviewer-authority envelope in ignored ledger "
        "state, validate it, then inject it into a distinct reviewer venue; mutually "
        "exclusive with --reviewer-authority-ref",
    )
    launch.add_argument(
        "--reviewer-authority-pr",
        dest="reviewer_authority_pr_number",
        type=int,
        default=None,
        help="PR number bound into a minted reviewer-authority envelope",
    )
    launch.add_argument(
        "--reviewer-authority-head-sha",
        default=None,
        help="PR head SHA bound into a minted reviewer-authority envelope",
    )
    launch.add_argument(
        "--reviewer-authority-actor",
        default=None,
        help="reviewer login bound into a minted reviewer-authority envelope (never a token)",
    )
    launch.add_argument(
        "--reviewer-authority-pr-author",
        default=None,
        help="target PR author login bound into a minted reviewer-authority envelope; "
        "must differ from --reviewer-authority-actor",
    )
    launch.add_argument(
        "--reviewer-authority-ratified-prompt-sha",
        default=None,
        help="ratified reviewer prompt SHA bound into a minted envelope; defaults to --prompt-sha",
    )
    launch.add_argument(
        "--reviewer-authority-emitting-role",
        default="controller",
        choices=["operator", "controller", "architect", "implementer", "reviewer", "verification", "agent_reviewer"],
        help="canonical non-ratifying emitting role for a minted reviewer-authority envelope",
    )
    launch.add_argument(
        "--seat-env-file",
        dest="seat_env_file",
        default=None,
        help="v3.1-G2f (F4/D2): path to an owner-only (0600-class) env file sourced into "
        "the seat process via an exec-wrap before launch — the per-seat credential "
        "contract (e.g. a reviewer token). The file PATH transits argv; the secret VALUE "
        "never enters argv, the tmux server, or any record. Refused if missing or "
        "group/world-accessible",
    )
    launch.add_argument(
        "--claim-ticket",
        dest="claim_ticket",
        default=None,
        help="ce-ops#38: acquire + verify a work-claim lock on this ticket "
        "(owner/name#N / issue URL / N inside the slug) BEFORE any lane side "
        "effect; a foreign active claim refuses the launch",
    )
    launch.add_argument(
        "--purpose",
        default=None,
        help="operator-readable purpose recorded in the governed seat lifecycle record",
    )
    launch.add_argument("--host-id", default=lane_runtime.DEFAULT_HOST_ID)
    launch.add_argument("--pane-id", default=None)
    launch.add_argument("--session", default=None, help="tmux session name")
    launch.add_argument("--window", default=None, help="tmux window name")
    launch.add_argument("--worktree-path", default=None)
    launch.add_argument("--branch", default=None)
    launch.add_argument("--envelope-ref", default=None)
    launch.add_argument(
        "--no-tmux",
        action="store_true",
        help=(
            "request the logged headless operator-inspectable visibility backend "
            "instead of tmux"
        ),
    )
    launch.add_argument(
        "--terminal-kind",
        choices=["tmux", "headless", "herdr"],
        default=None,
        help="visibility backend terminal kind for the lane (default: tmux)",
    )
    launch.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit the machine-readable launch record (pane_path + the Pane Registry record) — "
        "the v3.1-G2b consumption seam for the reviewer-venue bridge; default output unchanged",
    )

    st = lane_sub.add_parser("status", help="read the live Pane Registry record for a lane")
    st.add_argument("--controller-id", required=True)
    st.add_argument("--lane-id", required=True)
    st.add_argument("--ledger-root", required=True)
    st.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    vf = lane_sub.add_parser("verify", help="verify a lane closeout (stop line + completion report)")
    vf.add_argument("--controller-id", required=True)
    vf.add_argument("--lane-id", required=True)
    vf.add_argument("--ledger-root", required=True)
    vf.add_argument("--transcript", required=True)
    vf.add_argument("--stop-line", required=True)
    vf.add_argument("--completion-report", default=None)
    vf.add_argument("--json", action="store_true", dest="json_output")

    ar = lane_sub.add_parser("archive", help="archive + hash a transcript under an ignored root")
    ar.add_argument("--transcript", required=True)
    ar.add_argument("--archive-root", required=True)
    ar.add_argument("--batch-slug", required=True)
    ar.add_argument("--role", required=True)
    ar.add_argument("--repo-root", default=None, help="repo root for the git-ignore check")
    ar.add_argument("--json", action="store_true", dest="json_output")

    ledger = groups.add_parser("ledger", help="Side-Effect Ledger runtime (append-only hash chain)")
    ledger_sub = ledger.add_subparsers(dest="ledger_cmd")

    rec = ledger_sub.add_parser("record", help="append one redaction-safe Side-Effect Ledger record")
    rec.add_argument("--controller-id", required=True)
    rec.add_argument("--lane-id", required=True)
    rec.add_argument("--claim-ref", required=True, help="claim path relative to --active-work-ledger-root")
    rec.add_argument("--effect-id", required=True)
    rec.add_argument("--effect-kind", required=True, choices=sorted(EFFECT_KINDS))
    rec.add_argument("--effect-status", required=True, choices=sorted(EFFECT_STATUSES))
    rec.add_argument("--summary", required=True)
    rec.add_argument("--occurred-at", required=True, help="ISO-8601 UTC timestamp or source-controlled ref")
    rec.add_argument("--repo-root", required=True)
    rec.add_argument("--side-effect-ledger-root", required=True)
    rec.add_argument("--active-work-ledger-root", required=True, help="path to .ce/state/active-work-ledger")
    rec.add_argument("--actor-role", default=None, choices=["controller", "architect", "implementer", "reviewer", "verification"])
    rec.add_argument("--pane-ref", default=None)
    rec.add_argument("--subject-ref", default=None)
    rec.add_argument("--evidence-ref", action="append", dest="evidence_refs", default=None, help="repeatable redaction-safe evidence reference")
    rec.add_argument("--redaction", action="append", dest="redactions", default=None, help="repeatable redaction note")
    rec.add_argument("--details-json", default=None, help="non-secret metadata as a JSON object (arrays/scalars rejected)")
    rec.add_argument("--json", action="store_true", dest="json_output")

    lv = ledger_sub.add_parser("verify", help="validate the Side-Effect Ledger hash chain and replay it")
    lv.add_argument("--side-effect-ledger-root", required=True)
    lv.add_argument("--active-work-ledger-root", default=None, help="optional: bind each record to a live claim")
    lv.add_argument("--controller-id", default=None, help="optional: restrict verification to one controller")
    lv.add_argument("--lane-id", default=None, help="optional: restrict verification to one lane")
    lv.add_argument("--json", action="store_true", dest="json_output")

    worker = groups.add_parser("worker", help="worker isolation/spawn runtime")
    worker_sub = worker.add_subparsers(dest="worker_cmd")

    wsp = worker_sub.add_parser("spawn", help="spawn a governed harness-agnostic CE worker")
    wsp.add_argument("--role", required=True, choices=sorted(worker_spawn.WORKER_ROLES))
    wsp.add_argument("--harness", required=True, choices=sorted(launch_runtime.SUPPORTED_HARNESSES))
    wsp.add_argument("--worktree", required=True, help="existing worker worktree path; must differ from the caller cwd")
    wsp.add_argument("--scope-id", required=True, help="ticket/scope identifier carried into the worker record")
    prompt = wsp.add_mutually_exclusive_group(required=True)
    prompt.add_argument("--prompt-file", default=None, help="prompt file consumed by digest/ref; body is not recorded")
    prompt.add_argument("--brief", default=None, help="inline brief digested but not recorded")
    wsp.add_argument("--dry-run", action="store_true", help="plan only; no launch and no worker.yaml write")
    wsp.add_argument("--depth", type=int, default=None, help="worker recursion depth (default: CE_WORKER_DEPTH+1 or 1)")
    wsp.add_argument("--max-depth", type=int, default=worker_spawn.DEFAULT_MAX_DEPTH, help="fail-closed recursion depth bound")
    wsp.add_argument("--parent-id", default=None, help="parent/foreman id; defaults from CE_WORKER_ID/CE_FOREMAN_ID/CE_CONTROLLER_ID")
    wsp.add_argument("--worker-id", default=None, help="optional stable worker id; otherwise derived from value-free inputs")
    wsp.add_argument("--json", action="store_true", dest="json_output")

    wrun = worker_sub.add_parser(
        "run",
        help="run a sanctioned .claude/agents role brief in a governed worker lane and return findings",
    )
    wrun.add_argument("--role", required=True, help="role name from .claude/agents/<role>.md")
    wrun.add_argument("--brief", required=True, help="brief file to run")
    wrun.add_argument("--repo-root", default=".", help="repo root containing .claude/agents (default: cwd)")
    wrun.add_argument("--worktree", default=None, help="existing worker worktree path (default: --repo-root)")
    wrun.add_argument("--harness", default="claude", choices=sorted(launch_runtime.SUPPORTED_HARNESSES))
    wrun.add_argument("--run-id", default=None, help="optional run id for .ce/state/worker-runs")
    wrun.add_argument("--parent-id", default=None, help="parent/foreman id; defaults from worker-spawn environment")
    wrun.add_argument("--worker-id", default=None, help="optional stable worker id for the spawned lane")
    wrun.add_argument(
        "--findings-timeout",
        type=float,
        default=300.0,
        help="seconds to wait for the worker findings artifact (default: 300)",
    )
    wrun.add_argument("--json", action="store_true", dest="json_output")

    wse = worker_sub.add_parser(
        "scrub-env",
        help="emit a scrubbed worker environment for a bridge-launched worker",
    )
    wse.add_argument("--worker-id", required=True)
    wse.add_argument("--role", required=True, choices=sorted(worker_spawn.WORKER_ROLES))
    wse.add_argument("--scope-id", required=True)
    wse.add_argument("--depth", type=int, required=True)
    wse.add_argument("--parent-id", default=None)
    wse.add_argument("--home-path", required=True)
    wse.add_argument("--json", action="store_true", dest="json_output")

    wa = worker_sub.add_parser("allocate", help="start a worker container bound to a live claim under a ratified policy")
    wa.add_argument("--policy", required=True, help="path to the ratified worker-container policy record")
    wa.add_argument("--controller-id", required=True)
    wa.add_argument("--lane-id", required=True)
    wa.add_argument("--claim-ref", required=True, help="claim path relative to --active-work-ledger-root")
    wa.add_argument("--lease-ref", required=True, help="lease path relative to --active-work-ledger-root")
    wa.add_argument("--active-work-ledger-root", required=True, help="path to .ce/state/active-work-ledger")
    wa.add_argument("--container-instance-root", required=True, help="root for container-instance records")
    wa.add_argument("--instance-id", required=True)
    wa.add_argument("--started-at", default=None, help="ISO-8601 UTC start timestamp (defaults to now)")
    wa.add_argument("--details-json", default=None, help="non-secret metadata as a JSON object (secret-shaped values refused)")
    wa.add_argument("--side-effect-ledger-root", default=None, help="optional: record a container_started side effect")
    wa.add_argument("--repo-root", default=None, help="repo root (required with --side-effect-ledger-root)")
    wa.add_argument("--json", action="store_true", dest="json_output")

    wt = worker_sub.add_parser("terminate", help="revoke broker grants, stop the container, write a stopped record")
    wt.add_argument("--instance-id", required=True)
    wt.add_argument("--claim-id", required=True)
    wt.add_argument("--container-instance-root", required=True)
    wt.add_argument(
        "--reason",
        required=True,
        choices=["normal_release", "claim_lapsed", "validator_refusal", "operator_abort", "force_reap"],
    )
    wt.add_argument("--exit-code", type=int, default=0)
    wt.add_argument("--controller-id", default=None)
    wt.add_argument("--lane-id", default=None)
    wt.add_argument("--claim-ref", default=None, help="claim path relative to --active-work-ledger-root")
    wt.add_argument("--active-work-ledger-root", default=None)
    wt.add_argument("--side-effect-ledger-root", default=None, help="optional: record a container_stopped side effect")
    wt.add_argument("--repo-root", default=None)
    wt.add_argument("--json", action="store_true", dest="json_output")

    wg = worker_sub.add_parser("gc", help="reap container-instance records that outlived a released claim (PCO-043)")
    wg.add_argument("--container-instance-root", required=True)
    wg.add_argument("--claim-id", default=None, help="optional: scope the sweep to one claim")
    wg.add_argument("--json", action="store_true", dest="json_output")

    ws = worker_sub.add_parser("status", help="read a local container-instance record (read-only)")
    ws.add_argument("--container-instance-root", required=True)
    ws.add_argument("--claim-id", required=True)
    ws.add_argument("--instance-id", required=True)
    ws.add_argument("--json", action="store_true", dest="json_output")

    wtp = worker_sub.add_parser(
        "worktree-prune",
        help=argparse.SUPPRESS,
        description="report/apply fail-safe stale git worktree pruning",
    )
    wtp.add_argument("--repo-root", default=".", help="repository root for git worktree list (default: cwd)")
    wtp.add_argument(
        "--extra-root",
        action="append",
        default=None,
        dest="extra_roots",
        help="extra root to scan for orphan dirs; repeatable (default includes /var/tmp)",
    )
    wtp.add_argument(
        "--no-default-extra-root",
        action="store_true",
        help="do not scan the default /var/tmp extra root",
    )
    wtp.add_argument(
        "--age-hours",
        type=float,
        default=worktree_prune.DEFAULT_AGE_HOURS,
        help=f"minimum newest-mtime age for pruning (default: {worktree_prune.DEFAULT_AGE_HOURS:g})",
    )
    wtp.add_argument("--apply", action="store_true", help="remove only PRUNABLE entries and append audit records")
    wtp.add_argument("--state-root", default=None, help="audit state root (default: <repo-root>/.ce/state)")
    wtp.add_argument("--json", action="store_true", dest="json_output")

    # ce fanin — local read-only evidence fan-in packet (Gate 7, RV1-070/071).
    fanin = groups.add_parser(
        "fanin", help="build/inspect a local read-only evidence fan-in packet (no authority)"
    )
    fanin_sub = fanin.add_subparsers(dest="fanin_cmd")

    fb = fanin_sub.add_parser(
        "build", help="aggregate local evidence into a deterministic content-hashed packet"
    )
    fb.add_argument("--request", required=True, help="path to the fan-in request (YAML/JSON)")
    fb.add_argument(
        "--packet-root",
        required=True,
        help="ignored output root for the packet (e.g. .ce/state/fan-in/)",
    )
    fb.add_argument("--repo-root", default=None, help="repo root for the git-ignore guard")
    fb.add_argument("--packet-id", default=None, help="override the request's packet_id")
    # Refusal-only authority flags: a fan-in packet never grants authority.
    fb.add_argument(
        "--ratify",
        action="store_true",
        help="refuse-only flag: ratification is never granted by fan-in (always refused)",
    )
    fb.add_argument(
        "--enqueue",
        action="store_true",
        help="refuse-only flag: integration-queue enqueue is never granted by fan-in (always refused)",
    )
    fb.add_argument(
        "--land",
        action="store_true",
        help="refuse-only flag: landing is never granted by fan-in (always refused)",
    )
    fb.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    fi = fanin_sub.add_parser("inspect", help="verify a packet's content hash + shape (read-only)")
    fi.add_argument("--packet", required=True, help="path to an existing fan-in packet")
    fi.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    # ce queue — Integration Queue preview plus the controller-side Integrator
    # poll belt. Preview payloads remain authority-free; explicit live flags
    # route through the merge-gated Integrator belt and fail closed.
    queue = groups.add_parser(
        "queue",
        help="preview/inspect Integration Queue state or run the Integrator poll belt",
    )
    queue_sub = queue.add_subparsers(dest="queue_cmd")

    qd = queue_sub.add_parser(
        "dry-run",
        help="reconstruct a deterministic serialized landing preview from verified fan-in evidence",
    )
    qd.add_argument("--request", required=True, help="path to the dry-run request (YAML/JSON)")
    qd.add_argument(
        "--preview-root",
        required=True,
        help="ignored output root for the preview (e.g. .ce/state/integration-queue/)",
    )
    qd.add_argument("--repo-root", default=None, help="repo root for the git-ignore guard")
    qd.add_argument("--preview-id", default=None, help="override the request's preview_id")
    qd.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    qi = queue_sub.add_parser("inspect", help="verify a preview's content hash + shape (read-only)")
    qi.add_argument("--preview", required=True, help="path to an existing dry-run landing preview")
    qi.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")
    # ce-ops#218: the belt-driven live merge-queue repair poll lives in the v3 CLI
    # (`cev3 queue-poll`) — it imports the v3 forge belt, which must not be reached
    # from this v1 CLI (v1⊥v3 isolation, docs/architecture/VERSION_BOUNDARY.md).

    # ce event — G2.003.1 CE-event runtime. Local, daemonless, network-free
    # append-only signed-block chains under the ignored .ce/ce-events/spool/
    # root. No cryptography/key custody; signature stays reserved-inactive.
    event = groups.add_parser(
        "event", help="append/verify/sign/replay/index local CE-event chains (G2.003.1)"
    )
    event_sub = event.add_subparsers(dest="event_cmd")

    ea = event_sub.add_parser(
        "append", help="append a shape-only-signed CE-event block to a local chain"
    )
    ea.add_argument("--stream", required=True, help="chain stream name (path-safe slug)")
    ea.add_argument("--event-root", required=True, help="CE-event home (e.g. .ce/ce-events)")
    ea.add_argument("--block-id", required=True, help="block id (pattern ceevt-<slug>)")
    ea.add_argument("--emitting-role", required=True, help="canonical non-ratifying emitting role")
    ea.add_argument(
        "--operating-mode",
        required=True,
        help="operating-mode context strict|auto|transcendence (recorded only; "
        "an unknown mode is refused by the runtime with G2-EVENT-MODE-INVALID)",
    )
    ea.add_argument("--recorded-at", required=True, help="UTC timestamp YYYY-MM-DDThh:mm:ssZ")
    ea.add_argument("--event-json", required=True, help="event mapping as JSON (kind/subject/summary[/payload])")
    ea.add_argument("--repo-root", default=None, help="repo root for the git-ignore guard")
    ea.add_argument("--key-id", default=ce_event_runtime.DEFAULT_KEY_ID, help="shape-only signature key_id")
    ea.add_argument(
        "--signature-value",
        default=ce_event_runtime.SIGNATURE_VALUE,
        help="refuse-guarded: must stay reserved-inactive (no cryptography)",
    )
    ea.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    ev = event_sub.add_parser("verify", help="validate an on-disk CE-event chain + head manifest")
    ev.add_argument("--stream", required=True)
    ev.add_argument("--event-root", required=True)
    ev.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    es = event_sub.add_parser("sign", help="refresh a draft block's shape-only signature + content hash")
    es.add_argument("--block-json", required=True, help="draft CE-event block mapping as JSON")
    es.add_argument("--key-id", default=None, help="shape-only signature key_id")
    es.add_argument(
        "--signature-value",
        default=ce_event_runtime.SIGNATURE_VALUE,
        help="refuse-guarded: must stay reserved-inactive (no cryptography)",
    )
    es.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    er = event_sub.add_parser("replay", help="deterministic ordered read-only projection of a chain")
    er.add_argument("--stream", required=True)
    er.add_argument("--event-root", required=True)
    er.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    ei = event_sub.add_parser("index", help="deterministic content-hashed read-only index of a chain")
    ei.add_argument("--stream", required=True)
    ei.add_argument("--event-root", required=True)
    ei.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    # ce pcl — G2.004.1 PCL runtime. Local, daemonless, network-free append-only
    # content-addressed record chains. Records are the per-repo authoritative,
    # tracked-or-synced coordination ledger under .ce/pcl/records/<ledger>/; the
    # rebuildable index/merge cache lives under the ignored .ce/pcl/cache/. No
    # cryptography/key custody; signature stays reserved-inactive; PCL never ratifies.
    pcl = groups.add_parser(
        "pcl", help="append/verify/replay/index/merge local PCL coordination ledgers (G2.004.1)"
    )
    pcl_sub = pcl.add_subparsers(dest="pcl_cmd")

    pa = pcl_sub.add_parser("append", help="append a shape-only-signed PCL record to a tracked local ledger")
    pa.add_argument("--ledger", required=True, help="ledger name (path-safe slug)")
    pa.add_argument("--pcl-root", required=True, help="PCL home (e.g. .ce/pcl)")
    pa.add_argument("--record-id", required=True, help="record id (pattern pcl-<slug>)")
    pa.add_argument("--record-kind", required=True, help="canonical PCL record_kind")
    pa.add_argument("--emitting-role", required=True, help="canonical non-ratifying emitting role")
    pa.add_argument(
        "--operating-mode",
        required=True,
        help="operating-mode context strict|auto|transcendence (recorded only; an unknown "
        "mode is refused with G2-PCL-MODE-INVALID)",
    )
    pa.add_argument("--recorded-at", required=True, help="UTC timestamp YYYY-MM-DDThh:mm:ssZ")
    pa.add_argument("--body-json", required=True, help="record body mapping as JSON")
    pa.add_argument("--repo-root", default=None, help="repo root (records must target .ce/state for live local state)")
    pa.add_argument("--key-id", default=pcl_runtime.DEFAULT_KEY_ID, help="shape-only signature key_id")
    pa.add_argument(
        "--signature-value",
        default=pcl_runtime.SIGNATURE_VALUE,
        help="refuse-guarded: must stay reserved-inactive (no cryptography)",
    )
    pa.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    pv = pcl_sub.add_parser("verify", help="validate an on-disk PCL ledger + head manifest")
    pv.add_argument("--ledger", required=True)
    pv.add_argument("--pcl-root", required=True)
    pv.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    pr = pcl_sub.add_parser("replay", help="deterministic ordered read-only projection of a ledger")
    pr.add_argument("--ledger", required=True)
    pr.add_argument("--pcl-root", required=True)
    pr.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    pi = pcl_sub.add_parser("index", help="deterministic content-hashed index (written to the ignored cache)")
    pi.add_argument("--ledger", required=True)
    pi.add_argument("--pcl-root", required=True)
    pi.add_argument("--repo-root", default=None, help="repo root for the cache git-ignore guard")
    pi.add_argument("--no-cache", action="store_true", help="compute only; do not write the cache projection")
    pi.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    pm = pcl_sub.add_parser("merge", help="deterministic conflict-detecting merge projection of >=2 ledgers")
    pm.add_argument("--source", action="append", dest="sources", required=True, help="repeatable source ledger (>=2)")
    pm.add_argument("--target", required=True, help="target ledger name for the merge projection")
    pm.add_argument("--pcl-root", required=True)
    pm.add_argument("--repo-root", default=None, help="repo root for the cache git-ignore guard")
    pm.add_argument("--no-cache", action="store_true", help="compute only; do not write the cache projection")
    pm.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    # ce brain — local Knowledge-SSOT assertion ledger plus rebuildable recall
    # ingest. The recall store remains a derived projection of Markdown source.
    brain = groups.add_parser(
        "brain",
        help=(
            "local Knowledge-SSOT assertion ledger + recall "
            "(assert/check/correct/sync/ingest/recall/verify/probe/bootstrap)"
        ),
    )
    brain_sub = brain.add_subparsers(dest="brain_cmd")

    def _add_state_root(p):
        p.add_argument(
            "--state-root",
            default=V3_LOCAL_STATE_ROOT,
            help=f"CE local state root (default: {V3_LOCAL_STATE_ROOT})",
        )

    def _add_required_scope(p):
        scope_group = p.add_mutually_exclusive_group(required=True)
        scope_group.add_argument("--scope", default=None, help="scope as a non-empty string")
        scope_group.add_argument("--scope-json", default=None, help="scope as a JSON object")

    def _add_optional_scope(p):
        scope_group = p.add_mutually_exclusive_group(required=False)
        scope_group.add_argument("--scope", default=None, help="override corrected assertion scope as a string")
        scope_group.add_argument("--scope-json", default=None, help="override corrected assertion scope as a JSON object")

    ba = brain_sub.add_parser("assert", help="append one structured brain assertion")
    _add_state_root(ba)
    _add_required_scope(ba)
    ba.add_argument("--id", dest="assertion_id", default=None, help="optional brain-assertion-* id")
    ba.add_argument("--statement", default=None, help="required SSOT statement (derived from claim when omitted)")
    ba.add_argument(
        "--type",
        dest="assertion_type",
        default=None,
        choices=sorted(brain_runtime.ASSERTION_TYPES),
        help="assertion type (default: decision)",
    )
    ba.add_argument(
        "--verification-method",
        default=None,
        choices=sorted(brain_runtime.VERIFICATION_METHOD_TYPES),
        help="verification method (derived from evidence-ref when omitted)",
    )
    ba.add_argument("--claim-json", required=True, help="structured claim mapping as JSON")
    ba.add_argument("--evidence-ref", required=True, help="required local/opaque evidence reference")
    ba.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    bc = brain_sub.add_parser("check", help="return active verified assertion or unknown")
    _add_state_root(bc)
    _add_required_scope(bc)
    bc.add_argument("--claim-json", required=True, help="structured claim mapping as JSON")
    bc.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    bco = brain_sub.add_parser("correct", help="supersede an active assertion and append its correction")
    _add_state_root(bco)
    _add_optional_scope(bco)
    bco.add_argument("--id", dest="assertion_id", required=True, help="active brain-assertion-* id to supersede")
    bco.add_argument("--new-id", dest="new_assertion_id", default=None, help="optional corrected brain-assertion-* id")
    bco.add_argument("--statement", default=None, help="corrected SSOT statement (derived from claim when omitted)")
    bco.add_argument(
        "--type",
        dest="assertion_type",
        default=None,
        choices=sorted(brain_runtime.ASSERTION_TYPES),
        help="corrected assertion type (default: previous assertion type)",
    )
    bco.add_argument(
        "--verification-method",
        default=None,
        choices=sorted(brain_runtime.VERIFICATION_METHOD_TYPES),
        help="corrected verification method (derived from evidence-ref when omitted)",
    )
    bco.add_argument("--claim-json", required=True, help="corrected structured claim mapping as JSON")
    bco.add_argument("--evidence-ref", required=True, help="required correction evidence reference")
    bco.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    bs = brain_sub.add_parser(
        "sync",
        help="reconcile ignored local brain runtime state from tracked canonical brain sources",
    )
    _add_state_root(bs)
    bs.add_argument(
        "--repo-root",
        default=None,
        help="repo root containing .ce/brain/assertions.yaml (default: derived from --state-root)",
    )
    bs.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    breconcile = brain_sub.add_parser(
        "reconcile",
        help="plan or atomically apply an explicitly accepted static-evidence hash-chain repair",
    )
    breconcile.add_argument("--repo-root", default=".", help="repository root containing the tracked ledger")
    breconcile.add_argument("--ledger-path", default=None, help="tracked ledger path, relative to --repo-root")
    breconcile.add_argument("--id", action="append", dest="assertion_ids", required=True, help="active assertion id to reconcile (repeatable)")
    breconcile.add_argument("--apply", action="store_true", help="write only after accepting the exact fresh plan digest")
    breconcile.add_argument("--accept-plan-sha", default=None, help="required exact plan_sha256 with --apply")
    breconcile.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    bi = brain_sub.add_parser("ingest", help="derive/update the local rebuildable recall vector store")
    _add_state_root(bi)
    _add_optional_scope(bi)
    bi.add_argument("--source", action="append", dest="sources", required=True, help="repeatable Markdown file or directory source")
    bi.add_argument("--db", default=None, help="recall SQLite DB path (default: <state-root>/brain/recall.sqlite)")
    bi.add_argument(
        "--embedder",
        default="deterministic",
        choices=("deterministic", "embeddinggemma", "vllm-openai"),
        help="embedding adapter (default: deterministic offline fake)",
    )
    bi.add_argument("--model-path", default=None, help="local model path for --embedder embeddinggemma")
    bi.add_argument(
        "--endpoint",
        default=None,
        help="override /v1/embeddings URL for --embedder vllm-openai (default: http://127.0.0.1:8989/v1/embeddings)",
    )
    bi.add_argument(
        "--endpoint-model-id",
        default=None,
        dest="endpoint_model_id",
        help="override model name for --embedder vllm-openai (default: Qwen/Qwen3-Embedding-8B)",
    )
    bi.add_argument(
        "--endpoint-dim",
        default=None,
        type=int,
        dest="endpoint_dim",
        help="override expected embedding dimension for --embedder vllm-openai (default: 4096)",
    )
    bi.add_argument(
        "--allow-confidential-egress",
        action="store_true",
        help="permit egress-requiring embedders to process confidential recall chunks",
    )
    bi.add_argument(
        "--as-of",
        default=None,
        help="snapshot timestamp for produced records (YYYY-MM-DDTHH:MM:SSZ; deterministic default)",
    )
    bi.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    br = brain_sub.add_parser(
        "recall",
        help="hybrid (semantic+keyword) recall surface: SSOT-precedence, tier-tagged pointers",
    )
    _add_state_root(br)
    br.add_argument("context", help="free-form context to recall against (task/ticket/diff)")
    br.add_argument("--db", default=None, help="recall SQLite DB path (default: <state-root>/brain/recall.sqlite)")
    br.add_argument(
        "--embedder",
        default="deterministic",
        choices=("deterministic", "embeddinggemma", "vllm-openai"),
        help="embedding adapter to query with — MUST match the embedder the store was ingested with (default: deterministic offline fake)",
    )
    br.add_argument("--model-path", default=None, help="local model path for --embedder embeddinggemma (must match ingest)")
    br.add_argument(
        "--endpoint",
        default=None,
        help="override /v1/embeddings URL for --embedder vllm-openai (default: http://127.0.0.1:8989/v1/embeddings)",
    )
    br.add_argument(
        "--endpoint-model-id",
        default=None,
        dest="endpoint_model_id",
        help="override model name for --embedder vllm-openai (default: Qwen/Qwen3-Embedding-8B)",
    )
    br.add_argument(
        "--endpoint-dim",
        default=None,
        type=int,
        dest="endpoint_dim",
        help="override expected embedding dimension for --embedder vllm-openai (default: 4096)",
    )
    br.add_argument("--top-k", type=int, default=brain_recall_surface.DEFAULT_TOP_K, help="max items per tier")
    br.add_argument("--scope", default=None, help="restrict recall to this scope string")
    br.add_argument("--as-of", default=None, help="exclude recall records stamped after this as_of (YYYY-MM-DDTHH:MM:SSZ)")
    br.add_argument(
        "--allow-confidential-egress",
        action="store_true",
        help="permit an egress-requiring embedder to embed the query over a confidential corpus",
    )
    br.add_argument(
        "--hydrate",
        action="store_true",
        help="emit a session-hydration payload (additive over the always-load CORE markdown)",
    )
    br.add_argument("--core-path", default=None, help="always-load CORE markdown path reported by --hydrate (never edited)")
    br.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    bv = brain_sub.add_parser("verify", help="validate the local brain assertion ledger")
    _add_state_root(bv)
    bv.add_argument("--drift", action="store_true", help="re-verify active assertions against their evidence_ref")
    bv.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    bh = brain_sub.add_parser("hydrate", help="emit deterministic active decision/lesson hydration contract")
    _add_state_root(bh)
    bh.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    bp = brain_sub.add_parser("probe", help="freshly interrogate Knowledge-SSOT capability probe(s)")
    bp.add_argument("probe_name", nargs="?", metavar="name", help="probe name")
    bp.add_argument("--all", action="store_true", dest="all_probes", help="run all registered probes")
    bp.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    be = brain_sub.add_parser("eval", help=argparse.SUPPRESS)
    be.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    bb = brain_sub.add_parser("bootstrap", help="emit the deterministic brain injection bootstrap payload")
    _add_state_root(bb)
    _add_optional_scope(bb)
    bb.add_argument("--role", default=brain_bootstrap.DEFAULT_ROLE, help="bootstrap role label")
    bb.add_argument("--seat-class", default=brain_bootstrap.DEFAULT_SEAT_CLASS, help="foreman/worker; unknown fails closed to foreman")
    bb.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    orchestrator = groups.add_parser(
        "orchestrator",
        help="inspect Orchestrator runtime records (read-only)",
    )
    orchestrator_sub = orchestrator.add_subparsers(dest="orchestrator_cmd")
    orch_status = orchestrator_sub.add_parser(
        "status",
        help="read and validate Orchestrator runtime records (read-only)",
    )
    orch_status.add_argument("--repo-root", default=".", help="repo root (default: cwd)")
    orch_status.add_argument(
        "--state-dir",
        default=None,
        help="orchestrator state dir (default: <repo-root>/.ce/state/orchestrator)",
    )
    orch_status.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    bin_ = brain_sub.add_parser(
        "init",
        help="idempotently bootstrap a valid genesis brain assertion ledger (ce-ops#206)",
    )
    _add_state_root(bin_)
    bin_.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    # ce connector — GitHub connector runtime. Validates a connector descriptor +
    # Mission-Brief (G2.005.0 substrate). G2.005.1 added read-only verify/plan/fetch;
    # G2.005.2 adds the strict-mode write path write-plan/submit, bounded to the
    # tracker_mirror verbs. Credential by reference (never stored/printed); offline
    # fails closed.
    connector = groups.add_parser(
        "connector", help="GitHub connector runtime: read-only verify/plan/fetch (G2.005.1) + strict-mode write-plan/submit (G2.005.2)"
    )
    connector_sub = connector.add_subparsers(dest="connector_cmd")

    cv = connector_sub.add_parser("verify", help="validate a connector + Mission-Brief pair (offline)")
    cv.add_argument("--connector", required=True, help="path to a connector descriptor *.ce.yml")
    cv.add_argument("--mission-brief", required=True, help="path to a Mission-Brief *.ce.yml")
    cv.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    cp = connector_sub.add_parser("plan", help="build + validate a read-only read plan (offline)")
    cp.add_argument("--connector", required=True)
    cp.add_argument("--mission-brief", required=True)
    cp.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    cf = connector_sub.add_parser("fetch", help="execute one read-only GET; credential by reference; offline fails closed")
    cf.add_argument("--connector", required=True)
    cf.add_argument("--mission-brief", required=True)
    cf.add_argument("--resource", required=True, help="read resource path (e.g. repos/OWNER/REPO/issues)")
    cf.add_argument("--provider", default=connector_runtime.DEFAULT_PROVIDER, choices=sorted(connector_runtime.PROVIDER_READ_CLIENTS), help="read provider adapter (github default; jira/gitlab read-only, G2.005.3)")
    cf.add_argument("--base-url", default=None, help="read API base URL (overrides the provider default)")
    cf.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    cwp = connector_sub.add_parser("write-plan", help="build + validate a strict-mode tracker_mirror write plan (offline) (G2.005.2)")
    cwp.add_argument("--connector", required=True)
    cwp.add_argument("--mission-brief", required=True)
    cwp.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    cs = connector_sub.add_parser("submit", help="execute one bounded tracker_mirror write; credential REQUIRED by reference; offline fails closed (G2.005.2)")
    cs.add_argument("--connector", required=True)
    cs.add_argument("--mission-brief", required=True)
    cs.add_argument("--verb", required=True, choices=sorted(connector_runtime.WRITE_METHODS), help="tracker_mirror write verb")
    cs.add_argument("--resource", required=True, help="write resource path (e.g. repos/OWNER/REPO/issues)")
    cs.add_argument("--payload", default=None, help="path to a JSON request-body file (optional)")
    cs.add_argument("--base-url", default=connector_runtime.DEFAULT_GITHUB_API_BASE, help="write API base URL")
    cs.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    playbook = groups.add_parser(
        "playbook",
        help="discover, inspect, and run governed CE playbooks",
    )
    playbook_sub = playbook.add_subparsers(dest="playbook_cmd")
    pl = playbook_sub.add_parser("list", help="list governed CE playbooks")
    pl.add_argument(
        "--playbooks-root",
        "--root",
        dest="playbooks_root",
        default=".",
        help="root to search for PLAYBOOK.md files (default: cwd)",
    )
    pl.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    ps = playbook_sub.add_parser("show", help="show a public playbook and projected descriptor")
    ps.add_argument("ref", help="playbook id, directory, or PLAYBOOK.md path")
    ps.add_argument(
        "--playbooks-root",
        "--root",
        dest="playbooks_root",
        default=".",
        help="root used to resolve playbook ids (default: cwd)",
    )
    ps.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    prun = playbook_sub.add_parser("run", help="run a governed CE playbook")
    prun.add_argument("ref", help="playbook id, directory, or PLAYBOOK.md path")
    prun.add_argument(
        "--playbooks-root",
        "--root",
        dest="playbooks_root",
        default=".",
        help="root used to resolve playbook ids (default: cwd)",
    )
    prun.add_argument("--dry-run", action="store_true", help="print the governed run plan without side effects")
    prun.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    # ce reviewer-triage — ce-ops#120 Phase 1-2 plan-only reviewer assignment.
    # This surface consumes explicit PR facts + tracked local policy and emits a
    # decision record. It performs no source-host mutation: no review request,
    # no reviewer venue spawn, no envelope minting.
    reviewer = groups.add_parser(
        "reviewer-triage",
        help="plan-only reviewer assignment decision (no source-host mutation)",
    )
    reviewer_sub = reviewer.add_subparsers(dest="reviewer_triage_cmd")
    rp = reviewer_sub.add_parser("plan", help="emit a reviewer-triage decision record")
    rp.add_argument("--pr", required=True, type=int, dest="pr_number", help="pull request number")
    rp.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")
    rp.add_argument("--repo-root", default=".", help="repo root for tracked policy inputs")
    rp.add_argument("--repo", default=None, help="owner/name repo id (default: derived from origin URL)")
    rp.add_argument("--head-sha", default=None, help="PR head SHA (default: local HEAD)")
    rp.add_argument("--expected-head-sha", default=None, help="fail closed unless it matches --head-sha")
    rp.add_argument("--author-run-id", default=None, help="author run id for the decision work_ref")
    rp.add_argument("--author-login", default=None, help="author source-host login")
    rp.add_argument("--author-human-id", default=None, help="resolved author human id")
    rp.add_argument("--author-controller-id", default=None, help="author controller id")
    rp.add_argument("--author-venue-id", default=None, help="author venue id")
    rp.add_argument("--author-credential-domain-ref", default=None, help="author credential-domain ref")
    rp.add_argument("--author-os-user-ref", default=None, help="author OS-user-domain ref")
    rp.add_argument("--author-host-ref", default=None, help="author host ref")
    rp.add_argument("--last-pusher-login", default=None, help="last pusher source-host login")
    rp.add_argument("--last-pusher-human-id", default=None, help="resolved last-pusher human id")
    rp.add_argument("--changed-path", action="append", dest="changed_paths", default=None)
    rp.add_argument("--mutation-class", action="append", dest="mutation_classes", default=None)
    rp.add_argument("--risk-tier", default="medium")
    rp.add_argument("--registry", default=None, help="reviewer registry YAML (default: .ce/reviewer-registry.yml if present)")
    rp.add_argument("--coordination-policy", default=None, help="coordination policy YAML (default: .ce/coordination.yml)")
    rp.add_argument("--codeowners", default=None, help="CODEOWNERS path (default: .github/CODEOWNERS)")
    rp.add_argument("--codeowners-text", default=None, help="inline CODEOWNERS text for tests/offline probes")
    rp.add_argument("--required-team", action="append", dest="required_teams", default=None)

    # ce check — umbrella wrapper over the retained creator-engine-validator
    # conformance checks (DP-1 = A: ce wraps the validator subcommands).
    check = groups.add_parser(
        "check", help="run creator-engine-validator conformance checks (wraps the validator)"
    )
    check.add_argument("paths", nargs="*", default=["."], help="paths to validate")
    check.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")
    check.add_argument("--tenant", default=None, help="restrict cross-artifact checks to one tenant")
    check.add_argument("--list-checks", action="store_true", help="list enabled checks and their FRs")
    check.add_argument(
        "--profile",
        choices=check_profiles.CHECK_PROFILES,
        default=None,
        help=argparse.SUPPRESS,
    )

    # ce doctor — governed-environment guard preflight (DP-3 = B, RV1-061).
    doctor = groups.add_parser(
        "doctor", help="governed-environment guard preflight; refuses ungoverned host drift"
    )
    doctor.add_argument("--repo-root", default=".", help="repo root to preflight (default: cwd)")
    doctor.add_argument("--venv", default=None, help="target controller/seat venv directory to inspect")
    doctor.add_argument(
        "--target-python",
        dest="target_python",
        default=None,
        help="target controller/seat interpreter path to inspect (overrides --venv)",
    )
    doctor.add_argument(
        "--check-seat-env",
        action="store_true",
        help="require the target controller/seat env check even when no .venv is discovered",
    )
    doctor.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")
    doctor.add_argument(
        "--require-visible-launch",
        action="store_true",
        help="treat a missing visible tmux terminal as a refusal (PCO-049)",
    )
    doctor.add_argument(
        "--require-worker",
        action="store_true",
        help="treat missing rootless Podman (or rootful Podman) as a refusal (PCO-045)",
    )
    doctor.add_argument(
        "--no-check-packaging",
        action="store_true",
        help="skip the dependency wheelhouse contract clause (RED-G-6)",
    )
    doctor.add_argument(
        "--require-installed-ce",
        action="store_true",
        help="refuse unless doctor is running via an installed ce/cev3 console script",
    )
    doctor.add_argument(
        "--harness",
        default=launch_runtime.DEFAULT_HARNESS,
        choices=sorted(launch_runtime.SUPPORTED_HARNESSES),
        help="Controller-seat harness binary to preflight when visible launch is required",
    )

    heartbeat = groups.add_parser("heartbeat", help="check supervised daemon heartbeat freshness")
    heartbeat_sub = heartbeat.add_subparsers(dest="heartbeat_cmd")
    heartbeat_check = heartbeat_sub.add_parser("check", help="classify daemon heartbeats and emit alarms")
    heartbeat_check.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable report")

    # ce containment-probe — ce-ops#221 Fix-1. Containment is PROBED from the
    # live kernel runtime (/proc/<pid>), never self-reported. Fail-closed:
    # contained=true requires positive kernel-isolation evidence.
    containment = groups.add_parser(
        "containment-probe",
        help="probe live-runtime containment of a pid from /proc (fail-closed; never self-reported)",
    )
    containment.add_argument(
        "pid",
        nargs="?",
        default=str(os.getpid()),
        help="target pid to probe (default: this process)",
    )
    containment.add_argument(
        "--proc-root",
        default="/proc",
        help="proc tree root to read (default: /proc; override for fixtures)",
    )
    containment.add_argument(
        "--host-pid",
        default="1",
        help="reference host pid to compare namespaces/root against (default: 1)",
    )
    containment.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit the machine-readable JSON verdict",
    )
    containment.add_argument(
        "--herdr-socket",
        default=None,
        help="controller-held herdr socket path to probe for per-seat liveness",
    )
    containment.add_argument(
        "--herdr-pane-id",
        default=None,
        help="herdr pane id to probe for agent-status readiness",
    )
    containment.add_argument(
        "--herdr-binary",
        default="herdr",
        help="herdr CLI binary used for the liveness probe (default: herdr)",
    )
    containment.add_argument(
        "--ring1-tool",
        default="git",
        help="Ring-1 guarded tool to probe via the target process PATH (default: git)",
    )

    containment_status_cmd = groups.add_parser(
        "containment-status",
        help="probe containment for a fleet of seats from live pids (fail-closed)",
    )
    containment_status_cmd.add_argument(
        "--seat",
        action="append",
        dest="containment_seats",
        default=[],
        help="repeatable seat id or seat=pid binding; comma-separated values allowed",
    )
    containment_status_cmd.add_argument(
        "--registry",
        action="append",
        dest="containment_registries",
        default=[],
        help="repeatable registry file/dir containing pane or seat-lifecycle records",
    )
    containment_status_cmd.add_argument(
        "--proc-root",
        default="/proc",
        help="proc tree root to read (default: /proc; override for fixtures)",
    )
    containment_status_cmd.add_argument(
        "--host-pid",
        default="1",
        help="reference host pid to compare namespaces/root against (default: 1)",
    )
    containment_status_cmd.add_argument(
        "--herdr-socket",
        default=None,
        help="controller-held herdr socket path to probe herdr seats",
    )
    containment_status_cmd.add_argument(
        "--herdr-binary",
        default="herdr",
        help="herdr CLI binary used for liveness probes (default: herdr)",
    )
    containment_status_cmd.add_argument(
        "--ring1-tool",
        default="git",
        help="Ring-1 guarded tool to probe via each target PATH (default: git)",
    )
    containment_status_cmd.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit the machine-readable JSON fleet status",
    )

    posture = groups.add_parser(
        "posture",
        help="print the read-only Controller posture banner",
    )
    posture.add_argument("--repo-root", default=".", help="repo root to inspect (default: cwd)")
    posture.add_argument(
        "--role",
        default=None,
        help="override role for deterministic offline evidence (default: CE_* role env or unknown)",
    )
    posture.add_argument(
        "--harness",
        default=None,
        help="override harness for deterministic offline evidence (default: CE_* harness env or claude)",
    )
    posture.add_argument(
        "--launch-mode",
        default=None,
        help="override launch mode for deterministic offline evidence (default: CE_* launch env or derived)",
    )
    posture.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    # INTERNAL command (see INTERNAL_COMMAND_GROUPS): hidden from `ce --help` and
    # not on the public product surface yet. Graduates to a public product command
    # in a later release after internal testing (ce-ops#237).
    herdr = groups.add_parser(
        "herdr",
        help=argparse.SUPPRESS,
    )
    herdr_sub = herdr.add_subparsers(dest="herdr_cmd")

    herdr_remote_attach = herdr_sub.add_parser(
        "remote-attach",
        help="attach to a contained herdr seat through authenticated herdr remote reach",
    )
    herdr_remote_attach.add_argument(
        "--remote",
        dest="remote_target",
        required=True,
        help="SSH target understood by herdr --remote",
    )
    herdr_remote_attach.add_argument(
        "--session",
        default=None,
        help="optional named herdr server/session on the remote target",
    )
    herdr_remote_attach.add_argument(
        "--pane-id",
        default=None,
        help="optional contained seat pane id to carry in the plan metadata",
    )
    herdr_remote_attach.add_argument(
        "--surface-ref",
        default=None,
        help="optional contained herdr surface ref to carry in plan metadata",
    )
    herdr_remote_attach.add_argument(
        "--workspace-id",
        default=None,
        help="optional herdr workspace id to carry in plan metadata",
    )
    herdr_remote_attach.add_argument(
        "--herdr-binary",
        default="herdr",
        help="herdr CLI binary (default: herdr)",
    )
    herdr_remote_attach.add_argument(
        "--dry-run",
        action="store_true",
        help="print the herdr remote command without attaching",
    )
    herdr_remote_attach.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit the machine-readable remote attach plan",
    )

    # INTERNAL command (see INTERNAL_COMMAND_GROUPS): the `ce ask` / `ce support`
    # doc-grounded support agent. THIS slice ships an HONEST SCAFFOLD of the P0
    # substrate only (corpus allowlist + confidentiality intersection, read-only
    # profile, system-prompt contract); the model wiring + eval are later tickets.
    # Dev-gated (hidden from `ce --help`) per the internal-then-public doctrine;
    # graduates to a public product command after the eval clears. `support` is a
    # seam-label alias registered as its own parser (the launch/hud convention),
    # so the command inventory stays one-key-per-group.
    def _add_support_ask_parser(name: str) -> None:
        ask = groups.add_parser(name, help=argparse.SUPPRESS)
        ask.add_argument(
            "question",
            nargs="*",
            help="the support question (scaffold: not yet answered)",
        )
        ask.add_argument(
            "--foundations",
            action="store_true",
            help="print the read-only P0 substrate the scaffold has built",
        )
        ask.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="emit the machine-readable scaffold status",
        )

    _add_support_ask_parser("ask")
    _add_support_ask_parser("support")

    # INTERNAL command (see INTERNAL_COMMAND_GROUPS): advisory ce-ops inbound
    # triage queue maintenance. It never ratifies, approves, dispatches, merges,
    # or blocks CI; --apply only patches an existing sentinel comment.
    triage = groups.add_parser("triage", help=argparse.SUPPRESS)
    triage_sub = triage.add_subparsers(dest="triage_cmd")
    triage_queue = triage_sub.add_parser("queue", help=argparse.SUPPRESS)
    triage_queue_sub = triage_queue.add_subparsers(dest="triage_queue_cmd")

    def _add_triage_queue_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--repo", default=ce_ops_triage_queue.DEFAULT_REPO)
        p.add_argument("--queue-issue", type=int, default=ce_ops_triage_queue.DEFAULT_QUEUE_ISSUE)
        p.add_argument("--audit-root", default=None)
        p.add_argument("--apply", action="store_true")
        p.add_argument("--json", action="store_true", dest="json_output")

    tq_scan = triage_queue_sub.add_parser("scan", help=argparse.SUPPRESS)
    _add_triage_queue_args(tq_scan)
    tq_inspect = triage_queue_sub.add_parser("inspect", help=argparse.SUPPRESS)
    _add_triage_queue_args(tq_inspect)

    # INTERNAL command (see INTERNAL_COMMAND_GROUPS): merge-triggered
    # dependency-unlock evaluator (slice 1). Ships SHADOW-only: no repo
    # variable enables live mode in this PR, so `ce dependency-unlock scan`
    # never makes a GitHub write call by default. It never ratifies,
    # approves, merges, dispatches, or bypasses a required check.
    dependency_unlock_group = groups.add_parser("dependency-unlock", help=argparse.SUPPRESS)
    dependency_unlock_sub = dependency_unlock_group.add_subparsers(dest="dependency_unlock_cmd")
    dep_unlock_scan = dependency_unlock_sub.add_parser("scan", help=argparse.SUPPRESS)
    dep_unlock_scan.add_argument(
        "--event-path",
        default=None,
        help="path to a GitHub pull_request event JSON (defaults to $GITHUB_EVENT_PATH)",
    )
    dep_unlock_scan.add_argument("--pr-repo", default=None, help="manual override: merged PR owner/name")
    dep_unlock_scan.add_argument("--pr-number", type=int, default=None, help="manual override: merged PR number")
    dep_unlock_scan.add_argument("--merge-sha", default=None, help="manual override: merge commit SHA")
    dep_unlock_scan.add_argument("--merged-at", default=None, help="manual override: merged-at timestamp")
    dep_unlock_scan.add_argument(
        "--search-repo",
        default=dependency_unlock.DEFAULT_SEARCH_REPO,
        help="repo to search for candidate blocked issues",
    )
    dep_unlock_scan.add_argument("--audit-root", default=None)
    dep_unlock_scan.add_argument("--json", action="store_true", dest="json_output")

    publish_branch_cmd = groups.add_parser(
        "publish-branch",
        help="host-side publish gate for a contained seat's committed branch",
    )
    publish_branch_cmd.add_argument("branch", help="local branch to publish to origin")
    publish_branch_cmd.add_argument("--repo-root", default=".", help="repo worktree containing the branch")
    publish_branch_cmd.add_argument("--repo", default=None, help="owner/name repo; default derives from origin URL")
    publish_branch_cmd.add_argument("--seat-id", required=True, help="contained seat id that authored the branch")
    publish_branch_cmd.add_argument("--actor", default="host-substrate", help="host actor performing the publish")
    publish_branch_cmd.add_argument("--expect-author-name", default=None)
    publish_branch_cmd.add_argument("--expect-author-email", default=None)
    publish_branch_cmd.add_argument("--expect-committer-name", default=None)
    publish_branch_cmd.add_argument("--expect-committer-email", default=None)
    publish_branch_cmd.add_argument("--controller-id", default=None, help="side-effect ledger controller id")
    publish_branch_cmd.add_argument("--lane-id", default=None, help="side-effect ledger lane id")
    publish_branch_cmd.add_argument("--claim-ref", default=None, help="active-work claim ref bound to this publish")
    publish_branch_cmd.add_argument("--side-effect-ledger-root", default=None)
    publish_branch_cmd.add_argument("--active-work-ledger-root", default=None)
    publish_branch_cmd.add_argument("--dry-run", action="store_true", help="verify publishability without pushing")
    publish_branch_cmd.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    validate_pr = groups.add_parser(
        "validate-pr",
        help="run the local PR preflight gate set against committed base..HEAD state",
    )
    validate_pr.add_argument("--repo-root", default=".", help="PR worktree root (default: current directory)")
    validate_pr.add_argument(
        "--base",
        default="origin/main",
        help="base branch/ref to fetch and merge-base against (default: origin/main)",
    )
    validate_pr.add_argument(
        "--declared-work-class",
        choices=pr_preflight.WORK_CLASS_INPUTS,
        help="declared PR work class; when omitted, read exactly one declared-work-class line from the PR carrier/body",
    )
    validate_pr.add_argument(
        "--head-ref",
        default=None,
        help="PR head branch name for carrier slug (default: current branch)",
    )
    validate_pr.add_argument(
        "--pr-body-file",
        type=Path,
        default=None,
        help="optional PR body file for CE-TEST-COUPLING-EXEMPT detection in the test-coupling gate",
    )
    validate_pr.add_argument(
        "--pr-body",
        default=None,
        help="optional literal PR body for CE-TEST-COUPLING-EXEMPT detection in the test-coupling gate",
    )
    validate_pr.add_argument(
        "--allow-dirty",
        action="store_true",
        help="continue despite working-tree changes; committed base..HEAD state is still what gets validated",
    )
    validate_pr.add_argument(
        "--test-command",
        default=pr_preflight.DEFAULT_TEST_COMMAND,
        help=f"test command to compare at base and HEAD (default: {pr_preflight.DEFAULT_TEST_COMMAND})",
    )
    validate_pr.add_argument(
        "--profile",
        choices=pr_preflight.VALIDATE_PR_PROFILES,
        default=None,
        help=argparse.SUPPRESS,
    )

    # ce automerge-decide — CEO-mode auto-merge classifier (PR-A, ce-ops#291).
    # Classify-only / dry-run: prints the decision + rationale for a given PR;
    # performs NO merge, mints NO capability marker.  Inert by construction.
    automerge_decide = groups.add_parser(
        "automerge-decide",
        help=(
            "classify a PR's mutation class + emit AUTO/GESTURE decision "
            "(dry-run only; never merges, never mints a capability marker)"
        ),
    )
    automerge_decide.add_argument(
        "--paths",
        action="append",
        dest="changed_paths",
        default=None,
        metavar="PATH",
        help="repeatable: repo-relative path changed in the PR (from git diff --name-only)",
    )
    automerge_decide.add_argument(
        "--paths-file",
        default=None,
        dest="paths_file",
        metavar="FILE",
        help="path to a newline-separated file of changed paths (alternative to --paths)",
    )
    automerge_decide.add_argument(
        "--declared-work-class",
        default="S",
        dest="declared_work_class",
        choices=pr_preflight.WORK_CLASS_INPUTS,
        help="declared PR work class (default: S)",
    )
    automerge_decide.add_argument(
        "--run-mode",
        default=None,
        dest="run_mode",
        choices=["dev", "strangeLoop", "ceo"],
        help=(
            "advisory run mode override for AutoReview/automerge policy evaluation; "
            "defaults to the policy state, whose shipped default is dev"
        ),
    )
    automerge_decide.add_argument(
        "--policy-state",
        default=None,
        dest="policy_state_path",
        metavar="PATH",
        help=(
            "path to the automerge policy state JSON "
            "(default: .ce/state/automerge/policy.json relative to --repo-root)"
        ),
    )
    automerge_decide.add_argument(
        "--repo-root",
        default=".",
        dest="repo_root",
        help="repo root for default policy state path (default: current directory)",
    )
    automerge_decide.add_argument(
        "--pr",
        type=int,
        default=None,
        dest="pr_number",
        help="optional PR number for the audit record",
    )
    automerge_decide.add_argument(
        "--head-sha",
        default=None,
        dest="head_sha",
        help="optional PR head SHA for the audit record",
    )
    # Workflow-only actuator metadata flags. They are intentionally registered
    # outside parser._actions so the generated public CLI reference stays stable.
    for option, dest in (
        ("--repo", "repo"),
        ("--branch", "branch"),
        ("--base", "base"),
        ("--author-login", "author_login"),
        ("--approver-login", "approver_login"),
    ):
        automerge_decide._option_string_actions[option] = argparse._StoreAction(
            option_strings=[option],
            dest=dest,
            nargs=None,
            const=None,
            default=None,
            type=None,
            choices=None,
            required=False,
            help=argparse.SUPPRESS,
            metavar=None,
        )
    automerge_decide.add_argument(
        "--checks-json",
        default=None,
        dest="checks_json",
        help=(
            "optional JSON object mapping check-name to status, or @FILE containing one "
            "(e.g. '{\"ci\": \"success\"}')"
        ),
    )
    automerge_decide.add_argument(
        "--review-decision",
        default=None,
        dest="review_decision",
        choices=["APPROVED", "CHANGES_REQUESTED", "REVIEW_REQUIRED", ""],
        help="optional GitHub reviewDecision for the PR",
    )
    automerge_decide.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit machine-readable JSON decision record",
    )

    # ce automerge-status — read-only observability over dry-run decision logs.
    automerge_status = groups.add_parser(
        "automerge-status",
        help="read dry-run automerge decision logs (read-only; never merges)",
    )
    automerge_status.add_argument(
        "--repo-root",
        default=".",
        dest="repo_root",
        help="repo root for default state dir (default: current directory)",
    )
    automerge_status.add_argument(
        "--state-dir",
        default=None,
        dest="state_dir",
        metavar="DIR",
        help="state dir containing automerge/decisions (default: .ce/state relative to --repo-root)",
    )
    automerge_status.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit machine-readable JSON decision records",
    )

    # ce automerge-kill-switch — governed live-policy disarm/re-arm switch.
    automerge_kill_switch = groups.add_parser(
        "automerge-kill-switch",
        help="read or toggle the durable live-policy automerge kill-switch",
    )
    automerge_kill_switch.add_argument(
        "action",
        choices=("status", "on", "off"),
        help="status reads, on disarms, off clears the live-policy kill-switch",
    )
    automerge_kill_switch.add_argument(
        "--repo-root",
        default=".",
        dest="repo_root",
        help="repo root for default policy state path (default: current directory)",
    )
    automerge_kill_switch.add_argument(
        "--policy-state",
        default=None,
        dest="policy_state_path",
        metavar="PATH",
        help=(
            "path to the automerge policy state JSON "
            "(default: .ce/state/automerge/policy.json relative to --repo-root)"
        ),
    )
    automerge_kill_switch.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit machine-readable JSON policy state",
    )

    # ce init — idempotent CE-native project scaffolding.
    init = groups.add_parser(
        "init", help="scaffold a CE-governed project with offline templates"
    )
    init.add_argument(
        "target",
        nargs="?",
        default=None,
        help="target project directory (default: cwd)",
    )
    init.add_argument("--repo-root", default=None, help=argparse.SUPPRESS)
    init.add_argument(
        "--force",
        action="store_true",
        help="overwrite CE scaffold files that differ from the embedded templates",
    )
    init.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    # ce claim acquire|release|status — the ce-ops#38 work-claim-lock MVP. The
    # authoritative claim is a structured GitHub issue comment; this surface is a
    # thin CLI over the shared `work_claims` runtime (forge-native, advisory).
    claim = groups.add_parser(
        "claim", help="work-claim locks: hub-visible per-ticket compose/dispatch claims (ce-ops#38)"
    )
    claim_sub = claim.add_subparsers(dest="claim_cmd")

    def _add_ticket_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("ticket", help="owner/name#N, a GitHub issue URL, or N (with --repo)")
        p.add_argument("--repo", default=None, help="owner/name context for a bare issue number")
        p.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    ca = claim_sub.add_parser("acquire", help="acquire + verify a work claim (atomic dispatch posture)")
    _add_ticket_args(ca)
    ca.add_argument("--reason", default="manual", choices=list(work_claims.VALID_REASONS))
    ca.add_argument("--holder", default=None, help="claim holder id (default: env/controller/hostname)")
    ca.add_argument("--host", default=None, help="claim host (default: hostname)")
    ca.add_argument("--stale-after-seconds", type=int, default=work_claims.DEFAULT_STALE_AFTER_SECONDS,
                    dest="stale_after_seconds", help="staleness fence (status/takeover threshold; never auto-release)")
    ca.add_argument("--takeover", action="store_true", help="seize a STALE foreign (or legacy) claim explicitly")
    ca.add_argument("--takeover-reason", default=None, dest="takeover_reason")

    cr = claim_sub.add_parser("release", help="release a held claim (structured release comment)")
    _add_ticket_args(cr)
    cr.add_argument("--claim-id", default=None, dest="claim_id", help="claim id to release (default: your active claim)")
    cr.add_argument("--reason", default="deliverable-posted", help="release_reason text")
    cr.add_argument("--deliverable-url", default=None, dest="deliverable_url")

    cst = claim_sub.add_parser("status", help="read the live claim state (no mutation)")
    _add_ticket_args(cst)
    cst.add_argument("--write-cache", default=None, dest="write_cache",
                     metavar="ROOT", help="write the view-only Cockpit cache under <ROOT>/claims/claims.json")

    ctr = claim_sub.add_parser("transition", help=argparse.SUPPRESS)
    ctr.add_argument("slug", help="claim slug, matching .ce/claims/<slug>.md")
    ctr.add_argument("new_state", choices=CLAIM_LIFECYCLE_STATES, help="target lifecycle state")
    ctr.add_argument("--pr", default=None, help="pull request URL to store on the claim")
    ctr.add_argument("--sha", default=None, help="merge or release SHA to store on the claim")
    ctr.add_argument(
        "--force",
        action="store_true",
        help="bypass transition order/state restrictions; landed/released SHA evidence is still verified",
    )
    ctr.add_argument("--repo-root", default=".", help="repo root containing .ce/claims (default: cwd)")
    ctr.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    cl = claim_sub.add_parser("list", help=argparse.SUPPRESS)
    cl.add_argument("--repo-root", default=".", help="repo root containing .ce/claims (default: cwd)")
    cl.add_argument("--state", choices=CLAIM_LIFECYCLE_STATES, default=None, help="filter by lifecycle state")
    cl.add_argument("--seat", default=None, help="filter by seat id")
    cl.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    # ce pickup poll — the ce-ops#55/#182 autonomous forge work-pickup "conveyor belt".
    # A per-seat READ-ONLY poller over the GitHub Search API; observe-only by
    # default (S1), claims via the forge + a dedup ledger (S2, dry-run by default),
    # and triggers a fresh governed `ce lane launch` ONLY when --enable-launch is set
    # (S3, canary OFF by default). The poller NEVER authors (CC-D-2 / CDX-D-1).
    pickup = groups.add_parser(
        "pickup", help="autonomous forge work-pickup poller (read-only; ce-ops#55/#182)"
    )
    pickup_sub = pickup.add_subparsers(dest="pickup_cmd")

    # ce pickup triage — ce-ops#187 bounded forge-triage belt planner. Offline
    # by default: JSON issue set in, deterministic pickup work-items out. It
    # never launches lanes; --apply is the sole source-host mutation path.
    pt = pickup_sub.add_parser("triage", help="emit deterministic claimable pickup work")
    pt.add_argument("--arc-ticket", required=True, dest="arc_ticket",
                    help="parent/arc ticket (owner/name#N, URL, or N with --repo)")
    pt.add_argument("--issues-json", default="-", dest="issues_json",
                    help="path to GitHub Search/list issues JSON, or '-' for stdin")
    pt.add_argument("--repo", default=None,
                    help="owner/name default repo for bare arc tickets or issue payloads")
    pt.add_argument("--label", default=forge_triage.DEFAULT_PICKUP_LABEL,
                    help="pickup label to add and expose as a ce pickup poll hint")
    pt.add_argument("--seat", action="append", dest="triage_seats", default=[],
                    help="repeatable seat/assignee login; comma-separated allowed")
    pt.add_argument("--apply", action="store_true",
                    help="apply planned labels/assignees through gh api after claim collision checks")
    pt.add_argument("--check-claims", action="store_true", dest="check_claims",
                    help="dry-run with live work-claim collision checks through gh api")
    pt.add_argument("--json", action="store_true", dest="json_output",
                    help="emit machine-readable JSON")

    dp = pickup_sub.add_parser("dispatch-plan", help="emit a deterministic seat-dispatch plan from issues JSON")
    dp.add_argument("--arc-ticket", required=True, dest="arc_ticket")
    dp.add_argument("--issues-json", default="-", dest="issues_json")
    dp.add_argument("--repo", default=None)
    dp.add_argument("--label", default=dispatch_plan.DEFAULT_PICKUP_LABEL)
    dp.add_argument("--seat", action="append", dest="dispatch_seats", default=[])
    dp.add_argument("--json", action="store_true", dest="json_output")

    pp = pickup_sub.add_parser("poll", help="one read-only Search API poll → work-items JSON")
    pp.add_argument("--identity", required=True,
                    help="seat identity (e.g. ce-dev-2); selects ~/.ce-keys/<identity>.pat")
    pp.add_argument("--keys-dir", default=None, dest="keys_dir",
                    help="PAT directory (default: ~/.ce-keys)")
    pp.add_argument("--allow-ambient-gh", action="store_true", dest="allow_ambient_gh",
                    help="allow fallback to ambient gh auth token after CE_PICKUP_TOKEN and PAT file")
    pp.add_argument("--repo", default=None,
                    help="restrict Search API queries and claims to one owner/name repo")
    pp.add_argument("--org", default=None,
                    help="restrict Search API queries to one GitHub org/user slug")
    pp.add_argument("--label", action="append", default=[], dest="pickup_labels",
                    help="repeatable team label to include as labeled work (comma-separated allowed)")
    pp.add_argument("--state-root", "--ledger-root", default=None, dest="pickup_ledger_root",
                    help="pickup state root for dedup ledger (default: <state>/pickup)")
    pp.add_argument("--claim", action="store_true", dest="pickup_claim",
                    help="S2: forge-arbitrate a claim per actionable item (else observe-only)")
    pp.add_argument("--run-id", default=None, dest="pickup_run_id",
                    help="run id stamped into the claim marker (default: derived)")
    pp.add_argument("--enable-launch", action="store_true", dest="enable_launch",
                    help="S3 canary (default OFF): on a successful claim, launch a governed lane")
    pp.add_argument("--harness", default="claude", choices=("claude", "codex"),
                    help="harness for the spawned governed lane (S3)")
    pp.add_argument("--seed-root", default=None, dest="seed_root",
                    help="directory for per-item seed files (S3; default: <ledger-root>/seeds)")
    pp.add_argument("--repo-root", default=".", dest="pickup_repo_root",
                    help="repo root for the spawned governed lane (S3)")
    pp.add_argument("--lane-ledger-root", default=None, dest="lane_ledger_root",
                    help="active-work-ledger root for the spawned lane (S3; default: <repo-root>/.ce/state/active-work-ledger)")
    pp.add_argument("--backoff-seconds", type=float, default=1.0, dest="backoff_seconds",
                    help="re-read backoff for the fail-closed acquire race (default: 1.0)")
    pp.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    # ce launch / ce hud — deterministic visible Controller-seat launcher
    # (DP-2 = B, RV1-063). ce hud is an alias/seam label for the same launcher.
    def _add_launch_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--harness", default=launch_runtime.DEFAULT_HARNESS, help="Controller-seat harness")
        p.add_argument("--session", default=launch_runtime.DEFAULT_SESSION, help="tmux session name")
        p.add_argument("--window", default=launch_runtime.DEFAULT_WINDOW, help="tmux window name")
        p.add_argument("--resume", action="store_true", help="attach an existing launcher session")
        p.add_argument("--dry-run", action="store_true", help="plan only; no tmux spawn, no provider login")
        p.add_argument(
            "--preflight",
            action="store_true",
            help=(
                "diagnose launch pre-spawn gates without mutating seat, tmux, ledger, or runtime state; "
                "exit 0 = all evaluable gates pass and no critical gates skipped; "
                "exit 1 = at least one gate WOULD-REFUSE; "
                "exit 3 = all evaluable gates pass but one or more critical gates "
                "(e.g. containment provisioning) could not be evaluated without a live launch"
            ),
        )
        p.add_argument(
            "--no-tmux",
            action="store_true",
            help="refuse-only flag: request a non-visible/headless seat (always refused)",
        )
        p.add_argument(
            "--role",
            choices=[launch_runtime.CONTROLLER_ROLE],
            default=None,
            help=(
                "raw role=controller launch request; refuses until a governed "
                "takeover evidence packet is supplied"
            ),
        )
        p.add_argument(
            "--takeover-evidence",
            default=None,
            help=(
                "path to a ce takeover --dry-run --json evidence packet that "
                "authorizes role=controller launch"
            ),
        )
        # CC-G-D Ring 0 governed-Claude surfaces. Pass dashed values with `=`
        # (e.g. --claude-arg=--dangerously-skip-permissions).
        p.add_argument(
            "--claude-arg",
            action="append",
            dest="claude_arg",
            default=None,
            help="repeatable extra arg passed to the claude harness (use --claude-arg=<value> for dashed values)",
        )
        p.add_argument(
            "--codex-arg",
            action="append",
            dest="codex_arg",
            default=None,
            help="repeatable allowlisted extra arg passed to the codex harness (use --codex-arg=<value> for dashed values)",
        )
        p.add_argument(
            "--mcp-config",
            dest="mcp_config",
            default=None,
            help="CE-owned MCP config path inside the repo for strict MCP pinning",
        )
        p.add_argument(
            "--completion-report-ref",
            dest="completion_report_ref",
            default=None,
            help="deterministic completion-report pointer recorded for Ring 0 closeout verification",
        )
        p.add_argument(
            "--closeout-file",
            dest="closeout_file",
            default=None,
            help="deterministic closeout file pointer recorded for Ring 0 closeout verification",
        )
        p.add_argument(
            "--runtime-policy",
            dest="runtime_policy",
            default=None,
            help="v3.5-F: path to the ratified runtime policy whose resource_envelopes "
            "bound this seat (systemd-run --user wrap); --dry-run renders the "
            "resource_bound block offline",
        )
        p.add_argument(
            "--backend",
            choices=(*ce_runtime_policy.CLI_BACKEND_CHOICES, launch_runtime.HOST_BACKEND_OPT_OUT),
            default=None,
            help=(
                "runtime backend selector carried by --runtime-policy "
                "(gvisor aliases to gvisor-proxy); host explicitly opts out of "
                "contained launch"
            ),
        )
        p.add_argument(
            "--claim-ticket",
            dest="claim_ticket",
            default=None,
            help="ce-ops#38: acquire + verify a work-claim lock on this ticket "
            "(owner/name#N, an issue URL, or N inside the slug) BEFORE any launch "
            "side effect; a foreign active claim refuses the launch",
        )
        p.add_argument("--repo-root", default=".", help="repo root for lifecycle registration")
        p.add_argument(
            "--ledger-root",
            default=None,
            help="path to .ce/state/active-work-ledger for lifecycle registration",
        )
        p.add_argument(
            "--controller-id",
            default=None,
            help="owner/controller id recorded in the governed seat lifecycle record",
        )
        p.add_argument(
            "--host-id",
            default=None,
            help="host id recorded in the governed seat lifecycle record",
        )
        p.add_argument(
            "--purpose",
            default=None,
            help="operator-readable purpose recorded in the governed seat lifecycle record",
        )
        p.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    launch = groups.add_parser(
        "launch", help="open/attach the visible Controller-seat tmux launcher (DP-2=B)"
    )
    _add_launch_args(launch)
    hud = groups.add_parser("hud", help="alias/seam label for `ce launch` (not a CE-native TUI)")
    _add_launch_args(hud)

    takeover = groups.add_parser(
        "takeover",
        help="read-only controller continuity takeover planner and evidence packet",
    )
    takeover.add_argument(
        "--from",
        required=True,
        dest="takeover_from",
        help="predecessor seat id or session name to detect in continuity state",
    )
    takeover.add_argument(
        "--harness",
        required=True,
        choices=sorted(takeover_runtime.SUPPORTED_HARNESSES),
        help="replacement Controller-seat harness to validate",
    )
    takeover.add_argument("--repo-root", required=True, help="repo root whose .ce state is inspected")
    takeover.add_argument(
        "--duty-manifest",
        default=None,
        help=(
            "machine-readable watcher/daemon duty manifest used to plan "
            "dry-run re-arm actions"
        ),
    )
    takeover.add_argument(
        "--dry-run",
        action="store_true",
        help="print every action that would be taken; do not mutate state",
    )
    takeover.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    continuity_drill = groups.add_parser(
        "continuity-drill",
        help="scheduled benign Controller continuity drill proof",
    )
    continuity_drill.add_argument(
        "--from",
        required=True,
        dest="takeover_from",
        help="predecessor seat id or session name to detect in continuity state",
    )
    continuity_drill.add_argument(
        "--harness",
        required=True,
        choices=sorted(takeover_runtime.SUPPORTED_HARNESSES),
        help="replacement Controller-seat harness to validate",
    )
    continuity_drill.add_argument("--repo-root", required=True, help="repo root whose .ce state is inspected")
    continuity_drill.add_argument(
        "--as-of",
        default=None,
        help="drill schedule date as YYYY-MM-DD (default: current UTC date)",
    )
    continuity_drill.add_argument(
        "--prior-run",
        action="append",
        default=[],
        help="prior drill result as YYYY-MM-DD:clean or YYYY-MM-DD:failed; repeatable",
    )
    continuity_drill.add_argument(
        "--promotion-candidate",
        action="store_true",
        help="mark this drill as required before a controller substrate promotion",
    )
    continuity_drill.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    for name, (help_text, _v3_name) in V3_FORWARDING_SHIMS.items():
        shim = groups.add_parser(name, help=help_text, add_help=False)
        shim.add_argument("v3_args", nargs=argparse.REMAINDER)

    # ce harness-matrix — PROBED harness-support capability matrix (SSOT).
    # Emits a HARNESS x CAPABILITY matrix DERIVED from the adapter specs/config at
    # runtime (never hand-asserted), with a provenance note per cell. The antidote
    # to the containment-probe incident (ce-ops#221): the matrix shows the PROBED
    # truth, not a prose claim.
    harness_matrix_p = groups.add_parser(
        "harness-matrix",
        help="emit the PROBED harness-support capability matrix",
    )
    harness_matrix_p.add_argument(
        "--repo-root", default=".", help="repo root to probe (default: cwd)"
    )
    harness_matrix_p.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit machine-readable JSON instead of Markdown",
    )

    return parser


def _lane_launch(args) -> int:
    brain_code = _preflight_launch_brain_bootstrap(args, "lane launch")
    if brain_code != 0:
        return brain_code
    # ce-ops#38: acquire + verify the work claim BEFORE any lane side effect.
    claim_code, claim_ctx = _acquire_launch_claim(args, "lane launch")
    if claim_code != 0:
        return claim_code
    command = args.command.split() if args.command else None
    claude_arg = getattr(args, "claude_arg", None)
    if command is not None and claude_arg:
        command = [*command, *claude_arg]
    terminal_kind = (
        args.terminal_kind
        if getattr(args, "terminal_kind", None)
        else ("headless" if args.no_tmux else lane_runtime.TMUX_TERMINAL_KIND)
    )
    try:
        result = lane_runtime.launch(
            controller_id=args.controller_id,
            lane_id=args.lane_id,
            role=args.role,
            prompt=args.prompt,
            prompt_sha=args.prompt_sha,
            repo_root=args.repo_root,
            ledger_root=args.ledger_root,
            handoff=args.handoff,
            handoff_sha=args.handoff_sha,
            command=command,
            terminal_kind=terminal_kind,
            host_id=args.host_id,
            pane_id=args.pane_id,
            session=args.session,
            window=args.window,
            worktree_path=args.worktree_path,
            branch=args.branch,
            envelope_ref=args.envelope_ref,
            mcp_config_path=getattr(args, "mcp_config", None),
            closeout_file=getattr(args, "closeout_file", None),
            completion_report_ref=getattr(args, "completion_report_ref", None),
            operating_mode=getattr(args, "operating_mode", None),
            autonomy_class=getattr(args, "autonomy_class", None),
            lane_kind=getattr(args, "lane_kind", None),
            tenant_policy=getattr(args, "tenant_policy", None),
            ratification_evidence_ref=getattr(args, "ratification_evidence_ref", None),
            reviewer_authority_ref=getattr(args, "reviewer_authority_ref", None),
            mint_reviewer_authority=getattr(args, "mint_reviewer_authority", False),
            reviewer_authority_pr_number=getattr(args, "reviewer_authority_pr_number", None),
            reviewer_authority_head_sha=getattr(args, "reviewer_authority_head_sha", None),
            reviewer_authority_actor=getattr(args, "reviewer_authority_actor", None),
            reviewer_authority_pr_author=getattr(args, "reviewer_authority_pr_author", None),
            reviewer_authority_ratified_prompt_sha=getattr(args, "reviewer_authority_ratified_prompt_sha", None),
            reviewer_authority_emitting_role=getattr(args, "reviewer_authority_emitting_role", "controller"),
            seat_env_file=getattr(args, "seat_env_file", None),
            runtime_policy=getattr(args, "runtime_policy", None),
            backend=getattr(args, "backend", None),
            work_claim=_claim_binding(claim_ctx),
            purpose=_claim_purpose(args, claim_ctx),
            tmux_adapter=_make_tmux_adapter(),
        )
    except lane_runtime.LaneLaunchError as exc:
        _release_claim_context(claim_ctx, reason="launch-refused-before-side-effect")
        print(f"ERROR: ce lane launch refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        # v3.1-G2b: the lane-launch consumption seam (twin of `ce launch --json`). The Pane
        # Registry record already carries the value-free terminal {session_id, window_id, pane_id};
        # the v3 reviewer-venue bridge parses this to stamp the review dispatch.
        print(json.dumps(
            {
                "pane_path": str(result.pane_path),
                "record": result.record,
                "reviewer_authority_ref": result.reviewer_authority_ref,
                "seat_record_ref": result.seat_record_ref,
                "seat_lifecycle_state": result.seat_lifecycle_state,
            },
            indent=2, sort_keys=True,
        ))
    else:
        term = result.record["terminal"]
        if term.get("kind") == lane_runtime.TMUX_TERMINAL_KIND:
            surface = (
                f"tmux session={term['session_id']} window={term['window_id']} "
                f"pane={term['pane_id']}"
            )
        else:
            # Non-tmux inspectable lanes have no tmux session/window ids; describe
            # them by kind + surface ref + pid instead.
            surface = (
                f"{term.get('kind')} surface={term.get('surface_ref')} "
                f"pid={term.get('pid')}"
            )
        print(f"ce lane launch: wrote {result.pane_path} ({surface})")
    return 0


def _lane_status(args) -> int:
    try:
        info = lane_runtime.status(
            controller_id=args.controller_id, lane_id=args.lane_id, ledger_root=args.ledger_root
        )
    except lane_runtime.LaneStatusError as exc:
        print(f"ERROR: ce lane status [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(info, indent=2, sort_keys=True))
    else:
        print(info["summary"])
    return 0


def _lane_verify(args) -> int:
    try:
        result = lane_runtime.verify(
            controller_id=args.controller_id,
            lane_id=args.lane_id,
            ledger_root=args.ledger_root,
            transcript=args.transcript,
            stop_line=args.stop_line,
            completion_report=args.completion_report,
        )
    except lane_runtime.LaneVerifyError as exc:
        print(f"ERROR: ce lane verify [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"ce lane verify: OK (stop line present in {result['transcript']})")
    return 0


def _lane_archive(args) -> int:
    try:
        result = transcript_archive.archive(
            transcript=args.transcript,
            archive_root=args.archive_root,
            batch_slug=args.batch_slug,
            role=args.role,
            repo_root=args.repo_root,
        )
    except transcript_archive.ArchiveError as exc:
        print(f"ERROR: ce lane archive refused: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps({"archive_path": str(result.archive_path), "sha256": result.sha256}, indent=2, sort_keys=True))
    else:
        print(f"ce lane archive: {result.archive_path}")
        print(f"sha256: {result.sha256}")
    return 0


def _ledger_record(args) -> int:
    details = None
    if args.details_json is not None:
        try:
            details = json.loads(args.details_json)
        except json.JSONDecodeError as exc:
            print(f"ERROR: ce ledger record: --details-json is not valid JSON: {exc}", file=sys.stderr)
            return 1
    try:
        result = side_effect_ledger_runtime.record(
            controller_id=args.controller_id,
            lane_id=args.lane_id,
            claim_ref=args.claim_ref,
            effect_id=args.effect_id,
            effect_kind=args.effect_kind,
            effect_status=args.effect_status,
            summary=args.summary,
            occurred_at=args.occurred_at,
            repo_root=args.repo_root,
            side_effect_ledger_root=args.side_effect_ledger_root,
            active_work_ledger_root=args.active_work_ledger_root,
            actor_role=args.actor_role,
            pane_ref=args.pane_ref,
            subject_ref=args.subject_ref,
            evidence_refs=args.evidence_refs,
            redactions=args.redactions,
            details=details,
        )
    except side_effect_ledger_runtime.LedgerRecordError as exc:
        print(f"ERROR: ce ledger record refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(
            {
                "record_path": str(result.record_path),
                "head_path": str(result.head_path),
                "sequence": result.sequence,
                "record_sha256": result.record_sha256,
                "previous_record_sha256": result.previous_record_sha256,
            },
            indent=2,
            sort_keys=True,
        ))
    else:
        print(f"ce ledger record: wrote {result.record_path} (sequence={result.sequence})")
        print(f"record_sha256: {result.record_sha256}")
    return 0


def _ledger_verify(args) -> int:
    try:
        result = side_effect_ledger_runtime.verify(
            side_effect_ledger_root=args.side_effect_ledger_root,
            active_work_ledger_root=args.active_work_ledger_root,
            controller_id=args.controller_id,
            lane_id=args.lane_id,
        )
    except side_effect_ledger_runtime.LedgerVerifyError as exc:
        print(f"ERROR: ce ledger verify [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(result.summary, indent=2, sort_keys=True))
    else:
        status = "OK" if result.ok else "FAIL"
        print(f"ce ledger verify: {status} ({result.summary['record_count']} record(s))")
        for chain in result.summary["chains"]:
            print(
                f"  chain {chain['controller_id']}/{chain['lane_id']}: "
                f"{chain['record_count']} record(s), head={chain['head_sha256']}"
            )
        for error in result.errors:
            print(f"  ERROR: {error}", file=sys.stderr)
    return 0 if result.ok else 1


def _worker_allocate(args) -> int:
    details = None
    if args.details_json is not None:
        try:
            details = json.loads(args.details_json)
        except json.JSONDecodeError as exc:
            print(f"ERROR: ce worker allocate: --details-json is not valid JSON: {exc}", file=sys.stderr)
            return 1
    try:
        result = worker_runtime.allocate_worker(
            policy_path=args.policy,
            controller_id=args.controller_id,
            lane_id=args.lane_id,
            claim_ref=args.claim_ref,
            lease_ref=args.lease_ref,
            active_work_ledger_root=args.active_work_ledger_root,
            container_instance_root=args.container_instance_root,
            instance_id=args.instance_id,
            started_at=args.started_at,
            details=details,
            side_effect_ledger_root=args.side_effect_ledger_root,
            repo_root=args.repo_root,
            runner=_make_worker_runner(),
            broker=_make_worker_broker(),
        )
    except worker_runtime.WorkerRuntimeError as exc:
        print(f"ERROR: ce worker allocate refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(
            {
                "instance_path": str(result.instance_path),
                "container_id": result.container_id,
                "enforcement_primitive": result.record["enforcement_primitive"],
                "secret_grant_count": len(result.secret_grants),
                "side_effect_path": str(result.side_effect_path) if result.side_effect_path else None,
            },
            indent=2,
            sort_keys=True,
        ))
    else:
        print(f"ce worker allocate: started {args.instance_id} -> {result.instance_path}")
        print(f"enforcement_primitive: {result.record['enforcement_primitive']}")
    return 0


def _worker_spawn(args) -> int:
    try:
        result = worker_spawn.spawn_worker(
            role=args.role,
            harness=args.harness,
            worktree=args.worktree,
            scope_id=args.scope_id,
            prompt_file=args.prompt_file,
            brief=args.brief,
            dry_run=args.dry_run,
            depth=args.depth,
            max_depth=args.max_depth,
            parent_id=args.parent_id,
            worker_id=args.worker_id,
            parent_worktree=Path.cwd(),
            launcher=_make_worker_spawn_launcher(),
        )
    except worker_spawn.WorkerSpawnError as exc:
        print(f"ERROR: ce worker spawn refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        verb = "planned" if result.plan.dry_run else "spawned"
        print(f"ce worker spawn: {verb} {result.plan.worker_id} ({result.plan.role}/{result.plan.harness})")
        print(f"record: {result.record_path}")
    return 0


def _worker_run(args) -> int:
    try:
        result = worker_run.run_worker_role(
            role=args.role,
            brief=args.brief,
            repo_root=args.repo_root,
            worktree=args.worktree,
            harness=args.harness,
            run_id=args.run_id,
            parent_id=args.parent_id,
            worker_id=args.worker_id,
            launcher=_make_worker_run_launcher(),
            seeder=_make_worker_run_seeder(),
            collector=_make_worker_run_collector(args.findings_timeout),
        )
    except worker_run.WorkerRunError as exc:
        print(f"ERROR: ce worker run refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(f"ce worker run: completed {result.run_id} ({result.role.name}/{args.harness})")
        print(f"findings: {result.findings_path}")
    return 0


def _worker_scrub_env(args) -> int:
    try:
        child_env, scrubbed = worker_spawn.scrub_worker_environment(
            worker_id=args.worker_id,
            role=args.role,
            scope_id=args.scope_id,
            depth=args.depth,
            parent_id=args.parent_id,
            home_path=args.home_path,
        )
    except worker_spawn.WorkerSpawnError as exc:
        print(f"ERROR: ce worker scrub-env refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    payload = {
        "child_env": child_env,
        "scrubbed_env_names": list(scrubbed),
    }
    if getattr(args, "json_output", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"ce worker scrub-env: {len(child_env)} env vars emitted")
    return 0


def _worker_terminate(args) -> int:
    try:
        result = worker_runtime.terminate_worker(
            instance_id=args.instance_id,
            claim_id=args.claim_id,
            container_instance_root=args.container_instance_root,
            reason=args.reason,
            exit_code=args.exit_code,
            controller_id=args.controller_id,
            lane_id=args.lane_id,
            claim_ref=args.claim_ref,
            active_work_ledger_root=args.active_work_ledger_root,
            side_effect_ledger_root=args.side_effect_ledger_root,
            repo_root=args.repo_root,
            runner=_make_worker_runner(),
            broker=_make_worker_broker(),
        )
    except worker_runtime.WorkerRuntimeError as exc:
        print(f"ERROR: ce worker terminate refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(
            {
                "instance_path": str(result.instance_path),
                "stopped_at": result.record["stopped_at"],
                "side_effect_path": str(result.side_effect_path) if result.side_effect_path else None,
            },
            indent=2,
            sort_keys=True,
        ))
    else:
        print(f"ce worker terminate: stopped {args.instance_id} ({args.reason})")
    return 0


def _worker_gc(args) -> int:
    try:
        result = worker_runtime.garbage_collect_worker(
            container_instance_root=args.container_instance_root,
            claim_id=args.claim_id,
            runner=_make_worker_runner(),
            broker=_make_worker_broker(),
        )
    except worker_runtime.WorkerRuntimeError as exc:
        print(f"ERROR: ce worker gc refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps({"reaped_instance_ids": result.reaped_instance_ids}, indent=2, sort_keys=True))
    else:
        if result.reaped_instance_ids:
            print(f"ce worker gc: reaped {len(result.reaped_instance_ids)} instance(s): "
                  + ", ".join(result.reaped_instance_ids))
        else:
            print("ce worker gc: no orphaned container instances to reap")
    return 0


def _worker_status(args) -> int:
    instance_path = (
        worker_runtime.Path(args.container_instance_root) / args.claim_id / f"{args.instance_id}.yaml"
    )
    if not instance_path.is_file():
        print(f"ERROR: ce worker status: no container-instance record at {instance_path}", file=sys.stderr)
        return 1
    record = worker_runtime.load_yaml(instance_path)
    if getattr(args, "json_output", False):
        print(json.dumps(record, indent=2, sort_keys=True))
    else:
        running = record.get("stopped_at") is None
        print(
            f"ce worker status: {args.instance_id} claim={record.get('claim_id')} "
            f"state={'running' if running else 'stopped'} "
            f"enforcement_primitive={record.get('enforcement_primitive')}"
        )
    return 0


def _worker_worktree_prune(args) -> int:
    extra_roots = []
    if not args.no_default_extra_root:
        extra_roots.append(worktree_prune.DEFAULT_EXTRA_ROOT)
    if args.extra_roots:
        extra_roots.extend(Path(root) for root in args.extra_roots)
    try:
        if args.apply:
            result = worktree_prune.apply_prune(
                repo_root=args.repo_root,
                extra_roots=extra_roots,
                age_hours=args.age_hours,
                state_root=args.state_root,
            )
        else:
            result = worktree_prune.scan_worktrees(
                repo_root=args.repo_root,
                extra_roots=extra_roots,
                age_hours=args.age_hours,
            )
    except worktree_prune.WorktreePruneError as exc:
        print(f"ERROR: ce worker worktree-prune refused: {exc}", file=sys.stderr)
        return 1

    payload = result.to_dict()
    if getattr(args, "json_output", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        action = "applied" if result.applied else "dry-run"
        print(f"ce worker worktree-prune: {action} ({payload['summary']['total']} candidate(s))")
        print(f"{'VERDICT':<12} {'REASON':<18} {'BRANCH':<24} PATH")
        for entry in result.entries:
            branch = entry.branch or "-"
            removed = " removed" if entry.removed else ""
            error = f" error={entry.removal_error}" if entry.removal_error else ""
            print(f"{entry.verdict:<12} {entry.reason:<18} {branch:<24} {entry.path}{removed}{error}")
        if result.audit_path:
            print(f"audit: {result.audit_path}")
    return 1 if payload["summary"]["errors"] else 0


def _fanin_build(args) -> int:
    authority_action = next(
        (name for name in ("ratify", "enqueue", "land") if getattr(args, name, False)), None
    )
    try:
        result = fanin_runtime.build(
            request=args.request,
            packet_root=args.packet_root,
            repo_root=args.repo_root,
            packet_id=args.packet_id,
            authority_action=authority_action,
        )
    except fanin_runtime.FaninBuildError as exc:
        print(f"ERROR: ce fanin build refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(
            {
                "packet_path": str(result.packet_path),
                "content_hash": result.content_hash,
                "evidence_count": result.evidence_count,
                "ledger_chain_count": result.ledger_chain_count,
                "has_authority": False,
            },
            indent=2,
            sort_keys=True,
        ))
    else:
        print(f"ce fanin build: wrote {result.packet_path}")
        print(f"content_hash: {result.content_hash}")
        print(
            f"aggregated {result.evidence_count} evidence manifest(s), "
            f"{result.ledger_chain_count} ledger chain(s); has_authority=false"
        )
    return 0


def _fanin_inspect(args) -> int:
    try:
        result = fanin_runtime.inspect(packet=args.packet)
    except fanin_runtime.FaninInspectError as exc:
        print(f"ERROR: ce fanin inspect [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(
            {
                "ok": result.ok,
                "packet_path": str(result.packet_path),
                "content_hash": result.content_hash,
                "packet_id": result.packet.get("packet_id"),
                "issues": list(result.issues),
            },
            indent=2,
            sort_keys=True,
        ))
    else:
        status = "OK" if result.ok else "FAIL"
        print(f"ce fanin inspect: {status} ({result.packet_path})")
        print(f"content_hash: {result.content_hash}")
        for issue in result.issues:
            print(f"  ERROR: {issue}", file=sys.stderr)
    return 0 if result.ok else 1


def _queue_dry_run(args) -> int:
    # Preview-only (v1). The live belt-driven actions moved to `cev3 queue-poll`
    # (v3) to keep this v1 CLI free of any v3 forge import (ce-ops#218).
    try:
        result = integration_queue_dry_run.build(
            request=args.request,
            preview_root=args.preview_root,
            repo_root=args.repo_root,
            preview_id=args.preview_id,
        )
    except integration_queue_dry_run.QueueBuildError as exc:
        print(f"ERROR: ce queue dry-run refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(
            {
                "preview_path": str(result.preview_path),
                "content_hash": result.content_hash,
                "lane_count": result.lane_count,
                "mode": result.preview["mode"],
                "has_authority": False,
            },
            indent=2,
            sort_keys=True,
        ))
    else:
        print(f"ce queue dry-run: wrote {result.preview_path}")
        print(f"content_hash: {result.content_hash}")
        print(
            f"previewed serialized landing order across {result.lane_count} lane(s); "
            "mode=dry-run has_authority=false"
        )
    return 0


def _queue_inspect(args) -> int:
    try:
        result = integration_queue_dry_run.inspect(preview=args.preview)
    except integration_queue_dry_run.QueueInspectError as exc:
        print(f"ERROR: ce queue inspect [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(
            {
                "ok": result.ok,
                "preview_path": str(result.preview_path),
                "content_hash": result.content_hash,
                "preview_id": result.preview.get("preview_id"),
                "issues": list(result.issues),
            },
            indent=2,
            sort_keys=True,
        ))
    else:
        status = "OK" if result.ok else "FAIL"
        print(f"ce queue inspect: {status} ({result.preview_path})")
        print(f"content_hash: {result.content_hash}")
        for issue in result.issues:
            print(f"  ERROR: {issue}", file=sys.stderr)
    return 0 if result.ok else 1


def _conveyor_bridge(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="ce conveyor")
    sub = parser.add_subparsers(dest="conveyor_cmd", required=True)
    sweep = sub.add_parser(
        "sweep",
        help="enqueue approved+green creator-engine PRs stranded outside the merge queue",
    )
    sweep.add_argument("--repo", default="creator-engine/creator-engine", help="owner/name repository scope")
    sweep.add_argument("--queue-branch", default="main", dest="queue_branch", help="merge queue branch")
    sweep.add_argument("--token-env", default="GH_TOKEN", help="env var containing the GitHub token")
    sweep.add_argument("--dry-run", action="store_true", help="log eligible PRs without enqueueing")
    sweep.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")
    args = parser.parse_args(argv)
    if args.conveyor_cmd != "sweep":
        parser.print_usage(sys.stderr)
        return 2
    command = [
        sys.executable,
        "-m",
        "creator_engine_validator.forge.integrator_belt",
        "stranded-sweep",
        "--repo",
        args.repo,
        "--queue-branch",
        args.queue_branch,
        "--token-env",
        args.token_env,
    ]
    if getattr(args, "dry_run", False):
        command.append("--dry-run")
    if getattr(args, "json_output", False):
        command.append("--json")
    proc = subprocess.run(command, check=False)
    return int(proc.returncode)


def _dequeue(args) -> int:
    argv = [
        sys.executable,
        "-m",
        "creator_engine_validator.v3_cli",
        "queue-dequeue",
        str(args.pr_number),
        "--repo",
        args.repo,
        "--token-env",
        args.token_env,
    ]
    if getattr(args, "convert_to_draft", False):
        argv.append("--convert-to-draft")
    if getattr(args, "json_output", False):
        argv.append("--json")
    env = os.environ.copy()
    env[_V3_FORWARDED_ENV] = "1"
    proc = subprocess.run(argv, check=False, env=env)
    return int(proc.returncode)


def _forward_v3_argv(name: str, remainder: Sequence[str]) -> int:
    _help_text, v3_name = V3_FORWARDING_SHIMS[name]
    env = os.environ.copy()
    env[_V3_FORWARDED_ENV] = "1"
    argv = [
        sys.executable,
        "-m",
        "creator_engine_validator.v3_cli",
        v3_name,
        *remainder,
    ]
    proc = subprocess.run(argv, check=False, env=env)
    return int(proc.returncode)


def _forward_v3_command(args) -> int:
    return _forward_v3_argv(args.group, getattr(args, "v3_args", ()))


def _print_usage_with_stage_map(parser: argparse.ArgumentParser) -> None:
    parser.print_usage(sys.stderr)
    print(journey_guidance.stage_map_text(), file=sys.stderr)


def _event_append(args) -> int:
    try:
        event = json.loads(args.event_json)
    except json.JSONDecodeError as exc:
        print(f"ERROR: ce event append: --event-json is not valid JSON: {exc}", file=sys.stderr)
        return 1
    try:
        result = ce_event_runtime.append(
            stream=args.stream,
            event_root=args.event_root,
            block_id=args.block_id,
            emitting_role=args.emitting_role,
            operating_mode=args.operating_mode,
            event=event,
            recorded_at=args.recorded_at,
            repo_root=args.repo_root,
            key_id=args.key_id,
            signature_value=args.signature_value,
        )
    except ce_event_runtime.CeEventRuntimeError as exc:
        print(f"ERROR: ce event append refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(
            {
                "block_path": str(result.block_path),
                "head_path": str(result.head_path),
                "stream": result.stream,
                "sequence": result.sequence,
                "content_hash": result.content_hash,
                "parent_hash": result.parent_hash,
            },
            indent=2,
            sort_keys=True,
        ))
    else:
        print(f"ce event append: wrote {result.block_path} (stream={result.stream} sequence={result.sequence})")
        print(f"content_hash: {result.content_hash}")
    return 0


def _event_verify(args) -> int:
    try:
        result = ce_event_runtime.verify(stream=args.stream, event_root=args.event_root)
    except ce_event_runtime.CeEventRuntimeError as exc:
        print(f"ERROR: ce event verify [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(result.summary, indent=2, sort_keys=True))
    else:
        status = "OK" if result.ok else "FAIL"
        print(f"ce event verify: {status} (stream={result.stream}, {result.summary['block_count']} block(s))")
        for error in result.errors:
            print(f"  ERROR: {error}", file=sys.stderr)
    return 0 if result.ok else 1


def _event_sign(args) -> int:
    try:
        block = json.loads(args.block_json)
    except json.JSONDecodeError as exc:
        print(f"ERROR: ce event sign: --block-json is not valid JSON: {exc}", file=sys.stderr)
        return 1
    try:
        signed = ce_event_runtime.sign(
            block=block, key_id=args.key_id, signature_value=args.signature_value
        )
    except ce_event_runtime.CeEventRuntimeError as exc:
        print(f"ERROR: ce event sign refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(signed, indent=2, sort_keys=True))
    else:
        print(f"ce event sign: content_hash={signed['content_hash']} signature={signed['signature']['value']}")
    return 0


def _event_replay(args) -> int:
    try:
        result = ce_event_runtime.replay(stream=args.stream, event_root=args.event_root)
    except ce_event_runtime.CeEventRuntimeError as exc:
        print(f"ERROR: ce event replay [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(
            {
                "stream": result.stream,
                "content_hash": result.content_hash,
                "block_count": result.projection["block_count"],
                "blocks": list(result.blocks),
            },
            indent=2,
            sort_keys=True,
        ))
    else:
        print(f"ce event replay: stream={result.stream} ({result.projection['block_count']} block(s))")
        print(f"content_hash: {result.content_hash}")
    return 0


def _event_index(args) -> int:
    try:
        result = ce_event_runtime.index(stream=args.stream, event_root=args.event_root)
    except ce_event_runtime.CeEventRuntimeError as exc:
        print(f"ERROR: ce event index [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(result.index, indent=2, sort_keys=True))
    else:
        print(f"ce event index: stream={result.stream} ({result.index['block_count']} block(s))")
        print(f"content_hash: {result.content_hash}")
    return 0


def _pcl_append(args) -> int:
    try:
        body = json.loads(args.body_json)
    except json.JSONDecodeError as exc:
        print(f"ERROR: ce pcl append: --body-json is not valid JSON: {exc}", file=sys.stderr)
        return 1
    try:
        result = pcl_runtime.append(
            ledger=args.ledger,
            pcl_root=args.pcl_root,
            record_id=args.record_id,
            record_kind=args.record_kind,
            emitting_role=args.emitting_role,
            operating_mode=args.operating_mode,
            body=body,
            recorded_at=args.recorded_at,
            repo_root=args.repo_root,
            key_id=args.key_id,
            signature_value=args.signature_value,
        )
    except pcl_runtime.PclRuntimeError as exc:
        print(f"ERROR: ce pcl append refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(
            {
                "record_path": str(result.record_path),
                "head_path": str(result.head_path),
                "ledger": result.ledger,
                "sequence": result.sequence,
                "content_hash": result.content_hash,
                "parent_hash": result.parent_hash,
            },
            indent=2,
            sort_keys=True,
        ))
    else:
        print(f"ce pcl append: wrote {result.record_path} (ledger={result.ledger} sequence={result.sequence})")
        print(f"content_hash: {result.content_hash}")
    return 0


def _pcl_verify(args) -> int:
    try:
        result = pcl_runtime.verify(ledger=args.ledger, pcl_root=args.pcl_root)
    except pcl_runtime.PclRuntimeError as exc:
        print(f"ERROR: ce pcl verify [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(result.summary, indent=2, sort_keys=True))
    else:
        status = "OK" if result.ok else "FAIL"
        print(f"ce pcl verify: {status} (ledger={result.ledger}, {result.summary['record_count']} record(s))")
        for error in result.errors:
            print(f"  ERROR: {error}", file=sys.stderr)
    return 0 if result.ok else 1


def _pcl_replay(args) -> int:
    try:
        result = pcl_runtime.replay(ledger=args.ledger, pcl_root=args.pcl_root)
    except pcl_runtime.PclRuntimeError as exc:
        print(f"ERROR: ce pcl replay [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(
            {
                "ledger": result.ledger,
                "content_hash": result.content_hash,
                "record_count": result.projection["record_count"],
                "records": list(result.records),
            },
            indent=2,
            sort_keys=True,
        ))
    else:
        print(f"ce pcl replay: ledger={result.ledger} ({result.projection['record_count']} record(s))")
        print(f"content_hash: {result.content_hash}")
    return 0


def _pcl_index(args) -> int:
    try:
        result = pcl_runtime.index(
            ledger=args.ledger,
            pcl_root=args.pcl_root,
            write_cache=not getattr(args, "no_cache", False),
            repo_root=args.repo_root,
        )
    except pcl_runtime.PclRuntimeError as exc:
        print(f"ERROR: ce pcl index [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(result.index, indent=2, sort_keys=True))
    else:
        print(f"ce pcl index: ledger={result.ledger} ({result.index['record_count']} record(s))")
        print(f"content_hash: {result.content_hash}")
        if result.cache_path is not None:
            print(f"cache: {result.cache_path}")
    return 0


def _pcl_merge(args) -> int:
    try:
        result = pcl_runtime.merge(
            sources=args.sources,
            target=args.target,
            pcl_root=args.pcl_root,
            write_cache=not getattr(args, "no_cache", False),
            repo_root=args.repo_root,
        )
    except pcl_runtime.PclRuntimeError as exc:
        print(f"ERROR: ce pcl merge [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(result.merged, indent=2, sort_keys=True))
    else:
        print(f"ce pcl merge: target={result.target} ({result.merged['record_count']} record(s))")
        print(f"content_hash: {result.content_hash}")
        if result.cache_path is not None:
            print(f"cache: {result.cache_path}")
    return 0


def _brain_claim(args, *, context: str) -> dict:
    try:
        claim = json.loads(args.claim_json)
    except json.JSONDecodeError as exc:
        print(f"ERROR: ce brain {context}: --claim-json is not valid JSON: {exc}", file=sys.stderr)
        raise SystemExit(1)
    if not isinstance(claim, dict):
        print(f"ERROR: ce brain {context}: --claim-json must decode to a JSON object", file=sys.stderr)
        raise SystemExit(1)
    return claim


def _brain_scope(args, *, required: bool) -> str | dict | None:
    raw_json = getattr(args, "scope_json", None)
    if raw_json is not None:
        try:
            scope = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            print(f"ERROR: ce brain: --scope-json is not valid JSON: {exc}", file=sys.stderr)
            raise SystemExit(1)
        if not isinstance(scope, dict):
            print("ERROR: ce brain: --scope-json must decode to a JSON object", file=sys.stderr)
            raise SystemExit(1)
        return scope
    scope_text = getattr(args, "scope", None)
    if scope_text is not None:
        return scope_text
    if required:
        print("ERROR: ce brain: scope is required", file=sys.stderr)
        raise SystemExit(1)
    return None


def _brain_error(verb: str, exc: brain_runtime.BrainRuntimeError) -> int:
    print(f"ERROR: ce brain {verb} refused [{exc.code}]: {exc}", file=sys.stderr)
    errors = getattr(exc, "errors", ())
    for error in errors:
        print(f"  ERROR: {error.format()}", file=sys.stderr)
    return 1


def _brain_assert(args) -> int:
    try:
        result = brain_runtime.assert_claim(
            claim=_brain_claim(args, context="assert"),
            scope=_brain_scope(args, required=True),
            evidence_ref=args.evidence_ref,
            statement=args.statement,
            assertion_type=args.assertion_type,
            verification_method=args.verification_method,
            state_root=args.state_root,
            assertion_id=args.assertion_id,
        )
    except SystemExit as exc:
        return int(exc.code)
    except brain_runtime.BrainRuntimeError as exc:
        return _brain_error("assert", exc)
    if getattr(args, "json_output", False):
        print(json.dumps(
            {
                "ledger_path": str(result.ledger_path),
                "id": result.record["id"],
                "status": result.record["status"],
                "sequence": result.sequence,
                "content_hash": result.content_hash,
                "prev_hash": result.prev_hash,
            },
            indent=2,
            sort_keys=True,
        ))
    else:
        print(f"ce brain assert: wrote {result.record['id']} to {result.ledger_path}")
        print(f"content_hash: {result.content_hash}")
    return 0


def _brain_check(args) -> int:
    try:
        result = brain_runtime.check_claim(
            claim=_brain_claim(args, context="check"),
            scope=_brain_scope(args, required=True),
            state_root=args.state_root,
        )
    except SystemExit as exc:
        return int(exc.code)
    except brain_runtime.BrainRuntimeError as exc:
        return _brain_error("check", exc)
    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    elif result.status == "unknown":
        print("ce brain check: unknown")
    else:
        assert result.record is not None
        print(f"ce brain check: active ({result.record['id']})")
        print(f"content_hash: {result.record['content_hash']}")
    return 0


def _brain_correct(args) -> int:
    try:
        result = brain_runtime.correct_claim(
            assertion_id=args.assertion_id,
            claim=_brain_claim(args, context="correct"),
            scope=_brain_scope(args, required=False),
            evidence_ref=args.evidence_ref,
            statement=args.statement,
            assertion_type=args.assertion_type,
            verification_method=args.verification_method,
            state_root=args.state_root,
            new_assertion_id=args.new_assertion_id,
        )
    except SystemExit as exc:
        return int(exc.code)
    except brain_runtime.BrainRuntimeError as exc:
        return _brain_error("correct", exc)
    if getattr(args, "json_output", False):
        print(json.dumps(
            {
                "ledger_path": str(result.ledger_path),
                "superseded_id": result.superseded_record["id"],
                "superseded_status": result.superseded_record["status"],
                "id": result.record["id"],
                "status": result.record["status"],
                "content_hash": result.record["content_hash"],
            },
            indent=2,
            sort_keys=True,
        ))
    else:
        print(
            f"ce brain correct: superseded {result.superseded_record['id']} "
            f"with {result.record['id']}"
        )
        print(f"content_hash: {result.record['content_hash']}")
    return 0


def _brain_verify(args) -> int:
    if getattr(args, "drift", False):
        drift = ce_brain_drift.verify_state_root(args.state_root)
        ok = drift.ok
        errors = [error.format() for error in drift.findings]
        summary = {
            "active_count": drift.active_count,
            "drift": drift.to_dict(),
            "errors": errors,
            "head_content_hash": drift.head_content_hash,
            "record_count": drift.record_count,
        }
    else:
        result = brain_runtime.verify_ledger(args.state_root)
        summary = dict(result.summary)
        probe_errors = ce_brain_assertions.validate_file(result.ledger_path) if result.ok else []
        ok = result.ok and not probe_errors
        errors = [*result.errors, *(error.format() for error in probe_errors)]
        summary["errors"] = errors
    if getattr(args, "json_output", False):
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        status = "OK" if ok else "FAIL"
        suffix = " --drift" if getattr(args, "drift", False) else ""
        print(f"ce brain verify{suffix}: {status} ({summary.get('record_count', 0)} record(s))")
        for error in errors:
            print(f"  ERROR: {error}", file=sys.stderr)
        if getattr(args, "drift", False) and not ok:
            print(
                "  NOTE: If this is ignored instance-local .ce/state/brain drift, "
                "run `ce brain sync` to reconcile from tracked .ce/brain sources; "
                "CI is unaffected by ignored instance-local runtime state. "
                "PR changes to tracked .ce/brain sources are still gated.",
                file=sys.stderr,
            )
    return 0 if ok else 1


def _brain_hydrate(args) -> int:
    try:
        payload = brain_runtime.hydrate_contract(args.state_root)
    except brain_runtime.BrainRuntimeError as exc:
        return _brain_error("hydrate", exc)
    if getattr(args, "json_output", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    summary = payload["summary"]
    resume = payload.get("newest_resume_state")
    print(
        "ce brain hydrate: "
        f"{summary['active_decision_count']} active decision(s), "
        f"{summary['active_lesson_count']} active lesson(s)"
    )
    print(f"ledger_path: {payload['ledger_path']}")
    print(f"newest_resume_state: {resume['path'] if resume else 'none'}")
    return 0


def _brain_sync(args) -> int:
    try:
        result = brain_runtime.sync_authoritative_ledger(
            state_root=args.state_root,
            repo_root=getattr(args, "repo_root", None),
        )
    except brain_runtime.BrainRuntimeError as exc:
        return _brain_error("sync", exc)
    payload = {
        "active_count": result.active_count,
        "authoritative_exists": result.authoritative_exists,
        "authoritative_path": str(result.authoritative_path),
        "head_content_hash": result.head_content_hash,
        "ledger_path": str(result.ledger_path),
        "record_count": result.record_count,
        "updated": result.updated,
    }
    if getattr(args, "json_output", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif result.authoritative_exists:
        action = "reconciled" if result.updated else "already in sync"
        print(f"ce brain sync: {action} ({result.record_count} record(s))")
        print(f"source: {result.authoritative_path}")
        print(f"target: {result.ledger_path}")
        if result.head_content_hash is not None:
            print(f"head_content_hash: {result.head_content_hash}")
    else:
        print(f"ce brain sync: no canonical brain ledger at {result.authoritative_path}; nothing to reconcile")
    return 0


def _brain_reconcile(args) -> int:
    try:
        if getattr(args, "apply", False):
            if not args.accept_plan_sha:
                raise brain_reconcile.BrainReconcileRefused("--apply requires --accept-plan-sha")
            result = brain_reconcile.apply(
                repo_root=args.repo_root,
                ledger_path=args.ledger_path,
                assertion_ids=args.assertion_ids,
                accept_plan_sha=args.accept_plan_sha,
            )
            payload = result.to_dict()
        else:
            if args.accept_plan_sha:
                raise brain_reconcile.BrainReconcileRefused("--accept-plan-sha requires --apply")
            payload = {"ledger_path": str((Path(args.repo_root) / (args.ledger_path or ".ce/brain/assertions.yaml")).resolve()),
                       "persisted_sha256": None,
                       "plan": brain_reconcile.plan(repo_root=args.repo_root, ledger_path=args.ledger_path, assertion_ids=args.assertion_ids),
                       "written": False}
    except brain_runtime.BrainRuntimeError as exc:
        return _brain_error("reconcile", exc)
    if getattr(args, "json_output", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        plan = payload["plan"]
        action = "wrote" if payload["written"] else "planned"
        print(f"ce brain reconcile: {action} {len(plan['changed_assertion_ids'])} assertion(s)")
        print(f"plan_sha256: {plan['plan_sha256']}")
        print(f"ledger_head_before: {plan['ledger_head_before']}")
        print(f"ledger_head_after: {plan['ledger_head_after']}")
        if payload["persisted_sha256"] is not None:
            print(f"persisted_sha256: {payload['persisted_sha256']}")
    return 0


def _brain_probe(args) -> int:
    has_name = getattr(args, "probe_name", None) is not None
    has_all = bool(getattr(args, "all_probes", False))
    if has_name == has_all:
        print("ERROR: ce brain probe: specify exactly one of <name> or --all", file=sys.stderr)
        return 2
    if has_all:
        results = sorted(brain_probe.probe_all(), key=lambda result: result.name)
        payload = {"probes": [result.to_dict() for result in results]}
        if getattr(args, "json_output", False):
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            for result in results:
                print(f"ce brain probe {result.name}: {result.verdict}")
        return 0

    result = brain_probe.probe(args.probe_name)
    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(f"ce brain probe {result.name}: {result.verdict}")
    return 0


def _brain_eval(args) -> int:
    from . import brain_eval

    report = brain_eval.run_eval()
    payload = report.to_dict()
    if getattr(args, "json_output", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        status = "OK" if report.ok else "FAIL"
        print(
            f"ce brain eval: {status} "
            f"({report.passed_count}/{report.case_count} case(s) passed; "
            f"{report.fixture_count} fixture(s))"
        )
        for leg, metrics in payload["metrics"].items():
            summary = " ".join(f"{name}={value:.6f}" for name, value in metrics.items())
            print(f"  {leg}: {summary}")
    return 0 if report.ok else 1


def _brain_ingest(args) -> int:
    try:
        scope = _brain_scope(args, required=False)
    except SystemExit as exc:
        return int(exc.code)
    if scope is None:
        scope = brain_ingest_runtime.DEFAULT_SCOPE
    try:
        result = brain_ingest_runtime.ingest_markdown(
            sources=args.sources,
            state_root=args.state_root,
            db_path=args.db,
            scope=scope,
            embedder_name=args.embedder,
            model_path=args.model_path,
            endpoint=getattr(args, "endpoint", None),
            endpoint_model_id=getattr(args, "endpoint_model_id", None),
            endpoint_dim=getattr(args, "endpoint_dim", None),
            allow_confidential_egress=args.allow_confidential_egress,
            as_of=args.as_of,
        )
    except brain_ingest_runtime.BrainIngestError as exc:
        print(f"ERROR: ce brain ingest refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    except brain_recall.BrainRecallError as exc:
        print(f"ERROR: ce brain ingest refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1

    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(f"ce brain ingest: {result.chunk_count} chunk(s) from {result.source_count} source file(s)")
        print(f"db: {result.db_path}")
        print(f"model: {result.model_id} dim={result.dim}")
        print(
            f"upserted: {result.embedded_count} skipped: {result.skipped_count} "
            f"deleted: {result.deleted_count}"
        )
    return 0


def _brain_bootstrap(args) -> int:
    try:
        payload = brain_bootstrap.build_bootstrap_payload(
            state_root=args.state_root,
            scope=_brain_scope(args, required=False),
            role=args.role,
            seat_class=args.seat_class,
        )
    except SystemExit as exc:
        return int(exc.code)
    except brain_bootstrap.BrainBootstrapRefused as exc:
        print(f"ERROR: ce brain bootstrap refused [{exc.code}]: {exc}", file=sys.stderr)
        for error in getattr(exc, "errors", ()):
            print(f"  ERROR: {error}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        ks = payload["knowledge_ssot"]
        print(
            "ce brain bootstrap: "
            f"{ks['scope_relevant_count']} assertion(s) "
            f"from {ks['record_count']} record(s)"
        )
        print(f"head_content_hash: {ks['head_content_hash']}")
    return 0


def _orchestrator_status(args) -> int:
    status = orchestrator_status.load_status(
        repo_root=getattr(args, "repo_root", "."),
        state_dir=getattr(args, "state_dir", None),
    )
    if getattr(args, "json_output", False):
        print(json.dumps(status, indent=2, sort_keys=True))
    else:
        print(orchestrator_status.render_human(status))
    return 0 if status["ok"] else 1


# ce-ops#206: the fixed, deterministic genesis assertion `ce brain init` writes
# to bootstrap an empty workspace's brain ledger. Its claim merely records that
# the ledger was genesis-initialized — it carries no capability verdict and is
# never corrected; downstream asserts/corrects layer on top of it. The id is
# fixed so re-running init is a deterministic no-op rather than appending a
# fresh genesis on every invocation.
_BRAIN_INIT_ASSERTION_ID = "brain-assertion-genesis-0001"
_BRAIN_INIT_SCOPE = "global"
_BRAIN_INIT_CLAIM = {
    "subject": "brain-ledger",
    "predicate": "is",
    "object": "genesis-initialized",
}
_BRAIN_INIT_EVIDENCE_REF = "ce-ops#206:ce-brain-init"


def _brain_init_payload(result_path, *, created: bool, summary) -> dict:
    return {
        "ledger_path": str(result_path),
        "created": created,
        "already_initialized": not created,
        "genesis_id": _BRAIN_INIT_ASSERTION_ID,
        "record_count": summary.get("record_count"),
        "active_count": summary.get("active_count"),
        "head_content_hash": summary.get("head_content_hash"),
    }


class BrainInitError(Exception):
    """``brain_init`` refused (fail-closed: a corrupt/invalid ledger)."""

    def __init__(self, message: str, *, errors: Sequence[str] = ()) -> None:
        super().__init__(message)
        self.errors = list(errors)


class BrainInitOutcome:
    """Structured, JSON-safe result of the programmatic ``brain_init`` (PR-4).

    The genesis-ledger bootstrap, library-callable for orchestration by
    ``ce onboard`` (so the orchestrator does not shell out to its own CLI). The
    CLI handler ``_brain_init`` renders the same outcome.
    """

    def __init__(self, payload: dict, *, content_hash: str | None) -> None:
        self.payload = payload
        self.content_hash = content_hash

    @property
    def created(self) -> bool:
        return bool(self.payload.get("created"))

    def to_dict(self) -> dict:
        return dict(self.payload)


def brain_init(state_root=V3_LOCAL_STATE_ROOT) -> BrainInitOutcome:
    """Idempotently bootstrap a valid genesis brain assertion ledger (ce-ops#206).

    Idempotent / fail-closed: a present VALID ledger is a no-op; a corrupt /
    invalid / conflicting ledger raises :class:`BrainInitError` (we never
    overwrite or append a duplicate genesis on top of a broken ledger).
    """
    path = brain_runtime.ledger_path(state_root)
    if path.is_file():
        verify = brain_runtime.verify_ledger(state_root)
        if verify.ok:
            payload = _brain_init_payload(verify.ledger_path, created=False, summary=verify.summary)
            return BrainInitOutcome(payload, content_hash=verify.summary.get("head_content_hash"))
        raise BrainInitError(
            f"existing ledger at {path} is not valid; refusing to overwrite",
            errors=verify.errors,
        )

    result = brain_runtime.assert_claim(
        claim=dict(_BRAIN_INIT_CLAIM),
        scope=_BRAIN_INIT_SCOPE,
        evidence_ref=_BRAIN_INIT_EVIDENCE_REF,
        state_root=state_root,
        assertion_id=_BRAIN_INIT_ASSERTION_ID,
    )
    verify = brain_runtime.verify_ledger(state_root)
    if not verify.ok:
        # Defensive: the SSOT write path should always land a valid ledger.
        raise BrainInitError(
            f"wrote ledger at {result.ledger_path} but it did not verify",
            errors=verify.errors,
        )
    payload = _brain_init_payload(result.ledger_path, created=True, summary=verify.summary)
    return BrainInitOutcome(payload, content_hash=result.content_hash)


def _brain_init(args) -> int:
    state_root = args.state_root
    path = brain_runtime.ledger_path(state_root)
    json_output = getattr(args, "json_output", False)
    try:
        outcome = brain_init(state_root)
    except BrainInitError as exc:
        print(
            f"ERROR: ce brain init refused [CE-BRAIN-INIT-REFUSED]: {exc}",
            file=sys.stderr,
        )
        for error in exc.errors:
            print(f"  ERROR: {error}", file=sys.stderr)
        return 1
    except brain_runtime.BrainRuntimeError as exc:
        return _brain_error("init", exc)

    if json_output:
        print(json.dumps(outcome.payload, indent=2, sort_keys=True))
    elif outcome.created:
        print(f"ce brain init: initialized genesis ledger at {outcome.payload['ledger_path']}")
        print(f"content_hash: {outcome.content_hash}")
    else:
        print(f"ce brain init: already initialized ({path})")
        print(f"head_content_hash: {outcome.payload.get('head_content_hash')}")
    return 0


def _brain_recall(args) -> int:
    db_path = args.db
    if db_path is None:
        db_path = brain_ingest_runtime.default_db_path(args.state_root)
    try:
        surface = brain_recall_surface.open_surface(
            db_path=db_path,
            state_root=args.state_root,
            embedder_name=args.embedder,
            model_path=args.model_path,
            endpoint=getattr(args, "endpoint", None),
            endpoint_model_id=getattr(args, "endpoint_model_id", None),
            endpoint_dim=getattr(args, "endpoint_dim", None),
        )
    except brain_recall.BrainRecallError as exc:
        print(f"ERROR: ce brain recall refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    try:
        if getattr(args, "hydrate", False):
            payload = surface.hydrate_session(
                args.context,
                top_k=args.top_k,
                core_path=args.core_path,
                scope=args.scope,
                as_of=args.as_of,
                allow_confidential_egress=args.allow_confidential_egress,
            )
        else:
            payload = surface.recall(
                args.context,
                top_k=args.top_k,
                scope=args.scope,
                as_of=args.as_of,
                allow_confidential_egress=args.allow_confidential_egress,
            )
    except brain_recall.BrainRecallError as exc:
        print(f"ERROR: ce brain recall refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    except brain_runtime.BrainRuntimeError as exc:
        # A malformed/tampered SSOT ledger fails CLOSED: refuse rather than
        # silently downgrade to probabilistic-only recall.
        return _brain_error("recall", exc)

    if getattr(args, "json_output", False):
        print(json.dumps(payload.to_dict(), indent=2, sort_keys=True))
        return 0

    if getattr(args, "hydrate", False):
        print(
            f"ce brain recall (hydrate): CORE {'loaded' if payload.core_loaded else 'absent'}"
            f"{f' ({payload.core_path})' if payload.core_path else ''}; "
            f"{len(payload.recall)} additive recall pointer(s)"
        )
        items = payload.recall
    else:
        print(f"ce brain recall: {len(payload.items)} item(s) for {args.context!r}")
        items = payload.items
    for item in items:
        if item.tier == brain_recall_surface.TIER_SSOT:
            print(f"  [SSOT] {item.assertion_id} (verified) score={item.score}")
        else:
            print(
                f"  [recall] {item.source_path}#{item.chunk_ref} "
                f"as_of={item.as_of} score={item.score} (re-verify against source)"
            )
    return 0


def _connector_plan_payload(plan) -> dict:
    return {
        "connector_id": plan.connector_id,
        "connector_kind": plan.connector_kind,
        "provider_class": plan.provider_class,
        "capability_scope": plan.capability_scope,
        "read_verbs": list(plan.read_verbs),
        "assignment_ref": plan.assignment_ref,
        "credential_ref_name": plan.credential_ref_name,
    }


def _connector_verify(args, *, verb: str = "verify") -> int:
    try:
        plan = connector_runtime.verify(connector_path=args.connector, mission_brief_path=args.mission_brief)
    except connector_runtime.ConnectorRuntimeError as exc:
        print(f"ERROR: ce connector {verb} [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(_connector_plan_payload(plan), indent=2, sort_keys=True))
    else:
        print(f"ce connector {verb}: OK (connector={plan.connector_id} scope={plan.capability_scope} kind={plan.connector_kind})")
    return 0


def _connector_plan(args) -> int:
    return _connector_verify(args, verb="plan")


def _connector_fetch(args) -> int:
    try:
        receipt = connector_runtime.fetch(
            connector_path=args.connector,
            mission_brief_path=args.mission_brief,
            resource=args.resource,
            provider=args.provider,
            base_url=args.base_url,
        )
    except connector_runtime.ConnectorRuntimeError as exc:
        print(f"ERROR: ce connector fetch [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(receipt.to_dict(), indent=2, sort_keys=True))
    else:
        print(f"ce connector fetch: status={receipt.status} results={receipt.result_count} (connector={receipt.connector_id})")
    return 0


def _connector_write_plan_payload(plan) -> dict:
    return {
        "connector_id": plan.connector_id,
        "connector_kind": plan.connector_kind,
        "provider_class": plan.provider_class,
        "capability_scope": plan.capability_scope,
        "write_verbs": list(plan.write_verbs),
        "operating_mode": plan.operating_mode,
        "assignment_ref": plan.assignment_ref,
        "credential_ref_name": plan.credential_ref_name,
    }


def _connector_write_plan(args) -> int:
    try:
        plan = connector_runtime.write_plan(connector_path=args.connector, mission_brief_path=args.mission_brief)
    except connector_runtime.ConnectorRuntimeError as exc:
        print(f"ERROR: ce connector write-plan [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(_connector_write_plan_payload(plan), indent=2, sort_keys=True))
    else:
        print(
            f"ce connector write-plan: OK (connector={plan.connector_id} scope={plan.capability_scope} "
            f"mode={plan.operating_mode} verbs={','.join(plan.write_verbs)})"
        )
    return 0


def _connector_submit(args) -> int:
    payload = None
    if getattr(args, "payload", None):
        try:
            with open(args.payload, encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, ValueError) as exc:
            print(f"ERROR: ce connector submit [G2-CONN-VALIDATION]: cannot read --payload: {exc}", file=sys.stderr)
            return 1
    try:
        receipt = connector_runtime.submit(
            connector_path=args.connector,
            mission_brief_path=args.mission_brief,
            verb=args.verb,
            resource=args.resource,
            payload=payload,
            base_url=args.base_url,
        )
    except connector_runtime.ConnectorRuntimeError as exc:
        print(f"ERROR: ce connector submit [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(receipt.to_dict(), indent=2, sort_keys=True))
    else:
        print(f"ce connector submit: status={receipt.status} verb={receipt.verb} (connector={receipt.connector_id})")
    return 0


def _default_repo_name(repo_root) -> str:
    remote = reviewer_triage.git_value(repo_root, "remote", "get-url", "origin")
    if not remote:
        return "unknown/unknown"
    remote = remote.rstrip("/")
    if remote.endswith(".git"):
        remote = remote[:-4]
    if remote.startswith("git@") and ":" in remote:
        return remote.split(":", 1)[1]
    if "github.com/" in remote:
        return remote.split("github.com/", 1)[1]
    return remote.rsplit("/", 2)[-2] + "/" + remote.rsplit("/", 1)[-1] if "/" in remote else remote


def _reviewer_triage_plan(args) -> int:
    from pathlib import Path

    repo_root = Path(args.repo_root)
    repo = args.repo or _default_repo_name(repo_root)
    head_sha = args.head_sha or reviewer_triage.git_value(repo_root, "rev-parse", "HEAD") or "0" * 40
    changed_paths = list(args.changed_paths or reviewer_triage.git_changed_paths(repo_root))
    mutation_classes = list(args.mutation_classes or reviewer_triage.infer_mutation_classes(changed_paths))
    registry_path = Path(args.registry) if args.registry else repo_root / ".ce" / "reviewer-registry.yml"
    coordination_path = (
        Path(args.coordination_policy)
        if args.coordination_policy
        else repo_root / ".ce" / "coordination.yml"
    )
    codeowners_text = args.codeowners_text
    if codeowners_text is None:
        codeowners_path = Path(args.codeowners) if args.codeowners else repo_root / ".github" / "CODEOWNERS"
        codeowners_text = reviewer_triage.read_text_if_exists(codeowners_path)

    last_pusher = None
    if args.last_pusher_login or args.last_pusher_human_id:
        last_pusher = {
            "login": args.last_pusher_login or "",
            "human_id": args.last_pusher_human_id or "",
        }

    decision = reviewer_triage.plan_reviewer_triage(
        repo=repo,
        pr_number=args.pr_number,
        head_sha=head_sha,
        expected_head_sha=args.expected_head_sha or head_sha,
        author_run_id=args.author_run_id or f"pr-{args.pr_number}",
        author_identity={
            "login": args.author_login or "",
            "human_id": args.author_human_id or "",
            "controller_id": args.author_controller_id or "",
            "venue_id": args.author_venue_id or "",
            "credential_domain_ref": args.author_credential_domain_ref or "",
            "os_user_ref": args.author_os_user_ref or "",
            "host_ref": args.author_host_ref or "",
        },
        last_pusher=last_pusher,
        changed_paths=changed_paths,
        mutation_classes=mutation_classes,
        risk_tier=args.risk_tier,
        codeowners_text=codeowners_text,
        coordination_policy=reviewer_triage.load_optional_yaml(coordination_path),
        registry=reviewer_triage.load_optional_yaml(registry_path),
        ruleset_required_teams=list(args.required_teams or []),
    )
    if getattr(args, "json_output", False):
        print(json.dumps(decision, indent=2, sort_keys=True))
    else:
        selected = decision["assignment"]["selected_reviewers"]
        if selected:
            print(f"ce reviewer-triage plan: selected {', '.join(selected)}")
        else:
            esc = decision["escalation"]
            print(f"ce reviewer-triage plan: no assignment ({esc['status']}:{esc['reason']})")
    return 0


def _emit_triage_queue(args, payload: dict) -> int:
    if getattr(args, "json_output", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        kind = payload.get("kind", "ce-triage-queue")
        count = payload.get("queue_entry_count", 0)
        applied = "applied" if payload.get("applied") else "planned"
        print(f"{kind}: {applied} {count} entr{'y' if count == 1 else 'ies'}")
        for warning in payload.get("warnings", ()):
            print(f"  warning: {warning}", file=sys.stderr)
    return 0


def _triage_queue_scan(args) -> int:
    try:
        payload = ce_ops_triage_queue.scan_and_triage(
            repo=args.repo,
            queue_issue=args.queue_issue,
            audit_root=args.audit_root,
            apply=getattr(args, "apply", False),
            gh_runner=_make_gh_runner(),
        )
    except Exception as exc:  # noqa: BLE001 - advisory workflow must fail open.
        payload = {
            "kind": "ce-triage-queue-scan",
            "schema_version": ce_ops_triage_queue.SCHEMA_VERSION,
            "advisory": ce_ops_triage_queue.NON_AUTHORITY_STATEMENT,
            "repo": args.repo,
            "queue_issue": args.queue_issue,
            "applied": False,
            "queue_entry_count": 0,
            "entries": [],
            "warnings": [f"scan_failed:{exc}"],
        }
    return _emit_triage_queue(args, payload)


def _triage_queue_inspect(args) -> int:
    try:
        payload = ce_ops_triage_queue.inspect_queue(
            repo=args.repo,
            queue_issue=args.queue_issue,
            audit_root=args.audit_root,
            gh_runner=_make_gh_runner(),
        )
        if getattr(args, "apply", False):
            payload.setdefault("warnings", []).append("inspect_ignores_apply")
    except Exception as exc:  # noqa: BLE001 - advisory workflow must fail open.
        payload = {
            "kind": "ce-triage-queue-inspect",
            "schema_version": ce_ops_triage_queue.SCHEMA_VERSION,
            "advisory": ce_ops_triage_queue.NON_AUTHORITY_STATEMENT,
            "repo": args.repo,
            "queue_issue": args.queue_issue,
            "comment_id": None,
            "queue_entry_count": 0,
            "entries": [],
            "warnings": [f"inspect_failed:{exc}"],
        }
    return _emit_triage_queue(args, payload)


def _emit_dependency_unlock(args, payload: dict) -> int:
    if getattr(args, "json_output", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        kind = payload.get("kind", dependency_unlock.KIND)
        status = payload.get("status", "unknown")
        count = payload.get("proposal_count", 0)
        print(f"{kind}: {status} mode={payload.get('mode', 'shadow')} proposal_count={count}")
        for warning in payload.get("warnings", ()):
            print(f"  warning: {warning}", file=sys.stderr)
    return 0


def _dependency_unlock_skip_payload(reason: str) -> dict:
    return {
        "kind": dependency_unlock.KIND,
        "schema_version": dependency_unlock.SCHEMA_VERSION,
        "advisory": dependency_unlock.NON_AUTHORITY_STATEMENT,
        "status": "skipped",
        "reason": reason,
        "proposal_count": 0,
        "proposals": [],
        "warnings": [reason],
    }


def _dependency_unlock_scan(args) -> int:
    now = dependency_unlock.utc_now_iso()
    merged = None
    if args.pr_repo and args.pr_number is not None and args.merge_sha and args.merged_at:
        merged = dependency_unlock.MergedItem(
            repo=args.pr_repo,
            number=args.pr_number,
            merge_sha=args.merge_sha,
            merged_at=args.merged_at,
        )
    else:
        event_path = args.event_path or os.environ.get("GITHUB_EVENT_PATH")
        if event_path:
            try:
                event = json.loads(Path(event_path).read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                payload = _dependency_unlock_skip_payload(f"event_unreadable:{exc}")
                dependency_unlock.write_audit_record(args.audit_root, payload, evaluated_at=now)
                return _emit_dependency_unlock(args, payload)
            merged = dependency_unlock.merged_item_from_event(
                event, default_repo=os.environ.get("GITHUB_REPOSITORY")
            )

    if merged is None:
        payload = _dependency_unlock_skip_payload("no_merged_pr_context")
        dependency_unlock.write_audit_record(args.audit_root, payload, evaluated_at=now)
        return _emit_dependency_unlock(args, payload)

    try:
        payload = dependency_unlock.evaluate_pr_merge(
            merged,
            search_repo=args.search_repo,
            run_mode=os.environ.get("CE_DEP_UNLOCK_RUN_MODE"),
            kill_switch=os.environ.get("CE_DEP_UNLOCK_KILL_SWITCH"),
            gh_runner=_make_gh_runner(),
            audit_root=args.audit_root,
            now=now,
        )
    except Exception as exc:  # noqa: BLE001 - advisory workflow must fail open.
        payload = {
            "kind": dependency_unlock.KIND,
            "schema_version": dependency_unlock.SCHEMA_VERSION,
            "advisory": dependency_unlock.NON_AUTHORITY_STATEMENT,
            "status": "refused",
            "reason": f"scan_failed:{exc}",
            "proposal_count": 0,
            "proposals": [],
            "warnings": [f"scan_failed:{exc}"],
        }
        dependency_unlock.write_audit_record(args.audit_root, payload, evaluated_at=now)
    return _emit_dependency_unlock(args, payload)


def _pickup_triage(args) -> int:
    try:
        if args.issues_json == "-":
            issues_text = sys.stdin.read()
        else:
            issues_text = Path(args.issues_json).read_text(encoding="utf-8")
        issue_payloads = forge_triage.load_issue_payloads(issues_text)
        apply = getattr(args, "apply", False)
        check_claims = apply or getattr(args, "check_claims", False)
        runner = _make_gh_runner() if check_claims else None
        result = forge_triage.plan_triage(
            arc_ticket=args.arc_ticket,
            issues=issue_payloads,
            repo=args.repo,
            pickup_label=args.label,
            assign_to=getattr(args, "triage_seats", ()) or (),
            gh_runner=runner,
        )
        if apply:
            result = forge_triage.apply_triage_result(result, runner)
    except (OSError, forge_triage.ForgeTriageError) as exc:
        payload = {"ok": False, "error": str(exc)}
        if getattr(args, "json_output", False):
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"ERROR: ce pickup triage refused: {exc}", file=sys.stderr)
        return 2

    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        verb = "applied" if result.applied else "planned"
        print(
            f"ce pickup triage: {verb} {len(result.items)} pickup item(s); "
            f"poll with ce pickup poll {result.pickup_query_hint}"
        )
        for item in result.items:
            seat = f" -> {item.seat}" if item.seat else ""
            print(
                f"  - {item.issue.repo}#{item.issue.number}{seat} "
                f"({item.work_class}/{item.mutation_class})"
            )
        print(
            "  commissioned unscheduled advisory: "
            f"{len(result.commissioned_unscheduled)} item(s) "
            f"({result.commissioned_unscheduled_status})"
        )
        for item in result.commissioned_unscheduled:
            commissioned_by = ", ".join(item.commissioned_by) or "unknown"
            print(
                f"    - {item.issue.repo}#{item.issue.number} "
                f"(commissioned_by: {commissioned_by}; advisory_only: true)"
            )
    return 0


def _dispatch_plan(args) -> int:
    try:
        if args.issues_json == "-":
            issues_text = sys.stdin.read()
        else:
            issues_text = Path(args.issues_json).read_text(encoding="utf-8")
        issue_payloads = forge_triage.load_issue_payloads(issues_text)
        result = dispatch_plan.plan_dispatch(
            arc_ticket=args.arc_ticket,
            issues=issue_payloads,
            repo=args.repo,
            pickup_label=args.label,
            assign_to=getattr(args, "dispatch_seats", ()) or (),
        )
    except (OSError, forge_triage.ForgeTriageError) as exc:
        payload = {"ok": False, "error": str(exc)}
        if getattr(args, "json_output", False):
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"ERROR: ce pickup dispatch-plan refused: {exc}", file=sys.stderr)
        return 2

    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(
            f"ce pickup dispatch-plan: planned {len(result.items)} item(s); "
            f"pickup label {result.pickup_label}"
        )
        for item in result.items:
            seat = item.seat or "unassigned"
            print(
                f"  - {item.issue.repo}#{item.issue.number} -> {seat} "
                f"({item.work_class}/{item.mutation_class}) {item.suggested_branch}"
            )
    return 0


def _check(args) -> int:
    """Wrap the retained creator-engine-validator conformance checks."""
    from . import cli as validator_cli

    prefix: list[str] = []
    if getattr(args, "json_output", False):
        prefix.append("--json")
    if getattr(args, "tenant", None):
        prefix.extend(["--tenant", args.tenant])
    if getattr(args, "list_checks", False):
        return validator_cli.main([*prefix, "--list-checks"])
    paths = list(args.paths) if args.paths else ["."]
    profile: list[str] = []
    if getattr(args, "profile", None):
        profile.extend(["--profile", args.profile])
    return validator_cli.main([*prefix, "check", *profile, *paths])


def _init(args) -> int:
    if args.repo_root is not None and args.target is None:
        try:
            result = init_runtime.init_repo(args.repo_root)
        except init_runtime.InitRefused as exc:
            print(f"ERROR: ce init refused [{exc.code}]: {exc}", file=sys.stderr)
            return 1
        except init_runtime.InitError as exc:
            print(f"ERROR: ce init failed [{exc.code}]: {exc}", file=sys.stderr)
            return 1
        if getattr(args, "json_output", False):
            print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        else:
            print(
                f"ce init: {len(result.created)} dir(s) created, "
                f"{len(result.existing)} present -> {result.marker_path}"
            )
            print(journey_guidance.stage_map_text())
        return 0

    target = args.target or "."
    try:
        result = project_init.init_project(target, force=getattr(args, "force", False))
    except project_init.ProjectInitRefused as exc:
        print(f"ERROR: ce init refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    except project_init.ProjectInitError as exc:
        print(f"ERROR: ce init failed [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(
            f"ce init: {len(result.created)} created, "
            f"{len(result.skipped)} skipped, {len(result.overwritten)} overwritten "
            f"-> {result.target}"
        )
        for action in result.actions:
            print(f"  {action.status}: {action.path} ({action.reason})")
        print(journey_guidance.stage_map_text())
    return 0


def _harness_matrix(args) -> int:
    """Emit the PROBED harness-support capability matrix.

    Every cell is derived by inspecting the live adapter specs / committed config
    at runtime (never hand-asserted); each carries a provenance note. The antidote
    to the false 'contained gVisor' prose claim (ce-ops#221).
    """
    from . import harness_matrix as _hm

    matrix = _hm.build_matrix(repo_root=args.repo_root)
    if getattr(args, "json_output", False):
        print(_hm.render_json(matrix), end="")
    else:
        print(_hm.render_markdown(matrix), end="")
    return 0


def _posture(args) -> int:
    banner = controller_posture.collect_posture(
        repo_root=args.repo_root,
        environ=os.environ,
        role=getattr(args, "role", None),
        harness=getattr(args, "harness", None),
        launch_mode=getattr(args, "launch_mode", None),
    )
    if getattr(args, "json_output", False):
        print(controller_posture.render_json(banner), end="")
    else:
        print(controller_posture.render_text(banner), end="")
    return 0


def _print_launch_refusal(args, invoked_as: str, exc: launch_runtime.LaunchError) -> int:
    if getattr(args, "json_output", False) and hasattr(exc, "to_dict"):
        print(json.dumps(exc.to_dict(), indent=2, sort_keys=True))
        return 1
    print(f"ERROR: ce {invoked_as} refused [{exc.code}]: {exc}", file=sys.stderr)
    return 1


def _launch(args, invoked_as: str = "launch") -> int:
    harness_args = None
    if args.harness == "claude":
        harness_args = getattr(args, "claude_arg", None)
    elif args.harness == "codex":
        harness_args = getattr(args, "codex_arg", None)
    try:
        launch_runtime._validate_governed_controller_launch(  # type: ignore[attr-defined]
            role=getattr(args, "role", None),
            harness=args.harness,
            repo_root=getattr(args, "repo_root", None),
            session=args.session,
            takeover_evidence=getattr(args, "takeover_evidence", None),
        )
    except launch_runtime.LaunchError as exc:
        return _print_launch_refusal(args, invoked_as, exc)
    connection = onboard_connection_status.read_status(Path(args.repo_root) / ".ce" / "state")
    if connection.state == onboard_connection_status.UNRESOLVED_CONNECTION:
        print(
            "WARNING: ce launch: onboard forge connection is unresolved; "
            "launch remains available. " + connection.detail,
            file=sys.stderr,
        )
    if getattr(args, "preflight", False):
        report = launch_runtime.preflight_launch(
            harness=args.harness,
            session=args.session,
            window=args.window,
            invoked_as=invoked_as,
            resume=args.resume,
            visible=not args.no_tmux,
            extra_args=harness_args,
            mcp_config_path=getattr(args, "mcp_config", None),
            closeout_file=getattr(args, "closeout_file", None),
            completion_report_ref=getattr(args, "completion_report_ref", None),
            runtime_policy=getattr(args, "runtime_policy", None),
            backend=getattr(args, "backend", None),
            repo_root=getattr(args, "repo_root", None),
            tmux_adapter=_make_tmux_adapter(),
        )
        for line in report.format_lines():
            print(line)
        return report.exit_code

    brain_code = _preflight_launch_brain_bootstrap(args, invoked_as)
    if brain_code != 0:
        return brain_code
    # ce-ops#38: acquire + verify the work claim BEFORE any launch side effect.
    claim_code, claim_ctx = _acquire_launch_claim(args, invoked_as)
    if claim_code != 0:
        return claim_code
    try:
        result = launch_runtime.launch(
            harness=args.harness,
            session=args.session,
            window=args.window,
            invoked_as=invoked_as,
            resume=args.resume,
            dry_run=args.dry_run,
            visible=not args.no_tmux,
            role=getattr(args, "role", None),
            takeover_evidence=getattr(args, "takeover_evidence", None),
            extra_args=harness_args,
            mcp_config_path=getattr(args, "mcp_config", None),
            closeout_file=getattr(args, "closeout_file", None),
            completion_report_ref=getattr(args, "completion_report_ref", None),
            runtime_policy=getattr(args, "runtime_policy", None),
            backend=getattr(args, "backend", None),
            repo_root=getattr(args, "repo_root", None),
            ledger_root=getattr(args, "ledger_root", None),
            owner_controller_id=getattr(args, "controller_id", None),
            host_id=getattr(args, "host_id", None),
            purpose=_claim_purpose(args, claim_ctx),
            work_claim=_claim_binding(claim_ctx),
            tmux_adapter=_make_tmux_adapter(),
        )
    except launch_runtime.LaunchError as exc:
        _release_claim_context(claim_ctx, reason="launch-refused-before-side-effect")
        return _print_launch_refusal(args, invoked_as, exc)
    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        if result.plan.dry_run:
            print(
                f"ce {invoked_as} (dry-run): would {result.plan.mode} {result.plan.harness} "
                f"in tmux session={result.plan.session} window={result.plan.window} "
                f"(visibility={result.plan.visibility})"
            )
        elif result.attached:
            print(f"ce {invoked_as}: attached visible Controller seat in session={result.plan.session}")
        else:
            term = result.terminal or {}
            print(
                f"ce {invoked_as}: spawned visible Controller seat "
                f"(session={term.get('session_id')} window={term.get('window_id')} pane={term.get('pane_id')})"
            )
    return 0


def _takeover(args) -> int:
    try:
        plan = takeover_runtime.build_plan(
            predecessor=args.takeover_from,
            harness=args.harness,
            repo_root=args.repo_root,
            dry_run=args.dry_run,
            duty_manifest=getattr(args, "duty_manifest", None),
        )
    except takeover_runtime.TakeoverError as exc:
        if getattr(args, "json_output", False):
            print(
                json.dumps(
                    {
                        "kind": "ce-takeover-error",
                        "schema_version": "1",
                        "code": exc.code,
                        "message": str(exc),
                        "predecessor": args.takeover_from,
                        "repo_root": str(Path(args.repo_root).resolve()),
                        "dry_run": args.dry_run,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        print(f"ERROR: ce takeover refused [{exc.code}]: {exc}", file=sys.stderr)
        return 2
    if getattr(args, "json_output", False):
        print(takeover_runtime.render_json(plan), end="")
    else:
        for line in plan.format_lines():
            print(line)
    return 0 if plan.ring0_ok else 1


def _checkpoint(args) -> int:
    """Persist only caller-injected facts; this command has no controller authority."""
    try:
        result = checkpoint_runtime.create_checkpoint(
            repo_root=args.repo_root,
            facts_path=args.facts,
            prior_checkpoint=args.prior_checkpoint,
            clean_boundary=args.clean_boundary,
            as_of=args.as_of,
        )
    except checkpoint_runtime.CheckpointError as exc:
        if getattr(args, "json_output", False):
            print(json.dumps({"kind": "ce-checkpoint-result", "status": "refused", "message": str(exc)}, sort_keys=True))
        else:
            print(f"ERROR: ce checkpoint refused: {exc}", file=sys.stderr)
        return 2
    payload = result.to_dict()
    if getattr(args, "json_output", False):
        print(json.dumps(payload, sort_keys=True))
    else:
        state = "idempotent" if result.idempotent else "persisted"
        print(f"ce checkpoint: {state}; complete=green; path={result.path}; sha256={result.sha256}")
        print("/clear was not performed or claimed; only consider it after independently verifying this persisted-byte hash.")
    return 0


def _continuity_drill(args) -> int:
    try:
        prior_runs = tuple(
            continuity_drill_runtime.parse_prior_run(value)
            for value in getattr(args, "prior_run", ())
        )
        record = continuity_drill_runtime.build_record(
            predecessor=args.takeover_from,
            harness=args.harness,
            repo_root=args.repo_root,
            as_of=getattr(args, "as_of", None),
            prior_runs=prior_runs,
            promotion_candidate=getattr(args, "promotion_candidate", False),
            environ=os.environ,
        )
    except continuity_drill_runtime.ContinuityDrillError as exc:
        if getattr(args, "json_output", False):
            print(
                continuity_drill_runtime.render_abort_json(
                    predecessor=args.takeover_from,
                    harness=args.harness,
                    repo_root=args.repo_root,
                    error=exc,
                ),
                end="",
            )
        print(f"ERROR: ce continuity-drill refused [{exc.code}]: {exc}", file=sys.stderr)
        return 2
    except takeover_runtime.TakeoverError as exc:
        if getattr(args, "json_output", False):
            print(
                continuity_drill_runtime.render_abort_json(
                    predecessor=args.takeover_from,
                    harness=args.harness,
                    repo_root=args.repo_root,
                    error=exc,
                ),
                end="",
            )
        print(f"ERROR: ce continuity-drill refused [{exc.code}]: {exc}", file=sys.stderr)
        return 2
    if getattr(args, "json_output", False):
        print(continuity_drill_runtime.render_json(record), end="")
    else:
        for line in record.format_lines():
            print(line)
    return record.exit_code


def _doctor(args) -> int:
    target_python = _target_python_from_args(args, Path(args.repo_root))
    report = doctor_runtime.run_doctor(
        args.repo_root,
        require_visible_launch=args.require_visible_launch,
        require_worker=args.require_worker,
        check_packaging=not args.no_check_packaging,
        require_installed_ce=getattr(args, "require_installed_ce", False),
        target_python=target_python,
        check_seat_env=args.check_seat_env,
        argv0=sys.argv[0],
        harness=getattr(args, "harness", launch_runtime.DEFAULT_HARNESS),
    )
    if getattr(args, "json_output", False):
        print(json.dumps(report.payload, indent=2, sort_keys=True))
    else:
        print(doctor_runtime.render_human(report))
    return 0 if report.ok else 1


def _target_python_from_args(args, repo_root: Path) -> Path | None:
    explicit = getattr(args, "target_python", None)
    if explicit:
        return Path(explicit)
    venv = getattr(args, "venv", None)
    if venv:
        venv_path = Path(venv)
        if not venv_path.is_absolute():
            venv_path = repo_root / venv_path
        return venv_path / "bin" / "python"
    return None


def _bootstrap(args) -> int:
    target_python = _target_python_from_args(args, Path(args.repo_root))
    result = bootstrap_runtime.bootstrap(args.repo_root, target_python)
    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    elif result.ok:
        changed = "updated" if result.changed else "already provisioned"
        print(f"ce bootstrap: {changed} ({result.target_python})")
    else:
        print(
            f"ERROR: ce bootstrap refused [{result.reason}]: {result.detail}\n"
            f"remediation: {result.remediation}",
            file=sys.stderr,
        )
    return 0 if result.ok else 1


def _containment_probe(args) -> int:
    """ce-ops#221 Fix-1 — emit a live-runtime containment verdict for a pid.

    Exit 0 only when containment is positively proven; non-zero (fail-closed)
    otherwise. The verdict is never self-reported — it is read from /proc.
    """
    reader = containment_probe.ProcReader(root=args.proc_root)
    verdict = containment_probe.probe_containment(
        args.pid, reader=reader, host_pid=args.host_pid
    )
    herdr = containment_probe.probe_herdr_session(
        socket_path=getattr(args, "herdr_socket", None),
        pane_id=getattr(args, "herdr_pane_id", None),
        herdr_binary=getattr(args, "herdr_binary", "herdr"),
    )
    ring1 = containment_probe.probe_ring1_enforcement(
        args.pid,
        reader=reader,
        tool=getattr(args, "ring1_tool", "git"),
    )
    payload = containment_probe.attestation_payload(
        verdict,
        herdr_session=herdr,
        ring1_enforcement=ring1,
    )
    if getattr(args, "json_output", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(containment_probe.render_human(verdict))
    return 0 if verdict.contained else 1


def _make_publish_branch_runner():
    """Factory for host-side publish git runner (monkeypatchable in tests)."""
    return publish_gate.default_git_runner


def _publish_ledger_context(args) -> publish_gate.PublishLedgerContext | None:
    if getattr(args, "dry_run", False):
        return None
    required = (
        "controller_id",
        "lane_id",
        "claim_ref",
        "side_effect_ledger_root",
        "active_work_ledger_root",
    )
    missing = [name.replace("_", "-") for name in required if not getattr(args, name, None)]
    if missing:
        raise ValueError("live publish requires " + ", ".join(f"--{name}" for name in missing))
    return publish_gate.PublishLedgerContext(
        controller_id=args.controller_id,
        lane_id=args.lane_id,
        claim_ref=args.claim_ref,
        repo_root=args.repo_root,
        side_effect_ledger_root=args.side_effect_ledger_root,
        active_work_ledger_root=args.active_work_ledger_root,
        actor=args.actor,
        seat_id=args.seat_id,
    )


def _publish_branch(args) -> int:
    expected = publish_gate.SeatIdentityExpectation(
        author_name=args.expect_author_name,
        author_email=args.expect_author_email,
        committer_name=args.expect_committer_name,
        committer_email=args.expect_committer_email,
    )
    try:
        ledger_context = _publish_ledger_context(args)
    except ValueError as exc:
        payload = {
            "ok": False,
            "branch": args.branch,
            "refusal_reason": "missing_ledger_context",
            "evidence": [str(exc)],
        }
        if getattr(args, "json_output", False):
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"ERROR: ce publish-branch refused [missing_ledger_context]: {exc}", file=sys.stderr)
        return 1

    result = publish_gate.publish_branch(
        args.branch,
        repo=args.repo,
        repo_root=args.repo_root,
        expected_identity=expected,
        ledger_context=ledger_context,
        apply=not args.dry_run,
        runner=_make_publish_branch_runner(),
    )
    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    elif result.ok:
        action = "pushed" if result.pushed else ("verified" if args.dry_run else "already published")
        print(f"ce publish-branch: {action} {result.branch} at {result.local_head}")
    else:
        print(
            f"ERROR: ce publish-branch refused [{result.refusal_reason}]: "
            + "; ".join(result.evidence),
            file=sys.stderr,
        )
    return 0 if result.ok else 1


def _containment_status(args) -> int:
    status = containment_status.probe_fleet(
        seat_specs=getattr(args, "containment_seats", ()),
        registry_paths=getattr(args, "containment_registries", ()),
        proc_root=args.proc_root,
        host_pid=args.host_pid,
        herdr_socket=getattr(args, "herdr_socket", None),
        herdr_binary=getattr(args, "herdr_binary", "herdr"),
        ring1_tool=getattr(args, "ring1_tool", "git"),
    )
    if getattr(args, "json_output", False):
        print(containment_status.render_json(status))
    else:
        print(containment_status.render_table(status))
    return 0 if status.ok else 1


def _herdr_remote_attach(args) -> int:
    herdr_session = _herdr_session_module()
    try:
        plan = herdr_session.plan_remote_attach(
            remote_target=args.remote_target,
            session=args.session,
            pane_id=args.pane_id,
            surface_ref=getattr(args, "surface_ref", None),
            workspace_id=getattr(args, "workspace_id", None),
            herdr_binary=args.herdr_binary,
        )
    except herdr_session.HerdrCommandError as exc:
        print(f"ERROR: ce herdr remote-attach refused: {exc}", file=sys.stderr)
        return 1

    if getattr(args, "json_output", False):
        print(json.dumps(plan.to_dict(), indent=2, sort_keys=True))
    elif getattr(args, "dry_run", False):
        print("ce herdr remote-attach: " + shlex.join(plan.argv))
        print("auth_channel: authenticated herdr remote reach")
        print("reach_plane: herdr-remote")
        print("isolation_plane: runtime")
        print("requires_host_root: false")
        print("requires_runtime_attach: false")
        print(
            "contract: reach is authenticated herdr remote; isolation is runtime "
            "(runsc/docker/podman) and remains a separate decision"
        )

    if getattr(args, "json_output", False) or getattr(args, "dry_run", False):
        return 0

    try:
        herdr_session.remote_attach(
            remote_target=args.remote_target,
            session=args.session,
            pane_id=args.pane_id,
            surface_ref=getattr(args, "surface_ref", None),
            workspace_id=getattr(args, "workspace_id", None),
            herdr_binary=args.herdr_binary,
            runner=_make_herdr_attach_runner(),
        )
    except herdr_session.HerdrCommandError as exc:
        print(f"ERROR: ce herdr remote-attach failed: {exc}", file=sys.stderr)
        return 1
    return 0


def _automerge_decide(args) -> int:
    """ce automerge-decide — classify + dry-run decision (PR-A, ce-ops#291).

    Classify-ONLY: prints the AUTO/GESTURE decision and rationale.
    NEVER merges, NEVER mints a capability marker.  Inert by construction.
    """
    from .forge.automerge_policy import (
        AutoMergePolicyStateError,
        automerge_policy_state_path,
        decide_automerge,
        load_automerge_policy_state,
    )

    # Resolve changed paths.
    changed_paths: list[str] = list(getattr(args, "changed_paths", None) or [])
    paths_file = getattr(args, "paths_file", None)
    if paths_file:
        try:
            extra = Path(paths_file).read_text(encoding="utf-8").splitlines()
            changed_paths.extend(p.strip() for p in extra if p.strip())
        except OSError as exc:
            print(f"ERROR: ce automerge-decide: cannot read --paths-file: {exc}", file=sys.stderr)
            return 1

    # Resolve policy state path.
    repo_root = Path(getattr(args, "repo_root", "."))
    policy_state_path_arg = getattr(args, "policy_state_path", None)
    if policy_state_path_arg:
        policy_path = Path(policy_state_path_arg)
    else:
        policy_path = automerge_policy_state_path(repo_root / ".ce/state")

    try:
        policy_state = load_automerge_policy_state(policy_path)
    except AutoMergePolicyStateError as exc:
        print(f"ERROR: ce automerge-decide: policy state unreadable: {exc}", file=sys.stderr)
        print("(falling back to shipped default: dev mode, all flags false)", file=sys.stderr)
        policy_state = None  # decide_automerge handles None → shipped default

    # Parse optional checks JSON.
    checks = None
    checks_json_str = getattr(args, "checks_json", None)
    if checks_json_str:
        try:
            if checks_json_str.startswith("@"):
                checks_path = checks_json_str[1:]
                if not checks_path:
                    raise ValueError("checks-json @file path is empty")
                checks_json_str = Path(checks_path).read_text(encoding="utf-8")
            checks = json.loads(checks_json_str)
            if not isinstance(checks, dict):
                raise ValueError("checks-json must be a JSON object")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"ERROR: ce automerge-decide: --checks-json invalid: {exc}", file=sys.stderr)
            return 1

    review_decision = getattr(args, "review_decision", None) or None

    decision = decide_automerge(
        changed_paths=changed_paths,
        declared_work_class=getattr(args, "declared_work_class", "S"),
        policy_state=policy_state,
        checks=checks,
        review_decision=review_decision,
        pr_number=getattr(args, "pr_number", None),
        head_sha=getattr(args, "head_sha", None),
        repo=getattr(args, "repo", None),
        branch=getattr(args, "branch", None),
        base=getattr(args, "base", None),
        run_mode=getattr(args, "run_mode", None),
        author_login=getattr(args, "author_login", None),
        approver_login=getattr(args, "approver_login", None),
        repo_root=repo_root,
    )

    if getattr(args, "json_output", False):
        print(json.dumps(decision.to_dict(), indent=2, sort_keys=True))
    else:
        print(f"ce automerge-decide: {decision.decision}")
        print(f"  mutation_class  : {decision.mutation_class}")
        print(f"  size_band       : {decision.size_band}")
        print(f"  run_mode        : {decision.run_mode}")
        print(f"  kill_switch     : {decision.kill_switch}")
        print(f"  class_flag      : {decision.class_flag}")
        print(f"  checks_green    : {decision.checks_green}")
        print(f"  review_blocked  : {decision.review_decision_blocked}")
        print(f"  ratification    : {decision.ratification_gates}")
        print("  rationale:")
        for line in decision.rationale:
            print(f"    - {line}")
    return 0


def _automerge_status(args) -> int:
    """ce automerge-status — read dry-run decision logs without side effects."""

    from .forge.automerge_policy import (
        AUTOMERGE_ARMING_RUN_MODES,
        AutoMergePolicyStateError,
        automerge_policy_state_path,
        load_automerge_policy_state,
        load_decision_records,
    )

    repo_root = Path(getattr(args, "repo_root", "."))
    state_dir_arg = getattr(args, "state_dir", None)
    state_dir = Path(state_dir_arg) if state_dir_arg else repo_root / ".ce/state"
    policy_path = automerge_policy_state_path(state_dir)

    try:
        records = load_decision_records(state_dir)
    except AutoMergePolicyStateError as exc:
        print(f"ERROR: ce automerge-status: decision records unreadable: {exc}", file=sys.stderr)
        return 1
    try:
        policy_state = load_automerge_policy_state(policy_path)
    except AutoMergePolicyStateError as exc:
        print(f"ERROR: ce automerge-status: policy state unreadable: {exc}", file=sys.stderr)
        return 1

    arming_state = (
        f"ARMED(run_mode={policy_state.run_mode})"
        if policy_state.run_mode in AUTOMERGE_ARMING_RUN_MODES and not policy_state.kill_switch
        else "DISARMED"
    )
    policy_payload = {
        "path": str(policy_path),
        "arming_state": arming_state,
        "run_mode": policy_state.run_mode,
        "enabling_ref": policy_state.enabling_decision_ref,
        "kill_switch": policy_state.kill_switch,
    }

    if getattr(args, "json_output", False):
        print(
            json.dumps(
                {"state_dir": str(state_dir), "policy": policy_payload, "records": records},
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    print(f"ce automerge-status: {len(records)} decision record(s)")
    print(f"  arming state   : {arming_state}")
    print(f"  enabling_ref   : {_automerge_status_value(policy_state.enabling_decision_ref)}")
    print(f"  kill_switch    : {policy_state.kill_switch}")
    for record in records:
        decision = _automerge_status_decision(record.get("decision"))
        pr_number = record.get("pr_number")
        pr_label = f"#{pr_number}" if pr_number is not None else "(unknown PR)"
        print(f"PR {pr_label}: {decision}")
        print(f"  head_sha       : {_automerge_status_value(record.get('head_sha'))}")
        print(f"  rationale      : {_automerge_status_value(record.get('rationale'))}")
        print(f"  gates          : {_automerge_status_value(record.get('gate_results', record.get('gates')))}")
        print(f"  checks_green   : {_automerge_status_value(record.get('checks_green'))}")
        print(f"  reviewDecision : {_automerge_status_value(record.get('reviewDecision'))}")
        print(f"  run_mode       : {_automerge_status_value(record.get('run_mode'))}")
        print(f"  class_flag     : {_automerge_status_value(record.get('class_flag'))}")
        print(f"  timestamps     : {_automerge_status_timestamps(record)}")
    return 0


def _press_merge_evidence(args) -> int:
    """ce press-merge-evidence — canonical renderer; no PR or repo mutation."""

    from .forge.press_merge_evidence import (
        assemble_press_merge_evidence_from_files,
        canonical_json_bytes,
    )

    try:
        bundle = assemble_press_merge_evidence_from_files(
            decision_file=args.decision_file,
            paths_file=args.paths_file,
            checks_json_file=getattr(args, "checks_json_file", None),
            pr_json_file=getattr(args, "pr_json_file", None),
            approval_witnesses_json_file=getattr(args, "approval_witnesses_json_file", None),
            current_head_sha_observed=getattr(args, "current_head_sha", None),
            repo_root=getattr(args, "repo_root", "."),
            minted_at_utc=getattr(args, "minted_at_utc", None),
            assembler_workflow=getattr(args, "assembler_workflow", None),
            assembler_run_id=getattr(args, "assembler_run_id", None),
            assembler_run_attempt=getattr(args, "assembler_run_attempt", None),
            read_repo_sha=getattr(args, "read_repo_sha", None),
            decision_artifact_name=getattr(args, "decision_artifact_name", None),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: ce press-merge-evidence: {exc}", file=sys.stderr)
        return 1

    sys.stdout.buffer.write(canonical_json_bytes(bundle))
    return 0


def _press_merge_evidence_from_argv(argv: Sequence[str]) -> int:
    """Hidden renderer entry: available to workflow, absent from public parser inventory."""

    parser = argparse.ArgumentParser(
        prog="ce press-merge-evidence",
        description="Render a canonical read-only press-merge evidence bundle.",
    )
    parser.add_argument("--decision-file", required=True)
    parser.add_argument("--paths-file", required=True)
    parser.add_argument("--checks-json-file", default=None)
    parser.add_argument("--pr-json-file", default=None)
    parser.add_argument("--approval-witnesses-json-file", default=None)
    parser.add_argument("--current-head-sha", default=None)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--minted-at-utc", default=None)
    parser.add_argument("--assembler-workflow", default=None)
    parser.add_argument("--assembler-run-id", default=None)
    parser.add_argument("--assembler-run-attempt", default=None)
    parser.add_argument("--read-repo-sha", default=None)
    parser.add_argument("--decision-artifact-name", default=None)
    return _press_merge_evidence(parser.parse_args(argv))


def _automerge_kill_switch(args) -> int:
    """ce automerge-kill-switch — read or toggle durable live-policy state."""

    from .forge.automerge_policy import (
        AutoMergePolicyStateError,
        automerge_policy_state_path,
        load_automerge_policy_state,
        update_automerge_policy_kill_switch,
    )

    repo_root = Path(getattr(args, "repo_root", "."))
    policy_state_path_arg = getattr(args, "policy_state_path", None)
    policy_path = (
        Path(policy_state_path_arg)
        if policy_state_path_arg
        else automerge_policy_state_path(repo_root / ".ce/state")
    )
    action = getattr(args, "action")

    try:
        if action == "status":
            policy_state = load_automerge_policy_state(policy_path)
        elif action == "on":
            policy_state = update_automerge_policy_kill_switch(policy_path, active=True)
        elif action == "off":
            policy_state = update_automerge_policy_kill_switch(policy_path, active=False)
        else:
            print("ERROR: ce automerge-kill-switch: unknown action", file=sys.stderr)
            return 2
    except AutoMergePolicyStateError as exc:
        print(f"ERROR: ce automerge-kill-switch {action}: policy state error: {exc}", file=sys.stderr)
        if action == "on":
            print(
                "Manual fallback: set CE_AUTOMERGE_KILL_SWITCH=true in the GitHub Actions environment.",
                file=sys.stderr,
            )
        return 1

    payload = {
        "path": str(policy_path),
        "kill_switch": policy_state.kill_switch,
        "run_mode": policy_state.run_mode,
        "enabling_ref": policy_state.enabling_decision_ref,
    }

    if getattr(args, "json_output", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    state_label = "ON" if policy_state.kill_switch else "OFF"
    effect_label = "DISARMED" if policy_state.kill_switch else "READY"
    print(f"ce automerge-kill-switch: {state_label}")
    print(f"  live_policy    : {effect_label}")
    print(f"  policy_state   : {policy_path}")
    print(f"  run_mode       : {policy_state.run_mode}")
    print(f"  enabling_ref   : {_automerge_status_value(policy_state.enabling_decision_ref)}")
    return 0


def _automerge_status_decision(value) -> str:
    decision = str(value) if value is not None else "UNKNOWN"
    if decision == "GESTURE":
        return "MANUAL"
    return decision


def _automerge_status_value(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value) if value else "-"
    if isinstance(value, dict):
        if not value:
            return "-"
        return ", ".join(f"{key}={value[key]}" for key in sorted(value))
    return str(value)


def _automerge_status_timestamps(record) -> str:
    keys = (
        "timestamp",
        "created_at",
        "createdAt",
        "decided_at",
        "decidedAt",
        "emitted_at",
        "emittedAt",
        "updated_at",
        "updatedAt",
    )
    values = [f"{key}={record[key]}" for key in keys if record.get(key) is not None]
    return ", ".join(values) if values else "-"


def _make_gh_runner():
    """Factory for the work-claim gh runner (monkeypatchable in tests)."""
    return work_claims.default_gh_runner


def _claim_acquire(args) -> int:
    try:
        key = work_claims.parse_ticket(args.ticket, getattr(args, "repo", None))
        result = work_claims.acquire(
            key, _make_gh_runner(),
            reason=args.reason, holder=args.holder, host=args.host,
            stale_after_seconds=args.stale_after_seconds,
            takeover=args.takeover, takeover_reason=args.takeover_reason,
        )
    except work_claims.WorkClaimError as exc:
        return _emit_claim(args, 2, f"ce claim acquire refused (input): {exc}", None)
    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    elif result.ok:
        print(f"ce claim acquire: OK ({result.note}) — claim {result.claim_id} on {result.work_key}")
    else:
        print(f"ERROR: ce claim acquire refused [{result.refusal_reason}]: {result.note}", file=sys.stderr)
    return 0 if result.ok else 1


def _claim_release(args) -> int:
    try:
        key = work_claims.parse_ticket(args.ticket, getattr(args, "repo", None))
        result = work_claims.release(
            key, _make_gh_runner(),
            claim_id=args.claim_id, reason=args.reason,
            deliverable_url=args.deliverable_url,
        )
    except work_claims.WorkClaimError as exc:
        return _emit_claim(args, 2, f"ce claim release refused (input): {exc}", None)
    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    elif result.ok:
        print(f"ce claim release: OK — released {result.claim_id} on {result.work_key}")
    else:
        print(f"ERROR: ce claim release refused [{result.refusal_reason}]: {result.note}", file=sys.stderr)
    return 0 if result.ok else 1


def _claim_status(args) -> int:
    try:
        key = work_claims.parse_ticket(args.ticket, getattr(args, "repo", None))
        result = work_claims.status(key, _make_gh_runner())
    except work_claims.WorkClaimError as exc:
        return _emit_claim(args, 2, f"ce claim status refused (input): {exc}", None)
    if getattr(args, "write_cache", None):
        cache = work_claims.build_cache(result, key.repo_slug, work_claims.utc_now_iso())
        work_claims.write_cache(args.write_cache, cache)
    if getattr(args, "json_output", False):
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        active = result.state.active
        if active is None:
            print(f"ce claim status: {result.work_key} — UNCLAIMED ({len(result.state.comment_ids)} comments seen)")
        else:
            flag = " [STALE]" if active.stale else ""
            print(
                f"ce claim status: {result.work_key} — held by {active.holder}@{active.host} "
                f"(claim {active.claim_id}, {active.kind}){flag}"
            )
        if result.state.invalid_count:
            print(f"  ⚠ {result.state.invalid_count} invalid_marker comment(s)", file=sys.stderr)
    # status itself never refuses on a foreign claim — it reports. Exit 1 only if
    # an invalid marker pollutes the view (the operator must repair it).
    return 1 if result.state.invalid_count else 0


def _claim_lifecycle_module():
    return importlib.import_module("creator_engine_validator.claim_lifecycle")


def _claim_transition(args) -> int:
    claim_lifecycle = _claim_lifecycle_module()
    try:
        result = claim_lifecycle.transition_claim(
            args.repo_root,
            args.slug,
            args.new_state,
            pr=args.pr,
            sha=args.sha,
            force=args.force,
        )
    except claim_lifecycle.ClaimLifecycleError as exc:
        return _emit_claim(args, 2, f"ce claim transition refused: {exc}", None)
    if getattr(args, "json_output", False):
        print(json.dumps(result.log_payload(), indent=2, sort_keys=True))
    else:
        print(claim_lifecycle.structured_log_line(result))
    return 0


def _claim_list(args) -> int:
    claim_lifecycle = _claim_lifecycle_module()
    try:
        rows = claim_lifecycle.list_claims(args.repo_root, state=args.state, seat=args.seat)
    except claim_lifecycle.ClaimLifecycleError as exc:
        return _emit_claim(args, 2, f"ce claim list refused: {exc}", None)
    if getattr(args, "json_output", False):
        print(json.dumps(rows, indent=2, sort_keys=True))
    else:
        print(claim_lifecycle.format_table(rows), end="")
    return 0


def _make_pickup_transport():
    """Factory for the pickup Search API HTTPS transport (monkeypatchable in tests)."""
    from . import pickup as _pickup
    return _pickup._default_transport


def _make_pickup_gh_runner(identity: str, token: str | None = None):
    """Factory for the per-identity pickup gh runner (monkeypatchable in tests).

    Resolves the seat's own PAT (the #137 identity model) and returns a runner
    that injects it into the child ``gh`` env — never ambient/overwatch auth.
    """
    from . import pickup as _pickup
    resolved = token if token is not None else _pickup.resolve_token(identity=identity)
    return _pickup.make_gh_runner(resolved)


def _make_pickup_lane_spawn():
    """Factory for the pickup→lane spawn seam (monkeypatchable in tests).

    The lane is launched as a SUBPROCESS (`ce lane launch`) — the v1→v1 cross to
    the launcher that keeps ALL tmux coupling behind the lane primitive.
    """
    from . import pickup as _pickup
    return _pickup._default_spawn


def _pickup_poll(args) -> int:
    from . import pickup

    try:
        pickup.build_queries(
            labels=getattr(args, "pickup_labels", ()) or (),
            repo=getattr(args, "repo", None),
            org=getattr(args, "org", None),
        )
    except pickup.PickupError as exc:
        return _emit_pickup(args, 2, f"ce pickup poll refused (input): {exc}", None)

    heartbeat_path = Path(os.environ.get(
        "CE_BELT_HEARTBEAT_PATH",
        Path.home() / ".local" / "state" / "creator-engine" / "daemon-heartbeats" / "belt.json",
    ))
    heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
    heartbeat = DaemonHeartbeatEmitter(
        heartbeat_path,
        daemon_id="belt",
        expected_interval_seconds=float(os.environ.get("CE_BELT_INTERVAL_SECONDS", "120")),
        unit="ce-belt-daemon.service",
        scope="user",
    )
    start_index = max(heartbeat.last_pass_index, 0)
    heartbeat.emit("starting", start_index)
    pass_index = heartbeat.last_pass_index + 1

    try:
        token = pickup.resolve_token(
            keys_dir=args.keys_dir,
            identity=args.identity,
            allow_ambient_gh=getattr(args, "allow_ambient_gh", False),
        )
    except pickup.PickupError as exc:
        heartbeat.emit("failed", heartbeat.last_pass_index)
        return _emit_pickup(args, 2, f"ce pickup poll refused (input): {exc}", None)

    try:
        heartbeat.emit("running", pass_index)
        result = pickup.poll(
            token=token,
            transport=_make_pickup_transport(),
            labels=getattr(args, "pickup_labels", ()) or (),
            repo=getattr(args, "repo", None),
            org=getattr(args, "org", None),
        )
    except KeyboardInterrupt:  # pragma: no cover - operator stop for loop mode
        heartbeat.emit("stopping", heartbeat.last_pass_index)
        raise
    except pickup.PickupRateLimited as exc:
        heartbeat.emit("failed", heartbeat.last_pass_index)
        return _emit_pickup(
            args,
            2,
            f"ce pickup poll failed closed: {exc}",
            {"backoff": exc.to_payload()},
        )
    except pickup.PickupError as exc:
        heartbeat.emit("failed", heartbeat.last_pass_index)
        return _emit_pickup(args, 2, f"ce pickup poll failed: {exc}", None)

    # S1 observe-only is the default. When --claim is set the poller forge-arbitrates
    # a claim per actionable item (S2) and, only when --enable-launch is ALSO set,
    # spawns a fresh governed lane (S3, canary OFF by default).
    if getattr(args, "pickup_claim", False):
        code = _pickup_claim_and_launch(args, pickup, result, token)
        heartbeat.emit("pass_complete" if code == 0 else "failed", heartbeat.last_pass_index)
        return code

    payload = {
        "ok": True,
        "not_modified": result.not_modified,
        "last_modified": result.last_modified,
        "poll_interval": result.poll_interval,
        "rate_limit": result.rate_limit,
        "items": list(result.items),
        "count": len(result.items),
    }
    if getattr(args, "json_output", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"ce pickup poll: {len(result.items)} actionable item(s) "
              f"(next poll >= {result.poll_interval}s)")
        for item in result.items:
            print(f"  - [{item['kind']}] {item['repo']}#{item['number']} ({item['reason']}) {item['url']}")
    heartbeat.emit("pass_complete", pass_index)
    return 0


def _pickup_claim_and_launch(args, pickup, result, token: str) -> int:
    """S2/S3: forge-arbitrate a claim per actionable item, then (S3, gated) launch a lane.

    S2 wires the claim + dedup ledger (dry-run: a successful claim prints "would
    launch" but does NOT spawn a lane). S3 wires the gated `ce lane launch` behind
    ``--enable-launch`` (a per-seat canary, default OFF). See ``pickup.py``.
    """
    import os as _os

    from . import pickup as _pickup

    ledger_root = args.pickup_ledger_root or _os.path.join(V3_LOCAL_STATE_ROOT, "pickup")
    ledger_path = _os.path.join(ledger_root, _pickup.DEFAULT_LEDGER_NAME)
    run_id = args.pickup_run_id or f"pickup-{args.identity}-{result.last_modified or 'init'}"
    try:
        gh_runner = _make_pickup_gh_runner(args.identity, token)
    except TypeError:
        # Compatibility for tests or callers that monkeypatch the factory with
        # the older one-argument shape.
        gh_runner = _make_pickup_gh_runner(args.identity)

    repo_fence = getattr(args, "repo", None)
    enable_launch = bool(getattr(args, "enable_launch", False))

    claims: list[dict] = []
    for item in result.items:
        if repo_fence and item["repo"] != repo_fence:
            claims.append({**item, "claimed": False, "reason": "out_of_repo_fence",
                           "would_launch": False, "launched": False})
            continue
        outcome = _pickup.claim_item(
            item, identity=args.identity, gh_runner=gh_runner,
            ledger_path=ledger_path, run_id=run_id,
            backoff_seconds=getattr(args, "backoff_seconds", 1.0),
        )
        record = {
            "repo": item["repo"], "kind": item["kind"], "number": item["number"],
            "url": item["url"], "thread_id": item["thread_id"],
            "claimed": outcome.claimed, "reason": outcome.reason,
            "claim_id": outcome.claim_id,
            "would_launch": outcome.claimed and not enable_launch,
            "launched": False,
            "seed_path": None,
        }
        if outcome.claimed and enable_launch:
            record = _pickup_launch_for_outcome(args, _pickup, outcome, gh_runner, record)
        claims.append(record)

    payload = {
        "ok": True,
        "not_modified": result.not_modified,
        "last_modified": result.last_modified,
        "poll_interval": result.poll_interval,
        "rate_limit": result.rate_limit,
        "enable_launch": enable_launch,
        "claims": claims,
        "claimed_count": sum(1 for c in claims if c["claimed"]),
        "count": len(claims),
    }
    if getattr(args, "json_output", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"ce pickup poll: {payload['claimed_count']}/{len(claims)} item(s) claimed "
              f"(launch {'ON' if enable_launch else 'OFF — dry-run'})")
        for c in claims:
            if c["claimed"] and c["would_launch"]:
                print(f"  + would launch lane for [{c['kind']}] {c['repo']}#{c['number']} {c['url']}")
            elif c["claimed"] and c["launched"]:
                print(f"  ✓ launched lane for [{c['kind']}] {c['repo']}#{c['number']} (seed {c['seed_path']})")
            else:
                print(f"  - skipped [{c['kind']}] {c['repo']}#{c['number']} ({c['reason']})")
    return 0


def _pickup_launch_for_outcome(args, pickup, outcome, gh_runner, record) -> dict:
    """S3: write a seed file + spawn a governed lane for a successfully-claimed item.

    Gated behind --enable-launch (the per-seat canary, default OFF). Search API
    items have synthetic thread ids and no read marker, so idempotency remains
    the claim/dedup ledger. Legacy notification ids are marked read only after
    the lane confirms the `launched` sentinel.
    """
    import os as _os

    item = outcome.item
    repo_root = getattr(args, "pickup_repo_root", ".")
    lane_ledger_root = getattr(args, "lane_ledger_root", None) or _os.path.join(
        repo_root, ".ce", "state", "active-work-ledger"
    )
    seed_root = getattr(args, "seed_root", None) or _os.path.join(
        args.pickup_ledger_root or _os.path.join(V3_LOCAL_STATE_ROOT, "pickup"),
        "seeds",
    )
    run_id = args.pickup_run_id or f"pickup-{args.identity}"

    launch = pickup.launch_lane(
        item, identity=args.identity, run_id=run_id, claim_id=outcome.claim_id,
        harness=args.harness, seed_root=seed_root, repo_root=repo_root,
        ledger_root=lane_ledger_root, spawn=_make_pickup_lane_spawn(),
    )
    record["launched"] = launch.launched
    record["would_launch"] = False
    record["seed_path"] = launch.seed_path
    if launch.launched:
        record["thread_marked_read"] = pickup.mark_thread_read(item["thread_id"], gh_runner=gh_runner)
    else:
        record["note"] = launch.note
        record["thread_marked_read"] = False
    return record


def _emit_pickup(args, code: int, message: str, payload) -> int:
    if getattr(args, "json_output", False):
        print(json.dumps({"ok": code == 0, "error": message, **(payload or {})}, indent=2, sort_keys=True))
    else:
        print(f"ERROR: {message}", file=sys.stderr)
    return code


def _emit_claim(args, code: int, message: str, payload) -> int:
    if getattr(args, "json_output", False):
        print(json.dumps({"ok": code == 0, "error": message, **(payload or {})}, indent=2, sort_keys=True))
    else:
        print(f"ERROR: {message}", file=sys.stderr)
    return code


def _claim_binding(claim_ctx: object) -> seat_lifecycle.WorkClaimBinding | None:
    if not isinstance(claim_ctx, dict):
        return None
    binding = claim_ctx.get("binding")
    return binding if isinstance(binding, seat_lifecycle.WorkClaimBinding) else None


def _claim_purpose(args, claim_ctx: object) -> str | None:
    purpose = getattr(args, "purpose", None)
    if purpose:
        return purpose
    if isinstance(claim_ctx, dict):
        ticket = claim_ctx.get("ticket")
        if ticket:
            return str(ticket)
    return getattr(args, "claim_ticket", None)


def _release_claim_context(claim_ctx: object, *, reason: str) -> None:
    if not isinstance(claim_ctx, dict):
        return
    key = claim_ctx.get("key")
    runner = claim_ctx.get("runner")
    claim_id = claim_ctx.get("claim_id")
    holder = claim_ctx.get("holder")
    host = claim_ctx.get("host")
    if key is None or runner is None or not claim_id:
        return
    work_claims.best_effort_release(
        key,
        runner,
        str(claim_id),
        holder=str(holder or work_claims.resolve_holder()),
        host=str(host or work_claims.resolve_host()),
        reason=reason,
    )


def _preflight_launch_brain_bootstrap(args, invoked_as: str) -> int:
    if not getattr(args, "claim_ticket", None):
        return 0
    try:
        if invoked_as == "lane launch":
            state_root = Path(getattr(args, "repo_root", ".")) / V3_LOCAL_STATE_ROOT
            lane_runtime._build_lane_brain_bootstrap(  # type: ignore[attr-defined]
                state_root=state_root,
                role=getattr(args, "role", ""),
            )
        else:
            launch_runtime._build_controller_brain_bootstrap(  # type: ignore[attr-defined]
                getattr(args, "repo_root", None)
            )
    except lane_runtime.LaneLaunchError as exc:
        print(f"ERROR: ce {invoked_as} refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    except launch_runtime.LaunchError as exc:
        print(f"ERROR: ce {invoked_as} refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    return 0


def _acquire_launch_claim(args, invoked_as: str) -> tuple[int, object]:
    """Acquire + verify the v1 launch work claim (ce-ops#38), refuse-before-side-effect.

    Returns ``(exit_code, None)`` on refusal/bad-input (the caller returns it) or
    ``(0, claim_context)`` when the claim is held — ``claim_context`` is the
    context the caller uses to best-effort-release if the subsequent launch leg
    refuses, and to bind the work claim into the seat lifecycle record.
    ``(0, None)`` means no ``--claim-ticket``.
    """
    ticket = getattr(args, "claim_ticket", None)
    if not ticket:
        return 0, None
    try:
        key = work_claims.parse_ticket(ticket)
        runner = _make_gh_runner()
        holder = work_claims.resolve_holder()
        host = work_claims.resolve_host()
        result = work_claims.acquire(key, runner, reason="manual", holder=holder, host=host)
    except work_claims.WorkClaimError as exc:
        print(f"ERROR: ce {invoked_as} refused: --claim-ticket {exc}", file=sys.stderr)
        return 2, None
    if not result.ok:
        print(
            f"ERROR: ce {invoked_as} refused [claim:{result.refusal_reason}]: {result.note}",
            file=sys.stderr,
        )
        return 1, None
    binding = seat_lifecycle.WorkClaimBinding(
        work_key=key.work_key,
        claim_id=str(result.claim_id),
        claim_comment_url=result.posted_url,
        holder=holder,
        host=host,
        stale_after_seconds=work_claims.DEFAULT_STALE_AFTER_SECONDS,
    )
    return 0, {
        "key": key,
        "runner": runner,
        "claim_id": result.claim_id,
        "holder": holder,
        "host": host,
        "binding": binding,
        "ticket": f"{key.repo_slug}#{key.number}",
    }


def _verify_install(args) -> int:
    result = ce_provenance.verify_install(
        args.install_root,
        offline=args.offline,
    )
    payload = result.to_json()
    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif result.ok:
        mode = payload.get("sha256s", {}).get("status", "unknown")
        print(f"ce verify-install: PASS ({mode})")
        print(f"install_root: {payload['install_root']}")
    else:
        print(f"ERROR: ce verify-install refused: {result.reason}", file=sys.stderr)
        for problem in result.problems:
            print(f"  ERROR: {problem}", file=sys.stderr)
    return 0 if result.ok else 1


_LANE_DISPATCH = {
    "launch": _lane_launch,
    "status": _lane_status,
    "verify": _lane_verify,
    "archive": _lane_archive,
}

_LEDGER_DISPATCH = {
    "record": _ledger_record,
    "verify": _ledger_verify,
}

_WORKER_DISPATCH = {
    "run": _worker_run,
    "spawn": _worker_spawn,
    "scrub-env": _worker_scrub_env,
    "allocate": _worker_allocate,
    "terminate": _worker_terminate,
    "gc": _worker_gc,
    "status": _worker_status,
    "worktree-prune": _worker_worktree_prune,
}

_FANIN_DISPATCH = {
    "build": _fanin_build,
    "inspect": _fanin_inspect,
}

_QUEUE_DISPATCH = {
    "dry-run": _queue_dry_run,
    "inspect": _queue_inspect,
}

_EVENT_DISPATCH = {
    "append": _event_append,
    "verify": _event_verify,
    "sign": _event_sign,
    "replay": _event_replay,
    "index": _event_index,
}

_PCL_DISPATCH = {
    "append": _pcl_append,
    "verify": _pcl_verify,
    "replay": _pcl_replay,
    "index": _pcl_index,
    "merge": _pcl_merge,
}

_BRAIN_DISPATCH = {
    "assert": _brain_assert,
    "bootstrap": _brain_bootstrap,
    "check": _brain_check,
    "correct": _brain_correct,
    "eval": _brain_eval,
    "hydrate": _brain_hydrate,
    "init": _brain_init,
    "ingest": _brain_ingest,
    "recall": _brain_recall,
    "reconcile": _brain_reconcile,
    "probe": _brain_probe,
    "sync": _brain_sync,
    "verify": _brain_verify,
}

_ORCHESTRATOR_DISPATCH = {
    "status": _orchestrator_status,
}

_CONNECTOR_DISPATCH = {
    "verify": _connector_verify,
    "plan": _connector_plan,
    "fetch": _connector_fetch,
    "write-plan": _connector_write_plan,
    "submit": _connector_submit,
}

_REVIEWER_TRIAGE_DISPATCH = {
    "plan": _reviewer_triage_plan,
}

_CLAIM_DISPATCH = {
    "acquire": _claim_acquire,
    "list": _claim_list,
    "release": _claim_release,
    "status": _claim_status,
    "transition": _claim_transition,
}

_PICKUP_DISPATCH = {
    "dispatch-plan": _dispatch_plan,
    "poll": _pickup_poll,
    "triage": _pickup_triage,
}

_TRIAGE_QUEUE_DISPATCH = {
    "scan": _triage_queue_scan,
    "inspect": _triage_queue_inspect,
}

_DEPENDENCY_UNLOCK_DISPATCH = {
    "scan": _dependency_unlock_scan,
}

_HERDR_DISPATCH = {
    "remote-attach": _herdr_remote_attach,
}

_STALE_WHEEL_OVERRIDE_ENV = "CE_ALLOW_STALE_WHEEL"
_STALE_WHEEL_PACKAGE = "creator-engine-validator"
_STALE_WHEEL_GATE_COMMANDS = {
    ("validate-pr", None),
    ("brain", "correct"),
    ("brain", "sync"),
    ("brain", "verify"),
}


def _version_core(value: str) -> tuple[int, int, int] | None:
    match = re.match(r"^\s*(\d+)\.(\d+)\.(\d+)", value)
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def _is_newer_version(left: str, right: str) -> bool:
    left_core = _version_core(left)
    right_core = _version_core(right)
    if left_core is None or right_core is None:
        return False
    return left_core > right_core


def _read_source_declared_version(repo_root: Path) -> str | None:
    pyproject = repo_root / "validators" / "pyproject.toml"
    if pyproject.is_file():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            return None
        project = data.get("project", {})
        declared = project.get("version")
        if isinstance(declared, str) and declared:
            return declared

    version_py = repo_root / "validators" / "creator_engine_validator" / "version.py"
    if version_py.is_file():
        try:
            match = re.search(
                r'^__version__\s*=\s*"([^"]+)"',
                version_py.read_text(encoding="utf-8"),
                re.MULTILINE,
            )
        except OSError:
            return None
        if match:
            return match.group(1)
    return None


def _running_package_version() -> str:
    try:
        return importlib_metadata.version(_STALE_WHEEL_PACKAGE)
    except importlib_metadata.PackageNotFoundError:
        return version.__version__


def _find_creator_engine_checkout(start: str | Path | None) -> Path | None:
    if start is None:
        return None
    try:
        path = Path(start).expanduser().resolve()
    except OSError:
        return None
    if path.is_file():
        path = path.parent
    for candidate in (path, *path.parents):
        if (
            (candidate / "validators" / "pyproject.toml").is_file()
            and (candidate / "validators" / "creator_engine_validator" / "ce_cli.py").is_file()
        ):
            return candidate
    return None


def _running_from_checkout(repo_root: Path) -> bool:
    try:
        module_file = Path(__file__).resolve()
    except OSError:
        return False
    source_root = repo_root / "validators" / "creator_engine_validator"
    try:
        module_file.relative_to(source_root.resolve())
    except ValueError:
        return False
    return True


def _command_label(args) -> str:
    if args.group == "brain":
        brain_cmd = getattr(args, "brain_cmd", None)
        return f"brain {brain_cmd}" if brain_cmd else "brain"
    return str(args.group)


def _skew_candidate_roots(args) -> tuple[Path, ...]:
    roots: list[Path] = []
    for raw in (getattr(args, "repo_root", None), Path.cwd()):
        checkout = _find_creator_engine_checkout(raw)
        if checkout is not None and checkout not in roots:
            roots.append(checkout)
    return tuple(roots)


def _maybe_guard_stale_wheel_skew(args) -> int | None:
    if args.group is None:
        return None

    for repo_root in _skew_candidate_roots(args):
        if _running_from_checkout(repo_root):
            continue
        source_version = _read_source_declared_version(repo_root)
        if source_version is None:
            continue
        running_version = _running_package_version()
        if not _is_newer_version(source_version, running_version):
            continue

        label = _command_label(args)
        detail = (
            "CE stale-wheel/source-version skew detected: "
            f"checkout {repo_root} declares validators version {source_version}, "
            f"but the running package {_STALE_WHEEL_PACKAGE} is {running_version}."
        )
        if os.environ.get(_STALE_WHEEL_OVERRIDE_ENV) == "1":
            print(f"{detail} {_STALE_WHEEL_OVERRIDE_ENV}=1 set; proceeding by explicit override.", file=sys.stderr)
            return None

        command_key = (args.group, getattr(args, "brain_cmd", None) if args.group == "brain" else None)
        if command_key in _STALE_WHEEL_GATE_COMMANDS:
            print(
                f"ERROR: {detail} Refusing gate-relevant `ce {label}` under stale-wheel skew. "
                f"Use `PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli {label}` "
                f"from the checkout, or set `{_STALE_WHEEL_OVERRIDE_ENV}=1` to proceed explicitly.",
                file=sys.stderr,
            )
            return 2

        print(
            f"WARNING: {detail} Non-gate `ce {label}` will proceed. "
            f"Use `PYTHONPATH=validators python3 -m creator_engine_validator.ce_cli {label}` "
            f"from the checkout, or set `{_STALE_WHEEL_OVERRIDE_ENV}=1` to proceed explicitly.",
            file=sys.stderr,
        )
        return None

    return None


def _heartbeat_check(args: argparse.Namespace) -> int:
    state_dir, grace_factor, expected = daemon_heartbeat_alarm.configuration_from_environment()
    report = daemon_heartbeat_alarm.check_heartbeats(
        state_dir, grace_factor=grace_factor, expected_daemons=expected
    )
    if not report["ok"]:
        daemon_heartbeat_alarm.append_new_alarms(
            report, Path(".ce/state/controller-inbox/daemon-alarms.ndjson")
        )
    if args.json_output:
        print(json.dumps(report, sort_keys=True))
    else:
        for entry in report["daemons"]:
            marker = "OK" if entry["state"] == "OK" else "FAIL"
            print(f"[{marker}] {entry['daemon_id']}: {entry['state']} — {entry['cause']}")
    return 0 if report["ok"] else 1


def _maybe_print_startup_update_notice(args) -> None:
    if getattr(args, "json_output", False):
        return
    try:
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            return
        denied, _reason = hook_check.startup_toolchain_self_update_denied(cwd=Path.cwd())
        if denied:
            return
        result = update_runtime.check_startup_update_notice()
        if not (result.notice_due and result.available_semver):
            return
        print(f"ce {result.available_semver} available - run 'ce update'", file=sys.stderr)
        update_runtime.mark_startup_update_notice_shown(result.cache_path)
    except Exception:
        return


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "conveyor":
        return _conveyor_bridge(argv[1:])
    if argv and argv[0] == "press-merge-evidence":
        return _press_merge_evidence_from_argv(argv[1:])
    if argv and argv[0] in V3_FORWARDING_SHIMS:
        return _forward_v3_argv(argv[0], argv[1:])
    onboard_installer_flag_result = _maybe_refuse_native_onboard_installer_flags(argv)
    if onboard_installer_flag_result is not None:
        return onboard_installer_flag_result
    parser = _build_parser()
    args = parser.parse_args(argv)
    skew_result = _maybe_guard_stale_wheel_skew(args)
    if skew_result is not None:
        return skew_result
    _maybe_print_startup_update_notice(args)
    if args.group is None:
        _print_usage_with_stage_map(parser)
        return 2

    if args.group == "dequeue":
        return _dequeue(args)
    if args.group == "heartbeat":
        if getattr(args, "heartbeat_cmd", None) != "check":
            parser.parse_args(["heartbeat", "--help"])
            return 2
        return _heartbeat_check(args)
    if args.group == "lane":
        lane_cmd = getattr(args, "lane_cmd", None)
        handler = _LANE_DISPATCH.get(lane_cmd)
        if handler is None:
            parser.parse_args(["lane", "--help"])  # prints lane help, exits
            return 2
        return handler(args)
    if args.group == "ledger":
        ledger_cmd = getattr(args, "ledger_cmd", None)
        handler = _LEDGER_DISPATCH.get(ledger_cmd)
        if handler is None:
            parser.parse_args(["ledger", "--help"])  # prints ledger help, exits
            return 2
        return handler(args)
    if args.group == "worker":
        worker_cmd = getattr(args, "worker_cmd", None)
        handler = _WORKER_DISPATCH.get(worker_cmd)
        if handler is None:
            parser.parse_args(["worker", "--help"])  # prints worker help, exits
            return 2
        return handler(args)
    if args.group == "fanin":
        fanin_cmd = getattr(args, "fanin_cmd", None)
        handler = _FANIN_DISPATCH.get(fanin_cmd)
        if handler is None:
            parser.parse_args(["fanin", "--help"])  # prints fanin help, exits
            return 2
        return handler(args)
    if args.group == "queue":
        queue_cmd = getattr(args, "queue_cmd", None)
        handler = _QUEUE_DISPATCH.get(queue_cmd)
        if handler is None:
            parser.parse_args(["queue", "--help"])  # prints queue help, exits
            return 2
        return handler(args)
    if args.group == "event":
        event_cmd = getattr(args, "event_cmd", None)
        handler = _EVENT_DISPATCH.get(event_cmd)
        if handler is None:
            parser.parse_args(["event", "--help"])  # prints event help, exits
            return 2
        return handler(args)
    if args.group == "pcl":
        pcl_cmd = getattr(args, "pcl_cmd", None)
        handler = _PCL_DISPATCH.get(pcl_cmd)
        if handler is None:
            parser.parse_args(["pcl", "--help"])  # prints pcl help, exits
            return 2
        return handler(args)
    if args.group == "brain":
        brain_cmd = getattr(args, "brain_cmd", None)
        handler = _BRAIN_DISPATCH.get(brain_cmd)
        if handler is None:
            parser.parse_args(["brain", "--help"])  # prints brain help, exits
            return 2
        return handler(args)
    if args.group == "orchestrator":
        orchestrator_cmd = getattr(args, "orchestrator_cmd", None)
        handler = _ORCHESTRATOR_DISPATCH.get(orchestrator_cmd)
        if handler is None:
            parser.parse_args(["orchestrator", "--help"])  # prints orchestrator help, exits
            return 2
        return handler(args)
    if args.group == "connector":
        connector_cmd = getattr(args, "connector_cmd", None)
        handler = _CONNECTOR_DISPATCH.get(connector_cmd)
        if handler is None:
            parser.parse_args(["connector", "--help"])  # prints connector help, exits
            return 2
        return handler(args)
    if args.group == "playbook":
        if getattr(args, "playbook_cmd", None) is None:
            parser.parse_args(["playbook", "--help"])  # prints playbook help, exits
            return 2
        return playbook_runtime.run_cli(args)
    if args.group == "reviewer-triage":
        reviewer_triage_cmd = getattr(args, "reviewer_triage_cmd", None)
        handler = _REVIEWER_TRIAGE_DISPATCH.get(reviewer_triage_cmd)
        if handler is None:
            parser.parse_args(["reviewer-triage", "--help"])  # prints reviewer-triage help, exits
            return 2
        return handler(args)
    if args.group == "pickup":
        pickup_cmd = getattr(args, "pickup_cmd", None)
        handler = _PICKUP_DISPATCH.get(pickup_cmd)
        if handler is None:
            parser.print_usage(sys.stderr)
            return 2
        return handler(args)
    if args.group in V3_FORWARDING_SHIMS:
        return _forward_v3_command(args)
    if args.group == "triage":
        if getattr(args, "triage_cmd", None) != "queue":
            parser.parse_args(["triage", "--help"])  # prints triage help, exits
            return 2
        triage_queue_cmd = getattr(args, "triage_queue_cmd", None)
        handler = _TRIAGE_QUEUE_DISPATCH.get(triage_queue_cmd)
        if handler is None:
            parser.parse_args(["triage", "queue", "--help"])  # prints queue help, exits
            return 2
        return handler(args)
    if args.group == "dependency-unlock":
        dependency_unlock_cmd = getattr(args, "dependency_unlock_cmd", None)
        handler = _DEPENDENCY_UNLOCK_DISPATCH.get(dependency_unlock_cmd)
        if handler is None:
            parser.parse_args(["dependency-unlock", "--help"])  # prints group help, exits
            return 2
        return handler(args)
    if args.group == "claim":
        claim_cmd = getattr(args, "claim_cmd", None)
        handler = _CLAIM_DISPATCH.get(claim_cmd)
        if handler is None:
            parser.parse_args(["claim", "--help"])  # prints claim help, exits
            return 2
        return handler(args)
    if args.group == "herdr":
        herdr_cmd = getattr(args, "herdr_cmd", None)
        handler = _HERDR_DISPATCH.get(herdr_cmd)
        if handler is None:
            parser.parse_args(["herdr", "--help"])  # prints herdr help, exits
            return 2
        return handler(args)
    if args.group in ("ask", "support"):
        return support_runtime.run_cli(args)
    if args.group == "verify-install":
        return _verify_install(args)
    if args.group == "update":
        if getattr(args, "track", "release") == "main":
            return main_head_install.run_cli(args)
        return update_runtime.run_cli(args)
    if args.group == "clean-main-install":
        return main_head_install.run_cli(args)
    if args.group == "surfaces":
        surfaces_cmd = getattr(args, "surfaces_cmd", None)
        if surfaces_cmd == "check-updates":
            return surfaces_check_updates.run_cli(args)
        if surfaces_cmd == "fleet-rollout":
            return surfaces_fleet_rollout.run_cli(args)
        else:
            parser.parse_args(["surfaces", "--help"])  # prints surfaces help, exits
            return 2
    if args.group == "onboard":
        return ce_onboard.run_cli(args)
    if args.group == "bootstrap":
        return _bootstrap(args)
    if args.group == "checkpoint":
        return _checkpoint(args)
    if args.group == "check":
        return _check(args)
    if args.group == "doctor":
        return _doctor(args)
    if args.group == "containment-probe":
        return _containment_probe(args)
    if args.group == "publish-branch":
        return _publish_branch(args)
    if args.group == "validate-pr":
        return pr_preflight.run_cli(args)
    if args.group == "automerge-decide":
        return _automerge_decide(args)
    if args.group == "automerge-status":
        return _automerge_status(args)
    if args.group == "automerge-kill-switch":
        return _automerge_kill_switch(args)
    if args.group == "containment-status":
        return _containment_status(args)
    if args.group == "init":
        return _init(args)
    if args.group in ("launch", "hud"):
        return _launch(args, invoked_as=args.group)
    if args.group == "takeover":
        return _takeover(args)
    if args.group == "continuity-drill":
        return _continuity_drill(args)
    if args.group == "harness-matrix":
        return _harness_matrix(args)
    if args.group == "posture":
        return _posture(args)

    _print_usage_with_stage_map(parser)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
