import json
import logging
import os
import socket
import subprocess
import shutil
import tempfile
import threading
from pathlib import Path

import pytest

import ce_egress_self_review_broker as broker
from creator_engine_validator.forge.scoped_token import ScopedToken, TokenRequest
from egress_broker.config import load_broker_config

_REPO = "creator-engine/creator-engine"
_HEAD = "a" * 40
_SECRET = "ghs_abcdefghijklmnopqrstuvwxyz1234567890"

# The seat in ``_config`` posts AS ``cedev4vps-coder`` (its App owner). A
# distinct PR author keeps the author≠reviewer guard satisfied for the
# happy-path tests; the guard-specific tests below override this.
_OTHER_AUTHOR = "some-other-author"


def _author(login=_OTHER_AUTHOR):
    """Injectable author resolver: no live ``gh api`` call in unit tests."""
    return lambda repo, pr_number: login


def _config():
    return load_broker_config(
        {
            "repo": _REPO,
            "installation_owner": "creator-engine",
            "audit_log": "",
            "policy": {
                "base_branch": "main",
                "allowed_branch_namespaces": ["ce-"],
                "forbidden_branches": [],
                "authorized_emails": [],
                "authorized_logins": ["cedev4vps-coder"],
                "max_pushes_per_window": 10,
                "window_seconds": 3600,
            },
            "seats": {
                "seat-reviewer-1": {
                    "app_id": "4085526",
                    "app_owner": "cedev4vps-coder",
                    "pem_path": "/dev/shm/ce-dev4/ce-forge-dev4.pem",
                    "installation_id": 123,
                }
            },
        }
    )


def _request(event="COMMENT", body="Looks reasonable."):
    return broker.SelfReviewRequest(
        seat_id="seat-reviewer-1",
        pr_number=7,
        head_sha=_HEAD,
        event=event,
        body=body,
    )


def _payload(event="COMMENT", body="Looks reasonable."):
    return {
        "seat_id": "seat-reviewer-1",
        "pr_number": 7,
        "head_sha": _HEAD,
        "event": event,
        "body": body,
    }


def _token(value=_SECRET):
    return ScopedToken(
        run_id="self-review-run",
        repo=_REPO,
        policy_sha="0" * 64,
        secret_name="forge_self_review",
        permissions=(("metadata", "read"), ("pull_requests", "write")),
        expires_at="2026-06-25T12:00:00Z",
        token_ref="creator-engine/creator-engine@self-review",
        value=value,
    )


def test_import_bootstrap_prefers_configured_stable_broker_home(tmp_path, monkeypatch):
    stable = tmp_path / "stable" / "creator-engine"
    stable_validators = stable / "validators"
    stable_egress = stable / "tools" / "egress-broker"
    seat = tmp_path / "seat" / "creator-engine"
    seat_validators = seat / "validators"
    stable_validators.mkdir(parents=True)
    stable_egress.mkdir(parents=True)
    seat_validators.mkdir(parents=True)

    monkeypatch.chdir(seat)
    monkeypatch.syspath_prepend(str(seat_validators))

    resolved = broker._resolve_broker_repo_root(
        env={broker.CE_BROKER_HOME_ENV: str(stable)},
        script_file=seat / "tools" / "egress-broker" / "ce_egress_self_review_broker.py",
    )
    egress_path, validators_path = broker._configure_stable_import_paths(resolved)

    assert resolved == stable.resolve()
    assert egress_path == stable_egress
    assert validators_path == stable_validators
    assert str(stable_validators) in os.sys.path[:2]
    assert str(stable_egress) in os.sys.path[:2]
    assert os.sys.path.index(str(stable_validators)) < os.sys.path.index(str(seat_validators))


def _reviewer_authority_envelope(**overrides):
    envelope = {
        "envelope_id": "rva-test-reviewer-approve",
        "mechanic": "pr_review",
        "pr_number": 7,
        "head_sha": _HEAD,
        "actor": "reviewer-1",
        "ratified_prompt_sha": "b" * 64,
        "emitting_role": "reviewer",
        "operating_mode": "transcendence",
        "recorded_at": "2026-06-28T00:00:00Z",
    }
    envelope.update(overrides)
    return {"reviewer_authority_envelope": envelope}


