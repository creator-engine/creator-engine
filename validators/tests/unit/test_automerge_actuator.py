from __future__ import annotations

import json
import subprocess
from pathlib import Path

from creator_engine_validator.forge.automerge_actuator import actuate_if_ready

_REPO = "creator-engine/creator-engine"
_HEAD = "d" * 40
_POLICY_SHA = "a" * 64


class FakeActuatorGh:
    def __init__(self, *, check_conclusion: str = "success") -> None:
        self.check_conclusion = check_conclusion
        self.calls: list[list[str]] = []

    def __call__(self, argv, input_text=None):
        self.calls.append(list(argv))
        if argv[:3] == ["gh", "pr", "checks"]:
            payload = [{"name": "validate", "conclusion": self.check_conclusion}]
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")

        query = next((str(arg) for arg in argv if str(arg).startswith("query=")), "")
        if "enablePullRequestAutoMerge" in query:
            payload = {
                "data": {
                    "enablePullRequestAutoMerge": {
                        "pullRequest": {
                            "autoMergeRequest": {
                                "enabledAt": "now",
                                "mergeMethod": "SQUASH",
                            }
                        }
                    }
                }
            }
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")

        payload = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "id": "PR_kwDO",
                        "autoMergeRequest": None,
                    }
                }
            }
        }
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")

    def mutation_calls(self) -> list[list[str]]:
        return [
            call
            for call in self.calls
            if any("enablePullRequestAutoMerge" in str(arg) for arg in call)
        ]


def _decision(**overrides):
    payload = {
        "class": "tiny",
        "size_band": "target_advisory",
        "minimum_work_class": "tiny",
        "mutation_class": "docs",
        "gates": ["auto_back_gate"],
        "decision": "AUTO",
        "rationale": ["all_auto_guards_passed"],
        "policy_sha": _POLICY_SHA,
        "checks_snapshot": {"required_checks": ["validate"]},
        "required_checks": ["validate"],
        "run_mode": "ceo",
        "kill_switch": False,
        "class_flag": True,
        "enabling_decision_ref": "ce-ops#313-enable",
        "reviewDecision": "APPROVED",
        "checks_green": True,
        "pr_number": 313,
        "head_sha": _HEAD,
        "change": {
            "repo": _REPO,
            "branch": "ce-automerge-actuator",
            "base": "main",
            "pr_number": 313,
            "head_sha": _HEAD,
            "manifest_paths": [".ce/pr-manifests/ce-automerge-actuator.md"],
        },
    }
    payload.update(overrides)
    return payload


def _write(tmp_path: Path, payload) -> Path:
    path = tmp_path / "decision.json"
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_dormant_in_dev_makes_no_mutating_gh_calls(tmp_path: Path) -> None:
    gh = FakeActuatorGh()
    result = actuate_if_ready(_write(tmp_path, _decision(run_mode="dev")), gh_runner=gh)

    assert result.dormant is True
    assert result.reason == "run_mode_dev"
    assert result.acted is False
    assert gh.calls == []


def test_refuses_decision_not_auto(tmp_path: Path) -> None:
    gh = FakeActuatorGh()
    result = actuate_if_ready(_write(tmp_path, _decision(decision="GESTURE")), gh_runner=gh)

    assert result.refused is True
    assert result.reason == "decision_not_auto"
    assert gh.mutation_calls() == []


def test_refuses_kill_switch(tmp_path: Path) -> None:
    gh = FakeActuatorGh()
    result = actuate_if_ready(_write(tmp_path, _decision(kill_switch=True)), gh_runner=gh)

    assert result.refused is True
    assert result.reason == "kill_switch_not_false"
    assert gh.mutation_calls() == []


def test_refuses_class_flag_false(tmp_path: Path) -> None:
    gh = FakeActuatorGh()
    result = actuate_if_ready(_write(tmp_path, _decision(class_flag=False)), gh_runner=gh)

    assert result.refused is True
    assert result.reason == "class_flag_not_true"
    assert gh.mutation_calls() == []


def test_refuses_missing_enabling_ref(tmp_path: Path) -> None:
    gh = FakeActuatorGh()
    payload = _decision()
    del payload["enabling_decision_ref"]
    result = actuate_if_ready(_write(tmp_path, payload), gh_runner=gh)

    assert result.refused is True
    assert result.reason == "enabling_decision_ref_missing"
    assert gh.mutation_calls() == []


def test_refuses_red_required_check(tmp_path: Path) -> None:
    gh = FakeActuatorGh(check_conclusion="failure")
    result = actuate_if_ready(_write(tmp_path, _decision()), gh_runner=gh)

    assert result.refused is True
    assert result.reason == "required_checks_not_green"
    assert gh.mutation_calls() == []


def test_actuates_only_when_all_green(tmp_path: Path) -> None:
    gh = FakeActuatorGh()
    result = actuate_if_ready(_write(tmp_path, _decision()), gh_runner=gh)

    assert result.actuated is True
    assert result.acted is True
    assert result.reason == "all_predicates_green"
    assert len(gh.mutation_calls()) == 1
    assert result.auto_merge_result.enabled is True
