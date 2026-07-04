"""Pure conveyor daemon core for harvest-to-PR automation.

The daemon defaults to disarmed dry-run planning. Armed execution requires all
source-host mutation seams to be injected by the caller.
"""

from __future__ import annotations

import dataclasses
import json
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .conveyor import (
    DEFAULT_VALIDATE_COMMAND,
    ConveyorGitPhase,
    ConveyorBundleLandingResult,
    ConveyorCommandResult,
    ConveyorHarvestResult,
    ConveyorHarvestSpec,
    GitRunner,
    git_env_for_phase,
    land_bundle,
    prepare_harvest,
    validation_sandbox_spec_from_command,
)
from .pickup_payload_schema import DiscoveryPayloadRejected, validate_discovery_payload
from .daemon_lease import DaemonLease
from .checks.path_manifest_fidelity import branch_slug, extract_manifest_paths_from_file
from .forge.daemon_allocation import (
    DaemonAllocationError,
    DaemonPathAllocation,
    DaemonPathAllocator,
    DaemonPathReceipt,
)
from .validation_sandbox_receipt import ValidationSandboxReceiptIssuer
from .validation_sandbox_runner import (
    DEFAULT_POLICY_PATH as DEFAULT_VALIDATION_SANDBOX_POLICY_PATH,
    ValidationSandboxContainerRun,
    run_validation_sandbox_in_container,
)


DiscoveryRunner = Callable[[], Iterable["ConveyorDaemonItem | Mapping[str, Any]"]]
GhRunner = Callable[[Sequence[str], Path], ConveyorCommandResult | tuple[int, str, str]]
ValidateRunner = Callable[
    [Sequence[str], Path, Mapping[str, str] | None],
    ConveyorCommandResult | tuple[int, str, str],
]
PrepareRunner = Callable[..., ConveyorHarvestResult]
LandRunner = Callable[..., ConveyorBundleLandingResult]
NowRunner = Callable[[], str]
LedgerWriter = Callable[["ConveyorDaemonLedgerRecord"], None]
LogRunner = Callable[[str], None]
ValidationSandboxRunner = Callable[..., ValidationSandboxContainerRun]


PLAN_ACTIONS = ("prepare-harvest", "land-bundle", "push", "pr-open")
_PUBLISH_TRANSPORT_CONFIG_PATTERN = (
    r"^([cC][oO][rR][eE]\.[hH][oO][oO][kK][sS][pP][aA][tT][hH]|"
    r"[cC][rR][eE][dD][eE][nN][tT][iI][aA][lL]\.[hH][eE][lL][pP][eE][rR]|"
    r"[uU][rR][lL]\..*\.[iI][nN][sS][tT][eE][aA][dD][oO][fF])$"
)

# base and remote are pinned at the ConveyorDaemon level (mirrors
# validate_command below) rather than being read from an untrusted discovery
# payload. Both values flow into a *bare/positional* git argv slot
# (``git rebase <base>``, ``git push <remote> ...``) that git reinterprets as
# an option when the value starts with ``-`` (e.g. ``--exec=<cmd>`` on
# rebase) or as a transport-helper invocation for values shaped like
# ``ext::<cmd>`` (on push's <repository> positional). A compromised/malicious
# discovery payload must never be able to reach either sink.
DEFAULT_BASE = "origin/main"
DEFAULT_REMOTE = "origin"

# --- Trust boundary for filesystem paths -----------------------------------
#
# Raw discovery mappings are DATA describing only branch/issue/PR text. They
# must never hand the daemon execution CONTROL over *where on the filesystem*
# git operates. ConveyorDaemonItem instances may still carry daemon-allocated
# filesystem paths that reach git argv or become a git ``cwd``:
#
#   * ``bundle_path`` is passed as a bare positional to
#     ``git bundle verify <bundle>`` and ``git fetch <bundle> ...``
#     (conveyor.land_bundle). A value shaped like ``ext::sh -c '<cmd>'``
#     makes ``git fetch`` invoke an arbitrary transport-helper command
#     (RCE), independent of whatever bytes happen to live at that literal
#     path (``git bundle verify`` only checks the bundle is well-formed; it
#     does not constrain the *name* used to reach it).
#   * ``repo_path`` / ``worktree_path`` are used as the ``cwd`` for every
#     git/gh subprocess the daemon runs for an item (prepare, land, push,
#     pr-open). Even with ``remote``/``base`` pinned to trusted literal
#     strings, a cwd pointed at an attacker-staged directory can carry a
#     ``.git/config`` that redefines what those trusted literal names
#     *resolve to* (e.g. ``[remote "origin"] url = ext::sh -c '<cmd>'``),
#     which is RCE that bypasses the remote/base pin entirely.
#
# The item-path fix is confinement: every item path is resolved (symlinks +
# ``..`` collapsed) and REJECTED, fail-closed, unless it resolves under a
# daemon-pinned trusted root. This single invariant blocks both
# directory-redirection (an absolute path entirely outside the trusted tree)
# and ``..``-traversal (a path that starts under the root but walks back out).
# ``bundle_path`` additionally gets the same argv-gadget shape rejection as
# base/remote/validate_command below, as belt-and-suspenders: a confined
# *filename* still shouldn't be ``ext::``-shaped.
#
# There is no safe default trusted root (unlike base/remote, "no config
# supplied" cannot fall back to something world-writable like ``/tmp``), so
# ``repo_root``/``bundle_root`` are REQUIRED constructor arguments when the
# daemon is armed, exactly like the other armed-mode seams below.
#
# Confinement alone is a check-then-use race (CWE-367/TOCTOU) unless the
# *resolved* path is what actually gets used afterwards: the harvest/
# validate/land/push/pr-open sequence for one item spans a real subprocess
# (validate-pr can run up to 600s), during which an attacker who staged a
# legitimate-looking path could swap it for a symlink into an
# attacker-controlled repo. ``_process_armed`` therefore captures the
# resolved ``Path`` that ``_confine_path`` returns for each of
# bundle_path/repo_path/worktree_path and rebuilds the item
# (``dataclasses.replace``) around those resolved values *before* any
# prepare/land/push/pr-open call, so every downstream git/gh cwd or argv
# uses the realpath validated under root at check-time -- a later swap of
# the original path has no effect on what the daemon touches.


