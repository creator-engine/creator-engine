"""Single source of truth for the public-repo confidentiality rule.

The repository is public (it is the source of record for ``creator-engine.dev``),
so every tracked text file must never leak two classes of
content:

1. **Confidential ``ce-ops#NNN`` ticket references.** The ``ce-ops`` tracker is
   a private, internal issue tracker. Its ticket numbers must never appear in
   any public doc.
2. **Internal host / network identifiers.** Tailnet hostnames, seat-login
   markers, the internal VPS IP, and the hosting-provider name are internal
   fleet topology and must never appear in any public doc.

This module owns the rule (the public-doc file set, the forbidden patterns, the
``KNOWN_PENDING`` debt-ratchet allowlist, and the offense formatter). It is the
ONE place the rule lives. Two callers reuse it without forking it:

* the CI test ``test_public_docs_confidentiality.py`` (fail-closed merge gate),
* the fast standalone CLI check ``scan-public-docs-confidentiality`` that runs
  in ``ce validate-pr`` so a leak is caught BEFORE push, not only at CI.

The ``KNOWN_PENDING`` allowlist is a *debt ratchet*: it enumerates the files
that still carry internal references pending the separate redact/relocate
cleanup. New leaks are blocked immediately (any file not on the list that
introduces an offender fails), and the list may only shrink — a cleaned/removed
allowlisted file must be dropped from it.

This module file itself is excluded from the scan: it necessarily names the very
patterns it forbids.
"""
from __future__ import annotations

import re
import stat
import subprocess
from pathlib import Path

from .reporting import CheckResult, ValidationError, make_error

CHECK_NAME = "public_docs_confidentiality"
CONTRACT = "validators/tests/unit/test_public_docs_confidentiality.py"

# The standing reminder, surfaced verbatim in the failure remediation so a seat
# that triggers the guard learns the rule at the point of failure.
REMINDER = (
    "If you touch docs/**, run the confidentiality guard before push; "
    "ZERO ce-ops# refs in public docs."
)

# Forbidden patterns in any tracked text file. Keep each pattern's human label for
# debuggable failure output.
FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("confidential ce-ops# ticket reference", re.compile(r"ce-ops#\d+")),
    ("confidential ce-ops private-repo URL", re.compile(r"github\.com/creator-engine/ce-ops")),
    ("internal seat-login marker", re.compile(r"\bce-dev-\d+\b")),
    ("internal tailnet hostname", re.compile(r"\.tailf3cfef\.ts\.net")),
    ("internal VPS IP", re.compile(r"100\.72\.252\.20")),
    ("internal hosting-provider name", re.compile(r"Hetzner")),
    ("confidential internal codename skynet", re.compile(r"(?i)skynet")),
    ("confidential ce-ops hyphen ticket ref", re.compile(r"ce-ops-\d+")),
)

TICKET_REF_LABELS = frozenset(
    {
        "confidential ce-ops# ticket reference",
        "confidential ce-ops hyphen ticket ref",
    }
)
_CARRIER_TICKET_REF = r"(?:creator-engine/)?ce-ops#\d+"
_CHANGELOG_ISSUE_LINE = re.compile(rf"^issue: {_CARRIER_TICKET_REF}$")
_PR_MANIFEST_HEADER_LINE = re.compile(rf"^# PR path manifest — {_CARRIER_TICKET_REF}(?:\s.*)?$")

# Files containing NUL bytes are treated as binary and skipped. All other
# tracked files are decoded lossily so ASCII leaks are still caught in non-UTF-8
# text rather than silently skipped.
BINARY_SENTINEL = b"\0"

# Files that still carry internal references pending the separate
# redact/relocate cleanup. This list may ONLY shrink. Paths are repo-root
# relative, POSIX-separated.
KNOWN_PENDING: frozenset[str] = frozenset(
    {
        "docs/architecture/ADR-0006-derived-artifacts-out-of-trust-path.md",
        "docs/architecture/cockpit.md",
        "docs/architecture/egress-broker.md",
        "docs/architecture/HERDR_GOVERNANCE_BOUNDARY.md",
        "docs/architecture/seat-sentinel-contract.md",
        "docs/architecture/tasks-handoff-contract.md",
        "docs/architecture/work-claim-locks.md",
        "docs/assets/ce-logo-v2-weldarm.svg",
        "docs/contracts/brownfield-adoption.md",
        "docs/contracts/computer-use-authority-envelope.md",
        "docs/contracts/computer-use-worker-harness.md",
        "docs/contracts/devops-privileged-action-broker.md",
        "docs/contracts/installer.md",
        "docs/contracts/plain-join.md",
        "docs/contracts/README.md",
        "docs/contracts/runtime-policy.md",
        "docs/decisions/0005-openbao-secret-identity-backend.md",
        "docs/decisions/ADR-0007-egress-gateway-publish-broker.md",
        "docs/decisions/ADR-0008-web-control-ui.md",
        "docs/decisions/ADR-0009-bounded-work-units-small-batches.md",
        "docs/decisions/ADR-0010-take-app-wheel-out-of-authored-prs.md",
        "docs/decisions/ADR-0011-devops-privileged-action-broker.md",
        "docs/decisions/ADR-0012-openbao-micro-unit-standup.md",
        "docs/devops/openbao-approval-wall-arming.md",
        "docs/devops/openbao-operator-bringup.md",
        "docs/devops/openbao-production-golive.md",
        "docs/downloads/0.2.0/scanners/scanner-mirror.fragment.yaml",
        "docs/security/ce234-approval-capability-wall.md",
    }
)

# Internal-tree guard exceptions (ce-ops#283).
#
# ``docs/operations/**`` and ``docs/delivery/**`` are internal operating/
# delivery surfaces that currently live in the public docs tree. These explicit
# allowlists are a debt ratchet: current files are listed so the guard passes
# today, but future net-new files in either tree fail until they are moved out
# or deliberately added here. The guard also fails on stale entries (a listed
# file that no longer exists), so the lists may only shrink as files leave.
KNOWN_OPERATIONS_EXCEPTIONS: frozenset[str] = frozenset(
    {
        "docs/operations/ACTIVE_WORK_LEDGER_PROTOCOL.md",
        "docs/operations/AGENT_NATIVE_BOOTSTRAP.md",
        "docs/operations/AUTHOR_A_CE_VALID_PR.md",
        "docs/operations/CE_EVENT_PROTOCOL.md",
        "docs/operations/CLAUDE_CODE_CONTROLLER_SEAT_CONTRACT.md",
        "docs/operations/CLAUDE_CODE_HOOK_PACK.md",
        "docs/operations/CODEX_FIRST_CLASS_PROTOCOL.md",
        "docs/operations/COMPLETION_REPORT_PROTOCOL.md",
        "docs/operations/CONNECTOR_PROTOCOL.md",
        "docs/operations/CONTAINED_CONTROLLER_PARITY_ACCEPTANCE.md",
        "docs/operations/CONTROLLER_BOUNDARY_POLICY.md",
        "docs/operations/CONTROLLER_IDENTITY_PROTOCOL.md",
        "docs/operations/CONTROLLER_RUNTIME_CONTRACT_PROTOCOL.md",
        "docs/operations/DISTRIBUTED_IDENTITY_PROTOCOL.md",
        "docs/operations/EVIDENCE_FAN_IN_PROTOCOL.md",
        "docs/operations/EXTENSION_HOOK_CONTRACT.md",
        "docs/operations/PRESS_MERGE_BUNDLE.md",
        "docs/operations/GITHUB_NATIVE_COORDINATION_PROTOCOL.md",
        "docs/operations/GOVERNED_LANE_LAUNCH_PROTOCOL.md",
        "docs/operations/GREENFIELD_FIRST_PROJECT_PROTOCOL.md",
        "docs/operations/HARNESS_SEAT_CONTRACT.md",
        "docs/operations/HARNESS_SUPPORT_CAPABILITY_MATRIX.md",
        "docs/operations/HERDR_OPERATOR_REACH_PLANE.md",
        "docs/operations/INSTALLED_CE_DOGFOOD_MIGRATION.md",
        "docs/operations/INTEGRATION_QUEUE_DRY_RUN.md",
        "docs/operations/NO_COPY_PASTE_PATTERN.md",
        "docs/operations/ONBOARD_APPLY_PROTOCOL.md",
        "docs/operations/PANE_REGISTRY_PROTOCOL.md",
        "docs/operations/PATH_MANIFEST_FIDELITY_PROTOCOL.md",
        "docs/operations/PCL_PROTOCOL.md",
        "docs/operations/PCO_FANIN_PROTOCOL.md",
        "docs/operations/REVIEWER_TRIAGE.md",
        "docs/operations/REVIEWER_VENUE_AUTHORITY.md",
        "docs/operations/REVIEW_GATE_REVIEWER_VENUE_DESIGN.md",
        "docs/operations/ROLE_BOUNDARY_FAILSAFE_STAGE_1_DESIGN.md",
        "docs/operations/ROOT_WORKTREE_INVARIANT.md",
        "docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md",
        "docs/operations/SEAT_REAPER_PROTOCOL.md",
        "docs/operations/SIDE_EFFECT_LEDGER_PROTOCOL.md",
        "docs/operations/STATE_BOUNDARY_PROTOCOL.md",
        "docs/operations/TRANSCRIPT_ARCHIVE_PROTOCOL.md",
        "docs/operations/WORKER_CONTAINER_PROTOCOL.md",
        "docs/operations/WORKER_HOST_READINESS.md",
        "docs/operations/WORKTREE_ALLOCATOR_PROTOCOL.md",
        "docs/operations/WORKTREE_LEASE_PROTOCOL.md",
        "docs/operations/session-continuity-protocol.md",
    }
)

