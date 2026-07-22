"""Contract tests for the packaged canonical issue-reference parser."""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

from creator_engine_validator import issue_refs
from creator_engine_validator import ticket_reconcile_feed as feed


_REPO_ROOT = Path(__file__).resolve().parents[3]
_VALIDATORS = _REPO_ROOT / "validators"
_SHIM = _REPO_ROOT / "tools" / "ce-ops-autoclose" / "parse_issue_refs.py"
_ISSUE_REF = "ce-" + "ops#"


def _clean_environment() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}


def _load_shim() -> object:
    spec = importlib.util.spec_from_file_location("legacy_issue_refs", _SHIM)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _python_in(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def test_canonical_parser_preserves_title_body_and_malformed_boundaries():
    assert issue_refs.parse_title_refs(f"feat({_ISSUE_REF}595): ce-518") == [595, 518]
    assert issue_refs.parse_title_refs("[ce-egress] ce-271") == [271]
    assert issue_refs.parse_body_closing_refs(f"Closes {_ISSUE_REF}5, {_ISSUE_REF}6") == [5, 6]
    assert issue_refs.parse_body_closing_refs(f"Context only: {_ISSUE_REF}5") == []
    assert issue_refs.parse_body_closing_refs(f"Fixes {_ISSUE_REF}not-a-number") == []
    assert issue_refs.parse_all_refs(f"{_ISSUE_REF}5", f"Closes {_ISSUE_REF}5; {_ISSUE_REF}6") == [5, 6]
    assert issue_refs.parse_acceptance_evidence("Acceptance-Evidence: node::case") == "node::case"


def test_editable_feed_uses_package_callable_and_legacy_shim_delegates_identically():
    shim = _load_shim()

    assert feed.parse_all_refs is issue_refs.parse_all_refs
    assert shim.parse_all_refs is issue_refs.parse_all_refs
    assert shim.parse_title_refs is issue_refs.parse_title_refs
    assert shim.parse_body_closing_refs is issue_refs.parse_body_closing_refs
    assert shim.parse_acceptance_evidence is issue_refs.parse_acceptance_evidence


def test_bare_checkout_dynamic_shim_loads_only_canonical_module(tmp_path):
    script = f"""
import importlib.util
from pathlib import Path

shim = Path({_SHIM.as_posix()!r})
spec = importlib.util.spec_from_file_location('bare_checkout_issue_refs', shim)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
reference = 'ce-' + 'ops#'
assert module.parse_all_refs(f'feat({{reference}}595)', f'Closes {{reference}}596') == [595, 596]
assert module.parse_all_refs.__module__ == 'ce_issue_refs_canonical'
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=tmp_path,
        env=_clean_environment(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_wheel_install_exposes_canonical_parser_from_site_packages(tmp_path):
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    build = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-index",
            "--no-deps",
            "--no-build-isolation",
            "--ignore-requires-python",
            str(_VALIDATORS),
            "--wheel-dir",
            str(wheelhouse),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        env=_clean_environment(),
    )
    assert build.returncode == 0, build.stderr
    wheels = list(wheelhouse.glob("creator_engine_validator-*.whl"))
    assert len(wheels) == 1

    environment = tmp_path / "wheel-env"
    create = subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(environment)],
        text=True,
        capture_output=True,
        check=False,
        env=_clean_environment(),
    )
    assert create.returncode == 0, create.stderr
    wheel_python = _python_in(environment)
    install = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "--python",
            str(wheel_python),
            "install",
            "--no-index",
            "--no-deps",
            "--ignore-requires-python",
            str(wheels[0]),
        ],
        text=True,
        capture_output=True,
        check=False,
        env=_clean_environment(),
    )
    assert install.returncode == 0, install.stdout + install.stderr

    smoke = """
from pathlib import Path
from creator_engine_validator import issue_refs

reference = 'ce-' + 'ops#'
assert issue_refs.parse_all_refs(f'feat({reference}595)', f'Closes {reference}596') == [595, 596]
assert 'site-packages' in Path(issue_refs.__file__).parts
"""
    imported = subprocess.run(
        [str(wheel_python), "-I", "-c", smoke],
        cwd=tmp_path,
        env=_clean_environment(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert imported.returncode == 0, imported.stderr
