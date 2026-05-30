"""Unit tests for the Gate 3 governed lane-launch runtime (RV1-030/031/032).

These exercise ``lane_runtime`` directly with a tmux test double. The full
CLI surface and a real-tmux launch are covered by the CLI / integration
suites. No production worktree, ledger, or tmux session is mutated; all
state lives under pytest ``tmp_path``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import lane_runtime
from creator_engine_validator.checks.pane_registry import validate_pane_registry_record
from creator_engine_validator.tmux_adapter import TmuxPane


# ---------------------------------------------------------------------------
# Test doubles + fixtures
# ---------------------------------------------------------------------------


class FakeAdapter:
    """In-memory tmux adapter double: records spawns, never touches tmux."""

    kind = "tmux"

    def __init__(self, *, available: bool = True):
        self._available = available
        self.spawned: list[tuple[str, str, list[str]]] = []

    def is_available(self) -> bool:
        return self._available

    def ensure_pane(self, *, session, window, command, cwd=None):
        self.spawned.append((session, window, list(command)))
        self.last_cwd = cwd
        return TmuxPane(
            session_id="$1",
            window_id="@2",
            pane_id="%3",
            pane_tty="/dev/pts/9",
            pane_pid=4242,
            pane_cwd=(str(cwd) if cwd else None),
        )


def _write_prompt(tmp_path: Path, text: str = "governed gate prompt body\n") -> tuple[Path, str]:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(text, encoding="utf-8")
    sha = hashlib.sha256(prompt.read_bytes()).hexdigest()
    return prompt, sha


def _ledger_root(tmp_path: Path) -> Path:
    root = tmp_path / ".hermes" / "active-work-ledger"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_claim(
    ledger_root: Path,
    controller_id: str,
    lane_id: str,
    *,
    worktree_path: str = "/worktrees/gate3-lane",
    branch: str = "implementer/gate3-lane",
    envelope_ref: str = "envelopes/gate3.md",
    released: bool = False,
) -> Path:
    record = {
        "kind": "active-work-ledger-record",
        "record_type": "claim",
        "schema_version": "1",
        "controller_id": controller_id,
        "lane_id": lane_id,
        "record_timestamp": f"source-controlled:claims/{controller_id}/{lane_id}.yaml",
        "worktree_path": worktree_path,
        "envelope_ref": envelope_ref,
        "branch": branch,
        "lease_seconds": 3600,
        "claimed_at": f"source-controlled:claims/{controller_id}/{lane_id}.yaml",
        "last_heartbeat_at": f"source-controlled:claims/{controller_id}/{lane_id}.yaml",
    }
    if released:
        record["released_at"] = "2026-05-25T04:05:00Z"
        record["release_reason"] = "completed"
    path = ledger_root / "claims" / controller_id / f"{lane_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    return path


def _launch(tmp_path, **overrides):
    prompt, sha = overrides.pop("prompt_and_sha", _write_prompt(tmp_path))
    ledger = overrides.pop("ledger_root", _ledger_root(tmp_path))
    kwargs = dict(
        controller_id="hermes-primary",
        lane_id="gate3-lane",
        role="implementer",
        prompt=prompt,
        prompt_sha=sha,
        repo_root=tmp_path,
        ledger_root=ledger,
        tmux_adapter=FakeAdapter(),
    )
    kwargs.update(overrides)
    return lane_runtime.launch(**kwargs)


# ---------------------------------------------------------------------------
# Success path: pane record bound to a live claim
# ---------------------------------------------------------------------------


def test_launch_writes_pane_record_bound_to_live_claim(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    result = _launch(tmp_path, ledger_root=ledger)

    pane_path = ledger / "panes" / "hermes-primary" / "gate3-lane.yaml"
    assert pane_path.is_file()
    assert result.pane_path == pane_path
    record = yaml.safe_load(pane_path.read_text(encoding="utf-8"))
    assert record["kind"] == "pane-registry-record"
    assert record["controller_id"] == "hermes-primary"
    assert record["lane_id"] == "gate3-lane"
    assert record["role"] == "implementer"
    assert record["visibility"] == "operator_visible"
    assert record["terminal"]["kind"] == "tmux"
    assert record["terminal"]["session_id"] == "$1"
    assert record["terminal"]["window_id"] == "@2"
    assert record["terminal"]["pane_id"] == "%3"
    # bound to the claim
    assert record["claim_ref"] == "claims/hermes-primary/gate3-lane.yaml"
    assert record["worktree_path"] == "/worktrees/gate3-lane"
    assert record["branch"] == "implementer/gate3-lane"
    assert record["envelope_ref"] == "envelopes/gate3.md"


def test_written_pane_record_passes_pane_registry_schema(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    result = _launch(tmp_path, ledger_root=ledger)
    errors = validate_pane_registry_record(result.record, result.pane_path)
    assert errors == [], [e.format() for e in errors]


def test_no_tmp_artifact_left_after_pane_write(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    _launch(tmp_path, ledger_root=ledger)
    leftover = list((ledger / "panes").rglob("*.tmp.*"))
    assert leftover == []


# ---------------------------------------------------------------------------
# Refusals BEFORE side effects (no pane file, no tmux spawn)
# ---------------------------------------------------------------------------


def _assert_no_pane(ledger: Path, controller="hermes-primary", lane="gate3-lane"):
    assert not (ledger / "panes" / controller / f"{lane}.yaml").exists()


def test_launch_refuses_prompt_sha_mismatch_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    prompt, _ = _write_prompt(tmp_path)
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.PromptShaMismatch):
        _launch(
            tmp_path,
            ledger_root=ledger,
            prompt_and_sha=(prompt, "0" * 64),
            tmux_adapter=adapter,
        )
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_launch_refuses_missing_prompt_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.PromptMissing):
        _launch(
            tmp_path,
            ledger_root=ledger,
            prompt_and_sha=(tmp_path / "does-not-exist.md", "0" * 64),
            tmux_adapter=adapter,
        )
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_launch_refuses_missing_live_claim_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)  # no claim written
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.ClaimMissing):
        _launch(tmp_path, ledger_root=ledger, tmux_adapter=adapter)
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_launch_refuses_released_claim_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane", released=True)
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.ClaimReleased):
        _launch(tmp_path, ledger_root=ledger, tmux_adapter=adapter)
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_launch_refuses_controller_lane_mismatch_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    # claim file path matches lane but records a different lane_id internally
    path = ledger / "claims" / "hermes-primary" / "gate3-lane.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "kind": "active-work-ledger-record",
        "record_type": "claim",
        "schema_version": "1",
        "controller_id": "hermes-primary",
        "lane_id": "some-other-lane",
        "record_timestamp": "2026-05-25T04:00:00Z",
        "worktree_path": "/worktrees/x",
        "envelope_ref": "none",
        "lease_seconds": 3600,
        "claimed_at": "2026-05-25T04:00:00Z",
        "last_heartbeat_at": "2026-05-25T04:00:00Z",
    }
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.ClaimMismatch):
        _launch(tmp_path, ledger_root=ledger, tmux_adapter=adapter)
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_launch_refuses_headless_for_visibility_required_role(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.VisibilityRefused):
        _launch(tmp_path, ledger_root=ledger, terminal_kind="headless", tmux_adapter=adapter)
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_launch_refuses_tmux_unavailable_before_pane_write(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter(available=False)
    with pytest.raises(lane_runtime.TmuxUnavailableError):
        _launch(tmp_path, ledger_root=ledger, tmux_adapter=adapter)
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_launch_refuses_on_conflict_guard_before_pane_write(tmp_path):
    ledger = _ledger_root(tmp_path)
    # Two live claims, different controllers, same worktree_path -> PCO-010 conflict.
    _write_claim(ledger, "hermes-primary", "gate3-lane", worktree_path="/worktrees/shared")
    _write_claim(ledger, "other-controller", "other-lane", worktree_path="/worktrees/shared")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.ConflictGuardRefused):
        _launch(tmp_path, ledger_root=ledger, tmux_adapter=adapter)
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_launch_refuses_nondir_worktree_path_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.WorktreePathInvalid):
        _launch(
            tmp_path,
            ledger_root=ledger,
            worktree_path=str(tmp_path / "no-such-worktree"),
            tmux_adapter=adapter,
        )
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_launch_enforces_explicit_worktree_as_pane_cwd(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    wt = tmp_path / "wt"
    wt.mkdir()
    adapter = FakeAdapter()
    _launch(tmp_path, ledger_root=ledger, worktree_path=str(wt), tmux_adapter=adapter)
    assert adapter.last_cwd == str(wt)


def test_launch_refuses_handoff_sha_mismatch_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    handoff = tmp_path / "handoff.md"
    handoff.write_text("handoff body\n", encoding="utf-8")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.HandoffShaMismatch):
        _launch(
            tmp_path,
            ledger_root=ledger,
            handoff=handoff,
            handoff_sha="0" * 64,
            tmux_adapter=adapter,
        )
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_launch_does_not_launch_provider_by_default(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    _launch(tmp_path, ledger_root=ledger, tmux_adapter=adapter)
    assert adapter.spawned, "a pane should have been spawned"
    _, _, command = adapter.spawned[0]
    joined = " ".join(command).lower()
    for forbidden in ("claude", "openai", "gpt", "anthropic", "codex", "--api-key"):
        assert forbidden not in joined


# ---------------------------------------------------------------------------
# status / verify
# ---------------------------------------------------------------------------


def test_status_reads_live_pane_record(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    _launch(tmp_path, ledger_root=ledger)
    info = lane_runtime.status(
        controller_id="hermes-primary", lane_id="gate3-lane", ledger_root=ledger
    )
    assert info["record"]["status"] in lane_runtime.LIVE_STATUSES
    assert info["record"]["terminal"]["kind"] == "tmux"


def test_status_missing_record_raises(tmp_path):
    ledger = _ledger_root(tmp_path)
    with pytest.raises(lane_runtime.LaneStatusError):
        lane_runtime.status(
            controller_id="hermes-primary", lane_id="absent-lane", ledger_root=ledger
        )


def test_verify_ok_when_stop_line_present(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    _launch(tmp_path, ledger_root=ledger)
    transcript = tmp_path / "transcript.txt"
    stop = "CE_PCO_V1_G3_GOVERNED_LANE_LAUNCH_READY_FOR_SOURCE_RATIFICATION"
    transcript.write_text(f"...work...\n{stop}\n", encoding="utf-8")
    result = lane_runtime.verify(
        controller_id="hermes-primary",
        lane_id="gate3-lane",
        ledger_root=ledger,
        transcript=transcript,
        stop_line=stop,
    )
    assert result["ok"] is True


def test_verify_refuses_missing_stop_line(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    _launch(tmp_path, ledger_root=ledger)
    transcript = tmp_path / "transcript.txt"
    transcript.write_text("work happened but no terminal line\n", encoding="utf-8")
    with pytest.raises(lane_runtime.LaneVerifyError):
        lane_runtime.verify(
            controller_id="hermes-primary",
            lane_id="gate3-lane",
            ledger_root=ledger,
            transcript=transcript,
            stop_line="CE_PCO_V1_G3_GOVERNED_LANE_LAUNCH_READY_FOR_SOURCE_RATIFICATION",
        )


def test_verify_refuses_missing_transcript(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    _launch(tmp_path, ledger_root=ledger)
    with pytest.raises(lane_runtime.LaneVerifyError):
        lane_runtime.verify(
            controller_id="hermes-primary",
            lane_id="gate3-lane",
            ledger_root=ledger,
            transcript=tmp_path / "missing.txt",
            stop_line="X",
        )


def test_verify_refuses_missing_pane_record(tmp_path):
    ledger = _ledger_root(tmp_path)
    transcript = tmp_path / "transcript.txt"
    transcript.write_text("STOP\n", encoding="utf-8")
    with pytest.raises(lane_runtime.LaneVerifyError):
        lane_runtime.verify(
            controller_id="hermes-primary",
            lane_id="gate3-lane",
            ledger_root=ledger,
            transcript=transcript,
            stop_line="STOP",
        )


# ---------------------------------------------------------------------------
# CC-G-D — Ring 0 Claude refusal + governed command in `ce lane launch`
# ---------------------------------------------------------------------------


def test_lane_launch_refuses_claude_skip_perms_without_pack(tmp_path, monkeypatch):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    monkeypatch.setattr(lane_runtime, "_confirm_pack", lambda repo_root: False)
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.ClaudeLaunchRefused) as exc:
        _launch(
            tmp_path,
            ledger_root=ledger,
            command=["claude", "--dangerously-skip-permissions"],
            tmux_adapter=adapter,
        )
    assert exc.value.code == "G3-CLAUDE-REFUSED"
    assert "CC-D-6" in str(exc.value)
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_lane_launch_refuses_claude_bare_even_with_pack(tmp_path, monkeypatch):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    monkeypatch.setattr(lane_runtime, "_confirm_pack", lambda repo_root: True)
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.ClaudeLaunchRefused):
        _launch(tmp_path, ledger_root=ledger, command=["claude", "--bare"], tmux_adapter=adapter)
    _assert_no_pane(ledger)
    assert adapter.spawned == []


def test_lane_launch_pins_governed_command_for_claude(tmp_path, monkeypatch):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    monkeypatch.setattr(lane_runtime, "_confirm_pack", lambda repo_root: True)
    adapter = FakeAdapter()
    result = _launch(
        tmp_path,
        ledger_root=ledger,
        command=["claude", "--model", "claude-opus-4-7"],
        tmux_adapter=adapter,
    )
    (_sess, _win, cmd) = adapter.spawned[-1]
    assert cmd[0] == "claude"
    assert "--setting-sources" in cmd and "project" in cmd and "--strict-mcp-config" in cmd
    assert "--model" in cmd and "claude-opus-4-7" in cmd
    # The written pane record stays schema-clean (no extra CC-G-D fields).
    assert validate_pane_registry_record(result.record, result.pane_path) == []


def test_lane_launch_non_claude_command_unchanged(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    _launch(
        tmp_path,
        ledger_root=ledger,
        command=["sh", "-c", "echo hi"],
        tmux_adapter=adapter,
    )
    (_sess, _win, cmd) = adapter.spawned[-1]
    assert cmd == ["sh", "-c", "echo hi"]


# ---------------------------------------------------------------------------
# CC-G-D — Task 8: closeout pointer injection + Ring 0 closeout verification
# ---------------------------------------------------------------------------


def test_launch_writes_closeout_pointer_sidecar(tmp_path, monkeypatch):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    monkeypatch.setattr(lane_runtime, "_confirm_pack", lambda repo_root: True)
    result = _launch(
        tmp_path,
        ledger_root=ledger,
        command=["claude", "--setting-sources", "project"],
        completion_report_ref="reports/cc-g-d.yaml",
        closeout_file=".hermes/x/closeout.md",
        tmux_adapter=FakeAdapter(),
    )
    # Deterministic pointers ride the result.
    assert result.claude_governance["completion_report_ref"] == "reports/cc-g-d.yaml"
    assert result.claude_governance["closeout_ref"] == ".hermes/x/closeout.md"
    # ... and are persisted to an ignored sidecar (NOT the schema-validated record).
    sidecar = lane_runtime._governance_sidecar_path(ledger, "hermes-primary", "gate3-lane")
    assert sidecar.is_file()
    written = json.loads(sidecar.read_text(encoding="utf-8"))
    assert written["completion_report_ref"] == "reports/cc-g-d.yaml"
    # The tracked-shape pane record stays schema-clean.
    assert validate_pane_registry_record(result.record, result.pane_path) == []


def test_verify_closeout_blocks_on_missing_terminal_sections(tmp_path):
    bad = tmp_path / "closeout.md"
    bad.write_text("done.\n", encoding="utf-8")
    decision = lane_runtime.verify_closeout(
        closeout_file=str(bad), completion_report=None, posture="governed"
    )
    assert decision["decision"] == "block"  # Ring 0 fact; committed hook stays advisory


def test_verify_closeout_allows_complete_closeout(tmp_path):
    good = tmp_path / "closeout.md"
    good.write_text(
        "## Summary\nwork done\n\n"
        "## Recommended immediate next step\nratify\n\n"
        "## Exact next Source prompt pointer+SHA256\npath + sha\n",
        encoding="utf-8",
    )
    decision = lane_runtime.verify_closeout(
        closeout_file=str(good), completion_report=None, posture="governed"
    )
    assert decision.get("decision") != "block"


def test_verify_closeout_ungoverned_never_blocks(tmp_path):
    bad = tmp_path / "closeout.md"
    bad.write_text("done.\n", encoding="utf-8")
    decision = lane_runtime.verify_closeout(
        closeout_file=str(bad), completion_report=None, posture="ungoverned"
    )
    assert decision.get("decision") != "block"


# ---------------------------------------------------------------------------
# G2.002.1 operating-mode runtime carriers: ce lane launch default + refusals
# ---------------------------------------------------------------------------


def _write_tenant_policy(tmp_path, body: str, name: str = "tenant-policy.ce.yml"):
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


VALID_AUTO_TENANT_POLICY = """
operating_mode_policy:
  operating_mode: auto
  autonomy_class: operator_ratified_privileged
  default_for_migrated_v1_tenants: strict
  operator_policy_ref:
    ratified_prompt: .hermes/research/example/OPERATOR_AUTO.md
    sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
  privileged_floor:
    privileged_mutation_classes: [governance, security]
    required_ratifier_role: operator
    agent_reviewer: advisory_only
    agent_ratifier:
      status: reserved-inactive
      active_authority: none
  policy_authority:
    ratification_required_for_modes: [auto, transcendence]
    activation_record_required: true
  risk_coverage:
    required_validation_refs: [VAL-AUTO-REQUIRES-OPERATOR-POLICY]
