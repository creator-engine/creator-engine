import json
import urllib.error

import pytest

from creator_engine_validator.openbao_p3 import (
    AuditFailClosedProbe,
    OpenBaoBrokerSession,
    OpenBaoDeploymentConfig,
    OpenBaoHttpConfig,
    OperatorActionRequired,
    WrappedAppRoleBootstrapConfig,
    build_p3_deployment_plan,
    make_openbao_http_runner,
    unwrap_wrapped_approle_secret_id,
    verify_audit_fail_closed,
)
from creator_engine_validator.secret_identity import (
    OpenBaoRequest,
    OpenBaoResponse,
    SecretBackendTransportError,
    SecretIdentityRefused,
    SecretRef,
)


def _runtime_ref(**overrides) -> SecretRef:
    values = {
        "backend": "openbao",
        "mount": "ce-kv",
        "path": "forge/github-apps/ce-shared/private-key",
        "field": "pem",
        "version": 1,
        "purpose": "github-app-pem",
        "owner_ref": "github-app:ce-shared",
        "policy_sha": "a" * 64,
    }
    values.update(overrides)
    return SecretRef(**values)


def test_p3_local_deployment_plan_is_value_free_and_local_only():
    config = OpenBaoDeploymentConfig.local_ephemeral(
        address="http://127.0.0.1:18200",
        allowed_secret_refs=(_runtime_ref(),),
    )

    plan = build_p3_deployment_plan(config)

    assert plan.ready_for_local_execution is True
    assert plan.operator_required_steps == ()
    assert "start-local-openbao" in plan.automated_steps
    assert plan.record["topology"]["network_exposure"] == "local-loopback-only"
    assert plan.record["secret_zero"]["method"] == "response-wrapped-approle"
    assert "revoke-broker-tokens" in plan.record["emergency_revocation"]["steps"]
    assert "live-secret-value" not in repr(plan)
    assert "root_token" not in json.dumps(plan.record)


def test_p3_controller_pilot_plan_flags_operator_only_steps():
    config = OpenBaoDeploymentConfig.controller_pilot(
        host_ref="controller-vps:ce-pilot-1",
        address="https://openbao.internal.example",
        ca_bundle_ref="secret-ref:openbao-ca",
        allowed_secret_refs=(_runtime_ref(),),
    )

    plan = build_p3_deployment_plan(config)

    assert plan.ready_for_local_execution is False
    assert "operator-provision-controller-vps" in plan.operator_required_steps
    assert "operator-inject-wrapping-token" in plan.operator_required_steps
    assert "operator-unseal-shamir" in plan.operator_required_steps
    assert "operator-backup-restore-drill" in plan.operator_required_steps
    assert "operator-emergency-revocation-drill" in plan.operator_required_steps
    assert plan.record["unseal"]["operator_only"] is True
    assert plan.record["backup_restore"]["restore_test_required"] is True


def test_p3_plan_refuses_public_or_non_tls_controller_topology():
    with pytest.raises(SecretIdentityRefused):
        build_p3_deployment_plan(
            OpenBaoDeploymentConfig.controller_pilot(
                host_ref="controller-vps:ce-pilot-1",
                address="http://openbao.internal.example",
                ca_bundle_ref="secret-ref:openbao-ca",
                allowed_secret_refs=(_runtime_ref(),),
            )
        )

    with pytest.raises(SecretIdentityRefused):
        build_p3_deployment_plan(
            OpenBaoDeploymentConfig(
                profile="controller-pilot",
                host_ref="controller-vps:ce-pilot-1",
                address="https://openbao.example",
                ca_bundle_ref="secret-ref:openbao-ca",
                network_exposure="public",
                allowed_secret_refs=(_runtime_ref(),),
            )
        )


@pytest.mark.parametrize(
    "ref",
    [
        _runtime_ref(path="signing/roots/ce-root-v1", purpose="release-signing-root"),
        _runtime_ref(path="attestation/private-key", purpose="attestation-private-key"),
        _runtime_ref(path="forge/controller-key", purpose="controller-key"),
    ],
)
def test_p3_plan_refuses_governance_root_cotenancy(ref):
    config = OpenBaoDeploymentConfig.local_ephemeral(
        address="http://127.0.0.1:18200",
        allowed_secret_refs=(ref,),
    )

    with pytest.raises(SecretIdentityRefused):
        build_p3_deployment_plan(config)


def test_wrapped_approle_bootstrap_unwraps_and_returns_value_free_session():
    calls: list[OpenBaoRequest] = []

    def runner(request: OpenBaoRequest) -> OpenBaoResponse:
        calls.append(request)
        if request.path == "/v1/sys/wrapping/unwrap":
            assert request.token == "wrapping-token"
            return OpenBaoResponse(
                status=200,
                json={"data": {"secret_id": "secret-id-value", "secret_id_accessor": "sid-accessor"}},
            )
        if request.path == "/v1/auth/approle/login":
            assert request.json["role_id"] == "role-id-value"
            assert request.json["secret_id"] == "secret-id-value"
            return OpenBaoResponse(
                status=200,
                json={"auth": {"client_token": "broker-token", "accessor": "token-accessor", "lease_duration": 600}},
            )
        raise AssertionError(f"unexpected request: {request}")

    session = unwrap_wrapped_approle_secret_id(
        WrappedAppRoleBootstrapConfig(
            role_name="ce-broker",
            role_id_supplier=lambda: "role-id-value",
            wrapping_token_supplier=lambda: "wrapping-token",
        ),
        runner=runner,
    )

    assert isinstance(session, OpenBaoBrokerSession)
    assert session.token_supplier() == "broker-token"
    assert session.token_accessor_ref == "token-accessor"
    assert session.secret_id_accessor_ref == "sid-accessor"
    assert "broker-token" not in repr(session)
    assert "secret-id-value" not in repr(session)
    assert all("secret-id-value" not in repr(call) for call in calls)


