from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATORS_ROOT = REPO_ROOT / "validators"
if str(VALIDATORS_ROOT) not in sys.path:
    sys.path.insert(0, str(VALIDATORS_ROOT))


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
