"""CE work-claim locks — the shared, version-neutral claim runtime (ce-ops#38).

The work claim extends CE's claim discipline from *repo lanes* (the
``pco_allocator`` lease/active-work primitive) to *work items* — the compose /
implement / research / review tasks that today have **zero contention control**.
Two controllers on two hosts must never duplicate work on the same ticket; the
near-misses that motivated this gate (#16 spec, #174/#175 site PRs) were caught
only by eyeballs, which do not scale to 6+ concurrent workstreams.

**Authority = a forge-native issue comment.** The authoritative claim is an
append-only, structured GitHub *issue comment* on the target work item (the
fork adjudication chose this over labels and assignees — only a comment carries
holder/host/timestamp/stale-policy/release/takeover/idempotency in one
machine-readable, history-preserving record). The forge is already the
coordination bus, so the claim is cross-host-visible by construction and
survives host loss with zero new infrastructure.

**Honest posture — NOT a hard lock.** GitHub issue comments have no server-side
compare-and-swap and a ~1–3s consistency window, so two hosts can both
post-acquire and both read themselves as winner inside the window. This module
therefore implements the same *advisory* posture as
``forge/backlog.py`` (re-read, drift-check, deterministic earliest-``claimed_at``
tie-break, **no force overwrite**) — eventual correctness, not in-window
exclusion. The residual false-proceed risk is deliberately accepted for the
zero-new-infra trade; Cockpit surfacing, the stale fence, and the standing ops
rule are the mitigations. See ``docs/architecture/work-claim-locks.md``.

Version-boundary discipline (``_versions``): this is a **shared** runtime module
consumed by BOTH ``ce_cli`` (v1) and ``v3_cli`` (v3). It therefore imports NO v1
module, NO v3 module, and NOT ``forge.*`` — it mirrors the ``GhRunner`` / ``gh
api`` seam of ``forge/github_repo_config.py`` with its own private copy so the
HARD v1↔v3 invariant and the shared→version ratchet stay untouched. Every
GitHub call goes through an injectable :data:`GhRunner`; tests inject a fake
runner and perform **zero** live network calls, and importing this module
performs no I/O.

Defensive only — a coordination lock over CE's own governed work items.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import socket
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

# --- marker grammar ----------------------------------------------------------

#: The HTML sentinel that prefixes every structured claim comment. A comment is
#: a CE work-claim marker iff this exact token appears in its body; the JSON
#: record follows it.
SENTINEL = "<!-- ce-work-claim:v1 -->"

#: The legacy interim human lock (the standing ops rule that pre-dates this
#: gate). Detection is EXACT: a comment whose first non-whitespace line begins
#: with U+1F512 followed by `` in-compose`` (``🔒 in-compose``). It is treated as
#: a foreign active claim until an explicit structured release/takeover appears
#: or a recognized deliverable-release comment supersedes it.
_LEGACY_LOCK_PREFIX = "\U0001f512 in-compose"

#: The legacy deliverable-release convention (``📦`` … "BANKED" / "deliverable").
#: A 📦 comment posted AFTER a legacy lock supersedes that legacy lock (the
#: "Release = the 📦 deliverable comment" rule from the issue). It does NOT
#: release a *structured* claim — those require a structured release/takeover.
_DELIVERABLE_MARK = "\U0001f4e6"

KIND = "ce-work-claim"
SCHEMA_VERSION = 1

_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "acquire": (
        "kind", "schema_version", "action", "work_key", "claim_id", "holder",
        "host", "claimed_at", "stale_after_seconds", "idempotency_key",
    ),
    "release": (
        "kind", "schema_version", "action", "work_key", "claim_id", "holder",
        "host", "released_at", "release_reason",
    ),
    "takeover": (
        "kind", "schema_version", "action", "work_key", "claim_id",
        "supersedes_claim_id", "holder", "host", "claimed_at",
        "takeover_reason", "observed_stale_after_seconds",
    ),
}

#: Default staleness fence (4h) — a status + takeover-eligibility threshold, NOT
#: an expiry. A claim older than this stays active until an explicit structured
#: release/takeover is posted.
DEFAULT_STALE_AFTER_SECONDS = 14400

VALID_REASONS = ("compose", "implement", "review", "manual")

#: The view-only Cockpit cache subdir under the v3 local-state ``--root``. The
#: cache is fast/tolerant display data; dispatch enforcement NEVER reads it.
CLAIMS_SUBDIR = "claims"
CLAIMS_CACHE_FILENAME = "claims.json"


# --- errors ------------------------------------------------------------------


class WorkClaimError(Exception):
    """Bad local input / ambiguous ticket / unavailable ``gh`` (CLI exit 2)."""

    code = "WCLAIM-INPUT"


class WorkClaimRefused(Exception):
    """Refused by an active foreign claim / invalid marker / drift (CLI exit 1)."""

    code = "WCLAIM-REFUSED"

    def __init__(
        self,
        message: str,
        *,
        reason: str,
        work_key: "WorkKey | None" = None,
        holder: str | None = None,
        host: str | None = None,
        claim_id: str | None = None,
        claimed_at: str | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.work_key = work_key
        self.holder = holder
        self.host = host
        self.claim_id = claim_id
        self.claimed_at = claimed_at


# --- gh transport (private copy of the forge GhRunner seam) ------------------

#: A GhRunner runs a ``gh`` invocation (argv including the leading "gh") with an
#: optional stdin body and returns the completed process — byte-for-byte the
#: shape of ``forge.github_repo_config.GhRunner``, copied (not imported) to keep
#: this module free of any ``forge.*`` (v3) edge.
GhRunner = Callable[[Sequence[str], "str | None"], "subprocess.CompletedProcess"]


def default_gh_runner(
    argv: Sequence[str], input_text: str | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(argv),
        check=False,
        capture_output=True,
        text=True,
        input=input_text,
        timeout=60,
    )


def _gh_api(
    runner: GhRunner,
    path: str,
    *,
    method: str | None = None,
    fields: Sequence[str] = (),
    body: dict | None = None,
) -> tuple[int, object, str]:
    """Invoke ``gh api [--method M] <path> [-f k=v ...] [--input -]``.

    Returns ``(returncode, parsed_json_or_None, stderr)``. Never raises on a
    non-zero exit (the caller decides) and never raises on unparseable stdout.
    """
    argv: list[str] = ["gh", "api"]
    if method is not None:
        argv += ["--method", method]
    argv.append(path)
    for f in fields:
        argv += ["-f", f]
    input_text: str | None = None
    if body is not None:
        argv += ["--input", "-"]
        input_text = json.dumps(body)
    proc = runner(argv, input_text)
    parsed: object = None
    out = (proc.stdout or "").strip()
    if out:
        try:
            parsed = json.loads(out)
        except (json.JSONDecodeError, ValueError):
            parsed = None
    return proc.returncode, parsed, proc.stderr or ""


# --- work key ----------------------------------------------------------------


@dataclass(frozen=True)
class WorkKey:
    """The canonical work item: ``<owner>/<repo>:issue:<number>``."""

    owner: str
    repo: str
    number: int

    @property
    def work_key(self) -> str:
        return f"{self.owner}/{self.repo}:issue:{self.number}"

    @property
    def repo_slug(self) -> str:
        return f"{self.owner}/{self.repo}"


_REPO_SLUG_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_URL_RE = re.compile(
    r"^https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/issues/(\d+)/?",
)
_OWNER_REPO_NUM_RE = re.compile(
    r"^([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?:#|:issue:|/issues/)(\d+)$",
)


def parse_ticket(raw: str, repo: str | None = None) -> WorkKey:
    """Parse a ticket reference into a :class:`WorkKey`.

    Accepts ``owner/name#N``, ``owner/name:issue:N``, the full
    ``https://github.com/owner/name/issues/N`` URL, and a bare ``N`` when
    ``repo`` (``owner/name``) is supplied. A bare issue number WITHOUT a repo
    context is rejected (ambiguous) — exit 2 at the CLI.
    """
    if raw is None:
        raise WorkClaimError("missing ticket")
    text = raw.strip()
    if not text:
        raise WorkClaimError("empty ticket")

    m = _URL_RE.match(text)
    if m:
        return WorkKey(m.group(1), m.group(2), int(m.group(3)))

    m = _OWNER_REPO_NUM_RE.match(text)
    if m:
        return WorkKey(m.group(1), m.group(2), int(m.group(3)))

    if text.isdigit():
        if not repo:
            raise WorkClaimError(
                f"ambiguous bare issue number {text!r}: supply --repo owner/name "
                "(or a fully-qualified ticket like owner/name#N)"
            )
        if not _REPO_SLUG_RE.match(repo):
            raise WorkClaimError(f"--repo must be owner/name, got {repo!r}")
        owner, name = repo.split("/", 1)
        return WorkKey(owner, name, int(text))

    raise WorkClaimError(
        f"unrecognized ticket {raw!r}: use owner/name#N, a GitHub issue URL, "
        "or N with --repo owner/name"
    )


# --- timestamps --------------------------------------------------------------


def _parse_ts(value: Any) -> datetime | None:
    """Parse an ISO-8601 UTC timestamp (tolerant of a trailing ``Z``)."""
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def utc_now_iso() -> str:
    """Current UTC time as an ISO-8601 ``…Z`` string (the I/O-edge clock)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- comment normalization + marker parsing ----------------------------------