def test_comment_review_mints_and_injects_token_only_into_gh_env(caplog):
    minted: list[TokenRequest] = []
    spawned: list[tuple[list[str], str | None, dict[str, str]]] = []

    def mint(req: TokenRequest):
        minted.append(req)
        return _token()

    def spawn(argv, input_text, env):
        spawned.append((list(argv), input_text, dict(env)))
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"id": 987}), stderr="")

    caplog.set_level(logging.INFO, logger="ce-egress-self-review")
    result = broker.submit_self_review(
        _request(),
        config=_config(),
        resolve_id_fn=lambda seat: 123,
        mint_fn=mint,
        gh_spawn=spawn,
        resolve_author_fn=_author(),
    )

    assert result.to_dict() == {
        "ok": True,
        "repo": _REPO,
        "pr_number": 7,
        "head_sha": _HEAD,
        "event": "COMMENT",
        "review_id": 987,
        "applied": True,
    }
    assert minted[0].repo == _REPO
    assert minted[0].permissions == broker.REVIEW_PERMISSIONS
    assert minted[0].requested_ttl_seconds == broker.REVIEW_TTL_SECONDS

    argv, input_text, child_env = spawned[0]
    assert argv == ["gh", "api", "-X", "POST", f"repos/{_REPO}/pulls/7/reviews", "--input", "-"]
    assert json.loads(input_text or "") == {
        "body": "Looks reasonable.",
        "commit_id": _HEAD,
        "event": "COMMENT",
    }
    assert child_env["GH_TOKEN"] == _SECRET

    evidence = (
        json.dumps(result.to_dict(), sort_keys=True)
        + repr(argv)
        + (input_text or "")
        + caplog.text
    )
    assert _SECRET not in evidence
    assert "GH_TOKEN" not in evidence


def test_request_changes_review_uses_same_review_api_shape():
    spawned: list[tuple[list[str], str | None, dict[str, str]]] = []

    def spawn(argv, input_text, env):
        spawned.append((list(argv), input_text, dict(env)))
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"id": 988}), stderr="")

    result = broker.submit_self_review(
        _request(event="REQUEST_CHANGES", body="Please fix the failing path."),
        config=_config(),
        resolve_id_fn=lambda seat: 123,
        mint_fn=lambda req: _token(),
        gh_spawn=spawn,
        resolve_author_fn=_author(),
    )

    assert result.event == "REQUEST_CHANGES"
    argv, input_text, _env = spawned[0]
    assert argv == ["gh", "api", "-X", "POST", f"repos/{_REPO}/pulls/7/reviews", "--input", "-"]
    assert json.loads(input_text or "")["event"] == "REQUEST_CHANGES"


def test_approve_is_refused_before_resolve_mint_or_transport():
    called = {"resolve": 0, "mint": 0, "spawn": 0}

    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.submit_self_review(
            _request(event="APPROVE"),
            config=_config(),
            resolve_id_fn=lambda seat: called.__setitem__("resolve", called["resolve"] + 1),
            mint_fn=lambda req: called.__setitem__("mint", called["mint"] + 1),
            gh_spawn=lambda *args: called.__setitem__("spawn", called["spawn"] + 1),
        )

    assert "COMMENT or REQUEST_CHANGES" in str(exc.value)
    assert called == {"resolve": 0, "mint": 0, "spawn": 0}


def test_approve_refused_in_dev_mode():
    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.parse_request(_payload(event="APPROVE"), run_mode="dev")

    assert "APPROVE is controller approval-wall only" in str(exc.value)


def test_approve_refused_when_run_mode_none():
    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.parse_request(_payload(event="APPROVE"), run_mode=None)

    assert "APPROVE is controller approval-wall only" in str(exc.value)


@pytest.mark.parametrize(
    "argv",
    [
        ["--serve", "--config", "broker.json"],
        ["--serve", "--config", "broker.json", "--run-mode", "dev"],
    ],
)
def test_main_absent_and_dev_run_mode_reach_serve_and_approve_stays_refused(
    argv, monkeypatch
):
    seen = {}

    def fake_serve(**kwargs):
        seen.update(kwargs)

    monkeypatch.setattr(broker, "load_broker_config", lambda path: _config())
    monkeypatch.setattr(broker, "systemd_activated_unix_socket", lambda: None)
    monkeypatch.setattr(broker, "serve", fake_serve)

    assert broker.main(argv) == broker.EXIT_OK

    assert seen["run_mode"] == "dev"
    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.parse_request(_payload(event="APPROVE"), run_mode=seen["run_mode"])
    assert "APPROVE is controller approval-wall only" in str(exc.value)


