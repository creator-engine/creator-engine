# Validation Sandbox Receipts

Validation sandbox receipts are host-side authority evidence. The signing secret
must be sourced before launching the sandbox and must never be placed in
`ValidationSandboxSpec.env`.

Production callers source the receipt signing secret through the host/controller
secret path, preferably `SecretIdentityBackend` backed by OpenBao, materialized
into controller memory or a controller-owned tmpfs file. The caller then
constructs `ValidationSandboxReceiptIssuer(secret=...)` and passes it to
`run_validation_sandbox_in_container`.

The sandbox environment remains scrubbed by the Slice-7 validation-env seam:
`require_no_credential_env` still rejects credential-shaped values,
`podman-verification-v1` keeps `secret_allowlist: []`, and the launcher receives
`secret_grants=()`. The receipt key signs the observed result after the
container exits; it is not available inside the validation container.