@dataclass(frozen=True)
class Comment:
    """A normalized GitHub issue comment (the L1 input to the state machine)."""

    id: int
    body: str
    created_at: str = ""
    author: str | None = None


def _normalize_comment(raw: Any) -> Comment | None:
    if not isinstance(raw, dict):
        return None
    cid = raw.get("id")
    body = raw.get("body")
    if cid is None or not isinstance(body, str):
        return None
    try:
        cid_int = int(cid)
    except (TypeError, ValueError):
        # GraphQL node ids are non-numeric; fall back to a stable hash so the
        # deterministic tie-breaker still has a total order.
        cid_int = int(hashlib.sha256(str(cid).encode()).hexdigest()[:12], 16)
    created = raw.get("created_at") or raw.get("createdAt") or ""
    user = raw.get("user") if isinstance(raw.get("user"), dict) else {}
    author = (user or {}).get("login") if isinstance(user, dict) else None
    if author is None and isinstance(raw.get("author"), dict):
        author = raw["author"].get("login")
    return Comment(id=cid_int, body=body, created_at=str(created), author=author)


@dataclass(frozen=True)
class Marker:
    """One parsed claim signal extracted from a comment body."""

    status: str  # acquire | release | takeover | legacy | deliverable | invalid
    comment_id: int
    created_at: str
    work_key: str | None = None
    claim_id: str | None = None
    fields: dict[str, Any] = field(default_factory=dict)


