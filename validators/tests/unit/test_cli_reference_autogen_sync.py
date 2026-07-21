"""Generate-then-verify proof for the ``ce`` CLI-reference doc-autogen pilot.

Proves the load-bearing invariant of the doc-autogen design: the committed
``.ce/reference/cli.generated.md`` is a CHECKED ARTIFACT — the check passes when the doc
matches the generator's projection of the live ``ce`` argparse tree and FAILS
CLOSED when the committed doc drifts (stale or missing).
"""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

from creator_engine_validator.checks import registered_checks
from creator_engine_validator.checks.cli_reference_autogen_sync import (
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
    spec = importlib.util.spec_from_file_location("_test_gen_cli_reference", gen_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed_repo(root: Path, *, doc_text: str | None) -> None:
    """Lay down a minimal repo: the generator + (optionally) a committed doc."""
    (root / GENERATOR_RELATIVE).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_REPO_ROOT / GENERATOR_RELATIVE, root / GENERATOR_RELATIVE)
    if doc_text is not None:
        doc = root / DOC_RELATIVE
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(doc_text, encoding="utf-8")


def _codes(result) -> set[str]:
    return {error.code for error in result.errors}


def test_cli_reference_autogen_sync_is_registered():
    assert CHECK_NAME in registered_checks()


def test_committed_doc_in_repo_is_current():
    # The real committed .ce/reference/cli.generated.md must be fresh on HEAD.
    result = run([_REPO_ROOT])
    assert result.ok, [e.format() for e in result.errors]


def test_validate_pr_is_described_as_optional_diagnostic():
    rendered = _load_generator().render()

    assert "optional local PR diagnostic" in rendered


def test_passes_when_doc_matches_generator(tmp_path: Path):
    fresh = _load_generator().render()
    _seed_repo(tmp_path, doc_text=fresh)

    result = run([tmp_path])

    assert result.ok


def test_fails_closed_when_doc_is_stale(tmp_path: Path):
    fresh = _load_generator().render()
    stale = fresh + "\nDRIFTED HAND EDIT — generator was not re-run.\n"
    _seed_repo(tmp_path, doc_text=stale)

    result = run([tmp_path])

    assert not result.ok
    assert _codes(result) == {CODE_STALE}
    assert "scripts/gen_cli_reference.py --write" in result.errors[0].message


def test_fails_closed_when_doc_is_missing(tmp_path: Path):
    _seed_repo(tmp_path, doc_text=None)

    result = run([tmp_path])

    assert not result.ok
    assert _codes(result) == {CODE_STALE}


def test_generator_check_mode_round_trips(tmp_path: Path):
    """The generator's own --write then --check round-trips green (determinism)."""
    generator = _load_generator()
    _seed_repo(tmp_path, doc_text=None)

    generator.write(tmp_path)
    ok, message = generator.check(tmp_path)

    assert ok, message


def test_generator_check_mode_flags_drift(tmp_path: Path):
    generator = _load_generator()
    generator.write(tmp_path)  # writes under tmp_path/.ce/reference/cli.generated.md
    doc = tmp_path / DOC_RELATIVE
    doc.write_text(doc.read_text(encoding="utf-8") + "tamper\n", encoding="utf-8")

    ok, message = generator.check(tmp_path)

    assert not ok
    assert "stale" in message


def test_unreadable_generator_fails_closed(tmp_path: Path):
    # A generator that cannot import/render must fail closed, not silently pass.
    (tmp_path / GENERATOR_RELATIVE).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / GENERATOR_RELATIVE).write_text(
        "raise RuntimeError('boom')\n", encoding="utf-8"
    )
    (tmp_path / DOC_RELATIVE).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / DOC_RELATIVE).write_text("whatever\n", encoding="utf-8")

    result = run([tmp_path])

    assert not result.ok
    assert _codes(result) == {CODE_UNREADABLE}
