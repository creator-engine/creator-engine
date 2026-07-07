"""Shared terminal guidance for the CE journey surface.

This module is intentionally pure and shared by the public ``ce`` kernel, the
journey verb surface, scaffolded project docs, and tests so command hints do not
drift from the actual user-facing CLI.
"""

from __future__ import annotations

from typing import Final

STAGE_SEQUENCE: Final[tuple[str, ...]] = ("Frame", "Shape", "Build", "Review", "Ship")
STAGE_SEQUENCE_TEXT: Final[str] = " -> ".join(STAGE_SEQUENCE)
STAGE_SEQUENCE_DISPLAY: Final[str] = " \u2192 ".join(STAGE_SEQUENCE)

SCOPE_ID_PLACEHOLDER: Final[str] = "<id>"
GOAL_PLACEHOLDER: Final[str] = "..."
DONE_WHEN_PLACEHOLDER: Final[str] = "..."
CHANGE_TYPE_PLACEHOLDER: Final[str] = "<type>"


def shape_next(scope_id: str = SCOPE_ID_PLACEHOLDER) -> str:
    return (
        f'Next: ce scope {scope_id} --goal "{GOAL_PLACEHOLDER}" '
        f'--done-when "{DONE_WHEN_PLACEHOLDER}" --change-type {CHANGE_TYPE_PLACEHOLDER}'
    )


def scope_next(scope_id: str = SCOPE_ID_PLACEHOLDER) -> str:
    return f"Next: ce ratify {scope_id}"


def ratify_next(scope_id: str = SCOPE_ID_PLACEHOLDER) -> str:
    return f"Next: ce drive {scope_id} --spawn"


def drive_spawn_next(scope_id: str = SCOPE_ID_PLACEHOLDER) -> str:
    return f"Next: ce report {scope_id}  (when work completes)"


def report_next(next_scope_id: str | None = None) -> str:
    if next_scope_id:
        return f"Next: ce ratify {next_scope_id}  (if follow-on Scopes exist)"
    return "Journey complete."


STAGE_MAP_LINES: Final[tuple[str, str, str]] = (
    f"CE stages: {STAGE_SEQUENCE_DISPLAY}",
    "Start:     ce session | ce shape <id> | ce scope <id> --goal \"...\" --done-when \"...\" --change-type <type>",
    "Then:      ce ratify <id> | ce drive <id> --spawn | ce report <id>",
)


def stage_map_text(*, indent: str = "") -> str:
    return "\n".join(f"{indent}{line}" for line in STAGE_MAP_LINES)


JOURNEY_QUICKSTART_LINES: Final[tuple[str, ...]] = (
    shape_next(SCOPE_ID_PLACEHOLDER),
    scope_next(SCOPE_ID_PLACEHOLDER),
    ratify_next(SCOPE_ID_PLACEHOLDER),
    drive_spawn_next(SCOPE_ID_PLACEHOLDER),
    report_next(),
)


__all__ = [
    "CHANGE_TYPE_PLACEHOLDER",
    "DONE_WHEN_PLACEHOLDER",
    "GOAL_PLACEHOLDER",
    "JOURNEY_QUICKSTART_LINES",
    "SCOPE_ID_PLACEHOLDER",
    "STAGE_MAP_LINES",
    "STAGE_SEQUENCE",
    "STAGE_SEQUENCE_DISPLAY",
    "STAGE_SEQUENCE_TEXT",
    "drive_spawn_next",
    "ratify_next",
    "report_next",
    "scope_next",
    "shape_next",
    "stage_map_text",
]
