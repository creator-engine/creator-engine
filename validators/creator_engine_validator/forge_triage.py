"""Forge triage planner for bounded CE work pickup (ce-ops#187).

The planner consumes an arc ticket plus an offline JSON set of open GitHub
issues and emits deterministic, claimable pickup work. Dry-run planning is pure
for normal CLI use. When a ``gh_runner`` is supplied, the planner also checks
the forge-native work-claim status and refuses to surface actively claimed
items. Applying the plan is a separate explicit step that posts labels and/or
assignees through the same injectable ``gh`` seam.
"""
from __future__ import annotations

import json
import re
import subprocess
import urllib.parse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Callable

from . import work_claims
from .forge.hold_labels import AWAITING_OPERATOR_HOLD_LABELS, BLOCKING_LABEL_PREFIXES
from .work_sizing import MUTATION_CLASSES, WORK_CLASSES, WORK_CLASS_ALIASES, normalize_work_class, size_ceremony

GhRunner = Callable[[Sequence[str], "str | None"], subprocess.CompletedProcess]

DEFAULT_PICKUP_LABEL = "ce-pickup/triage-ready"
SCHEMA_VERSION = 1
_TIMELINE_PAGE_SIZE = 100
_TIMELINE_MAX_PAGES = 20
DEFAULT_USER_STORY_LABELS = ("user-story",)
DEFAULT_OPERATOR_AUTHOR_LOGINS = ("Operator",)

_GITHUB_ISSUE_RE = re.compile(
    r"https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/(?:issues|pull)/(\d+)"
)
_GITHUB_REF_URL_RE = re.compile(
    r"https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/issues/(\d+)"
)
_GITHUB_API_ISSUE_RE = re.compile(
    r"https?://api\.github\.com/repos/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/issues/(\d+)"
)
_API_REPO_RE = re.compile(r"https?://api\.github\.com/repos/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
_OWNER_REPO_REF_RE = re.compile(r"(?<![\w./-])([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(\d+)")
_SHORT_REPO_REF_RE = re.compile(r"(?<![\w./-])([A-Za-z0-9_.-]+)#(\d+)")
_BARE_ISSUE_REF_RE = re.compile(r"(?<![\w./-])#(\d+)")
_SHORT_TICKET_RE = re.compile(r"^[A-Za-z0-9_.-]+#(\d+)$")
_DEPENDENCY_BODY_RE = re.compile(
    r"\b(?:blocked\s*(?:-|\s+)by|depends\s+on|dependenc(?:y|ies))\b\s*:?\s*"
    r"(?:"
    r"https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(?:issues|pull)/\d+"
    r"|https?://api\.github\.com/repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/\d+"
    r"|[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#\d+"
    r"|[A-Za-z0-9_.-]+#\d+"
    r"|#\d+"
    r"|\d+"
    r")",
    re.IGNORECASE,
)

_BLOCKING_LABELS = AWAITING_OPERATOR_HOLD_LABELS
_BLOCKING_LABEL_PREFIXES = BLOCKING_LABEL_PREFIXES
_DONE_LABELS = frozenset(
    {
        "closed",
        "complete",
        "completed",
        "done",
        "state:closed",
        "state:done",
        "status:closed",
        "status:complete",
        "status:completed",
        "status:done",
    }
)
_AGGREGATE_LABELS = frozenset(
    {
        "aggregate",
        "arc",
        "debug",
        "epic",
        "kind:arc",
        "kind:debug",
        "kind:epic",
        "kind:meta",
        "kind/arc",
        "kind/debug",
        "kind/epic",
        "kind/meta",
        "meta",
        "meta-debug",
        "meta/debug",
        "parent",
        "rollup",
        "roadmap",
        "tracker",
        "tracking",
        "type:arc",
        "type:debug",
        "type:epic",
        "type:meta",
        "type/arc",
        "type/debug",
        "type/epic",
        "type/meta",
    }
)
_AGGREGATE_TITLE_RE = re.compile(
    r"^\s*(?:\[?\s*)?(?:arc|epic|meta|tracker|tracking|rollup|roadmap)\b",
    re.IGNORECASE,
)
# Hold markers carried in an issue body or comment (ce-ops#196). The
# AWAITING-OPERATOR queue rule + ⏸️ marker convention flag an item that is
# parked pending an Operator confirm; such items must never surface as ready.
_HOLD_MARKER_RE = re.compile(r"awaiting[-\s]*operator|⏸", re.IGNORECASE)
_COMMENT_PAGE_SIZE = 100
_COMMENT_MAX_PAGES = 20
_HELD_CHECKPOINT_LINE_RE = re.compile(r"\bheld[-\s]+checkpoints?\b", re.IGNORECASE)
_MARKDOWN_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+")
_DEPENDENCY_FIELDS = (
    "blocked_by",
    "blocked_by_issues",
    "dependencies",
    "depends_on",
    "required_issues",
)


class ForgeTriageError(Exception):
    """Bad offline input or failed explicit apply operation."""


@dataclass(frozen=True)
class IssueCandidate:
    """Normalized GitHub issue candidate."""

    repo: str
    number: int
    title: str = ""
    url: str | None = None
    state: str = "open"
    labels: tuple[str, ...] = ()
    assignees: tuple[str, ...] = ()
    body: str = ""
    work_class: str | None = None
    mutation_class: str | None = None
    raw: Mapping[str, Any] | None = None

    @property
    def work_key(self) -> work_claims.WorkKey:
        owner, name = self.repo.split("/", 1)
        return work_claims.WorkKey(owner, name, self.number)

    def to_dict(self) -> dict[str, Any]:
        return {
            "repo": self.repo,
            "number": self.number,
            "title": self.title,
            "url": self.url,
            "state": self.state,
            "labels": list(self.labels),
            "assignees": list(self.assignees),
            "work_key": self.work_key.work_key,
        }


@dataclass(frozen=True)
class PlannedMutation:
    """One planned belt pickup mutation."""

    kind: str
    value: str
    status: str = "planned"

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "value": self.value, "status": self.status}


