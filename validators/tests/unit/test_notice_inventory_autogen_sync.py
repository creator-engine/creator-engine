"""Generate-then-verify proof for NOTICE's lock-derived dependency inventory."""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.notice_inventory_autogen_sync import (
    CHECK_NAME,
    CODE_STALE,
    DOC_RELATIVE,
    GENERATOR_RELATIVE,
    run,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LOCK_RELATIVE = Path("validators/uv.lock")


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "_test_gen_notice_inventory", _REPO_ROOT / GENERATOR_RELATIVE
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed_repo(root: Path) -> None:
    (root / GENERATOR_RELATIVE).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_REPO_ROOT / GENERATOR_RELATIVE, root / GENERATOR_RELATIVE)
    (root / _LOCK_RELATIVE).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_REPO_ROOT / _LOCK_RELATIVE, root / _LOCK_RELATIVE)
    (root / DOC_RELATIVE).write_text(
        (_REPO_ROOT / DOC_RELATIVE).read_text(encoding="utf-8"), encoding="utf-8"
    )


def _codes(result) -> set[str]:
    return {error.code for error in result.errors}


def test_notice_inventory_sync_is_registered():
    assert CHECK_NAME in registered_checks()


def test_committed_notice_inventory_matches_lock():
    result = run([_REPO_ROOT])
    assert result.ok, [error.format() for error in result.errors]


def test_fails_closed_when_notice_inventory_is_stale(tmp_path: Path):
    _seed_repo(tmp_path)
    notice = tmp_path / DOC_RELATIVE
    notice.write_text(notice.read_text(encoding="utf-8").replace("`attrs` | `26.1.0`", "`attrs` | `0.0.0`"), encoding="utf-8")

    result = run([tmp_path])

    assert not result.ok
    assert _codes(result) == {CODE_STALE}


def test_fails_closed_when_lock_versions_drift(tmp_path: Path):
    _seed_repo(tmp_path)
    lock = tmp_path / _LOCK_RELATIVE
    lock.write_text(lock.read_text(encoding="utf-8").replace('name = "attrs"\nversion = "26.1.0"', 'name = "attrs"\nversion = "26.1.1"'), encoding="utf-8")

    result = run([tmp_path])

    assert not result.ok
    assert _codes(result) == {CODE_STALE}


def test_generator_write_then_check_round_trips(tmp_path: Path):
    _seed_repo(tmp_path)
    generator = _load_generator()
    generator.write(tmp_path)

    current, message = generator.check(tmp_path)

    assert current, message