def _first_nonblank_line(body: str) -> str:
    for line in body.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _extract_json_after_sentinel(body: str) -> dict[str, Any] | None:
    idx = body.find(SENTINEL)
    rest = body[idx + len(SENTINEL):]
    brace = rest.find("{")
    if brace < 0:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(rest[brace:])
    except (json.JSONDecodeError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def parse_comment(comment: Comment) -> Marker | None:
    """Parse one comment into a :class:`Marker`, or ``None`` if it carries none.

    A body bearing :data:`SENTINEL` but no valid structured record yields an
    ``invalid`` marker (so ``status`` reports ``invalid_marker`` and ``acquire``
    fails closed). The legacy 🔒 lock and the 📦 deliverable-release are matched
    by their exact line prefixes / marks.
    """
    body = comment.body
    if SENTINEL in body:
        record = _extract_json_after_sentinel(body)
        if record is None:
            return Marker("invalid", comment.id, comment.created_at)
        action = record.get("action")
        if action not in _REQUIRED_FIELDS:
            return Marker("invalid", comment.id, comment.created_at,
                          work_key=record.get("work_key"))
        missing = [f for f in _REQUIRED_FIELDS[action] if record.get(f) in (None, "")]
        if record.get("kind") != KIND or missing:
            return Marker("invalid", comment.id, comment.created_at,
                          work_key=record.get("work_key"))
        return Marker(
            action, comment.id, comment.created_at,
            work_key=str(record.get("work_key")),
            claim_id=str(record.get("claim_id")),
            fields=dict(record),
        )

    first = _first_nonblank_line(body)
    if first.startswith(_LEGACY_LOCK_PREFIX):
        return Marker(
            "legacy", comment.id, comment.created_at,
            claim_id=f"legacy-{comment.id}",
            fields={"holder": _legacy_holder(first), "line": first},
        )
    if _DELIVERABLE_MARK in body:
        return Marker("deliverable", comment.id, comment.created_at)
    return None


def _legacy_holder(line: str) -> str | None:
    # ``🔒 in-compose ce-dev-2 (…)`` → ``ce-dev-2``
    rest = line[len(_LEGACY_LOCK_PREFIX):].strip()
    return rest.split()[0] if rest else None


# --- the deterministic state machine (PURE) ----------------------------------


@dataclass(frozen=True)
class ClaimView:
    """One marker's resolved standing in the computed state (JSON-serializable)."""

    claim_id: str
    holder: str | None
    host: str | None
    status: str  # active | conflict | superseded | released | invalid
    claimed_at: str | None
    stale: bool
    comment_id: int
    kind: str  # structured | legacy

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "holder": self.holder,
            "host": self.host,
            "status": self.status,
            "claimed_at": self.claimed_at,
            "stale": self.stale,
            "comment_id": self.comment_id,
            "kind": self.kind,
        }