@dataclass(frozen=True)
class CommissionedPredicateConfig:
    """Configurable commissioned-work predicate for unscheduled sweep output."""

    user_story_labels: tuple[str, ...] = DEFAULT_USER_STORY_LABELS
    operator_author_logins: tuple[str, ...] = DEFAULT_OPERATOR_AUTHOR_LOGINS


@dataclass(frozen=True)
class CommissionedUnscheduledItem:
    """One commissioned issue that is not referenced by the active arc."""

    issue: IssueCandidate
    commissioned_by: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue": self.issue.to_dict(),
            "work_key": self.issue.work_key.work_key,
            "commissioned_by": list(self.commissioned_by),
            "unmilestoned": True,
            "referenced_by_active_arc": False,
            "advisory_only": True,
            "planned_mutations": [],
        }


@dataclass(frozen=True)
class TriageAction:
    """One claimable issue plus the belt mutations that make it pick-up ready."""

    issue: IssueCandidate
    arc_ticket: str
    work_class: str
    mutation_class: str
    sizing: Mapping[str, Any]
    pickup_label: str
    pickup_query_hint: str
    seat: str | None = None
    mutations: tuple[PlannedMutation, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "arc_ticket": self.arc_ticket,
            "issue": self.issue.to_dict(),
            "work_key": self.issue.work_key.work_key,
            "work_class": self.work_class,
            "mutation_class": self.mutation_class,
            "sizing": dict(self.sizing),
            "pickup_label": self.pickup_label,
            "pickup_query_hint": self.pickup_query_hint,
            "seat": self.seat,
            "planned_mutations": [m.to_dict() for m in self.mutations],
        }