def test_wrapped_approle_bootstrap_scrubs_transport_exceptions():
    def runner(_request: OpenBaoRequest) -> OpenBaoResponse:
        raise RuntimeError("failed with secret-id-value")

    with pytest.raises(SecretBackendTransportError) as exc:
        unwrap_wrapped_approle_secret_id(
            WrappedAppRoleBootstrapConfig(
                role_name="ce-broker",
                role_id_supplier=lambda: "role-id-value",
                wrapping_token_supplier=lambda: "wrapping-token",
            ),
            runner=runner,
        )

    assert "secret-id-value" not in str(exc.value)
    assert exc.value.__cause__ is None


def test_http_runner_uses_headers_and_redacts_errors():
    captured = {}

    def transport(method, url, headers, body, timeout, ssl_context):
        captured.update(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "body": body,
                "timeout": timeout,
                "ssl_context": ssl_context,
            }
        )
        return 200, b'{"ok": true}'

    runner = make_openbao_http_runner(
        OpenBaoHttpConfig(address="https://bao.example", timeout_seconds=3),
        transport=transport,
    )
    response = runner(OpenBaoRequest(method="POST", path="/v1/sys/health", token="broker-token", json={"x": "y"}))

    assert response.status == 200
    assert response.json["ok"] is True
    assert captured["url"] == "https://bao.example/v1/sys/health"
    assert captured["headers"]["X-Vault-Token"] == "broker-token"
    assert captured["body"] == b'{"x":"y"}'
    assert captured["timeout"] == 3


def test_http_runner_emits_openbao_wrap_ttl_header():
    captured = {}

    def transport(method, url, headers, body, timeout, ssl_context):
        captured.update(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "body": body,
                "timeout": timeout,
                "ssl_context": ssl_context,
            }
        )
        return 200, b'{"wrap_info":{"token":"wrapped"}}'

    runner = make_openbao_http_runner(
        OpenBaoHttpConfig(address="https://bao.example", timeout_seconds=3),
        transport=transport,
    )
    response = runner(
        OpenBaoRequest(
            method="POST",
            path="/v1/auth/approle/role/ce-dev-3/secret-id",
            token="broker-token",
            json={"num_uses": 1},
            wrap_ttl_seconds=300,
        )
    )

    assert response.status == 200
    assert captured["headers"]["X-Vault-Wrap-TTL"] == "300s"


def test_http_runner_scrubs_url_errors():
    def transport(_method, _url, _headers, _body, _timeout, _ssl_context):
        raise urllib.error.URLError("offline broker-token")

    runner = make_openbao_http_runner(
        OpenBaoHttpConfig(address="https://bao.example"),
        transport=transport,
    )

    with pytest.raises(SecretBackendTransportError) as exc:
        runner(OpenBaoRequest(method="GET", path="/v1/sys/health", token="broker-token"))

    assert "broker-token" not in str(exc.value)
    assert exc.value.__cause__ is None


def test_audit_fail_closed_probe_reports_expected_block():
    calls: list[str] = []
    blocked = False

    def runner(request: OpenBaoRequest) -> OpenBaoResponse:
        calls.append(request.path)
        if request.path == "/v1/sys/audit":
            return OpenBaoResponse(status=200, json={"file/": {"type": "file"}})
        if request.path == "/v1/secret/data/canary":
            return OpenBaoResponse(status=500 if blocked else 200, json={"data": {"data": {"ok": "yes"}}})
        raise AssertionError(f"unexpected request: {request}")

    def break_audit() -> None:
        nonlocal blocked
        blocked = True

    result = verify_audit_fail_closed(
        AuditFailClosedProbe(
            token_supplier=lambda: "broker-token",
            canary_path="/v1/secret/data/canary",
        ),
        runner=runner,
        break_audit=break_audit,
    )

    assert result.fail_closed is True
    assert result.before_status == 200
    assert result.after_status == 500
    assert calls == ["/v1/sys/audit", "/v1/secret/data/canary", "/v1/secret/data/canary"]


def test_audit_fail_closed_probe_refuses_missing_audit_device():
    def runner(request: OpenBaoRequest) -> OpenBaoResponse:
        assert request.path == "/v1/sys/audit"
        return OpenBaoResponse(status=200, json={})

    with pytest.raises(OperatorActionRequired):
        verify_audit_fail_closed(
            AuditFailClosedProbe(token_supplier=lambda: "broker-token"),
            runner=runner,
            break_audit=lambda: None,
        )