@dataclass(frozen=True)
class ClaimState:
    """The folded view of all markers for one work key (PURE)."""

    work_key: str
    active: ClaimView | None
    entries: list[ClaimView]
    invalid_count: int
    comment_ids: list[int]

    @property
    def active_count(self) -> int:
        return 1 if self.active is not None else 0

    @property
    def stale_count(self) -> int:
        return len([e for e in self.entries if e.status == "active" and e.stale])


def compute_state(
    comments: Sequence[Comment],
    work_key: str,
    now: datetime,
    *,
    stale_default: int = DEFAULT_STALE_AFTER_SECONDS,
) -> ClaimState:
    """Fold all comments for ``work_key`` into the active-holder view (PURE).

    The algorithm (spec §State Machine): parse markers, ignore other work keys,
    apply releases to matching ``claim_id``, apply takeovers/deliverables to the
    claims they supersede, then pick the active holder by earliest live
    ``claimed_at`` (tie-break: comment id, then ``claim_id``). Staleness is a
    flag on the active claim, never an auto-release.
    """
    markers = [m for c in comments for m in (parse_comment(c),) if m is not None]
    # Markers are processed in forge order (comment id ascending) so "earlier"
    # is well-defined for legacy supersession.
    markers.sort(key=lambda m: m.comment_id)

    claims: dict[str, Marker] = {}
    released: set[str] = set()
    superseded: set[str] = set()
    invalid_count = 0

    deliverable_after: list[int] = [
        m.comment_id for m in markers if m.status == "deliverable"
    ]
    structured_release_takeover_after: list[int] = [
        m.comment_id for m in markers if m.status in ("release", "takeover")
    ]

    for m in markers:
        if m.status == "invalid":
            # An invalid marker only counts against THIS work key (or when it
            # carries no parseable work key at all — it still pollutes the issue).
            if m.work_key in (None, work_key):
                invalid_count += 1
            continue
        if m.status == "deliverable":
            continue
        if m.status in ("acquire", "takeover", "release") and m.work_key != work_key:
            continue  # a marker for a different work item — ignore
        if m.status == "release":
            if m.claim_id:
                released.add(m.claim_id)
            continue
        if m.status == "takeover":
            sup = m.fields.get("supersedes_claim_id")
            if sup:
                superseded.add(str(sup))
            if m.claim_id:
                claims[m.claim_id] = m
            continue
        if m.status == "acquire":
            if m.claim_id:
                claims[m.claim_id] = m
            continue
        if m.status == "legacy":
            # A legacy lock is active until a later structured release/takeover
            # OR a later 📦 deliverable-release supersedes it.
            later = any(cid > m.comment_id for cid in deliverable_after) or any(
                cid > m.comment_id for cid in structured_release_takeover_after
            )
            if later:
                released.add(m.claim_id)  # type: ignore[arg-type]
            if m.claim_id:
                claims[m.claim_id] = m

    views: list[ClaimView] = []
    live: list[ClaimView] = []
    for claim_id, m in claims.items():
        is_legacy = m.status == "legacy"
        claimed_at = m.created_at if is_legacy else m.fields.get("claimed_at")
        holder = m.fields.get("holder")
        host = m.fields.get("host")
        stale = False
        if not is_legacy:
            stale_after = m.fields.get("stale_after_seconds") or stale_default
            ts = _parse_ts(claimed_at)
            if ts is not None and isinstance(stale_after, (int, float)):
                stale = (now - ts).total_seconds() > float(stale_after)
        if claim_id in released:
            status = "released"
        elif claim_id in superseded:
            status = "superseded"
        else:
            status = "active"  # provisional; the loser(s) become conflict below
        view = ClaimView(
            claim_id=claim_id,
            holder=holder,
            host=host,
            status=status,
            claimed_at=claimed_at,
            stale=stale,
            comment_id=m.comment_id,
            kind="legacy" if is_legacy else "structured",
        )
        if status == "active":
            live.append(view)
        else:
            views.append(view)

    active: ClaimView | None = None
    if live:
        live.sort(
            key=lambda v: (
                _parse_ts(v.claimed_at) or datetime.max.replace(tzinfo=timezone.utc),
                v.comment_id,
                v.claim_id,
            )
        )
        winner = live[0]
        active = winner
        views.append(winner)
        for loser in live[1:]:
            views.append(
                ClaimView(
                    claim_id=loser.claim_id,
                    holder=loser.holder,
                    host=loser.host,
                    status="conflict",
                    claimed_at=loser.claimed_at,
                    stale=loser.stale,
                    comment_id=loser.comment_id,
                    kind=loser.kind,
                )
            )

    views.sort(key=lambda v: v.comment_id)
    return ClaimState(
        work_key=work_key,
        active=active,
        entries=views,
        invalid_count=invalid_count,
        comment_ids=[c.id for c in comments],
    )


