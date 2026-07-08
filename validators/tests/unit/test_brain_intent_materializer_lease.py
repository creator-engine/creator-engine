from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import creator_engine_validator.brain_intent_materializer as materializer
from creator_engine_validator.brain_intent_materializer import MaterializerLease
from creator_engine_validator.daemon_lease import DaemonLeaseHeld


class FakeLease:
    released = False

    def release(self) -> None:
        self.released = True


def test_materializer_lease_calls_daemon_lease_for_brain_append(tmp_path: Path):
    calls = []
    fake = FakeLease()

    def acquire(*args, **kwargs):
        calls.append((args, kwargs))
        return fake

    lease = MaterializerLease(tmp_path / ".ce" / "state" / "brain-intent-materializer", acquire_func=acquire)
    lease.acquire()
    lease.release()

    assert calls[0][0][:2] == ("brain-append", "brain-intent-materializer")
    assert calls[0][1]["state_root"] == tmp_path / ".ce" / "state" / "brain-intent-materializer" / "leases"
    assert fake.released


def test_second_acquisition_while_first_is_held_raises(tmp_path: Path):
    root = tmp_path / ".ce" / "state" / "brain-intent-materializer"
    first = MaterializerLease(root).acquire()
    try:
        with pytest.raises(DaemonLeaseHeld):
            MaterializerLease(root).acquire()
    finally:
        first.release()


def test_lease_releases_on_context_exit(tmp_path: Path):
    root = tmp_path / ".ce" / "state" / "brain-intent-materializer"

    with MaterializerLease(root):
        assert (root / "leases" / "brain-append.lease").is_file()

    assert not (root / "leases" / "brain-append.lease").exists()


def test_module_docstring_contains_q4_singleton_caveat():
    assert inspect.getdoc(materializer)
    assert (
        "Under multi-instance topology this local lease is not a correctness guard; correctness then requires an external linearizable lock with the same brain-append exclusion scope (Q4 ratified ruling)."
        in inspect.getdoc(materializer)
    )
