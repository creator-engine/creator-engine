"""Unit tests for the ``ce`` CLI lane command family (RV1-030/031/032).

Drives ``creator_engine_validator.ce_cli.main`` directly. tmux is replaced by
a test double via the monkeypatchable adapter factory so refusals and the
record-write path can be exercised without a real tmux process.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from creator_engine_validator import brain_runtime, ce_cli
from creator_engine_validator.tmux_adapter import TmuxPane


class FakeAdapter:
    kind = "tmux"

    def __init__(self, *, available: bool = True):
        self._available = available
        self.spawned: list[tuple[str, str, list[str], str | None]] = []

    def is_available(self) -> bool:
        return self._available

    def ensure_pane(self, *, session, window, command, cwd=None, env=None):
        self.spawned.append((session, window, list(command), cwd))
        self.last_env = dict(env) if env else None
        return TmuxPane(session_id="$1", window_id="@2", pane_id="%3", pane_tty="/dev/pts/9", pane_pid=4242)


@pytest.fixture()
def use_fake_tmux(monkeypatch):
    adapter = FakeAdapter()
    monkeypatch.setattr(ce_cli, "_make_tmux_adapter", lambda: adapter)
    return adapter


def _write_brain_ledger(state_root: Path) -> None:
    result = brain_runtime.assert_claim(
        assertion_id="brain-assertion-ce-lane-cli-0001",
        claim={"subject": "lane", "predicate": "bootstrap", "object": "ready"},
        scope="global",
        evidence_ref="validators/tests/unit/test_ce_lane_cli.py#brain-ledger",
        state_root=state_root,
        records=[],
        write=lambda _path, _text: None,
    )
    path = brain_runtime.ledger_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(brain_runtime.serialize_ledger([result.record]), encoding="utf-8")


@pytest.fixture(autouse=True)
def _seed_brain_ledger(tmp_path):
    _write_brain_ledger(tmp_path / ".ce" / "state")


def _prompt(tmp_path: Path) -> tuple[Path, str]:
    p = tmp_path / "prompt.md"
    p.write_text("gate3 prompt\n", encoding="utf-8")
    return p, hashlib.sha256(p.read_bytes()).hexdigest()


def _ledger(tmp_path: Path) -> Path:
    root = tmp_path / ".hermes" / "active-work-ledger"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _claim(ledger: Path, controller="hermes-primary", lane="gate3-lane", *, released=False) -> Path:
    record = {
        "kind": "active-work-ledger-record",
        "record_type": "claim",
        "schema_version": "1",
        "controller_id": controller,
        "lane_id": lane,
        "record_timestamp": f"source-controlled:claims/{controller}/{lane}.yaml",
        "worktree_path": "/worktrees/gate3-lane",
        "envelope_ref": "envelopes/gate3.md",
        "branch": "implementer/gate3-lane",
        "lease_seconds": 3600,
        "claimed_at": f"source-controlled:claims/{controller}/{lane}.yaml",
        "last_heartbeat_at": f"source-controlled:claims/{controller}/{lane}.yaml",
    }
    if released:
        record["released_at"] = "2026-05-25T04:05:00Z"
        record["release_reason"] = "completed"
    path = ledger / "claims" / controller / f"{lane}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    return path


def _launch_argv(tmp_path, ledger, prompt, sha, **extra):
    argv = [
        "lane", "launch",
        "--controller-id", "hermes-primary",
        "--lane-id", "gate3-lane",
        "--role", "implementer",
        "--prompt", str(prompt),
        "--prompt-sha", sha,
        "--repo-root", str(tmp_path),
        "--ledger-root", str(ledger),
    ]
    for k, v in extra.items():
        flag = "--" + k.replace("_", "-")
        if v is True:
            argv.append(flag)
        else:
            argv.extend([flag, str(v)])
    return argv


def _pane_path(ledger, controller="hermes-primary", lane="gate3-lane"):
    return ledger / "panes" / controller / f"{lane}.yaml"


# ---------------------------------------------------------------------------
# --help reachability (argparse wiring)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("argv", [
    ["--help"],
    ["lane", "--help"],
    ["lane", "launch", "--help"],
    ["lane", "status", "--help"],
    ["lane", "verify", "--help"],
    ["lane", "archive", "--help"],
])
def test_help_is_reachable(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        ce_cli.main(argv)
    assert exc.value.code == 0


# ---------------------------------------------------------------------------
# Required RED tests — launch refusals before side effects
# ---------------------------------------------------------------------------


def test_ce_lane_launch_refuses_prompt_sha_mismatch_before_side_effects(tmp_path, use_fake_tmux, capsys):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, _ = _prompt(tmp_path)
    ret = ce_cli.main(_launch_argv(tmp_path, ledger, prompt, "0" * 64))
    assert ret != 0
    assert not _pane_path(ledger).exists()
    assert use_fake_tmux.spawned == []


def test_ce_lane_launch_refuses_missing_live_claim_before_side_effects(tmp_path, use_fake_tmux):
    ledger = _ledger(tmp_path)  # no claim
    prompt, sha = _prompt(tmp_path)
    ret = ce_cli.main(_launch_argv(tmp_path, ledger, prompt, sha))
    assert ret != 0
    assert not _pane_path(ledger).exists()
    assert use_fake_tmux.spawned == []


def test_ce_lane_launch_refuses_released_claim_before_side_effects(tmp_path, use_fake_tmux):
    ledger = _ledger(tmp_path)
    _claim(ledger, released=True)
    prompt, sha = _prompt(tmp_path)
    ret = ce_cli.main(_launch_argv(tmp_path, ledger, prompt, sha))
    assert ret != 0
    assert not _pane_path(ledger).exists()
    assert use_fake_tmux.spawned == []


def test_ce_lane_launch_no_tmux_uses_headless_logged_surface(tmp_path, use_fake_tmux):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    ret = ce_cli.main(
        _launch_argv(
            tmp_path, ledger, prompt, sha,
            no_tmux=True,
            command="true",
        )
    )
    assert ret == 0
    assert use_fake_tmux.spawned == []
    record = yaml.safe_load(_pane_path(ledger).read_text(encoding="utf-8"))
    assert record["visibility"] == "operator_inspectable"
    assert record["terminal"]["kind"] == "headless"
    assert "session_id" not in record["terminal"]
    surface_ref = Path(record["terminal"]["surface_ref"])
    assert surface_ref.is_file()
    payload = json.loads(surface_ref.read_text(encoding="utf-8"))
    assert payload["stream_ref"].endswith("/stream.log")


def test_ce_lane_launch_terminal_kind_herdr_satisfies_visibility(tmp_path, use_fake_tmux, monkeypatch):
    from creator_engine_validator import visibility_backend as vb
    from creator_engine_validator.runner.herdr_session import HerdrPane

    class FakeHerdrBackend:
        terminal_kind = "herdr"
        visibility_class = vb.OPERATOR_INSPECTABLE

        def is_available(self):
            return True

        def ensure_surface(self, *, session, window, command, cwd=None, env=None, seat_dir=None):
            return vb.SurfaceHandle(
                visibility_class=self.visibility_class,
                terminal={
                    "kind": "herdr",
                    "surface_ref": "herdr-surface-918aa1506d296ee1a72da70227854392",
                    "pane_id": "pane-1",
                    "pid": 4242,
                },
                native=HerdrPane(
                    "pane-1",
                    "herdr-surface-918aa1506d296ee1a72da70227854392",
                    4242,
                ),
            )

    monkeypatch.setattr(
        ce_cli.lane_runtime,
        "get_visibility_backend",
        lambda kind: FakeHerdrBackend() if kind == "herdr" else pytest.fail(kind),
    )

    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    ret = ce_cli.main(
        _launch_argv(
            tmp_path,
            ledger,
            prompt,
            sha,
            terminal_kind="herdr",
            command="sh -c 'printf ce-herdr-live'",
        )
    )
    assert ret == 0
    assert use_fake_tmux.spawned == []
    record = yaml.safe_load(_pane_path(ledger).read_text())
    assert record["visibility"] == "operator_inspectable"
    assert record["terminal"]["kind"] == "herdr"
    assert record["terminal"]["surface_ref"] == "herdr-surface-918aa1506d296ee1a72da70227854392"
    assert "/run/ce/herdr/control.sock" not in repr(record["terminal"])


def test_ce_lane_launch_refuses_tmux_unavailable_before_pane_write(tmp_path, monkeypatch):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    monkeypatch.setattr(ce_cli, "_make_tmux_adapter", lambda: FakeAdapter(available=False))
    ret = ce_cli.main(_launch_argv(tmp_path, ledger, prompt, sha))
    assert ret != 0
    assert not _pane_path(ledger).exists()


def test_ce_lane_launch_claim_ticket_refuses_missing_brain_before_work_claim_acquire(
    tmp_path, monkeypatch, use_fake_tmux, capsys
):
    brain_runtime.ledger_path(tmp_path / ".ce" / "state").unlink()
    calls = []

    def _acquire(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("work claim acquire must not run before brain bootstrap preflight")

    monkeypatch.setattr(ce_cli.work_claims, "acquire", _acquire)
    ledger = _ledger(tmp_path)
    prompt, sha = _prompt(tmp_path)

    ret = ce_cli.main(
        _launch_argv(
            tmp_path,
            ledger,
            prompt,
            sha,
            claim_ticket="creator-engine/ce-ops#305",
        )
    )

    assert ret != 0
    assert calls == []
    assert not _pane_path(ledger).exists()
    assert use_fake_tmux.spawned == []
    assert "G3-BRAIN-BOOTSTRAP-REFUSED" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Required RED test — launch writes a pane registry record bound to the claim
# ---------------------------------------------------------------------------


def test_ce_lane_launch_writes_pane_registry_record_bound_to_live_claim(tmp_path, use_fake_tmux, capsys):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    ret = ce_cli.main(_launch_argv(tmp_path, ledger, prompt, sha))
    assert ret == 0
    pane = _pane_path(ledger)
    assert pane.is_file()
    record = yaml.safe_load(pane.read_text(encoding="utf-8"))
    assert record["claim_ref"] == "claims/hermes-primary/gate3-lane.yaml"
    assert record["terminal"]["kind"] == "tmux"
    assert record["visibility"] == "operator_visible"
    assert use_fake_tmux.spawned, "tmux pane should have been spawned"


def test_ce_lane_launch_injects_abs_ledger_root_into_pane_env(tmp_path, use_fake_tmux):
    # Gate B (B-1): every governed lane exports its ABSOLUTE Active-Work Ledger root
    # into the pane environment as CE_LEDGER_ROOT, so the in-band hook can resolve §7
    # posture from the seat's REAL claim (reachable from a worktree with no local
    # ledger) rather than the whole posture-root tree.
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    ret = ce_cli.main(_launch_argv(tmp_path, ledger, prompt, sha))
    assert ret == 0
    env = use_fake_tmux.last_env
    assert env is not None
    assert env["CE_LEDGER_ROOT"] == str(ledger.resolve())
    assert Path(env["CE_LEDGER_ROOT"]).is_absolute()


# ---------------------------------------------------------------------------
# Required RED test — status reads the live pane record
# ---------------------------------------------------------------------------


def test_ce_lane_status_reads_live_pane_record(tmp_path, use_fake_tmux, capsys):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    ce_cli.main(_launch_argv(tmp_path, ledger, prompt, sha))
    capsys.readouterr()
    ret = ce_cli.main([
        "lane", "status",
        "--controller-id", "hermes-primary",
        "--lane-id", "gate3-lane",
        "--ledger-root", str(ledger),
        "--json",
    ])
    assert ret == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["record"]["lane_id"] == "gate3-lane"
    assert payload["record"]["terminal"]["kind"] == "tmux"


def test_ce_lane_status_missing_record_exits_nonzero(tmp_path):
    ledger = _ledger(tmp_path)
    ret = ce_cli.main([
        "lane", "status",
        "--controller-id", "hermes-primary",
        "--lane-id", "absent",
        "--ledger-root", str(ledger),
    ])
    assert ret != 0


# ---------------------------------------------------------------------------
# Required RED test — verify refuses missing stop line
# ---------------------------------------------------------------------------


def test_ce_lane_verify_refuses_missing_stop_line(tmp_path, use_fake_tmux):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    ce_cli.main(_launch_argv(tmp_path, ledger, prompt, sha))
    transcript = tmp_path / "t.txt"
    transcript.write_text("no terminal line here\n", encoding="utf-8")
    ret = ce_cli.main([
        "lane", "verify",
        "--controller-id", "hermes-primary",
        "--lane-id", "gate3-lane",
        "--ledger-root", str(ledger),
        "--transcript", str(transcript),
        "--stop-line", "CE_PCO_V1_G3_GOVERNED_LANE_LAUNCH_READY_FOR_SOURCE_RATIFICATION",
    ])
    assert ret != 0


def test_ce_lane_verify_ok_with_stop_line(tmp_path, use_fake_tmux):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    ce_cli.main(_launch_argv(tmp_path, ledger, prompt, sha))
    stop = "CE_PCO_V1_G3_GOVERNED_LANE_LAUNCH_READY_FOR_SOURCE_RATIFICATION"
    transcript = tmp_path / "t.txt"
    transcript.write_text(f"work\n{stop}\n", encoding="utf-8")
    ret = ce_cli.main([
        "lane", "verify",
        "--controller-id", "hermes-primary",
        "--lane-id", "gate3-lane",
        "--ledger-root", str(ledger),
        "--transcript", str(transcript),
        "--stop-line", stop,
    ])
    assert ret == 0


# ---------------------------------------------------------------------------
# Required RED test — archive hashes transcript bytes (CLI surface)
# ---------------------------------------------------------------------------


def test_ce_lane_archive_hashes_transcript_bytes(tmp_path, capsys):
    transcript = tmp_path / "pane.txt"
    body = b"transcript bytes\nstop\n"
    transcript.write_bytes(body)
    archive_root = tmp_path / "out"  # outside repo
    ret = ce_cli.main([
        "lane", "archive",
        "--transcript", str(transcript),
        "--archive-root", str(archive_root),
        "--batch-slug", "gate3",
        "--role", "implementer",
    ])
    assert ret == 0
    out = capsys.readouterr().out
    expected = hashlib.sha256(body).hexdigest()
    assert expected in out


# ---------------------------------------------------------------------------
# G2.002.1 operating-mode runtime carriers (CLI surface)
# ---------------------------------------------------------------------------


_VALID_AUTO_TENANT_POLICY = """
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


