"""CE v3 forge backlog adapter — Projects-v2 reader/writer + the forge-projected
claim (the v3.5-C **α-precursor** gate; consumed by A-C4).

Design §A.4 / A.0 invariant: **the forge is the only shared state.** A PCO
claim today lives instance-local (invisible to the other peer); a *team-visible*
claim is **projected onto the forge** — the backlog item's **assignee +
Projects `Status=Running`** — and that projection is **re-read and
drift-checked immediately before** the local claim.

**Advisory lock — honestly.** Assignee + Status are advisory, NOT atomic
(coordination-layer §11.1 claim-side TOCTOU). This module therefore ships:

- an **idempotency key** over ``(repo, item_id, claimant_instance,
  lease_window)`` (:func:`idempotency_key`);
- a **short randomized back-off + re-read after write**
  (:func:`claim_item`'s verify leg, with injectable back-off/sleep for
  deterministic tests);
- **"earlier-``claimed_at``-wins" reconciliation surfaced as an
  :class:`Escalation`** — never a silent overwrite. There is deliberately no
  ``force`` flag and no code path that overwrites a competing claim.

**Do not read this module as a hard lock. It is not one.** Two seats can
still interleave between the drift-check read and the write; the back-off +
re-read narrows the window and the escalation surfaces the collision to a
human. The webhook-ingestion plane (design §9.4) is OUT of scope — this is
the projection + drift-check, not a live receiver.

Like the rest of ``forge/``, every GitHub call goes through an injectable
:data:`GhRunner` (``gh`` subprocess by default); tests inject a fake runner
and perform **zero** live network/subprocess; importing this module performs
no I/O and registers no validator check. Reads/writes are split REST (issue
assignees) + GraphQL (Projects-v2 item Status / Claimed-at fields); the
caller supplies the project/field/option node ids in :class:`ProjectRef`
(discoverable once per project; this module never guesses them).
"""
from __future__ import annotations

import hashlib
import json
import random
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from ._redact import redact_gh_stderr
from .github_repo_config import ForgeConfigError, GhRunner

__ce_version_line__ = "v3"


# --- value types ---------------------------------------------------------------

@dataclass(frozen=True)
class ProjectRef:
    """The Projects-v2 coordinates of the ONE backlog (caller-discovered ids).

    ``repo`` is ``owner/name``; ``project_id`` the ``PVT_…`` node id;
    ``status_field_id`` the Status single-select field's node id;
    ``running_option_id`` the ``Running`` option id of that field;
    ``claimed_at_field_id`` an optional text field recording the claim
    timestamp (enables earlier-``claimed_at``-wins reconciliation).
    """

    repo: str
    project_id: str
    status_field_id: str
    running_option_id: str
    claimed_at_field_id: str | None = None


@dataclass(frozen=True)
class ItemRef:
    """One backlog item: the Projects-v2 item node + its Issue number."""

    item_id: str
    issue_number: int


@dataclass(frozen=True)
class BacklogItem:
    """The observed forge-side state of one backlog item (the shared truth)."""

    item_id: str
    status: str | None
    assignees: tuple[str, ...]
    claimed_at: str | None = None


@dataclass(frozen=True)
class ClaimPlan:
    """The plan-by-default result: what a live claim WOULD write."""

    item: ItemRef
    claimant_login: str
    claimed_at: str
    idempotency_key: str
    applied: bool = False


@dataclass(frozen=True)
class Escalation:
    """A claim collision surfaced for a HUMAN — never resolved by overwrite.

    ``winner`` follows earlier-``claimed_at``-wins where both timestamps are
    known; the reconciliation is REPORTED, not enforced — no claim is removed.
    """

    item: ItemRef
    reason: str
    observed: BacklogItem
    winner: str | None = None


@dataclass(frozen=True)
class DriftReport:
    """The drift-check verdict taken immediately before a local claim."""

    drifted: bool
    details: tuple[str, ...] = field(default=())


# --- pure helpers ----------------------------------------------------------------

