import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier, Lock

from creator_engine_validator.forge.scoped_token import ScopedToken, TokenRequest
from egress_broker.audit import append_audit
from egress_broker.config import load_broker_config
from egress_broker.forge_read import (
    KIND_OWN_PARITY_STATUS,
    READ_PERMISSIONS,
    ForgeReadRefused,
    cli_payload,
    handle_forge_read_request,
    parse_request,
)

_REPO = "creator-engine/creator-engine"
_SECRET = "ghs_abcdefghijklmnopqrstuvwxyz1234567890"
_T0 = datetime(2026, 7, 6, 14, 15, 0, tzinfo=timezone.utc)


def _at(dt):
    return lambda: dt


def _config(tmp_path, *, cap=10):
    return load_broker_config(
        {
            "repo": _REPO,
            "installation_owner": "creator-engine",
            "audit_log": str(tmp_path / "audit.jsonl"),
            "policy": {
                "base_branch": "main",
                "allowed_branch_namespaces": ["ce-"],
                "forbidden_branches": [],
                "authorized_emails": [],
                "authorized_logins": ["cedev4vps-coder"],
                "max_pushes_per_window": cap,
                "window_seconds": 3600,
            },
            "seats": {
                "dev-4": {
                    "app_id": "4085526",
                    "app_owner": "cedev4vps-coder",
                    "pem_path": "/dev/shm/ce-dev4/ce-forge-dev4.pem",
                    "installation_id": 475,
                }
            },
        }
    )


def _token(req: TokenRequest):
    return ScopedToken(
        run_id=req.run_id,
        repo=req.repo,
        policy_sha=req.policy_sha,
        secret_name=req.secret_name,
        permissions=tuple(sorted(req.permissions.items())),
        expires_at="2026-07-06T15:00:00Z",
        token_ref=f"{req.repo}@read",
        value=_SECRET,
    )


