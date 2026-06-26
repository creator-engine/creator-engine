from __future__ import annotations

import json
from pathlib import Path

from creator_engine_validator import brain_probe


class FakeCompleted:
    def __init__(self, returncode: int, stdout: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
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


def test_self_identity_probe_is_deterministic_with_injected_runtime(tmp_path: Path):
    tailscale_payload = {
        "Self": {
            "DNSName": "seat-one.tailnet.example.",
            "HostName": "seat-one",
            "TailscaleIPs": ["100.64.0.10"],
        },
        "Peer": {
            "peer-a": {"DNSName": "peer-a.tailnet.example.", "Online": True},
            "peer-b": {"DNSName": "peer-b.tailnet.example.", "Online": False},
        },
    }

    def run(command):
        if command[:3] == ["tailscale", "status", "--json"]:
            return FakeCompleted(0, json.dumps(tailscale_payload))
        if command[:1] == ["nvidia-smi"]:
            return FakeCompleted(0, "NVIDIA A100\n")
        return FakeCompleted(0)

    context = brain_probe.ProbeContext(
        repo_root=tmp_path,
        env={"HOSTNAME": "seat-one", "USER": "controller"},
        run=run,
    )

    first = brain_probe.probe("self_identity", context).to_dict()
    second = brain_probe.probe("self_identity", context).to_dict()

    assert first == second
    assert first["verdict"] == "present"
    assert first["evidence"]["runtime_name"] == "seat-one"
    assert first["evidence"]["os_users"]["current_user"] == "controller"
    assert first["evidence"]["tailnet_self"]["self"]["dns_name"] == "seat-one.tailnet.example"
    assert first["evidence"]["reachable_peers"] == ["peer-a.tailnet.example"]


def test_self_identity_probe_reflects_mutated_hostname(tmp_path: Path):
    def run(command):
        if command[:1] == ["tailscale"]:
            return FakeCompleted(1)
        if command[:1] == ["nvidia-smi"]:
            return FakeCompleted(1)
        return FakeCompleted(0)

    before = brain_probe.probe(
        "self_identity",
        brain_probe.ProbeContext(repo_root=tmp_path, env={"HOSTNAME": "seat-a", "USER": "controller"}, run=run),
    )
    after = brain_probe.probe(
        "self_identity",
        brain_probe.ProbeContext(repo_root=tmp_path, env={"HOSTNAME": "seat-b", "USER": "controller"}, run=run),
    )

    assert before.evidence["runtime_name"] == "seat-a"
    assert after.evidence["runtime_name"] == "seat-b"


def test_worker_spawn_runtime_support_checks_module_and_git_worktree(tmp_path: Path):
    def run(command):
        assert command[-3:] == ["worktree", "list", "--porcelain"]
        return FakeCompleted(0, f"worktree {tmp_path}\n")

    result = brain_probe.probe(
        "worker_spawn_runtime_support",
        brain_probe.ProbeContext(repo_root=tmp_path, run=run),
    )

    assert result.verdict == "present"
    assert result.evidence["missing_entrypoints"] == []
    assert result.evidence["git_available"] is True


def test_codex_pretooluse_hook_probe_reads_committed_entrypoint(tmp_path: Path):
    hook = tmp_path / ".codex" / "hooks" / "ce-pretooluse-codex.py"
    hook.parent.mkdir(parents=True)
    hook.write_text(
        "from creator_engine_validator.codex_pretooluse import main\n",
        encoding="utf-8",
    )

    result = brain_probe.probe("codex_pretooluse_hook", brain_probe.ProbeContext(repo_root=tmp_path))

    assert result.verdict == "present"
    assert result.evidence["imports_validator_entrypoint"] is True


def test_codex_fan_out_surfaces_probe_requires_governed_role_files(tmp_path: Path):
    agents = tmp_path / ".claude" / "agents"
    agents.mkdir(parents=True)
    for name in ["architect_research.md", "implementer.md", "reviewer.md", "verification.md"]:
        (agents / name).write_text("Governed worker role\n", encoding="utf-8")

    present = brain_probe.probe("codex_fan_out_surfaces", brain_probe.ProbeContext(repo_root=tmp_path))
    (agents / "reviewer.md").unlink()
    absent = brain_probe.probe("codex_fan_out_surfaces", brain_probe.ProbeContext(repo_root=tmp_path))

    assert present.verdict == "present"
    assert absent.verdict == "absent"
    assert absent.evidence["missing"]


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
