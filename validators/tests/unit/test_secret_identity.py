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
    OpenBaoSecretIdentityBackend,
    SecretGrant,
    SecretIdentityError,
    SecretIdentityRefused,
    SecretRef,
    SecretRequest,
    UnknownBackend,
    available_backends,
    get_backend,
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
