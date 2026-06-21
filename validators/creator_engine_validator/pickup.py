"""CE ce-ops#55 — the autonomous forge work-pickup poller (the "conveyor belt").

A per-seat **read-only** poller that lets a dev-seat pick up its OWN GitHub
review-requests / assigned-issues / labeled / @mention work with no human relay.

Adopted design (ce-ops#55, Operator-ratified):

* Poll the GitHub **Notifications API** (``GET /notifications``) with conditional
  ``If-Modified-Since`` / ``Last-Modified`` requests; honor ``X-Poll-Interval``;
  a ``304`` is a free no-op (it does not count against the rate limit).
* Per-identity auth via ``~/.ce-keys/ce-dev-N.pat`` (or ``CE_PICKUP_TOKEN``).
* Resolve each notification thread → a normalized work-item
  ``{repo, kind, number, url, reason, thread_id}``; the actionable reasons are
  ``review_requested`` / ``assign`` / ``manual`` (→ ``assigned``) / labeling
  (→ ``labeled``) / ``mention`` (→ ``mention``). Non-actionable reasons
  (``subscribed`` / ``comment``) are filtered out.

**Hard Ring-0 constraint (verified in code):** CE refuses headless authoring —
``claude_launch_spec.CLAUSE_PRINT`` (``CC-D-2``: ``-p``/``--print``) and
``codex_launch_spec.CLAUSE_HEADLESS`` (``CDX-D-1``: ``exec``/``review``/``apply``).
So this poller is **read-only and NEVER authors**. Actual work runs as a fresh
governed lane via ``ce lane launch`` (S3), fed a seed-file; the poller only
observes (S1), claims via the forge (S2), and triggers the lane (S3, gated OFF
by default).

The lone live network touch lives behind an injectable ``transport`` seam (a
stdlib ``urllib`` HTTPS call by default), mirroring ``forge/app_jwt_runner.py``;
tests inject fakes and perform ZERO live network / subprocess. Importing this
module performs no I/O and registers no validator check.

Defensive only — it picks up the Creator Engine's own work; never offensive.
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import work_claims

#: HTTPS transport: ``(method, url, headers, body) -> (status, headers, body_text)``.
Transport = Callable[[str, str, "dict[str, str]", "str | None"], "tuple[int, dict[str, str], str]"]

_API_ROOT = "https://api.github.com"
_API_VERSION = "2022-11-28"
_ACCEPT = "application/vnd.github+json"

#: The default seat PAT location (per-identity, one file per dev).
DEFAULT_KEYS_DIR = Path.home() / ".ce-keys"
#: The env override for the seat token (takes precedence over the PAT file).
TOKEN_ENV = "CE_PICKUP_TOKEN"

#: GitHub's documented minimum notification poll interval (seconds); honored if
#: the server omits ``X-Poll-Interval`` on a response.
DEFAULT_POLL_INTERVAL = 60

#: Notification ``reason`` → normalized work-item ``kind``. Any reason NOT in this
#: map (e.g. ``subscribed`` / ``comment`` / ``state_change`` / ``ci_activity``) is
#: non-actionable and filtered out — the poller never picks up passive noise.
_REASON_TO_KIND: dict[str, str] = {
    "review_requested": "review_requested",
    "assign": "assigned",
    "manual": "assigned",
    "team_mention": "mention",
    "mention": "mention",
    "labeled": "labeled",
}


class PickupError(Exception):
    """Bad local input / missing credential / unreachable forge (CLI exit 2)."""

    code = "PICKUP-INPUT"


@dataclass(frozen=True)
class PollResult:
    """The outcome of one read-only notifications poll (PURE value).

    ``not_modified`` is ``True`` for a 304 (a free no-op: empty ``items``, the
    prior ``last_modified`` carried forward unchanged so the next poll stays
    conditional). On a 200, ``last_modified`` is the fresh server cursor.
    """

    items: tuple[dict[str, Any], ...] = ()
    last_modified: str | None = None
    poll_interval: int = DEFAULT_POLL_INTERVAL
    not_modified: bool = False


def _default_transport(  # pragma: no cover - the lone live HTTPS shell; tests inject a fake
    method: str, url: str, headers: dict[str, str], body: str | None
) -> tuple[int, dict[str, str], str]:
    data = body.encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            return resp.status, dict(resp.headers), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read().decode("utf-8", "replace")


def resolve_token(
    *, keys_dir: Path | str | None = None, identity: str, environ: Mapping[str, str] | None = None
) -> str:
    """Resolve the per-identity PAT: ``$CE_PICKUP_TOKEN`` else ``<keys_dir>/<identity>.pat``.

    Per-identity auth keeps the pickup loop running as the dev's OWN account (the
    #137 identity model), never a shared/overwatch token. A missing credential
    raises :class:`PickupError` (fail-closed) — a token-less poller would silently
    fall back to ambient auth.
    """
    env = os.environ if environ is None else environ
    env_token = env.get(TOKEN_ENV)
    if env_token and env_token.strip():
        return env_token.strip()
    base = Path(keys_dir) if keys_dir is not None else DEFAULT_KEYS_DIR
    pat = base / f"{identity}.pat"
    if pat.is_file():
        text = pat.read_text(encoding="utf-8").strip()
        if text:
            return text
    raise PickupError(
        f"no pickup token for identity {identity!r}: set ${TOKEN_ENV} or write {pat}"
    )


def _api_to_web_url(api_url: str, subject_type: str) -> str:
    """Map a notification subject API url → the human ``github.com`` url.

    ``…/repos/o/r/pulls/7`` → ``https://github.com/o/r/pull/7`` and
    ``…/repos/o/r/issues/5`` → ``https://github.com/o/r/issues/5``. An
    unrecognized url is returned unchanged (best-effort; never raises).
    """
    marker = "/repos/"
    idx = api_url.find(marker)
    if idx < 0:
        return api_url
    tail = api_url[idx + len(marker):]  # o/r/pulls/7
    parts = tail.split("/")
    if len(parts) >= 4 and parts[2] in ("pulls", "issues"):
        owner, repo, kind, number = parts[0], parts[1], parts[2], parts[3]
        web_kind = "pull" if kind == "pulls" else "issues"
        return f"https://github.com/{owner}/{repo}/{web_kind}/{number}"
    return api_url


def _subject_number(api_url: str) -> int | None:
    """Extract the trailing issue/PR number from a subject API url."""
    tail = api_url.rstrip("/").rsplit("/", 1)[-1]
    return int(tail) if tail.isdigit() else None


def resolve_thread(raw: Mapping[str, Any]) -> dict[str, Any] | None:
    """Normalize one notification thread → a work-item, or ``None`` if non-actionable.

    A work-item is ``{repo, kind, number, url, reason, thread_id, title,
    subject_type}``. A thread whose ``reason`` is not in :data:`_REASON_TO_KIND`
    (``subscribed`` / ``comment`` / …) yields ``None`` (filtered). A thread with no
    resolvable issue/PR number also yields ``None`` (nothing to act on).
    """
    if not isinstance(raw, Mapping):
        return None
    reason = str(raw.get("reason") or "")
    kind = _REASON_TO_KIND.get(reason)
    if kind is None:
        return None
    subject = raw.get("subject") if isinstance(raw.get("subject"), Mapping) else {}
    repo_obj = raw.get("repository") if isinstance(raw.get("repository"), Mapping) else {}
    repo = str(repo_obj.get("full_name") or "")
    api_url = str(subject.get("url") or "")
    number = _subject_number(api_url)
    if not repo or number is None:
        return None
    subject_type = str(subject.get("type") or "")
    return {
        "repo": repo,
        "kind": kind,
        "number": number,
        "url": _api_to_web_url(api_url, subject_type),
        "reason": reason,
        "thread_id": str(raw.get("id") or ""),
        "title": subject.get("title"),
        "subject_type": subject_type,
        "updated_at": raw.get("updated_at"),
    }


def _header(headers: Mapping[str, str], name: str) -> str | None:
    """Case-insensitive header lookup (HTTP header names are case-insensitive)."""
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return None


def poll(
    *,
    token: str,
    transport: Transport | None = None,
    last_modified: str | None = None,
    all_threads: bool = False,
) -> PollResult:
    """One READ-ONLY notifications poll → a :class:`PollResult` (observe-only).

    Issues ``GET /notifications`` with ``Authorization: Bearer <token>`` and, when
    ``last_modified`` is set, a conditional ``If-Modified-Since`` header. A ``304``
    returns an empty-items :class:`PollResult` (``not_modified=True``) carrying the
    prior cursor forward — the free no-op that keeps the loop cheap under the rate
    limit. A ``200`` parses the JSON array, resolves each thread to a work-item
    (filtering non-actionable reasons), and captures the fresh ``Last-Modified`` +
    ``X-Poll-Interval``. This NEVER mutates the forge.
    """
    if not token or not token.strip():
        raise PickupError("poll requires a non-empty token (a token-less poll falls back to ambient auth)")
    _transport = transport or _default_transport
    headers = {
        "Authorization": f"Bearer {token.strip()}",
        "Accept": _ACCEPT,
        "X-GitHub-Api-Version": _API_VERSION,
    }
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    url = f"{_API_ROOT}/notifications"
    if all_threads:
        url += "?all=true"

    status, resp_headers, body = _transport("GET", url, headers, None)

    if status == 304:
        return PollResult(items=(), last_modified=last_modified, not_modified=True,
                          poll_interval=_interval(resp_headers))
    if not (200 <= status < 300):
        raise PickupError(f"notifications poll failed (HTTP {status})")

    try:
        payload = json.loads(body) if body and body.strip() else []
    except (ValueError, TypeError) as exc:
        raise PickupError(f"unparseable notifications payload: {exc}") from exc
    threads = payload if isinstance(payload, list) else []

    items: list[dict[str, Any]] = []
    for raw in threads:
        item = resolve_thread(raw) if isinstance(raw, Mapping) else None
        if item is not None:
            items.append(item)

    new_last_modified = _header(resp_headers, "Last-Modified") or last_modified
    return PollResult(
        items=tuple(items),
        last_modified=new_last_modified,
        poll_interval=_interval(resp_headers),
        not_modified=False,
    )


def _interval(headers: Mapping[str, str]) -> int:
    raw = _header(headers, "X-Poll-Interval")
    if raw is None:
        return DEFAULT_POLL_INTERVAL
    try:
        value = int(str(raw).strip())
    except (ValueError, TypeError):
        return DEFAULT_POLL_INTERVAL
    return value if value > 0 else DEFAULT_POLL_INTERVAL


# ===========================================================================
# S2 — claim + idempotency (forge-arbitrated claim + an append-only dedup ledger).
# ===========================================================================

#: The append-only dedup ledger (NDJSON), mirroring ``runner/notify_feed.py``'s
#: pure-fold pattern: the dedup key is ``(thread_id, item_id, action)`` and carries
#: ONLY GitHub server timestamps — NO wall-clock diffing — so it is idempotent
#: across restarts and re-polls by construction.
DEFAULT_LEDGER_NAME = "ledger.ndjson"

#: The single pickup ``action`` recorded today (one per picked-up thread).
ACTION_CLAIM = "claim"

#: A GhRunner runs a ``gh`` invocation (argv incl. the leading "gh") with an
#: optional stdin body — the same shape as ``work_claims.GhRunner``.
GhRunner = Callable[[Sequence[str], "str | None"], "subprocess.CompletedProcess"]

#: A PR-author lookup: ``(item, gh_runner) -> author_login`` (the independent-
#: reviewer fence input). Injectable so tests perform zero live forge reads.
PrAuthorLookup = Callable[[Mapping[str, Any], GhRunner], "str | None"]


@dataclass(frozen=True)
class ClaimOutcome:
    """The outcome of attempting to claim one work-item (PURE value).

    ``claimed`` is the gate for an S3 launch. ``reason`` is one of: ``claimed`` /
    ``already_seen`` (dedup) / ``own_pr_review_refused`` (independent-reviewer) /
    ``active_foreign_claim`` / ``stale_foreign_claim`` / ``lost_after_reread`` /
    ``no_number``. ``would_launch`` / ``launched`` are set by the S3 caller.
    """

    item: Mapping[str, Any]
    claimed: bool
    reason: str
    claim_id: str | None = None
    posted_url: str | None = None
    would_launch: bool = False
    launched: bool = False
    seed_path: str | None = None
    note: str | None = None


def ledger_key(thread_id: str, item_id: str, action: str) -> tuple[str, str, str]:
    """The dedup identity ``(thread_id, item_id, action)`` — NO clock term."""
    return (str(thread_id), str(item_id), str(action))


def _ledger_path(path: Path | str) -> Path:
    return Path(path)


def load_ledger(path: Path | str) -> list[dict[str, Any]]:
    """Read the dedup ledger (NDJSON, tolerant). Missing file ⇒ ``[]`` (I/O edge).

    A malformed line is skipped (at worst a benign re-claim attempt that the
    forge-arbitrated acquire then fails closed on — never a lost pickup).
    """
    p = _ledger_path(path)
    if not p.is_file():
        return []
    out: list[dict[str, Any]] = []
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(record, dict):
            out.append(record)
    return out


def ledger_keys(records: Iterable[Mapping[str, Any]]) -> set[tuple[str, str, str]]:
    """Fold ledger records → the set of seen dedup keys (PURE)."""
    keys: set[tuple[str, str, str]] = set()
    for r in records:
        if not isinstance(r, Mapping):
            continue
        keys.add(ledger_key(
            str(r.get("thread_id") or ""),
            str(r.get("item_id") or ""),
            str(r.get("action") or ""),
        ))
    return keys


def append_ledger(path: Path | str, record: Mapping[str, Any]) -> None:
    """Append one dedup record to the ledger (I/O edge, the only governance-free write)."""
    p = _ledger_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def _item_id(item: Mapping[str, Any]) -> str:
    """The stable per-item dedup component: ``<repo>:<number>``."""
    return f"{item.get('repo')}:{item.get('number')}"


def default_pr_author_lookup(item: Mapping[str, Any], gh_runner: GhRunner) -> str | None:
    """Resolve a PR's author login via ``GET repos/{repo}/pulls/{n}`` (live read).

    Returns ``None`` when the item is not a PR or the read does not yield an
    author. For ``review_requested`` items, the caller treats ``None`` as
    indeterminate and refuses before claiming; the no-self-review fence must
    prove the author is foreign, not merely fail to prove it is us. Never raises.
    """
    repo = str(item.get("repo") or "")
    number = item.get("number")
    if not repo or number is None or str(item.get("subject_type")) != "PullRequest":
        return None
    try:
        proc = gh_runner(["gh", "api", "--method", "GET", f"repos/{repo}/pulls/{number}"], None)
    except Exception:
        return None
    out = (getattr(proc, "stdout", "") or "").strip()
    if not out:
        return None
    try:
        payload = json.loads(out)
    except (ValueError, TypeError):
        return None
    user = payload.get("user") if isinstance(payload, Mapping) else None
    return user.get("login") if isinstance(user, Mapping) else None


def _self_assign(work_key: work_claims.WorkKey, identity: str, gh_runner: GhRunner) -> bool:
    """Self-assign the issue/PR to ``identity`` (best-effort; never raises).

    Returns ``ok``. The structured claim comment is the AUTHORITATIVE lock (the
    #38 work-claim shape); the assignee is the human-visible forge signal.
    """
    try:
        proc = gh_runner(
            ["gh", "api", "--method", "POST",
             f"repos/{work_key.repo_slug}/issues/{work_key.number}/assignees",
             "--input", "-"],
            json.dumps({"assignees": [identity]}),
        )
    except Exception:
        return False
    return getattr(proc, "returncode", 1) == 0


def claim_item(
    item: Mapping[str, Any],
    *,
    identity: str,
    gh_runner: GhRunner,
    ledger_path: Path | str,
    run_id: str,
    pr_author_lookup: PrAuthorLookup | None = None,
    backoff_seconds: float = 1.0,
) -> ClaimOutcome:
    """Forge-arbitrate a claim on one work-item (fail-closed), with dedup + the
    independent-reviewer fence.

    Order (each gate fails closed before any side effect):

    1. **Independent-reviewer refusal** — for a ``review_requested`` item whose PR
       author IS this identity, refuse (we never review our own PR). NO post.
    2. **Dedup** — if ``(thread_id, <repo>:<number>, claim)`` is already in the
       ledger, short-circuit (``already_seen``); NO post.
    3. **Forge-arbitrated claim** — ``work_claims.acquire`` reads → refuses on a
       foreign active claim → posts the structured ``ce-work-claim`` marker (the
       #38 shape) → re-reads after a bounded backoff → proceeds only if our claim
       wins, else posts a void release and fails closed.
    4. **Self-assign** the issue/PR to ``identity`` (human-visible forge signal).
    5. **Append** the dedup record (server timestamps only; no wall-clock).
    """
    number = item.get("number")
    repo = str(item.get("repo") or "")
    if not repo or number is None:
        return ClaimOutcome(item=item, claimed=False, reason="no_number")

    thread_id = str(item.get("thread_id") or "")
    item_id = _item_id(item)
    key_tuple = ledger_key(thread_id, item_id, ACTION_CLAIM)

    # 1. Independent-reviewer refusal (own-PR review) — before any side effect.
    if item.get("kind") == "review_requested":
        lookup = pr_author_lookup or default_pr_author_lookup
        author = lookup(item, gh_runner)
        if not author:
            return ClaimOutcome(
                item=item,
                claimed=False,
                reason="pr_author_unknown_refused",
                note="PR author lookup was unavailable — refusing review claim fail-closed",
            )
        if author and author == identity:
            return ClaimOutcome(item=item, claimed=False, reason="own_pr_review_refused",
                                note=f"PR author {author!r} is this identity — refusing self-review")

    # 2. Dedup — a server-keyed short-circuit (no wall-clock).
    if key_tuple in ledger_keys(load_ledger(ledger_path)):
        return ClaimOutcome(item=item, claimed=False, reason="already_seen")

    # 3. Forge-arbitrated claim (fail-closed, race-tested in work_claims.acquire).
    work_key = work_claims.WorkKey(*repo.split("/", 1), int(number))
    result = work_claims.acquire(
        work_key, gh_runner,
        holder=identity, host=identity, reason="manual",
        backoff_seconds=backoff_seconds,
    )
    if not result.ok:
        return ClaimOutcome(item=item, claimed=False,
                            reason=result.refusal_reason or "claim_refused",
                            note=result.note)

    # 4. Self-assign (human-visible; the comment marker is the authoritative lock).
    _self_assign(work_key, identity, gh_runner)

    # 5. Append the dedup record (GitHub server-time stamp from the marker).
    append_ledger(ledger_path, {
        "kind": "ce-pickup-dedup",
        "schema_version": 1,
        "thread_id": thread_id,
        "item_id": item_id,
        "action": ACTION_CLAIM,
        "repo": repo,
        "number": int(number),
        "work_kind": item.get("kind"),
        "identity": identity,
        "run_id": run_id,
        "claim_id": result.claim_id,
        "claimed_at": _claim_marker_time(result),
    })
    return ClaimOutcome(item=item, claimed=True, reason="claimed",
                        claim_id=result.claim_id, posted_url=result.posted_url)


def _claim_marker_time(result: work_claims.ClaimResult) -> str | None:
    """The GitHub server-time of the winning claim marker (never the local clock)."""
    active = result.state.active if result.state else None
    return active.claimed_at if active else None


#: Ambient auth env vars dropped from the child ``gh`` env so the per-identity
#: ``GH_TOKEN`` is unambiguous (``GH_TOKEN`` already wins by precedence; dropping
#: these is defense-in-depth — the same hygiene the v3 credential_runner applies).
_AMBIENT_AUTH_ENV = ("GITHUB_TOKEN", "GH_CONFIG_DIR", "GH_HOST")


def make_gh_runner(token: str) -> GhRunner:
    """Return a :data:`GhRunner` that runs ``gh`` AS ``identity`` (token in the child env ONLY).

    The per-identity PAT lands in a per-call child ``GH_TOKEN`` env — never the
    argv, a log, the returned process, or disk — so the pickup loop authenticates
    as the dev's OWN account (the #137 identity model), never ambient/overwatch auth.
    """
    def runner(argv: Sequence[str], input_text: str | None = None) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        for var in _AMBIENT_AUTH_ENV:
            env.pop(var, None)
        env["GH_TOKEN"] = token
        return subprocess.run(
            list(argv), check=False, capture_output=True, text=True,
            input=input_text, env=env, timeout=60,
        )
    return runner


# ===========================================================================
# S3 — `ce lane launch` wiring (canary, gated behind --enable-launch).
# ===========================================================================

import hashlib  # noqa: E402  (kept local to the S3 leg)

#: The spawn seam: ``(argv) -> CompletedProcess``. Defaults to a real subprocess
#: ``ce lane launch`` (the v1→v1 SUBPROCESS + DATA cross to the launcher — keeps
#: ALL tmux coupling behind the lane primitive, the one seam). Tests inject a fake.
Spawn = Callable[[Sequence[str]], "subprocess.CompletedProcess"]

#: Work-item ``kind`` → the governed lane ``--role`` / ``--lane-kind``. A review
#: request drives a reviewer/review lane; everything else an implementer lane.
_KIND_TO_ROLE = {"review_requested": "reviewer"}
_KIND_TO_LANE_KIND = {"review_requested": "review"}
_DEFAULT_ROLE = "implementer"
_DEFAULT_LANE_KIND = "implementation"

#: The lane-launch sentinel that confirms the seat is live (the lane runtime's
#: registered lifecycle state). The notification thread is marked read ONLY after
#: this is observed — never on a mere spawn-exit-0.
LAUNCHED_STATE = "launched"


@dataclass(frozen=True)
class Seed:
    """A written seed file + its byte-level SHA256 (the SHA-binding pointer shape)."""

    path: str
    sha256: str


@dataclass(frozen=True)
class LaunchResult:
    """The outcome of an S3 lane launch (PURE value)."""

    launched: bool
    seed_path: str | None = None
    lane_id: str | None = None
    note: str | None = None


def _default_spawn(argv: Sequence[str]) -> subprocess.CompletedProcess:  # pragma: no cover - live subprocess shell
    return subprocess.run(list(argv), check=False, capture_output=True, text=True, timeout=120)


def _lane_id(item: Mapping[str, Any], run_id: str) -> str:
    repo = str(item.get("repo") or "").replace("/", "-")
    return f"pickup-{repo}-{item.get('number')}-{run_id}"


def build_seed(
    item: Mapping[str, Any], *, identity: str, run_id: str, claim_id: str | None,
    seed_root: Path | str,
) -> Seed:
    """Write a per-item seed file and return its path + byte-level SHA256 (the
    do_not_replan SHA-binding pointer shape; [[ce-seat-dispatch-prompt-pointer-sha]]).

    The seed is a self-contained brief (it must not reference a private ticket a
    contained seat cannot read; [[ce-no-egress-seat-self-contained-briefs]]) — it
    embeds the work-item the lane is to act on.
    """
    root = Path(seed_root)
    root.mkdir(parents=True, exist_ok=True)
    role = _KIND_TO_ROLE.get(str(item.get("kind")), _DEFAULT_ROLE)
    body = (
        f"# CE work-pickup seed — {item.get('repo')}#{item.get('number')}\n\n"
        f"You are picking up auto-detected forge work as **{identity}** ({role} lane).\n\n"
        f"- repo: {item.get('repo')}\n"
        f"- item: #{item.get('number')} ({item.get('subject_type')})\n"
        f"- kind: {item.get('kind')} (notification reason: {item.get('reason')})\n"
        f"- url: {item.get('url')}\n"
        f"- title: {item.get('title')}\n"
        f"- claim_id: {claim_id}\n"
        f"- run_id: {run_id}\n\n"
        f"The work-claim lock is already held by this identity. Do the {role} work "
        f"for the item above; reach green, commit locally, then hand off push/merge "
        f"to the controller (a §7-governed seat cannot push).\n"
    )
    path = root / f"{_lane_id(item, run_id)}.seed.md"
    path.write_text(body, encoding="utf-8")
    return Seed(path=str(path), sha256=hashlib.sha256(body.encode("utf-8")).hexdigest())


def build_lane_argv(
    item: Mapping[str, Any], *, identity: str, run_id: str, harness: str,
    seed: Seed, repo_root: str, ledger_root: str,
) -> list[str]:
    """Build the ``ce lane launch`` argv binding the seed as the prompt pointer + SHA (PURE).

    The seed file IS the ``--prompt`` pointer and its SHA the ``--prompt-sha`` (the
    lane primitive's existing SHA-binding gate). The harness rides ``--command``
    (the lane runtime's harness seam); a review item launches a ``reviewer`` lane.
    """
    role = _KIND_TO_ROLE.get(str(item.get("kind")), _DEFAULT_ROLE)
    lane_kind = _KIND_TO_LANE_KIND.get(str(item.get("kind")), _DEFAULT_LANE_KIND)
    return [
        "ce", "lane", "launch",
        "--controller-id", identity,
        "--lane-id", _lane_id(item, run_id),
        "--role", role,
        "--lane-kind", lane_kind,
        "--prompt", seed.path,
        "--prompt-sha", seed.sha256,
        "--repo-root", repo_root,
        "--ledger-root", ledger_root,
        "--command", harness,
        "--json",
    ]


def launch_lane(
    item: Mapping[str, Any], *, identity: str, run_id: str, claim_id: str | None,
    harness: str, seed_root: Path | str, repo_root: str, ledger_root: str,
    spawn: Spawn | None = None,
) -> LaunchResult:
    """Write a seed and spawn a fresh governed ``ce lane launch`` for a claimed item.

    Returns ``launched=True`` ONLY when the spawn exits 0 AND its JSON reports the
    lane's :data:`LAUNCHED_STATE` sentinel — the caller marks the notification
    thread read only on that confirmation, never on a bare exit-0.
    """
    runner = spawn or _default_spawn
    seed = build_seed(item, identity=identity, run_id=run_id, claim_id=claim_id, seed_root=seed_root)
    argv = build_lane_argv(
        item, identity=identity, run_id=run_id, harness=harness,
        seed=seed, repo_root=repo_root, ledger_root=ledger_root,
    )
    try:
        proc = runner(argv)
    except Exception as exc:
        return LaunchResult(launched=False, seed_path=seed.path, note=f"spawn error: {exc}")
    if getattr(proc, "returncode", 1) != 0:
        return LaunchResult(launched=False, seed_path=seed.path,
                            note=f"lane launch exited {getattr(proc, 'returncode', '?')}")
    state = None
    out = (getattr(proc, "stdout", "") or "").strip()
    if out:
        try:
            state = json.loads(out).get("seat_lifecycle_state")
        except (ValueError, TypeError, AttributeError):
            state = None
    launched = state == LAUNCHED_STATE
    return LaunchResult(
        launched=launched, seed_path=seed.path, lane_id=_lane_id(item, run_id),
        note=None if launched else f"lane did not confirm '{LAUNCHED_STATE}' (state={state!r})",
    )


def mark_thread_read(thread_id: str, *, gh_runner: GhRunner) -> bool:
    """Mark a notification thread read (``PATCH /notifications/threads/{id}``).

    Called ONLY after a launch confirms :data:`LAUNCHED_STATE` — so an item the
    poller could not actually pick up stays unread and is retried next tick.
    Best-effort: a failure leaves the thread unread (a benign re-pickup that the
    dedup ledger + forge-arbitrated acquire then short-circuit). Never raises.
    """
    if not thread_id:
        return False
    try:
        proc = gh_runner(
            ["gh", "api", "--method", "PATCH", f"notifications/threads/{thread_id}"], None
        )
    except Exception:
        return False
    return getattr(proc, "returncode", 1) == 0