@dataclass(frozen=True)
class ConveyorDaemonItem:
    """One discovered completed branch ready for conveyor processing."""

    branch: str
    worktree_path: Path | None = None
    bundle_path: Path | None = None
    repo_path: Path | None = None
    base: str = "origin/main"
    issue: str = "ce-conveyor"
    title: str = "Conveyor harvest"
    kind: str = "changed"
    scope: str = "conveyor harvest"
    body: str = "- Prepared conveyor harvest."
    declared_work_class: str = "story"
    carrier_date: str | None = None
    rebase: bool = True
    refresh_base: bool = True
    allow_dirty_validation: bool = True
    remote: str = "origin"
    pr_title: str | None = None
    pr_body: str | None = None
    pr_base: str | None = None
    identity: str | None = None
    allocation_receipt: DaemonPathReceipt | None = None

    @classmethod
    def from_mapping(
        cls,
        payload: Mapping[str, Any],
        *,
        audit_sink: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> "ConveyorDaemonItem":
        # Raw discovery mappings cross the ADR-0004 trust boundary. Validate
        # the allowlisted data-only shape before reading any field; rejected
        # control fields such as validate_command/base/remote or local paths
        # are audited by the shared schema and never reach item construction.
        parsed = validate_discovery_payload(payload, audit_sink=audit_sink, source="conveyor_daemon")
        return cls(
            branch=parsed.branch_name,
            issue=parsed.issue,
            title=parsed.pr_title,
            kind="changed",
            scope="conveyor harvest",
            body=parsed.pr_body,
            declared_work_class="story",
            pr_title=parsed.pr_title,
            pr_body=parsed.pr_body,
        )

    @property
    def key(self) -> str:
        return self.identity or branch_slug(self.branch)

    def harvest_spec(
        self, *, carrier_date: str, validate_command: tuple[str, ...], base: str
    ) -> ConveyorHarvestSpec:
        if self.worktree_path is None:
            raise ValueError("worktree_path is required after daemon allocation")
        return ConveyorHarvestSpec(
            worktree_path=self.worktree_path,
            branch=self.branch,
            base=base,
            issue=self.issue,
            title=self.title,
            kind=self.kind,
            scope=self.scope,
            body=self.body,
            declared_work_class=self.declared_work_class,
            carrier_date=carrier_date,
            rebase=self.rebase,
            refresh_base=self.refresh_base,
            validate_command=validate_command,
            allow_dirty_validation=self.allow_dirty_validation,
        )


@dataclass(frozen=True)
class ConveyorDaemonLedgerRecord:
    """Append-only record for an armed source-host mutation attempt."""

    timestamp: str
    action: str
    path: str
    sha: str
    branch: str
    status: str
    returncode: int
    stdout: str = ""
    stderr: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "path": self.path,
            "sha": self.sha,
            "branch": self.branch,
            "status": self.status,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class ConveyorValidationLedgerBinding:
    """Side-effect ledger coordinates for validation sandbox receipts."""

    controller_id: str
    lane_id: str
    claim_ref: str
    repo_root: Path | str
    side_effect_ledger_root: Path | str
    active_work_ledger_root: Path | str


@dataclass(frozen=True)
class ConveyorDaemonItemResult:
    """Outcome for one discovered item."""

    status: str
    branch: str
    key: str
    planned_actions: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    prepare_result: ConveyorHarvestResult | None = None
    landing_result: ConveyorBundleLandingResult | None = None
    pr_url: str | None = None
    ledger_records: tuple[ConveyorDaemonLedgerRecord, ...] = ()


@dataclass(frozen=True)
class ConveyorDaemonRunResult:
    """Outcome for one discovery pass."""

    armed: bool
    discovered_count: int
    results: tuple[ConveyorDaemonItemResult, ...]
    discovery_error: str | None = None

    @property
    def planned_count(self) -> int:
        return sum(1 for result in self.results if result.status == "planned")

    @property
    def failed_count(self) -> int:
        return sum(1 for result in self.results if result.status == "failed")


class ConveyorDaemon:
    """Testable daemon loop over injected discovery and command seams."""

    def __init__(
        self,
        *,
        discovery_runner: DiscoveryRunner,
        armed: bool = False,
        git_runner: GitRunner | None = None,
        validate_runner: ValidateRunner | None = None,
        gh_runner: GhRunner | None = None,
        now: NowRunner | None = None,
        ledger_writer: LedgerWriter | None = None,
        ledger_path: Path | str | None = None,
        log_runner: LogRunner | None = None,
        prepare_runner: PrepareRunner = prepare_harvest,
        land_runner: LandRunner = land_bundle,
        validate_command: Sequence[str] | None = None,
        base: str | None = None,
        remote: str | None = None,
        repo_root: Path | str | None = None,
        bundle_root: Path | str | None = None,
        path_allocator: DaemonPathAllocator | None = None,
        daemon_lease: DaemonLease | None = None,
        receipt_issuer: ValidationSandboxReceiptIssuer | None = None,
        validation_sandbox_runner: ValidationSandboxRunner = run_validation_sandbox_in_container,
        validation_sandbox_policy_path: Path | str = DEFAULT_VALIDATION_SANDBOX_POLICY_PATH,
        validation_sandbox_command_runner: Any | None = None,
        validation_ledger_binding: ConveyorValidationLedgerBinding | None = None,
        validation_ledger_recorder: Callable[..., Any] | None = None,
    ) -> None:
        self.discovery_runner = discovery_runner
        self.armed = armed
        self.daemon_lease = daemon_lease
        self.git_runner = git_runner
        # Retained for constructor/API compatibility; armed mode injects the
        # sandbox-backed validator at prepare time instead of using this seam.
        self.validate_runner = validate_runner
        self.gh_runner = gh_runner
        self.now = now
        self.ledger_writer = ledger_writer or (_jsonl_ledger_writer(Path(ledger_path)) if ledger_path is not None else None)
        self.log_runner = log_runner
        self.prepare_runner = prepare_runner
        self.land_runner = land_runner
        self.path_allocator = path_allocator
        self.receipt_issuer = receipt_issuer
        self.validation_sandbox_runner = validation_sandbox_runner
        self.validation_sandbox_policy_path = Path(validation_sandbox_policy_path)
        self.validation_sandbox_command_runner = validation_sandbox_command_runner
        self.validation_ledger_binding = validation_ledger_binding
        self.validation_ledger_recorder = validation_ledger_recorder
        # validate_command is pinned here, at daemon construction time, and is
        # never sourced from a discovery payload (see ConveyorDaemonItem.from_mapping).
        self.validate_command: tuple[str, ...] = tuple(
            str(part) for part in (validate_command if validate_command is not None else DEFAULT_VALIDATE_COMMAND)
        )
        # base and remote are likewise pinned here, at daemon construction
        # time (trusted operator/CLI config), and are never sourced from a
        # discovery payload (see ConveyorDaemonItem.from_mapping and the
        # module docstring comment above DEFAULT_BASE). _process_armed uses
        # self.base/self.remote exclusively; any per-item base/remote in a
        # discovered payload is rejected by the schema rather than honored.
        # Defense-in-depth: even this trusted config value is rejected here
        # if it is shaped like a git argv-injection gadget, so a
        # misconfigured/compromised launcher can't smuggle one in either.
        self.base: str = _reject_git_ref_shape(
            str(base) if base is not None else DEFAULT_BASE, label="base"
        )
        self.remote: str = _reject_git_ref_shape(
            str(remote) if remote is not None else DEFAULT_REMOTE, label="remote"
        )
        # repo_root/bundle_root are the trusted confinement anchors for item
        # filesystem paths (see the module comment above DEFAULT_BASE).
        # There is no safe implicit default, so they are resolved here if
        # supplied and required below when armed; every item
        # bundle_path/repo_path/worktree_path must resolve under one of these
        # before the daemon will touch it.
        self.repo_root: Path | None = (
            Path(repo_root).resolve()
            if repo_root is not None
            else (path_allocator.roots.repo_root if path_allocator is not None else None)
        )
        self.worktree_root: Path | None = path_allocator.roots.worktree_root if path_allocator is not None else self.repo_root
        self.bundle_root: Path | None = (
            Path(bundle_root).resolve()
            if bundle_root is not None
            else (path_allocator.roots.bundle_root if path_allocator is not None else None)
        )
        self._completed_keys: set[str] = set()

        if self.armed:
            missing = []
            if self.git_runner is None:
                missing.append("git_runner")
            if self.gh_runner is None:
                missing.append("gh_runner")
            if self.now is None:
                missing.append("now")
            if self.ledger_writer is None:
                missing.append("ledger_writer")
            if self.path_allocator is None:
                missing.append("path_allocator")
            if self.repo_root is None:
                missing.append("repo_root")
            if self.bundle_root is None:
                missing.append("bundle_root")
            if self.daemon_lease is None:
                missing.append("daemon_lease")
            if self.receipt_issuer is None:
                missing.append("receipt_issuer")
            if self.validation_ledger_binding is None:
                missing.append("validation_ledger_binding")
            if missing:
                raise ValueError(f"armed conveyor daemon requires injected {', '.join(missing)}")

    def run_once(self) -> ConveyorDaemonRunResult:
        """Run one discovery pass.

        Disarmed mode plans only. Armed mode processes each item independently
        and continues after per-item failures.
        """

        if self.armed:
            heartbeat_error = self._heartbeat_lease()
            if heartbeat_error is not None:
                return ConveyorDaemonRunResult(
                    armed=self.armed,
                    discovered_count=0,
                    results=(),
                    discovery_error=heartbeat_error,
                )

        try:
            discovered_items: list[ConveyorDaemonItem] = []
            for item in self.discovery_runner():
                try:
                    discovered_items.append(
                        _coerce_item(item, audit_sink=self._audit_discovery_payload_rejection)
                    )
                except DiscoveryPayloadRejected:
                    continue
                except TypeError as exc:
                    if not str(exc).startswith("unsupported discovery item type:"):
                        raise
                    self._audit_discovery_payload_rejection(
                        {
                            "action": "discovery_payload_rejected",
                            "source": "conveyor_daemon",
                            "reason": "unsupported_discovery_item_type",
                            "detail": str(exc),
                        }
                    )
                    continue
            discovered = tuple(discovered_items)
        except Exception as exc:
            self._log(f"conveyor discovery failed: {exc}")
            return ConveyorDaemonRunResult(
                armed=self.armed,
                discovered_count=0,
                results=(),
                discovery_error=str(exc),
            )

        seen_this_pass: set[str] = set()
        results: list[ConveyorDaemonItemResult] = []
        for item in discovered:
            if self.armed and (heartbeat_error := self._heartbeat_lease()) is not None:
                results.append(self._failed(item, (heartbeat_error,)))
                self._log(f"conveyor stopping pass before item after heartbeat failure: {heartbeat_error}")
                break

            if item.key in seen_this_pass or item.key in self._completed_keys:
                results.append(
                    ConveyorDaemonItemResult(
                        status="skipped",
                        branch=item.branch,
                        key=item.key,
                        reasons=("already processed in this daemon lifetime",),
                    )
                )
                continue
            seen_this_pass.add(item.key)

            if not self.armed:
                result = ConveyorDaemonItemResult(
                    status="planned",
                    branch=item.branch,
                    key=item.key,
                    planned_actions=PLAN_ACTIONS,
                )
                self._log(f"conveyor dry-run plan {item.branch}: {', '.join(PLAN_ACTIONS)}")
            else:
                result = self._process_armed(item)
                if result.status == "pr-opened":
                    self._completed_keys.add(item.key)
            results.append(result)

        return ConveyorDaemonRunResult(
            armed=self.armed,
            discovered_count=len(discovered),
            results=tuple(results),
        )

    def run_loop(self, *, iterations: int) -> tuple[ConveyorDaemonRunResult, ...]:
        """Run a finite daemon loop without sleeping or external scheduling."""

        if iterations < 1:
            raise ValueError("iterations must be >= 1")
        return tuple(self.run_once() for _ in range(iterations))

    def _process_armed(self, item: ConveyorDaemonItem) -> ConveyorDaemonItemResult:
        records: list[ConveyorDaemonLedgerRecord] = []
        assert self.path_allocator is not None
        allocation: DaemonPathAllocation | None = None
        receipt: DaemonPathReceipt | None = None
        mode_check: Mapping[str, Any] | None = None
        audit_item = item
        try:
            materialized = self._materialize_allocation(item)
            if isinstance(materialized, ConveyorDaemonItemResult):
                return materialized
            item, allocation, receipt = materialized
            audit_item = item

            mode_check = self._allocation_mode_check(allocation)

            # Confine/validate every daemon-issued filesystem path and the
            # pr_base shape BEFORE any prepare/land/push/pr-open action runs,
            # so a rejected item never reaches git_runner/gh_runner at all
            # (fail closed, log, skip).
            violations, resolved_paths = self._path_confinement_violations(item)
            if violations:
                return self._failed(item, violations, ledger_records=records)
            # TOCTOU close: `_path_confinement_violations` already resolved
            # bundle_path/repo_path/worktree_path (symlinks + `..` collapsed)
            # to verify they land under the pinned root, then handed those
            # resolved Paths back via `resolved_paths`. From here on we thread
            # THOSE resolved paths through every downstream call.
            item = dataclasses.replace(
                item,
                bundle_path=resolved_paths["bundle_path"],
                repo_path=resolved_paths["repo_path"],
                worktree_path=resolved_paths["worktree_path"],
            )
            audit_item = item
            assert self.git_runner is not None
            assert self.gh_runner is not None
            carrier_date = item.carrier_date or _date_from_timestamp(self._timestamp())
            prepared = self.prepare_runner(
                dataclasses.replace(
                    item.harvest_spec(
                        carrier_date=carrier_date,
                        validate_command=self.validate_command,
                        base=self.base,
                    ),
                    allow_dirty_validation=False,
                    commit_carriers_before_validation=True,
                ),
                git_runner=self.git_runner,
                validate_runner=self._armed_validate_runner(item, allocation, records),
            )
            if not prepared.ready:
                return self._failed(item, prepared.reasons, prepare_result=prepared, ledger_records=records)

            landed = self.land_runner(
                item.bundle_path,
                prepared.branch_slug,
                self.base,
                repo_path=item.repo_path,
                git_runner=self.git_runner,
            )
            if not landed.ready:
                reasons = tuple(f"{reason.code}: {reason.message}" for reason in landed.reasons)
                return self._failed(item, reasons, prepare_result=prepared, landing_result=landed, ledger_records=records)

            try:
                _reject_git_ref_shape(landed.branch, label="landed.branch")
            except ValueError as exc:
                return self._failed(
                    item,
                    (str(exc),),
                    prepare_result=prepared,
                    landing_result=landed,
                    ledger_records=records,
                )

            validation_tree_sha = _latest_validation_record_tree_sha(records)
            if validation_tree_sha is None:
                return self._failed(
                    item,
                    ("refusing to land unverified tree: no successful validation record found",),
                    prepare_result=prepared,
                    landing_result=landed,
                    ledger_records=records,
                )
            landed_tree_check = self._validate_landed_tree_matches_record(
                item=item,
                landed=landed,
                validation_tree_sha=validation_tree_sha,
            )
            if landed_tree_check is not None:
                return self._failed(
                    item,
                    (landed_tree_check,),
                    prepare_result=prepared,
                    landing_result=landed,
                    ledger_records=records,
                )

            publish_recheck = self._validate_publish_rechecks(
                item=item,
                landed=landed,
                validation_tree_sha=validation_tree_sha,
            )
            if publish_recheck:
                self._audit_publish(item=item, landed=landed, status="failed", checks=publish_recheck)
                return self._failed(
                    item,
                    tuple(publish_recheck.values()),
                    prepare_result=prepared,
                    landing_result=landed,
                    ledger_records=records,
                )
            self._audit_publish(
                item=item,
                landed=landed,
                status="success",
                checks={"status": "publish re-checks passed"},
            )

            push_args = _git_push_args(self.remote, landed.branch)
            push_result = _coerce_result(
                self.git_runner(
                    push_args,
                    item.repo_path,
                    git_env_for_phase(ConveyorGitPhase.TRANSPORT),
                )
            )
            records.append(
                self._record_mutation(
                    action="push",
                    path=f"{self.remote}/{landed.branch}",
                    sha=landed.head_sha or "",
                    branch=landed.branch,
                    command=("git", *push_args),
                    result=push_result,
                )
            )
            if push_result.returncode != 0:
                return self._failed(
                    item,
                    (f"push failed: {_command_detail(push_result)}",),
                    prepare_result=prepared,
                    landing_result=landed,
                    ledger_records=records,
                )

            pr_result = _coerce_result(self.gh_runner(_pr_create_args(self.base, item, landed), item.repo_path))
            pr_url = _first_stdout_line(pr_result.stdout)
            records.append(
                self._record_mutation(
                    action="pr-open",
                    path=pr_url or f"{_pr_base(self.base, item)}<-{landed.branch}",
                    sha=landed.head_sha or "",
                    branch=landed.branch,
                    command=("gh", *_pr_create_args(self.base, item, landed)),
                    result=pr_result,
                )
            )
            if pr_result.returncode != 0:
                return self._failed(
                    item,
                    (f"pr-open failed: {_command_detail(pr_result)}",),
                    prepare_result=prepared,
                    landing_result=landed,
                    ledger_records=records,
                )

            return ConveyorDaemonItemResult(
                status="pr-opened",
                branch=item.branch,
                key=item.key,
                prepare_result=prepared,
                landing_result=landed,
                pr_url=pr_url,
                ledger_records=tuple(records),
            )
        except Exception as exc:
            return self._failed(item, (f"exception: {exc}",), ledger_records=records)
        finally:
            if allocation is not None and receipt is not None:
                cleanup_result = self._cleanup_allocation(receipt)
                self._audit_allocation(
                    item=audit_item,
                    allocation=allocation,
                    mode_check=mode_check,
                    cleanup_result=cleanup_result,
                )

    def _materialize_allocation(
        self, item: ConveyorDaemonItem
    ) -> tuple[ConveyorDaemonItem, DaemonPathAllocation, DaemonPathReceipt] | ConveyorDaemonItemResult:
        assert self.path_allocator is not None

        executable_paths = {
            "bundle_path": item.bundle_path,
            "repo_path": item.repo_path,
            "worktree_path": item.worktree_path,
        }
        present_paths = {name: path for name, path in executable_paths.items() if path is not None}
        if present_paths:
            if item.allocation_receipt is None:
                return self._failed(
                    item,
                    ("executable item paths require a valid daemon allocation receipt",),
                )
            missing_paths = tuple(name for name, path in executable_paths.items() if path is None)
            if missing_paths:
                return self._failed(
                    item,
                    (f"allocation receipt supplied, but executable item paths are incomplete: {', '.join(missing_paths)}",),
                )
            try:
                allocation = self.path_allocator.verify_receipt(item.allocation_receipt)
            except DaemonAllocationError as exc:
                return self._failed(item, (f"daemon allocation receipt rejected: {exc}",))

            # Direct item paths must be confined and match the allocation
            # bound to the receipt. The receipt allocation remains the source
            # of truth for downstream paths.
            violations, resolved_paths = self._path_confinement_violations(item)
            if violations:
                return self._failed(item, violations)
            mismatches = self._allocation_path_mismatches(allocation, resolved_paths)
            if mismatches:
                return self._failed(item, mismatches)
            receipt = item.allocation_receipt
        else:
            if item.allocation_receipt is not None:
                return self._failed(
                    item,
                    ("allocation receipt supplied without executable item paths",),
                )
            try:
                allocation, receipt = self.path_allocator.allocate_conveyor_paths(
                    repo=item.key,
                    branch_name=item.branch,
                )
            except DaemonAllocationError as exc:
                return self._failed(item, (f"daemon path allocation failed: {exc}",))

        paths = self._conveyor_paths_from_allocation(allocation)
        if len(paths) == 3 and all(isinstance(path, Path) for path in paths):
            return dataclasses.replace(
                item,
                bundle_path=paths[0],
                repo_path=paths[1],
                worktree_path=paths[2],
                allocation_receipt=receipt,
            ), allocation, receipt
        return self._failed(item, paths)

    def _conveyor_paths_from_allocation(
        self, allocation: DaemonPathAllocation
    ) -> tuple[Path, Path, Path] | tuple[str, ...]:
        missing = tuple(
            field_name
            for field_name in ("bundle_path", "repo_path", "worktree_path")
            if getattr(allocation, field_name) is None
        )
        if missing:
            return (f"daemon allocation is missing conveyor paths: {', '.join(missing)}",)
        assert allocation.bundle_path is not None
        assert allocation.repo_path is not None
        assert allocation.worktree_path is not None
        return allocation.bundle_path, allocation.repo_path, allocation.worktree_path

    def _allocation_path_mismatches(
        self,
        allocation: DaemonPathAllocation,
        resolved_paths: Mapping[str, Path],
    ) -> tuple[str, ...]:
        mismatches: list[str] = []
        for field_name, expected_path in (
            ("bundle_path", allocation.bundle_path),
            ("repo_path", allocation.repo_path),
            ("worktree_path", allocation.worktree_path),
        ):
            if expected_path is None:
                mismatches.append(f"daemon allocation is missing {field_name}")
                continue
            if resolved_paths.get(field_name) != Path(expected_path).resolve():
                mismatches.append(f"{field_name} does not match daemon allocation receipt")
        return tuple(mismatches)

    def _allocation_mode_check(self, allocation: DaemonPathAllocation) -> dict[str, Any]:
        assert self.path_allocator is not None
        checks: dict[str, Any] = {}
        all_ok = True
        for field_name, kind, path in allocation.iter_paths():
            confined = self.path_allocator.roots.confine_path(path, kind)
            exists = confined.exists()
            is_dir = confined.is_dir()
            mode = confined.stat().st_mode & 0o777 if exists else None
            mode_ok = bool(exists and is_dir and mode == 0o700)
            all_ok = all_ok and mode_ok
            checks[field_name] = {
                "exists": exists,
                "is_dir": is_dir,
                "mode": oct(mode) if mode is not None else None,
                "mode_ok": mode_ok,
            }
        return {"ok": all_ok, "paths": checks}

    def _cleanup_allocation(self, receipt: DaemonPathReceipt) -> Mapping[str, Any]:
        assert self.path_allocator is not None
        try:
            cleaned = self.path_allocator.cleanup(receipt)
        except DaemonAllocationError as exc:
            return {"status": "failed", "cleaned": False, "error": str(exc)}
        return {"status": "success", "cleaned": cleaned}

    def _audit_allocation(
        self,
        *,
        item: ConveyorDaemonItem,
        allocation: DaemonPathAllocation,
        mode_check: Mapping[str, Any] | None,
        cleanup_result: Mapping[str, Any],
    ) -> None:
        assert self.path_allocator is not None
        roots = self.path_allocator.roots
        paths: list[dict[str, str]] = []
        for field_name, kind, path in allocation.iter_paths():
            confined = roots.confine_path(path, kind)
            paths.append(
                {
                    "field": field_name,
                    "root_kind": kind,
                    "relative_path": str(confined.relative_to(roots.root_for(kind))),
                }
            )
        record = {
            "action": "conveyor_allocation_audit",
            "phase": "allocation",
            "allocation_id": allocation.allocation_id,
            "item_key": item.key,
            "paths": paths,
            "mode_check": dict(mode_check or {}),
            "cleanup": dict(cleanup_result),
        }
        self._log(f"conveyor allocation audit: {json.dumps(record, sort_keys=True, default=str)}")

    def _path_confinement_violations(
        self, item: ConveyorDaemonItem
    ) -> tuple[tuple[str, ...], dict[str, Path]]:
        """Fail-closed audit of every item path/branch-shape
        field that reaches a git/gh argv or becomes a subprocess cwd.

        Returns a ``(violations, resolved_paths)`` pair. ``violations`` is
        empty if the item is safe to process; otherwise it is a tuple of
        human-readable violation reasons (one per failed check — an item can
        fail more than one check at once). ``resolved_paths`` maps
        ``"bundle_path"``/``"repo_path"``/``"worktree_path"`` to the
        already-resolved (symlinks + ``..`` collapsed, verified-under-root)
        :class:`Path` that ``_confine_path`` returned for that field; it is
        only complete (all three keys present) when ``violations`` is empty.
        Callers MUST use these resolved paths -- not the raw ``item``
        fields -- for every downstream action, so a path swapped out from
        under the daemon after this check runs cannot change what gets
        touched (see the TOCTOU note in ``_process_armed``).
        """

        assert self.repo_root is not None
        assert self.bundle_root is not None

        violations: list[str] = []
        resolved: dict[str, Path] = {}

        # bundle_path reaches a bare positional git argv slot (see the
        # module comment above DEFAULT_BASE), so it gets both the
        # argv-gadget shape rejection (mirrors base/remote/validate_command)
        # AND path confinement.
        if item.bundle_path is None:
            violations.append("bundle_path is required after daemon allocation")
        else:
            try:
                _reject_git_argv_gadget(str(item.bundle_path), label="bundle_path")
            except ValueError as exc:
                violations.append(str(exc))

        for label, value, root in (
            ("bundle_path", item.bundle_path, self.bundle_root),
            ("repo_path", item.repo_path, self.repo_root),
            ("worktree_path", item.worktree_path, self.worktree_root),
        ):
            if value is None:
                violations.append(f"{label} is required after daemon allocation")
                continue
            try:
                resolved[label] = _confine_path(value, root=root, label=label)
            except ValueError as exc:
                violations.append(str(exc))

        try:
            _reject_git_ref_shape(item.branch, label="branch")
        except ValueError as exc:
            violations.append(str(exc))

        # pr_base is not a filesystem path, but it flows into a fixed
        # flag-value slot (`gh pr create --base <pr_base>`); it is not RCE
        # (the value can never be reinterpreted as another flag or as a
        # transport-helper invocation from a fixed slot) but a payload could
        # still misdirect the PR at an unintended branch, so reject the same
        # dangerous shapes defense-in-depth.
        if item.pr_base is not None:
            try:
                _reject_git_ref_shape(item.pr_base, label="pr_base")
            except ValueError as exc:
                violations.append(str(exc))

        return tuple(violations), resolved

    def _record_mutation(
        self,
        *,
        action: str,
        path: str,
        sha: str,
        branch: str,
        command: Sequence[str],
        result: ConveyorCommandResult,
        details: Mapping[str, Any] | None = None,
    ) -> ConveyorDaemonLedgerRecord:
        assert self.ledger_writer is not None
        record_details: dict[str, Any] = {"command": tuple(command)}
        if details is not None:
            record_details.update(dict(details))
        record = ConveyorDaemonLedgerRecord(
            timestamp=self._timestamp(),
            action=action,
            path=path,
            sha=sha,
            branch=branch,
            status="success" if result.returncode == 0 else "failed",
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            details=record_details,
        )
        self.ledger_writer(record)
        return record

    def _armed_validate_runner(
        self,
        item: ConveyorDaemonItem,
        allocation: DaemonPathAllocation,
        records: list[ConveyorDaemonLedgerRecord],
    ) -> ValidateRunner:
        def run(
            args: Sequence[str],
            cwd: Path,
            env: Mapping[str, str] | None,
        ) -> ConveyorCommandResult:
            assert self.path_allocator is not None
            assert self.git_runner is not None
            assert self.receipt_issuer is not None
            if allocation.worktree_path is None:
                return ConveyorCommandResult(1, "", "daemon allocation is missing worktree_path")
            try:
                sandbox_cwd = self.path_allocator.roots.confine_path(cwd, "worktree")
            except DaemonAllocationError as exc:
                return ConveyorCommandResult(1, "", f"validation cwd rejected: {exc}")
            expected_cwd = Path(allocation.worktree_path).resolve()
            if sandbox_cwd != expected_cwd:
                return ConveyorCommandResult(1, "", "validation cwd does not match daemon allocation receipt")

            head_tree = _coerce_result(
                self.git_runner(
                    ("rev-parse", "HEAD^{tree}"),
                    sandbox_cwd,
                    git_env_for_phase(ConveyorGitPhase.LOCAL),
                )
            )
            if head_tree.returncode != 0:
                return ConveyorCommandResult(
                    head_tree.returncode,
                    head_tree.stdout,
                    f"validation tree identity failed: {_command_detail(head_tree)}",
                )

            spec = validation_sandbox_spec_from_command(
                args,
                sandbox_cwd,
                env,
                timeout_seconds=600,
            )
            kwargs: dict[str, Any] = {
                "tree_sha": head_tree.stdout.strip(),
                "policy_path": self.validation_sandbox_policy_path,
                "receipt_issuer": self.receipt_issuer,
                "instance_id": f"conveyor-validation-{allocation.allocation_id}",
            }
            if self.validation_sandbox_command_runner is not None:
                kwargs["command_runner"] = self.validation_sandbox_command_runner
            if self.validation_ledger_recorder is not None:
                kwargs["ledger_recorder"] = self.validation_ledger_recorder
            if self.validation_ledger_binding is not None:
                kwargs.update(dataclasses.asdict(self.validation_ledger_binding))

            try:
                sandbox_run = self.validation_sandbox_runner(spec, **kwargs)
            except Exception as exc:
                return ConveyorCommandResult(1, "", f"validation sandbox failed: {exc}")

            result = ConveyorCommandResult(
                sandbox_run.result.returncode,
                sandbox_run.result.stdout,
                sandbox_run.result.stderr,
            )
            if sandbox_run.receipt is not None:
                records.append(
                    self._record_mutation(
                        action="validate",
                        path=str(sandbox_cwd),
                        sha=sandbox_run.receipt.tree_sha,
                        branch=item.branch,
                        command=spec.command,
                        result=result,
                        details={
                            "receipt": sandbox_run.receipt.to_dict(),
                            "side_effect_path": None
                            if sandbox_run.side_effect_path is None
                            else str(sandbox_run.side_effect_path),
                            "side_effect_record": sandbox_run.side_effect_record,
                        },
                    )
                )
                self._audit_validation(
                    item=item,
                    allocation=allocation,
                    tree_sha=sandbox_run.receipt.tree_sha,
                    result=result,
                    side_effect_path=sandbox_run.side_effect_path,
                    side_effect_record=sandbox_run.side_effect_record,
                )
            return result

        return run

    def _audit_validation(
        self,
        *,
        item: ConveyorDaemonItem,
        allocation: DaemonPathAllocation,
        tree_sha: str,
        result: ConveyorCommandResult,
        side_effect_path: Path | None,
        side_effect_record: Mapping[str, Any] | None,
    ) -> None:
        record = {
            "action": "conveyor_validation_phase_audit",
            "allocation_id": allocation.allocation_id,
            "item_key": item.key,
            "tree_sha": tree_sha,
            "status": "success" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "side_effect_path": None if side_effect_path is None else str(side_effect_path),
            "side_effect_record": _validation_side_effect_summary(side_effect_record),
        }
        self._log(f"conveyor validation audit: {json.dumps(record, sort_keys=True, default=str)}")

    def _audit_publish(
        self,
        *,
        item: ConveyorDaemonItem,
        landed: ConveyorBundleLandingResult,
        status: str,
        checks: Mapping[str, str],
    ) -> None:
        record = {
            "action": "conveyor_publish_phase_audit",
            "item_key": item.key,
            "branch": landed.branch,
            "head_sha": landed.head_sha or "",
            "status": status,
            "checks": dict(checks),
        }
        self._log(f"conveyor publish audit: {json.dumps(record, sort_keys=True, default=str)}")

    def _validate_landed_tree_matches_record(
        self,
        *,
        item: ConveyorDaemonItem,
        landed: ConveyorBundleLandingResult,
        validation_tree_sha: str,
    ) -> str | None:
        assert self.git_runner is not None
        if item.repo_path is None:
            return "repo_path is required to compare landed tree with validation record tree"

        landed_tree = _coerce_result(
            self.git_runner(
                ("rev-parse", f"{landed.branch}^{{tree}}"),
                item.repo_path,
                git_env_for_phase(ConveyorGitPhase.LOCAL),
            )
        )
        if landed_tree.returncode != 0:
            return f"landed tree identity failed: {_command_detail(landed_tree)}"

        landed_tree_sha = landed_tree.stdout.strip()
        if landed_tree_sha != validation_tree_sha:
            return (
                "landed tip tree does not match validation record tree: "
                f"landed={landed_tree_sha} validation_record={validation_tree_sha}"
            )
        return None

    def _validate_publish_rechecks(
        self,
        *,
        item: ConveyorDaemonItem,
        landed: ConveyorBundleLandingResult,
        validation_tree_sha: str,
    ) -> dict[str, str]:
        checks: dict[str, str] = {}
        head_check = self._validate_landed_head_and_tree_identity(
            item=item,
            landed=landed,
            validation_tree_sha=validation_tree_sha,
        )
        if head_check is not None:
            checks["head_tree_identity"] = head_check
        ancestry_check = self._validate_publish_base_ancestry(item=item, landed=landed)
        if ancestry_check is not None:
            checks["base_ancestry"] = ancestry_check
        manifest_check = self._validate_publish_manifest_fidelity(item=item, landed=landed)
        if manifest_check is not None:
            checks["manifest_fidelity"] = manifest_check
        config_check = self._validate_publish_transport_config(item=item)
        if config_check is not None:
            checks["transport_config"] = config_check
        return checks

    def _validate_landed_head_and_tree_identity(
        self,
        *,
        item: ConveyorDaemonItem,
        landed: ConveyorBundleLandingResult,
        validation_tree_sha: str,
    ) -> str | None:
        assert self.git_runner is not None
        if item.repo_path is None:
            return "repo_path is required to compare landed head/tree identity"
        head = _coerce_result(
            self.git_runner(
                ("rev-parse", f"{landed.branch}^{{commit}}"),
                item.repo_path,
                git_env_for_phase(ConveyorGitPhase.LOCAL),
            )
        )
        if head.returncode != 0:
            return f"landed head identity failed: {_command_detail(head)}"
        landed_head_sha = head.stdout.strip()
        if not landed_head_sha:
            return "landed head identity failed: empty rev-parse output"
        if landed.head_sha and landed_head_sha != landed.head_sha:
            return (
                "landed head commit does not match landing result head: "
                f"landed={landed_head_sha} landing_result={landed.head_sha}"
            )
        return self._validate_landed_tree_matches_record(
            item=item,
            landed=landed,
            validation_tree_sha=validation_tree_sha,
        )

    def _validate_publish_base_ancestry(
        self,
        *,
        item: ConveyorDaemonItem,
        landed: ConveyorBundleLandingResult,
    ) -> str | None:
        assert self.git_runner is not None
        if item.repo_path is None:
            return "repo_path is required to re-check publish base ancestry"
        if landed.behind != 0:
            return f"publish base ancestry re-check failed: landed result is behind base by {landed.behind} commits"
        result = _coerce_result(
            self.git_runner(
                ("rev-list", "--left-right", "--count", f"{self.base}...{landed.branch}"),
                item.repo_path,
                git_env_for_phase(ConveyorGitPhase.LOCAL),
            )
        )
        if result.returncode != 0:
            return f"publish base ancestry re-check failed: {_command_detail(result)}"
        parts = result.stdout.strip().split()
        if len(parts) != 2:
            return f"publish base ancestry re-check failed: could not parse rev-list output {result.stdout.strip()!r}"
        try:
            behind = int(parts[0])
        except ValueError:
            return f"publish base ancestry re-check failed: could not parse rev-list output {result.stdout.strip()!r}"
        if behind != 0:
            return f"publish base ancestry re-check failed: landed branch is behind base by {behind} commits"
        return None

    def _validate_publish_manifest_fidelity(
        self,
        *,
        item: ConveyorDaemonItem,
        landed: ConveyorBundleLandingResult,
    ) -> str | None:
        assert self.git_runner is not None
        if item.repo_path is None:
            return "repo_path is required to re-check publish manifest fidelity"
        diff = _coerce_result(
            self.git_runner(
                ("diff", "--name-status", "--find-renames", f"{self.base}..{landed.branch}"),
                item.repo_path,
                git_env_for_phase(ConveyorGitPhase.LOCAL),
            )
        )
        if diff.returncode != 0:
            return f"publish manifest fidelity re-check failed: {_command_detail(diff)}"
        try:
            changed = _paths_from_name_status(diff.stdout)
        except ValueError as exc:
            return f"publish manifest fidelity re-check failed: malformed name-status output: {exc}"
        manifest = item.repo_path / ".ce" / "pr-manifests" / f"{branch_slug(landed.branch)}.md"
        manifest_paths = set(extract_manifest_paths_from_file(manifest))
        if not manifest_paths:
            return f"publish manifest fidelity re-check failed: no manifest paths in {manifest.relative_to(item.repo_path)}"
        if changed != manifest_paths:
            missing = sorted(changed - manifest_paths)
            unfulfilled = sorted(manifest_paths - changed)
            return (
                "publish manifest fidelity re-check failed: diff paths do not match carrier manifest "
                f"extra_diff={missing} missing_diff={unfulfilled}"
            )
        return None

    def _validate_publish_transport_config(self, *, item: ConveyorDaemonItem) -> str | None:
        assert self.git_runner is not None
        if item.repo_path is None:
            return "repo_path is required to inspect local transport config"
        result = _coerce_result(
            self.git_runner(
                ("config", "--local", "--get-regexp", _PUBLISH_TRANSPORT_CONFIG_PATTERN),
                item.repo_path,
                git_env_for_phase(ConveyorGitPhase.LOCAL),
            )
        )
        if result.returncode == 1 and not result.stdout.strip():
            return None
        if result.returncode != 0:
            return f"publish transport config guard failed: {_command_detail(result)}"
        matches = tuple(
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip() and _is_forbidden_publish_transport_config(line)
        )
        if matches:
            return f"publish transport config guard failed: forbidden local git config keys present: {', '.join(matches)}"
        return None

    def _failed(
        self,
        item: ConveyorDaemonItem,
        reasons: Sequence[str],
        *,
        prepare_result: ConveyorHarvestResult | None = None,
        landing_result: ConveyorBundleLandingResult | None = None,
        ledger_records: Sequence[ConveyorDaemonLedgerRecord] = (),
    ) -> ConveyorDaemonItemResult:
        reason_tuple = tuple(str(reason) for reason in reasons)
        self._log(f"conveyor item failed {item.branch}: {'; '.join(reason_tuple)}")
        return ConveyorDaemonItemResult(
            status="failed",
            branch=item.branch,
            key=item.key,
            reasons=reason_tuple,
            prepare_result=prepare_result,
            landing_result=landing_result,
            ledger_records=tuple(ledger_records),
        )

    def _timestamp(self) -> str:
        assert self.now is not None
        timestamp = self.now()
        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError("now must return a non-empty timestamp string")
        return timestamp

    def _heartbeat_lease(self) -> str | None:
        assert self.daemon_lease is not None
        try:
            self.daemon_lease.heartbeat()
        except Exception as exc:
            error = f"daemon lease heartbeat failed: {exc}"
            self._log(f"conveyor {error}")
            return error
        return None

    def _log(self, message: str) -> None:
        if self.log_runner is not None:
            self.log_runner(message)

    def _audit_discovery_payload_rejection(self, record: Mapping[str, Any]) -> None:
        self._log(f"conveyor discovery payload audit: {json.dumps(dict(record), sort_keys=True)}")


def _coerce_item(
    item: ConveyorDaemonItem | Mapping[str, Any],
    *,
    audit_sink: Callable[[Mapping[str, Any]], None] | None = None,
) -> ConveyorDaemonItem:
    if isinstance(item, ConveyorDaemonItem):
        return item
    if isinstance(item, Mapping):
        return ConveyorDaemonItem.from_mapping(item, audit_sink=audit_sink)
    raise TypeError(f"unsupported discovery item type: {type(item).__name__}")


def _coerce_result(result: ConveyorCommandResult | tuple[int, str, str]) -> ConveyorCommandResult:
    if isinstance(result, ConveyorCommandResult):
        return result
    return ConveyorCommandResult(result[0], result[1], result[2])


def _jsonl_ledger_writer(path: Path) -> LedgerWriter:
    def write(record: ConveyorDaemonLedgerRecord) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.as_dict(), sort_keys=True) + "\n")

    return write