# --- identity helpers --------------------------------------------------------


def resolve_holder(holder: str | None = None, environ: dict[str, str] | None = None) -> str:
    env = environ if environ is not None else os.environ
    return (
        holder
        or env.get("CE_CLAIM_HOLDER")
        or env.get("CE_CONTROLLER_ID")
        or socket.gethostname()
        or "ce-unknown"
    )


def resolve_host(host: str | None = None) -> str:
    return host or socket.gethostname() or "unknown-host"


def make_idempotency_key(holder: str, host: str, work_key: str, nonce: str) -> str:
    return f"{holder}-{host}-{work_key}-{nonce}"


def make_claim_id(idempotency_key: str) -> str:
    digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:16]
    return f"wclaim-{digest}"


# --- marker rendering --------------------------------------------------------


def render_marker(record: dict[str, Any]) -> str:
    """Render a structured claim record as a sentinel-prefixed comment body."""
    payload = json.dumps(record, indent=2, sort_keys=True)
    action = record.get("action", "?")
    return f"{SENTINEL}\n\n```json\n{payload}\n```\n\n_CE work-claim · action={action}_\n"


# --- the forge I/O edge ------------------------------------------------------


def fetch_comments(
    key: WorkKey, runner: GhRunner
) -> list[Comment]:
    """Read all issue comments for ``key`` (the only live forge READ).

    Raises :class:`WorkClaimError` when ``gh`` is unavailable / errors (exit 2).
    """
    rc, parsed, stderr = _gh_api(
        runner,
        f"repos/{key.repo_slug}/issues/{key.number}/comments?per_page=100",
        method="GET",
    )
    if rc != 0:
        raise WorkClaimError(
            f"gh api failed reading comments for {key.work_key} (rc={rc}): "
            f"{_redact(stderr)}"
        )
    if not isinstance(parsed, list):
        # A reachable-but-empty issue returns ``[]``; anything else is a fault.
        if parsed is None:
            return []
        raise WorkClaimError(f"unexpected gh api comments payload for {key.work_key}")
    out: list[Comment] = []
    for raw in parsed:
        c = _normalize_comment(raw)
        if c is not None:
            out.append(c)
    return out


def _post_comment(key: WorkKey, runner: GhRunner, body: str) -> tuple[bool, str | None, str]:
    """Post one issue comment. Returns ``(ok, comment_url, stderr)``."""
    rc, parsed, stderr = _gh_api(
        runner,
        f"repos/{key.repo_slug}/issues/{key.number}/comments",
        method="POST",
        body={"body": body},
    )
    url = parsed.get("html_url") if isinstance(parsed, dict) else None
    return rc == 0, url, stderr


