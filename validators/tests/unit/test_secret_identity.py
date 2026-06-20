from dataclasses import FrozenInstanceError

import pytest
from jsonschema import Draft202012Validator, ValidationError as JsonSchemaError

from creator_engine_validator.schema import load_schema
from creator_engine_validator.secret_identity import (
    AuditUnavailable,
    BackendAlreadyRegistered,
    FakeSecretIdentityBackend,
    IdentityDescriptor,
    OpenBaoConfig,
    OpenBaoRequest,
    OpenBaoResponse,
    OpenBaoAppRoleSession,
    OpenBaoSecretIdentityBackend,
    SecretGrant,
    SecretIdentityError,
    SecretIdentityRefused,
    SecretRef,
    SecretRequest,
    SecretZeroGrant,
    SecretZeroPayload,
    SecretZeroRequest,
    UnknownBackend,
    WrappedSecretZeroRetrieval,
    available_backends,
    get_backend,
    redeem_wrapped_secret_zero,
    register_backend,
)


def _secret_ref(**overrides) -> SecretRef:
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


def _secret_request(**overrides) -> SecretRequest:
    values = {
        "run_id": "run-123",
        "seat_id": "dev-1",
        "repo": "creator-engine/creator-engine",
        "secret_ref": _secret_ref(),
        "ttl_seconds": 600,
        "delivery": "file",
        "requested_capabilities": ("read",),
        "audit_context": {"ticket": "ce-ops#113"},
    }
    values.update(overrides)
    return SecretRequest(**values)


def _secret_zero_request(**overrides) -> SecretZeroRequest:
    values = {
        "run_id": "run-123",
        "seat_id": "dev-3",
        "role_name": "ce-dev-3",
        "delivery_ref": "broker-channel:dev-3:run-123",
        "wrap_ttl_seconds": 300,
        "secret_id_ttl_seconds": 300,
        "secret_id_num_uses": 1,
        "delivery": "broker-channel",
        "auth_mount": "approle",
        "audit_context": {"ticket": "ce-ops#135"},
    }
    values.update(overrides)
    return SecretZeroRequest(**values)


def _openbao_backend(runner, **overrides) -> OpenBaoSecretIdentityBackend:
    values = {
        "config": OpenBaoConfig(
            address="https://bao.example",
            token_supplier=lambda: "broker-token",
        ),
        "runner": runner,
        "allowed_refs": {_secret_ref()},
    }
    values.update(overrides)
    return OpenBaoSecretIdentityBackend(**values)


def test_secret_identity_value_objects_are_frozen_and_value_free():
    ref = _secret_ref()
    with pytest.raises(FrozenInstanceError):
        ref.path = "other"  # type: ignore[misc]

    record = ref.to_record()
    assert record["path"] == "forge/github-apps/ce-shared/private-key"
    assert "value" not in record
    assert "live-secret-value" not in repr(record)


def test_secret_ref_and_grant_schemas_reject_values(repo_root):
    ref_schema = load_schema(repo_root / "schemas/secret-ref.schema.yaml")
    grant_schema = load_schema(repo_root / "schemas/secret-grant.schema.yaml")
    secret_zero_schema = load_schema(repo_root / "schemas/secret-zero-grant.schema.yaml")

    Draft202012Validator(ref_schema).validate(_secret_ref().to_record())
    with pytest.raises(JsonSchemaError):
        Draft202012Validator(ref_schema).validate(_secret_ref().to_record() | {"value": "leak"})

    grant = SecretGrant(
        grant_id="grant-run-123-001",
        run_id="run-123",
        seat_id="dev-1",
        secret_ref=_secret_ref(),
        lease_id=None,
        token_accessor_ref="accessor:abc123",
        issued_at="2026-06-19T03:00:00Z",
        expires_at="2026-06-19T03:10:00Z",
        delivery_ref=None,
        audit_ref="audit:sys-audit:abc123",
        revoked_at=None,
    )
    Draft202012Validator(grant_schema).validate(grant.to_record())
    with pytest.raises(JsonSchemaError):
        Draft202012Validator(grant_schema).validate(grant.to_record() | {"secret_value": "leak"})

    secret_zero_grant = SecretZeroGrant(
        grant_id="openbao-secret-zero:run-123:dev-3",
        run_id="run-123",
        seat_id="dev-3",
        role_name="ce-dev-3",
        auth_mount="approle",
        issued_at="2026-06-20T03:00:00Z",
        expires_at="2026-06-20T03:05:00Z",
        delivery_ref="broker-channel:dev-3:run-123",
        wrap_accessor_ref="wrap-accessor",
        wrapped_accessor_ref="secret-id-accessor",
        audit_ref="openbao-secret-zero:run-123:approle/ce-dev-3",
        revoked_at=None,
    )
    Draft202012Validator(secret_zero_schema).validate(secret_zero_grant.to_record())
    with pytest.raises(JsonSchemaError):
        Draft202012Validator(secret_zero_schema).validate(
            secret_zero_grant.to_record() | {"wrapping_token": "wrapped-token-value"}
        )