def test_main_strangeloop_run_mode_reaches_serve(monkeypatch):
    seen = {}

    def fake_serve(**kwargs):
        seen.update(kwargs)

    monkeypatch.setattr(broker, "load_broker_config", lambda path: _config())
    monkeypatch.setattr(broker, "systemd_activated_unix_socket", lambda: None)
    monkeypatch.setattr(broker, "serve", fake_serve)

    assert (
        broker.main(["--serve", "--config", "broker.json", "--run-mode", "strangeLoop"])
        == broker.EXIT_OK
    )

    assert seen["run_mode"] == "strangeLoop"
    request = broker.parse_request(
        {
            **_payload(event="APPROVE"),
            "reviewer_authority_envelope": _reviewer_authority_envelope(),
        },
        run_mode=seen["run_mode"],
    )
    assert request.event == "APPROVE"


@pytest.mark.parametrize("host_run_mode", [None, "dev"])
def test_payload_run_mode_cannot_relax_approval_guard(host_run_mode):
    payload = {
        **_payload(event="APPROVE"),
        "run_mode": "strangeLoop",
        "reviewer_authority_envelope": _reviewer_authority_envelope(),
    }

    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.parse_request(payload, run_mode=host_run_mode)

    assert "APPROVE is controller approval-wall only" in str(exc.value)


def test_parser_help_lists_run_mode_flag_and_choices():
    help_text = broker._build_parser().format_help()

    assert "--run-mode" in help_text
    assert "dev" in help_text
    assert "strangeLoop" in help_text


def test_main_invalid_run_mode_rejects_fail_closed():
    with pytest.raises(SystemExit) as exc:
        broker.main(["--serve", "--config", "broker.json", "--run-mode", "solo"])

    assert exc.value.code == 2


@pytest.mark.parametrize("run_mode", ["solo", "team"])
def test_approve_refused_in_current_solo_team_modes(run_mode):
    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.parse_request(
            {**_payload(event="APPROVE"), "reviewer_authority_envelope": _reviewer_authority_envelope()},
            run_mode=run_mode,
        )

    assert "APPROVE is controller approval-wall only" in str(exc.value)


def test_approve_missing_envelope_refused_in_strangeloop_mode():
    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.parse_request(_payload(event="APPROVE"), run_mode="strangeLoop")

    assert "missing reviewer-authority-envelope" in str(exc.value)


def test_approve_allowed_in_strangeloop_mode_with_valid_envelope():
    request = broker.parse_request(
        {**_payload(event="APPROVE"), "reviewer_authority_envelope": _reviewer_authority_envelope()},
        run_mode="strangeLoop",
    )

    assert request.event == "APPROVE"
    assert request.reviewer_authority_envelope is not None


def test_approve_loads_reviewer_authority_ref_from_pane_env(tmp_path, monkeypatch):
    ref = tmp_path / "reviewer-authority.ce.yml"
    ref.write_text(json.dumps(_reviewer_authority_envelope()), encoding="utf-8")
    monkeypatch.setenv(broker.CE_REVIEWER_AUTHORITY_ENV, str(ref))

    request = broker.parse_request(_payload(event="APPROVE"), run_mode="strangeLoop")

    assert request.event == "APPROVE"
    assert request.reviewer_authority_envelope == _reviewer_authority_envelope()


def test_approve_refuses_invalid_reviewer_authority_ref_from_pane_env(tmp_path, monkeypatch):
    ref = tmp_path / "reviewer-authority.ce.yml"
    ref.write_text(
        json.dumps(_reviewer_authority_envelope(mechanic="merge")),
        encoding="utf-8",
    )
    monkeypatch.setenv(broker.CE_REVIEWER_AUTHORITY_ENV, str(ref))

    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.parse_request(_payload(event="APPROVE"), run_mode="strangeLoop")

    assert "invalid reviewer-authority-envelope ref" in str(exc.value)


def _assert_payload_ref_refused_without_open(monkeypatch, host_ref, payload_ref, payload_key):
    opened_host_refs = []
    original_open = Path.open
    host_resolved = host_ref.resolve()

    def spy_open(self, *args, **kwargs):
        if self.resolve() == host_resolved:
            opened_host_refs.append(self)
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", spy_open)

    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.parse_request(
            {**_payload(event="APPROVE"), payload_key: payload_ref},
            run_mode="strangeLoop",
        )

    assert "reviewer-authority-envelope ref must" in str(exc.value)
    assert opened_host_refs == []