def test_ce_lane_launch_defaults_strict_and_succeeds(tmp_path, use_fake_tmux, capsys):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    ret = ce_cli.main(_launch_argv(tmp_path, ledger, prompt, sha))
    assert ret == 0


def test_ce_lane_launch_accepts_carrier_flags(tmp_path, use_fake_tmux, capsys):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    ret = ce_cli.main(
        _launch_argv(
            tmp_path,
            ledger,
            prompt,
            sha,
            operating_mode="strict",
            autonomy_class="operator_ratified_privileged",
            lane_kind="implementation",
        )
    )
    assert ret == 0


def test_ce_lane_launch_refuses_auto_without_tenant_policy(tmp_path, use_fake_tmux, capsys):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    ret = ce_cli.main(_launch_argv(tmp_path, ledger, prompt, sha, operating_mode="auto"))
    assert ret == 1
    assert "G2-AUTO-WITHOUT-OPERATOR-POLICY" in capsys.readouterr().err


def test_ce_lane_launch_allows_auto_with_operator_ratified_tenant_policy(tmp_path, use_fake_tmux, capsys):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    policy = tmp_path / "tenant-policy.ce.yml"
    policy.write_text(_VALID_AUTO_TENANT_POLICY, encoding="utf-8")
    ret = ce_cli.main(
        _launch_argv(
            tmp_path,
            ledger,
            prompt,
            sha,
            operating_mode="auto",
            autonomy_class="operator_ratified_privileged",
            tenant_policy=str(policy),
        )
    )
    assert ret == 0