def test_openbao_response_repr_str_and_json_repr_redact_raw_values():
    response = OpenBaoResponse(
        status=200,
        json={
            "data": {
                "data": {"pem": "live-secret-value"},
                "metadata": {"version": 1},
            }
        },
    )

    assert "live-secret-value" not in repr(response)
    assert "live-secret-value" not in str(response)
    assert "live-secret-value" not in repr(response.json)
    assert "live-secret-value" not in repr(response.json["data"])
    assert response.json["data"]["data"]["pem"] == "live-secret-value"


def test_registry_returns_fresh_backend_and_refuses_duplicates():
    key = "test-secret-identity"
    register_backend(key, lambda: FakeSecretIdentityBackend())
    assert key in available_backends()
    assert get_backend(key).backend_key == "fake"
    assert get_backend(key) is not get_backend(key)

    with pytest.raises(BackendAlreadyRegistered):
        register_backend(key, lambda: FakeSecretIdentityBackend())
    with pytest.raises(UnknownBackend):
        get_backend("missing-secret-identity")


def test_fake_backend_issues_materializes_and_revokes_value_free_grants():
    backend = FakeSecretIdentityBackend(
        identities={
            "dev-1": IdentityDescriptor(
                identity_ref="identity:dev-1",
                seat_id="dev-1",
                human_id="peer-operator",
                github_login_ref="github:dev-1",
                email_ref="email:dev-1",
                reviewer_persona_ref="reviewer:dev-1",
                policy_refs=("policy:secret",),
            )
        },
        allowed_refs={_secret_ref()},
    )

    assert backend.resolve_identity("dev-1").github_login_ref == "github:dev-1"
    grant = backend.issue(_secret_request())
    assert grant.secret_ref == _secret_ref()
    assert "value" not in grant.to_record()

    materialized = backend.materialize(grant, "tmpfs:/run/ce/secrets/github-app.pem")
    assert materialized.delivery_ref == "tmpfs:/run/ce/secrets/github-app.pem"
    revoked = backend.revoke(materialized)
    assert revoked.revoked_at is not None
    assert backend.collect_audit(revoked)["grant_id"] == grant.grant_id


def test_fake_backend_issues_value_free_secret_zero_grant():
    backend = FakeSecretIdentityBackend()

    grant = backend.issue_secret_zero(_secret_zero_request())

    assert grant.seat_id == "dev-3"
    assert grant.role_name == "ce-dev-3"
    assert grant.delivery_ref == "broker-channel:dev-3:run-123"
    assert "wrapping-token" not in repr(grant.to_record())
    assert backend.collect_audit(grant)["backend"] == "fake"


def test_fake_backend_refuses_unlisted_secret_before_grant():
    backend = FakeSecretIdentityBackend(allowed_refs=set())
    with pytest.raises(SecretIdentityRefused):
        backend.issue(_secret_request())


