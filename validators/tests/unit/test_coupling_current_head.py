"""Current-head coupling evidence is complete, deterministic, and fail-closed."""
from __future__ import annotations

import hashlib
import json
import subprocess

import pytest

from creator_engine_validator.forge.coupling_current_head import (
    SEED_KINDS,
    build_obligation_set,
    verify_live_current_head,
    verify_obligation_set,
)

_REPO = "creator-engine/creator-engine"
_BASE = "b" * 40
_HEAD = "d" * 40
_BRANCH = "ce640-coupling-current-head-gate"
_PATHS = ("README.md", ".ce/pr-manifests/ce640-coupling-current-head-gate.md")


def _snapshot() -> dict:
    result = build_obligation_set(
        repo=_REPO, pr_number=640, base=_BASE, head=_HEAD, branch=_BRANCH, paths=_PATHS,
    )
    assert result is not None
    return result


def _rehash(snapshot: dict) -> None:
    payload = {key: value for key, value in snapshot.items() if key != "obligation_set_sha256"}
    snapshot["obligation_set_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def test_clean_rederivation_passes() -> None:
    snapshot = _snapshot()
    result = verify_obligation_set(snapshot, _snapshot())
    assert result.passed is True
    assert result.reason == "current_head_matches"


@pytest.mark.parametrize("kind", SEED_KINDS)
def test_each_seed_coupling_refuses_decision_time_drift(kind: str) -> None:
    expected = _snapshot()
    current = _snapshot()
    for obligation in current["obligations"]:
        if obligation["kind"] == kind:
            obligation["subject"]["paths_sha256"] = "a" * 64
            break
    _rehash(current)

    result = verify_obligation_set(expected, current)
    assert result.status == "DRIFT"
    assert kind in result.drifted_kinds


class _LiveGh:
    def __init__(self, *, head: str = _HEAD, paths: tuple[str, ...] = _PATHS) -> None:
        self.head = head
        self.paths = paths

    def __call__(self, argv, input_text=None):
        if argv[:3] == ["gh", "pr", "view"]:
            return subprocess.CompletedProcess(
                argv, 0,
                stdout=json.dumps({"headRefOid": self.head, "baseRefOid": _BASE, "headRefName": _BRANCH}),
                stderr="",
            )
        if argv[:3] == ["gh", "pr", "diff"]:
            return subprocess.CompletedProcess(argv, 0, stdout="\n".join(self.paths) + "\n", stderr="")
        raise AssertionError(argv)


def test_live_rederivation_passes_only_for_the_exact_current_subject() -> None:
    assert verify_live_current_head(_snapshot(), gh_runner=_LiveGh()).passed is True


def test_live_new_head_is_a_fail_closed_drift() -> None:
    result = verify_live_current_head(_snapshot(), gh_runner=_LiveGh(head="e" * 40))
    assert result.status == "DRIFT"
    assert set(result.drifted_kinds) == set(SEED_KINDS)
