"""Pure policy for the GitHub environment supplied to CE child processes."""
from __future__ import annotations

from collections.abc import Iterable, Mapping


_CHILD_ENV_EXCLUSIONS = frozenset(
    {
        "gh_token",
        "github_token",
        "ce_ops_read_token",
        "ce_pr_read_token",
        "gh_enterprise_token",
        "github_enterprise_token",
        "gh_debug",
        "gh_host",
        "gh_config_dir",
        "github_api_url",
    }
)


def _is_app_key_name(name: str) -> bool:
    upper = name.upper()
    return upper.endswith("_PEM") or "PRIVATE_KEY" in upper or "APP_KEY" in upper


def scoped_github_child_env(
    env: Mapping[str, str],
    active_token: str,
    *,
    token_source_names: Iterable[str | None] = (),
) -> dict[str, str]:
    """Return a new GitHub child environment carrying only ``active_token``.

    This mapping performs no I/O and does not mutate ``env``. Control and
    credential names are compared case-insensitively so inherited spelling
    cannot change the child credential boundary.
    """
    excluded = set(_CHILD_ENV_EXCLUSIONS)
    excluded.update(name.casefold() for name in token_source_names if name is not None)
    child = {
        name: value
        for name, value in env.items()
        if name.casefold() not in excluded and not _is_app_key_name(name)
    }
    child["GH_TOKEN"] = active_token
    return child
