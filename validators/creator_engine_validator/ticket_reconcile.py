"""Report-only stale ce-ops ticket reconciliation.

The functions in this module operate on caller-provided data only. They do not
fetch issue or pull-request state, mutate tickets, or infer fuzzy title matches.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_TICKET_REPO = "creator-engine/ce-ops"
EVIDENCE_BRANCH = "branch"
EVIDENCE_TICKET_REF = "ticket-ref"
EVIDENCE_ORDER = (EVIDENCE_BRANCH, EVIDENCE_TICKET_REF)


@dataclass(frozen=True, order=True)
class OpenTicket:
    """Open ticket input for stale-ticket reconciliation."""

    number: int
    title: str = ""
    branch_slug_hints: tuple[str, ...] = ()


@dataclass(frozen=True, order=True)
class MergedPullRequest:
    """Merged pull request input for stale-ticket reconciliation."""

    number: int
    title: str = ""
    head_branch: str = ""
    body: str = ""


@dataclass(frozen=True, order=True)
class StaleTicketMatch:
    """Report-only indication that a merged PR appears to satisfy an open ticket."""

    ticket_number: int
    pr_number: int
    evidence: tuple[str, ...]
    ticket_repo: str = DEFAULT_TICKET_REPO

    @property
    def evidence_tag(self) -> str:
        return "+".join(self.evidence)

    @property
    def report_line(self) -> str:
        repo_name = self.ticket_repo.rsplit("/", 1)[-1]
        return (
            f"STALE-OPEN {repo_name}#{self.ticket_number} <- PR#{self.pr_number} "
            f"({self.evidence_tag})"
        )


def reconcile_stale_tickets(
    open_tickets: Sequence[Mapping[str, Any] | OpenTicket],
    merged_prs: Sequence[Mapping[str, Any] | MergedPullRequest],
    *,
    ticket_repo: str = DEFAULT_TICKET_REPO,
    reference_numbers: Callable[[str, str], Sequence[int]] | None = None,
) -> list[StaleTicketMatch]:
    """Return deterministic report-only stale-ticket matches.

    Generic matching (the compatibility default) is intentionally conservative:
    - PR head branch contains ``ce-<ticket-number>-`` or a supplied branch hint.
    - PR title/body contains ``ce-ops#<ticket-number>`` or the fully qualified
      ``owner/ce-ops#<ticket-number>`` ticket reference.

    When ``reference_numbers`` is supplied, reconciliation switches to the
    fixed CE-ops advisory projection: a pair is retained only when the
    normalized branch contains the literal ``ce-<ticket-number>-`` marker and
    the canonical parser does *not* see that ticket in the PR title/body.  The
    parser is evaluated once per PR so the projection is deterministic and a
    caller can inject the shared production grammar without copying it here.
    """

    tickets = [_coerce_ticket(item) for item in open_tickets]
    prs = [_coerce_pr(item) for item in merged_prs]
    matches: dict[tuple[int, int], set[str]] = {}

    parsed_refs: list[frozenset[int]] | None = None
    if reference_numbers is not None:
        parsed_refs = [
            _coerce_reference_numbers(reference_numbers(pr.title, pr.body))
            for pr in prs
        ]

    for ticket in tickets:
        for pr_index, pr in enumerate(prs):
            if parsed_refs is None:
                evidence = _evidence_for(ticket, pr, ticket_repo=ticket_repo)
            elif _literal_branch_matches(ticket.number, pr.head_branch) and (
                ticket.number not in parsed_refs[pr_index]
            ):
                evidence = (EVIDENCE_BRANCH,)
            else:
                evidence = ()
            if not evidence:
                continue
            matches.setdefault((ticket.number, pr.number), set()).update(evidence)

    return [
        StaleTicketMatch(ticket_number, pr_number, _ordered_evidence(evidence), ticket_repo)
        for (ticket_number, pr_number), evidence in sorted(matches.items())
    ]


def render_report(matches: Sequence[StaleTicketMatch]) -> str:
    """Render deterministic text report lines."""

    lines = [match.report_line for match in sorted(matches)]
    return "\n".join(lines)


def render_json(matches: Sequence[StaleTicketMatch]) -> str:
    """Render machine-readable JSON for reconciliation results."""

    payload = {
        "matches": [
            {
                "evidence": list(match.evidence),
                "evidence_tag": match.evidence_tag,
                "pr_number": match.pr_number,
                "report_line": match.report_line,
                "ticket_number": match.ticket_number,
            }
            for match in sorted(matches)
        ]
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def load_tickets_json(path: str | Path) -> list[Mapping[str, Any]]:
    """Load ticket input from a JSON file.

    Accepted shapes are either a top-level list or a mapping with ``tickets``.
    """

    data = _load_json(path)
    if isinstance(data, list):
        return data
    if isinstance(data, Mapping) and isinstance(data.get("tickets"), list):
        return data["tickets"]
    raise ValueError("ticket JSON must be a list or object with a tickets list")


def load_prs_json(path: str | Path) -> list[Mapping[str, Any]]:
    """Load merged PR input from a JSON file.

    Accepted shapes are a top-level list, ``pull_requests``, or ``prs``.
    """

    data = _load_json(path)
    if isinstance(data, list):
        return data
    if isinstance(data, Mapping):
        for key in ("pull_requests", "prs"):
            if isinstance(data.get(key), list):
                return data[key]
    raise ValueError("PR JSON must be a list or object with pull_requests/prs list")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tickets_json", help="JSON file with open ticket records")
    parser.add_argument("prs_json", help="JSON file with merged PR records")
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit machine-readable JSON",
    )
    parser.add_argument(
        "--ticket-repo",
        default=DEFAULT_TICKET_REPO,
        help="qualified ticket repository, default: creator-engine/ce-ops",
    )
    args = parser.parse_args(argv)

    try:
        matches = reconcile_stale_tickets(
            load_tickets_json(args.tickets_json),
            load_prs_json(args.prs_json),
            ticket_repo=args.ticket_repo,
        )
    except (OSError, ValueError, TypeError) as exc:
        print(f"ticket-reconcile: {exc}", file=sys.stderr)
        return 2

    output = render_json(matches) if args.json_output else render_report(matches)
    if output:
        print(output)
    return 0


def _coerce_ticket(item: Mapping[str, Any] | OpenTicket) -> OpenTicket:
    if isinstance(item, OpenTicket):
        return item
    if not isinstance(item, Mapping):
        raise TypeError(f"ticket must be a mapping, got {type(item).__name__}")
    number = _coerce_number(item.get("number"), "ticket number")
    return OpenTicket(
        number=number,
        title=str(item.get("title") or ""),
        branch_slug_hints=_coerce_hints(item),
    )


def _coerce_pr(item: Mapping[str, Any] | MergedPullRequest) -> MergedPullRequest:
    if isinstance(item, MergedPullRequest):
        return item
    if not isinstance(item, Mapping):
        raise TypeError(f"PR must be a mapping, got {type(item).__name__}")
    number = _coerce_number(item.get("number"), "PR number")
    return MergedPullRequest(
        number=number,
        title=str(item.get("title") or ""),
        head_branch=str(
            item.get("head_branch")
            or item.get("headBranch")
            or item.get("headRefName")
            or item.get("head_ref")
            or ""
        ),
        body=str(item.get("body") or ""),
    )


def _coerce_number(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise TypeError(f"{field} must be an integer")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{field} must be an integer") from exc
    if number <= 0:
        raise ValueError(f"{field} must be positive")
    return number


def _coerce_hints(item: Mapping[str, Any]) -> tuple[str, ...]:
    raw = (
        item.get("branch_slug_hints")
        or item.get("branch_slugs")
        or item.get("branch_hints")
        or ()
    )
    if isinstance(raw, str):
        raw = (raw,)
    if not isinstance(raw, Sequence):
        raise TypeError("branch slug hints must be a string or sequence")
    return tuple(str(hint).strip() for hint in raw if str(hint).strip())


def _evidence_for(
    ticket: OpenTicket,
    pr: MergedPullRequest,
    *,
    ticket_repo: str,
) -> tuple[str, ...]:
    evidence: list[str] = []
    if _branch_matches(ticket, pr.head_branch):
        evidence.append(EVIDENCE_BRANCH)
    if _ticket_ref_matches(ticket.number, f"{pr.title}\n{pr.body}", ticket_repo=ticket_repo):
        evidence.append(EVIDENCE_TICKET_REF)
    return tuple(evidence)


def _branch_matches(ticket: OpenTicket, head_branch: str) -> bool:
    branch = _normalise_branch(head_branch)
    if not branch:
        return False
    if f"ce-{ticket.number}-" in branch:
        return True
    # WARNING: hints are matched as substrings, not anchored patterns.
    return any(_normalise_branch(hint) in branch for hint in ticket.branch_slug_hints)


def _literal_branch_matches(ticket_number: int, head_branch: str) -> bool:
    branch = _normalise_branch(head_branch)
    return bool(branch) and f"ce-{ticket_number}-" in branch


def _coerce_reference_numbers(values: Sequence[int]) -> frozenset[int]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise TypeError("reference-number callback must return a sequence")
    return frozenset(_coerce_number(value, "reference number") for value in values)


def _ticket_ref_matches(ticket_number: int, text: str, *, ticket_repo: str) -> bool:
    lowered = text.lower()
    if not lowered:
        return False
    repo = ticket_repo.lower().strip()
    repo_name = repo.rsplit("/", 1)[-1]
    patterns = [
        rf"(?<![\w/.-]){re.escape(repo_name)}#{ticket_number}(?!\d)",
        rf"(?<![\w.-]){re.escape(repo)}#{ticket_number}(?!\d)",
    ]
    return any(re.search(pattern, lowered) for pattern in patterns)


def _ordered_evidence(evidence: set[str]) -> tuple[str, ...]:
    return tuple(tag for tag in EVIDENCE_ORDER if tag in evidence)


def _normalise_branch(value: str) -> str:
    branch = value.lower().strip()
    for prefix in ("refs/heads/", "origin/"):
        if branch.startswith(prefix):
            branch = branch[len(prefix) :]
    return branch


def _load_json(path: str | Path) -> Any:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


if __name__ == "__main__":
    raise SystemExit(main())
