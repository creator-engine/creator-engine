"""Unit tests for the thin egress-broker CLI (``tools/egress-broker/ce_egress_broker.py``).

The CLI is a deterministic shell over ``orchestrator.courier``: parse ``--seat/--repo-path/
--branch/--config`` (+ ``--apply``), load the config, build the seat's openssl signer, run the
courier, and map the outcome to an exit code — ``0`` allow, non-zero on a fail-closed refusal or
a config error. ``main`` takes an injectable ``courier_fn`` so these tests exercise the full CLI
surface (arg parsing, signer wiring, exit codes, output) with ZERO live git/gh/openssl.
"""

import json

import pytest

import ce_egress_broker as cli
import ce_egress_self_push_broker as self_push_cli
from egress_broker.orchestrator import BrokerResult, EgressRefused
from egress_broker.policy import Decision


def _config_file(tmp_path):
    doc = {
        "repo": "creator-engine/creator-engine",
        "installation_owner": "creator-engine",
        "audit_log": str(tmp_path / "audit.jsonl"),
        "policy": {
            "base_branch": "main",
            "allowed_branch_namespaces": ["ce-"],
            "forbidden_branches": ["develop"],
            "authorized_emails": [],
            "authorized_logins": ["cedev4vps-coder"],
            "max_pushes_per_window": 10,
            "window_seconds": 3600,
        },
        "seats": {
            "dev-4": {
                "app_id": "4085526",
                "app_owner": "cedev4vps-coder",
                "pem_path": "/dev/shm/ce-dev4/ce-forge-dev4.pem",
                "installation_id": None,
            }
        },
    }
    p = tmp_path / "broker.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


def _ok_result(applied):
    return BrokerResult(
        seat_id="dev-4", branch="ce-x", head_sha="a" * 40, allowed=True, applied=applied,
        pushed=applied, pr_number=321 if applied else None, installation_id=555 if applied else None,
        decision=Decision(allowed=True, checks=()),
    )


def _args(tmp_path, *extra):
    return ["--seat", "dev-4", "--repo-path", "/seat/ws", "--branch", "ce-x",
            "--config", str(_config_file(tmp_path)), *extra]


def test_dry_run_returns_zero_and_does_not_request_apply(tmp_path, capsys):
    seen = {}

    def fake_courier(seat_id, repo_path, branch, **kw):
        seen.update(
            seat_id=seat_id,
            branch=branch,
            apply=kw["apply"],
            declared_work_class=kw["declared_work_class"],
        )
        return _ok_result(applied=False)

    rc = cli.main(_args(tmp_path), courier_fn=fake_courier)
    assert rc == 0
    assert seen == {
        "seat_id": "dev-4",
        "branch": "ce-x",
        "apply": False,
        "declared_work_class": None,
    }  # apply defaults OFF; work class defaults to carrier discovery
    assert "ce-x" in capsys.readouterr().out


def test_declared_work_class_arg_is_threaded_to_courier(tmp_path):
    seen = {}

    def fake_courier(seat_id, repo_path, branch, **kw):
        seen["declared_work_class"] = kw["declared_work_class"]
        return _ok_result(applied=False)

    rc = cli.main(_args(tmp_path, "--declared-work-class", "story"), courier_fn=fake_courier)

    assert rc == 0
    assert seen["declared_work_class"] == "story"


def test_apply_flag_requests_apply(tmp_path):
    seen = {}

    def fake_courier(seat_id, repo_path, branch, **kw):
        seen["apply"] = kw["apply"]
        seen["signer"] = kw.get("signer")
        return _ok_result(applied=True)

    rc = cli.main(_args(tmp_path, "--apply"), courier_fn=fake_courier)
    assert rc == 0
    assert seen["apply"] is True
    assert callable(seen["signer"])  # a signer was wired for the (known) seat on apply


def test_refusal_returns_nonzero(tmp_path, capsys):
    def fake_courier(seat_id, repo_path, branch, **kw):
        raise EgressRefused("egress refused: signature is not trusted-good",
                            decision=Decision(allowed=False, checks=()))

    rc = cli.main(_args(tmp_path, "--apply"), courier_fn=fake_courier)
    assert rc != 0
    err = capsys.readouterr().err
    assert "refused" in err.lower()


def test_missing_config_returns_config_error_code(tmp_path):
    rc = cli.main(
        ["--seat", "dev-4", "--repo-path", "/x", "--branch", "ce-x", "--config", str(tmp_path / "nope.json")],
        courier_fn=lambda *a, **k: _ok_result(False),
    )
    assert rc == 3


