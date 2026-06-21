from __future__ import annotations

import json
from pathlib import Path

from creator_engine_validator import brain_probe


class FakeCompleted:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode
        self.stdout = ""
        self.stderr = ""


def test_unknown_probe_returns_unknown_without_guessing():
    result = brain_probe.probe("missing-capability")

    assert result.to_dict() == {
        "evidence": {"reason": "unknown_probe"},
        "name": "missing-capability",
        "verdict": "unknown",
    }


def test_gh_authenticated_uses_injected_runner_for_present_absent_unknown():
    present = brain_probe.probe(
        "gh_authenticated",
        brain_probe.ProbeContext(run=lambda _cmd: FakeCompleted(0)),
    )
    absent = brain_probe.probe(
        "gh_authenticated",
        brain_probe.ProbeContext(run=lambda _cmd: FakeCompleted(1)),
    )

    def broken(_cmd):
        raise OSError("gh unavailable")

    unknown = brain_probe.probe("gh_authenticated", brain_probe.ProbeContext(run=broken))

    assert present.verdict == "present"
    assert absent.verdict == "absent"
    assert unknown.verdict == "unknown"
    assert present.evidence["command"] == ["gh", "auth", "status"]
    assert unknown.evidence["error"] == "OSError"


def test_merge_group_trigger_reads_workflow_through_injected_reader(tmp_path: Path):
    workflow = tmp_path / ".github" / "workflows" / "validate.yml"

    present = brain_probe.probe(
        "merge_group_trigger",
        brain_probe.ProbeContext(
            repo_root=tmp_path,
            read_text=lambda path: "on:\n  merge_group:\n    types: [checks_requested]\n",
        ),
    )
    absent = brain_probe.probe(
        "merge_group_trigger",
        brain_probe.ProbeContext(repo_root=tmp_path, read_text=lambda path: "on:\n  pull_request:\n"),
    )

    def unreadable(path: Path) -> str:
        assert path == workflow
        raise FileNotFoundError(path)

    unknown = brain_probe.probe(
        "merge_group_trigger",
        brain_probe.ProbeContext(repo_root=tmp_path, read_text=unreadable),
    )

    assert present.verdict == "present"
    assert absent.verdict == "absent"
    assert unknown.verdict == "unknown"


def test_harness_fan_out_requires_explicit_harness_signal():
    present = brain_probe.probe(
        "harness_fan_out",
        brain_probe.ProbeContext(env={"CE_HARNESS_FAN_OUT": "1"}),
    )
    absent = brain_probe.probe(
        "harness_fan_out",
        brain_probe.ProbeContext(env={"CE_HARNESS_FAN_OUT": "false"}),
    )
    unknown = brain_probe.probe("harness_fan_out", brain_probe.ProbeContext(env={}))

    assert present.verdict == "present"
    assert absent.verdict == "absent"
    assert unknown.verdict == "unknown"


def test_wheelhouse_matches_source_uses_injected_checker(tmp_path: Path):
    present = brain_probe.probe(
        "wheelhouse_matches_source",
        brain_probe.ProbeContext(repo_root=tmp_path, wheel_source_checker=lambda _root: []),
    )
    absent = brain_probe.probe(
        "wheelhouse_matches_source",
        brain_probe.ProbeContext(repo_root=tmp_path, wheel_source_checker=lambda _root: ["drift"]),
    )

    def broken(_root):
        raise ValueError("bad wheel")

    unknown = brain_probe.probe(
        "wheelhouse_matches_source",
        brain_probe.ProbeContext(repo_root=tmp_path, wheel_source_checker=broken),
    )

    assert present.verdict == "present"
    assert absent.verdict == "absent"
    assert absent.evidence["violation_count"] == 1
    assert unknown.verdict == "unknown"
    assert unknown.evidence["error"] == "ValueError"


def test_wheelhouse_matches_source_absent_when_repo_evidence_missing(tmp_path: Path):
    result = brain_probe.probe(
        "wheelhouse_matches_source",
        brain_probe.ProbeContext(repo_root=tmp_path),
    )

    assert result.verdict == "absent"
    assert result.evidence["violation_count"] == 1
    assert "missing validator source tree" in result.evidence["violations"][0]


def test_probe_invalid_injected_result_returns_unknown():
    result = brain_probe.probe(
        "gh_authenticated",
        brain_probe.ProbeContext(probes={"gh_authenticated": lambda _context: {"verdict": "present"}}),
    )

    assert result.to_dict() == {
        "evidence": {"reason": "invalid_probe_result"},
        "name": "gh_authenticated",
        "verdict": "unknown",
    }


def test_probe_all_is_sorted_and_json_deterministic(tmp_path: Path):
    context = brain_probe.ProbeContext(
        repo_root=tmp_path,
        env={},
        run=lambda _cmd: FakeCompleted(0),
        read_text=lambda _path: "on:\n  merge_group:\n    types: [checks_requested]\n",
        wheel_source_checker=lambda _root: [],
    )

    first = [result.to_dict() for result in brain_probe.probe_all(context)]
    second = [result.to_dict() for result in brain_probe.probe_all(context)]

    assert [item["name"] for item in first] == sorted(brain_probe.PROBES)
    assert json.dumps(first, sort_keys=True, separators=(",", ":")) == json.dumps(
        second, sort_keys=True, separators=(",", ":")
    )
