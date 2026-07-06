"""Claim lifecycle frontmatter runtime for ``.ce/claims/<slug>.md`` files."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

import yaml


ORDERED_STATES = ("claimed", "in-build", "ready", "harvested", "landed", "released")
TERMINAL_STATES = ("landed", "released", "abandoned")
STATES = (*ORDERED_STATES, "abandoned")

_STATE_RANK = {state: index for index, state in enumerate(ORDERED_STATES)}
_SLUG_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_ISSUE_RE = re.compile(r"(?:^|-)ce-(\d+)(?:-|$)")
_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.DOTALL)


class ClaimLifecycleError(ValueError):
    """Raised when a claim file is missing, malformed, or cannot transition."""


@dataclass(frozen=True)
class TransitionResult:
    slug: str
    path: Path
    old_state: str
    new_state: str
    transitioned_at: str
    pr: str | None
    merge_sha: str | None
    seat: str
    controller: str

    def log_payload(self) -> dict[str, Any]:
        return {
            "event": "ce_claim_transition",
            "slug": self.slug,
            "old_state": self.old_state,
            "new_state": self.new_state,
            "transitioned_at": self.transitioned_at,
            "pr": self.pr,
            "merge_sha": self.merge_sha,
            "seat": self.seat,
            "controller": self.controller,
            "path": self.path.as_posix(),
        }


def utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def claims_dir(repo_root: str | Path) -> Path:
    return Path(repo_root) / ".ce" / "claims"


def claim_path(repo_root: str | Path, slug: str) -> Path:
    _validate_slug(slug)
    return claims_dir(repo_root) / f"{slug}.md"


def transition_claim(
    repo_root: str | Path,
    slug: str,
    new_state: str,
    *,
    pr: str | None = None,
    sha: str | None = None,
    force: bool = False,
    now: str | None = None,
) -> TransitionResult:
    """Transition one claim file and return the structured log payload data."""

    _validate_slug(slug)
    _validate_state(new_state)
    path = claim_path(repo_root, slug)
    if not path.is_file():
        raise ClaimLifecycleError(f"claim file not found: {path}")

    text = path.read_text(encoding="utf-8")
    data, body = parse_claim_text(text, slug=slug, now=now)
    old_state = str(data["state"])
    _assert_transition_allowed(old_state, new_state, force=force)

    transitioned_at = now or utc_now_iso()
    data["state"] = new_state
    data["transitioned_at"] = transitioned_at
    if pr is not None:
        data["pr"] = pr
    if sha is not None:
        data["merge_sha"] = sha
    _validate_claim_data(data, slug=slug)

    path.write_text(render_claim_text(data, body), encoding="utf-8")
    return TransitionResult(
        slug=slug,
        path=path,
        old_state=old_state,
        new_state=new_state,
        transitioned_at=transitioned_at,
        pr=_nullable_str(data.get("pr")),
        merge_sha=_nullable_str(data.get("merge_sha")),
        seat=str(data["seat"]),
        controller=str(data["controller"]),
    )


def list_claims(
    repo_root: str | Path,
    *,
    state: str | None = None,
    seat: str | None = None,
) -> list[dict[str, Any]]:
    if state is not None:
        _validate_state(state)

    root = claims_dir(repo_root)
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.md")):
        slug = path.stem
        try:
            data, _body = parse_claim_text(path.read_text(encoding="utf-8"), slug=slug)
            _validate_claim_data(data, slug=slug)
        except (OSError, ClaimLifecycleError):
            continue
        if state is not None and data.get("state") != state:
            continue
        if seat is not None and data.get("seat") != seat:
            continue
        rows.append(
            {
                "slug": data["slug"],
                "state": data["state"],
                "seat": data["seat"],
                "controller": data["controller"],
                "pr": data.get("pr"),
                "merge_sha": data.get("merge_sha"),
                "transitioned_at": data["transitioned_at"],
                "path": path.as_posix(),
            }
        )
    return rows


def parse_claim_text(text: str, *, slug: str, now: str | None = None) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter, upgrading legacy prose to a claimed skeleton."""

    _validate_slug(slug)
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return _legacy_claim_data(slug, now=now), text

    raw_data = yaml.safe_load(match.group(1)) or {}
    if not isinstance(raw_data, dict):
        raise ClaimLifecycleError("claim frontmatter must be a YAML mapping")
    data = dict(raw_data)
    _normalize_timestamp_fields(data)
    _fill_missing_defaults(data, slug, now=now)
    _validate_claim_data(data, slug=slug)
    return data, match.group(2)


def render_claim_text(data: dict[str, Any], body: str) -> str:
    frontmatter = yaml.safe_dump(data, sort_keys=False, allow_unicode=False).strip()
    frontmatter = _render_plain_timestamp_fields(frontmatter)
    return f"---\n{frontmatter}\n---\n{body.lstrip()}"


def format_table(rows: Iterable[dict[str, Any]]) -> str:
    rows = list(rows)
    headers = ("slug", "state", "seat", "pr", "transitioned_at")
    if not rows:
        return "SLUG STATE SEAT PR TRANSITIONED_AT\n"
    widths = {
        key: max(len(key.upper()), *(len(_cell(row.get(key))) for row in rows))
        for key in headers
    }
    lines = [" ".join(key.upper().ljust(widths[key]) for key in headers)]
    for row in rows:
        lines.append(" ".join(_cell(row.get(key)).ljust(widths[key]) for key in headers))
    return "\n".join(lines) + "\n"


