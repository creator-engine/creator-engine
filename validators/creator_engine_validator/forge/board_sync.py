"""CE v3 forge board-sync adapter — Projects-v2 desired-state sync.

Given a :class:`BoardSyncRef` and a sequence of :class:`DesiredItem` states
(loaded from a declarative YAML file via :func:`load_desired_state`), this
module:

(a) **reads** current board items (issues + draft items with status field)
    from an org Projects-v2 board via paginating GraphQL;
(b) **computes** a pure drift report (:class:`DriftReport`): missing items,
    stale status, orphans, and any unknown status-option names that would
    fail-close the sync;
(c) **applies** updates idempotently with ``apply=True``: adds missing issue
    items to the board and updates stale single-select status fields; orphans
    (items on the board but absent from the desired set) are reported and
    never deleted.

**Plan-by-default**: with ``apply=False`` (the default) NOTHING is written —
:func:`sync_board` returns a :class:`SyncResult` describing what would change.

**Fail-closed**: if any desired item's ``status`` value is not present in
``ref.status_options``, the sync refuses all mutations and surfaces the
unknown option names in :attr:`DriftReport.unknown_status_options`.

**Idempotent**: if the board already matches the desired state, a second run
produces no API calls beyond the initial read.

**Reuse**: the module imports :data:`backlog._STATUS_MUTATION`,
:func:`backlog._run_json`, and :func:`backlog._default_gh_runner` from the
companion ``backlog`` module instead of duplicating GraphQL. All GitHub calls
go through an injectable :data:`~.github_repo_config.GhRunner` seam; tests
inject a fake runner and perform **zero** live network or subprocess calls.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ._redact import redact_gh_stderr
from .backlog import _STATUS_MUTATION, _default_gh_runner, _run_json
from .github_repo_config import ForgeConfigError, GhRunner

__ce_version_line__ = "v3"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class BoardSyncError(Exception):
    """Board-sync configuration or runtime error (YAML schema, option lookup)."""

    code = "CE-BOARD-SYNC"


# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BoardSyncRef:
    """Projects-v2 coordinates for one CE org project board.

    ``project_id`` is the ``PVT_...`` project node id;
    ``status_field_id`` is the Status single-select field node id;
    ``status_options`` maps status names (e.g. ``"In flight"``) to their
    single-select option node ids.  Caller-discovered; this module never
    guesses them.
    """

    project_id: str
    status_field_id: str
    status_options: dict  # str -> str: name -> option_id

    def option_id(self, status_name: str) -> str:
        """Return the option node id for *status_name* or raise :exc:`BoardSyncError`."""
        try:
            return self.status_options[status_name]
        except KeyError:
            known = sorted(self.status_options)
            raise BoardSyncError(
                f"unknown status option {status_name!r}; "
                f"known options: {known!r}"
            ) from None


@dataclass(frozen=True)
class IssueCoord:
    """A GitHub issue identified by repository + number."""

    repo: str    # "owner/name"
    number: int

    @classmethod
    def parse(cls, ref: str) -> "IssueCoord":
        """Parse ``"owner/name#N"`` or raise :exc:`ValueError`."""
        try:
            repo_part, num_part = ref.rsplit("#", 1)
            return cls(repo=repo_part.strip(), number=int(num_part.strip()))
        except (ValueError, AttributeError) as exc:
            raise ValueError(
                f"invalid issue ref {ref!r}: expected owner/name#N"
            ) from exc


@dataclass(frozen=True)
class DesiredItem:
    """One entry from the desired-state YAML: issue → target status."""

    issue: IssueCoord
    status: str   # desired status column name


@dataclass(frozen=True)
class BoardItem:
    """One item observed on the board (issue or draft)."""

    item_id: str          # ``PVTI_...`` node id
    issue_repo: str | None   # ``"owner/name"`` or ``None`` for drafts
    issue_number: int | None
    status: str | None    # current status name, or ``None`` when unset
    is_draft: bool = False


@dataclass(frozen=True)
class DriftReport:
    """Pure drift verdict between desired and observed board state.

    ``missing`` — desired items absent from the board entirely.
    ``stale_status`` — pairs of ``(desired, observed)`` where the item is on
    the board but carries a different status than desired.
    ``orphans`` — board items (non-draft) absent from the desired set; reported
    but **never** deleted.
    ``unknown_status_options`` — desired status names not present in
    :attr:`BoardSyncRef.status_options`; when non-empty the sync is
    fail-closed.
    """

    missing: tuple  # tuple[DesiredItem, ...]
    stale_status: tuple  # tuple[tuple[DesiredItem, BoardItem], ...]
    orphans: tuple  # tuple[BoardItem, ...]
    unknown_status_options: tuple  # tuple[str, ...]

    @property
    def has_drift(self) -> bool:
        """True when there are missing items or stale status fields."""
        return bool(self.missing or self.stale_status)

    @property
    def fail_closed(self) -> bool:
        """True when unknown status options prevent any mutation."""
        return bool(self.unknown_status_options)


@dataclass(frozen=True)
class SyncResult:
    """Outcome of a :func:`sync_board` call."""

    drift: DriftReport
    applied: bool                  # True only when ``apply=True`` was passed
    added: tuple                   # tuple[DesiredItem, ...] — items added to board
    status_updated: tuple          # tuple[DesiredItem, ...] — status updated to desired
    errors: tuple                  # tuple[str, ...] — per-item error strings


# ---------------------------------------------------------------------------
# GraphQL strings (board-specific; status-update is reused from backlog)
# ---------------------------------------------------------------------------

_LIST_ITEMS_QUERY = """
query($project: ID!, $cursor: String) {
  node(id: $project) {
    ... on ProjectV2 {
      items(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          status: fieldValueByName(name: "Status") {
            ... on ProjectV2ItemFieldSingleSelectValue { name optionId }
          }
          content {
            ... on Issue {
              number
              repository { nameWithOwner }
            }
            ... on DraftIssue { title }
          }
        }
      }
    }
  }
}
"""

_ADD_ITEM_MUTATION = """
mutation($project: ID!, $content: ID!) {
  addProjectV2ItemById(input: { projectId: $project, contentId: $content }) {
    item { id }
  }
}
"""


# ---------------------------------------------------------------------------
# Board I/O (all through the injectable runner)
# ---------------------------------------------------------------------------

def read_board_items(
    ref: BoardSyncRef,
    *,
    gh_runner: GhRunner | None = None,
) -> list:
    """Read all items from the board, paginating until exhausted.

    Returns a :class:`list` of :class:`BoardItem` (both issues and drafts).
    Raises :exc:`~.github_repo_config.ForgeConfigError` on transport failure.
    """
    runner = gh_runner or _default_gh_runner
    items: list = []
    cursor: str | None = None

    while True:
        argv: list = [
            "gh", "api", "graphql",
            "-f", f"query={_LIST_ITEMS_QUERY}",
            "-f", f"project={ref.project_id}",
        ]
        if cursor is not None:
            argv += ["-f", f"cursor={cursor}"]

        payload = _run_json(
            runner, argv,
            f"list items for project {ref.project_id!r}",
        )

        node = (
            (payload or {}).get("data", {}).get("node", {})
            if isinstance(payload, dict) else {}
        )
        items_block = node.get("items", {}) if isinstance(node, dict) else {}
        nodes = items_block.get("nodes", []) if isinstance(items_block, dict) else []

        for raw in nodes or []:
            if not isinstance(raw, dict):
                continue
            item_id = raw.get("id") or ""
            status_obj = raw.get("status")
            status_name: str | None = (
                status_obj.get("name") if isinstance(status_obj, dict) else None
            )
            content = raw.get("content")
            if isinstance(content, dict) and "number" in content:
                repo_obj = content.get("repository")
                issue_repo: str | None = (
                    repo_obj.get("nameWithOwner")
                    if isinstance(repo_obj, dict) else None
                )
                items.append(BoardItem(
                    item_id=item_id,
                    issue_repo=issue_repo,
                    issue_number=int(content["number"]),
                    status=status_name,
                    is_draft=False,
                ))
            elif isinstance(content, dict) and "title" in content:
                items.append(BoardItem(
                    item_id=item_id,
                    issue_repo=None,
                    issue_number=None,
                    status=status_name,
                    is_draft=True,
                ))
            else:
                items.append(BoardItem(
                    item_id=item_id,
                    issue_repo=None,
                    issue_number=None,
                    status=status_name,
                    is_draft=False,
                ))

        page_info = items_block.get("pageInfo", {}) if isinstance(items_block, dict) else {}
        if not (page_info.get("hasNextPage") if isinstance(page_info, dict) else False):
            break
        cursor = page_info.get("endCursor") if isinstance(page_info, dict) else None
        if not cursor:
            break

    return items


def _get_issue_node_id(
    repo: str,
    number: int,
    *,
    gh_runner: GhRunner | None = None,
) -> str:
    """Resolve a GitHub issue's Projects-v2-compatible node id via the REST API.

    Returns the opaque ``I_...`` node id.
    Raises :exc:`~.github_repo_config.ForgeConfigError` on failure.
    """
    runner = gh_runner or _default_gh_runner
    payload = _run_json(
        runner,
        ["gh", "api", f"repos/{repo}/issues/{number}"],
        f"resolve node id for {repo}#{number}",
    )
    if not isinstance(payload, dict):
        raise ForgeConfigError(
            f"could not resolve issue node id for {repo}#{number}: "
            "API response was not a JSON object"
        )
    node_id = payload.get("node_id")
    if not isinstance(node_id, str) or not node_id:
        raise ForgeConfigError(
            f"issue {repo}#{number} API response has no 'node_id' field"
        )
    return node_id


def _add_issue_to_board(
    ref: BoardSyncRef,
    coord: IssueCoord,
    *,
    gh_runner: GhRunner | None = None,
) -> str:
    """Add a GitHub issue to the board and return the new item node id.

    First resolves the issue's ``node_id`` via the REST API, then calls the
    ``addProjectV2ItemById`` mutation. Returns the new ``PVTI_...`` item id.
    Raises :exc:`~.github_repo_config.ForgeConfigError` on any failure.
    """
    runner = gh_runner or _default_gh_runner
    content_id = _get_issue_node_id(coord.repo, coord.number, gh_runner=runner)
    payload = _run_json(
        runner,
        [
            "gh", "api", "graphql",
            "-f", f"query={_ADD_ITEM_MUTATION}",
            "-f", f"project={ref.project_id}",
            "-f", f"content={content_id}",
        ],
        f"add issue {coord.repo}#{coord.number} to project {ref.project_id!r}",
    )
    item_id: str = ""
    if isinstance(payload, dict):
        item_id = (
            payload
            .get("data", {})
            .get("addProjectV2ItemById", {})
            .get("item", {})
            .get("id", "")
        ) or ""
    if not item_id:
        raise ForgeConfigError(
            f"addProjectV2ItemById for {coord.repo}#{coord.number} "
            "returned no item id"
        )
    return item_id


def _update_item_status(
    ref: BoardSyncRef,
    item_id: str,
    status_name: str,
    *,
    gh_runner: GhRunner | None = None,
) -> None:
    """Set the Status single-select field on *item_id* to *status_name*.

    Reuses :data:`backlog._STATUS_MUTATION` (no GraphQL duplication).
    Raises :exc:`BoardSyncError` for unknown status names (fail-closed before
    the network call) or :exc:`~.github_repo_config.ForgeConfigError` on
    transport failure.
    """
    option_id = ref.option_id(status_name)  # raises BoardSyncError if unknown
    runner = gh_runner or _default_gh_runner
    _run_json(
        runner,
        [
            "gh", "api", "graphql",
            "-f", f"query={_STATUS_MUTATION}",
            "-f", f"project={ref.project_id}",
            "-f", f"item={item_id}",
            "-f", f"field={ref.status_field_id}",
            "-f", f"option={option_id}",
        ],
        f"update status of item {item_id!r} to {status_name!r}",
    )


# ---------------------------------------------------------------------------
# Pure drift computation
# ---------------------------------------------------------------------------

def compute_drift(
    ref: BoardSyncRef,
    desired: Sequence,   # Sequence[DesiredItem]
    observed: Sequence,  # Sequence[BoardItem]
) -> DriftReport:
    """Pure drift computation — desired vs observed board state.

    Missing items: desired but absent from the board.
    Stale status: present on the board but carrying a different status.
    Orphans: on the board (non-draft) but absent from the desired set.
    Unknown status options: desired status values not in
    ``ref.status_options`` — collected here so the caller can fail-close
    before any mutation.

    Repository name comparison is case-insensitive (GitHub names are).
    """
    # Collect unknown status options before any mutation check
    unknown: list = []
    for d in desired:
        if d.status not in ref.status_options and d.status not in unknown:
            unknown.append(d.status)

    # Index observed non-draft items by (repo_lower, number)
    obs_index: dict = {}
    for b in observed:
        if b.issue_repo is not None and b.issue_number is not None:
            obs_index[(b.issue_repo.lower(), b.issue_number)] = b

    # Compute missing and stale
    desired_keys: set = set()
    missing: list = []
    stale: list = []

    for d in desired:
        key = (d.issue.repo.lower(), d.issue.number)
        desired_keys.add(key)
        if key not in obs_index:
            missing.append(d)
        else:
            b = obs_index[key]
            if b.status != d.status:
                stale.append((d, b))

    # Orphans: non-draft board items not in desired set
    orphans: list = []
    for b in observed:
        if b.is_draft:
            continue
        if b.issue_repo is not None and b.issue_number is not None:
            if (b.issue_repo.lower(), b.issue_number) not in desired_keys:
                orphans.append(b)
        else:
            orphans.append(b)

    return DriftReport(
        missing=tuple(missing),
        stale_status=tuple(stale),
        orphans=tuple(orphans),
        unknown_status_options=tuple(unknown),
    )


# ---------------------------------------------------------------------------
# Sync orchestrator
# ---------------------------------------------------------------------------

def sync_board(
    ref: BoardSyncRef,
    desired: Sequence,   # Sequence[DesiredItem]
    *,
    apply: bool = False,
    gh_runner: GhRunner | None = None,
) -> SyncResult:
    """Idempotent board sync: read → drift → (optionally) apply.

    **Plan-by-default** (``apply=False``): reads the board and computes the
    drift report; nothing is written.

    **Execute mode** (``apply=True``): for each missing item, resolves the
    issue node id, adds it to the board, and immediately sets its status field;
    for each stale item, updates the status field only. Orphans are never
    deleted.

    **Fail-closed**: if :attr:`DriftReport.fail_closed` is ``True`` (unknown
    status option names), returns immediately with no mutations and an error
    string in :attr:`SyncResult.errors`.

    **Idempotency**: when the board already matches the desired state, the
    drift report is empty and no mutations are issued.
    """
    runner = gh_runner or _default_gh_runner
    observed = read_board_items(ref, gh_runner=runner)
    drift = compute_drift(ref, desired, observed)

    if drift.fail_closed:
        return SyncResult(
            drift=drift,
            applied=False,
            added=(),
            status_updated=(),
            errors=(
                f"unknown status option(s) {list(drift.unknown_status_options)!r}; "
                "no mutations applied (fail-closed)",
            ),
        )

    if not apply:
        return SyncResult(
            drift=drift,
            applied=False,
            added=(),
            status_updated=(),
            errors=(),
        )

    added: list = []
    status_updated: list = []
    errors: list = []

    # Add missing items then immediately set their status
    for d in drift.missing:
        try:
            item_id = _add_issue_to_board(ref, d.issue, gh_runner=runner)
            added.append(d)
            # Status update: fail-closed was already checked above
            try:
                _update_item_status(ref, item_id, d.status, gh_runner=runner)
                status_updated.append(d)
            except (ForgeConfigError, BoardSyncError) as exc:
                errors.append(
                    f"update status after add {d.issue.repo}#{d.issue.number}: {exc}"
                )
        except ForgeConfigError as exc:
            errors.append(f"add {d.issue.repo}#{d.issue.number}: {exc}")

    # Update status on existing stale items
    for d, b in drift.stale_status:
        try:
            _update_item_status(ref, b.item_id, d.status, gh_runner=runner)
            status_updated.append(d)
        except (ForgeConfigError, BoardSyncError) as exc:
            errors.append(
                f"update status {d.issue.repo}#{d.issue.number}: {exc}"
            )

    return SyncResult(
        drift=drift,
        applied=True,
        added=tuple(added),
        status_updated=tuple(status_updated),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# YAML desired-state loader
# ---------------------------------------------------------------------------

def load_desired_state(path: "Path | str") -> "tuple[BoardSyncRef, list]":
    """Load board desired state from a YAML file.

    Returns ``(ref, desired_items)`` where ``ref`` is a :class:`BoardSyncRef`
    and ``desired_items`` is a :class:`list` of :class:`DesiredItem`.

    Expected YAML schema::

        project_id: "PVT_..."          # org project node id
        status_field_id: "PVTSSF_..."  # Status field node id
        status_options:
          "In flight": "opt_..."
          "Done":      "opt_..."
        items:
          - issue: owner/name#N
            status: "In flight"
            label: "optional human label (ignored by sync)"

    Raises :exc:`BoardSyncError` on any schema or file-read error.
    """
    import yaml  # lazy import — PyYAML is a core CE dep (pyproject.toml)

    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise BoardSyncError(
            f"could not read board state YAML {path}: {exc}"
        ) from exc
    except yaml.YAMLError as exc:
        raise BoardSyncError(
            f"could not parse board state YAML {path}: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        raise BoardSyncError(
            f"board state YAML {path}: top-level value must be a mapping"
        )

    project_id = raw.get("project_id") or ""
    if not project_id:
        raise BoardSyncError(
            f"board state YAML {path}: missing required field 'project_id'"
        )

    status_field_id = raw.get("status_field_id") or ""
    if not status_field_id:
        raise BoardSyncError(
            f"board state YAML {path}: missing required field 'status_field_id'"
        )

    status_options_raw = raw.get("status_options") or {}
    if not isinstance(status_options_raw, dict):
        raise BoardSyncError(
            f"board state YAML {path}: 'status_options' must be a mapping"
        )
    status_options = {str(k): str(v) for k, v in status_options_raw.items()}
    if not status_options:
        raise BoardSyncError(
            f"board state YAML {path}: 'status_options' must not be empty"
        )

    ref = BoardSyncRef(
        project_id=project_id,
        status_field_id=status_field_id,
        status_options=status_options,
    )

    items_raw = raw.get("items") or []
    if not isinstance(items_raw, list):
        raise BoardSyncError(
            f"board state YAML {path}: 'items' must be a list"
        )

    items: list = []
    for i, entry in enumerate(items_raw):
        if not isinstance(entry, dict):
            raise BoardSyncError(
                f"board state YAML {path}: item[{i}] must be a mapping"
            )
        issue_ref = entry.get("issue") or ""
        if not issue_ref:
            raise BoardSyncError(
                f"board state YAML {path}: item[{i}] missing required field 'issue'"
            )
        status = entry.get("status") or ""
        if not status:
            raise BoardSyncError(
                f"board state YAML {path}: item[{i}] missing required field 'status'"
            )
        try:
            coord = IssueCoord.parse(str(issue_ref))
        except ValueError as exc:
            raise BoardSyncError(
                f"board state YAML {path}: item[{i}].issue: {exc}"
            ) from exc
        items.append(DesiredItem(issue=coord, status=status))

    return ref, items
