"""Integration tests for ``creator_engine_validator hook-check``.

Exercises the CLI seam a future Claude ``command``-type hook (CC-G-C)
will invoke: JSON-in (``--stdin`` / ``--input-json``), JSON-decision-out,
exit ``0`` for evaluated allow/deny/block decisions, non-zero only for
invalid input. No Claude launch, no pane spawn, no ``.claude/**`` writes.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from creator_engine_validator import brain_bootstrap
from creator_engine_validator.cli import main
pytestmark = pytest.mark.slow



REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = REPO_ROOT / "examples"


def _run(argv, capsys, stdin_text=None, monkeypatch=None):
    if stdin_text is not None:
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_text))
    code = main(argv)
    out = capsys.readouterr().out
    return code, out


def _pin_bootstrap_seat_class(monkeypatch, tmp_path: Path, seat_class: str) -> None:
    payload = {
        "kind": brain_bootstrap.BOOTSTRAP_KIND,
        "schema_version": brain_bootstrap.BOOTSTRAP_SCHEMA_VERSION,
        "context": {
            "role": "implementer",
            "seat_class": seat_class,
            "scope": {"seat_class": seat_class},
        },
        "knowledge_ssot": {
            "ledger_path": ".ce/state/brain/assertions.yaml",
            "record_count": 0,
            "active_count": 0,
            "scope_relevant_count": 0,
            "head_content_hash": None,
            "assertions": [],
        },
    }
    ref = tmp_path / f"brain-bootstrap-{seat_class}.json"
    digest = brain_bootstrap.write_payload(ref, payload)
    monkeypatch.setenv(brain_bootstrap.BOOTSTRAP_REF_ENV, str(ref))
    monkeypatch.setenv(brain_bootstrap.BOOTSTRAP_SHA256_ENV, digest)


def _write_worker_record(root: Path, worker_id: str) -> Path:
    import yaml

    from creator_engine_validator import worker_spawn

    role = "implementer"
    surface_ref = worker_spawn.WORKER_TIER_ROLE_SURFACE_REFS.get(role)
    if surface_ref is not None:
        surface_path = root / surface_ref
        surface_path.parent.mkdir(parents=True, exist_ok=True)
        surface_path.write_text(f"# {role}\n", encoding="utf-8")

    path = root / ".ce" / "state" / "workers" / worker_id / "worker.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "kind": "ce-worker-spawn-record",
        "schema_version": "1",
        "worker_id": worker_id,
        "role": role,
        "lane_kind": "implementation",
        "harness": "claude",
        "scope_id": "ce-ops#163",
        "parent_id": "ce-dev-4",
        "worktree_path": str(root),
        "prompt": {"kind": "brief", "ref": "inline-brief", "sha256": "a" * 64},
        "depth": 1,
        "max_depth": 3,
        "record_path": str(path),
        "launch_command": ["ce", "launch"],
        "launch_command_sha256": "b" * 64,
        "scrubbed_env_names": [],
        "child_env_names": [],
        "dry_run": False,
        "launch_state": "launched",
        "seat_refs": {"seat_lifecycle_state": "active"},
        "governed_worker_contract": worker_spawn.governed_worker_contract(role=role, max_depth=3),
    }
    path.write_text(yaml.safe_dump(record, sort_keys=True), encoding="utf-8")
    return path


def test_hook_check_stdin_governed_out_of_manifest_advisory(capsys, monkeypatch):
    # G-i: author-time path-manifest enforcement is ADVISORY under governed
    # posture (scope is enforced post-hoc by the CI path_manifest_fidelity
    # PR-diff gate). Secret/mechanic denies stay hard (see the canaries below).
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "README.md"},
        "ce": {"posture": "governed", "manifest_paths": ["schemas/x.yaml"]},
    }
    code, out = _run(["hook-check", "--stdin"], capsys, json.dumps(event), monkeypatch)
    assert code == 0  # advisory-allow is a decision, not a CLI crash
    payload = json.loads(out)
    assert payload["decision"] == "allow"
    assert payload["advisory"] is True
    assert payload["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert payload["posture"] == "governed"


def test_hook_check_cli_allows_foreman_implementation_with_worker_record_env(capsys, tmp_path, monkeypatch):
    _write_worker_record(tmp_path, "worker-from-env")
    monkeypatch.setenv("CE_WORKER_ID", "worker-from-env")
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "validators/creator_engine_validator/hook_check.py"},
        "ce": {
            "posture": "governed",
            "manifest_paths": ["validators/creator_engine_validator/hook_check.py"],
            "mutation_class": "code",
            "seat_class": "foreman",
            "worker_id": "worker-from-env",
        },
    }

    code, out = _run(
        ["hook-check", "--stdin", "--posture-root", str(tmp_path)],
        capsys,
        json.dumps(event),
        monkeypatch,
    )

    assert code == 0
    payload = json.loads(out)
    assert payload["posture"] == "governed"
    assert payload["decision"] == "allow"
    assert payload["advisory"] is False


def test_hook_check_input_json_file(capsys, tmp_path, monkeypatch):
    _pin_bootstrap_seat_class(monkeypatch, tmp_path, "worker")
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "schemas/x.yaml"},
        "ce": {"posture": "governed", "manifest_paths": ["schemas/x.yaml"]},
    }
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(event), encoding="utf-8")
    code, out = _run(["hook-check", "--input-json", str(event_file)], capsys)
    assert code == 0
    payload = json.loads(out)
    assert payload["decision"] == "allow"


def test_hook_check_requires_an_input_mode(capsys):
    # Neither --stdin nor --input-json: invalid arguments -> non-zero exit.
    with pytest.raises(SystemExit) as exc:
        main(["hook-check"])
    assert exc.value.code != 0


def test_hook_check_invalid_json_exits_nonzero(capsys, monkeypatch):
    code, out = _run(["hook-check", "--stdin"], capsys, "{not json", monkeypatch)
    assert code != 0


def test_hook_check_stop_block_via_closeout_file(capsys, tmp_path, monkeypatch):
    closeout = tmp_path / "closeout.md"
    closeout.write_text("no canonical sections here", encoding="utf-8")
    event = {"hook_event_name": "Stop", "ce": {"posture": "governed"}}
    code, out = _run(
        ["hook-check", "--stdin", "--closeout-file", str(closeout)],
        capsys,
        json.dumps(event),
        monkeypatch,
    )
    assert code == 0
    payload = json.loads(out)
    assert payload["decision"] == "block"
    assert payload["hookSpecificOutput"]["hookEventName"] == "Stop"


def test_hook_check_posture_auto_examples_subdir_no_longer_governs(capsys, monkeypatch):
    # Gate B (posture-claim reachability): pointing --posture-root at a tree that
    # carries tracked examples/** claim+pane fixtures NO LONGER resolves `governed`.
    # Posture discovery is scoped to <posture_root>/.hermes/active-work-ledger (or a
    # launch-pinned --ledger-root), never the whole tree, so a fixture can never be
    # matched as a live governing claim. (Before Gate B this asserted `governed`.)
    posture_root = EXAMPLES / "well-formed/pane-registry"
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "README.md"},
        "ce": {"manifest_paths": ["schemas/x.yaml"]},
    }
    code, out = _run(
        ["hook-check", "--stdin", "--posture", "auto", "--posture-root", str(posture_root)],
        capsys,
        json.dumps(event),
        monkeypatch,
    )
    assert code == 0
    payload = json.loads(out)
    assert payload["posture"] == "ungoverned"
    assert payload["decision"] == "allow"
    assert payload["advisory"] is True


def _write_ledger_binding(ledger_root: Path, lane: str = "cli-lane", controller: str = "hermes-primary") -> None:
    """Write a live claim + cleanly-bound live tmux pane under a real ledger root."""
    claims = ledger_root / "claims" / controller
    panes = ledger_root / "panes" / controller
    claims.mkdir(parents=True, exist_ok=True)
    panes.mkdir(parents=True, exist_ok=True)
    (claims / f"{lane}.yaml").write_text(
        "kind: active-work-ledger-record\n"
        "record_type: claim\n"
        'schema_version: "1"\n'
        f"controller_id: {controller}\n"
        f"lane_id: {lane}\n"
        f'record_timestamp: "source-controlled:claims/{controller}/{lane}.yaml"\n'
        f"worktree_path: /worktrees/{lane}\n"
        f"envelope_ref: .hermes/envelopes/{lane}.md\n"
        "lease_seconds: 3600\n"
        f'claimed_at: "source-controlled:claims/{controller}/{lane}.yaml"\n'
        f'last_heartbeat_at: "source-controlled:claims/{controller}/{lane}.yaml"\n',
        encoding="utf-8",
    )
    (panes / f"{lane}.yaml").write_text(
        "kind: pane-registry-record\n"
        "record_type: pane_identity\n"
        'schema_version: "1"\n'
        f"controller_id: {controller}\n"
        f"lane_id: {lane}\n"
        f"claim_ref: claims/{controller}/{lane}.yaml\n"
        "host_id: workstation-a\n"
        f"pane_id: pane-{lane}-001\n"
        "role: implementer\n"
        "status: active\n"
        'record_timestamp: "2026-05-26T00:00:00Z"\n'
        "visibility: operator_visible\n"
        "terminal:\n"
        "  kind: tmux\n"
        "  session_id: ce\n"
        "  window_id: w\n"
        "  pane_id: '1'\n"
        'registered_at: "2026-05-26T00:00:00Z"\n'
        "last_seen_at: source-controlled:pane.yaml\n",
        encoding="utf-8",
    )


def test_hook_check_ledger_root_resolves_governed_via_real_claim(capsys, tmp_path, monkeypatch):
    # Gate B (B-1 + B-2) full CLI seam: a launch-pinned --ledger-root makes the seat's
    # REAL claim reachable from a worktree posture-root that carries NO local ledger
    # (only the examples footgun) -> governed, and the sacred push hard-deny still fires.
    real_ledger = tmp_path / "root" / ".hermes" / "active-work-ledger"
    _write_ledger_binding(real_ledger)
    wt = tmp_path / "wt"
    (wt / "examples").mkdir(parents=True)  # worktree carries tracked fixtures, no real ledger

    edit_event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "README.md"},
        "ce": {"manifest_paths": ["schemas/x.yaml"]},
    }
    code, out = _run(
        ["hook-check", "--stdin", "--posture", "auto",
         "--posture-root", str(wt), "--ledger-root", str(real_ledger)],
        capsys,
        json.dumps(edit_event),
        monkeypatch,
    )
    assert code == 0
    assert json.loads(out)["posture"] == "governed"

    push_event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "git push origin main"},
    }
    code, out = _run(
        ["hook-check", "--stdin", "--posture", "auto",
         "--posture-root", str(wt), "--ledger-root", str(real_ledger)],
        capsys,
        json.dumps(push_event),
        monkeypatch,
    )
    assert code == 0
    payload = json.loads(out)
    assert payload["posture"] == "governed"
    assert payload["decision"] == "deny"  # SACRED: governed seat push stays hard-denied


def test_hook_check_posture_auto_ungoverned_empty(capsys, tmp_path, monkeypatch):
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "README.md"},
        "ce": {"manifest_paths": ["schemas/x.yaml"]},
    }
    code, out = _run(
        ["hook-check", "--stdin", "--posture", "auto", "--posture-root", str(tmp_path)],
        capsys,
        json.dumps(event),
        monkeypatch,
    )
    assert code == 0
    payload = json.loads(out)
    assert payload["posture"] == "ungoverned"
    assert payload["decision"] == "allow"
    assert payload["advisory"] is True


def test_hook_check_manifest_doc_parsing(capsys, tmp_path, monkeypatch):
    _pin_bootstrap_seat_class(monkeypatch, tmp_path, "worker")
    handoff = EXAMPLES / "well-formed/handoffs/example-handoff.md"
    # In-manifest path from the fenced ALLOWED_PATHS block -> allow.
    in_event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "docs/example/file-a.md"},
        "ce": {"posture": "governed"},
    }
    code, out = _run(
        ["hook-check", "--stdin", "--manifest-doc", str(handoff)],
        capsys,
        json.dumps(in_event),
        monkeypatch,
    )
    assert code == 0
    assert json.loads(out)["decision"] == "allow"

    out_event = dict(in_event)
    out_event["tool_input"] = {"file_path": "docs/example/not-listed.md"}
    code, out = _run(
        ["hook-check", "--stdin", "--manifest-doc", str(handoff)],
        capsys,
        json.dumps(out_event),
        monkeypatch,
    )
    assert code == 0
    out_payload = json.loads(out)
    assert out_payload["decision"] == "allow"  # out-of-manifest is advisory (G-i)
    assert out_payload["advisory"] is True


def test_hook_check_foreman_seat_class_policy_ref_denies(capsys, tmp_path, monkeypatch):
    policy = tmp_path / "seat-class.ce.yml"
    policy.write_text(
        "kind: seat-class-policy-record\n"
        'schema_version: "1"\n'
        "policy_id: cli-foreman\n"
        f"policy_sha: {'b' * 64}\n"
        "seat_class: foreman\n"
        "default_seat_class: foreman\n"
        "recursion:\n"
        "  foreman_of_foreman_allowed: true\n"
        "  max_depth: 3\n"
        "delegation_required_mutation_classes:\n"
        "  - code\n",
        encoding="utf-8",
    )
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "validators/creator_engine_validator/hook_check.py"},
        "ce": {
            "posture": "governed",
            "manifest_paths": ["validators/creator_engine_validator/hook_check.py"],
            "mutation_class": "code",
            "seat_class_policy_ref": "seat-class.ce.yml",
        },
    }

    code, out = _run(
        ["hook-check", "--stdin", "--posture-root", str(tmp_path)],
        capsys,
        json.dumps(event),
        monkeypatch,
    )

    assert code == 0
    payload = json.loads(out)
    assert payload["decision"] == "deny"
    assert payload["advisory"] is False
    assert payload["wouldHaveDenied"] is True
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "worker delegation" in payload["reason"]


def test_hook_check_worker_seat_class_policy_ref_does_not_warn(capsys, tmp_path, monkeypatch):
    _pin_bootstrap_seat_class(monkeypatch, tmp_path, "worker")
    policy = tmp_path / "seat-class.ce.yml"
    policy.write_text(
        "kind: seat-class-policy-record\n"
        'schema_version: "1"\n'
        "policy_id: cli-worker\n"
        f"policy_sha: {'c' * 64}\n"
        "seat_class: worker\n"
        "default_seat_class: foreman\n"
        "recursion:\n"
        "  foreman_of_foreman_allowed: true\n"
        "  max_depth: 3\n"
        "delegation_required_mutation_classes:\n"
        "  - code\n",
        encoding="utf-8",
    )
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "validators/creator_engine_validator/hook_check.py"},
        "ce": {
            "posture": "governed",
            "manifest_paths": ["validators/creator_engine_validator/hook_check.py"],
            "mutation_class": "code",
            "seat_class_policy_ref": "seat-class.ce.yml",
        },
    }

    code, out = _run(
        ["hook-check", "--stdin", "--posture-root", str(tmp_path)],
        capsys,
        json.dumps(event),
        monkeypatch,
    )

    assert code == 0
    payload = json.loads(out)
    assert payload["decision"] == "allow"
    assert payload["advisory"] is False
    assert payload["wouldHaveDenied"] is False


def test_hook_check_launch_pinned_brain_bootstrap_seat_class_overrides_event(capsys, tmp_path, monkeypatch):
    _pin_bootstrap_seat_class(monkeypatch, tmp_path, "worker")
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "validators/creator_engine_validator/hook_check.py"},
        "ce": {
            "posture": "governed",
            "manifest_paths": ["validators/creator_engine_validator/hook_check.py"],
            "mutation_class": "code",
            "seat_class": "foreman",
        },
    }

    code, out = _run(["hook-check", "--stdin"], capsys, json.dumps(event), monkeypatch)

    assert code == 0
    payload = json.loads(out)
    assert payload["decision"] == "allow"
    assert payload["advisory"] is False
    assert payload["wouldHaveDenied"] is False


def test_hook_check_missing_brain_bootstrap_denies_event_worker_seat_class(capsys, monkeypatch):
    monkeypatch.delenv(brain_bootstrap.BOOTSTRAP_REF_ENV, raising=False)
    monkeypatch.delenv(brain_bootstrap.BOOTSTRAP_SHA256_ENV, raising=False)
    monkeypatch.delenv("CE_SEAT_CLASS", raising=False)
    monkeypatch.delenv("CE_LAUNCH_TYPE", raising=False)
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "validators/creator_engine_validator/hook_check.py"},
        "ce": {
            "posture": "governed",
            "manifest_paths": ["validators/creator_engine_validator/hook_check.py"],
            "mutation_class": "code",
            "seat_class": "worker",
        },
    }

    code, out = _run(["hook-check", "--stdin"], capsys, json.dumps(event), monkeypatch)

    assert code == 0
    payload = json.loads(out)
    assert payload["decision"] == "deny"
    assert payload["advisory"] is False
    assert payload["wouldHaveDenied"] is True
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "worker delegation" in payload["reason"]


def test_hook_check_invalid_brain_bootstrap_seat_class_denies(capsys, tmp_path, monkeypatch):
    ref = tmp_path / "brain-bootstrap.json"
    ref.write_text(
        json.dumps({"context": {"seat_class": "worker"}}, sort_keys=True),
        encoding="utf-8",
    )
    monkeypatch.setenv(brain_bootstrap.BOOTSTRAP_REF_ENV, str(ref))
    monkeypatch.setenv(brain_bootstrap.BOOTSTRAP_SHA256_ENV, "0" * 64)
    event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": "validators/creator_engine_validator/hook_check.py"},
        "ce": {
            "posture": "governed",
            "manifest_paths": ["validators/creator_engine_validator/hook_check.py"],
            "mutation_class": "code",
            "seat_class": "worker",
        },
    }

    code, out = _run(["hook-check", "--stdin"], capsys, json.dumps(event), monkeypatch)

    assert code == 0
    payload = json.loads(out)
    assert payload["decision"] == "deny"
    assert payload["advisory"] is False
    assert payload["wouldHaveDenied"] is True
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "worker delegation" in payload["reason"]


def test_hook_check_end_to_end_governed_lane(capsys, tmp_path, monkeypatch):
    # Construct a governed posture root: a live tmux pane bound to a live
    # unreleased claim whose envelope_ref points at a handoff carrying a
    # fenced ALLOWED_PATHS manifest. This is the canonical hook path.
    root = tmp_path
    claims = root / ".hermes/active-work-ledger/claims/hermes-primary"
    panes = root / ".hermes/pane-registry"
    claims.mkdir(parents=True)
    panes.mkdir(parents=True)
    (claims / "lane.yaml").write_text(
        "kind: active-work-ledger-record\n"
        "record_type: claim\n"
        'schema_version: "1"\n'
        "controller_id: hermes-primary\n"
        "lane_id: e2e-lane\n"
        'record_timestamp: "source-controlled:lane.yaml"\n'
        "worktree_path: /worktrees/e2e-lane\n"
        "envelope_ref: .hermes/handoff.md\n"
        "lease_seconds: 3600\n"
        'claimed_at: "source-controlled:lane.yaml"\n'
        'last_heartbeat_at: "source-controlled:lane.yaml"\n',
        encoding="utf-8",
    )
    (panes / "pane.yaml").write_text(
        "kind: pane-registry-record\n"
        "record_type: pane_identity\n"
        'schema_version: "1"\n'
        "controller_id: hermes-primary\n"
        "lane_id: e2e-lane\n"
        "claim_ref: ../active-work-ledger/claims/hermes-primary/lane.yaml\n"
        "host_id: workstation-a\n"
        "pane_id: pane-e2e-001\n"
        "role: implementer\n"
        "status: active\n"
        'record_timestamp: "2026-05-26T00:00:00Z"\n'
        "visibility: operator_visible\n"
        "terminal:\n"
        "  kind: tmux\n"
        "  session_id: ce\n"
        "  window_id: w\n"
        "  pane_id: '1'\n"
        'registered_at: "2026-05-26T00:00:00Z"\n'
        "last_seen_at: source-controlled:pane.yaml\n",
        encoding="utf-8",
    )
    (root / ".hermes/handoff.md").write_text(
        "# handoff\n\nALLOWED_PATHS_COUNT=1\n"
        "ALLOWED_PATHS_SHA256=" + _sha_for(["docs/keep.md"]) + "\n\n"
        "```text\ndocs/keep.md\n```\n",
        encoding="utf-8",
    )
    _pin_bootstrap_seat_class(monkeypatch, tmp_path, "worker")

    base = {"hook_event_name": "PreToolUse", "tool_name": "Edit"}

    allow_event = dict(base, tool_input={"file_path": "docs/keep.md"})
    code, out = _run(
        ["hook-check", "--stdin", "--posture-root", str(root)],
        capsys,
        json.dumps(allow_event),
        monkeypatch,
    )
    assert code == 0
    payload = json.loads(out)
    assert payload["posture"] == "governed"
    assert payload["decision"] == "allow"

    off_manifest_event = dict(base, tool_input={"file_path": "docs/other.md"})
    code, out = _run(
        ["hook-check", "--stdin", "--posture-root", str(root)],
        capsys,
        json.dumps(off_manifest_event),
        monkeypatch,
    )
    assert code == 0
    off_payload = json.loads(out)
    assert off_payload["decision"] == "allow"  # governed out-of-manifest is advisory (G-i)
    assert off_payload["advisory"] is True


def _sha_for(paths):
    import hashlib

    normalized = "\n".join(sorted(set(p for p in paths if p))) + "\n"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
