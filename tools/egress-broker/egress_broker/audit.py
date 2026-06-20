"""The egress-broker append-only audit — the signed-authorship / transport anchor.

ADR-0007 makes the gateway a high-assurance component that "demands … strong audit". Every
broker decision — allow OR deny — appends ONE immutable JSONL record capturing: the seat, the
commit sha + author, what was verified (the policy checks + failing reasons), which
App/installation couriered it, the push/PR result, and a timestamp. The same log feeds the
basic rate guard (:func:`count_recent_pushes`).

This is the broker's HOST-SIDE operational audit (not the governance evidence spine), so it
deliberately records the non-secret identifiers ADR-0007 asks for — the ``app_owner`` and the
numeric ``installation_id`` (an identifier, not a credential). It is fail-closed SECRET-FREE:
:func:`append_audit` refuses any record carrying a token/secret/PEM key or token-shaped value,
so a future caller can never leak a credential into the durable log.

Pure stdlib; the only I/O is the append + the rate read, and the clock is injectable (``now``)
so tests are deterministic.
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path

#: Record keys that must never appear (a credential by name). Substring-matched, case-insensitive.
_FORBIDDEN_KEY_SUBSTRINGS = ("token", "secret", "pem", "private_key", "app_key", "password", "value")
#: Token-shaped values (the ``_redact`` shapes): a gh*_ / github_pat_ token or a 3-part JWT.
_TOKEN_SHAPE = re.compile(r"(?:gh[opusr]_|github_pat_)[A-Za-z0-9_.\-]{8,}|eyJ[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+){2}")


class AuditSecretLeak(Exception):
    """A record carried credential-shaped material — refused (the audit stays secret-free)."""


def _now_iso(now: Callable[[], datetime] | None) -> str:
    dt = (now or (lambda: datetime.now(timezone.utc)))()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _assert_secret_free(obj: object, *, _path: str = "") -> None:
    """Recursively refuse a credential-by-name key or a token-shaped value (fail-closed)."""
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            key = str(k).lower()
            if any(sub in key for sub in _FORBIDDEN_KEY_SUBSTRINGS):
                raise AuditSecretLeak(
                    f"audit record key {k!r} looks like a credential; refusing to persist it"
                )
            _assert_secret_free(v, _path=f"{_path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _assert_secret_free(v, _path=f"{_path}[{i}]")
    elif isinstance(obj, str):
        if _TOKEN_SHAPE.search(obj):
            raise AuditSecretLeak(
                f"audit record value at {_path or '<root>'} is token-shaped; refusing to persist it"
            )


def append_audit(
    path: str | Path, record: Mapping, *, now: Callable[[], datetime] | None = None
) -> dict:
    """Append one ``record`` (stamped with ``recorded_at``) as a JSON line; return the stamped dict.

    Refuses (``AuditSecretLeak``, BEFORE any write) a record carrying a credential-by-name key or
    a token-shaped value, so the durable log stays secret-free. Creates the parent directory and
    the file if needed; never truncates (append-only).
    """
    _assert_secret_free(record)
    stamped = {**dict(record), "recorded_at": _now_iso(now)}
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(stamped, sort_keys=True, separators=(",", ":"))
    with p.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return stamped


def _parse_recorded_at(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def count_recent_pushes(
    path: str | Path,
    seat_id: str,
    *,
    window_seconds: int,
    now: Callable[[], datetime] | None = None,
) -> int:
    """Count this seat's ALLOWED + PUSHED audit records within the last ``window_seconds``.

    The rate-guard input for the policy core. A missing log is ``0``; garbled lines are skipped
    (never fatal). Only records with ``decision == "allow"`` and ``pushed`` true inside the
    window count — denials and out-of-window history do not.
    """
    p = Path(path).expanduser()
    if not p.is_file():
        return 0
    cutoff_now = (now or (lambda: datetime.now(timezone.utc)))()
    if cutoff_now.tzinfo is None:
        cutoff_now = cutoff_now.replace(tzinfo=timezone.utc)
    count = 0
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(rec, dict):
            continue
        if rec.get("seat_id") != seat_id or rec.get("decision") != "allow" or not rec.get("pushed"):
            continue
        when = _parse_recorded_at(rec.get("recorded_at"))
        if when is None:
            continue
        if (cutoff_now - when).total_seconds() <= window_seconds:
            count += 1
    return count