def _redact(stderr: str) -> str:
    """Coarse stderr redaction (token-shaped substrings → ``***``)."""
    return re.sub(r"gh[ps]_[A-Za-z0-9]{20,}", "***", stderr or "").strip()


# --- public results ----------------------------------------------------------


@dataclass
class ClaimResult:
    """The outcome of an acquire / release / status operation."""

    ok: bool
    action: str
    work_key: str
    state: ClaimState
    refusal_reason: str | None = None
    claim_id: str | None = None
    posted_url: str | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "action": self.action,
            "work_key": self.work_key,
            "active_claim": self.state.active.to_dict() if self.state.active else None,
            "refusal_reason": self.refusal_reason,
            "comments_seen": len(self.state.comment_ids),
            "claim_id": self.claim_id,
            "entries": [e.to_dict() for e in self.state.entries],
            "invalid_count": self.state.invalid_count,
            "stale_count": self.state.stale_count,
            "posted_url": self.posted_url,
            "note": self.note,
        }


def status(
    key: WorkKey,
    runner: GhRunner,
    *,
    now: datetime | None = None,
) -> ClaimResult:
    """Read the live claim state for ``key`` (no mutation)."""
    now = now or datetime.now(timezone.utc)
    comments = fetch_comments(key, runner)
    state = compute_state(comments, key.work_key, now)
    note = None
    if state.invalid_count:
        note = "invalid_marker"
    return ClaimResult(
        ok=True, action="status", work_key=key.work_key, state=state,
        claim_id=state.active.claim_id if state.active else None, note=note,
    )


def _is_self(view: ClaimView | None, holder: str, host: str) -> bool:
    return bool(view and view.holder == holder and view.host == host)


def _active_foreign_claim_refusal(key: WorkKey, active: ClaimView) -> WorkClaimRefused:
    """Build the structured refusal used by the read-only and acquire gates."""
    return WorkClaimRefused(
        "double-assignment blocked: "
        f"{key.work_key} held by {active.holder}@{active.host} "
        f"since {active.claimed_at} (claim {active.claim_id})",
        reason="active_foreign_claim",
        work_key=key,
        holder=active.holder,
        host=active.host,
        claim_id=active.claim_id,
        claimed_at=active.claimed_at,
    )


def block_if_active_foreign_claim(
    key: WorkKey,
    runner: GhRunner,
    *,
    holder: str | None = None,
    host: str | None = None,
    now: datetime | None = None,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
) -> None:
    """Read live claims and raise for a fresh foreign holder without writing.

    A stale foreign claim is only warned about because it remains seizable, while
    a matching holder and host is an idempotent self-claim and returns normally.
    """
    now = now or datetime.now(timezone.utc)
    holder = resolve_holder(holder)
    host = resolve_host(host)
    comments = fetch_comments(key, runner)
    state = compute_state(
        comments, key.work_key, now, stale_default=stale_after_seconds,
    )
    active = state.active
    if active is None or _is_self(active, holder, host):
        return
    if active.stale:
        logger.warning(
            "stale foreign work claim remains seizable: %s held by %s@%s "
            "since %s (claim %s)",
            key.work_key,
            active.holder,
            active.host,
            active.claimed_at,
            active.claim_id,
        )
        return
    raise _active_foreign_claim_refusal(key, active)