KNOWN_DELIVERY_EXCEPTIONS: frozenset[str] = frozenset(
    {
        "docs/delivery/ASSIGNMENT_ENVELOPE_DRY_RUN.md",
        "docs/delivery/ASSIGNMENT_ENVELOPE_TEMPLATE.md",
        "docs/delivery/DEFINITION_OF_DONE.md",
        "docs/delivery/DEFINITION_OF_READY.md",
        "docs/delivery/DEPLOYMENT_APPROVAL_POLICY.md",
        "docs/delivery/ENVELOPE_CONSUMPTION_CHECKLIST.md",
        "docs/delivery/MERGE_APPROVAL_CHECKLIST.md",
        "docs/delivery/NEXT_TASK_PROTOCOL.md",
        "docs/delivery/README.md",
        "docs/delivery/RELEASE_CANDIDATE_CHECKLIST.md",
        "docs/delivery/RELEASE_DEPLOY_GOVERNANCE.md",
        "docs/delivery/REVIEWER_IDENTITY_REQUIREMENTS.md",
        "docs/delivery/REVIEW_EVIDENCE_TEMPLATE.md",
        "docs/delivery/REVIEW_GATE.md",
        "docs/delivery/ROLLBACK_AND_POST_RELEASE_EVIDENCE.md",
        "docs/delivery/SCOPE_AUDIT_CHECKLIST.md",
        "docs/delivery/VERSIONING_AND_RELEASE_POLICY.md",
        "docs/delivery/WORKTREE_RUNTIME_PROTOCOL.md",
    }
)

# Internal public-doc trees guarded against net-new files, paired with their
# debt-ratchet exception allowlists.
INTERNAL_GUARDED_TREES: tuple[tuple[str, frozenset[str]], ...] = (
    ("docs/operations", KNOWN_OPERATIONS_EXCEPTIONS),
    ("docs/delivery", KNOWN_DELIVERY_EXCEPTIONS),
)

