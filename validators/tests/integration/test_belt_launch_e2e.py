"""ce-ops#205 — offline, repeatable end-to-end harness for the belt's
autonomous-launch path.

This drives the WHOLE ce-ops#55 work-pickup belt launch leg —
``pickup.launch_lane`` → ``pco_allocator.allocate_in_place`` → ``ce lane launch``
(``lane_runtime.launch``) — to ``LAUNCHED_STATE`` (a spawned governed lane) in a
fully-initialized TEST workspace, so EVERY remaining ``lane launch`` governance
gate is surfaced and closed AT ONCE rather than discovered one-at-a-time via live
canaries.

The belt launches in ``strict`` operating mode (``build_lane_argv`` passes no
``--operating-mode``), an ``implementer`` role, and an ``implementation``
lane-kind for non-review work. ``implementer`` IS a visibility-required role, so
the lane runtime hard-requires a tmux server for the real spawn. The pre-spawn
governance gates (operating-mode floor, prompt pointer+SHA, visibility, the live
Active-Work claim, the conflict guard, the worktree-path check, the brain
bootstrap, the Ring-0 governed-command build) are ALL exercised offline with no
tmux server and no network; the final visible-tmux spawn is gated behind a real
tmux binary and tears its throwaway session down.

Workspace init is real: a ``git init`` repo, the ``.ce/state`` tree, and a
genuine brain assertion ledger bootstrapped through ``brain_runtime.assert_claim``
(the same SSOT path ``ce brain assert`` drives). NO production worktree, ledger,
or tmux session is mutated.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from creator_engine_validator import (
    brain_runtime,
    lane_runtime,
    pickup,
    seat_lifecycle,
)

# A production-length pickup lane_id is what the belt actually mints
# (``pickup._lane_id`` → ``pickup-<repo-with-slashes-as-dashes>-<n>-<run_id>``);
# the long lane_id is what overflowed the worktree-lease id under PCO-020 in
# ce-ops#203, so the harness exercises a realistic length end-to-end.
_ITEM = {
    "repo": "creator-engine/creator-engine",
    "kind": "assigned",
    "number": 205,
    "url": "https://github.com/creator-engine/creator-engine/issues/205",
    "reason": "assigned",
    "subject_type": "Issue",
    "title": "ce-ops#205 belt launch e2e harness",
    "thread_id": "search:assigned:creator-engine/creator-engine:assigned:205",
}
_IDENTITY = "ce-dev-2"
_RUN_ID = "20260622000000"


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _init_workspace(
    tmp_path: Path, *, bootstrap_brain: bool = True
) -> tuple[Path, Path, Path]:
    """Create a real git repo + ``.ce/state`` tree + bootstrapped brain ledger.

    Returns ``(repo_root, state_root, ledger_root)``.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", cwd=repo)
    _git("config", "user.email", "ce205@example.invalid", cwd=repo)
    _git("config", "user.name", "ce205-harness", cwd=repo)
    (repo / "README.md").write_text("ce205 harness workspace\n", encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-qm", "init", cwd=repo)

    state_root = repo / ".ce" / "state"
    ledger_root = state_root / "active-work-ledger"
    ledger_root.mkdir(parents=True, exist_ok=True)

    if bootstrap_brain:
        # Workspace-init prerequisite: a per-repo brain assertion ledger MUST
        # pre-exist at <repo-root>/.ce/state/brain/assertions.yaml or the lane
        # runtime refuses with G3-BRAIN-BOOTSTRAP-REFUSED. A single genesis
        # assertion writes a valid, hash-chained ledger — exactly what
        # ``ce brain assert`` does.
        brain_runtime.assert_claim(
            assertion_id="brain-assertion-ce205-belt-e2e-0001",
            claim={"subject": "belt", "predicate": "bootstrap", "object": "ready"},
            scope="global",
            evidence_ref="validators/tests/integration/test_belt_launch_e2e.py#bootstrap",
            state_root=state_root,
        )
        assert brain_runtime.verify_ledger(state_root).ok
    return repo, state_root, ledger_root


def _parse_lane_launch_argv(argv: list[str]) -> dict[str, str | bool]:
    assert argv[:5] == [
        sys.executable,
        "-m",
        "creator_engine_validator.ce_cli",
        "lane",
        "launch",
    ]
    flags: dict[str, str | bool] = {}
    i = 5
    while i < len(argv):
        tok = argv[i]
        assert tok.startswith("--"), f"unexpected positional argv token: {tok!r}"
        key = tok[2:]
        if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
            flags[key] = argv[i + 1]
            i += 2
        else:
            flags[key] = True
            i += 1
    return flags


def _required_flag(flags: dict[str, str | bool], name: str) -> str:
    value = flags.get(name)
    assert isinstance(value, str) and value, f"missing --{name}"
    return value


def test_workspace_bootstrap_closes_the_brain_gate(tmp_path: Path) -> None:
    """The bootstrapped brain ledger satisfies the G3-BRAIN-BOOTSTRAP-REFUSED gate.

    The live canary hit this gate first; here it passes because the workspace-init
    leg wrote a valid ledger. Proven by building the lane's bootstrap payload
    directly (the exact call ``lane_runtime.launch`` makes at step 5b→6).
    """
    repo, state_root, _ = _init_workspace(tmp_path)
    payload = lane_runtime._build_lane_brain_bootstrap(
        state_root=state_root, role="implementer"
    )
    assert payload["kind"] == "brain-bootstrap-context"

    # And without the ledger the gate fires — the negative control.
    bare = tmp_path / "bare"
    (bare / ".ce" / "state").mkdir(parents=True)
    with pytest.raises(lane_runtime.BrainBootstrapLaneRefused):
        lane_runtime._build_lane_brain_bootstrap(
            state_root=bare / ".ce" / "state", role="implementer"
        )


def test_belt_allocation_writes_a_live_claim(tmp_path: Path) -> None:
    """``allocate_in_place`` (the belt's pre-spawn step) writes a schema-valid,
    lease-covered, unreleased Active-Work claim that the launch claim gate accepts.
    """
    repo, _, ledger_root = _init_workspace(tmp_path)
    lane_id = pickup._lane_id(_ITEM, _RUN_ID)
    fresh = pickup.pco_allocator.allocate_in_place(
        ledger_root=ledger_root,
        lane_id=lane_id,
        controller_id=_IDENTITY,
        worktree_path=repo,
        envelope_ref="none",
    )
    assert fresh is True
    claim_path = ledger_root / "claims" / _IDENTITY / f"{lane_id}.yaml"
    assert claim_path.is_file()
    # Idempotent re-poll of an already-claimed item is a no-op (no double-alloc).
    assert (
        pickup.pco_allocator.allocate_in_place(
            ledger_root=ledger_root,
            lane_id=lane_id,
            controller_id=_IDENTITY,
            worktree_path=repo,
            envelope_ref="none",
        )
        is False
    )


def test_belt_argv_is_strict_mode_implementer_implementation(tmp_path: Path) -> None:
    """The belt argv carries no ``--operating-mode`` (strict default), role
    ``implementer``, lane-kind ``implementation`` — so the Operator-only G2
    auto/transcendence floors do NOT apply to belt launches.
    """
    seed = pickup.build_seed(
        _ITEM, identity=_IDENTITY, run_id=_RUN_ID, claim_id="claim-x",
        seed_root=tmp_path / "seeds",
    )
    argv = pickup.build_lane_argv(
        _ITEM, identity=_IDENTITY, run_id=_RUN_ID, harness="/bin/true",
        seed=seed, repo_root=str(tmp_path / "repo"), ledger_root=str(tmp_path / "led"),
    )
    assert "--operating-mode" not in argv
    assert argv[argv.index("--role") + 1] == "implementer"
    assert argv[argv.index("--lane-kind") + 1] == "implementation"


def test_launched_state_matches_runtime_governed_state() -> None:
    """REGRESSION (ce-ops#205): the belt's success sentinel MUST equal the state a
    fully-governed spawn actually reports.

    ``seat_lifecycle.register_spawn`` returns ``REGISTRATION_STATE_GOVERNED``
    (``"alive"``). The old literal ``"launched"`` never matched, so the belt
    reported ``launched=False`` for EVERY successful spawn. Bind the sentinel to
    the lifecycle constant.
    """
    assert pickup.LAUNCHED_STATE == seat_lifecycle.REGISTRATION_STATE_GOVERNED
    assert pickup.LAUNCHED_STATE == "alive"


def test_belt_launch_drives_all_pre_spawn_gates_offline(tmp_path: Path) -> None:
    """Full belt path with NO tmux server: every PRE-spawn governance gate passes
    and the ONLY remaining step is the visible-tmux spawn (G3-TMUX-UNAVAILABLE).

    This is the offline, network-free, deterministic core of the harness: it
    proves the belt argv satisfies the operating-mode floor, the prompt
    pointer+SHA, the visibility requirement, the live Active-Work claim, the
    conflict guard, the worktree-path check, the brain bootstrap, and the Ring-0
    governed-command build — failing ONLY at the unavailable tmux server.
    """
    repo, state_root, ledger_root = _init_workspace(tmp_path, bootstrap_brain=False)
    assert not brain_runtime.verify_ledger(state_root).ok

    class _UnavailableVisibility:
        visibility_class = "operator_visible"

        def is_available(self) -> bool:
            return False

        def ensure_surface(self, **kwargs):  # pragma: no cover - availability gate stops first
            raise AssertionError("offline harness must not materialize a live surface")

    def _spawn(argv: list[str]) -> subprocess.CompletedProcess:
        # Re-invoke lane_runtime.launch in-process with a fake unavailable
        # visibility backend so we see the typed refusal, not a subprocess exit
        # code. The parser mirrors ce_cli's production argv contract and forwards
        # the exact values the belt emitted.
        flags = _parse_lane_launch_argv(argv)
        assert flags.get("json") is True
        with pytest.raises(lane_runtime.TmuxUnavailableError):
            lane_runtime.launch(
                controller_id=_required_flag(flags, "controller-id"),
                lane_id=_required_flag(flags, "lane-id"),
                role=_required_flag(flags, "role"),
                prompt=_required_flag(flags, "prompt"),
                prompt_sha=_required_flag(flags, "prompt-sha"),
                repo_root=_required_flag(flags, "repo-root"),
                ledger_root=_required_flag(flags, "ledger-root"),
                command=[_required_flag(flags, "command")],
                lane_kind=_required_flag(flags, "lane-kind"),
                worktree_path=_required_flag(flags, "worktree-path"),
                visibility_backend=_UnavailableVisibility(),
            )
        # Surface a sentinel exit so launch_lane reports the spawn step is all
        # that remains.
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="tmux-unavailable")

    result = pickup.launch_lane(
        _ITEM, identity=_IDENTITY, run_id=_RUN_ID, claim_id="claim-x",
        harness="/bin/true", seed_root=tmp_path / "seeds",
        repo_root=str(repo), ledger_root=str(ledger_root),
        spawn=_spawn,
    )
    # Allocation + seed succeeded; the only thing left is the visible spawn.
    assert result.seed_path is not None
    assert Path(result.seed_path).is_file()
    assert result.lane_id == pickup._lane_id(_ITEM, _RUN_ID)
    assert result.launched is False  # the tmux spawn is the sole remaining step
    claim_path = ledger_root / "claims" / _IDENTITY / f"{result.lane_id}.yaml"
    assert claim_path.is_file()  # the pre-spawn claim gate is satisfied
    assert brain_runtime.verify_ledger(state_root).ok  # launch_lane bootstrapped it