def acquire(
    key: WorkKey,
    runner: GhRunner,
    *,
    holder: str | None = None,
    host: str | None = None,
    reason: str = "manual",
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
    takeover: bool = False,
    takeover_reason: str | None = None,
    now: datetime | None = None,
    nonce: str | None = None,
    claim_id: str | None = None,
    idempotency_key: str | None = None,
    backoff_seconds: float = 1.0,
    sleep: Callable[[float], None] | None = None,
    hard_block: bool = True,
) -> ClaimResult:
    """Acquire the work claim with the atomic-dispatch posture (spec §Atomic).

    Reads → blocks on a foreign active claim by default → posts a structured acquire (or
    takeover) → re-reads after a bounded backoff → recomputes the deterministic
    winner → proceeds only if the just-posted claim wins, else posts a void
    release and fails closed.
    """
    now = now or datetime.now(timezone.utc)
    holder = resolve_holder(holder)
    host = resolve_host(host)
    nonce = nonce or hashlib.sha256(f"{now.isoformat()}-{os.getpid()}".encode()).hexdigest()[:10]
    idempotency_key = idempotency_key or make_idempotency_key(holder, host, key.work_key, nonce)
    claim_id = claim_id or make_claim_id(idempotency_key)

    # 1. Read all comments + compute the active holder.
    comments = fetch_comments(key, runner)
    state = compute_state(comments, key.work_key, now)
    active = state.active

    # 2/3. A foreign active claim refuses before we post anything.
    if active is not None and not _is_self(active, holder, host):
        if not takeover:
            reason_code = "stale_foreign_claim" if active.stale else "active_foreign_claim"
            if hard_block and not active.stale:
                raise _active_foreign_claim_refusal(key, active)
            return ClaimResult(
                ok=False, action="acquire", work_key=key.work_key, state=state,
                refusal_reason=reason_code, claim_id=None,
                note=(
                    f"held by {active.holder}@{active.host} (claim {active.claim_id}); "
                    + ("stale — pass --takeover to seize" if active.stale
                       else "active — refusing to duplicate work")
                ),
            )
        # --takeover present: a stale claim is seizable; a fresh one is not.
        if not active.stale and active.kind != "legacy":
            return ClaimResult(
                ok=False, action="acquire", work_key=key.work_key, state=state,
                refusal_reason="takeover_not_stale", claim_id=None,
                note=f"claim {active.claim_id} is not stale; takeover refused",
            )

    # 4. Post the structured acquire/takeover comment.
    if takeover and active is not None and not _is_self(active, holder, host):
        record = {
            "kind": KIND, "schema_version": SCHEMA_VERSION, "action": "takeover",
            "work_key": key.work_key, "claim_id": claim_id,
            "supersedes_claim_id": active.claim_id,
            "holder": holder, "host": host, "claimed_at": _iso(now),
            "takeover_reason": takeover_reason or "stale-and-operator-approved",
            "observed_stale_after_seconds": stale_after_seconds,
        }
    else:
        record = {
            "kind": KIND, "schema_version": SCHEMA_VERSION, "action": "acquire",
            "work_key": key.work_key, "claim_id": claim_id, "holder": holder,
            "host": host, "pid": os.getpid(), "reason": reason,
            "claimed_at": _iso(now), "stale_after_seconds": stale_after_seconds,
            "idempotency_key": idempotency_key,
        }
    ok, url, stderr = _post_comment(key, runner, render_marker(record))
    if not ok:
        raise WorkClaimError(f"gh api failed posting claim for {key.work_key}: {_redact(stderr)}")

    # 5/6. Bounded backoff, then re-read + recompute the deterministic winner.
    if backoff_seconds > 0:
        (sleep or time.sleep)(backoff_seconds)
    comments = fetch_comments(key, runner)
    state = compute_state(comments, key.work_key, now)
    winner = state.active

    # 7. Proceed only if the just-posted claim is the active holder.
    if winner is not None and winner.claim_id == claim_id:
        return ClaimResult(
            ok=True, action="acquire", work_key=key.work_key, state=state,
            claim_id=claim_id, posted_url=url,
            note="takeover" if record["action"] == "takeover" else "acquired",
        )

    # 8. Our claim lost the re-read — post a best-effort void release, fail closed.
    void = _release_record(key, claim_id, holder, host, now, "lost-acquire-race")
    _post_comment(key, runner, render_marker(void))
    state = compute_state(fetch_comments(key, runner), key.work_key, now)
    return ClaimResult(
        ok=False, action="acquire", work_key=key.work_key, state=state,
        refusal_reason="lost_after_reread", claim_id=claim_id, posted_url=url,
        note=(
            f"another claim won the re-read ({winner.claim_id if winner else 'none'}); "
            "released our marker and refusing"
        ),
    )