# Explicit baseline exceptions for the widened public-repo scan. Entries are
# keyed by repo-relative file plus forbidden token class; real token values are
# intentionally not recorded here. The compact rows keep the source diff small
# while still enumerating exact file/token-class pairs.
_ALLOWED_OFFENSE_ROWS = """\
confidential ce-ops hyphen ticket ref|.ce/changelog/ce-348-adr-0013-promote.md
confidential ce-ops hyphen ticket ref|deploy/dgx-controller-runsc/DESIGN.md,deploy/dgx-controller-runsc/Dockerfile,deploy/dgx-controller-runsc/README.md,deploy/dgx-controller-runsc/ce-controller-gh-guard.sh,deploy/dgx-controller-runsc/run-controller-runsc.sh,deploy/dgx-controller-runsc/test-controller-dry-run.sh,deploy/dgx-runsc/README.md,docs/architecture/ADR-0006-derived-artifacts-out-of-trust-path.md,docs/contracts/devops-privileged-action-broker.md,docs/decisions/0005-openbao-secret-identity-backend.md,docs/decisions/ADR-0011-devops-privileged-action-broker.md
confidential ce-ops hyphen ticket ref|docs/decisions/ADR-0012-openbao-micro-unit-standup.md,docs/devops/openbao/secret-migration-inventory.tsv,tools/egress-broker/README.md,validators/tests/unit/test_devops_privileged_action_broker.py,validators/tests/unit/test_dgx_controller_runsc.py,validators/tests/unit/test_openbao_golive.py,validators/tests/unit/test_openbao_p3.py,validators/tests/unit/test_public_docs_confidentiality.py
confidential ce-ops private-repo URL|.ce/changelog/ce-348-adr-0013-promote.md,docs/architecture/ADR-0006-derived-artifacts-out-of-trust-path.md,docs/decisions/0005-openbao-secret-identity-backend.md,docs/decisions/ADR-0012-openbao-micro-unit-standup.md,validators/tests/unit/test_ce_launch_cli.py,validators/tests/unit/test_ce_ops_triage_queue.py,validators/tests/unit/test_forge_triage.py,validators/tests/unit/test_public_docs_confidentiality.py,validators/tests/unit/test_work_claims.py
confidential ce-ops# ticket reference|.ce/changelog/bugfix-54-56-58.md,.ce/changelog/ce-286-host-uds-persist.md,.ce/changelog/ce-287-broker-brokenpipe.md,.ce/changelog/ce-288-count-agnostic-checks.md,.ce/changelog/ce-291-automerge-classifier-dryrun.md,.ce/changelog/ce-295-annoyance-tool-reflex.md
confidential ce-ops# ticket reference|.ce/changelog/ce-305-fix-egress-socket-test.md
confidential ce-ops# ticket reference|.ce/changelog/ce-344-slice3-skillify.md
confidential ce-ops# ticket reference|.ce/changelog/ce-366-main-head-resolver.md
confidential ce-ops# ticket reference|.ce/changelog/ce-appgrant-failclosed.md,.ce/changelog/ce-arad-pilot-runbook.md,.ce/changelog/ce-belt-claim-path-fix.md
confidential ce-ops# ticket reference|.ce/changelog/ce-confidentiality-pre-push-guard.md,.ce/changelog/ce-dev4-surface-update.md
confidential ce-ops# ticket reference|.ce/changelog/ce-forge-persona-catalog.md,.ce/changelog/ce-forge-rebase-dismiss-fix.md,.ce/changelog/ce-g9-brain-smoke.md,.ce/changelog/ce-integrator-daemon.md,.ce/changelog/ce-integrator-discovery-fix.md,.ce/changelog/ce-integrator-reviews-fix.md
confidential ce-ops# ticket reference|.ce/changelog/ce-openbao-vps-standup.md,.ce/changelog/ce-ops-232-host-persistent-seat-logging-pr.md
confidential ce-ops# ticket reference|.ce/changelog/ce-preflight-before-push-ssot.md,.ce/changelog/ce-remove-internal-roadmaps.md,.ce/changelog/ce-republish-020-rootv1.md,.ce/changelog/ce-republish-020-with71.md,.ce/changelog/ce-republish-020-with85.md,.ce/changelog/ce-review-daemon.md
confidential ce-ops# ticket reference|.ce/changelog/ce105-s1-deploy-classifier.md,.ce/changelog/ce107b-sec7-forge-guard.md,.ce/changelog/ce109-ring1-fs-mediation.md,.ce/changelog/ce11-test-tier-split.md
confidential ce-ops# ticket reference|.ce/changelog/ce119-tasks-handoff-contract.md,.ce/changelog/ce121-134-aarch64-wheelhouse.md
confidential ce-ops# ticket reference|.ce/changelog/ce128-backend-selector-policy.md,.ce/changelog/ce128-contained-launch-proof.md,.ce/changelog/ce128-docker-runsc-plan.md,.ce/changelog/ce128-launch-runner-integration.md,.ce/changelog/ce128-vps-contained-herdr.md,.ce/changelog/ce132-cleanroom-install-s1.md,.ce/changelog/ce133-adr0006-design.md,.ce/changelog/ce133-remove-committed-app-wheel.md,.ce/changelog/ce135-openbao-secret-zero-broker.md
confidential ce-ops# ticket reference|.ce/changelog/ce146-ssdf-slsa-matrix.md,.ce/changelog/ce148-seat-provisioning.md,.ce/changelog/ce154-autoclose.md
confidential ce-ops# ticket reference|.ce/changelog/ce163-born-foreman-inject.md,.ce/changelog/ce163-foreman-canon-enforced.md,.ce/changelog/ce163-foreman-hard-deny.md,.ce/changelog/ce163-foreman-seat-class.md,.ce/changelog/ce163-foreman-warn-arm.md,.ce/changelog/ce163-worker-spawn-primitive.md,.ce/changelog/ce164-fwheel1-author-gate.md
confidential ce-ops# ticket reference|.ce/changelog/ce164-work-sizing-floor.md,.ce/changelog/ce166-knowledge-ssot-slice1.md,.ce/changelog/ce166-knowledge-ssot-slice2.md,.ce/changelog/ce167-brain-assertion-ledger.md,.ce/changelog/ce168-work-sizing.md,.ce/changelog/ce173-idempotent-reinstall.md,.ce/changelog/ce173-null-probe-prior-app.md,.ce/changelog/ce174-stale-base-rerun.md,.ce/changelog/ce176-brain-probe.md
confidential ce-ops# ticket reference|.ce/changelog/ce177-brain-drift-ci.md,.ce/changelog/ce177-knowledge-ssot-drift-ci.md,.ce/changelog/ce178-brain-bootstrap.md,.ce/changelog/ce179-brain-recall-adapter.md,.ce/changelog/ce180-brain-ingest-sqlite-gemma.md,.ce/changelog/ce181-brain-recall-surface.md,.ce/changelog/ce182-pickup-feed-422-test-guard.md,.ce/changelog/ce182-search-pickup-feed.md,.ce/changelog/ce185-devops-privileged-action-broker.md,.ce/changelog/ce186-g6-seat-class-enforce.md
confidential ce-ops# ticket reference|.ce/changelog/ce187-42-w8-dispatch-plan.md,.ce/changelog/ce187-forge-triage.md,.ce/changelog/ce188-belt-reviews-pickup-claim-bridge.md,.ce/changelog/ce188-belt-reviews-pickup.md,.ce/changelog/ce189-supersession-guard.md,.ce/changelog/ce191-n3-first-value-mythos.md,.ce/changelog/ce191-n6-clean-room-rehearsal.md,.ce/changelog/ce191-n6-wire-first-value.md
confidential ce-ops# ticket reference|.ce/changelog/ce194-triage-hygiene.md,.ce/changelog/ce195-launch-argv-python-m.md,.ce/changelog/ce196-queue-hygiene-completeness.md,.ce/changelog/ce197-install-robustness.md,.ce/changelog/ce197-launcher-refuse.md,.ce/changelog/ce197-onboard-orchestrator.md,.ce/changelog/ce197-profile-path.md,.ce/changelog/ce197-verify-install.md,.ce/changelog/ce200-belt-lane-claim-allocation.md,.ce/changelog/ce203-lease-id-length.md
confidential ce-ops# ticket reference|.ce/changelog/ce205-launch-harness.md,.ce/changelog/ce206-brain-init.md,.ce/changelog/ce207-visibility-backend.md,.ce/changelog/ce207-w1-visibility-backend.md,.ce/changelog/ce207-w2prime-pty-session.md,.ce/changelog/ce211-node24-actions.md
confidential ce-ops# ticket reference|.ce/changelog/ce214-pr-open-carrier-scaffold.md,.ce/changelog/ce216-deterministic-resolvers.md,.ce/changelog/ce216-escalation-seam.md,.ce/changelog/ce216-executor-race-guard.md,.ce/changelog/ce217-u1-herdr-ce-scaffold.md
confidential ce-ops# ticket reference|.ce/changelog/ce218-belt-poller.md,.ce/changelog/ce219-codex-pretooluse-hook.md,.ce/changelog/ce219-codex-ring1-hookpack.md,.ce/changelog/ce219-ring1-codex-enforcement.md,.ce/changelog/ce220-harness-matrix.md,.ce/changelog/ce221-containment-probe-failclosed.md,.ce/changelog/ce221-containment-probe.md,.ce/changelog/ce221-probe-gvisor-detect.md
confidential ce-ops# ticket reference|.ce/changelog/ce223-clean-install-prereqs.md,.ce/changelog/ce227-wave-a.md,.ce/changelog/ce227-wave-b.md,.ce/changelog/ce227-wave-c.md
confidential ce-ops# ticket reference|.ce/changelog/ce229-live-action-scope-guard.md,.ce/changelog/ce230-verify-by-reaction.md
confidential ce-ops# ticket reference|.ce/changelog/ce240-contained-controller-scaffold.md,.ce/changelog/ce242-contained-seat-self-push-pr.md,.ce/changelog/ce242-live-self-push-pr.md,.ce/changelog/ce243-seat-review-transport-deputy-pr.md,.ce/changelog/ce244-bootstrap-injection-pr.md
confidential ce-ops# ticket reference|.ce/changelog/ce244-bootstrap-ssot-overlay.md,.ce/changelog/ce244-worker-tier.md,.ce/changelog/ce247-mint-on-approval-pr.md,.ce/changelog/ce249-split-relocate-and-scrub.md,.ce/changelog/ce25-ce-version-surface.md
confidential ce-ops# ticket reference|.ce/changelog/ce253-controller-inbox.md,.ce/changelog/ce262-closes-linkage-guard.md
confidential ce-ops# ticket reference|.ce/changelog/ce262-cross-repo-autoclose.md,.ce/changelog/ce266-broker-openbao-minter.md,.ce/changelog/ce267-broker-daemon-vault-wiring.md,.ce/changelog/ce268-self-review-daemon-vault-wiring.md,.ce/changelog/ce275-vps-image-pin.md
confidential ce-ops# ticket reference|.ce/changelog/ce281-broker-optional-signature.md,.ce/changelog/ce282-broker-socket-reachability.md,.ce/changelog/ce289-sopeercred-attestation.md,.ce/changelog/ce293-activate-belt-daemon.md
confidential ce-ops# ticket reference|.ce/changelog/ce298-human-contributor-role.md,.ce/changelog/ce303-preflight-before-push-directive.md,.ce/changelog/ce316-doc-autogen-cli-reference.md,.ce/changelog/ce323-install-shell-fix.md,.ce/changelog/ce337-rereview-phase2-autowire.md,.ce/changelog/ce39-merge-queue.md
confidential ce-ops# ticket reference|.ce/changelog/ce55-pickup-search-type-qualifier.md,.ce/changelog/ce80-republish-233.md,.ce/changelog/ce80-republish-post241.md,.ce/changelog/ce80-signed-publish.md,.ce/changelog/ce81-trustroot-fingerprint-anchor.md,.ce/changelog/ce88-live-forge-applydriver.md,.ce/changelog/ce89-spawn-repo-root.md
confidential ce-ops# ticket reference|.ce/changelog/ce94-127-forge-identity.md,.ce/changelog/ce99-p1-devops.md,.ce/changelog/ceops95-seat-lifecycle-phase1.md,.ce/changelog/feat-ce314-skills-pilot-antidrift-guard.md
confidential ce-ops# ticket reference|.ce/changelog/feat-runsc-detached-launch-mode.md,.ce/changelog/feat-vps-seat-validator-venv.md,.ce/changelog/fix-ce-ops-328-brownfield-forge-identity.md,.ce/changelog/ga2-runner-ring1-impl.md,.ce/changelog/livedriver-uv-mirror.md,.ce/changelog/release-0-3-0-publish.md,.ce/changelog/release-0-3-0-staging.md
confidential ce-ops# ticket reference|.ce/changelog/v35-roadmap-plan.md,.ce/pr-manifests/b8-operator-alerting.md,.ce/pr-manifests/bugfix-54-56-58.md,.ce/pr-manifests/ce-279-surfaces-render.md,.ce/pr-manifests/ce-286-host-uds-persist.md,.ce/pr-manifests/ce-287-broker-brokenpipe.md,.ce/pr-manifests/ce-288-count-agnostic-checks.md,.ce/pr-manifests/ce-290-broker-pr-body-workclass.md,.ce/pr-manifests/ce-292-autoreview-enforcement.md,.ce/pr-manifests/ce-292-autoreview.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce-295-w5-g5-body-emit.md,.ce/pr-manifests/ce-326-onboard-os-native-default.md,.ce/pr-manifests/ce-327-per-user-app.md,.ce/pr-manifests/ce-333-contributor-dev-install.md,.ce/pr-manifests/ce-334-packaging-test-skip-guard.md,.ce/pr-manifests/ce-335-rename-aware-gates.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce-342-ci-retrigger.md,.ce/pr-manifests/ce-344-slice3-skillify.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce-351-launcher-argparity.md,.ce/pr-manifests/ce-351-queue-daemon-relocation.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce-366-main-head-resolver.md,.ce/pr-manifests/ce-381-automerge-decide-pathset.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce-appgrant-failclosed.md,.ce/pr-manifests/ce-autorelease-phase-a.md,.ce/pr-manifests/ce-belt-claim-path-fix.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce-brain-deterministic-citations.md,.ce/pr-manifests/ce-brain-eval-harness.md,.ce/pr-manifests/ce-brain-hydration-launch.md,.ce/pr-manifests/ce-brownfield-detector-loosen.md,.ce/pr-manifests/ce-confidentiality-pre-push-guard.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce-egress-broker.md,.ce/pr-manifests/ce-fleet-status.md,.ce/pr-manifests/ce-forge-rebase-dismiss-fix.md,.ce/pr-manifests/ce-fwheel1-author-gate.md,.ce/pr-manifests/ce-g9-brain-smoke.md,.ce/pr-manifests/ce-gate-daemon-systemd.md,.ce/pr-manifests/ce-grading-spine-first.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce-hook-apisurface-classifier.md,.ce/pr-manifests/ce-integrator-daemon.md,.ce/pr-manifests/ce-integrator-discovery-fix.md,.ce/pr-manifests/ce-integrator-reviews-fix.md,.ce/pr-manifests/ce-l3-triage-ready-queue-p0.md,.ce/pr-manifests/ce-n2-triage-pickup-filter.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce-openbao-vps-standup.md,.ce/pr-manifests/ce-preflight-before-push-ssot.md,.ce/pr-manifests/ce-recipe-signer-parameterize.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce-release-signing-key-id.md,.ce/pr-manifests/ce-republish-020-rootv1.md,.ce/pr-manifests/ce-republish-020-with71.md,.ce/pr-manifests/ce-review-daemon.md,.ce/pr-manifests/ce-search-api-headroom.md,.ce/pr-manifests/ce-support-agent-p0.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce-triage-autolabel.md,.ce/pr-manifests/ce020-release.md,.ce/pr-manifests/ce103-s2-posture.md,.ce/pr-manifests/ce104-review-gate-design.md,.ce/pr-manifests/ce105-s1-deploy-classifier.md,.ce/pr-manifests/ce107b-sec7-forge-guard.md,.ce/pr-manifests/ce109-ring1-fs-mediation.md,.ce/pr-manifests/ce109-s8c-landlock-cred-deny.md,.ce/pr-manifests/ce11-suite-speed-p2.md,.ce/pr-manifests/ce11-test-tier-split.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce110-harness-adapter.md,.ce/pr-manifests/ce113-openbao-design.md,.ce/pr-manifests/ce113-openbao-golive.md,.ce/pr-manifests/ce113-openbao-p3.md,.ce/pr-manifests/ce115-wave1-controller-containment.md,.ce/pr-manifests/ce119-tasks-handoff-contract.md,.ce/pr-manifests/ce120-reviewer-triage.md,.ce/pr-manifests/ce120-wave3-reviewer-triage-wiring.md,.ce/pr-manifests/ce121-134-aarch64-wheelhouse.md,.ce/pr-manifests/ce121-aarch64.md,.ce/pr-manifests/ce122-uname-guard.md,.ce/pr-manifests/ce123-scanner-mirror.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce124-cli-shims.md,.ce/pr-manifests/ce125-runtime-provision.md,.ce/pr-manifests/ce126-app-zero-repos.md,.ce/pr-manifests/ce126-scope-target-repo.md,.ce/pr-manifests/ce127-forge-identity-bind.md,.ce/pr-manifests/ce128-backend-selector-policy.md,.ce/pr-manifests/ce128-contained-launch-proof.md,.ce/pr-manifests/ce128-dgx-runsc.md,.ce/pr-manifests/ce128-docker-runsc-plan.md,.ce/pr-manifests/ce128-launch-runner-integration.md,.ce/pr-manifests/ce128-vps-contained-herdr.md,.ce/pr-manifests/ce130-ratified-by-identity.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce132-cleanroom-install-s1.md,.ce/pr-manifests/ce133-adr0006-design.md,.ce/pr-manifests/ce135-openbao-secret-zero-broker.md,.ce/pr-manifests/ce135-openbao-standup.md,.ce/pr-manifests/ce137-identity-registry.md,.ce/pr-manifests/ce140-readme-refresh.md,.ce/pr-manifests/ce141-docs-nav-refresh.md,.ce/pr-manifests/ce147-identity-registry-dimensions.md,.ce/pr-manifests/ce148-seat-provisioning.md,.ce/pr-manifests/ce149-launcher-hermes-to-ce.md,.ce/pr-manifests/ce151-stale-review-reconcile.md,.ce/pr-manifests/ce154-autoclose.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce157-context-observability-design.md,.ce/pr-manifests/ce157-mint-broker.md,.ce/pr-manifests/ce158-trust-anchor.md,.ce/pr-manifests/ce159-brownfield-scanners.md,.ce/pr-manifests/ce160-rulesets-protection-floor.md,.ce/pr-manifests/ce162-seat-ops-ssot.md,.ce/pr-manifests/ce163-born-foreman-inject.md,.ce/pr-manifests/ce163-foreman-canon-enforced.md,.ce/pr-manifests/ce163-foreman-hard-deny.md,.ce/pr-manifests/ce163-foreman-seat-class.md,.ce/pr-manifests/ce163-foreman-warn-arm.md,.ce/pr-manifests/ce163-worker-spawn-primitive.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce164-work-sizing-floor.md,.ce/pr-manifests/ce164-work-sizing-test-loc-exclusion.md,.ce/pr-manifests/ce166-knowledge-ssot-slice1.md,.ce/pr-manifests/ce166-knowledge-ssot-slice2.md,.ce/pr-manifests/ce166-knowledge-ssot-slice3.md,.ce/pr-manifests/ce167-brain-assertion-ledger.md,.ce/pr-manifests/ce168-work-sizing.md,.ce/pr-manifests/ce173-idempotent-reinstall.md,.ce/pr-manifests/ce173-null-probe-prior-app.md,.ce/pr-manifests/ce174-stale-base-rerun.md,.ce/pr-manifests/ce176-brain-probe.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce177-knowledge-ssot-drift-ci.md,.ce/pr-manifests/ce178-brain-bootstrap.md,.ce/pr-manifests/ce185-broker-slice1.md,.ce/pr-manifests/ce185-devops-broker-adr.md,.ce/pr-manifests/ce186-g6-seat-class-enforce.md,.ce/pr-manifests/ce187-forge-triage.md,.ce/pr-manifests/ce188-belt-reviews-pickup-claim-bridge.md,.ce/pr-manifests/ce188-belt-reviews-pickup.md,.ce/pr-manifests/ce189-supersession-guard.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce192-ci-shallow-fetch.md,.ce/pr-manifests/ce194-triage-hygiene.md,.ce/pr-manifests/ce195-launch-argv-python-m.md,.ce/pr-manifests/ce196-queue-hygiene-completeness.md,.ce/pr-manifests/ce197-install-robustness.md,.ce/pr-manifests/ce197-launcher-refuse.md,.ce/pr-manifests/ce197-onboard-orchestrator.md,.ce/pr-manifests/ce197-profile-path.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce197-verify-install.md,.ce/pr-manifests/ce198-dogfood-installed-ce.md,.ce/pr-manifests/ce200-belt-lane-claim-allocation.md,.ce/pr-manifests/ce203-lease-id-length.md,.ce/pr-manifests/ce205-launch-harness.md,.ce/pr-manifests/ce206-brain-init.md,.ce/pr-manifests/ce207-channel-emission.md,.ce/pr-manifests/ce207-notify-reports.md,.ce/pr-manifests/ce207-visibility-backend.md,.ce/pr-manifests/ce207-w2prime-pty-session.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce209-deflake-seat-sentinel.md,.ce/pr-manifests/ce21-per-pr-carrier.md,.ce/pr-manifests/ce211-node24-actions.md,.ce/pr-manifests/ce213-carrier-presence-gate.md,.ce/pr-manifests/ce214-pr-open-carrier-scaffold.md,.ce/pr-manifests/ce216-deterministic-resolvers.md,.ce/pr-manifests/ce216-escalation-seam.md,.ce/pr-manifests/ce216-eviction-detection.md,.ce/pr-manifests/ce216-executor-race-guard.md,.ce/pr-manifests/ce216-integrator-phase2-resolver.md,.ce/pr-manifests/ce216-integrator-runner.md,.ce/pr-manifests/ce217-launcher-term-readiness.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce217-u2-herdr-containment-wrapper.md,.ce/pr-manifests/ce217-u3-herdr-backend.md,.ce/pr-manifests/ce217-u3live-herdr-session.md,.ce/pr-manifests/ce217-ulauncher-herdr-runsc.md,.ce/pr-manifests/ce218-belt-poller.md,.ce/pr-manifests/ce219-codex-pretooluse-hook.md,.ce/pr-manifests/ce219-codex-ring1-hookpack.md,.ce/pr-manifests/ce219-ring1-codex-enforcement.md,.ce/pr-manifests/ce220-harness-matrix.md,.ce/pr-manifests/ce221-containment-probe-failclosed.md,.ce/pr-manifests/ce221-containment-probe.md,.ce/pr-manifests/ce221-probe-gvisor-detect.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce223-clean-install-prereqs.md,.ce/pr-manifests/ce224-restore-lane-harness-row.md,.ce/pr-manifests/ce225-openbao-bringup-perms.md,.ce/pr-manifests/ce227-wave-a.md,.ce/pr-manifests/ce227-wave-b.md,.ce/pr-manifests/ce227-wave-c.md,.ce/pr-manifests/ce229-live-action-scope-guard.md,.ce/pr-manifests/ce23-s1-baseline-attestation.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce233-harden-verify-by-reaction.md,.ce/pr-manifests/ce234-credential-wall-approval.md,.ce/pr-manifests/ce235-dequeue-settle.md,.ce/pr-manifests/ce237-herdr-reach-plane-a4.md,.ce/pr-manifests/ce239-approval-wall-openbao.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce241-contained-controller-parity.md,.ce/pr-manifests/ce243-self-review-broker.md,.ce/pr-manifests/ce244-bootstrap-ssot-overlay.md,.ce/pr-manifests/ce244-worker-tier.md,.ce/pr-manifests/ce246-integrator-latest-rollup.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce249-split-relocate-and-scrub.md,.ce/pr-manifests/ce25-version-surface.md,.ce/pr-manifests/ce250-republish-s8c.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce251-republish-e3.md,.ce/pr-manifests/ce252-validate-pr-ci-parity.md,.ce/pr-manifests/ce252-validate-pr-preflight.md,.ce/pr-manifests/ce256-retire-tmux-detached-seat-launch.md,.ce/pr-manifests/ce258-stranded-pr-sweep.md,.ce/pr-manifests/ce259-worker-run.md,.ce/pr-manifests/ce260-release-artifact-parity-guard.md,.ce/pr-manifests/ce261-contained-seat-toolchain.md,.ce/pr-manifests/ce262-closes-linkage-guard.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce262-cross-repo-autoclose.md,.ce/pr-manifests/ce263-seat-restart-reliability.md,.ce/pr-manifests/ce272-surfaces-manifest-ssot.md,.ce/pr-manifests/ce273-surfaces-manifest-consistent.md,.ce/pr-manifests/ce274-digest-pin-images.md,.ce/pr-manifests/ce275-vps-image-pin.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce276-surfaces-check-updates.md,.ce/pr-manifests/ce278-fleet-rollout.md,.ce/pr-manifests/ce28-web-control-ui-adr.md,.ce/pr-manifests/ce280-ci-build-args-from-surfaces.md,.ce/pr-manifests/ce283-docs-internal-tree-guard.md,.ce/pr-manifests/ce285-egress-broker-socket-activation.md,.ce/pr-manifests/ce289-sopeercred-attestation.md,.ce/pr-manifests/ce293-activate-belt-daemon.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce297-claude-code-adapter.md,.ce/pr-manifests/ce298-human-contributor-role.md,.ce/pr-manifests/ce299-trust-tier-criteria.md,.ce/pr-manifests/ce300-orphan-container-fix.md,.ce/pr-manifests/ce316-doc-autogen-cli-reference.md,.ce/pr-manifests/ce322-doc-autogen-schema-reference.md,.ce/pr-manifests/ce323-install-shell-fix.md,.ce/pr-manifests/ce337-rereview-phase2-autowire.md,.ce/pr-manifests/ce38-work-claims.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce43-seat-reaper.md,.ce/pr-manifests/ce45-journey-cockpit.md,.ce/pr-manifests/ce55-pickup-search-type-qualifier.md,.ce/pr-manifests/ce57-datebomb-fix.md,.ce/pr-manifests/ce63-d1-contributing-guide.md,.ce/pr-manifests/ce65-changelog-0-2-0.md,.ce/pr-manifests/ce69-mirror-rescope.md,.ce/pr-manifests/ce71-userlevel-apply.md,.ce/pr-manifests/ce80-republish-233.md,.ce/pr-manifests/ce80-republish-post238.md,.ce/pr-manifests/ce80-republish-post241.md,.ce/pr-manifests/ce80-republish-s2.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce80-signed-publish.md,.ce/pr-manifests/ce81-trustroot-fingerprint-anchor.md,.ce/pr-manifests/ce82-lane-venv-docs.md,.ce/pr-manifests/ce83-issue-intake-role-contract.md,.ce/pr-manifests/ce84-identity-semantics-doc.md,.ce/pr-manifests/ce85-e3-adoption-apply.md,.ce/pr-manifests/ce85-plain-join.md,.ce/pr-manifests/ce88-apply-driver.md,.ce/pr-manifests/ce88-live-forge-applydriver.md,.ce/pr-manifests/ce88-pco-release-pane-terminalize.md,.ce/pr-manifests/ce89-controller-seat-exclusivity-doc.md,.ce/pr-manifests/ce89-spawn-repo-root.md
confidential ce-ops# ticket reference|.ce/pr-manifests/ce9-role-boundary-design.md,.ce/pr-manifests/ce94-127-forge-identity.md,.ce/pr-manifests/ce94-finegrained-pat.md,.ce/pr-manifests/ce95-seats-ls.md,.ce/pr-manifests/ce97-test-notification-hygiene.md,.ce/pr-manifests/ce98-pco-release-collision.md,.ce/pr-manifests/ce99-p1-devops.md,.ce/pr-manifests/ceops94-finegrained-bootstrap.md,.ce/pr-manifests/ceops95-phase1.md,.ce/pr-manifests/codex-ce142-computer-use-authority-envelope.md,.ce/pr-manifests/codex-ce145-playbooks-scaffold.md,.ce/pr-manifests/codex-ce171-forge-plan-protection-floor.md
confidential ce-ops# ticket reference|.ce/pr-manifests/codex-ce172-windows-wsl2-remediation.md,.ce/pr-manifests/codex-ce177-brain-drift-ci.md,.ce/pr-manifests/codex-ce182-search-pickup-feed.md,.ce/pr-manifests/codex-drive-bridge.md,.ce/pr-manifests/d3-mcp-fix.md,.ce/pr-manifests/f6-phase0-restamp.md,.ce/pr-manifests/feat-ce207-w1-visibility-backend.md
confidential ce-ops# ticket reference|.ce/pr-manifests/feat-runsc-detached-launch-mode.md,.ce/pr-manifests/feat-vps-seat-validator-venv.md,.ce/pr-manifests/fix-ce-ops-328-brownfield-forge-identity.md,.ce/pr-manifests/fix-ce315-b1-anchor-footgun.md,.ce/pr-manifests/fix-publish-answers-schema.md,.ce/pr-manifests/g2f-spawn-hardening.md,.ce/pr-manifests/ga2-runner-ring1-impl.md,.ce/pr-manifests/livedriver-uv-mirror.md,.ce/pr-manifests/livedriver-uv-verify-fix.md
confidential ce-ops# ticket reference|.ce/pr-manifests/seat-sentinels.md,.ce/pr-manifests/sentinel-readiness-fix.md,.ce/pr-manifests/site-v8-factory-floor.md,.ce/pr-manifests/track-b-openbao-completion.md,.ce/pr-manifests/u1-herdr-ce-side-scaffold.md,.ce/pr-manifests/v020-bump.md,.ce/pr-manifests/v35-roadmap-plan.md,.ce/pr-manifests/v35e-prime-wave.md,.ce/pr-manifests/w3-evidence-bundle-press-merge.md,.ce/reference/cli.generated.md
confidential ce-ops# ticket reference|.ce/reference/schemas.generated.md,.claude/agents/README.md,.claude/agents/reviewer.md,.github/scripts/ceops_autoclose.py,.github/workflows/ce-ops-autoclose.yml,.github/workflows/ce-ops-triage-queue.yml,.github/workflows/validate.yml,BUILD_NOTE.md,deploy/dgx-controller-runsc/DESIGN.md,deploy/dgx-controller-runsc/README.md,deploy/dgx-controller-runsc/ce-controller-gh-guard.sh,deploy/systemd/ce-belt-daemon-observed-run.md
confidential ce-ops# ticket reference|deploy/vps-runsc/Dockerfile,deploy/vps-runsc/README.md,docs/architecture/ADR-0006-derived-artifacts-out-of-trust-path.md,docs/architecture/HERDR_GOVERNANCE_BOUNDARY.md,docs/architecture/cockpit.md,docs/architecture/egress-broker.md,docs/architecture/seat-sentinel-contract.md,docs/architecture/tasks-handoff-contract.md,docs/architecture/work-claim-locks.md,docs/assets/ce-logo-v2-weldarm.svg,docs/contracts/README.md,docs/contracts/brownfield-adoption.md
confidential ce-ops# ticket reference|docs/contracts/computer-use-authority-envelope.md,docs/contracts/computer-use-worker-harness.md,docs/contracts/devops-privileged-action-broker.md,docs/contracts/installer.md,docs/contracts/plain-join.md,docs/contracts/runtime-policy.md,docs/decisions/0005-openbao-secret-identity-backend.md,docs/decisions/ADR-0007-egress-gateway-publish-broker.md,docs/decisions/ADR-0008-web-control-ui.md,docs/decisions/ADR-0009-bounded-work-units-small-batches.md,docs/decisions/ADR-0010-take-app-wheel-out-of-authored-prs.md,docs/decisions/ADR-0011-devops-privileged-action-broker.md
confidential ce-ops# ticket reference|docs/decisions/ADR-0012-openbao-micro-unit-standup.md,docs/devops/openbao-approval-wall-arming.md,docs/devops/openbao-operator-bringup.md,docs/devops/openbao-production-golive.md,docs/downloads/0.2.0/scanners/scanner-mirror.fragment.yaml,docs/security/ce234-approval-capability-wall.md,examples/reviewer-triage/reviewer-registry.yaml,playbooks/README.md,playbooks/author/envelope.template.yml,playbooks/author/workflow.ce.yml,playbooks/computer-use-ticket/envelope.template.yml,playbooks/computer-use-ticket/workflow.ce.yml
confidential ce-ops# ticket reference|playbooks/controller/briefs/annoyance-to-tool.md,playbooks/controller/briefs/dispatch.md,playbooks/controller/duties.yaml,playbooks/controller/envelope.template.yml,playbooks/controller/runbooks/controller-standup.md,playbooks/controller/workflow.ce.yml,playbooks/reviewer/README.md,playbooks/reviewer/envelope.template.yml,playbooks/reviewer/harness.md,playbooks/reviewer/workflow.ce.yml,site-archive/README.md,site-archive/index-v7-the-choice.html,specs/006-retire-speckit-principle-x/tasks.md,tools/egress-broker/README.md
confidential ce-ops# ticket reference|tools/egress-broker/apps.example.json,tools/egress-broker/ce_egress_self_push_broker.py,tools/egress-broker/ce_egress_self_review_broker.py,tools/egress-broker/egress_broker/config.py,tools/egress-broker/egress_broker/minter.py,tools/egress-broker/egress_broker/orchestrator.py,tools/mint-broker/mint_broker/binding.py,tools/mint-broker/mint_broker/config.py,tools/mint-broker/mint_broker/service.py,validators/creator_engine_validator/_versions.py,validators/creator_engine_validator/brain_bootstrap.py,validators/creator_engine_validator/brain_recall_surface.py
confidential ce-ops# ticket reference|validators/creator_engine_validator/ce_cli.py,validators/creator_engine_validator/ce_onboard.py,validators/creator_engine_validator/checks/ce_computer_use_authority_envelope.py,validators/creator_engine_validator/checks/ce_playbook_format.py,validators/creator_engine_validator/checks/handoff_schema.py,validators/creator_engine_validator/checks/harness_seat_contract.py,validators/creator_engine_validator/checks/pane_registry.py,validators/creator_engine_validator/checks/path_manifest_fidelity.py,validators/creator_engine_validator/checks/pr_closes_linkage.py,validators/creator_engine_validator/checks/seat_event.py,validators/creator_engine_validator/checks/skill_antidrift_guard.py,validators/creator_engine_validator/checks/surfaces_manifest.py
confidential ce-ops# ticket reference|validators/creator_engine_validator/checks/worker_tier_contract.py,validators/creator_engine_validator/cli.py,validators/creator_engine_validator/contained_controller_parity.py,validators/creator_engine_validator/containment_probe.py,validators/creator_engine_validator/dispatch_plan.py,validators/creator_engine_validator/doctor_runtime.py,validators/creator_engine_validator/forge/__init__.py,validators/creator_engine_validator/forge/automerge_policy.py,validators/creator_engine_validator/forge/controller_inbox.py,validators/creator_engine_validator/forge/deterministic_resolvers.py,validators/creator_engine_validator/forge/eviction_detection.py,validators/creator_engine_validator/forge/github_repo_config.py
confidential ce-ops# ticket reference|validators/creator_engine_validator/forge/integrator_belt.py,validators/creator_engine_validator/forge/integrator_executor.py,validators/creator_engine_validator/forge/integrator_runner.py,validators/creator_engine_validator/forge/re_review.py,validators/creator_engine_validator/forge/review_pickup.py,validators/creator_engine_validator/forge/ruleset.py,validators/creator_engine_validator/forge/scoped_token.py,validators/creator_engine_validator/forge/user_install_discovery.py,validators/creator_engine_validator/forge_triage.py,validators/creator_engine_validator/hook_check.py,validators/creator_engine_validator/lane_runtime.py,validators/creator_engine_validator/launch_runtime.py
confidential ce-ops# ticket reference|validators/creator_engine_validator/onboard_apply.py,validators/creator_engine_validator/onboard_apply_live.py,validators/creator_engine_validator/openbao_golive.py,validators/creator_engine_validator/openbao_p3.py,validators/creator_engine_validator/orchestrator.py,validators/creator_engine_validator/packaging_runtime.py,validators/creator_engine_validator/pco_allocator.py,validators/creator_engine_validator/pickup.py,validators/creator_engine_validator/pickup_search.py,validators/creator_engine_validator/playbook_runtime.py,validators/creator_engine_validator/reaper_executors.py,validators/creator_engine_validator/release_publish.py
confidential ce-ops# ticket reference|validators/creator_engine_validator/runner/backend.py,validators/creator_engine_validator/runner/cockpit_readmodel.py,validators/creator_engine_validator/runner/herdr_containment.py,validators/creator_engine_validator/runner/herdr_session.py,validators/creator_engine_validator/runner/notify_feed.py,validators/creator_engine_validator/runner/os_native_backend.py,validators/creator_engine_validator/schema.py,validators/creator_engine_validator/schemas/automerge-policy.schema.yaml,validators/creator_engine_validator/schemas/dispatch-record.schema.yaml,validators/creator_engine_validator/schemas/harness-seat-contract.schema.yaml,validators/creator_engine_validator/schemas/pane-registry.schema.yaml,validators/creator_engine_validator/schemas/runtime-policy.schema.yaml
confidential ce-ops# ticket reference|validators/creator_engine_validator/schemas/seat-event.schema.yaml,validators/creator_engine_validator/schemas/seat-lifecycle.schema.yaml,validators/creator_engine_validator/schemas/worker-tier-contract.schema.yaml,validators/creator_engine_validator/seat_class.py,validators/creator_engine_validator/seat_lifecycle.py,validators/creator_engine_validator/seat_pty_session.py,validators/creator_engine_validator/seat_reaper.py,validators/creator_engine_validator/seat_sentinel.py,validators/creator_engine_validator/secret_identity.py,validators/creator_engine_validator/tmux_adapter.py,validators/creator_engine_validator/v3_cli.py,validators/creator_engine_validator/v3_cockpit.py
confidential ce-ops# ticket reference|validators/creator_engine_validator/v3_forge_join.py,validators/creator_engine_validator/v3_installer.py,validators/creator_engine_validator/v3_seat_bridge.py,validators/creator_engine_validator/v3_session.py,validators/creator_engine_validator/version.py,validators/creator_engine_validator/visibility_backend.py,validators/creator_engine_validator/work_claims.py,validators/creator_engine_validator/worker_run.py,validators/creator_engine_validator/worker_spawn.py,validators/pyproject.toml,validators/tests/conftest.py,validators/tests/integration/test_belt_launch_e2e.py
confidential ce-ops# ticket reference|validators/tests/integration/test_ce_bootstrap_cli.py,validators/tests/integration/test_ce_brain_init_lane_gate.py,validators/tests/integration/test_herdr_live.py,validators/tests/integration/test_hook_check_cli.py,validators/tests/integration/test_install_bootstrap.py,validators/tests/integration/test_onboard_apply_brownfield.py,validators/tests/integration/test_pco_allocator_cli.py,validators/tests/integration/test_playbook_format_examples.py,validators/tests/integration/test_schema_packaging_wheel.py,validators/tests/integration/test_schema_path_resolution.py,validators/tests/integration/test_v1_delivery_rehearsal.py,validators/tests/unit/fixtures/ce88_live_forge/CAPTURE.md
confidential ce-ops# ticket reference|validators/tests/unit/fixtures/support_agent_zero_leak_cases.json,validators/tests/unit/test_authority_resolver.py,validators/tests/unit/test_automerge_actuator.py,validators/tests/unit/test_automerge_policy.py,validators/tests/unit/test_automerge_status.py,validators/tests/unit/test_brain_recall_surface.py,validators/tests/unit/test_carrier_gen.py,validators/tests/unit/test_ce262_parse_issue_refs.py,validators/tests/unit/test_ce_brain_init.py,validators/tests/unit/test_ce_claim_cli.py,validators/tests/unit/test_ce_lane_cli.py,validators/tests/unit/test_ce_launch_cli.py
confidential ce-ops# ticket reference|validators/tests/unit/test_ce_onboard.py,validators/tests/unit/test_ce_onboard_cli.py,validators/tests/unit/test_ce_ops_triage_queue.py,validators/tests/unit/test_ce_playbook_format.py,validators/tests/unit/test_ce_runtime_policy.py,validators/tests/unit/test_ce_worker_cli.py,validators/tests/unit/test_ceops_autoclose.py,validators/tests/unit/test_cockpit_claims.py,validators/tests/unit/test_cockpit_journey.py,validators/tests/unit/test_cockpit_peek.py,validators/tests/unit/test_cockpit_readmodel.py,validators/tests/unit/test_contained_controller_parity.py
confidential ce-ops# ticket reference|validators/tests/unit/test_contained_launch_proof.py,validators/tests/unit/test_containment_probe.py,validators/tests/unit/test_conveyor.py,validators/tests/unit/test_deterministic_resolvers.py,validators/tests/unit/test_devops_privileged_action_broker.py,validators/tests/unit/test_dispatch_plan.py,validators/tests/unit/test_doctor_onboard_probes.py,validators/tests/unit/test_egress_broker_daemon_vault.py,validators/tests/unit/test_egress_orchestrator.py,validators/tests/unit/test_egress_review_daemon_vault.py,validators/tests/unit/test_egress_signature_policy.py,validators/tests/unit/test_egress_vault_signer.py
confidential ce-ops# ticket reference|validators/tests/unit/test_eviction_detection.py,validators/tests/unit/test_fleet_manifest_guard.py,validators/tests/unit/test_forge_triage.py,validators/tests/unit/test_gate_daemons_systemd.py,validators/tests/unit/test_harness_seat_contract.py,validators/tests/unit/test_herdr_containment.py,validators/tests/unit/test_herdr_session.py,validators/tests/unit/test_hook_check.py,validators/tests/unit/test_integration_queue_dry_run_contract.py,validators/tests/unit/test_integrator_belt.py,validators/tests/unit/test_integrator_escalation.py,validators/tests/unit/test_integrator_executor.py
confidential ce-ops# ticket reference|validators/tests/unit/test_integrator_llm_resolver.py,validators/tests/unit/test_integrator_runner.py,validators/tests/unit/test_lane_runtime.py,validators/tests/unit/test_lane_runtime_resource_bound.py,validators/tests/unit/test_lane_runtime_reviewer_venue.py,validators/tests/unit/test_launch_runtime.py,validators/tests/unit/test_launch_runtime_resource_bound.py,validators/tests/unit/test_mint_broker_binding.py,validators/tests/unit/test_mint_broker_config.py,validators/tests/unit/test_mint_broker_service.py,validators/tests/unit/test_notify_feed.py,validators/tests/unit/test_oci_image.py
confidential ce-ops# ticket reference|validators/tests/unit/test_onboard_apply.py,validators/tests/unit/test_onboard_apply_live.py,validators/tests/unit/test_onboard_apply_live_token_minter.py,validators/tests/unit/test_open_change.py,validators/tests/unit/test_orchestrator.py,validators/tests/unit/test_orchestrator_records.py,validators/tests/unit/test_orchestrator_status.py,validators/tests/unit/test_packaging_contract.py,validators/tests/unit/test_pane_registry.py,validators/tests/unit/test_path_manifest_fidelity.py,validators/tests/unit/test_pco_allocator.py,validators/tests/unit/test_pickup.py
confidential ce-ops# ticket reference|validators/tests/unit/test_playbook_runtime.py,validators/tests/unit/test_pr_closes_linkage.py,validators/tests/unit/test_public_docs_confidentiality.py,validators/tests/unit/test_public_docs_confidentiality_cli.py,validators/tests/unit/test_re_review.py,validators/tests/unit/test_release_phase_a.py,validators/tests/unit/test_release_publish.py,validators/tests/unit/test_resolve_live_config_broker.py,validators/tests/unit/test_review_pickup.py,validators/tests/unit/test_reviewer_triage_plan.py,validators/tests/unit/test_ruleset.py,validators/tests/unit/test_runner_backend.py
confidential ce-ops# ticket reference|validators/tests/unit/test_schema.py,validators/tests/unit/test_schema_packaging_completeness.py,validators/tests/unit/test_scoped_token.py,validators/tests/unit/test_seat_class.py,validators/tests/unit/test_seat_pty_session.py,validators/tests/unit/test_seat_reaper.py,validators/tests/unit/test_seat_sentinel.py,validators/tests/unit/test_secret_identity.py,validators/tests/unit/test_skill_antidrift_guard.py,validators/tests/unit/test_support_agent_p0.py,validators/tests/unit/test_support_agent_phase1.py,validators/tests/unit/test_tmux_adapter.py
confidential ce-ops# ticket reference|validators/tests/unit/test_transcript_archive.py,validators/tests/unit/test_user_install_discovery.py,validators/tests/unit/test_v1_docs_reconciliation.py,validators/tests/unit/test_v3_claim_dispatch.py,validators/tests/unit/test_v3_cli.py,validators/tests/unit/test_v3_cockpit.py,validators/tests/unit/test_v3_cockpit_journey.py,validators/tests/unit/test_v3_installer.py,validators/tests/unit/test_v3_seat_bridge.py,validators/tests/unit/test_version_boundary.py,validators/tests/unit/test_version_surface.py,validators/tests/unit/test_visibility_backend.py
confidential ce-ops# ticket reference|validators/tests/unit/test_vps_runsc_image.py,validators/tests/unit/test_vps_runsc_launcher.py,validators/tests/unit/test_wheelhouse_built_surface.py,validators/tests/unit/test_work_claims.py,validators/tests/unit/test_work_sizing_floor.py,validators/tests/unit/test_worker_run.py,validators/tests/unit/test_worker_spawn.py,validators/tests/unit/test_worker_tier_contract.py,validators/tests/unit/test_workflow_merge_group_trigger.py
confidential internal codename skynet|.ce/changelog/ce-348-adr-0013-promote.md,validators/tests/unit/test_public_docs_confidentiality.py
internal VPS IP|deploy/queue-daemon/RELOCATION.md,deploy/queue-daemon/ce-queue-daemon.service
internal hosting-provider name|.ce/changelog/ce113-openbao-golive.md,.ce/changelog/ce249-redact-live-infra.md,.ce/pr-manifests/ce113-openbao-golive.md,validators/tests/unit/test_fleet_manifest_guard.py,validators/tests/unit/test_public_docs_confidentiality_cli.py
internal seat-login marker|.ce/brain/assertions.yaml,.ce/changelog/ce85-plain-join.md,.ce/changelog/ceops94-finegrained-bootstrap.md,.ce/coordination.yml,.ce/pr-manifests/ce38-work-claims.md,.ce/reference/cli.generated.md,.github/CODEOWNERS,deploy/queue-daemon/RELOCATION.md,deploy/queue-daemon/ce-queue-daemon.service,deploy/systemd/README.md,deploy/systemd/ce-belt-daemon-observed-run.md,deploy/systemd/ce-egress-broker.socket
internal seat-login marker|deploy/systemd/ce-egress-self-review.socket,deploy/systemd/ce-review-pickup-daemon.service,deploy/systemd/install-gate-daemons-systemd.sh,docs/contracts/devops-privileged-action-broker.md,docs/contracts/plain-join.md,docs/decisions/ADR-0009-bounded-work-units-small-batches.md,docs/decisions/ADR-0010-take-app-wheel-out-of-authored-prs.md,docs/decisions/ADR-0011-devops-privileged-action-broker.md,docs/decisions/ADR-0012-openbao-micro-unit-standup.md,docs/devops/openbao-operator-bringup.md,docs/devops/openbao-production-golive.md,docs/devops/openbao/secret-migration-inventory.tsv
internal seat-login marker|examples/reviewer-triage/eligible.yaml,examples/reviewer-triage/missing-access.yaml,examples/reviewer-triage/no-available-reviewer.yaml,examples/reviewer-triage/privileged-requires-source.yaml,examples/reviewer-triage/same-controller-tier1-reject.yaml,examples/reviewer-triage/same-host-tier2-valid.yaml,examples/reviewer-triage/same-human-reject.yaml,examples/reviewer-triage/tier4-release-valid.yaml,examples/reviewer-triage/uncontained-reject.yaml,examples/reviewer-triage/unresolved-identity-reject.yaml,tools/egress-broker/apps.example.json,validators/creator_engine_validator/ce_cli.py
internal seat-login marker|validators/creator_engine_validator/contained_controller_parity.py,validators/creator_engine_validator/forge/controller_inbox.py,validators/creator_engine_validator/forge/review_pickup.py,validators/creator_engine_validator/work_claims.py,validators/tests/integration/test_belt_launch_e2e.py,validators/tests/integration/test_hook_check_cli.py,validators/tests/unit/fixtures/ce88_live_forge/CAPTURE.md,validators/tests/unit/fixtures/ce88_live_forge/user_response_finegrained.txt,validators/tests/unit/fixtures/support_agent_zero_leak_cases.json,validators/tests/unit/test_ce_brain_drift.py,validators/tests/unit/test_ce_claim_cli.py,validators/tests/unit/test_ce_launch_cli.py
internal seat-login marker|validators/tests/unit/test_ce_onboard.py,validators/tests/unit/test_ce_ops_triage_queue.py,validators/tests/unit/test_ce_worker_cli.py,validators/tests/unit/test_cockpit_claims.py,validators/tests/unit/test_contained_controller_parity.py,validators/tests/unit/test_containment_status.py,validators/tests/unit/test_controller_inbox.py,validators/tests/unit/test_devops_privileged_action_broker.py,validators/tests/unit/test_egress_broker_daemon_vault.py,validators/tests/unit/test_egress_commit_facts.py,validators/tests/unit/test_egress_config.py,validators/tests/unit/test_egress_host_broker.py
internal seat-login marker|validators/tests/unit/test_egress_orchestrator.py,validators/tests/unit/test_egress_policy.py,validators/tests/unit/test_egress_review_daemon_vault.py,validators/tests/unit/test_egress_signature_policy.py,validators/tests/unit/test_egress_vault_signer.py,validators/tests/unit/test_forge_triage.py,validators/tests/unit/test_gate_daemons_systemd.py,validators/tests/unit/test_hook_check.py,validators/tests/unit/test_lane_runtime.py,validators/tests/unit/test_launch_runtime.py,validators/tests/unit/test_onboard_apply.py,validators/tests/unit/test_onboard_apply_live.py
internal seat-login marker|validators/tests/unit/test_openbao_golive.py,validators/tests/unit/test_openbao_p3.py,validators/tests/unit/test_pane_registry.py,validators/tests/unit/test_pickup.py,validators/tests/unit/test_publish_gate.py,validators/tests/unit/test_re_review.py,validators/tests/unit/test_review_pickup.py,validators/tests/unit/test_reviewer_triage_plan.py,validators/tests/unit/test_seat_reaper.py,validators/tests/unit/test_secret_identity.py,validators/tests/unit/test_v3_cli.py,validators/tests/unit/test_v3_installer.py
internal seat-login marker|validators/tests/unit/test_work_claims.py,validators/tests/unit/test_worker_spawn.py,validators/tests/unit/test_worker_tier_contract.py
"""


