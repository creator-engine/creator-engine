"""Shared diagnostics for GitHub protection-floor capability failures."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

PROTECTION_FLOOR_UNENFORCEABLE_CODE = "protection_floor_unenforceable"
PROTECTION_FLOOR_REMEDIATION = (
    "upgrade to GitHub Team/Pro or make the repository public, then rerun onboard so GitHub "
    "can enforce the CE branch-protection/rulesets floor"
)


def api_error_text(parsed: object, stderr: str) -> str:
    parts: list[str] = []
    if isinstance(parsed, Mapping):
        message = parsed.get("message")
        if message:
            parts.append(str(message))
        errors = parsed.get("errors")
        if isinstance(errors, list):
            for item in errors:
                if isinstance(item, Mapping):
                    item_message = item.get("message") or item.get("code")
                    if item_message:
                        parts.append(str(item_message))
                elif item:
                    parts.append(str(item))
    if stderr:
        parts.append(stderr)
    return " ".join(parts)


def _has_forbidden_status_signal(parsed: object, stderr: str) -> bool:
    if "http 403" in (stderr or "").lower():
        return True
    if not isinstance(parsed, Mapping):
        return False
    for key in ("status", "status_code", "http_status"):
        value = parsed.get(key)
        if value == 403:
            return True
        if isinstance(value, str) and value.strip().lower() in {"403", "http 403"}:
            return True
    return False


def protection_floor_unenforceable(parsed: object, stderr: str) -> bool:
    """Detect GitHub plan/capability 403s for branch protection/rulesets.

    The wording differs between classic protection and rulesets, so this matches
    capability/remediation markers rather than one exact message. It intentionally
    does not match generic auth failures such as "Resource not accessible by
    integration".
    """
    text = api_error_text(parsed, stderr).lower()
    if not text:
        return False
    if not _has_forbidden_status_signal(parsed, stderr):
        return False
    unsupported_markers = (
        "protected branches are not available",
        "branch protection rules are not available",
        "branch protection is not available",
        "repository rulesets are not available",
        "rulesets are not available",
        "not available for private repositories",
        "make this repository public",
        "upgrade to github pro",
        "upgrade to github team",
    )
    capability_markers = (
        "private repositories",
        "this plan",
        "make this repository public",
        "upgrade",
    )
    return any(marker in text for marker in unsupported_markers) and any(
        marker in text for marker in capability_markers
    )


def protection_floor_unenforceable_diagnostic(
    *, surface: str, parsed: object, stderr: str
) -> dict[str, Any]:
    return {
        "ok": False,
        "code": PROTECTION_FLOOR_UNENFORCEABLE_CODE,
        "reason": PROTECTION_FLOOR_UNENFORCEABLE_CODE,
        "surface": surface,
        "message": api_error_text(parsed, stderr).strip(),
        "remediation": PROTECTION_FLOOR_REMEDIATION,
    }