def _pr_create_args(
    base: str, item: ConveyorDaemonItem, landed: ConveyorBundleLandingResult
) -> tuple[str, ...]:
    return (
        "pr",
        "create",
        "--base",
        _pr_base(base, item),
        "--head",
        landed.branch,
        "--title",
        item.pr_title or item.title,
        "--body",
        item.pr_body or item.body,
    )


def _git_push_args(remote: str, branch: str) -> list[str]:
    return ["push", "--", remote, f"{branch}:{branch}"]


def _latest_validation_record_tree_sha(records: Sequence[ConveyorDaemonLedgerRecord]) -> str | None:
    for record in reversed(records):
        if record.action != "validate" or record.returncode != 0:
            continue
        receipt = record.details.get("receipt")
        if isinstance(receipt, Mapping):
            tree_sha = receipt.get("tree_sha")
            if isinstance(tree_sha, str) and tree_sha:
                return tree_sha
        if record.sha:
            return record.sha
    return None


def _paths_from_name_status(stdout: str) -> set[str]:
    paths: set[str] = set()
    for line_number, line in enumerate(stdout.splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0].strip()
        if not status:
            raise ValueError(f"line {line_number} has empty status")
        if status.startswith(("R", "C")):
            if len(parts) != 3:
                raise ValueError(f"line {line_number} expected status, old path, and new path")
        elif len(parts) != 2:
            raise ValueError(f"line {line_number} expected status and path")
        current_path = parts[-1].strip()
        if not current_path:
            raise ValueError(f"line {line_number} has empty path")
        paths.add(current_path)
    return {path for path in paths if path}