def _allowed_offense_reason(rel: str) -> str:
    if rel.startswith("docs/"):
        return "Pre-existing docs debt already governed by the public-doc confidentiality ratchet."
    if rel.startswith("validators/tests/"):
        return "Pre-existing validator test fixture/reference uses synthetic or asserted marker text."
    if rel.startswith("validators/"):
        return "Pre-existing validator source or schema text references private-tracker marker classes."
    if rel.startswith(".ce/"):
        return "Pre-existing CE metadata history references private-tracker or seat marker classes."
    if rel.startswith((".github/", "deploy/", "tools/", "examples/", "playbooks/", "site-archive/", ".claude/", "specs/")):
        return "Pre-existing operational/config fixture text references governed internal marker classes."
    return "Pre-existing tracked text baseline reference; value not recorded in the allowlist."


def _parse_allowed_offenses() -> dict[tuple[str, str], str]:
    allowed: dict[tuple[str, str], str] = {}
    for raw in _ALLOWED_OFFENSE_ROWS.strip().splitlines():
        label, rels = raw.split("|", 1)
        for rel in rels.split(","):
            allowed[(rel, label)] = _allowed_offense_reason(rel)
    return allowed


ALLOWED_OFFENSES = _parse_allowed_offenses()

# This module file must not be scanned: it names the forbidden patterns by
# design.
_SELF = Path(__file__).resolve()
_SELF_REL = "validators/creator_engine_validator/public_docs_confidentiality.py"


