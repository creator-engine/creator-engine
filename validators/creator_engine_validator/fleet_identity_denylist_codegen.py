"""Generate the fleet manifest CE-internal identity denylist snapshot.

The private identity registry stays in ``creator-engine/ce-ops``. This helper
extracts only concrete identifier strings needed by the public fleet manifest
guard, then compares or prints a public snapshot module.
"""

from __future__ import annotations

import argparse
import base64
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import yaml

SOURCE_REPO = "creator-engine/ce-ops"
SOURCE_PATH = "infra/identity-registry.yaml"

_IGNORED_VALUES = frozenset(
    {
        "",
        "*",
        "App",
        "PAT",
        "TODO_VERIFY",
        "ce",
        "correct",
        "integrator",
        "nefarious",
        "nvis",
        "openbao",
    }
)


def _iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for child in value.values():
            yield from _iter_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_strings(child)
    elif isinstance(value, str):
        yield value.strip()


def _selected_values(registry: Mapping[str, Any]) -> Iterable[str]:
    """Yield concrete identity values while avoiding broad prose fields."""

    for account in registry.get("accounts", []):
        if not isinstance(account, Mapping):
            continue
        yield from _iter_strings(
            {
                "login": account.get("login"),
                "owning_seat": account.get("owning_seat"),
                "host": account.get("host"),
                "noreply_commit_email": account.get("noreply_commit_email"),
            }
        )

    for app in registry.get("apps", []):
        if not isinstance(app, Mapping):
            continue
        yield from _iter_strings(
            {
                "repo_scope": app.get("repo_scope"),
                "pem_custody": app.get("pem_custody"),
            }
        )

    for token in registry.get("tokens", []):
        if not isinstance(token, Mapping):
            continue
        yield from _iter_strings(
            {
                "host_binding": token.get("host_binding"),
                "storage_pointer": token.get("storage_pointer"),
                "rotation_owner": token.get("rotation_owner"),
                "resource_owner": token.get("resource_owner"),
            }
        )

    for key in registry.get("signing_keys", []):
        if not isinstance(key, Mapping):
            continue
        yield from _iter_strings(key)

    for entry in registry.get("host_topology", []):
        if not isinstance(entry, Mapping):
            continue
        yield from _iter_strings(
            {
                "name": entry.get("name"),
                "host": entry.get("host"),
                "tailnet_ip": entry.get("tailnet_ip"),
                "users": entry.get("users"),
                "credential_pointers": entry.get("credential_pointers"),
            }
        )

    for entry in registry.get("authoring_review_matrix", []):
        if not isinstance(entry, Mapping):
            continue
        yield from _iter_strings(
            {
                "seat": entry.get("seat"),
                "authors_as": entry.get("authors_as"),
                "may_review": entry.get("may_review"),
            }
        )


def _token_variants(value: str) -> Iterable[str]:
    if value in _IGNORED_VALUES or value.startswith("TODO_"):
        return
    if len(value) < 4:
        return

    yield value

    if value.startswith("openbao-ref:"):
        pointer = value.removeprefix("openbao-ref:")
        if "#" in pointer:
            yield pointer.split("#", 1)[0]
        yield pointer

    if "ce-kv/" in value:
        yield "ce-kv/"
    if "ce-kv/forge/" in value:
        yield "ce-kv/forge/"

    seat_match = value.removeprefix("ce-")
    if seat_match in {"dev-1", "dev-2", "dev-3", "dev-4"}:
        yield f"ce{seat_match.replace('-', '')}"


def derive_identity_registry_denylist(registry: Mapping[str, Any]) -> tuple[str, ...]:
    """Derive public denylist tokens from the private identity registry data."""

    tokens = {"creator-engine/ce-ops"}
    for value in _selected_values(registry):
        tokens.update(_token_variants(value))
    return tuple(sorted(tokens, key=str.casefold))


def load_registry_text(text: str) -> dict[str, Any]:
    loaded = yaml.safe_load(text) or {}
    if not isinstance(loaded, dict):
        raise ValueError("identity registry must be a mapping")
    return loaded


def _gh_api_json(path: str) -> dict[str, Any]:
    result = subprocess.run(
        ["gh", "api", path],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown gh api failure"
        raise RuntimeError(detail)
    return yaml.safe_load(result.stdout)


def fetch_registry() -> tuple[str, str]:
    data = _gh_api_json(f"repos/{SOURCE_REPO}/contents/{SOURCE_PATH}")
    content = str(data["content"])
    blob_sha = str(data["sha"])
    return blob_sha, base64.b64decode(content).decode("utf-8")


def render_snapshot(*, source_blob_sha: str, tokens: Iterable[str]) -> str:
    lines = [
        '"""Vendored CE identity denylist snapshot for fleet manifest validation.',
        "",
        "Generated from the private identity registry. Do not vendor the source",
        "registry body into this public repository.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        f"SOURCE_REPO = {SOURCE_REPO!r}",
        f"SOURCE_PATH = {SOURCE_PATH!r}",
        f"SOURCE_BLOB_SHA = {source_blob_sha!r}",
        "",
        "IDENTITY_REGISTRY_DENYLIST_TOKENS = (",
    ]
    for token in tokens:
        lines.append(f"    {token!r},")
    lines.extend([")", ""])
    return "\n".join(lines)


def _snapshot_path(repo_root: Path) -> Path:
    return (
        repo_root
        / "validators"
        / "creator_engine_validator"
        / "fleet_identity_denylist_snapshot.py"
    )


def _cmd_print(_: argparse.Namespace) -> int:
    blob_sha, text = fetch_registry()
    tokens = derive_identity_registry_denylist(load_registry_text(text))
    print(render_snapshot(source_blob_sha=blob_sha, tokens=tokens), end="")
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    blob_sha, text = fetch_registry()
    tokens = derive_identity_registry_denylist(load_registry_text(text))
    expected = render_snapshot(source_blob_sha=blob_sha, tokens=tokens)
    actual = _snapshot_path(Path(args.repo_root)).read_text(encoding="utf-8")
    if actual != expected:
        raise SystemExit(
            "vendored fleet identity denylist snapshot is stale; "
            "regenerate with the print command"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(required=True)

    print_parser = subparsers.add_parser(
        "print", help="print the current snapshot module"
    )
    print_parser.set_defaults(func=_cmd_print)

    check_parser = subparsers.add_parser("check", help="check the vendored snapshot against ce-ops")
    check_parser.add_argument("--repo-root", default=".")
    check_parser.set_defaults(func=_cmd_check)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
