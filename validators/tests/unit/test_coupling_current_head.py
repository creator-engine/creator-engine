"""Current-head coupling evidence is complete, deterministic, and fail-closed."""
from __future__ import annotations

import hashlib
import json
import subprocess

import pytest

from creator_engine_validator.forge.coupling_current_head import (
    SEED_KINDS,
    build_obligation_set,
    rederive_live_obligation_set,
    resolve_decision_base_sha,
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
    def __init__(
        self,
        *,
        head: str = _HEAD,
        base: str = _BASE,
        paths: tuple[str, ...] = _PATHS,
        state: str = "OPEN",
        is_draft: bool = False,
        view_returncode: int = 0,
        diff_returncode: int = 0,
        invalid_json: bool = False,
        raise_on: str | None = None,
    ) -> None:
        self.head = head
        self.base = base
        self.paths = paths
        self.state = state
        self.is_draft = is_draft
        self.view_returncode = view_returncode
        self.diff_returncode = diff_returncode
        self.invalid_json = invalid_json
        self.raise_on = raise_on

    def __call__(self, argv, input_text=None):
        if argv[:3] == ["gh", "pr", "view"]:
            if self.raise_on == "view":
                raise OSError("view unavailable")
            stdout = "not-json" if self.invalid_json else json.dumps({
                "headRefOid": self.head,
                "baseRefOid": self.base,
                "headRefName": _BRANCH,
                "state": self.state,
                "isDraft": self.is_draft,
            })
            return subprocess.CompletedProcess(
                argv, self.view_returncode, stdout=stdout, stderr="",
            )
        if argv[:3] == ["gh", "pr", "diff"]:
            if self.raise_on == "diff":
                raise OSError("diff unavailable")
            return subprocess.CompletedProcess(
                argv, self.diff_returncode, stdout="\n".join(self.paths) + "\n", stderr=""
            )
        raise AssertionError(argv)


def test_live_rederivation_passes_only_for_the_exact_current_subject() -> None:
    assert verify_live_current_head(_snapshot(), gh_runner=_LiveGh()).passed is True


def test_live_new_head_is_a_fail_closed_drift() -> None:
    result = verify_live_current_head(_snapshot(), gh_runner=_LiveGh(head="e" * 40))
    assert result.status == "DRIFT"
    assert set(result.drifted_kinds) == set(SEED_KINDS)


def test_live_base_only_drift_is_fail_closed() -> None:
    result = verify_live_current_head(_snapshot(), gh_runner=_LiveGh(base="c" * 40))
    assert result.status == "DRIFT"
    assert result.reason == "subject_drift"


def test_live_paths_only_drift_is_fail_closed() -> None:
    result = verify_live_current_head(_snapshot(), gh_runner=_LiveGh(paths=("README.md", "docs/new.md")))
    assert result.status == "DRIFT"
    assert result.reason == "subject_drift"


@pytest.mark.parametrize(
    ("gh", "expected"),
    [
        (_LiveGh(view_returncode=1), "live_subject_unreadable"),
        (_LiveGh(raise_on="view"), "live_subject_unreadable"),
        (_LiveGh(invalid_json=True), "live_subject_unparseable"),
        (_LiveGh(diff_returncode=1), "live_diff_unreadable"),
        (_LiveGh(raise_on="diff"), "live_diff_unreadable"),
    ],
)
def test_live_transport_and_parse_errors_fail_closed(gh: _LiveGh, expected: str) -> None:
    current, error = rederive_live_obligation_set(_snapshot(), gh_runner=gh)
    assert current is None
    assert error == expected


@pytest.mark.parametrize(
    ("gh", "expected"),
    [(_LiveGh(state="CLOSED"), "live_subject_not_open"), (_LiveGh(is_draft=True), "live_subject_draft")],
)
def test_live_non_open_or_draft_pr_is_refused(gh: _LiveGh, expected: str) -> None:
    current, error = rederive_live_obligation_set(_snapshot(), gh_runner=gh)
    assert current is None
    assert error == expected


def test_ref_name_base_resolves_through_live_pr_view() -> None:
    resolved, provenance = resolve_decision_base_sha(
        repo=_REPO, pr_number=640, base="main", gh_runner=_LiveGh()
    )
    assert resolved == _BASE
    assert provenance == "live_pr_view"


def test_ref_name_base_resolution_failure_is_not_a_snapshot() -> None:
    resolved, provenance = resolve_decision_base_sha(
        repo=_REPO, pr_number=640, base="main", gh_runner=_LiveGh(view_returncode=1)
    )
    assert (resolved, provenance) == (None, None)