"""

AGENT_RATIFIER_ACTIVE_TENANT_POLICY = VALID_AUTO_TENANT_POLICY.replace(
    "active_authority: none", "active_authority: privileged_governance"
)

ADVISORY_AS_RATIFIER_TENANT_POLICY = VALID_AUTO_TENANT_POLICY.replace(
    "required_ratifier_role: operator", "required_ratifier_role: agent_reviewer"
)


def test_launch_defaults_to_strict_operating_mode(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    result = _launch(tmp_path, ledger_root=ledger)
    assert result.operating_mode == "strict"


def test_launch_accepts_explicit_strict_and_carrier_fields(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    result = _launch(
        tmp_path,
        ledger_root=ledger,
        operating_mode="strict",
        autonomy_class="operator_ratified_privileged",
        lane_kind="implementation",
    )
    assert result.operating_mode == "strict"
    assert result.lane_kind == "implementation"


def test_launch_refuses_invalid_operating_mode_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.OperatingModeInvalid) as exc:
        _launch(tmp_path, ledger_root=ledger, operating_mode="permissive", tmux_adapter=adapter)
    assert exc.value.code == "G2-OPERATING-MODE-INVALID"
    assert adapter.spawned == []


def test_launch_refuses_invalid_lane_kind_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.LaneKindInvalid):
        _launch(tmp_path, ledger_root=ledger, lane_kind="deploy-and-merge", tmux_adapter=adapter)
    assert adapter.spawned == []


def test_launch_refuses_reserved_autonomy_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.ReservedAutonomyActive):
        _launch(
            tmp_path,
            ledger_root=ledger,
            autonomy_class="reserved_future_agent_ratification",
            tmux_adapter=adapter,
        )
    assert adapter.spawned == []


def test_launch_refuses_auto_without_tenant_policy_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.AutoWithoutOperatorPolicy) as exc:
        _launch(tmp_path, ledger_root=ledger, operating_mode="auto", tmux_adapter=adapter)
    assert exc.value.code == "G2-AUTO-WITHOUT-OPERATOR-POLICY"
    assert adapter.spawned == []


def test_launch_refuses_transcendence_without_tenant_policy_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.TranscendenceWithoutOperatorPolicy):
        _launch(tmp_path, ledger_root=ledger, operating_mode="transcendence", tmux_adapter=adapter)
    assert adapter.spawned == []


def test_launch_allows_auto_with_operator_ratified_tenant_policy(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    policy = _write_tenant_policy(tmp_path, VALID_AUTO_TENANT_POLICY)
    result = _launch(
        tmp_path,
        ledger_root=ledger,
        operating_mode="auto",
        autonomy_class="operator_ratified_privileged",
        tenant_policy=policy,
    )
    assert result.operating_mode == "auto"


def test_launch_refuses_agent_ratifier_active_tenant_policy_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    policy = _write_tenant_policy(tmp_path, AGENT_RATIFIER_ACTIVE_TENANT_POLICY)
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.AgentRatifierActive) as exc:
        _launch(
            tmp_path,
            ledger_root=ledger,
            operating_mode="auto",
            tenant_policy=policy,
            tmux_adapter=adapter,
        )
    assert exc.value.code == "G2-AGENT-RATIFIER-ACTIVE"
    assert adapter.spawned == []


def test_launch_refuses_advisory_role_as_ratifier_tenant_policy_before_side_effects(tmp_path):
    ledger = _ledger_root(tmp_path)
    _write_claim(ledger, "hermes-primary", "gate3-lane")
    policy = _write_tenant_policy(tmp_path, ADVISORY_AS_RATIFIER_TENANT_POLICY)
    adapter = FakeAdapter()
    with pytest.raises(lane_runtime.PrivilegedRatifierInvalid):
        _launch(
            tmp_path,
            ledger_root=ledger,
            operating_mode="auto",
            tenant_policy=policy,
            tmux_adapter=adapter,
        )
    assert adapter.spawned == []
