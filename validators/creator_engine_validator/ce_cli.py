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
ce fanin build       # aggregate local evidence into a deterministic fan-in packet (RV1-070/071)
ce fanin inspect     # verify a fan-in packet's content hash + shape, read-only
ce queue dry-run     # preview a serialized canonical-branch landing order, no authority (RV1-082)
ce queue inspect     # verify a dry-run landing preview's content hash + shape, read-only
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
ce connector verify     # validate a connector descriptor + Mission-Brief pair (offline) (G2.005.1)
ce connector plan       # build + validate a read-only read plan (offline)
ce connector fetch      # execute one read-only GET via an injectable client; credential by reference; offline fails closed
ce connector write-plan # build + validate a strict-mode tracker_mirror write plan (offline) (G2.005.2)
ce connector submit     # execute one bounded tracker_mirror write; credential REQUIRED by reference; offline fails closed
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
import json
import sys
from typing import Sequence

from . import (
    ce_event_runtime,
    connector_runtime,
    doctor_runtime,
    fanin_runtime,
    init_runtime,
    integration_queue_dry_run,
    lane_runtime,
    launch_runtime,
    pcl_runtime,
    side_effect_ledger_runtime,
    transcript_archive,
    worker_runtime,
)
from .checks.side_effect_ledger import EFFECT_KINDS, EFFECT_STATUSES
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ce", description="Creator Engine kernel (v1.0 Gate 3 lane-launch surface)"
    )
    groups = parser.add_subparsers(dest="group")

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
    launch.add_argument("--ledger-root", required=True, help="path to .hermes/active-work-ledger")
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
        help="CE-owned MCP config path inside the repo / .hermes (pins --strict-mcp-config)",
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
        "--ratification-evidence",
        dest="ratification_evidence_ref",
        default=None,
        help="inherited ratification-evidence pointer carried for elevated modes / privileged lane kinds",
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
        help="refuse-only flag: request a non-visible terminal (always refused for visible roles)",
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
    rec.add_argument("--active-work-ledger-root", required=True, help="path to .hermes/active-work-ledger")
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

    worker = groups.add_parser("worker", help="worker isolation runtime (rootless Podman + credential broker)")
    worker_sub = worker.add_subparsers(dest="worker_cmd")

    wa = worker_sub.add_parser("allocate", help="start a worker container bound to a live claim under a ratified policy")
    wa.add_argument("--policy", required=True, help="path to the ratified worker-container policy record")
    wa.add_argument("--controller-id", required=True)
    wa.add_argument("--lane-id", required=True)
    wa.add_argument("--claim-ref", required=True, help="claim path relative to --active-work-ledger-root")
    wa.add_argument("--lease-ref", required=True, help="lease path relative to --active-work-ledger-root")
    wa.add_argument("--active-work-ledger-root", required=True, help="path to .hermes/active-work-ledger")
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
        help="ignored output root for the packet (e.g. .hermes/fan-in/)",
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

    # ce queue — Integration Queue dry-run seam (Gate 8, RV1-082). Local
    # serialized landing preview only; live enqueue/land/merge is refused.
    queue = groups.add_parser(
        "queue",
        help="preview/inspect an Integration Queue dry-run landing order (no authority)",
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
        help="ignored output root for the preview (e.g. .hermes/integration-queue/)",
    )
    qd.add_argument("--repo-root", default=None, help="repo root for the git-ignore guard")
    qd.add_argument("--preview-id", default=None, help="override the request's preview_id")
    # Refusal-only authority flags: the dry-run seam never lands/enqueues/merges.
    qd.add_argument(
        "--enqueue",
        action="store_true",
        help="refuse-only flag: live enqueue is never granted by the dry-run seam (always refused)",
    )
    qd.add_argument(
        "--land",
        action="store_true",
        help="refuse-only flag: live landing is never granted by the dry-run seam (always refused)",
    )
    qd.add_argument(
        "--merge",
        action="store_true",
        help="refuse-only flag: live merge is never granted by the dry-run seam (always refused)",
    )
    qd.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    qi = queue_sub.add_parser("inspect", help="verify a preview's content hash + shape (read-only)")
    qi.add_argument("--preview", required=True, help="path to an existing dry-run landing preview")
    qi.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

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
    pa.add_argument("--repo-root", default=None, help="repo root (records must not target .hermes/)")
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
    cf.add_argument("--base-url", default=connector_runtime.DEFAULT_GITHUB_API_BASE, help="read API base URL")
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

    # ce check — umbrella wrapper over the retained creator-engine-validator
    # conformance checks (DP-1 = A: ce wraps the validator subcommands).
    check = groups.add_parser(
        "check", help="run creator-engine-validator conformance checks (wraps the validator)"
    )
    check.add_argument("paths", nargs="*", default=["."], help="paths to validate")
    check.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")
    check.add_argument("--tenant", default=None, help="restrict cross-artifact checks to one tenant")
    check.add_argument("--list-checks", action="store_true", help="list enabled checks and their FRs")

    # ce doctor — governed-environment guard preflight (DP-3 = B, RV1-061).
    doctor = groups.add_parser(
        "doctor", help="governed-environment guard preflight; refuses ungoverned host drift"
    )
    doctor.add_argument("--repo-root", default=".", help="repo root to preflight (default: cwd)")
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
        help="skip the dependency/wheelhouse contract clause (RED-G-6)",
    )

    # ce init — idempotent local v1.0 kernel state initialization (RV1-062).
    init = groups.add_parser(
        "init", help="idempotently initialize local .hermes/ kernel state (refuses ungoverned state)"
    )
    init.add_argument("--repo-root", default=".", help="repo root to initialize (default: cwd)")
    init.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    # ce launch / ce hud — deterministic visible Controller-seat launcher
    # (DP-2 = B, RV1-063). ce hud is an alias/seam label for the same launcher.
    def _add_launch_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--harness", default=launch_runtime.DEFAULT_HARNESS, help="Controller-seat harness")
        p.add_argument("--session", default=launch_runtime.DEFAULT_SESSION, help="tmux session name")
        p.add_argument("--window", default=launch_runtime.DEFAULT_WINDOW, help="tmux window name")
        p.add_argument("--resume", action="store_true", help="attach an existing launcher session")
        p.add_argument("--dry-run", action="store_true", help="plan only; no tmux spawn, no provider login")
        p.add_argument(
            "--no-tmux",
            action="store_true",
            help="refuse-only flag: request a non-visible/headless seat (always refused)",
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
            "--mcp-config",
            dest="mcp_config",
            default=None,
            help="CE-owned MCP config path inside the repo / .hermes (pins --strict-mcp-config)",
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
        p.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")

    launch = groups.add_parser(
        "launch", help="open/attach the visible Controller-seat tmux launcher (DP-2=B)"
    )
    _add_launch_args(launch)
    hud = groups.add_parser("hud", help="alias/seam label for `ce launch` (not a CE-native TUI)")
    _add_launch_args(hud)

    return parser


def _lane_launch(args) -> int:
    command = args.command.split() if args.command else None
    claude_arg = getattr(args, "claude_arg", None)
    if command is not None and claude_arg:
        command = [*command, *claude_arg]
    terminal_kind = "headless" if args.no_tmux else lane_runtime.TMUX_TERMINAL_KIND
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
            tmux_adapter=_make_tmux_adapter(),
        )
    except lane_runtime.LaneLaunchError as exc:
        print(f"ERROR: ce lane launch refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    term = result.record["terminal"]
    print(
        f"ce lane launch: wrote {result.pane_path} "
        f"(tmux session={term['session_id']} window={term['window_id']} pane={term['pane_id']})"
    )
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
    live_action = next(
        (name for name in ("enqueue", "land", "merge") if getattr(args, name, False)), None
    )
    try:
        result = integration_queue_dry_run.build(
            request=args.request,
            preview_root=args.preview_root,
            repo_root=args.repo_root,
            preview_id=args.preview_id,
            live_action=live_action,
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
    return validator_cli.main([*prefix, "check", *paths])


def _init(args) -> int:
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
    return 0


def _launch(args, invoked_as: str = "launch") -> int:
    try:
        result = launch_runtime.launch(
            harness=args.harness,
            session=args.session,
            window=args.window,
            invoked_as=invoked_as,
            resume=args.resume,
            dry_run=args.dry_run,
            visible=not args.no_tmux,
            extra_args=getattr(args, "claude_arg", None),
            mcp_config_path=getattr(args, "mcp_config", None),
            closeout_file=getattr(args, "closeout_file", None),
            completion_report_ref=getattr(args, "completion_report_ref", None),
            tmux_adapter=_make_tmux_adapter(),
        )
    except launch_runtime.LaunchError as exc:
        print(f"ERROR: ce {invoked_as} refused [{exc.code}]: {exc}", file=sys.stderr)
        return 1
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


def _doctor(args) -> int:
    report = doctor_runtime.run_doctor(
        args.repo_root,
        require_visible_launch=args.require_visible_launch,
        require_worker=args.require_worker,
        check_packaging=not args.no_check_packaging,
    )
    if getattr(args, "json_output", False):
        print(json.dumps(report.payload, indent=2, sort_keys=True))
    else:
        print(doctor_runtime.render_human(report))
    return 0 if report.ok else 1


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
    "allocate": _worker_allocate,
    "terminate": _worker_terminate,
    "gc": _worker_gc,
    "status": _worker_status,
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

_CONNECTOR_DISPATCH = {
    "verify": _connector_verify,
    "plan": _connector_plan,
    "fetch": _connector_fetch,
    "write-plan": _connector_write_plan,
    "submit": _connector_submit,
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

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
    if args.group == "connector":
        connector_cmd = getattr(args, "connector_cmd", None)
        handler = _CONNECTOR_DISPATCH.get(connector_cmd)
        if handler is None:
            parser.parse_args(["connector", "--help"])  # prints connector help, exits
            return 2
        return handler(args)
    if args.group == "check":
        return _check(args)
    if args.group == "doctor":
        return _doctor(args)
    if args.group == "init":
        return _init(args)
    if args.group in ("launch", "hud"):
        return _launch(args, invoked_as=args.group)

    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
