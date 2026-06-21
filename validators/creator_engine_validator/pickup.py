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
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