@pytest.mark.parametrize(
    "secret_request",
    [
        _secret_request(secret_ref=_secret_ref(policy_sha="z" * 64)),
        _secret_request(secret_ref=_secret_ref(policy_sha="A" * 64)),
        _secret_request(repo="creator-engine/creator-engine/extra"),
        _secret_request(ttl_seconds=3601),
        _secret_request(secret_ref=_secret_ref(purpose="controller-private-key")),
    ],
)
def test_fake_backend_refuses_invalid_request_shape_before_grant(secret_request):
    backend = FakeSecretIdentityBackend(allowed_refs={secret_request.secret_ref})

    with pytest.raises(SecretIdentityRefused):
        backend.issue(secret_request)


def test_fake_backend_refuses_unlisted_capability_before_grant():
    ref = _secret_ref()
    backend = FakeSecretIdentityBackend(
        allowed_refs={ref},
        allowed_capabilities={ref: {"read"}},
    )

    with pytest.raises(SecretIdentityRefused):
        backend.issue(_secret_request(requested_capabilities=("mint",)))


def test_openbao_adapter_performs_no_io_on_init_and_refuses_without_audit():
    calls: list[OpenBaoRequest] = []

    def runner(request: OpenBaoRequest) -> OpenBaoResponse:
        calls.append(request)
        if request.path == "/v1/sys/health":
            return OpenBaoResponse(status=200, json={"sealed": False})
        if request.path == "/v1/sys/audit":
            return OpenBaoResponse(status=200, json={})
        raise AssertionError(f"unexpected request: {request}")

    backend = OpenBaoSecretIdentityBackend(
        OpenBaoConfig(
            address="https://bao.example",
            token_supplier=lambda: "broker-token",
        ),
        runner=runner,
    )
    assert calls == []
    with pytest.raises(AuditUnavailable):
        backend.validate_config()
    assert [call.path for call in calls] == ["/v1/sys/health", "/v1/sys/audit"]


def test_openbao_adapter_uses_injected_io_and_never_returns_secret_value():
    calls: list[OpenBaoRequest] = []
    materialized: list[tuple[str, str]] = []

    def runner(request: OpenBaoRequest) -> OpenBaoResponse:
        calls.append(request)
        if request.path == "/v1/sys/health":
            return OpenBaoResponse(status=200, json={"sealed": False})
        if request.path == "/v1/sys/audit":
            return OpenBaoResponse(status=200, json={"file/": {"type": "file"}})
        if (
            request.path
            == "/v1/ce-kv/data/forge/github-apps/ce-shared/private-key?version=1"
        ):
            return OpenBaoResponse(
                status=200,
                json={
                    "data": {
                        "data": {"pem": "live-secret-value"},
                        "metadata": {"version": 1},
                    }
                },
            )
        raise AssertionError(f"unexpected request: {request}")

    backend = OpenBaoSecretIdentityBackend(
        OpenBaoConfig(
            address="https://bao.example",
            token_supplier=lambda: "broker-token",
        ),
        runner=runner,
        materializer=lambda target_ref, value: materialized.append((target_ref, value)),
        allowed_refs={_secret_ref()},
    )

    grant = backend.issue(_secret_request())
    assert "live-secret-value" not in repr(grant)
    assert grant.lease_id is None
    assert grant.audit_ref.startswith("openbao:")

    materialized_grant = backend.materialize(grant, "tmpfs:/run/ce/secret.pem")
    assert materialized == [("tmpfs:/run/ce/secret.pem", "live-secret-value")]
    assert "live-secret-value" not in repr(materialized_grant)
    assert materialized_grant.delivery_ref == "tmpfs:/run/ce/secret.pem"

    revoked = backend.revoke(materialized_grant)
    assert revoked.revoked_at is not None
    audit = backend.collect_audit(revoked)
    assert audit["backend"] == "openbao"
    assert audit["audit_ref"] == grant.audit_ref

    assert [call.path for call in calls[:3]] == [
        "/v1/sys/health",
        "/v1/sys/audit",
        "/v1/ce-kv/data/forge/github-apps/ce-shared/private-key?version=1",
    ]
    assert all("live-secret-value" not in repr(call) for call in calls)