def test_ce_lane_launch_refuses_agent_ratifier_active_tenant_policy(tmp_path, use_fake_tmux, capsys):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    policy = tmp_path / "bad-policy.ce.yml"
    policy.write_text(
        _VALID_AUTO_TENANT_POLICY.replace("active_authority: none", "active_authority: privileged_governance"),
        encoding="utf-8",
    )
    ret = ce_cli.main(
        _launch_argv(tmp_path, ledger, prompt, sha, operating_mode="auto", tenant_policy=str(policy))
    )
    assert ret == 1
    assert "G2-AGENT-RATIFIER-ACTIVE" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# v3.1-G2b — `ce lane launch --json` consumption seam (the reviewer-venue bridge)
# ---------------------------------------------------------------------------
def test_ce_lane_launch_json_emits_record_and_pane_path(tmp_path, use_fake_tmux, capsys):
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    ret = ce_cli.main(_launch_argv(tmp_path, ledger, prompt, sha, json=True))
    assert ret == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pane_path"] == str(_pane_path(ledger))
    term = payload["record"]["terminal"]
    assert term == {"kind": "tmux", "session_id": "$1", "window_id": "@2",
                    "pane_id": "%3", "pane_tty": "/dev/pts/9", "pane_pid": 4242}
    assert payload["record"]["claim_ref"] == "claims/hermes-primary/gate3-lane.yaml"


def test_ce_lane_launch_human_output_is_byte_unchanged(tmp_path, use_fake_tmux, capsys):
    # The flagless human line is byte-identical to today's (the --json addition is additive).
    ledger = _ledger(tmp_path)
    _claim(ledger)
    prompt, sha = _prompt(tmp_path)
    ret = ce_cli.main(_launch_argv(tmp_path, ledger, prompt, sha))
    assert ret == 0
    out = capsys.readouterr().out
    assert out == (
        f"ce lane launch: wrote {_pane_path(ledger)} "
        f"(tmux session=$1 window=@2 pane=%3)\n"
    )
