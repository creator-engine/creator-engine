"""Named ``ce check`` profiles.

Profiles are deliberately narrow allowlists. They are not a generic
check-skipping mechanism; each profile owns an explicit set of omissions and a
human-readable reason.
"""

from __future__ import annotations

import sys
from typing import TextIO

CLIENT_REPO_PROFILE = "client-repo"
CHECK_PROFILES = (CLIENT_REPO_PROFILE,)

CLIENT_REPO_OMITTED_CHECK_REASONS: dict[str, str] = {
    "mutation_class": "it requires the CE-resident docs/contracts/mutation-class-taxonomy.yml taxonomy file",
    "surfaces_manifest_complete": "it requires the CE-resident surfaces/manifest.yaml rented-surface inventory",
    "surfaces_manifest_consistent": "it requires the CE-resident surfaces/manifest.yaml rented-surface inventory",
    "v3_naming_hygiene": "it requires the CE-resident schemas/*.yaml v3 schema surface",
}


def omitted_checks_for_profile(profile: str | None) -> dict[str, str]:
    """Return omitted check reasons for a known profile, refusing unknown names."""

    if profile is None:
        return {}
    if profile == CLIENT_REPO_PROFILE:
        return dict(CLIENT_REPO_OMITTED_CHECK_REASONS)
    raise ValueError(f"unknown ce check profile {profile!r}; expected one of: {', '.join(CHECK_PROFILES)}")


def emit_profile_notices(profile: str, omissions: dict[str, str], stream: TextIO | None = None) -> None:
    """Print one pinned notice per omitted check."""

    out = stream if stream is not None else sys.stderr
    for check_name in sorted(omissions):
        print(f"NOTICE: omitted check {check_name} for profile {profile} because {omissions[check_name]}.", file=out)


__all__ = [
    "CHECK_PROFILES",
    "CLIENT_REPO_OMITTED_CHECK_REASONS",
    "CLIENT_REPO_PROFILE",
    "emit_profile_notices",
    "omitted_checks_for_profile",
]
