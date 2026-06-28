"""ce-ops#331 — end-to-end wheel packaging proof (the gap CI missed).

The unit invariants in ``tests/unit/test_schema_packaging_completeness.py`` assert
the conditions that make the wheel ship the schemas and the resolver find them.
This integration test closes the loop that the existing suite never exercised —
it always ran from the source tree (CWD = repo root, schemas present), which is
exactly why the "installed wheel ships ZERO schema files" blocker went unnoticed.

Here we build the wheel from source, ``pip install`` it into a FRESH clean venv
that has NO access to the source ``schemas/``, then run ``ce brain init`` from a
throwaway non-repo directory and assert it writes a valid genesis ledger.
"""
from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

STRICT_ENV = "CE_SCHEMA_PACKAGING_STRICT"
REQUIRED_DEV_WHEEL_PROJECTS = ("build", "setuptools")


def _venv_bin(venv_dir: Path, name: str) -> Path:
    bindir = "Scripts" if os.name == "nt" else "bin"
    exe = f"{name}.exe" if os.name == "nt" else name
    return venv_dir / bindir / exe


def _strict_schema_packaging_lane() -> bool:
    return os.environ.get(STRICT_ENV) == "1" or os.environ.get("CI") == "true"


def _skip_or_fail(message: str) -> None:
    if _strict_schema_packaging_lane():
        pytest.fail(f"{message} ({STRICT_ENV}=1/CI strict lane must run this test)")
    pytest.skip(message)


def _assert_dev_build_wheels_vendored(validators_dir: Path) -> None:
    wheelhouse_dev = validators_dir / "wheelhouse-dev"
    missing = [
        project
        for project in REQUIRED_DEV_WHEEL_PROJECTS
        if not any(wheelhouse_dev.glob(f"{project}-*.whl"))
    ]
    if missing:
        _skip_or_fail(
            "schema packaging integration test must not skip for missing build "
            "backend tooling; vendor these wheels in validators/wheelhouse-dev/: "
            + ", ".join(missing)
        )


def test_installed_wheel_resolves_schemas_from_non_repo_cwd(repo_root: Path, tmp_path: Path):
    """A wheel-installed CLI resolves its schemas from a non-repo CWD (ce-ops#331)."""
    validators_dir = repo_root / "validators"
    if not validators_dir.is_dir():  # pragma: no cover - installed-wheel context
        _skip_or_fail("no source tree to build from")
    if sys.version_info < (3, 14):  # pragma: no cover - contract floor
        _skip_or_fail("packaging contract targets python>=3.14")

    # 1. Build the wheel from source.
    _assert_dev_build_wheels_vendored(validators_dir)
    dist_dir = tmp_path / "dist"
    build_cmd = [
        sys.executable,
        "-m",
        "build",
        "--wheel",
        "--no-isolation",
        "--outdir",
        str(dist_dir),
        str(validators_dir),
    ]
    try:
        proc = subprocess.run(build_cmd, capture_output=True, text=True, timeout=600)
    except (FileNotFoundError, subprocess.SubprocessError) as exc:  # pragma: no cover
        _skip_or_fail(f"python -m build unavailable; offline dev wheelhouse install is broken: {exc}")
    if proc.returncode != 0:  # pragma: no cover - environment guard
        _skip_or_fail(
            "wheel build failed; build backend/deps must be available from "
            f"validators/wheelhouse-dev/ in the offline lane:\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    wheels = sorted(dist_dir.glob("creator_engine_validator-*.whl"))
    assert len(wheels) == 1, f"expected one wheel, got {[w.name for w in wheels]}"
    wheel = wheels[0]

    # The wheel must physically carry the schema files.
    with zipfile.ZipFile(wheel) as zf:
        shipped = [n for n in zf.namelist() if n.endswith(".schema.yaml")]
    assert shipped, "built wheel ships ZERO schema files (ce-ops#331 regression)"

    # 2. Fresh clean venv built by the base interpreter (creating a venv from
    #    within a venv via the in-process API can yield a broken pip), then
    #    install ONLY the built wheel into it. Runtime deps are resolved offline
    #    from the vendored ``validators/wheelhouse/`` when present so this runs in
    #    CI's offline lane.
    venv_dir = tmp_path / "clean-venv"
    mk = subprocess.run(
        [sys.executable, "-m", "venv", "--clear", str(venv_dir)],
        capture_output=True, text=True, timeout=300,
    )
    if mk.returncode != 0:  # pragma: no cover - environment guard
        _skip_or_fail(f"could not create clean venv:\n{mk.stderr}")
    py = _venv_bin(venv_dir, "python")
    wheelhouse = validators_dir / "wheelhouse"
    install_cmd = [str(py), "-m", "pip", "install", "--quiet"]
    if wheelhouse.is_dir():
        install_cmd += ["--no-index", "--find-links", str(wheelhouse)]
    install_cmd.append(str(wheel))
    # Strip PYTHONPATH so the SOURCE package on the parent's path cannot satisfy
    # the requirement (pip would otherwise see it "already installed" and skip the
    # wheel, leaving no console script) — and so resolution is genuinely
    # wheel-only, which is the whole point of this test.
    clean_install_env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    clean_install_env["PYTHONPATH"] = ""
    install = subprocess.run(
        install_cmd, capture_output=True, text=True, timeout=600, env=clean_install_env
    )
    if install.returncode != 0:  # pragma: no cover - offline/dep guard
        _skip_or_fail(f"pip install of built wheel failed (offline deps?):\n{install.stderr}")
    ce = _venv_bin(venv_dir, "ce")
    if not ce.is_file():  # pragma: no cover - environment guard
        _skip_or_fail(
            "clean venv has no 'ce' console script after install "
            f"(venv/pip environment issue):\n{install.stdout}\n{install.stderr}"
        )

    # 3. Run a schema-validating command from a NON-repo CWD, with a clean env so
    #    the source tree's ``schemas/`` cannot be discovered via CWD or PYTHONPATH.
    work = tmp_path / "notarepo"
    work.mkdir()
    state_root = work / ".ce" / "state"
    clean_env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PWD"}}
    clean_env["PYTHONPATH"] = ""
    run = subprocess.run(
        [str(ce), "brain", "init", "--state-root", str(state_root)],
        cwd=str(work), capture_output=True, text=True, timeout=120, env=clean_env,
    )
    assert run.returncode == 0, (
        "ce brain init from a non-repo CWD failed against the installed wheel "
        f"(ce-ops#331):\nstdout:\n{run.stdout}\nstderr:\n{run.stderr}"
    )
    ledger = state_root / "brain" / "assertions.yaml"
    assert ledger.is_file(), f"genesis ledger was not written: {ledger}"