def _validation_side_effect_summary(side_effect_record: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not side_effect_record:
        return {"present": False}
    fields: dict[str, Any] = {}
    for key in ("effect_kind", "subject_git_sha", "status", "returncode", "controller_id", "lane_id"):
        if key not in side_effect_record:
            continue
        value = side_effect_record[key]
        if isinstance(value, (str, int, float, bool)) or value is None:
            fields[key] = _bounded_audit_scalar(value)
    return {"present": True, "fields": fields}


def _bounded_audit_scalar(value: Any) -> Any:
    if isinstance(value, str) and len(value) > 128:
        return value[:125] + "..."
    return value


def _is_forbidden_publish_transport_config(line: str) -> bool:
    key = line.strip().split(maxsplit=1)[0].lower()
    return key in {"core.hookspath", "credential.helper"} or (
        key.startswith("url.") and key.endswith(".insteadof")
    )


def _pr_base(base: str, item: ConveyorDaemonItem) -> str:
    if item.pr_base:
        return item.pr_base
    if "/" in base:
        return base.rsplit("/", 1)[1]
    return base


_GIT_REF_FORBIDDEN = re.compile(r"[\000-\037\177 ~^:?*\[\\]")


def _reject_git_ref_shape(value: str, *, label: str) -> str:
    """Fail closed for ref-like values that reach git/gh argv.

    This intentionally mirrors the practical shape constraints from
    ``git check-ref-format`` without shelling out during daemon audits.
    """

    value = _reject_git_argv_gadget(value, label=label)
    if _GIT_REF_FORBIDDEN.search(value):
        raise ValueError(f"{label} contains a character disallowed in git refs: {value!r}")
    if ".." in value:
        raise ValueError(f"{label} must not contain '..' (git ref traversal shape): {value!r}")
    if "@{" in value or value == "@":
        raise ValueError(f"{label} must not contain git ref reflog syntax: {value!r}")
    if value.startswith("/") or value.endswith("/") or "//" in value:
        raise ValueError(f"{label} must not have leading, trailing, or repeated '/': {value!r}")
    if value.endswith("."):
        raise ValueError(f"{label} must not end with '.': {value!r}")
    for component in value.split("/"):
        if not component:
            raise ValueError(f"{label} must not contain an empty ref component: {value!r}")
        if component.startswith("."):
            raise ValueError(f"{label} ref components must not start with '.': {value!r}")
        if component.endswith(".lock"):
            raise ValueError(f"{label} ref components must not end with '.lock': {value!r}")
    return value


def _reject_git_argv_gadget(value: str, *, label: str) -> str:
    """Fail closed if a value destined for a bare git argv slot is shaped
    like an option or a transport-helper gadget.

    Applied to:

    * the daemon-pinned ``base``/``remote`` config themselves
      (defense-in-depth for a misconfigured/compromised launcher) on top of
      the primary control, which is that these values are never sourced
      from the discovery payload in the first place;
    * the item ``bundle_path``, as belt-and-suspenders on top
      of ``_confine_path`` confinement -- a confined *filename* still
      shouldn't be ``ext::``-shaped before it reaches
      ``git bundle verify``/``git fetch``;
    * the item ``pr_base``, which reaches a fixed
      ``gh pr create --base <value>`` flag-value slot (not RCE from that
      slot, but rejecting the same shapes is cheap defense-in-depth against
      branch misdirection).
    """

    if not value:
        raise ValueError(f"{label} must not be empty")
    if value.startswith("-"):
        raise ValueError(f"{label} must not start with '-' (git option/gadget shape): {value!r}")
    if "::" in value:
        raise ValueError(f"{label} must not contain '::' (git transport-helper shape): {value!r}")
    return value


def _confine_path(value: Path, *, root: Path, label: str) -> Path:
    """Fail closed unless *value* resolves under the trusted *root*.

    Both *value* and *root* are resolved (symlinks followed, ``..``
    collapsed) before comparison, so this single check rejects both a
    directory-redirection (an absolute path entirely outside the trusted
    tree, e.g. an attacker-staged repo elsewhere on disk) and a
    ``..``-traversal path that starts under the root but walks back out.
    ``root`` itself is accepted (a path equal to the root is "under" it).
    """

    resolved_root = Path(root).resolve()
    resolved_value = Path(value).resolve()
    try:
        resolved_value.relative_to(resolved_root)
    except ValueError:
        raise ValueError(
            f"{label} must resolve under the trusted root {resolved_root} "
            f"(got {value!r} -> resolved {resolved_value})"
        ) from None
    return resolved_value


def _first_stdout_line(stdout: str) -> str | None:
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _command_detail(result: ConveyorCommandResult) -> str:
    return result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"


def _date_from_timestamp(timestamp: str) -> str:
    if len(timestamp) >= 10 and timestamp[4:5] == "-" and timestamp[7:8] == "-":
        return timestamp[:10]
    raise ValueError("timestamp must begin with YYYY-MM-DD when carrier_date is omitted")


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


__all__ = [
    "ConveyorDaemon",
    "ConveyorDaemonItem",
    "ConveyorDaemonItemResult",
    "ConveyorDaemonLedgerRecord",
    "ConveyorDaemonRunResult",
    "ConveyorValidationLedgerBinding",
    "PLAN_ACTIONS",
]