def _audit_records(tmp_path):
    return [
        json.loads(line)
        for line in (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def test_get_issue_mints_read_only_token_and_injects_only_child_env(tmp_path):
    minted: list[TokenRequest] = []
    spawned: list[tuple[list[str], str | None, dict[str, str]]] = []

    def mint(req):
        minted.append(req)
        return _token(req)

    def spawn(argv, input_text, env):
        spawned.append((list(argv), input_text, dict(env)))
        if argv[:4] == ["gh", "api", "-X", "GET"]:
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout=json.dumps({"number": 475, "title": "read lane"}),
                stderr="",
            )
        return subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")

    response = handle_forge_read_request(
        cli_payload("get-issue", _REPO, 475, seat_id="dev-4"),
        config=_config(tmp_path),
        signer=lambda data: b"sig",
        resolve_id_fn=lambda seat: 475,
        mint_fn=mint,
        gh_spawn=spawn,
        audit_now=_at(_T0),
    )

    assert response["ok"] is True
    assert response["body"] == {"number": 475, "title": "read lane"}
    assert response["request_path"] == f"repos/{_REPO}/issues/475"
    assert minted[0].permissions == READ_PERMISSIONS
    assert all(level == "read" for level in minted[0].permissions.values())
    assert minted[0].escalation_authority == ()

    get_argv, get_input, get_env = spawned[0]
    assert get_argv == ["gh", "api", "-X", "GET", f"repos/{_REPO}/issues/475"]
    assert get_input is None
    assert get_env["GH_TOKEN"] == _SECRET
    assert "GITHUB_TOKEN" not in get_env
    assert spawned[1][0] == ["gh", "api", "-X", "DELETE", "installation/token"]

    rendered = json.dumps(response, sort_keys=True) + (tmp_path / "audit.jsonl").read_text()
    assert _SECRET not in rendered
    audit = _audit_records(tmp_path)[0]
    assert audit["event"] == "forge_read"
    assert audit["decision"] == "allow"
    assert audit["seat_id"] == "dev-4"
    assert audit["repo"] == _REPO
    assert audit["resource"] == f"{_REPO}#475"


def test_write_shaped_read_request_refused_before_mint_or_transport_and_audited(tmp_path):
    called = {"mint": 0, "spawn": 0}
    response = handle_forge_read_request(
        {
            **cli_payload("get-issue", _REPO, 475, seat_id="dev-4"),
            "method": "POST",
            "permissions": {"contents": "write"},
            "body": "attempted mutation",
        },
        config=_config(tmp_path),
        signer=lambda data: b"sig",
        resolve_id_fn=lambda seat: 475,
        mint_fn=lambda req: called.__setitem__("mint", called["mint"] + 1),
        gh_spawn=lambda *args: called.__setitem__("spawn", called["spawn"] + 1),
        audit_now=_at(_T0),
    )

    assert response["ok"] is False
    assert "write-shaped fields" in response["error"]
    assert called == {"mint": 0, "spawn": 0}
    audit = _audit_records(tmp_path)[0]
    assert audit["decision"] == "deny"
    assert audit["seat_id"] == "dev-4"
    assert audit["repo"] == _REPO
    assert audit["resource"] == f"{_REPO}#475"


def test_rate_cap_refusal_happens_before_mint_and_emits_audit(tmp_path):
    config = _config(tmp_path, cap=1)
    append_audit(
        config.audit_log,
        {
            "event": "forge_read",
            "seat_id": "dev-4",
            "repo": _REPO,
            "resource": f"{_REPO}#1",
            "verb": "get-issue",
            "decision": "allow",
        },
        now=_at(_T0),
    )
    called = {"mint": 0, "spawn": 0}

    response = handle_forge_read_request(
        cli_payload("list-comments", _REPO, 475, seat_id="dev-4"),
        config=config,
        signer=lambda data: b"sig",
        resolve_id_fn=lambda seat: 475,
        mint_fn=lambda req: called.__setitem__("mint", called["mint"] + 1),
        gh_spawn=lambda *args: called.__setitem__("spawn", called["spawn"] + 1),
        audit_now=_at(_T0),
    )

    assert response["ok"] is False
    assert "rate cap exceeded" in response["error"]
    assert called == {"mint": 0, "spawn": 0}
    records = _audit_records(tmp_path)
    assert [r["decision"] for r in records] == ["allow", "deny"]
    assert records[-1]["verb"] == "list-comments"
    assert records[-1]["resource"] == f"{_REPO}#475"


def test_rate_cap_count_check_mint_is_serialized_at_cap_minus_one(tmp_path):
    config = _config(tmp_path, cap=2)
    append_audit(
        config.audit_log,
        {
            "event": "forge_read",
            "seat_id": "dev-4",
            "repo": _REPO,
            "resource": f"{_REPO}#1",
            "verb": "get-issue",
            "decision": "allow",
        },
        now=_at(_T0),
    )
    start = Barrier(2)
    minted: list[str] = []
    minted_lock = Lock()

    def mint(req):
        with minted_lock:
            minted.append(req.run_id)
        return _token(req)

    def gh_get(path, runner):
        time.sleep(0.15)
        return {"path": path}, {"status": 200}

    def invoke(number):
        start.wait(timeout=5)
        return handle_forge_read_request(
            cli_payload("get-issue", _REPO, number, seat_id="dev-4"),
            config=config,
            signer=lambda data: b"sig",
            resolve_id_fn=lambda seat: 475,
            mint_fn=mint,
            revoke_fn=lambda token: True,
            gh_get_fn=gh_get,
            audit_now=_at(_T0),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = (pool.submit(invoke, 475), pool.submit(invoke, 476))
        results = [future.result(timeout=5) for future in futures]

    assert [result["ok"] for result in results].count(True) == 1
    assert [result["ok"] for result in results].count(False) == 1
    assert len(minted) == 1
    refused = next(result for result in results if not result["ok"])
    assert "rate cap exceeded" in refused["error"]
    records = _audit_records(tmp_path)
    assert [r["decision"] for r in records].count("allow") == 2
    assert [r["decision"] for r in records].count("deny") == 1


def test_parse_request_accepts_only_forge_read_verbs():
    req = parse_request(cli_payload("get-pr", _REPO, 42, seat_id="dev-4"))
    assert req.verb == "get-pr"

    try:
        parse_request(cli_payload("create-comment", _REPO, 42, seat_id="dev-4"))
    except ForgeReadRefused as exc:
        assert "unsupported forge-read verb" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("create-comment should be refused")


def test_kind_own_parity_seam_is_documented_for_later_slice():
    assert "deferred" in KIND_OWN_PARITY_STATUS
    assert "kind:own" in KIND_OWN_PARITY_STATUS
