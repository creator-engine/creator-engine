"""Fail-closed freshness guard for NOTICE's lock-derived dependency inventory."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Iterable

from ..reporting import CheckResult, ValidationError, make_error
from . import register

CHECK_NAME = "notice_inventory_autogen_sync"
CODE_STALE = "VAL-AUTOGEN-STALE-NOTICE"
CODE_UNREADABLE = "VAL-AUTOGEN-NOTICE-UNREADABLE"
DOC_RELATIVE = Path("NOTICE")
GENERATOR_RELATIVE = Path("scripts/gen_notice_inventory.py")
CONTRACT = str(GENERATOR_RELATIVE)


def _repo_root_for(path: Path) -> Path | None:
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / GENERATOR_RELATIVE).is_file():
            return candidate
    return None


def _load_generator(repo_root: Path):
    spec = importlib.util.spec_from_file_location(
        "creator_engine_validator._gen_notice_inventory", repo_root / GENERATOR_RELATIVE
    )
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load generator at {repo_root / GENERATOR_RELATIVE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_repo(repo_root: Path) -> list[ValidationError]:
    try:
        generator = _load_generator(repo_root)
        current, message = generator.check(repo_root)
    except Exception as exc:  # noqa: BLE001 - the legal inventory fails closed
        return [
            make_error(
                CODE_UNREADABLE,
                repo_root / GENERATOR_RELATIVE,
                "",
                f"NOTICE-inventory generator is unrenderable: {exc}",
                CONTRACT,
            )
        ]
    if current:
        return []
    code = CODE_UNREADABLE if "unreadable" in message else CODE_STALE
    return [make_error(code, repo_root / DOC_RELATIVE, "", message, CONTRACT)]


@register(CHECK_NAME, [CODE_STALE, CODE_UNREADABLE])
def run(paths: Iterable[Path]) -> CheckResult:
    roots: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        root = _repo_root_for(Path(raw))
        if root is not None and root.resolve() not in seen:
            seen.add(root.resolve())
            roots.append(root)
    errors = [error for root in roots for error in validate_repo(root)]
    return CheckResult(name=CHECK_NAME, errors=tuple(errors))