def release(
    key: WorkKey,
    runner: GhRunner,
    *,
    holder: str | None = None,
    host: str | None = None,
    claim_id: str | None = None,
    reason: str = "deliverable-posted",
    deliverable_url: str | None = None,
    now: datetime | None = None,
) -> ClaimResult:
    """Release a held claim by posting a structured release comment.

    When ``claim_id`` is omitted, releases the active claim if it is held by this
    ``(holder, host)``; otherwise refuses (we never release someone else's claim).
    """
    now = now or datetime.now(timezone.utc)
    holder = resolve_holder(holder)
    host = resolve_host(host)
    comments = fetch_comments(key, runner)
    state = compute_state(comments, key.work_key, now)

    target = claim_id
    if target is None:
        if state.active is None:
            return ClaimResult(
                ok=False, action="release", work_key=key.work_key, state=state,
                refusal_reason="no_active_claim", note="nothing to release",
            )
        if not _is_self(state.active, holder, host):
            return ClaimResult(
                ok=False, action="release", work_key=key.work_key, state=state,
                refusal_reason="foreign_claim",
                note=f"active claim {state.active.claim_id} is not yours; pass --claim-id to override",
            )
        target = state.active.claim_id

    record = _release_record(key, target, holder, host, now, reason, deliverable_url)
    ok, url, stderr = _post_comment(key, runner, render_marker(record))
    if not ok:
        raise WorkClaimError(f"gh api failed posting release for {key.work_key}: {_redact(stderr)}")
    state = compute_state(fetch_comments(key, runner), key.work_key, now)
    return ClaimResult(
        ok=True, action="release", work_key=key.work_key, state=state,
        claim_id=target, posted_url=url, note="released",
    )


def best_effort_release(
    key: WorkKey,
    runner: GhRunner,
    claim_id: str,
    *,
    holder: str,
    host: str,
    reason: str,
    now: datetime | None = None,
) -> bool:
    """Post a structured release without raising (dispatch refusal cleanup)."""
    now = now or datetime.now(timezone.utc)
    try:
        record = _release_record(key, claim_id, holder, host, now, reason)
        ok, _url, _stderr = _post_comment(key, runner, render_marker(record))
        return ok
    except Exception:  # never let cleanup mask the original refusal
        return False


def _release_record(
    key: WorkKey, claim_id: str, holder: str, host: str, now: datetime,
    reason: str, deliverable_url: str | None = None,
) -> dict[str, Any]:
    record = {
        "kind": KIND, "schema_version": SCHEMA_VERSION, "action": "release",
        "work_key": key.work_key, "claim_id": claim_id, "holder": holder,
        "host": host, "released_at": _iso(now), "release_reason": reason,
    }
    if deliverable_url:
        record["deliverable_url"] = deliverable_url
    return record


def _iso(now: datetime) -> str:
    return now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- the view-only Cockpit cache (L1-shaped; NEVER read by enforcement) -------


def build_cache(result: ClaimResult, repo_slug: str, fetched_at: str) -> dict[str, Any]:
    """Shape the view-only claim cache (the L1 input the Cockpit fold consumes)."""
    entries = [e.to_dict() for e in result.state.entries]
    return {
        "kind": "ce-work-claim-cache",
        "schema_version": SCHEMA_VERSION,
        "fetched_at": fetched_at,
        "repo": repo_slug,
        "work_key": result.work_key,
        "active": result.state.active.to_dict() if result.state.active else None,
        "entries": entries,
        "active_count": result.state.active_count,
        "stale_count": result.state.stale_count,
        "invalid_count": result.state.invalid_count,
        "comment_ids": list(result.state.comment_ids),
    }


def write_cache(state_root: Path | str, cache: dict[str, Any]) -> Path:
    """Atomically write the view-only cache under ``<state_root>/claims/claims.json``.

    The write is atomic (temp + ``os.replace``) so a concurrent Cockpit read
    never sees a torn file. This cache is display data ONLY — dispatch
    enforcement always reads the live forge comments, never this file.
    """
    claims_dir = Path(state_root) / CLAIMS_SUBDIR
    claims_dir.mkdir(parents=True, exist_ok=True)
    target = claims_dir / CLAIMS_CACHE_FILENAME
    tmp = claims_dir / f".{CLAIMS_CACHE_FILENAME}.tmp"
    tmp.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, target)
    return target