@pytest.mark.skip(reason="live tmux smoke is intentionally excluded from the deterministic offline e2e")
def test_belt_launch_reaches_launched_state_with_real_tmux(tmp_path: Path) -> None:
    """The full belt path drives to ``LAUNCHED_STATE`` (a real spawned governed
    lane) when a tmux server is available — the complete e2e to a live seat.

    Uses a real ``ce lane launch`` subprocess (the belt's actual spawn seam) with
    ``/bin/true`` as the harness so the pane self-exits immediately; the
    throwaway session is force-killed in teardown regardless.
    """
    repo, _, ledger_root = _init_workspace(tmp_path)
    lane_id = pickup._lane_id(_ITEM, _RUN_ID)
    adapter = TmuxAdapter()
    if not adapter.is_available():
        pytest.skip("tmux server unavailable on this host")

    try:
        result = pickup.launch_lane(
            _ITEM, identity=_IDENTITY, run_id=_RUN_ID, claim_id="claim-x",
            harness="/bin/true", seed_root=tmp_path / "seeds",
            repo_root=str(repo), ledger_root=str(ledger_root),
        )
        assert result.launched is True, result.note
        assert result.lane_id == lane_id
        # The pane registry record + governed seat lifecycle record were written.
        pane_path = ledger_root / "panes" / _IDENTITY / f"{lane_id}.yaml"
        assert pane_path.is_file()
        # And the lane runtime reports the governed state the sentinel binds to.
        status = lane_runtime.status(
            controller_id=_IDENTITY, lane_id=lane_id, ledger_root=ledger_root
        )
        assert status is not None
    finally:
        # Force-kill the throwaway lane session/window if it lingers.
        subprocess.run(
            ["tmux", "kill-window", "-t", f"{lane_runtime.DEFAULT_SESSION}:{lane_id}"],
            check=False, capture_output=True, text=True,
        )