@pytest.mark.parametrize(
    "secret_request",
    [
        _secret_request(secret_ref=_secret_ref(policy_sha="z" * 64)),
        _secret_request(repo="creator-engine/creator-engine/extra"),
        _secret_request(ttl_seconds=3601),
        _secret_request(secret_ref=_secret_ref(backend="vault")),
        _secret_request(secret_ref=_secret_ref(purpose="hermes-controller-key")),
    ],
)
def test_openbao_issue_refuses_bad_shape_before_any_io(secret_request):
    calls: list[OpenBaoRequest] = []
    backend = _openbao_backend(
        lambda req: calls.append(req) or OpenBaoResponse(status=200),
        allowed_refs={secret_request.secret_ref},
    )

    with pytest.raises(SecretIdentityRefused):
        backend.issue(secret_request)

    assert calls == []


def test_openbao_issue_refuses_unlisted_secret_before_any_io():
    calls: list[OpenBaoRequest] = []
    backend = _openbao_backend(
        lambda req: calls.append(req) or OpenBaoResponse(status=200),
        allowed_refs=set(),
    )

    with pytest.raises(SecretIdentityRefused):
        backend.issue(_secret_request())

    assert calls == []


def test_openbao_issue_refuses_unlisted_capability_before_any_io():
    calls: list[OpenBaoRequest] = []
    ref = _secret_ref()
    backend = _openbao_backend(
        lambda req: calls.append(req) or OpenBaoResponse(status=200),
        allowed_refs={ref},
        allowed_capabilities={ref: {"read"}},
    )

    with pytest.raises(SecretIdentityRefused):
        backend.issue(_secret_request(requested_capabilities=("mint",)))

    assert calls == []


def test_openbao_issue_refuses_mount_config_mismatch_before_any_io():
    calls: list[OpenBaoRequest] = []
    backend = _openbao_backend(
        lambda req: calls.append(req) or OpenBaoResponse(status=200),
        config=OpenBaoConfig(
            address="https://bao.example",
            token_supplier=lambda: "broker-token",
            kv_mount="other-kv",
        ),
        allowed_refs={_secret_ref()},
    )

    with pytest.raises(SecretIdentityRefused):
        backend.issue(_secret_request())

    assert calls == []


def test_openbao_materialize_scrubs_runner_exception_values():
    calls: list[OpenBaoRequest] = []

    def runner(request: OpenBaoRequest) -> OpenBaoResponse:
        calls.append(request)
        if request.path == "/v1/sys/health":
            return OpenBaoResponse(status=200, json={"sealed": False})
        if request.path == "/v1/sys/audit":
            return OpenBaoResponse(status=200, json={"file/": {"type": "file"}})
        raise RuntimeError("backend failure mentions live-secret-value")

    backend = _openbao_backend(runner)
    grant = backend.issue(_secret_request())

    with pytest.raises(SecretIdentityError) as exc:
        backend.materialize(grant, "tmpfs:/run/ce/secret.pem")

    assert "live-secret-value" not in str(exc.value)
    assert exc.value.__cause__ is None
    assert exc.value.__context__ is None


def test_openbao_materialize_scrubs_materializer_exception_values():
    def runner(request: OpenBaoRequest) -> OpenBaoResponse:
        if request.path == "/v1/sys/health":
            return OpenBaoResponse(status=200, json={"sealed": False})
        if request.path == "/v1/sys/audit":
            return OpenBaoResponse(status=200, json={"file/": {"type": "file"}})
        if (
            request.path
            == "/v1/ce-kv/data/forge/github-apps/ce-shared/private-key?version=1"
        ):
            return OpenBaoResponse(
                status=200,
                json={
                    "data": {
                        "data": {"pem": "live-secret-value"},
                        "metadata": {"version": 1},
                    }
                },
            )
        raise AssertionError(f"unexpected request: {request}")

    def materializer(_target_ref: str, value: str) -> None:
        raise RuntimeError(f"failed to write {value}")

    backend = _openbao_backend(runner, materializer=materializer)
    grant = backend.issue(_secret_request())

    with pytest.raises(SecretIdentityError) as exc:
        backend.materialize(grant, "tmpfs:/run/ce/secret.pem")

    assert "live-secret-value" not in str(exc.value)
    assert exc.value.__cause__ is None
    assert exc.value.__context__ is None


