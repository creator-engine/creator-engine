"""Seat-side, authority-free handoff from one intake claim to a governed launcher.

This module intentionally owns no process, pane, credential, or work-claim
authority. The controller supplies normal territory/work-claim preflight and
the governed lane launcher as injected boundaries. The adapter verifies a brief
pin before calling either boundary and releases failed claims.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from creator_engine_validator.conveyor_intake_queue import IntakeQueue, IntakeUnit


_CANARY_SHA256 = re.compile(r"^[0-9a-f]{64}$")
PullState = Literal["empty", "claimed", "launched", "blocked_released"]
ClaimState = Literal["empty", "claimed"]


@dataclass(frozen=True)
class VerifiedLaneLaunch:
    """Value-free handoff supplied to the existing governed lane-launch seam."""

    unit_id: str
    brief_path: Path
    brief_sha256: str
    branch: str
    worktree: str
    work_class: str
    territory_paths: tuple[str, ...]


@dataclass(frozen=True)
class SeatPullOutcome:
    """Controller-safe evidence for exactly one seat pull attempt."""

    state: PullState
    claim_state: ClaimState
    seat_id: str
    unit_id: str | None = None
    brief_sha256: str | None = None
    detail: str | None = None


TerritoryClaimPreflight = Callable[[IntakeUnit, VerifiedLaneLaunch], bool]
GovernedLaneLauncher = Callable[[VerifiedLaneLaunch], bool]


class SeatPullAdapter:
    """Claim, verify, preflight, and hand a single unit to a governed launcher."""

    def __init__(
        self,
        queue: IntakeQueue,
        *,
        trusted_brief_root: Path,
        territory_claim_preflight: TerritoryClaimPreflight,
        governed_lane_launcher: GovernedLaneLauncher,
    ) -> None:
        self.queue = queue
        self.trusted_brief_root = Path(trusted_brief_root)
        self.territory_claim_preflight = territory_claim_preflight
        self.governed_lane_launcher = governed_lane_launcher

    def pull_one(self, seat_id: str, *, ttl_seconds: float | int | None = None) -> SeatPullOutcome:
        """Pull one unit, releasing it unless a governed launcher accepts it."""
        unit = self.queue.claim_entry(seat_id, ttl_seconds=ttl_seconds)
        if unit is None:
            return SeatPullOutcome(state="empty", claim_state="empty", seat_id=seat_id)

        brief_sha = unit.brief_sha
        try:
            launch = self._verified_launch(unit)
            if not self.territory_claim_preflight(unit, launch):
                return self._release_blocked(unit, seat_id, "territory_claim_refused")
            if not self.governed_lane_launcher(launch):
                return self._release_blocked(unit, seat_id, "launcher_refused")
        except (OSError, ValueError) as exc:
            return self._release_blocked(unit, seat_id, f"verification_refused:{exc}")
        except Exception as exc:
            return self._release_blocked(unit, seat_id, f"governed_seam_refused:{type(exc).__name__}")
        return SeatPullOutcome(
            state="launched",
            claim_state="claimed",
            seat_id=seat_id,
            unit_id=unit.unit_id,
            brief_sha256=brief_sha,
        )

    def _verified_launch(self, unit: IntakeUnit) -> VerifiedLaneLaunch:
        if not _CANARY_SHA256.fullmatch(unit.brief_sha):
            raise ValueError("brief_sha must be a lowercase 64-hex SHA-256 for seat pull")
        brief_path = _resolve_trusted_brief(self.trusted_brief_root, unit.brief_ref)
        actual_sha = hashlib.sha256(brief_path.read_bytes()).hexdigest()
        if actual_sha != unit.brief_sha:
            raise ValueError("brief_sha does not match trusted brief content")
        return VerifiedLaneLaunch(
            unit_id=unit.unit_id,
            brief_path=brief_path,
            brief_sha256=actual_sha,
            branch=unit.branch,
            worktree=unit.worktree,
            work_class=unit.work_class,
            territory_paths=unit.territory_paths,
        )

    def _release_blocked(self, unit: IntakeUnit, seat_id: str, detail: str) -> SeatPullOutcome:
        self.queue.release_entry(unit.unit_id, seat_id)
        return SeatPullOutcome(
            state="blocked_released",
            claim_state="claimed",
            seat_id=seat_id,
            unit_id=unit.unit_id,
            brief_sha256=unit.brief_sha,
            detail=detail,
        )


def _resolve_trusted_brief(trusted_root: Path, brief_ref: str) -> Path:
    """Resolve a relative brief reference without accepting escape or symlinks."""
    root = trusted_root.resolve(strict=True)
    reference = Path(brief_ref)
    if reference.is_absolute() or ".." in reference.parts:
        raise ValueError("brief_ref escapes trusted brief root")
    candidate = root / reference
    try:
        candidate.relative_to(root)
    except ValueError as exc:  # defensive on unusual platform path semantics
        raise ValueError("brief_ref escapes trusted brief root") from exc
    current = root
    for component in reference.parts:
        current = current / component
        if current.is_symlink():
            raise ValueError("brief_ref contains a symlink")
    if not candidate.is_file():
        raise ValueError("brief_ref is not a regular file")
    return candidate