@pytest.mark.parametrize(
    "payload_key",
    ["reviewer_authority_ref", "reviewer_authority_envelope_ref"],
)
def test_approve_refuses_absolute_payload_reviewer_authority_ref_without_open(
    tmp_path, monkeypatch, payload_key
):
    host_ref = tmp_path / "host-reviewer-authority.ce.yml"
    host_ref.write_text(json.dumps(_reviewer_authority_envelope()), encoding="utf-8")

    _assert_payload_ref_refused_without_open(
        monkeypatch,
        host_ref,
        str(host_ref),
        payload_key,
    )


@pytest.mark.parametrize(
    "payload_key",
    ["reviewer_authority_ref", "reviewer_authority_envelope_ref"],
)
def test_approve_refuses_escaping_payload_reviewer_authority_ref_without_open(
    tmp_path, monkeypatch, payload_key
):
    host_ref = tmp_path / "host-reviewer-authority.ce.yml"
    host_ref.write_text(json.dumps(_reviewer_authority_envelope()), encoding="utf-8")
    escaping_ref = os.path.relpath(host_ref, Path(broker._REPO_ROOT))
    assert escaping_ref.startswith("../")

    _assert_payload_ref_refused_without_open(
        monkeypatch,
        host_ref,
        escaping_ref,
        payload_key,
    )


def test_inline_envelope_wins_over_invalid_pane_env_ref(tmp_path, monkeypatch):
    ref = tmp_path / "reviewer-authority.ce.yml"
    ref.write_text("not: the authority envelope\n", encoding="utf-8")
    monkeypatch.setenv(broker.CE_REVIEWER_AUTHORITY_ENV, str(ref))

    request = broker.parse_request(
        {**_payload(event="APPROVE"), "reviewer_authority_envelope": _reviewer_authority_envelope()},
        run_mode="strangeLoop",
    )

    assert request.reviewer_authority_envelope == _reviewer_authority_envelope()


def test_submit_self_review_approve_refused_in_dev_mode():
    called = {"resolve": 0, "mint": 0, "spawn": 0}

    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.submit_self_review(
            _request(event="APPROVE"),
            config=_config(),
            resolve_id_fn=lambda seat: called.__setitem__("resolve", called["resolve"] + 1),
            mint_fn=lambda req: called.__setitem__("mint", called["mint"] + 1),
            gh_spawn=lambda *args: called.__setitem__("spawn", called["spawn"] + 1),
            run_mode="dev",
        )

    assert "COMMENT or REQUEST_CHANGES" in str(exc.value)
    assert called == {"resolve": 0, "mint": 0, "spawn": 0}


def test_submit_self_review_approve_allowed_in_strangeloop_mode(monkeypatch):
    called = {"resolve": 0, "mint": 0, "spawn": 0}

    def resolve_id(seat):
        called["resolve"] += 1
        return 123

    def mint(req):
        called["mint"] += 1
        return _token()

    def spawn(argv, input_text, env):
        called["spawn"] += 1
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"id": 989}), stderr="")

    def fake_submit(review, *, binding, minter, token_spawn=None, **kwargs):
        token = minter(
            TokenRequest(
                repo=review.repo,
                installation_id=binding.installation_id,
                run_id=binding.run_id,
                policy_sha=binding.policy_sha,
                permissions=dict(binding.permissions),
                secret_name=binding.secret_name,
                requested_ttl_seconds=binding.requested_ttl_seconds,
                escalation_authority=binding.escalation_authority,
            )
        )
        if token_spawn is not None:
            token_spawn(
                ["gh", "api", "-X", "POST", f"repos/{review.repo}/pulls/{review.pr_number}/reviews"],
                json.dumps({"event": review.event, "commit_id": review.head_sha}),
                {"GH_TOKEN": token.value},
            )
        return broker.SelfReviewResult(
            ok=True,
            repo=review.repo,
            pr_number=review.pr_number,
            head_sha=review.head_sha,
            event=review.event,
            review_id=989,
            applied=True,
        )

    monkeypatch.setattr(broker, "submit_contained_seat_pr_review", fake_submit)

    result = broker.submit_self_review(
        broker.SelfReviewRequest(
            seat_id="seat-reviewer-1",
            pr_number=7,
            head_sha=_HEAD,
            event="APPROVE",
            body="Looks reasonable.",
            reviewer_authority_envelope=_reviewer_authority_envelope(),
        ),
        config=_config(),
        resolve_id_fn=resolve_id,
        mint_fn=mint,
        gh_spawn=spawn,
        resolve_author_fn=_author(),
        run_mode="strangeLoop",
    )

    assert result.event == "APPROVE"
    assert called == {"resolve": 1, "mint": 1, "spawn": 1}