def idempotency_key(
    repo: str, item_id: str, claimant_instance: str, lease_window: str
) -> str:
    """The deterministic claim idempotency key (§11.1 recommendation).

    SHA256 over the canonical ``(repo, item_id, claimant_instance,
    lease_window)`` tuple — a retry of the same claim in the same lease
    window is the SAME claim, not a second one.
    """
    canon = "\n".join((repo, item_id, claimant_instance, lease_window)) + "\n"
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def drift_check(expected: BacklogItem, observed: BacklogItem) -> DriftReport:
    """Compare the re-read forge state against what the claimant expected.

    Pure. Any divergence (status moved, assignees changed) is drift — the
    claim MUST NOT proceed on stale knowledge.
    """
    details: list[str] = []
    if observed.status != expected.status:
        details.append(f"status drifted: expected {expected.status!r}, observed {observed.status!r}")
    if set(observed.assignees) != set(expected.assignees):
        details.append(
            f"assignees drifted: expected {sorted(expected.assignees)!r}, "
            f"observed {sorted(observed.assignees)!r}"
        )
    return DriftReport(drifted=bool(details), details=tuple(details))


def reconcile_competing_claim(
    item: ItemRef, ours: ClaimPlan, observed: BacklogItem
) -> Escalation | None:
    """Earlier-``claimed_at``-wins reconciliation — surfaced, never enforced.

    Returns an :class:`Escalation` when the post-write re-read shows another
    claimant on the item; ``None`` when the item is ours alone. The competing
    claim is NEVER overwritten or removed here.
    """
    others = tuple(a for a in observed.assignees if a != ours.claimant_login)
    if not others:
        return None
    winner: str | None = None
    if observed.claimed_at is not None:
        # ISO-8601 strings order lexicographically; the earlier claim wins.
        winner = others[0] if observed.claimed_at <= ours.claimed_at else ours.claimant_login
    return Escalation(
        item=item,
        reason=(
            f"competing claimant(s) {others!r} observed on item {item.item_id!r} "
            "after write; advisory lock — reconcile by earlier claimed_at "
            "(surfaced for a human, not auto-resolved)"
        ),
        observed=observed,
        winner=winner,
    )


# --- forge I/O (all through the injectable runner) ---------------------------------

_ITEM_QUERY = """
query($id: ID!) {
  node(id: $id) {
    ... on ProjectV2Item {
      id
      status: fieldValueByName(name: "Status") {
        ... on ProjectV2ItemFieldSingleSelectValue { name }
      }
      claimedAt: fieldValueByName(name: "Claimed-at") {
        ... on ProjectV2ItemFieldTextValue { text }
      }
      content {
        ... on Issue { assignees(first: 20) { nodes { login } } }
      }
    }
  }
}
"""

_STATUS_MUTATION = """
mutation($project: ID!, $item: ID!, $field: ID!, $option: String!) {
  updateProjectV2ItemFieldValue(
    input: {projectId: $project, itemId: $item, fieldId: $field,
            value: {singleSelectOptionId: $option}}
  ) { projectV2Item { id } }
}
"""

_CLAIMED_AT_MUTATION = """
mutation($project: ID!, $item: ID!, $field: ID!, $text: String!) {
  updateProjectV2ItemFieldValue(
    input: {projectId: $project, itemId: $item, fieldId: $field,
            value: {text: $text}}
  ) { projectV2Item { id } }
}
"""


def _default_gh_runner(
    argv: Sequence[str], input_text: str | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(argv), check=False, capture_output=True, text=True, input=input_text, timeout=60
    )


def _run_json(runner: GhRunner, argv: list[str], context: str) -> object:
    proc = runner(argv, None)
    if proc.returncode != 0:
        raise ForgeConfigError(
            f"{context} failed: {redact_gh_stderr(proc.stderr or '') or 'unknown error'}"
        )
    out = (proc.stdout or "").strip()
    if not out:
        return None
    try:
        return json.loads(out)
    except (json.JSONDecodeError, ValueError):
        return None


def read_backlog_item(ref: ProjectRef, item: ItemRef, *, gh_runner: GhRunner | None = None) -> BacklogItem:
    """Read the item's forge-projected claim state (Status + assignees + Claimed-at)."""
    runner = gh_runner or _default_gh_runner
    payload = _run_json(
        runner,
        ["gh", "api", "graphql", "-f", f"query={_ITEM_QUERY}", "-f", f"id={item.item_id}"],
        f"read of backlog item {item.item_id!r}",
    )
    node = payload.get("data", {}).get("node") if isinstance(payload, dict) else None
    if not isinstance(node, dict):
        raise ForgeConfigError(f"backlog item {item.item_id!r} not readable as a ProjectV2Item")
    status_obj = node.get("status")
    status = status_obj.get("name") if isinstance(status_obj, dict) else None
    claimed_obj = node.get("claimedAt")
    claimed_at = claimed_obj.get("text") if isinstance(claimed_obj, dict) else None
    content = node.get("content")
    nodes = (
        content.get("assignees", {}).get("nodes")
        if isinstance(content, dict) else None
    )
    assignees = tuple(
        n.get("login") for n in nodes if isinstance(n, dict) and n.get("login")
    ) if isinstance(nodes, list) else ()
    return BacklogItem(item_id=item.item_id, status=status, assignees=assignees, claimed_at=claimed_at)


