"""Generate-then-verify proof for the schema-reference doc-autogen guard."""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.schema_reference_autogen_sync import (
    CHECK_NAME,
    CODE_STALE,
    CODE_UNREADABLE,
    DOC_RELATIVE,
    GENERATOR_RELATIVE,
    run,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_generator():
    gen_path = _REPO_ROOT / GENERATOR_RELATIVE
    spec = importlib.util.spec_from_file_location("_test_gen_schema_reference", gen_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _seed_repo(root: Path, *, doc_text: str | None) -> None:
    """Lay down a minimal repo: the generator, schemas, and optional doc."""
    (root / GENERATOR_RELATIVE).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_REPO_ROOT / GENERATOR_RELATIVE, root / GENERATOR_RELATIVE)
    shutil.copytree(_REPO_ROOT / "schemas", root / "schemas")
    if doc_text is not None:
        doc = root / DOC_RELATIVE
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(doc_text, encoding="utf-8")


def _codes(result) -> set[str]:
    return {error.code for error in result.errors}


def test_schema_reference_autogen_sync_is_registered():
    assert CHECK_NAME in registered_checks()


def test_committed_schema_doc_in_repo_is_current():
    result = run([_REPO_ROOT])
    assert result.ok, [e.format() for e in result.errors]


def test_passes_when_doc_matches_generator(tmp_path: Path):
    fresh = _load_generator().render(_REPO_ROOT)
    _seed_repo(tmp_path, doc_text=fresh)

    result = run([tmp_path])

    assert result.ok


def test_fails_closed_when_doc_is_stale(tmp_path: Path):
    fresh = _load_generator().render(_REPO_ROOT)
    stale = fresh + "\nDRIFTED HAND EDIT - generator was not re-run.\n"
    _seed_repo(tmp_path, doc_text=stale)

    result = run([tmp_path])

    assert not result.ok
    assert _codes(result) == {CODE_STALE}
    assert "scripts/gen_schema_reference.py --write" in result.errors[0].message


def test_fails_closed_when_doc_is_missing(tmp_path: Path):
    _seed_repo(tmp_path, doc_text=None)

    result = run([tmp_path])

    assert not result.ok
    assert _codes(result) == {CODE_STALE}


def test_generator_check_mode_round_trips(tmp_path: Path):
    generator = _load_generator()
    _seed_repo(tmp_path, doc_text=None)

    generator.write(tmp_path)
    ok, message = generator.check(tmp_path)

    assert ok, message


def test_generator_check_mode_flags_doc_drift(tmp_path: Path):
    generator = _load_generator()
    _seed_repo(tmp_path, doc_text=None)
    generator.write(tmp_path)
    doc = tmp_path / DOC_RELATIVE
    doc.write_text(doc.read_text(encoding="utf-8") + "tamper\n", encoding="utf-8")

    ok, message = generator.check(tmp_path)

    assert not ok
    assert "stale" in message


def test_generator_check_mode_flags_schema_drift(tmp_path: Path):
    generator = _load_generator()
    _seed_repo(tmp_path, doc_text=None)
    generator.write(tmp_path)
    schema = tmp_path / "schemas" / "worker-tier-contract.schema.yaml"
    schema.write_text(
        schema.read_text(encoding="utf-8").replace(
            "Creator Engine governed worker tier contract",
            "Creator Engine governed worker tier contract DRIFTED",
        ),
        encoding="utf-8",
    )

    ok, message = generator.check(tmp_path)

    assert not ok
    assert "stale" in message


def test_unreadable_generator_fails_closed(tmp_path: Path):
    (tmp_path / GENERATOR_RELATIVE).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / GENERATOR_RELATIVE).write_text(
        "raise RuntimeError('boom')\n", encoding="utf-8"
    )
    (tmp_path / DOC_RELATIVE).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / DOC_RELATIVE).write_text("whatever\n", encoding="utf-8")

    result = run([tmp_path])

    assert not result.ok
    assert _codes(result) == {CODE_UNREADABLE}