class ConfidentialityScanError(Exception):
    """A scan-surface or file-read failure that must fail the check."""


def repo_root() -> Path:
    """Repo root: three parents up from this module.

    ``validators/creator_engine_validator/public_docs_confidentiality.py`` ->
    ``<repo>``.
    """
    return _SELF.parents[2]


def _tracked_repo_paths(root: Path) -> list[str]:
    """Return tracked repo-relative paths, failing closed if git cannot answer."""
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ConfidentialityScanError(f"could not enumerate tracked files: {exc}") from exc
    return [rel for rel in proc.stdout.decode("utf-8", errors="replace").split("\0") if rel]


def _is_binary_file(path: Path) -> bool:
    """True for binary files that are outside this text-only scan."""
    return BINARY_SENTINEL in path.read_bytes()


def _is_regular_file(path: Path) -> bool:
    """True only for regular files, failing closed on stat errors."""
    return stat.S_ISREG(path.stat().st_mode)


def public_repo_text_files(*, repo_root: Path | None = None) -> list[Path]:
    """All tracked text files in the public repository, excluding this module."""
    root = (repo_root or globals()["repo_root"]()).resolve()
    files: list[Path] = []
    for rel in sorted(_tracked_repo_paths(root)):
        path = root / rel
        if rel == _SELF_REL or path.resolve() == _SELF:
            continue
        try:
            if not _is_regular_file(path):
                continue
            if _is_binary_file(path):
                continue
        except OSError as exc:
            raise ConfidentialityScanError(f"{rel}: unreadable file: {exc}") from exc
        files.append(path)
    return files