def test_openbao_secret_zero_broker_mints_wrapped_secret_id_value_free():
    calls: list[OpenBaoRequest] = []
    delivered: list[tuple[str, SecretZeroPayload]] = []

    def runner(request: OpenBaoRequest) -> OpenBaoResponse:
        calls.append(request)
        if request.path == "/v1/sys/health":
            return OpenBaoResponse(status=200, json={"sealed": False})
        if request.path == "/v1/sys/audit":
            return OpenBaoResponse(status=200, json={"file/": {"type": "file"}})
        if request.path == "/v1/auth/approle/role/ce-dev-3/role-id":
            return OpenBaoResponse(status=200, json={"data": {"role_id": "role-id-value"}})
        if request.path == "/v1/auth/approle/role/ce-dev-3/secret-id":
            assert request.wrap_ttl_seconds == 300
            assert request.json["ttl"] == "300s"
            assert request.json["num_uses"] == 1
            assert request.json["metadata"]["seat_id"] == "dev-3"
            return OpenBaoResponse(
                status=200,
                json={
                    "wrap_info": {
                        "token": "wrapping-token-value",
                        "accessor": "wrap-accessor",
                        "wrapped_accessor": "secret-id-accessor",
                    }
                },
            )
        raise AssertionError(f"unexpected request: {request}")

    backend = OpenBaoSecretIdentityBackend(
        OpenBaoConfig(
            address="https://bao.example",
            token_supplier=lambda: "broker-token",
        ),
        runner=runner,
        secret_zero_deliverer=lambda target, payload: delivered.append((target, payload))
        or f"broker-channel-delivered:{payload.seat_id}",
    )

    grant = backend.issue_secret_zero(_secret_zero_request())

    assert grant.seat_id == "dev-3"
    assert grant.role_name == "ce-dev-3"
    assert grant.delivery_ref == "broker-channel-delivered:dev-3"
    assert grant.wrap_accessor_ref == "wrap-accessor"
    assert grant.wrapped_accessor_ref == "secret-id-accessor"
    assert "wrapping-token-value" not in repr(grant)
    assert "role-id-value" not in repr(grant.to_record())
    assert delivered[0][0] == "broker-channel:dev-3:run-123"
    assert delivered[0][1].role_id == "role-id-value"
    assert delivered[0][1].wrapping_token == "wrapping-token-value"
    assert "role-id-value" not in repr(delivered[0][1])
    assert "wrapping-token-value" not in repr(delivered[0][1])
    assert [call.path for call in calls] == [
        "/v1/sys/health",
        "/v1/sys/audit",
        "/v1/auth/approle/role/ce-dev-3/role-id",
        "/v1/auth/approle/role/ce-dev-3/secret-id",
    ]
    assert all("wrapping-token-value" not in repr(call) for call in calls)


@pytest.mark.parametrize(
    "secret_zero_request",
    [
        _secret_zero_request(role_name="ce-dev-4"),
        _secret_zero_request(seat_id="dev-9", role_name="ce-dev-9"),
        _secret_zero_request(wrap_ttl_seconds=601),
        _secret_zero_request(secret_id_ttl_seconds=601),
        _secret_zero_request(secret_id_num_uses=2),
        _secret_zero_request(delivery_ref="file:///tmp/wrap"),
    ],
)
def test_openbao_secret_zero_refuses_bad_request_before_any_io(secret_zero_request):
    calls: list[OpenBaoRequest] = []
    backend = OpenBaoSecretIdentityBackend(
        OpenBaoConfig(
            address="https://bao.example",
            token_supplier=lambda: "broker-token",
        ),
        runner=lambda request: calls.append(request) or OpenBaoResponse(status=200),
        secret_zero_deliverer=lambda _target, _payload: "broker-channel:dev-3",
    )

    with pytest.raises(SecretIdentityRefused):
        backend.issue_secret_zero(secret_zero_request)

    assert calls == []