def test_submit_self_review_approve_author_refused_before_envelope_or_mint():
    called = {"resolve": 0, "mint": 0, "spawn": 0}

    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.submit_self_review(
            broker.SelfReviewRequest(
                seat_id="seat-reviewer-1",
                pr_number=7,
                head_sha=_HEAD,
                event="APPROVE",
                reviewer_authority_envelope=_reviewer_authority_envelope(),
            ),
            config=_config(),
            resolve_id_fn=lambda seat: called.__setitem__("resolve", called["resolve"] + 1),
            mint_fn=lambda req: called.__setitem__("mint", called["mint"] + 1),
            gh_spawn=lambda *args: called.__setitem__("spawn", called["spawn"] + 1),
            resolve_author_fn=_author("cedev4vps-coder"),
            run_mode="strangeLoop",
        )

    assert "author≠reviewer" in str(exc.value)
    assert called == {"resolve": 0, "mint": 0, "spawn": 0}


def test_submit_self_review_approve_refuses_invalid_envelope_before_mint():
    called = {"resolve": 0, "mint": 0, "spawn": 0}

    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.submit_self_review(
            broker.SelfReviewRequest(
                seat_id="seat-reviewer-1",
                pr_number=7,
                head_sha=_HEAD,
                event="APPROVE",
                reviewer_authority_envelope=_reviewer_authority_envelope(emitting_role="controller"),
            ),
            config=_config(),
            resolve_id_fn=lambda seat: called.__setitem__("resolve", called["resolve"] + 1),
            mint_fn=lambda req: called.__setitem__("mint", called["mint"] + 1),
            gh_spawn=lambda *args: called.__setitem__("spawn", called["spawn"] + 1),
            resolve_author_fn=_author(),
            run_mode="strangeLoop",
        )

    assert "emitting_role must be reviewer" in str(exc.value)
    assert called == {"resolve": 0, "mint": 0, "spawn": 0}


@pytest.mark.parametrize("substrate", ["contained", "non-contained"])
def test_submit_self_review_approve_outcome_does_not_depend_on_containment(monkeypatch, substrate):
    def fake_submit(review, *, binding, minter, token_spawn=None, **kwargs):
        return broker.SelfReviewResult(
            ok=True,
            repo=review.repo,
            pr_number=review.pr_number,
            head_sha=review.head_sha,
            event=review.event,
            review_id=990,
            applied=True,
        )

    monkeypatch.setattr(broker, "submit_contained_seat_pr_review", fake_submit)

    result = broker.submit_self_review(
        broker.SelfReviewRequest(
            seat_id="seat-reviewer-1",
            pr_number=7,
            head_sha=_HEAD,
            event="APPROVE",
            reviewer_authority_envelope=_reviewer_authority_envelope(),
            containment_substrate=substrate,
        ),
        config=_config(),
        resolve_id_fn=lambda seat: 123,
        mint_fn=lambda req: _token(),
        resolve_author_fn=_author(),
        run_mode="strangeLoop",
    )

    assert result.event == "APPROVE"
    assert result.review_id == 990


def test_author_is_refused_before_resolve_mint_or_transport():
    # The seat posts AS ``cedev4vps-coder`` (its App owner). If the PR author
    # resolves to that same login, the seat is reviewing its own PR — refused
    # for COMMENT/REQUEST_CHANGES, before any installation/credential mint or
    # source-host write (parity with the APPROVE refusal).
    called = {"resolve": 0, "mint": 0, "spawn": 0}

    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.submit_self_review(
            _request(),
            config=_config(),
            resolve_id_fn=lambda seat: called.__setitem__("resolve", called["resolve"] + 1),
            mint_fn=lambda req: called.__setitem__("mint", called["mint"] + 1),
            gh_spawn=lambda *args: called.__setitem__("spawn", called["spawn"] + 1),
            resolve_author_fn=_author("cedev4vps-coder"),
        )

    assert "author≠reviewer" in str(exc.value)
    assert called == {"resolve": 0, "mint": 0, "spawn": 0}