def test_audit_log_override_replaces_config_value(tmp_path):
    seen = {}

    def fake_courier(seat_id, repo_path, branch, *, config, **kw):
        seen["audit_log"] = config.audit_log
        return _ok_result(False)

    override = str(tmp_path / "other-audit.jsonl")
    cli.main(_args(tmp_path, "--audit-log", override), courier_fn=fake_courier)
    assert seen["audit_log"] == override


def test_json_output_is_machine_readable(tmp_path, capsys):
    rc = cli.main(_args(tmp_path, "--json"), courier_fn=lambda *a, **k: _ok_result(False))
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["allowed"] is True and payload["seat_id"] == "dev-4"


def test_unknown_seat_still_runs_courier_for_the_audited_deny(tmp_path):
    # an unknown seat is refused+audited INSIDE the courier; the CLI must not pre-empt that
    called = {"n": 0}

    def fake_courier(seat_id, repo_path, branch, **kw):
        called["n"] += 1
        raise EgressRefused("seat 'dev-9' is not in the broker config")

    args = ["--seat", "dev-9", "--repo-path", "/x", "--branch", "ce-x",
            "--config", str(_config_file(tmp_path))]
    rc = cli.main(args, courier_fn=fake_courier)
    assert called["n"] == 1
    assert rc != 0


def test_self_push_broker_cli_wires_host_seams(tmp_path):
    seen = {}

    def fake_signer_factory(pem_path):
        seen["pem_path"] = pem_path
        return lambda payload: b"sig"

    def fake_serve(socket_path, **kw):
        seen.update(socket_path=socket_path, **kw)

    rc = self_push_cli.main(
        [
            "--socket", str(tmp_path / "dev-4.sock"),
            "--seat", "dev-4",
            "--host-repo-path", "/host/repo",
            "--config", str(_config_file(tmp_path)),
            "--expected-peer-uid", "1000,1001",
            "--expected-peer-gid", "2000",
            "--once",
        ],
        serve_fn=fake_serve,
        signer_factory=fake_signer_factory,
    )

    assert rc == 0
    assert seen["pem_path"] == "/dev/shm/ce-dev4/ce-forge-dev4.pem"
    assert seen["broker_seat_id"] == "dev-4"
    assert seen["host_repo_path"] == "/host/repo"
    assert seen["once"] is True
    assert seen["expected_peer_uids"] == frozenset({1000, 1001})
    assert seen["expected_peer_gids"] == frozenset({2000})
    assert callable(seen["signer"])


def test_self_push_broker_cli_requires_peercred_expectations(tmp_path, capsys):
    called = {"serve": False, "signer": False}

    def fake_serve(*args, **kwargs):
        called["serve"] = True

    def fake_signer_factory(pem_path):
        called["signer"] = True
        return lambda payload: b"sig"

    rc = self_push_cli.main(
        [
            "--socket", str(tmp_path / "dev-4.sock"),
            "--seat", "dev-4",
            "--host-repo-path", "/host/repo",
            "--config", str(_config_file(tmp_path)),
            "--once",
        ],
        serve_fn=fake_serve,
        signer_factory=fake_signer_factory,
    )

    assert rc == self_push_cli.EXIT_CONFIG_ERROR
    assert called == {"serve": False, "signer": False}
    assert "--expected-peer-uid" in capsys.readouterr().err


def test_self_push_broker_cli_config_error_and_runtime_error_codes(tmp_path, capsys):
    rc = self_push_cli.main(
        [
            "--socket", str(tmp_path / "dev-4.sock"),
            "--seat", "dev-4",
            "--host-repo-path", "/host/repo",
            "--config", str(tmp_path / "missing.json"),
            "--expected-peer-uid", "1000",
            "--expected-peer-gid", "1000",
        ],
        serve_fn=lambda *a, **k: None,
        signer_factory=lambda pem: (lambda payload: b"sig"),
    )
    assert rc == self_push_cli.EXIT_CONFIG_ERROR

    secret = "ghs_SHOULD_NOT_LEAK_0123456789"

    def leaking_serve(*args, **kwargs):
        raise RuntimeError(f"transport failed with {secret}")

    rc = self_push_cli.main(
        [
            "--socket", str(tmp_path / "dev-4.sock"),
            "--seat", "dev-4",
            "--host-repo-path", "/host/repo",
            "--config", str(_config_file(tmp_path)),
            "--expected-peer-uid", "1000",
            "--expected-peer-gid", "1000",
        ],
        serve_fn=leaking_serve,
        signer_factory=lambda pem: (lambda payload: b"sig"),
    )

    assert rc == self_push_cli.EXIT_RUNTIME_ERROR
    err = capsys.readouterr().err
    assert "RuntimeError" in err
    assert secret not in err