@dataclass(frozen=True)
class TriageResult:
    """Full deterministic triage result."""

    arc_ticket: str
    arc_work_key: str | None
    pickup_label: str
    pickup_query_hint: str
    applied: bool
    items: tuple[TriageAction, ...]
    commissioned_unscheduled: tuple[CommissionedUnscheduledItem, ...] = ()
    commissioned_unscheduled_status: str = "verified"
    skipped: tuple[Mapping[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "forge-triage-result",
            "schema_version": SCHEMA_VERSION,
            "arc_ticket": self.arc_ticket,
            "arc_work_key": self.arc_work_key,
            "pickup_label": self.pickup_label,
            "pickup_query_hint": self.pickup_query_hint,
            "applied": self.applied,
            "count": len(self.items),
            "items": [item.to_dict() for item in self.items],
            "commissioned_unscheduled_status": self.commissioned_unscheduled_status,
            "commissioned_unscheduled_count": len(self.commissioned_unscheduled),
            "commissioned_unscheduled": [
                item.to_dict() for item in self.commissioned_unscheduled
            ],
            "skipped_count": len(self.skipped),
            "skipped": [dict(item) for item in self.skipped],
        }


def load_issue_payloads(text: str) -> list[Any]:
    """Load GitHub Search/list issue JSON from text."""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ForgeTriageError(f"issues JSON is invalid: {exc}") from exc
    return _issue_payloads(payload)


def normalize_issue_payloads(
    payload: Any,
    *,
    default_repo: str | None = None,
) -> tuple[IssueCandidate, ...]:
    """Normalize a GitHub Search/list JSON payload into candidates."""
    candidates: list[IssueCandidate] = []
    for raw in _issue_payloads(payload):
        candidate = normalize_issue(raw, default_repo=default_repo)
        if candidate is not None:
            candidates.append(candidate)
    return tuple(_dedupe_candidates(candidates))


def normalize_issue(raw: Any, *, default_repo: str | None = None) -> IssueCandidate | None:
    """Normalize one raw GitHub issue object, returning ``None`` if unusable."""
    if not isinstance(raw, Mapping):
        return None
    repo = _repo_from_issue(raw) or default_repo
    number = _number_from_issue(raw)
    if not repo or number is None:
        return None
    labels = _labels_from_issue(raw)
    assignees = _assignees_from_issue(raw)
    return IssueCandidate(
        repo=repo,
        number=number,
        title=str(raw.get("title") or ""),
        url=_url_from_issue(raw),
        state=str(raw.get("state") or "open"),
        labels=labels,
        assignees=assignees,
        body=str(raw.get("body") or ""),
        work_class=_declared_field(raw, "work_class"),
        mutation_class=_declared_field(raw, "mutation_class"),
        raw=raw,
    )


def plan_triage(
    *,
    arc_ticket: str,
    issues: Any,
    repo: str | None = None,
    pickup_label: str = DEFAULT_PICKUP_LABEL,
    assign_to: Sequence[str] = (),
    gh_runner: GhRunner | None = None,
    commissioned_predicate: CommissionedPredicateConfig | Mapping[str, Any] | None = None,
) -> TriageResult:
    """Plan deterministic pickup actions for unblocked, unclaimed issues.

    Supplying ``gh_runner`` enables live in-flight PR and work-claim collision
    checks; no mutation happens here. Use :func:`apply_triage_result` for
    explicit writes.
    """
    candidates = normalize_issue_payloads(issues, default_repo=repo)
    arc_key = _parse_arc_ticket(arc_ticket, repo)
    if arc_key is None:
        raise ForgeTriageError(
            "arc ticket is invalid or ambiguous; use owner/name#N, a GitHub issue URL, "
            "or N with --repo"
        )
    arc_work_key = arc_key.work_key
    arc_candidate = _find_arc_candidate(candidates, arc_work_key)
    arc_held_refs = _extract_arc_held_checkpoint_refs(arc_candidate) if arc_candidate else {}
    commissioned_unscheduled_status = (
        "verified" if arc_candidate is not None else "arc_missing"
    )
    commissioned_unscheduled = _commissioned_unscheduled_items(
        candidates,
        arc_work_key=arc_work_key,
        arc_candidate=arc_candidate,
        config=_normalize_commissioned_predicate(commissioned_predicate),
    )
    candidates = _filter_candidates_by_arc_refs(
        candidates,
        arc_work_key,
        arc_candidate=arc_candidate,
    )
    normalized_label = _require_label(pickup_label)
    seats = _normalize_seats(assign_to)
    pickup_query_hint = f"--label {normalized_label}"

    items: list[TriageAction] = []
    skipped: list[Mapping[str, Any]] = []
    seat_index = 0
    for candidate in candidates:
        skip_reason = _skip_reason(
            candidate,
            arc_work_key=arc_work_key,
            arc_held_refs=arc_held_refs,
            gh_runner=gh_runner,
        )
        if skip_reason is not None:
            skipped.append(_skip_record(candidate, skip_reason))
            continue

        work_class = _infer_work_class(candidate)
        mutation_class = _infer_mutation_class(candidate)
        sizing = dict(size_ceremony(work_class, mutation_class))
        sizing["intent_ref"] = candidate.work_key.work_key

        seat = None
        mutations: list[PlannedMutation] = []
        if normalized_label not in candidate.labels:
            mutations.append(PlannedMutation("add_label", normalized_label))
        if seats:
            seat = seats[seat_index % len(seats)]
            seat_index += 1
            mutations.append(PlannedMutation("assign", seat))

        items.append(
            TriageAction(
                issue=candidate,
                arc_ticket=arc_ticket,
                work_class=work_class,
                mutation_class=mutation_class,
                sizing=sizing,
                pickup_label=normalized_label,
                pickup_query_hint=pickup_query_hint,
                seat=seat,
                mutations=tuple(mutations),
            )
        )

    return TriageResult(
        arc_ticket=arc_ticket,
        arc_work_key=arc_work_key,
        pickup_label=normalized_label,
        pickup_query_hint=pickup_query_hint,
        applied=False,
        items=tuple(items),
        commissioned_unscheduled=commissioned_unscheduled,
        commissioned_unscheduled_status=commissioned_unscheduled_status,
        skipped=tuple(skipped),
    )


def apply_triage_result(result: TriageResult, gh_runner: GhRunner) -> TriageResult:
    """Apply a planned result's label/assignee mutations through ``gh api``."""
    applied_items: list[TriageAction] = []
    for item in result.items:
        applied_mutations: list[PlannedMutation] = []
        for mutation in item.mutations:
            if mutation.status != "planned":
                applied_mutations.append(mutation)
                continue
            _apply_mutation(item.issue, mutation, gh_runner)
            applied_mutations.append(
                PlannedMutation(mutation.kind, mutation.value, status="applied")
            )
        applied_items.append(
            TriageAction(
                issue=item.issue,
                arc_ticket=item.arc_ticket,
                work_class=item.work_class,
                mutation_class=item.mutation_class,
                sizing=item.sizing,
                pickup_label=item.pickup_label,
                pickup_query_hint=item.pickup_query_hint,
                seat=item.seat,
                mutations=tuple(applied_mutations),
            )
        )
    return TriageResult(
        arc_ticket=result.arc_ticket,
        arc_work_key=result.arc_work_key,
        pickup_label=result.pickup_label,
        pickup_query_hint=result.pickup_query_hint,
        applied=True,
        items=tuple(applied_items),
        commissioned_unscheduled=result.commissioned_unscheduled,
        commissioned_unscheduled_status=result.commissioned_unscheduled_status,
        skipped=result.skipped,
    )


def _issue_payloads(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return list(payload)
    if isinstance(payload, Mapping):
        for key in ("items", "issues", "nodes"):
            value = payload.get(key)
            if isinstance(value, list):
                return list(value)
    raise ForgeTriageError("issues JSON must be a list or an object with items/issues/nodes")


def _dedupe_candidates(candidates: Sequence[IssueCandidate]) -> list[IssueCandidate]:
    seen: set[tuple[str, int]] = set()
    out: list[IssueCandidate] = []
    for candidate in sorted(candidates, key=lambda c: (c.repo.lower(), c.number)):
        key = (candidate.repo.lower(), candidate.number)
        if key in seen:
            continue
        seen.add(key)
        out.append(candidate)
    return out


def _filter_candidates_by_arc_refs(
    candidates: Sequence[IssueCandidate],
    arc_work_key: str | None,
    *,
    arc_candidate: IssueCandidate | None = None,
) -> tuple[IssueCandidate, ...]:
    if arc_work_key is None:
        return tuple(candidates)
    arc_candidate = arc_candidate or _find_arc_candidate(candidates, arc_work_key)
    if arc_candidate is None:
        return tuple(candidates)
    refs_by_repo = _extract_arc_issue_refs(arc_candidate)
    if not refs_by_repo:
        return tuple(candidates)

    filtered: list[IssueCandidate] = []
    for candidate in candidates:
        if candidate.work_key.work_key == arc_work_key:
            continue
        candidate_repo = candidate.repo.lower()
        referenced_numbers = refs_by_repo.get(candidate_repo)
        if referenced_numbers is not None and candidate.number in referenced_numbers:
            filtered.append(candidate)
    return tuple(filtered)


def _commissioned_unscheduled_items(
    candidates: Sequence[IssueCandidate],
    *,
    arc_work_key: str | None,
    arc_candidate: IssueCandidate | None,
    config: CommissionedPredicateConfig,
) -> tuple[CommissionedUnscheduledItem, ...]:
    if arc_work_key is None or arc_candidate is None:
        return ()
    refs_by_repo = _extract_arc_issue_refs(arc_candidate)
    items: list[CommissionedUnscheduledItem] = []
    for candidate in candidates:
        if candidate.work_key.work_key == arc_work_key:
            continue
        if _issue_ref_contains(refs_by_repo, candidate):
            continue
        if candidate.state.strip().lower() != "open":
            continue
        if _has_milestone(candidate):
            continue
        if _has_done_label(candidate) or _is_aggregate_issue(candidate):
            continue
        commissioned_by = _commissioned_by(candidate, config)
        if not commissioned_by:
            continue
        items.append(
            CommissionedUnscheduledItem(
                issue=candidate,
                commissioned_by=commissioned_by,
            )
        )
    return tuple(sorted(items, key=lambda item: (item.issue.repo.lower(), item.issue.number)))


def _normalize_commissioned_predicate(
    raw: CommissionedPredicateConfig | Mapping[str, Any] | None,
) -> CommissionedPredicateConfig:
    if raw is None:
        return CommissionedPredicateConfig()
    if isinstance(raw, CommissionedPredicateConfig):
        return raw
    labels = raw.get("user_story_labels", DEFAULT_USER_STORY_LABELS)
    authors = raw.get("operator_author_logins", DEFAULT_OPERATOR_AUTHOR_LOGINS)
    return CommissionedPredicateConfig(
        user_story_labels=_string_tuple(labels),
        operator_author_logins=_string_tuple(authors),
    )


def _commissioned_by(
    candidate: IssueCandidate,
    config: CommissionedPredicateConfig,
) -> tuple[str, ...]:
    reasons: list[str] = []
    configured_labels = {_label_key(label) for label in config.user_story_labels}
    candidate_labels = {_label_key(label) for label in candidate.labels}
    for label in sorted(candidate_labels.intersection(configured_labels)):
        reasons.append(f"label:{label}")

    author = _issue_author_login(candidate)
    configured_authors = {_label_key(login) for login in config.operator_author_logins}
    if author and _label_key(author) in configured_authors:
        reasons.append(f"author:{author}")
    return tuple(_dedupe_strings(reasons))


def _issue_author_login(candidate: IssueCandidate) -> str | None:
    raw = candidate.raw or {}
    if not isinstance(raw, Mapping):
        return None
    for key in ("user", "author", "created_by", "createdBy"):
        value = raw.get(key)
        if isinstance(value, Mapping):
            login = value.get("login") or value.get("name")
            if isinstance(login, str) and login.strip():
                return login.strip()
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in ("user_login", "author_login", "created_by_login"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _has_milestone(candidate: IssueCandidate) -> bool:
    raw = candidate.raw or {}
    if not isinstance(raw, Mapping):
        return False
    value = raw.get("milestone")
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return bool(value)
    return True


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        values = (value,)
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        values = value
    else:
        values = (value,)
    return tuple(str(item).strip() for item in values if str(item).strip())


def _find_arc_candidate(
    candidates: Sequence[IssueCandidate],
    arc_work_key: str,
) -> IssueCandidate | None:
    for candidate in candidates:
        if candidate.work_key.work_key == arc_work_key:
            return candidate
    return None


def _extract_arc_issue_refs(candidate: IssueCandidate) -> Mapping[str, frozenset[int]]:
    text = f"{candidate.title}\n{candidate.body}"
    return _extract_issue_refs(text, candidate.repo)


def _extract_arc_held_checkpoint_refs(
    candidate: IssueCandidate,
) -> Mapping[str, frozenset[int]]:
    refs: dict[str, set[int]] = {}
    in_held_list = False
    for line in candidate.body.splitlines():
        if _HELD_CHECKPOINT_LINE_RE.search(line):
            in_held_list = True
            _merge_issue_refs(refs, _extract_issue_refs(line, candidate.repo))
            continue
        if in_held_list and _MARKDOWN_HEADING_RE.match(line):
            break
        if in_held_list:
            _merge_issue_refs(refs, _extract_issue_refs(line, candidate.repo))
    return {repo: frozenset(numbers) for repo, numbers in refs.items()}


def _extract_issue_refs(text: str, default_repo: str) -> Mapping[str, frozenset[int]]:
    refs: dict[str, set[int]] = {}
    for match in _GITHUB_REF_URL_RE.finditer(text):
        _add_issue_ref(refs, f"{match.group(1)}/{match.group(2)}", int(match.group(3)))
    for match in _GITHUB_API_ISSUE_RE.finditer(text):
        _add_issue_ref(refs, f"{match.group(1)}/{match.group(2)}", int(match.group(3)))
    for match in _OWNER_REPO_REF_RE.finditer(text):
        _add_issue_ref(refs, match.group(1), int(match.group(2)))
    for match in _SHORT_REPO_REF_RE.finditer(text):
        _add_issue_ref(refs, _repo_for_short_ref(match.group(1), default_repo), int(match.group(2)))
    for match in _BARE_ISSUE_REF_RE.finditer(text):
        _add_issue_ref(refs, default_repo, int(match.group(1)))

    return {repo: frozenset(numbers) for repo, numbers in refs.items()}


def _merge_issue_refs(target: dict[str, set[int]], source: Mapping[str, frozenset[int]]) -> None:
    for repo, numbers in source.items():
        target.setdefault(repo, set()).update(numbers)


def _repo_for_short_ref(short_repo: str, arc_repo: str) -> str:
    owner, repo = arc_repo.split("/", 1)
    if short_repo.lower() == repo.lower():
        return arc_repo
    return f"{owner}/{short_repo}"


def _add_issue_ref(refs: dict[str, set[int]], repo: str, number: int) -> None:
    refs.setdefault(repo.lower(), set()).add(number)


def _repo_from_issue(raw: Mapping[str, Any]) -> str | None:
    for key in ("repo", "repository_full_name", "repo_full_name"):
        value = raw.get(key)
        if isinstance(value, str) and "/" in value:
            return value
    repository = raw.get("repository")
    if isinstance(repository, Mapping):
        for key in ("full_name", "nameWithOwner"):
            value = repository.get(key)
            if isinstance(value, str) and "/" in value:
                return value
    for key in ("repository_url", "url", "html_url"):
        value = raw.get(key)
        if isinstance(value, str):
            api_match = _API_REPO_RE.search(value)
            if api_match:
                return f"{api_match.group(1)}/{api_match.group(2)}"
            web_match = _GITHUB_ISSUE_RE.search(value)
            if web_match:
                return f"{web_match.group(1)}/{web_match.group(2)}"
    return None


def _number_from_issue(raw: Mapping[str, Any]) -> int | None:
    number = raw.get("number")
    try:
        return int(number)
    except (TypeError, ValueError):
        pass
    url = raw.get("html_url") or raw.get("url")
    if isinstance(url, str):
        match = _GITHUB_ISSUE_RE.search(url)
        if match:
            return int(match.group(3))
    return None


def _url_from_issue(raw: Mapping[str, Any]) -> str | None:
    for key in ("html_url", "url"):
        value = raw.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _labels_from_issue(raw: Mapping[str, Any]) -> tuple[str, ...]:
    values = raw.get("labels") or raw.get("label_names") or ()
    labels: list[str] = []
    if isinstance(values, (str, Mapping)):
        values = (values,)
    for value in (values if isinstance(values, Sequence) else ()):
        label: str | None = None
        if isinstance(value, str):
            label = value
        elif isinstance(value, Mapping) and isinstance(value.get("name"), str):
            label = value["name"]
        if label:
            labels.append(label.strip())
    return tuple(label for label in labels if label)


def _assignees_from_issue(raw: Mapping[str, Any]) -> tuple[str, ...]:
    values = raw.get("assignees") or ()
    if not values and raw.get("assignee"):
        values = (raw.get("assignee"),)
    assignees: list[str] = []
    if isinstance(values, (str, Mapping)):
        values = (values,)
    for value in (values if isinstance(values, Sequence) else ()):
        login: str | None = None
        if isinstance(value, str):
            login = value
        elif isinstance(value, Mapping) and isinstance(value.get("login"), str):
            login = value["login"]
        if login:
            assignees.append(login.strip())
    return tuple(login for login in assignees if login)


def _declared_field(raw: Mapping[str, Any], key: str) -> str | None:
    for source in (raw, raw.get("creator_engine")):
        if not isinstance(source, Mapping):
            continue
        value = source.get(key) or source.get(key.replace("_", "-"))
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return None


def _parse_arc_ticket(raw: str, repo: str | None) -> work_claims.WorkKey | None:
    try:
        return work_claims.parse_ticket(raw, repo)
    except work_claims.WorkClaimError:
        if repo:
            match = _SHORT_TICKET_RE.match(str(raw).strip())
            if match:
                try:
                    return work_claims.parse_ticket(match.group(1), repo)
                except work_claims.WorkClaimError:
                    return None
        return None


def _require_label(label: str) -> str:
    text = str(label or "").strip()
    if not text:
        raise ForgeTriageError("pickup label must be non-empty")
    return text


def _normalize_seats(assign_to: Sequence[str]) -> tuple[str, ...]:
    seats: list[str] = []
    seen: set[str] = set()
    for raw in assign_to or ():
        for part in str(raw).split(","):
            seat = part.strip()
            if seat and seat not in seen:
                seen.add(seat)
                seats.append(seat)
    return tuple(seats)


def _skip_reason(
    candidate: IssueCandidate,
    *,
    arc_work_key: str | None,
    arc_held_refs: Mapping[str, frozenset[int]],
    gh_runner: GhRunner | None,
) -> str | None:
    if arc_work_key and candidate.work_key.work_key == arc_work_key:
        return "arc_ticket"
    if candidate.state.strip().lower() != "open":
        return "not_open"
    if _has_done_label(candidate):
        return "closed_or_done"
    if _is_aggregate_issue(candidate):
        return "aggregate_issue"
    if _issue_ref_contains(arc_held_refs, candidate):
        return "held_checkpoint"
    if _body_carries_hold_marker(candidate):
        return "held_marker"
    if candidate.assignees:
        return "already_assigned"
    readiness = readiness_blockers(candidate)
    if readiness:
        return readiness[0]
    if gh_runner is not None:
        linked_pr = _linked_pr_status(candidate, gh_runner)
        if linked_pr is None:
            return "linked_pr_status_unavailable"
        if linked_pr == "open":
            return "open_pr"
        if linked_pr == "done":
            return "done_pr"
        hold_marker = _comments_carry_hold_marker(candidate, gh_runner)
        if hold_marker is None:
            return "hold_marker_status_unavailable"
        if hold_marker:
            return "held_marker"
        try:
            status = work_claims.status(candidate.work_key, gh_runner)
        except work_claims.WorkClaimError:
            return "claim_status_unavailable"
        if status.state.active is not None:
            return "active_claim"
    return None


def readiness_blockers(candidate: IssueCandidate) -> tuple[str, ...]:
    """Return deterministic readiness/dependency blockers for one issue."""
    reasons: list[str] = []
    lower_labels = {_label_key(label) for label in candidate.labels}
    if lower_labels.intersection(_BLOCKING_LABELS):
        reasons.append("blocked_label")
    if any(label.startswith(_BLOCKING_LABEL_PREFIXES) for label in lower_labels):
        reasons.append("blocked_label")
    raw = candidate.raw or {}
    for field in _DEPENDENCY_FIELDS:
        value = raw.get(field) if isinstance(raw, Mapping) else None
        if _non_empty_dependency_value(value):
            reasons.append("blocked_dependency")
            break
    if _DEPENDENCY_BODY_RE.search(candidate.body):
        reasons.append("blocked_dependency")
    return tuple(_dedupe_strings(reasons))


def _has_done_label(candidate: IssueCandidate) -> bool:
    labels = {_label_key(label) for label in candidate.labels}
    return bool(labels.intersection(_DONE_LABELS))


def _is_aggregate_issue(candidate: IssueCandidate) -> bool:
    labels = {_label_key(label) for label in candidate.labels}
    if labels.intersection(_AGGREGATE_LABELS):
        return True
    try:
        if normalize_work_class(candidate.work_class or "") == "L":
            return True
    except ValueError:
        pass
    if _AGGREGATE_TITLE_RE.search(candidate.title):
        return True
    raw = candidate.raw or {}
    if isinstance(raw, Mapping):
        if _raw_aggregate_marker(raw):
            return True
        if raw.get("pull_request"):
            return True
        for key in ("aggregate", "is_aggregate", "leaf", "leaf_work_item"):
            value = raw.get(key)
            if key in {"leaf", "leaf_work_item"} and value is False:
                return True
            if key in {"aggregate", "is_aggregate"} and value is True:
                return True
    return False


def _raw_aggregate_marker(raw: Mapping[str, Any]) -> bool:
    for key in ("kind", "type", "issue_type", "item_type", "category"):
        value = raw.get(key)
        if isinstance(value, Mapping):
            value = value.get("name") or value.get("kind")
        if isinstance(value, str) and _label_key(value) in _AGGREGATE_LABELS:
            return True
    return False


def _issue_ref_contains(refs: Mapping[str, frozenset[int]], candidate: IssueCandidate) -> bool:
    return candidate.number in refs.get(candidate.repo.lower(), frozenset())


def _body_carries_hold_marker(candidate: IssueCandidate) -> bool:
    return bool(_HOLD_MARKER_RE.search(candidate.body))


def _linked_pr_status(
    candidate: IssueCandidate,
    gh_runner: GhRunner,
) -> str | None:
    """Classify the issue's linked PR work as open/done/none.

    Returns ``"open"`` for an in-flight linked PR, ``"done"`` for a linked PR
    that has merged or closed-as-done (the issue stayed open behind it),
    ``"none"`` when no linked PR is found, and ``None`` (fail closed) on any
    ambiguous event or incomplete/failed lookup. Mirrors the #194 paginated,
    fail-closed timeline scan.
    """
    ambiguous = False
    done_seen = False
    for page in range(1, _TIMELINE_MAX_PAGES + 1):
        query = urllib.parse.urlencode(
            {"per_page": str(_TIMELINE_PAGE_SIZE), "page": str(page)}
        )
        path = f"repos/{candidate.repo}/issues/{candidate.number}/timeline?{query}"
        try:
            proc = gh_runner(["gh", "api", "--method", "GET", path], None)
        except (OSError, subprocess.SubprocessError):
            return None
        if getattr(proc, "returncode", 1) != 0:
            return None
        try:
            payload = json.loads((getattr(proc, "stdout", "") or "").strip())
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        if not isinstance(payload, list):
            return None

        for raw_event in payload:
            state = _linked_pr_state_from_timeline_event(raw_event)
            if state == "open":
                return "open"
            if state == "done":
                done_seen = True
            if state is None:
                ambiguous = True
        if len(payload) < _TIMELINE_PAGE_SIZE:
            if ambiguous:
                return None
            return "done" if done_seen else "none"
    return None


def _linked_pr_state_from_timeline_event(raw_event: Any) -> str | None:
    if not isinstance(raw_event, Mapping):
        return "none"
    candidates: list[Any] = []
    for key in ("source", "subject"):
        source = raw_event.get(key)
        if isinstance(source, Mapping):
            candidates.append(source.get("issue"))
    candidates.append(raw_event)

    ambiguous = False
    done_seen = False
    for issue in candidates:
        state = _linked_pr_state_from_issue_mapping(issue)
        if state == "open":
            return "open"
        if state == "done":
            done_seen = True
        if state is None:
            ambiguous = True
    if ambiguous:
        return None
    return "done" if done_seen else "none"


def _linked_pr_state_from_issue_mapping(issue: Any) -> str | None:
    if not isinstance(issue, Mapping):
        return "none"
    pull_request = issue.get("pull_request")
    is_pr = "pull_request" in issue and pull_request is not None
    if not is_pr:
        url = issue.get("url") or issue.get("html_url")
        if not (isinstance(url, str) and "/pull/" in url):
            return "none"
    # A merged PR is "done" regardless of the recorded state string.
    if isinstance(pull_request, Mapping) and pull_request.get("merged_at"):
        return "done"
    if issue.get("merged") is True or issue.get("merged_at"):
        return "done"
    state = issue.get("state")
    if not isinstance(state, str):
        return None
    state_lower = state.lower()
    if state_lower == "open":
        return "open"
    if state_lower == "closed":
        return "done"
    return None


def _comments_carry_hold_marker(
    candidate: IssueCandidate,
    gh_runner: GhRunner,
) -> bool | None:
    """Return whether any issue comment carries a hold marker.

    Paginated and fail-closed like the timeline scan: any failed/malformed
    lookup returns ``None`` so the caller excludes the candidate rather than
    leak a possibly-held item.
    """
    for page in range(1, _COMMENT_MAX_PAGES + 1):
        query = urllib.parse.urlencode(
            {"per_page": str(_COMMENT_PAGE_SIZE), "page": str(page)}
        )
        path = f"repos/{candidate.repo}/issues/{candidate.number}/comments?{query}"
        try:
            proc = gh_runner(["gh", "api", "--method", "GET", path], None)
        except (OSError, subprocess.SubprocessError):
            return None
        if getattr(proc, "returncode", 1) != 0:
            return None
        try:
            payload = json.loads((getattr(proc, "stdout", "") or "").strip())
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        if not isinstance(payload, list):
            return None
        for raw_comment in payload:
            if not isinstance(raw_comment, Mapping):
                return None
            body = raw_comment.get("body")
            if isinstance(body, str) and _HOLD_MARKER_RE.search(body):
                return True
        if len(payload) < _COMMENT_PAGE_SIZE:
            return False
    return None


def _skip_record(candidate: IssueCandidate, reason: str) -> dict[str, Any]:
    return {
        "repo": candidate.repo,
        "number": candidate.number,
        "work_key": candidate.work_key.work_key,
        "reason": reason,
    }


def _infer_work_class(candidate: IssueCandidate) -> str:
    declared = (candidate.work_class or "").strip()
    try:
        return normalize_work_class(declared)
    except ValueError:
        pass
    labels = {_label_key(label) for label in candidate.labels}
    for alias, work_class in WORK_CLASS_ALIASES.items():
        label_value = alias.lower()
        if label_value in labels:
            return work_class
        for prefix in ("work:", "work/", "work_class:", "work-class:", "size:", "size/"):
            if f"{prefix}{label_value}" in labels:
                return work_class
    return "S"


def _infer_mutation_class(candidate: IssueCandidate) -> str:
    declared = (candidate.mutation_class or "").strip().lower()
    if declared in MUTATION_CLASSES:
        return declared
    labels = {_label_key(label) for label in candidate.labels}
    for mutation_class in MUTATION_CLASSES:
        if mutation_class in labels:
            return mutation_class
        for prefix in ("mutation:", "mutation/", "mutation_class:", "mutation-class:"):
            if f"{prefix}{mutation_class}" in labels:
                return mutation_class
    if {"docs", "documentation"}.intersection(labels):
        return "docs"
    if {"schema", "contract", "contracts"}.intersection(labels):
        return "schema"
    if {"deploy", "release"}.intersection(labels):
        return "deploy"
    return "code"


def _label_key(label: str) -> str:
    return str(label or "").strip().lower()


def _non_empty_dependency_value(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return any(_non_empty_dependency_value(v) for v in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_non_empty_dependency_value(v) for v in value)
    return bool(value)


def _dedupe_strings(values: Sequence[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _apply_mutation(issue: IssueCandidate, mutation: PlannedMutation, gh_runner: GhRunner) -> None:
    if mutation.kind == "add_label":
        path = f"repos/{issue.repo}/issues/{issue.number}/labels"
        body = {"labels": [mutation.value]}
    elif mutation.kind == "assign":
        path = f"repos/{issue.repo}/issues/{issue.number}/assignees"
        body = {"assignees": [mutation.value]}
    else:
        raise ForgeTriageError(f"unknown planned mutation kind: {mutation.kind}")
    proc = gh_runner(
        ["gh", "api", "--method", "POST", path, "--input", "-"],
        json.dumps(body),
    )
    if getattr(proc, "returncode", 1) != 0:
        stderr = (getattr(proc, "stderr", "") or "").strip()
        detail = f": {stderr}" if stderr else ""
        raise ForgeTriageError(f"gh api failed applying {mutation.kind} to {issue.repo}#{issue.number}{detail}")
