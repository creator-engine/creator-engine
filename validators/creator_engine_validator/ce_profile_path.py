"""CE-marked shell-profile PATH block writer."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

__ce_version_line__ = "v1"

BEGIN_MARKER = "# >>> creator-engine PATH >>>"
END_MARKER = "# <<< creator-engine PATH <<<"


@dataclass(frozen=True)
class ProfilePathResult:
    profile_path: Path
    changed: bool

    def notice(self) -> str:
        state = "updated" if self.changed else "shell profile PATH block already current"
        if self.changed:
            return f"{state} shell profile PATH block: {self.profile_path}"
        return f"{state}: {self.profile_path}"

    def to_dict(self) -> dict[str, object]:
        return {"profile_path": str(self.profile_path), "changed": self.changed}


class ProfilePathError(Exception):
    """Profile PATH block could not be written safely."""


def default_profile_path(*, home: str | None = None) -> Path:
    resolved_home = home or os.environ.get("HOME")
    if not resolved_home:
        raise ProfilePathError("HOME is not set; cannot locate ~/.profile")
    return Path(resolved_home) / ".profile"


def _quote_static_path(path: str) -> str:
    return "'" + path.replace("'", "'\"'\"'") + "'"


def build_path_block(*, npm_global_bin: str | None = None) -> str:
    """Return the canonical CE-managed PATH block."""
    lines = [
        BEGIN_MARKER,
        "# Added by Creator Engine. Delete this whole marked block to undo.",
        "_ce_path_prepend() {",
        '  case ":${PATH:-}:" in',
        '    *":$1:"*) ;;',
        '    *) PATH="$1${PATH:+:$PATH}" ;;',
        "  esac",
        "}",
        '_ce_path_prepend "$HOME/.local/bin"',
    ]
    if npm_global_bin:
        lines.append(f"_ce_path_prepend {_quote_static_path(npm_global_bin)}")
    else:
        lines.extend(
            [
                '_ce_npm_bin=""',
                "if command -v npm >/dev/null 2>&1; then",
                '  _ce_npm_bin="$(npm bin -g 2>/dev/null || true)"',
                '  if [ -z "$_ce_npm_bin" ]; then',
                '    _ce_npm_prefix="$(npm prefix -g 2>/dev/null || true)"',
                '    [ -z "$_ce_npm_prefix" ] || _ce_npm_bin="${_ce_npm_prefix%/}/bin"',
                "  fi",
                '  [ -z "$_ce_npm_bin" ] || _ce_path_prepend "$_ce_npm_bin"',
                "fi",
                "unset _ce_npm_bin _ce_npm_prefix",
            ]
        )
    lines.extend(["export PATH", "unset -f _ce_path_prepend", END_MARKER])
    return "\n".join(lines) + "\n"


def _replace_or_append_block(text: str, block: str) -> str:
    begin = text.find(BEGIN_MARKER)
    end = text.find(END_MARKER)
    if begin == -1 and end == -1:
        prefix = text
        if prefix and not prefix.endswith("\n"):
            prefix += "\n"
        spacer = "\n" if prefix else ""
        return f"{prefix}{spacer}{block}"
    if begin == -1 or end == -1 or end < begin:
        raise ProfilePathError("found incomplete creator-engine PATH markers; refusing to guess")
    end += len(END_MARKER)
    if end < len(text) and text[end : end + 1] == "\n":
        end += 1
    return text[:begin] + block + text[end:]


def ensure_profile_path_block(
    profile_path: str | Path | None = None,
    *,
    npm_global_bin: str | None = None,
) -> ProfilePathResult:
    path = Path(profile_path) if profile_path is not None else default_profile_path()
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    updated = _replace_or_append_block(existing, build_path_block(npm_global_bin=npm_global_bin))
    if updated == existing:
        return ProfilePathResult(profile_path=path, changed=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding="utf-8")
    return ProfilePathResult(profile_path=path, changed=True)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ce-profile-path")
    parser.add_argument("--profile", default=None, help="shell profile to update (default: ~/.profile)")
    parser.add_argument("--npm-global-bin", default=None, help="static npm global bin path for tests")
    parser.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = ensure_profile_path_block(args.profile, npm_global_bin=args.npm_global_bin)
    except ProfilePathError as exc:
        print(f"ERROR: ce profile PATH update refused: {exc}", file=sys.stderr)
        return 1
    if args.json_output:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(result.notice())
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
