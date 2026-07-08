"""ce-ops#197 PR-5 — ``ce onboard`` orchestrator (strict-TDD).

Exercises the six-phase composition through the injectable :class:`OnboardLegs`
so the happy path and every degradation branch run offline with mocked legs:

* happy path (all legs OK, single live controller);
* idempotent re-run (legs report already-present);
* refuse-on-unverified-install (the provenance HARD gate);
* the #212 single-controller assertion (>1 live controller refuses);
* offline degradation;
* no-tmux / no-visible-launch graceful stop-before-launch;
* already-installed-but-absent → human-action install gate;
* the §A.5 install-mode default selection;
* the --emit-manifest schema + §B.2 consequence-class correctness;
* each --json phase record carries the §B.3 audit fields.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from creator_engine_validator import ce_onboard, launch_runtime


# --- leg fakes ---------------------------------------------------------------
def _ok_legs(**overrides) -> ce_onboard.OnboardLegs:
    base = dict(
        doctor=lambda repo_root, *, require_visible_launch: ce_onboard.DoctorLegResult(
            ok=True, low_tmpdir=False, path_gap=False, detail="doctor PASS",
        ),
        install_detect=lambda repo_root, *, install_root=None: ce_onboard.InstallDetectResult(
            present=True, command="curl ... | bash", detail="present",
        ),
        verify_install=lambda install_root, *, offline: {"ok": True, "status": "verified", "reason": ""},
        fix_path=lambda: {"profile_path": "/home/u/.profile", "changed": True},
        init=lambda repo_root: {"created": [".ce/state"], "existing": []},
        brain_init=lambda state_root: {"created": True, "already_initialized": False},
        launch=lambda *, harness, repo_root, ledger_root: ce_onboard.LaunchLegResult(
            ok=True, live_controllers=1, seat_record_ref="seats/h/c.yaml", detail="launched",
        ),
    )
    base.update(overrides)
    return ce_onboard.OnboardLegs(**base)


def _config(**overrides) -> ce_onboard.OnboardConfig:
    base = dict(install_mode="skip")  # default to deterministic mode in most tests
    base.update(overrides)
    return ce_onboard.OnboardConfig(**base)


# --- install-mode selection (§A.5) -------------------------------------------
def test_default_mode_is_hybrid_when_agent_present():
    assert ce_onboard.select_install_mode(None, agent_present=True) == "hybrid"


def test_default_mode_is_guided_when_no_agent():
    assert ce_onboard.select_install_mode(None, agent_present=False) == "guided"


def test_default_mode_is_never_print():
    # The ratified flip: print is the manual fallback, NEVER the default.
    assert ce_onboard.select_install_mode(None, agent_present=True) != "print"
    assert ce_onboard.select_install_mode(None, agent_present=False) != "print"


def test_explicit_mode_overrides_selection():
    assert ce_onboard.select_install_mode("print", agent_present=True) == "print"


def test_unknown_mode_refused():
    with pytest.raises(ce_onboard.OnboardError):
        ce_onboard.select_install_mode("nonsense", agent_present=True)


def test_agent_detection_reads_env(monkeypatch):
    monkeypatch.setenv("CE_INSTALL_AGENT", "claude --print")
    assert ce_onboard.detect_agent_present(which=lambda _n: None) is True


def test_agent_detection_probes_known_binaries(monkeypatch):
    monkeypatch.delenv("CE_INSTALL_AGENT", raising=False)
    assert ce_onboard.detect_agent_present(which=lambda n: "/usr/bin/codex" if n == "codex" else None)
    assert not ce_onboard.detect_agent_present(which=lambda _n: None)


# --- happy path --------------------------------------------------------------
def test_happy_path_runs_all_phases(monkeypatch):
    monkeypatch.delenv("CE_INSTALL_AGENT", raising=False)
    result = ce_onboard.run_onboard(_config(install_mode="hybrid"), legs=_ok_legs())
    assert result.ok
    ids = [p.id for p in result.phases]
    assert ids == ["doctor", "install", "verify_install", "fix_path", "bootstrap", "launch"]
    assert all(p.status in ("ok", "skipped") for p in result.phases)
    launch = result.phases[-1]
    assert launch.status == "ok"
    assert launch.verify["live_controllers"] == 1


def test_every_phase_record_carries_audit_fields():
    # §B.3: each --json phase record carries consequence_class / reversibility /
    # decision (the governed-rail audit fields).
    result = ce_onboard.run_onboard(_config(install_mode="hybrid"), legs=_ok_legs())
    for phase in result.phases:
        d = phase.to_dict()
        assert d["consequence_class"] in {
            "read_only", "low", "medium", "high", "binding",
        }
        assert d["reversibility"] in {"reversible", "partially_irreversible", "irreversible"}
        assert d["decision"] in {"auto", "confirm", "ratified", "human_action"}


def test_emit_manifest_guides_per_user_github_app():
    manifest = ce_onboard.emit_manifest()
    app_input = next(item for item in manifest["operator_inputs"] if item["id"] == "github.app")
    assert app_input["kind"] == "own"
    assert app_input["required_for"] == "contained-seat-onboarding"
    assert "per-user GitHub App" in app_input["human_action"]
    assert "shared App" in app_input["human_action"]


# --- idempotent re-run -------------------------------------------------------
def test_idempotent_rerun_is_safe_noop():
    legs = _ok_legs(
        fix_path=lambda: {"profile_path": "/home/u/.profile", "changed": False},
        brain_init=lambda state_root: {"created": False, "already_initialized": True},
    )
    result = ce_onboard.run_onboard(_config(install_mode="hybrid"), legs=legs)
    assert result.ok
    bootstrap = next(p for p in result.phases if p.id == "bootstrap")
    assert bootstrap.data["brain"]["already_initialized"] is True


# --- refuse-on-unverified-install (HARD gate) --------------------------------
def test_refuse_on_unverified_install():
    legs = _ok_legs(
        verify_install=lambda install_root, *, offline: {
            "ok": False, "status": "tampered", "reason": "hash mismatch",
        },
    )
    result = ce_onboard.run_onboard(_config(install_mode="hybrid"), legs=legs)
    assert not result.ok
    assert result.reason == "refuse-on-unverified-install"
    # The launch leg must NOT have run.
    assert "launch" not in [p.id for p in result.phases]
    verify = next(p for p in result.phases if p.id == "verify_install")
    assert verify.status == "refused"


def test_skip_mode_bypasses_provenance_gate():
    # --install-mode skip is the explicit dev-workspace override.
    legs = _ok_legs(verify_install=lambda *a, **k: pytest.fail("verify must not run in skip mode"))
    result = ce_onboard.run_onboard(_config(install_mode="skip"), legs=legs)
    assert result.ok
    verify = next(p for p in result.phases if p.id == "verify_install")
    assert verify.status == "skipped"


# --- #212 single-controller assertion ----------------------------------------
def test_single_controller_assertion_refuses_double_spawn():
    legs = _ok_legs(
        launch=lambda *, harness, repo_root, ledger_root: ce_onboard.LaunchLegResult(
            ok=True, live_controllers=2, seat_record_ref="x", detail="launched",
        ),
    )
    result = ce_onboard.run_onboard(_config(install_mode="skip"), legs=legs)
    assert not result.ok
    assert result.reason == "single-controller-assertion-failed"
    launch = next(p for p in result.phases if p.id == "launch")
    assert launch.status == "refused"
    assert launch.verify["live_controllers"] == 2


def test_single_controller_assertion_refuses_zero_controllers():
    legs = _ok_legs(
        launch=lambda *, harness, repo_root, ledger_root: ce_onboard.LaunchLegResult(
            ok=False, live_controllers=0, seat_record_ref=None, detail="no seat",
        ),
    )
    result = ce_onboard.run_onboard(_config(install_mode="skip"), legs=legs)
    assert not result.ok
    assert result.reason == "single-controller-assertion-failed"


def test_single_controller_refusal_surfaces_exit_127_tail_event(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text(
        json.dumps({"event": "launched", "seat_id": "exec-fail--controller", "pid": 123}) + "\n"
        + json.dumps({"event": "exited", "seat_id": "exec-fail--controller", "exit_code": 127}) + "\n",
        encoding="utf-8",
    )
    legs = _ok_legs(
        launch=lambda *, harness, repo_root, ledger_root: ce_onboard.LaunchLegResult(
            ok=False,
            live_controllers=0,
            seat_record_ref=None,
            detail="no seat",
            events_ref=str(events),
            command=["claude", "--print"],
        ),
    )

    result = ce_onboard.run_onboard(_config(install_mode="skip", harness="claude"), legs=legs)

    assert not result.ok
    launch = next(p for p in result.phases if p.id == "launch")
    assert "exit_code=127" in launch.detail
    assert "command=['claude', '--print']" in launch.detail
    assert "claude CLI not found on PATH" in launch.detail
    assert launch.verify["tail_event"]["exit_code"] == 127
    assert launch.verify["tail_event"]["command"] == ["claude", "--print"]


def test_default_launch_counts_single_controller_in_default_ledger(tmp_path, monkeypatch):
    def fake_launch(*, harness, repo_root, ledger_root, tmux_adapter):
        del harness, tmux_adapter
        resolved = (
            Path(ledger_root)
            if ledger_root is not None
            else Path(repo_root) / ".ce" / "state" / "active-work-ledger"
        )
        record = resolved / "seats" / "ce-dev-1" / "ce-controller.yaml"
        record.parent.mkdir(parents=True)
        record.write_text("lifecycle:\n  state: alive\n", encoding="utf-8")
        return SimpleNamespace(seat_record_ref=str(record))

    monkeypatch.setattr(launch_runtime, "launch", fake_launch)
    result = ce_onboard.run_onboard(
        _config(install_mode="skip", repo_root=str(tmp_path)),
        legs=_ok_legs(launch=ce_onboard._default_launch_leg),
    )
    assert result.ok
    launch = next(p for p in result.phases if p.id == "launch")
    assert launch.verify["live_controllers"] == 1
    assert launch.data["seat_record_ref"].endswith(
        ".ce/state/active-work-ledger/seats/ce-dev-1/ce-controller.yaml"
    )


# --- offline degradation -----------------------------------------------------
def test_offline_degradation_notes_local_only():
    seen = {}

    def verify(install_root, *, offline):
        seen["offline"] = offline
        return {"ok": True, "status": "local", "reason": ""}

    legs = _ok_legs(verify_install=verify)
    result = ce_onboard.run_onboard(
        _config(install_mode="hybrid", offline=True), legs=legs
    )
    assert result.ok
    assert seen["offline"] is True
    verify_phase = next(p for p in result.phases if p.id == "verify_install")
    assert "offline" in verify_phase.detail


# --- no-tmux / no-visible-launch ---------------------------------------------
def test_no_visible_launch_stops_before_launch():
    legs = _ok_legs(
        doctor=lambda repo_root, *, require_visible_launch: ce_onboard.DoctorLegResult(
            ok=False, refused_clauses=["PCO-049"], detail="no tmux",
        ),
    )
    result = ce_onboard.run_onboard(_config(install_mode="skip"), legs=legs)
    assert not result.ok
    assert result.reason == "no-visible-launch"
    # Everything up to launch ran.
    ids = [p.id for p in result.phases]
    assert "bootstrap" in ids
    launch = next(p for p in result.phases if p.id == "launch")
    assert launch.status == "blocked"


def test_no_launch_flag_completes_up_to_launch():
    result = ce_onboard.run_onboard(
        _config(install_mode="skip", no_launch=True), legs=_ok_legs()
    )
    assert result.ok
    launch = next(p for p in result.phases if p.id == "launch")
    assert launch.status == "skipped"


def test_hard_doctor_refusal_stops_immediately():
    legs = _ok_legs(
        doctor=lambda repo_root, *, require_visible_launch: ce_onboard.DoctorLegResult(
            ok=False, refused_clauses=["RED-G-6"], detail="ungoverned",
        ),
    )
    result = ce_onboard.run_onboard(_config(install_mode="skip"), legs=legs)
    assert not result.ok
    assert [p.id for p in result.phases] == ["doctor"]
    assert result.phases[0].status == "refused"


def test_red_g4_onboard_refusal_includes_actionable_state_path_guidance():
    legs = _ok_legs(
        doctor=lambda repo_root, *, require_visible_launch: ce_onboard.DoctorLegResult(
            ok=False, refused_clauses=["RED-G-4"], detail="ungoverned state path",
        ),
    )
    result = ce_onboard.run_onboard(
        _config(install_mode="skip", repo_root="/tmp/user-repo"), legs=legs
    )

    assert not result.ok
    doctor = result.phases[0]
    assert doctor.status == "refused"
    assert doctor.verify["refused_clauses"] == ["RED-G-4"]
    assert ".ce/state/" in doctor.data["guidance"]
    assert ".hermes/" not in doctor.data["guidance"]
    assert ".gitignore" not in doctor.data["guidance"]
    assert "ce init --repo-root /tmp/user-repo" in doctor.data["guidance"]
    assert "ce onboard --repo-root /tmp/user-repo" in doctor.data["guidance"]
    assert all("Add `.hermes/` to .gitignore" not in step for step in doctor.data["next_steps"])


def test_onboard_succeeds_with_ce_state_and_no_hermes_gitignore_entry(tmp_path: Path):
    (tmp_path / ".ce" / "state").mkdir(parents=True)
    legs = _ok_legs(
        doctor=lambda repo_root, *, require_visible_launch: ce_onboard.DoctorLegResult(
            ok=False, refused_clauses=["RED-G-4"], detail="legacy state path",
        ),
    )

    result = ce_onboard.run_onboard(
        _config(install_mode="skip", no_launch=True, repo_root=str(tmp_path)),
        legs=legs,
    )

    assert result.ok
    doctor = result.phases[0]
    assert doctor.status == "ok"
    assert doctor.verify["refused_clauses"] == []
    assert doctor.verify["legacy_state_clause_advisory"] is True
    assert ".hermes/" not in json.dumps(result.to_dict())


def test_legacy_hermes_directory_emits_advisory_not_refusal(tmp_path: Path):
    (tmp_path / ".ce" / "state").mkdir(parents=True)
    (tmp_path / ".hermes").mkdir()
    (tmp_path / ".gitignore").write_text(".hermes/\n", encoding="utf-8")

    result = ce_onboard.run_onboard(
        _config(install_mode="skip", no_launch=True, repo_root=str(tmp_path)),
        legs=_ok_legs(),
    )

    assert result.ok
    doctor = result.phases[0]
    assert doctor.status == "ok"
    assert doctor.data["advisories"]
    assert ".hermes/" in doctor.data["advisories"][0]


def test_user_project_onboard_not_blocked_by_packaging_clause(tmp_path: Path, monkeypatch):
    def git(args):
        import subprocess

        return subprocess.run(
            ["git", *args],
            cwd=str(tmp_path),
            check=True,
            capture_output=True,
            text=True,
        )

    monkeypatch.delenv("CE_INSTALL_AGENT", raising=False)
    git(["init", "--initial-branch=main"])
    (tmp_path / ".gitignore").write_text(".hermes/\n", encoding="utf-8")
    (tmp_path / ".ce" / "state").mkdir(parents=True)
    legs = _ok_legs(doctor=ce_onboard._default_doctor_leg)

    result = ce_onboard.run_onboard(
        _config(
            install_mode="skip",
            no_fix_path=True,
            no_launch=True,
            repo_root=str(tmp_path),
            state_root=str(tmp_path / ".ce" / "state"),
        ),
        legs=legs,
    )

    assert result.ok
    doctor = result.phases[0]
    assert doctor.id == "doctor"
    assert doctor.status == "ok"
    assert "RED-G-6" not in doctor.verify["refused_clauses"]


# --- install absent → human action -------------------------------------------
def test_install_absent_yields_human_action_gate():
    legs = _ok_legs(
        install_detect=lambda repo_root, *, install_root=None: ce_onboard.InstallDetectResult(
            present=False, command="curl ... | bash", detail="absent",
        ),
    )
    result = ce_onboard.run_onboard(_config(install_mode="guided"), legs=legs)
    assert not result.ok
    install = next(p for p in result.phases if p.id == "install")
    assert install.status == "human_action"
    assert install.decision == "human_action"
    assert install.data["command"] == "curl ... | bash"


def test_empty_install_root_uses_human_action_path_not_verify_refusal(tmp_path):
    empty_install_root = tmp_path / "empty-install"
    empty_install_root.mkdir()
    legs = _ok_legs(
        install_detect=ce_onboard._default_install_detect_leg,
        verify_install=lambda *a, **k: pytest.fail("verify must not run when install is absent"),
    )
    result = ce_onboard.run_onboard(
        _config(install_mode="guided", install_root=str(empty_install_root)),
        legs=legs,
    )
    assert not result.ok
    assert result.reason == "install required before onboard can continue"
    assert [p.id for p in result.phases] == ["doctor", "install"]
    install = result.phases[-1]
    assert install.status == "human_action"
    assert install.data["present"] is False
    assert "missing_install_state" not in json.dumps(result.to_dict())


def test_no_fix_path_skips_profile_block():
    result = ce_onboard.run_onboard(
        _config(install_mode="skip", no_fix_path=True), legs=_ok_legs()
    )
    fix = next(p for p in result.phases if p.id == "fix_path")
    assert fix.status == "skipped"


# --- emit-manifest (§A.1 + §B.2 classification) ------------------------------
def test_emit_manifest_schema_and_phase_ids():
    manifest = ce_onboard.emit_manifest()
    assert manifest["schema"] == "ce.onboard.manifest/v1"
    ids = [p["id"] for p in manifest["phases"]]
    assert ids == ["doctor", "install", "verify_install", "fix_path", "bootstrap", "launch"]
    for phase in manifest["phases"]:
        assert set(phase) == {
            "id", "action", "blast_radius", "consequence_class", "reversibility", "decision",
        }


def test_emit_manifest_consequence_classes_match_design():
    # The §B.2 table is the policy ground-truth; assert each phase's class.
    by_id = {p["id"]: p for p in ce_onboard.emit_manifest()["phases"]}
    assert by_id["doctor"]["consequence_class"] == "read_only"
    assert by_id["verify_install"]["consequence_class"] == "read_only"
    assert by_id["install"]["consequence_class"] == "low"
    assert by_id["fix_path"]["consequence_class"] == "low"
    assert by_id["bootstrap"]["consequence_class"] == "low"
    assert by_id["launch"]["consequence_class"] == "medium"
    # All the autonomous, reversible, user-scoped steps default to auto.
    for pid in ("doctor", "install", "verify_install", "fix_path", "bootstrap", "launch"):
        assert by_id[pid]["decision"] == "auto"
        assert by_id[pid]["reversibility"] == "reversible"


def test_emit_manifest_lists_full_taxonomy():
    manifest = ce_onboard.emit_manifest()
    assert manifest["consequence_classes"] == [
        "read_only", "low", "medium", "high", "binding",
    ]
    assert manifest["decisions"] == ["auto", "confirm", "ratified", "human_action"]


# --- result JSON is round-trippable ------------------------------------------
def test_result_to_dict_is_json_serializable():
    result = ce_onboard.run_onboard(_config(install_mode="hybrid"), legs=_ok_legs())
    blob = json.dumps(result.to_dict())
    parsed = json.loads(blob)
    assert parsed["install_mode"] == "hybrid"
    assert parsed["ok"] is True
    assert all("consequence_class" in p for p in parsed["phases"])


def test_unexpected_bootstrap_exception_yields_bounded_json_refusal():
    def boom(_state_root):
        raise RuntimeError("corrupt brain ledger")

    result = ce_onboard.run_onboard(
        _config(install_mode="skip"),
        legs=_ok_legs(brain_init=boom),
    )
    assert not result.ok
    assert result.reason == "CE-ONBOARD-BOOTSTRAP-FAILED"
    bootstrap = result.phases[-1]
    assert bootstrap.id == "bootstrap"
    assert bootstrap.status == "refused"
    assert bootstrap.verify["exception_class"] == "RuntimeError"
    payload = json.dumps(result.to_dict())
    assert "corrupt brain ledger" in payload
    assert "Traceback" not in payload
