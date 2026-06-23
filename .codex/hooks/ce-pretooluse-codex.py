#!/usr/bin/env python3
"""Repo-local Codex PreToolUse hook entrypoint."""
from __future__ import annotations

import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


ROOT = _repo_root()
sys.path.insert(0, str(ROOT / "validators"))

from creator_engine_validator.codex_pretooluse import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
