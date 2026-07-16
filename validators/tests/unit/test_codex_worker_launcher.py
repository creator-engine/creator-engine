"""Hermetic contracts for the policy-bound Codex one-shot launcher."""
from __future__ import annotations

from pathlib import Path

import pytest

from creator_engine_validator import codex_worker_launcher as launcher


REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = REPO_ROOT / "governance" / "policies" / "codex-one-shot-launch-v1.yaml"
WORKTREE = "/tmp/allocated-worker"
PINNED_BINARY = "/opt/creator-engine/codex/2026.07.16/bin/codex"


class RecordingRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[str, ...], str]] = []

    def run(self, argv, *, stdin: str) -> int:
        self.calls.append((tuple(argv), stdin))
        return 0


def policy() -> launcher.CodexOneShotPolicy:
    return launcher.load_policy(POLICY_PATH)


def plan(**overrides) -> launcher.CodexWorkerLaunchPlan:
    values = {
        "policy": policy(),
        "role": "implementer",
        "venue": "contained",
        "worktree": WORKTREE,
        "run_id": "test-run",
    }
    values.update(overrides)
    return launcher.build_launch_plan(**values)


def test_plan_has_exact_deterministic_argv_and_defaults() -> None:
    built = plan()
    assert built.model == "gpt-5.6-terra"
    assert built.effort == "high"
    assert built.argv == (
        PINNED_BINARY,
        "exec",
        "--ephemeral",
        "-c",
        "features.multi_agent=false",
        "-c",
        "features.multi_agent_v2=false",
        "-s",
        "danger-full-access",
        "-C",
        WORKTREE,
        "--add-dir",
        f"{WORKTREE}/governance",
        "--add-dir",
        f"{WORKTREE}/validators",
        "-o",
        f"{WORKTREE}/.ce/state/codex-one-shot/test-run.json",
        "-",
    )


def test_derived_run_id_and_output_are_repeatable() -> None:
    first = plan(run_id=None)
    second = plan(run_id=None)
    assert first.run_id == second.run_id
    assert first.output == second.output


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"role": "controller"}, "unknown role"),
        ({"venue": "vps"}, "unknown venue"),
        ({"codex_binary": "codex"}, "absolute"),
        ({"codex_binary": "/opt/other/codex"}, "does not match"),
        ({"add_dirs": [f"{WORKTREE}/governance", f"{WORKTREE}/governance"]}, "duplicate"),
        ({"add_dirs": ["/tmp/escape"]}, "escapes"),
        ({"caller_flags": ["--dangerously-bypass-approvals-and-sandbox"]}, "not permitted"),
    ],
)
def test_refusals_happen_while_building_plan(values, message: str) -> None:
    with pytest.raises(launcher.CodexWorkerLaunchError, match=message):
        plan(**values)


def test_add_dirs_are_canonical_not_caller_order() -> None:
    built = plan(add_dirs=[f"{WORKTREE}/validators", f"{WORKTREE}/governance"])
    assert [value for index, value in enumerate(built.argv) if built.argv[index - 1] == "--add-dir"] == [
        f"{WORKTREE}/governance",
        f"{WORKTREE}/validators",
    ]


def test_explicit_output_must_match_deterministic_path() -> None:
    with pytest.raises(launcher.CodexWorkerLaunchError, match="deterministic"):
        plan(output="/tmp/untrusted-output.json")


def test_strict_policy_rejects_unknown_keys(tmp_path: Path) -> None:
    raw = POLICY_PATH.read_text(encoding="utf-8") + "unknown_key: denied\n"
    candidate = tmp_path / "policy.yaml"
    candidate.write_text(raw, encoding="utf-8")
    with pytest.raises(launcher.CodexWorkerLaunchError, match="keys"):
        launcher.load_policy(candidate)


def test_only_explicit_launch_calls_injected_runner() -> None:
    runner = RecordingRunner()
    built = plan()
    assert runner.calls == []
    assert launcher.launch(built, runner=runner, stdin="bounded prompt") == 0
    assert runner.calls == [(built.argv, "bounded prompt")]