def structured_log_line(result: TransitionResult) -> str:
    return json.dumps(result.log_payload(), sort_keys=True, separators=(",", ":"))


def _validate_slug(slug: str) -> None:
    if not _SLUG_RE.fullmatch(slug):
        raise ClaimLifecycleError(f"invalid claim slug: {slug!r}")


def _validate_state(state: str) -> None:
    if state not in STATES:
        raise ClaimLifecycleError(f"invalid claim state: {state!r}")


def _assert_transition_allowed(old_state: str, new_state: str, *, force: bool) -> None:
    _validate_state(old_state)
    _validate_state(new_state)
    if force or old_state == new_state:
        return
    if old_state in {"released", "abandoned"}:
        raise ClaimLifecycleError(f"cannot transition from terminal state {old_state!r} without --force")
    if new_state == "abandoned":
        return
    if old_state == "abandoned":
        raise ClaimLifecycleError("cannot transition from abandoned without --force")
    if _STATE_RANK[new_state] < _STATE_RANK[old_state]:
        raise ClaimLifecycleError(
            f"refusing backward claim transition {old_state!r} -> {new_state!r} without --force"
        )


def _legacy_claim_data(slug: str, *, now: str | None) -> dict[str, Any]:
    issue = _issue_from_slug(slug)
    if issue is None:
        raise ClaimLifecycleError("legacy claim without frontmatter must use a slug containing ce-<issue>")
    ts = now or utc_now_iso()
    return {
        "slug": slug,
        "issue": issue,
        "repo": _env_first("GITHUB_REPOSITORY", default="creator-engine/creator-engine"),
        "state": "claimed",
        "seat": resolve_seat(),
        "controller": resolve_controller(),
        "claimed_at": ts,
        "transitioned_at": ts,
        "pr": None,
        "merge_sha": None,
        "refs": [f"ce-ops#{issue}"],
    }


def _fill_missing_defaults(data: dict[str, Any], slug: str, *, now: str | None) -> None:
    issue = _issue_from_slug(slug)
    ts = now or utc_now_iso()
    data.setdefault("slug", slug)
    if issue is not None:
        data.setdefault("issue", issue)
    data.setdefault("repo", _env_first("GITHUB_REPOSITORY", default="creator-engine/creator-engine"))
    data.setdefault("state", "claimed")
    data.setdefault("seat", resolve_seat())
    data.setdefault("controller", resolve_controller())
    data.setdefault("claimed_at", ts)
    data.setdefault("transitioned_at", data.get("claimed_at") or ts)
    data.setdefault("pr", None)
    data.setdefault("merge_sha", None)
    if issue is not None:
        data.setdefault("refs", [f"ce-ops#{issue}"])


def _validate_claim_data(data: dict[str, Any], *, slug: str) -> None:
    required = (
        "slug",
        "issue",
        "repo",
        "state",
        "seat",
        "controller",
        "claimed_at",
        "transitioned_at",
        "pr",
        "merge_sha",
        "refs",
    )
    missing = [key for key in required if key not in data]
    if missing:
        raise ClaimLifecycleError(f"claim frontmatter missing required field(s): {', '.join(missing)}")
    if data["slug"] != slug:
        raise ClaimLifecycleError(f"claim slug {data['slug']!r} does not match file slug {slug!r}")
    _validate_state(str(data["state"]))
    if not isinstance(data["refs"], list) or not all(isinstance(item, str) for item in data["refs"]):
        raise ClaimLifecycleError("claim refs must be a list of strings")
    for key in ("repo", "seat", "controller", "claimed_at", "transitioned_at"):
        if not isinstance(data[key], str) or not data[key]:
            raise ClaimLifecycleError(f"claim field {key} must be a non-empty string")
    if not isinstance(data["issue"], int):
        raise ClaimLifecycleError("claim issue must be an integer")
    for key in ("pr", "merge_sha"):
        value = data[key]
        if value is not None and not isinstance(value, str):
            raise ClaimLifecycleError(f"claim field {key} must be null or a string")


def _normalize_timestamp_fields(data: dict[str, Any]) -> None:
    for key in ("claimed_at", "transitioned_at"):
        value = data.get(key)
        if isinstance(value, datetime):
            if value.tzinfo is not None:
                value = value.astimezone(timezone.utc)
            rendered = value.replace(microsecond=0).isoformat()
            data[key] = rendered.replace("+00:00", "Z")
        elif isinstance(value, date):
            data[key] = value.isoformat()


def _render_plain_timestamp_fields(frontmatter: str) -> str:
    return re.sub(
        r"^(claimed_at|transitioned_at): '([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]+Z)'$",
        r"\1: \2",
        frontmatter,
        flags=re.MULTILINE,
    )


def resolve_seat() -> str:
    return _env_first("CE_SEAT", "CE_CLAIM_SEAT", "CE_WORKER_ID", "USER", default="unknown-seat")


def resolve_controller() -> str:
    return _env_first("CE_CONTROLLER", "CE_CONTROLLER_ID", "CONTROLLER_ID", default="unknown-controller")


def _env_first(*names: str, default: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


def _issue_from_slug(slug: str) -> int | None:
    match = _ISSUE_RE.search(slug)
    if match is None:
        return None
    return int(match.group(1))


def _nullable_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _cell(value: Any) -> str:
    return "-" if value in (None, "") else str(value)
