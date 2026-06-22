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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Callable

from . import work_claims
from .work_sizing import MUTATION_CLASSES, WORK_CLASSES, size_ceremony

GhRunner = Callable[[Sequence[str], "str | None"], subprocess.CompletedProcess]

DEFAULT_PICKUP_LABEL = "ce-pickup/triage-ready"
SCHEMA_VERSION = 1

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

_BLOCKING_LABELS = frozenset(
    {
        "blocked",
        "dependency-blocked",
        "dependencies-blocked",
        "do-not-pickup",
        "do not pickup",
        "hold",
        "on-hold",
        "on hold",
        "status:blocked",
        "waiting",
        "wip",
    }
)
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
) -> TriageResult:
    """Plan deterministic pickup actions for unblocked, unclaimed issues.

    Supplying ``gh_runner`` enables live work-claim collision checks only; no
    mutation happens here. Use :func:`apply_triage_result` for explicit writes.
    """
    candidates = normalize_issue_payloads(issues, default_repo=repo)
    arc_key = _parse_arc_ticket(arc_ticket, repo)
    arc_work_key = arc_key.work_key if arc_key is not None else None
    candidates = _filter_candidates_by_arc_refs(candidates, arc_work_key)
    normalized_label = _require_label(pickup_label)
    seats = _normalize_seats(assign_to)
    pickup_query_hint = f"--label {normalized_label}"

    items: list[TriageAction] = []
    skipped: list[Mapping[str, Any]] = []
    seat_index = 0
    for candidate in candidates:
        skip_reason = _skip_reason(candidate, arc_work_key=arc_work_key, gh_runner=gh_runner)
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
) -> tuple[IssueCandidate, ...]:
    if arc_work_key is None:
        return tuple(candidates)
    arc_candidate = _find_arc_candidate(candidates, arc_work_key)
    if arc_candidate is None:
        return tuple(candidates)
    refs_by_repo = _extract_arc_issue_refs(arc_candidate)
    if not refs_by_repo:
        return tuple(candidates)

    arc_repo = arc_candidate.repo.lower()
    filtered: list[IssueCandidate] = []
    for candidate in candidates:
        if candidate.work_key.work_key == arc_work_key:
            continue
        candidate_repo = candidate.repo.lower()
        referenced_numbers = refs_by_repo.get(candidate_repo)
        if referenced_numbers is not None:
            if candidate.number in referenced_numbers:
                filtered.append(candidate)
            continue
        if candidate_repo == arc_repo:
            continue
        filtered.append(candidate)
    return tuple(filtered)


def _find_arc_candidate(
    candidates: Sequence[IssueCandidate],
    arc_work_key: str,
) -> IssueCandidate | None:
    for candidate in candidates:
        if candidate.work_key.work_key == arc_work_key:
            return candidate
    return None


def _extract_arc_issue_refs(candidate: IssueCandidate) -> Mapping[str, frozenset[int]]:
    refs: dict[str, set[int]] = {}
    text = f"{candidate.title}\n{candidate.body}"
    arc_repo = candidate.repo

    for match in _GITHUB_REF_URL_RE.finditer(text):
        _add_issue_ref(refs, f"{match.group(1)}/{match.group(2)}", int(match.group(3)))
    for match in _GITHUB_API_ISSUE_RE.finditer(text):
        _add_issue_ref(refs, f"{match.group(1)}/{match.group(2)}", int(match.group(3)))
    for match in _OWNER_REPO_REF_RE.finditer(text):
        _add_issue_ref(refs, match.group(1), int(match.group(2)))
    for match in _SHORT_REPO_REF_RE.finditer(text):
        _add_issue_ref(refs, _repo_for_short_ref(match.group(1), arc_repo), int(match.group(2)))
    for match in _BARE_ISSUE_REF_RE.finditer(text):
        _add_issue_ref(refs, arc_repo, int(match.group(1)))

    return {repo: frozenset(numbers) for repo, numbers in refs.items()}


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
    gh_runner: GhRunner | None,
) -> str | None:
    if arc_work_key and candidate.work_key.work_key == arc_work_key:
        return "arc_ticket"
    if candidate.state.lower() != "open":
        return "not_open"
    if candidate.assignees:
        return "already_assigned"
    readiness = readiness_blockers(candidate)
    if readiness:
        return readiness[0]
    if gh_runner is not None:
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
    if any(label.startswith("blocked:") for label in lower_labels):
        reasons.append("blocked_label")
    raw = candidate.raw or {}
    for field in _DEPENDENCY_FIELDS:
        value = raw.get(field) if isinstance(raw, Mapping) else None
        if _non_empty_dependency_value(value):
            reasons.append("blocked_dependency")
            break
    if re.search(r"\b(blocked by|depends on|dependency:)\s+#?\d+", candidate.body, re.IGNORECASE):
        reasons.append("blocked_dependency")
    return tuple(_dedupe_strings(reasons))


def _skip_record(candidate: IssueCandidate, reason: str) -> dict[str, Any]:
    return {
        "repo": candidate.repo,
        "number": candidate.number,
        "work_key": candidate.work_key.work_key,
        "reason": reason,
    }


def _infer_work_class(candidate: IssueCandidate) -> str:
    declared = (candidate.work_class or "").strip().lower()
    if declared in WORK_CLASSES:
        return declared
    labels = {_label_key(label) for label in candidate.labels}
    for work_class in WORK_CLASSES:
        if work_class in labels:
            return work_class
        for prefix in ("work:", "work/", "work_class:", "work-class:", "size:", "size/"):
            if f"{prefix}{work_class}" in labels:
                return work_class
    return "story"


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