def test_unresolvable_author_fails_closed_before_resolve_mint_or_transport():
    # Author resolution failure (network/API error) must REFUSE, never post.
    called = {"resolve": 0, "mint": 0, "spawn": 0}

    def boom(repo, pr_number):
        raise broker.SelfReviewRefused(
            f"could not resolve PR author for {repo}#{pr_number}; refusing fail-closed"
        )

    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.submit_self_review(
            _request(),
            config=_config(),
            resolve_id_fn=lambda seat: called.__setitem__("resolve", called["resolve"] + 1),
            mint_fn=lambda req: called.__setitem__("mint", called["mint"] + 1),
            gh_spawn=lambda *args: called.__setitem__("spawn", called["spawn"] + 1),
            resolve_author_fn=boom,
        )

    assert "refusing fail-closed" in str(exc.value)
    assert called == {"resolve": 0, "mint": 0, "spawn": 0}


def test_parse_request_refuses_approve_before_core_call():
    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.parse_request(
            {
                "seat_id": "seat-reviewer-1",
                "pr_number": 7,
                "head_sha": _HEAD,
                "event": "APPROVE",
                "body": "not gate-valid",
            }
        )
    assert "APPROVE is controller approval-wall only" in str(exc.value)


def test_missing_injected_credential_fails_closed_before_gh_spawn():
    spawned: list[object] = []

    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.submit_self_review(
            _request(),
            config=_config(),
            resolve_id_fn=lambda seat: 123,
            mint_fn=lambda req: _token(value=""),
            gh_spawn=lambda *args: spawned.append(args),
            resolve_author_fn=_author(),
        )

    assert spawned == []
    assert "refused before forge side effect" in str(exc.value)


def test_secret_redacted_from_failed_gh_stderr_and_response():
    def spawn(argv, input_text, env):
        return subprocess.CompletedProcess(
            argv,
            1,
            stdout="",
            stderr=f"gh failed with bearer {_SECRET}",
        )

    with pytest.raises(broker.SelfReviewRefused) as exc:
        broker.submit_self_review(
            _request(),
            config=_config(),
            resolve_id_fn=lambda seat: 123,
            mint_fn=lambda req: _token(),
            gh_spawn=spawn,
            resolve_author_fn=_author(),
        )

    assert _SECRET not in str(exc.value)
    response = {"ok": False, "error": str(exc.value)}
    assert _SECRET not in json.dumps(response)


def test_bounded_json_request_refuses_oversize_and_non_object():
    with pytest.raises(broker.SelfReviewRefused):
        broker.bounded_json_load(b'{"x":"' + b"a" * 20 + b'"}', max_bytes=8)
    with pytest.raises(broker.SelfReviewRefused):
        broker.bounded_json_load(b'["not", "object"]', max_bytes=100)


def test_self_review_server_activation_keeps_existing_inode():
    socket_dir = Path(tempfile.mkdtemp(prefix="ce-sr-", dir="/var/tmp"))
    socket_path = socket_dir / "sr.sock"
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        listener.bind(str(socket_path))
        listener.listen(16)
        before = socket_path.stat()
        requests = []
        server_exceptions = []

        def submitter(request):
            requests.append(request)
            return broker.SelfReviewResult(
                ok=True,
                repo=_REPO,
                pr_number=request.pr_number,
                head_sha=request.head_sha,
                event=request.event,
                review_id=1234,
                applied=True,
            )

        def run_server():
            try:
                with broker.SelfReviewServer(
                    str(socket_path),
                    submitter=submitter,
                    max_request_bytes=broker.DEFAULT_MAX_REQUEST_BYTES,
                    activated_socket=listener,
                ) as server:
                    server.handle_request()
            except Exception as exc:  # pragma: no cover - asserted through server_exceptions
                server_exceptions.append(exc)

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        response = broker.send_request(str(socket_path), _request())
        server_thread.join(timeout=2)
        after = socket_path.stat()

        assert response == {
            "applied": True,
            "event": "COMMENT",
            "head_sha": _HEAD,
            "ok": True,
            "pr_number": 7,
            "repo": _REPO,
            "review_id": 1234,
        }
        assert [request.pr_number for request in requests] == [7]
        assert server_exceptions == []
        assert not server_thread.is_alive()
        assert (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino)
    finally:
        listener.close()
        shutil.rmtree(socket_dir, ignore_errors=True)
