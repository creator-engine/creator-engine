import contextlib
import io
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATORS_ROOT = REPO_ROOT / "validators"
if str(VALIDATORS_ROOT) not in sys.path:
    sys.path.insert(0, str(VALIDATORS_ROOT))


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "xdist_group(name): keep shared-state or session-memoized tests on one xdist worker",
    )


@pytest.fixture(scope="session")
def check_examples_result():
    from creator_engine_validator import cli as validator_cli

    output = io.StringIO()
    with contextlib.chdir(REPO_ROOT), contextlib.redirect_stdout(output):
        exit_code = validator_cli.main(["check-examples"])
    return exit_code, output.getvalue()


@pytest.fixture(scope="session")
def version_boundary_modules():
    from creator_engine_validator.checks.version_boundary import (
        _package_dir,
        discover_modules,
    )

    return discover_modules(_package_dir())


@pytest.fixture(scope="session")
def version_boundary_real_run():
    from creator_engine_validator.checks.version_boundary import run

    return run([])


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def examples_root(repo_root: Path) -> Path:
    return repo_root / "examples"


@pytest.fixture
def tenants_root(repo_root: Path) -> Path:
    return repo_root / "tenants"


@pytest.fixture
def validators_root(repo_root: Path) -> Path:
    return repo_root / "validators"
