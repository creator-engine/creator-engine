"""Pure conveyor daemon core for harvest-to-PR automation.

The daemon defaults to disarmed dry-run planning. Armed execution requires all
source-host mutation seams to be injected by the caller.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .conveyor import (
    DEFAULT_VALIDATE_COMMAND,
    ConveyorBundleLandingResult,
    ConveyorCommandResult,
    ConveyorHarvestResult,
    ConveyorHarvestSpec,
    land_bundle,
    prepare_harvest,
)
from .pickup_payload_schema import DiscoveryPayloadRejected, validate_discovery_payload
from .checks.path_manifest_fidelity import branch_slug


DiscoveryRunner = Callable[[], Iterable["ConveyorDaemonItem | Mapping[str, Any]"]]
CommandRunner = Callable[[Sequence[str], Path], ConveyorCommandResult | tuple[int, str, str]]
ValidateRunner = Callable[
    [Sequence[str], Path, Mapping[str, str] | None],
    ConveyorCommandResult | tuple[int, str, str],
]
PrepareRunner = Callable[..., ConveyorHarvestResult]
LandRunner = Callable[..., ConveyorBundleLandingResult]
NowRunner = Callable[[], str]
LedgerWriter = Callable[["ConveyorDaemonLedgerRecord"], None]
LogRunner = Callable[[str], None]


PLAN_ACTIONS = ("prepare-harvest", "land-bundle", "push", "pr-open")

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
    worktree_path: Path
    bundle_path: Path
    repo_path: Path
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
    daemon_owned_paths_allocated: bool = True

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
            worktree_path=Path("."),
            bundle_path=Path("."),
            repo_path=Path("."),
            issue=parsed.issue,
            title=parsed.pr_title,
            kind="changed",
            scope="conveyor harvest",
            body=parsed.pr_body,
            declared_work_class="story",
            pr_title=parsed.pr_title,
            pr_body=parsed.pr_body,
            daemon_owned_paths_allocated=False,
        )

    @property
    def key(self) -> str:
        return self.identity or branch_slug(self.branch)

    def harvest_spec(
        self, *, carrier_date: str, validate_command: tuple[str, ...], base: str
    ) -> ConveyorHarvestSpec:
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
        git_runner: CommandRunner | None = None,
        validate_runner: ValidateRunner | None = None,
        gh_runner: CommandRunner | None = None,
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
    ) -> None:
        self.discovery_runner = discovery_runner
        self.armed = armed
        self.git_runner = git_runner
        self.validate_runner = validate_runner
        self.gh_runner = gh_runner
        self.now = now
        self.ledger_writer = ledger_writer or (_jsonl_ledger_writer(Path(ledger_path)) if ledger_path is not None else None)
        self.log_runner = log_runner
        self.prepare_runner = prepare_runner
        self.land_runner = land_runner
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
        self.base: str = _reject_git_argv_gadget(
            str(base) if base is not None else DEFAULT_BASE, label="base"
        )
        self.remote: str = _reject_git_argv_gadget(
            str(remote) if remote is not None else DEFAULT_REMOTE, label="remote"
        )
        # repo_root/bundle_root are the trusted confinement anchors for item
        # filesystem paths (see the module comment above DEFAULT_BASE).
        # There is no safe implicit default, so they are resolved here if
        # supplied and required below when armed; every item
        # bundle_path/repo_path/worktree_path must resolve under one of these
        # before the daemon will touch it.
        self.repo_root: Path | None = Path(repo_root).resolve() if repo_root is not None else None
        self.bundle_root: Path | None = Path(bundle_root).resolve() if bundle_root is not None else None
        self._completed_keys: set[str] = set()

        if self.armed:
            missing = []
            if self.git_runner is None:
                missing.append("git_runner")
            if self.validate_runner is None:
                missing.append("validate_runner")
            if self.gh_runner is None:
                missing.append("gh_runner")
            if self.now is None:
                missing.append("now")
            if self.ledger_writer is None:
                missing.append("ledger_writer")
            if self.repo_root is None:
                missing.append("repo_root")
            if self.bundle_root is None:
                missing.append("bundle_root")
            if missing:
                raise ValueError(f"armed conveyor daemon requires injected {', '.join(missing)}")

    def run_once(self) -> ConveyorDaemonRunResult:
        """Run one discovery pass.

        Disarmed mode plans only. Armed mode processes each item independently
        and continues after per-item failures.
        """

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
        if not item.daemon_owned_paths_allocated:
            return self._failed(
                item,
                ("data-only discovery payload accepted, but daemon-owned path allocation is not wired",),
                ledger_records=records,
            )
        # Confine/validate every item filesystem path and the
        # pr_base shape BEFORE any prepare/land/push/pr-open action runs, so
        # a rejected item never reaches git_runner/gh_runner at all (fail
        # closed, log, skip). This is checked first, ahead of the try/except
        # below, so a violation is reported as its own precise reason rather
        # than folded into a generic "exception: ..." message.
        violations, resolved_paths = self._path_confinement_violations(item)
        if violations:
            return self._failed(item, violations, ledger_records=records)
        # TOCTOU close: `_path_confinement_violations` already resolved
        # bundle_path/repo_path/worktree_path (symlinks + `..` collapsed) to
        # verify they land under the pinned root, then handed those resolved
        # Paths back via `resolved_paths`. From here on we thread THOSE
        # resolved paths -- not the raw path values still sitting on
        # `item` -- through every downstream prepare/land/push/pr-open call.
        # If we kept using the raw, unresolved item fields, an attacker who
        # passes this check with a legitimate path and then swaps that
        # directory for a symlink to an attacker-controlled repo (e.g. one
        # whose `.git/config` sets `origin` to an `ext::` transport-helper
        # gadget) before harvest/validate/land/push actually run would
        # defeat confinement entirely: the *name* would still resolve under
        # root at check-time, but every subsequent git/gh subprocess cwd or
        # argv would silently follow the swapped target instead. Operating
        # on the already-resolved realpath for the rest of processing means
        # a later swap of the original path has no effect on what the
        # daemon actually touches.
        item = dataclasses.replace(
            item,
            bundle_path=resolved_paths["bundle_path"],
            repo_path=resolved_paths["repo_path"],
            worktree_path=resolved_paths["worktree_path"],
        )
        try:
            assert self.git_runner is not None
            assert self.validate_runner is not None
            assert self.gh_runner is not None
            carrier_date = item.carrier_date or _date_from_timestamp(self._timestamp())
            prepared = self.prepare_runner(
                item.harvest_spec(
                    carrier_date=carrier_date,
                    validate_command=self.validate_command,
                    base=self.base,
                ),
                git_runner=self.git_runner,
                validate_runner=self.validate_runner,
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

            push_result = _coerce_result(
                self.git_runner(["push", self.remote, f"{landed.branch}:{landed.branch}"], item.repo_path)
            )
            records.append(
                self._record_mutation(
                    action="push",
                    path=f"{self.remote}/{landed.branch}",
                    sha=landed.head_sha or "",
                    branch=landed.branch,
                    command=("git", "push", self.remote, f"{landed.branch}:{landed.branch}"),
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
        try:
            _reject_git_argv_gadget(str(item.bundle_path), label="bundle_path")
        except ValueError as exc:
            violations.append(str(exc))

        for label, value, root in (
            ("bundle_path", item.bundle_path, self.bundle_root),
            ("repo_path", item.repo_path, self.repo_root),
            ("worktree_path", item.worktree_path, self.repo_root),
        ):
            try:
                resolved[label] = _confine_path(value, root=root, label=label)
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
                _reject_git_argv_gadget(item.pr_base, label="pr_base")
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
    ) -> ConveyorDaemonLedgerRecord:
        assert self.ledger_writer is not None
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
            details={"command": tuple(command)},
        )
        self.ledger_writer(record)
        return record

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


def _pr_base(base: str, item: ConveyorDaemonItem) -> str:
    if item.pr_base:
        return item.pr_base
    if "/" in base:
        return base.rsplit("/", 1)[1]
    return base


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
    "PLAN_ACTIONS",
]
