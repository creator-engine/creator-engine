"""Regression guard for creator-engine#82.

CE lane prompts / templates / docs must NOT instruct a reader to run a
*worktree-relative* ``.venv/bin/python`` (or ``.venv-*/bin/python``). Isolated git
worktrees under ``ce-worktrees/*`` carry tracked source but no local ``.venv`` (it
is gitignored and local to the canonical checkout), so such a command fails with
``.venv/bin/python: No such file or directory`` after an otherwise-valid lane
allocation.

The sanctioned convention is ``${CE_VALIDATOR_PYTHON:-python}`` (documented in
``validators/README.md``): the active interpreter by default, overridable via the
``CE_VALIDATOR_PYTHON`` env var (e.g. an absolute canonical-checkout venv path) when
running from a worktree that has no active venv.

This guard keys on a worktree-RELATIVE ``.venv*/bin/python`` *module invocation*
(``... -m ...``). It deliberately ignores absolute venv paths
(``/canonical/.venv/bin/python``), venv *activation* lines
(``source .venv/bin/activate``), env-var assignments, and prose mentions — none of
those are the bug.
"""

from __future__ import annotations

import re
from pathlib import Path

# Negative lookbehind for ``/`` or a word char excludes absolute paths and
# assignments; the trailing ``-m`` keys on an actual interpreter invocation, so
# prose mentions of ``.venv/bin/python`` do not trip the guard.
WORKTREE_VENV_PYTHON = re.compile(r"(?<![\w/])\.venv[\w.\-]*/bin/python\s+-m\b")

REPO_ROOT = Path(__file__).resolve().parents[3]


def _scanned_files() -> list[Path]:
    """Lane prompts / templates / launch-and-runtime docs — the #82 surface.

    Excludes ``validators/tests/`` (so this guard does not match its own sample
    strings) and ``.ce/`` (changelog fragments / carriers may describe the pattern).
    """
    files: list[Path] = []
    for sub in ("docs", "templates"):
        directory = REPO_ROOT / sub
        if directory.is_dir():
            files.extend(sorted(directory.rglob("*.md")))
    for rel in ("validators/README.md", "CONTRIBUTING.md", "README.md"):
        path = REPO_ROOT / rel
        if path.is_file():
            files.append(path)
    return files


def test_no_worktree_relative_venv_python_in_docs() -> None:
    offenders: list[str] = []
    for path in _scanned_files():
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if WORKTREE_VENV_PYTHON.search(line):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}")
    assert not offenders, (
        "Worktree-relative `.venv*/bin/python -m ...` found (creator-engine#82); "
        "use `${CE_VALIDATOR_PYTHON:-python}` instead:\n" + "\n".join(offenders)
    )


def test_guard_regex_flags_bad_and_ignores_good() -> None:
    bad = [
        "PYTHONPATH=validators .venv/bin/python -m pytest validators/tests -q",
        "PYTHONPATH=validators .venv-test/bin/python -m pytest validators/tests",
        ".venv3/bin/python -m creator_engine_validator check",
    ]
    good = [
        'PYTHONPATH=validators "${CE_VALIDATOR_PYTHON:-python}" -m pytest validators/tests -q',
        "PYTHONPATH=validators /home/ce/canonical/.venv/bin/python -m pytest",  # absolute path
        "PYTHONPATH=validators python -m pytest validators/tests -q",
        "source .venv-test/bin/activate",  # activation, not a python invocation
        "export CE_VALIDATOR_PYTHON=/path/to/.venv/bin/python",  # assignment, no -m
        "a hardcoded `.venv/bin/python` from such a worktree fails",  # prose
    ]
    for sample in bad:
        assert WORKTREE_VENV_PYTHON.search(sample), f"guard should flag: {sample}"
    for sample in good:
        assert not WORKTREE_VENV_PYTHON.search(sample), f"guard should ignore: {sample}"


def test_readme_documents_ce_validator_python() -> None:
    readme = (REPO_ROOT / "validators" / "README.md").read_text(encoding="utf-8")
    assert "CE_VALIDATOR_PYTHON" in readme, (
        "validators/README.md must document the CE_VALIDATOR_PYTHON convention "
        "(creator-engine#82)."
    )