def display_rel(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _frontmatter_line_numbers(lines: list[str]) -> frozenset[int]:
    """Return 1-based frontmatter line numbers, or empty on ambiguity."""
    if not lines or lines[0] != "---":
        return frozenset()
    try:
        end = lines.index("---", 1)
    except ValueError:
        return frozenset()
    return frozenset(range(1, end + 2))


def _is_generated_manifest_boilerplate(line: str, stem: str) -> bool:
    return line == (
        "This per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`) lists the "
        "closed authorized path-set for this PR. CI runs "
        "`verify-path-manifest --base <sha> --manifest-dir .ce/pr-manifests "
        f"--head-ref {stem}` and requires this PR's `base..HEAD` diff to equal "
        "exactly the authorized path-set below; this carrier lists itself."
    )


def _is_structural_carrier_ticket_ref(
    *, rel: str, lineno: int, line: str, label: str, lines: list[str]
) -> bool:
    """Allow only generated carrier metadata ticket refs, fail-closed."""
    if label not in TICKET_REF_LABELS:
        return False

    path = Path(rel)
    stem = path.stem
    frontmatter = _frontmatter_line_numbers(lines)

    if rel.startswith(".ce/changelog/") and path.suffix == ".md":
        issue_lines = [idx for idx, text in enumerate(lines, start=1) if _CHANGELOG_ISSUE_LINE.fullmatch(text)]
        slug_lines = [idx for idx, text in enumerate(lines, start=1) if text == f"slug: {stem}"]
        if (
            lineno in frontmatter
            and line == f"slug: {stem}"
            and slug_lines == [lineno]
        ):
            return True
        return (
            lineno in frontmatter
            and _CHANGELOG_ISSUE_LINE.fullmatch(line) is not None
            and issue_lines == [lineno]
        )

    if rel.startswith(".ce/pr-manifests/") and path.suffix == ".md":
        header_lines = [
            idx for idx, text in enumerate(lines, start=1) if _PR_MANIFEST_HEADER_LINE.fullmatch(text)
        ]
        if (
            lineno == 1
            and _PR_MANIFEST_HEADER_LINE.fullmatch(line) is not None
            and header_lines == [lineno]
        ):
            return True
        if line in {
            f".ce/changelog/{stem}.md",
            f".ce/pr-manifests/{stem}.md",
        }:
            return True
        return _is_generated_manifest_boilerplate(line, stem)

    return False


def offenses(path: Path, *, repo_root: Path) -> list[str]:
    """Return ``"<rel>:<line> [<label>] <line-text>"`` for each offending line."""
    rel = display_rel(path, repo_root=repo_root)
    hits: list[str] = []
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ConfidentialityScanError(f"{rel}: unreadable file: {exc}") from exc
    if BINARY_SENTINEL in raw:
        return []
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    for lineno, line in enumerate(lines, start=1):
        for label, pattern in FORBIDDEN_PATTERNS:
            try:
                matched = pattern.search(line)
            except Exception as exc:  # pragma: no cover - exercised by monkeypatch
                raise ConfidentialityScanError(
                    f"{rel}:{lineno}: forbidden pattern failed for {label}: {exc}"
                ) from exc
            if matched:
                if _is_structural_carrier_ticket_ref(
                    rel=rel,
                    lineno=lineno,
                    line=line,
                    label=label,
                    lines=lines,
                ):
                    continue
                hits.append(f"{rel}:{lineno} [{label}] {line.strip()}")
    return hits


def _offense_key(formatted: str) -> tuple[str, str] | None:
    """Extract ``(relpath, token-class)`` from an offense formatter line."""
    try:
        rel, rest = formatted.split(":", 1)
        label = rest.split("[", 1)[1].split("]", 1)[0]
    except (IndexError, ValueError):
        return None
    return rel, label


def _scan_error(rel: str, message: str) -> str:
    return f"{rel}:0 [scan error] {message}"


def scan_offenses(*, repo_root: Path | None = None) -> list[str]:
    """Scan the whole tracked text surface, honouring explicit baseline entries.

    Returns one formatted line per non-allowlisted offending line.
    """
    root = (repo_root or globals()["repo_root"]()).resolve()
    offenders: list[str] = []
    try:
        files = public_repo_text_files(repo_root=root)
    except ConfidentialityScanError as exc:
        return [_scan_error(".", str(exc))]
    if not files:
        return [_scan_error(".", "tracked text scan found no files")]
    for path in files:
        rel = path.resolve().relative_to(root).as_posix()
        try:
            hits = offenses(path, repo_root=root)
        except ConfidentialityScanError as exc:
            offenders.append(_scan_error(rel, str(exc)))
            continue
        for hit in hits:
            key = _offense_key(hit)
            if key is not None and key in ALLOWED_OFFENSES:
                continue
            offenders.append(hit)
    return offenders


def internal_tree_files(root: Path, *, repo_root: Path) -> frozenset[str]:
    """All files below an internal public-doc tree, repo-root relative."""
    if not root.exists():
        return frozenset()
    return frozenset(
        display_rel(path, repo_root=repo_root)
        for path in root.rglob("*")
        if path.is_file()
    )


def internal_tree_violations(*, repo_root: Path | None = None) -> tuple[list[str], list[str]]:
    """Return ``(unreviewed, stale_exceptions)`` for the guarded internal trees.

    ``unreviewed`` are net-new files in ``docs/operations/**`` or
    ``docs/delivery/**`` not on the exception ratchet (these must be moved out
    of the served tree or deliberately added). ``stale_exceptions`` are listed
    files that no longer exist (these must be removed so the list only shrinks).
    """
    root = (repo_root or globals()["repo_root"]()).resolve()
    unreviewed: list[str] = []
    stale: list[str] = []
    for root_rel, known_exceptions in INTERNAL_GUARDED_TREES:
        actual = internal_tree_files(root / root_rel, repo_root=root)
        unreviewed.extend(sorted(actual - known_exceptions))
        stale.extend(sorted(known_exceptions - actual))
    return unreviewed, stale


def run(paths: list[Path] | None = None) -> CheckResult:
    """Standalone-check entrypoint for the CLI.

    ``paths`` is accepted for signature parity with other checks; the rule
    always scans the canonical public-doc surface rooted at the repo root, so
    the argument is advisory only (the first path, if a repo root, is used).
    """
    root: Path | None = None
    if paths:
        first = paths[0].resolve()
        if (first / "docs").is_dir() or (first / ".git").exists():
            root = first
    errors: list[ValidationError] = []

    # 1) Confidential ce-ops# / internal-host pattern scan.
    for line in scan_offenses(repo_root=root):
        rel = line.split(":", 1)[0]
        if "[scan error]" in line:
            errors.append(
                make_error(
                    code="CE-CONFIDENTIALITY-SCAN",
                    path=rel,
                    field="tracked text scan",
                    message=f"confidentiality scan failed closed: {line}.",
                    contract=CONTRACT,
                )
            )
            continue
        errors.append(
            make_error(
                code="CE-CONFIDENTIALITY",
                path=rel,
                field="public-doc line",
                message=(
                    f"public doc leaks a confidential/internal reference: {line}. "
                    "Remove the reference (product-lens rewrite). "
                    f"{REMINDER}"
                ),
                contract=CONTRACT,
            )
        )

    # 2) Internal-tree guard (ce-ops#283): no net-new docs/operations or
    #    docs/delivery files in the public tree, and no stale ratchet entries.
    unreviewed, stale = internal_tree_violations(repo_root=root)
    for rel in unreviewed:
        errors.append(
            make_error(
                code="CE-INTERNAL-TREE",
                path=rel,
                field="net-new internal file",
                message=(
                    "net-new internal file in the public docs tree; move it out "
                    "of the served docs tree, or deliberately add it to the "
                    "ce-ops#283 exception ratchet. "
                    f"{REMINDER}"
                ),
                contract=CONTRACT,
            )
        )
    for rel in stale:
        errors.append(
            make_error(
                code="CE-INTERNAL-TREE",
                path=rel,
                field="stale exception",
                message=(
                    "exception ratchet lists a file that no longer exists; the "
                    "list may only shrink, so remove this stale entry."
                ),
                contract=CONTRACT,
            )
        )
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