def test_openbao_secret_zero_refuses_unwrapped_secret_id_response():
    def runner(request: OpenBaoRequest) -> OpenBaoResponse:
        if request.path == "/v1/sys/health":
            return OpenBaoResponse(status=200, json={"sealed": False})
        if request.path == "/v1/sys/audit":
            return OpenBaoResponse(status=200, json={"file/": {"type": "file"}})
        if request.path == "/v1/auth/approle/role/ce-dev-3/role-id":
            return OpenBaoResponse(status=200, json={"data": {"role_id": "role-id-value"}})
        if request.path == "/v1/auth/approle/role/ce-dev-3/secret-id":
            return OpenBaoResponse(status=200, json={"data": {"secret_id": "secret-id-value"}})
        raise AssertionError(f"unexpected request: {request}")

    backend = OpenBaoSecretIdentityBackend(
        OpenBaoConfig(
            address="https://bao.example",
            token_supplier=lambda: "broker-token",
        ),
        runner=runner,
        secret_zero_deliverer=lambda _target, _payload: "broker-channel:dev-3",
    )

    with pytest.raises(SecretIdentityRefused) as exc:
        backend.issue_secret_zero(_secret_zero_request())

    assert "unwrapped SecretID" in str(exc.value)
    assert "secret-id-value" not in str(exc.value)


def test_openbao_secret_zero_deliverer_must_not_record_raw_values():
    def runner(request: OpenBaoRequest) -> OpenBaoResponse:
        if request.path == "/v1/sys/health":
            return OpenBaoResponse(status=200, json={"sealed": False})
        if request.path == "/v1/sys/audit":
            return OpenBaoResponse(status=200, json={"file/": {"type": "file"}})
        if request.path == "/v1/auth/approle/role/ce-dev-3/role-id":
            return OpenBaoResponse(status=200, json={"data": {"role_id": "role-id-value"}})
        if request.path == "/v1/auth/approle/role/ce-dev-3/secret-id":
            return OpenBaoResponse(
                status=200,
                json={"wrap_info": {"token": "wrapping-token-value"}},
            )
        raise AssertionError(f"unexpected request: {request}")

    backend = OpenBaoSecretIdentityBackend(
        OpenBaoConfig(
            address="https://bao.example",
            token_supplier=lambda: "broker-token",
        ),
        runner=runner,
        secret_zero_deliverer=lambda _target, payload: payload.wrapping_token,
    )

    with pytest.raises(SecretIdentityError) as exc:
        backend.issue_secret_zero(_secret_zero_request())

    assert "wrapping-token-value" not in str(exc.value)
    assert exc.value.__cause__ is None


def test_redeem_wrapped_secret_zero_returns_in_memory_openbao_session():
    calls: list[OpenBaoRequest] = []

    def runner(request: OpenBaoRequest) -> OpenBaoResponse:
        calls.append(request)
        if request.path == "/v1/sys/wrapping/unwrap":
            assert request.token == "wrapping-token-value"
            return OpenBaoResponse(
                status=200,
                json={"data": {"secret_id": "secret-id-value", "secret_id_accessor": "sid-accessor"}},
            )
        if request.path == "/v1/auth/approle/login":
            assert request.json["role_id"] == "role-id-value"
            assert request.json["secret_id"] == "secret-id-value"
            return OpenBaoResponse(
                status=200,
                json={"auth": {"client_token": "seat-token-value", "accessor": "token-accessor", "lease_duration": 600}},
            )
        raise AssertionError(f"unexpected request: {request}")

    session = redeem_wrapped_secret_zero(
        WrappedSecretZeroRetrieval(
            seat_id="dev-3",
            role_name="ce-dev-3",
            role_id_supplier=lambda: "role-id-value",
            wrapping_token_supplier=lambda: "wrapping-token-value",
        ),
        runner=runner,
    )

    assert isinstance(session, OpenBaoAppRoleSession)
    assert session.token_supplier() == "seat-token-value"
    assert session.token_accessor_ref == "token-accessor"
    assert session.secret_id_accessor_ref == "sid-accessor"
    assert session.as_openbao_config(address="https://bao.example").token_supplier() == "seat-token-value"
    assert "seat-token-value" not in repr(session)
    assert "secret-id-value" not in repr(session)
    assert all("secret-id-value" not in repr(call) for call in calls)
