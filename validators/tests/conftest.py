import contextlib
from datetime import datetime
import io
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATORS_ROOT = REPO_ROOT / "validators"
if str(VALIDATORS_ROOT) not in sys.path:
    sys.path.insert(0, str(VALIDATORS_ROOT))

# ADR-0007 egress broker (host-side, non-agent operational tooling under
# ``tools/egress-broker/``) is exercised by the CI-collected suite here. It is
# deliberately NOT part of the installable validator package (it is host
# operations, not validator logic), so its import root is added explicitly.
EGRESS_BROKER_ROOT = REPO_ROOT / "tools" / "egress-broker"
if str(EGRESS_BROKER_ROOT) not in sys.path:
    sys.path.insert(0, str(EGRESS_BROKER_ROOT))


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "xdist_group(name): keep shared-state or session-memoized tests on one xdist worker",
    )
    config.addinivalue_line(
        "markers",
        "sweep: requests the memoized ``check-examples`` sweep (the wall-time floor); "
        "auto-applied to every consumer of the ``check_examples_result`` fixture so the "
        "inner-loop fast lane is ``-m 'not sweep'``. NEVER use the fast lane as green-gate "
        "evidence (see validators/README.md).",
    )


def pytest_collection_modifyitems(config, items):
    """Derive the ``sweep`` mark from fixture requests, not a hand-kept list.

    Any test that requests the session-scoped ``check_examples_result`` fixture pays
    the one ~60-90s ``check-examples`` sweep; that is the *semantic* definition of a
    sweep consumer, so we mark it mechanically at collection time. A future consumer
    inherits the mark by construction — no 12-file list to drift out of date.
    """
    for item in items:
        if "check_examples_result" in getattr(item, "fixturenames", ()):
            item.add_marker("sweep")


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


@pytest.fixture
def freeze_work_claim_clock(monkeypatch):
    """Freeze the work-claim runtime clock to a supplied instant (ce-ops#57 guard).

    The v3 dispatch path (``v3_cli._acquire_dispatch_claim``) and the ``ce claim``
    CLI both call ``work_claims.acquire/status/release`` *without* an explicit
    ``now``, so they evaluate staleness against wall-clock time. A fixed-date
    claim fixture (``claimed_at = 2026-06-12T14:00:00Z``) therefore silently
    crosses its stale fence on any later calendar date and flips
    ``active_foreign_claim`` -> ``stale_foreign_claim`` — the #218 date-bomb.

    This freezes ``work_claims.datetime`` to a ``datetime`` subclass whose
    ``now()`` returns the supplied aware-UTC instant, while leaving
    ``fromisoformat``/``max``/construction intact so ``compute_state`` keeps
    working. Returns the frozen ``now`` for convenience.
    """

    def _freeze(now: datetime) -> datetime:
        from creator_engine_validator import work_claims as wc

        class _FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return now if tz is None else now.astimezone(tz)

        monkeypatch.setattr(wc, "datetime", _FrozenDatetime)
        return now

    return _freeze
