"""Unit tests for local forge resource locks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from creator_engine_validator.forge import resource_lock


def _state_root(tmp_path):
    return tmp_path / ".ce" / "state"


def test_acquire_release_is_held_and_list_held(tmp_path):
    state_root = _state_root(tmp_path)
    now = datetime(2026, 6, 28, 12, 0, tzinfo=UTC)

    record = resource_lock.acquire("worktree:/tmp/a", "seat-a", ttl=60, state_root=state_root, now=now)

    assert record.resource_id == "worktree:/tmp/a"
    assert record.holder == "seat-a"
    assert resource_lock.is_held("worktree:/tmp/a", state_root=state_root, now=now)
    assert [held.resource_id for held in resource_lock.list_held(state_root=state_root, now=now)] == [
        "worktree:/tmp/a"
    ]
    assert resource_lock.release("worktree:/tmp/a", "seat-a", state_root=state_root)
    assert not resource_lock.is_held("worktree:/tmp/a", state_root=state_root, now=now)
    assert resource_lock.list_held(state_root=state_root, now=now) == ()


def test_acquire_refuses_contended_active_lock(tmp_path):
    state_root = _state_root(tmp_path)
    now = datetime(2026, 6, 28, 12, 0, tzinfo=UTC)

    first = resource_lock.acquire("branch:feature-a", "seat-a", ttl=60, state_root=state_root, now=now)

    with pytest.raises(resource_lock.ResourceLockContended) as exc:
        resource_lock.acquire("branch:feature-a", "seat-b", ttl=60, state_root=state_root, now=now)

    assert exc.value.record == first
    assert exc.value.holder == "seat-a"


def test_stale_ttl_reclaim_replaces_holder(tmp_path):
    state_root = _state_root(tmp_path)
    start = datetime(2026, 6, 28, 12, 0, tzinfo=UTC)
    later = start + timedelta(seconds=61)

    first = resource_lock.acquire("pr:123", "seat-a", ttl=60, state_root=state_root, now=start)
    replacement = resource_lock.acquire("pr:123", "seat-b", ttl=60, state_root=state_root, now=later)

    assert first.path == replacement.path
    assert replacement.holder == "seat-b"
    assert resource_lock.is_held("pr:123", state_root=state_root, now=later)
    assert [held.holder for held in resource_lock.list_held(state_root=state_root, now=later)] == ["seat-b"]


def test_holder_identity_recorded_on_disk(tmp_path):
    state_root = _state_root(tmp_path)
    now = datetime(2026, 6, 28, 12, 0, tzinfo=UTC)

    record = resource_lock.acquire("territory:docs", "seat-a", ttl=60, state_root=state_root, now=now)

    assert record.path is not None
    payload = record.path.read_text(encoding="utf-8")
    assert '"holder": "seat-a"' in payload
    assert '"resource_id": "territory:docs"' in payload


def test_wrong_holder_release_refuses_and_keeps_lock(tmp_path):
    state_root = _state_root(tmp_path)
    now = datetime(2026, 6, 28, 12, 0, tzinfo=UTC)
    resource_lock.acquire("worktree:/tmp/a", "seat-a", ttl=60, state_root=state_root, now=now)

    with pytest.raises(resource_lock.ResourceLockOwnershipError):
        resource_lock.release("worktree:/tmp/a", "seat-b", state_root=state_root)

    assert resource_lock.is_held("worktree:/tmp/a", state_root=state_root, now=now)


def test_missing_release_is_false(tmp_path):
    assert not resource_lock.release("missing", "seat-a", state_root=_state_root(tmp_path))
