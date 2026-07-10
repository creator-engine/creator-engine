# DISPATCH — dev-3 — 2026-07-10 — unit: mint-broker runnable server (ce-419) — class S
Role: implementer foreman. Signal: `READY-FOR-HARVEST ce-419-mint-broker-server <full-40-hex-sha>`
or `BLOCKED ce-419-mint-broker-server <one-line-reason>`.
Branch `ce-419-mint-broker-server` off freshly fetched origin/main OR LATER. Worktree
/var/tmp/wt-ce-419-mint-broker-server. Standing preflight directive: run
`ce validate-pr --profile contained-seat` if your environment can; else focused tests +
BLOCKED(env) per protocol. PRE-SIGNAL CHECKLIST: focused tests green + confidentiality check:
`python -m pytest validators/tests/unit/test_public_docs_confidentiality.py::test_tracked_text_files_contain_no_new_confidential_or_internal_references -q`

## Context (embedded)
The mint-broker library is complete and pure (tools/mint-broker/mint_broker/{config,binding,
service}.py — handle_token_request is deliberately transport-free with full unit coverage).
The consumer posts JSON to `${CE_FORGE_MINT_BROKER_URL}/v1/token` via urllib. MISSING: any
runnable server. This unit ships the DEPLOYABLE ARTIFACT ONLY — the controller performs all
activation (PEM provisioning, network-exposure decision, TLS/nginx, systemctl) later.

## Unit
1. NEW `tools/mint-broker/ce_mint_broker_server.py` — thin stdlib HTTP layer:
   - Binds 127.0.0.1:PORT ONLY (port from config/env; refuse any bind address override that
     is not loopback — TLS/exposure is the reverse proxy's job, never this process's).
   - POST /v1/token → parse JSON body → mint_broker.service.handle_token_request → JSON
     response. Everything else → 404/405. Health: GET /healthz → 200 with NO body echo.
   - NOTE the runtime coupling: service.py imports egress_broker.audit — the entrypoint must
     extend sys.path to tools/egress-broker (document this in the module docstring and mirror
     it in the systemd unit's Environment/WorkingDirectory).
   - SECURITY (hard requirements, from the scope review):
     a. NEVER log request or response bodies at any level (caller ghu_ token arrives in the
        body; minted ghs_ token returns in it). Access logging = method + path + status ONLY.
     b. The PEM path from config is passed through untouched; PEM content never read into
        this layer, never in argv, never in exceptions.
     c. No new authn layer in this slice — the binding check + per-user rate cap in the pure
        service ARE the defense; say so in the docstring; exposure posture is controller-lane.
     d. Config file must be refused if world/group-writable (stat check at startup).
2. NEW `deploy/systemd/ce-mint-broker.service` — template following ce-egress-broker.service
   conventions + the LogsDirectory= pattern (no writable-$HOME dependency), dedicated
   service user placeholder, EnvironmentFile= for the config path.
3. NEW `tools/mint-broker/config.example.yaml` — every field of the existing config loader,
   placeholder values only, comments noting pem_path must live on tmpfs.
4. NEW `validators/tests/unit/test_mint_broker_server.py` — injected-transport tests (no real
   sockets needed beyond loopback ephemeral): happy-path mint via the wired pure function
   (stub the openssl signer seam the existing service tests use), 404/405 routing, healthz,
   non-loopback bind refusal, body-logging prohibition (assert the access-log formatter never
   receives body content), group-writable config refusal.

## Files (allowed writes)
The four NEW files above + `.ce/changelog/ce-419-mint-broker-server.md` + carrier
`.ce/pr-manifests/ce-419-mint-broker-server.md` (slug=branch) with exactly:
`- **Declared work class:** S`. Product lens; synthetic values everywhere.

## Stop lines
mint_broker/{config,binding,service}.py (pure library is FROZEN — wrap, don't edit),
tools/egress-broker/** (runtime dependency — import path only), tools/host-ops-broker/**
(parallel pattern lands SECOND, after this establishes it), secret_identity.py, ce_cli.py,
v3_cli.py, all other deploy/**, .github/**, docs/**, install.sh, docs/llms-install.md,
.ce/brain/assertions.yaml, every in-flight module.
