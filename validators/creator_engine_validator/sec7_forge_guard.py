"""Shared §7 governed-seat guard for high-risk forge operations.

This module is deliberately shared-version-line code: stdlib only, no v1 hook
imports, and no v3 forge imports. v1 hook code and v3 forge/CLI code can both
reuse the same action vocabulary without crossing the v1/v3 boundary.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

FORGE_ACTIONS: dict[str, str] = {
    "configure-repo": "forge_configure_repo",
    "ruleset": "forge_ruleset",
    "review-submit": "forge_review_submit",
    "auto-merge": "forge_auto_merge",
}

_ACTION_ALIASES: dict[str, str] = {
    "configure_repo": "configure-repo",
    "configure-repo": "configure-repo",
    "allow_auto_merge": "configure-repo",
    "configure_squash_only": "configure-repo",
    "ruleset": "ruleset",
    "upsert_ruleset": "ruleset",
    "delete_ruleset": "ruleset",
    "review_submit": "review-submit",
    "review-submit": "review-submit",
    "submit_review": "review-submit",
    "auto_merge": "auto-merge",
    "auto-merge": "auto-merge",
    "enable_auto_merge": "auto-merge",
}

POSTURE_ENV_VARS: tuple[str, ...] = (
    "CE_SEC7_POSTURE",
    "CE_RING1_POSTURE",
    "CE_POSTURE",
)


class Sec7ForgeRefused(RuntimeError):
    """A §7-governed context attempted a controller/forge operation."""


def normalize_forge_action(action: str) -> str | None:
    """Return the canonical dashed forge action, or ``None`` when unrelated."""

    raw = str(action or "").strip()
    if not raw:
        return None
    return _ACTION_ALIASES.get(raw, _ACTION_ALIASES.get(raw.replace("-", "_")))


def forge_mechanic_label(action: str) -> str | None:
    canonical = normalize_forge_action(action)
    return FORGE_ACTIONS.get(canonical or "")


def _posture_from_context(context: Any) -> str | None:
    if context is None:
        for name in POSTURE_ENV_VARS:
            value = os.environ.get(name)
            if value:
                return value.strip().lower()
        return None
    if isinstance(context, str):
        return context.strip().lower()
    if isinstance(context, Mapping):
        posture = context.get("posture")
        if not posture and isinstance(context.get("ce"), Mapping):
            posture = context["ce"].get("posture")
        return str(posture).strip().lower() if posture else None
    posture = getattr(context, "posture", None)
    return str(posture).strip().lower() if posture else None


def sec7_forge_refusal(action: str, context: Any = None) -> str | None:
    """Return a refusal reason when a §7-governed context invokes a forge op."""

    canonical = normalize_forge_action(action)
    if canonical is None:
        return None
    if _posture_from_context(context) != "governed":
        return None
    return (
        f"§7 governed-seat context is denied from invoking forge op {canonical!r}; "
        "this operation is reserved for controller/forge authority"
    )


def require_forge_allowed(action: str, context: Any = None) -> None:
    reason = sec7_forge_refusal(action, context)
    if reason is not None:
        raise Sec7ForgeRefused(reason)


__all__ = [
    "FORGE_ACTIONS",
    "POSTURE_ENV_VARS",
    "Sec7ForgeRefused",
    "forge_mechanic_label",
    "normalize_forge_action",
    "require_forge_allowed",
    "sec7_forge_refusal",
]