def project_claim(
    ref: ProjectRef,
    item: ItemRef,
    *,
    claimant_login: str,
    claimant_instance: str,
    lease_window: str,
    claimed_at: str,
    apply: bool = False,
    gh_runner: GhRunner | None = None,
) -> ClaimPlan:
    """Project the claim onto the forge: assignee + ``Status=Running``.

    Plan-by-default: with ``apply=False`` (the default) NOTHING is written —
    the returned plan shows what a live claim would do. With ``apply=True``
    the three write legs run: REST assignee add, GraphQL Status=Running,
    GraphQL Claimed-at (when the field is configured).
    """
    runner = gh_runner or _default_gh_runner
    plan = ClaimPlan(
        item=item,
        claimant_login=claimant_login,
        claimed_at=claimed_at,
        idempotency_key=idempotency_key(ref.repo, item.item_id, claimant_instance, lease_window),
        applied=apply,
    )
    if not apply:
        return plan
    _run_json(
        runner,
        ["gh", "api", "-X", "POST", f"repos/{ref.repo}/issues/{item.issue_number}/assignees",
         "-f", f"assignees[]={claimant_login}"],
        f"assignee projection for item {item.item_id!r}",
    )
    _run_json(
        runner,
        ["gh", "api", "graphql", "-f", f"query={_STATUS_MUTATION}",
         "-f", f"project={ref.project_id}", "-f", f"item={item.item_id}",
         "-f", f"field={ref.status_field_id}", "-f", f"option={ref.running_option_id}"],
        f"Status=Running projection for item {item.item_id!r}",
    )
    if ref.claimed_at_field_id:
        _run_json(
            runner,
            ["gh", "api", "graphql", "-f", f"query={_CLAIMED_AT_MUTATION}",
             "-f", f"project={ref.project_id}", "-f", f"item={item.item_id}",
             "-f", f"field={ref.claimed_at_field_id}", "-f", f"text={claimed_at}"],
            f"Claimed-at projection for item {item.item_id!r}",
        )
    return plan


def claim_item(
    ref: ProjectRef,
    item: ItemRef,
    *,
    claimant_login: str,
    claimant_instance: str,
    lease_window: str,
    claimed_at: str,
    expected: BacklogItem,
    apply: bool = False,
    gh_runner: GhRunner | None = None,
    backoff_seconds: Callable[[], float] | None = None,
    sleeper: Callable[[float], None] | None = None,
) -> ClaimPlan | Escalation:
    """The full advisory-claim protocol (§A.4): drift-check → write → verify.

    1. **Drift-check immediately before the claim:** re-read the item; any
       divergence from ``expected`` (or an existing foreign claimant) is an
       :class:`Escalation` — the claim does not proceed on stale knowledge.
    2. **Write** the projection (only with ``apply=True``; plan-by-default).
    3. **Back-off + re-read after write** (short randomized delay, injectable
       for tests): if a competing claimant now shows on the item, return the
       earlier-``claimed_at``-wins :class:`Escalation` — NEVER overwrite.
    """
    backoff = backoff_seconds or (lambda: random.uniform(0.4, 1.6))
    sleep = sleeper or time.sleep

    observed = read_backlog_item(ref, item, gh_runner=gh_runner)
    report = drift_check(expected, observed)
    if report.drifted:
        return Escalation(
            item=item,
            reason="drift-check before claim failed: " + "; ".join(report.details),
            observed=observed,
        )
    foreign = tuple(a for a in observed.assignees if a != claimant_login)
    if foreign:
        return Escalation(
            item=item,
            reason=f"item already claimed by {foreign!r} (advisory lock held)",
            observed=observed,
            winner=foreign[0],
        )

    plan = project_claim(
        ref, item,
        claimant_login=claimant_login, claimant_instance=claimant_instance,
        lease_window=lease_window, claimed_at=claimed_at,
        apply=apply, gh_runner=gh_runner,
    )
    if not apply:
        return plan

    sleep(backoff())
    after = read_backlog_item(ref, item, gh_runner=gh_runner)
    escalation = reconcile_competing_claim(item, plan, after)
    return escalation if escalation is not None else plan
