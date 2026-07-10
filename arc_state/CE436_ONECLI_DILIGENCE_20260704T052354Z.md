# CE436 OneCLI Adoption Diligence Report

UTC: 2026-07-04T05:23:54Z

Scope: research-only audit for `creator-engine/ce-ops#436`, OneCLI upstream `onecli/onecli` and reference integration `nanocoai/nanoclaw`.

## Evidence Baseline

- SSOT ticket: `creator-engine/ce-ops#436`, open, title `Contained SOLO deployment: NanoClaw/OneCLI-style local credential gateway (no OpenBao) - design`, URL https://github.com/creator-engine/ce-ops/issues/436.
- Reframe comment: https://github.com/creator-engine/ce-ops/issues/436#issuecomment-4880751114. It sets rent-first adoption diligence, keeps CE broker for governance lane, and names license, vault key custody, arm64, maturity/security, policy-layer, and NanoClaw setup as gate criteria.
- OneCLI clone commit: `890c5c31ac501b549534120d25e3b349552340ee` from `https://github.com/onecli/onecli`.
- NanoClaw clone commit: `aecad864e6371cb2a77ceaff8a38f9c4a8b71774` from `https://github.com/nanocoai/nanoclaw`.
- Environment limitation: `cargo` and `pnpm` were not installed. Cargo.lock and pnpm-lock license metadata were resolved by parsing lockfiles and querying crates.io/npm registry read-only. Docker exists but lacks `docker buildx`; GHCR manifest digest verification is UNVERIFIABLE from this host.

## Executive Summary

Verdict: ADOPT-WITH-CONDITIONS, not unconditional adopt.

OneCLI is a good fit for the commodity lane: API/model credential storage, request-time proxy injection, per-agent credential scoping, rate limits, and manual approvals. It should not replace CE's broker for GitHub push/PR authority or ratification semantics.

The biggest concrete custody fact is now verified: OneCLI local mode does not use passphrase/keychain unlock. It stores the AES-256-GCM master key as a base64 32-byte file in Docker volume-backed `/app/data/secret-encryption-key`, exports it as `SECRET_ENCRYPTION_KEY`, and auto-unlocks on reboot.

The highest adoption risks are supply-chain/update control and local exposure: default install/update flows chase `latest` unless overridden, gateway releases have no binary assets/signatures, NanoClaw's direct CLI download does not verify checksums, and upstream has open issues about unauthenticated local/admin API exposure.

CE should adopt OneCLI only behind CE-owned pinning, digest/checksum verification, launch-guard compatibility for placeholders, no self-update path, and a clear division: OneCLI = API credential proxy; CE broker = Git/messaging/governance authority.

## 1. License

### Repository LICENSE byte verification

- `onecli/onecli` LICENSE sha256: `b84f4620e3fba70c3a27d55fc9d4dda79948c2c55ebce9a007b55f9c4756d6ab`. GitHub reports Apache-2.0. The Rust gateway manifest also declares `license = "Apache-2.0"` at `apps/gateway/Cargo.toml` lines 1-5. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/LICENSE and https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/apps/gateway/Cargo.toml#L1-L5.
- `nanocoai/nanoclaw` LICENSE sha256: `d20135a5de128506f70407bdcd22f8c49862187a5c46da81b34b9ed91085a480`. GitHub reports MIT. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/LICENSE.

### OneCLI gateway Rust dependency licenses

Source lockfile: `onecli/onecli` `apps/gateway/Cargo.lock`, sha256 `ee9d3e4979c4e382556a743ecd1ea8e08055f4eb139160958585ab70eca2a770`, commit `890c5c31...`.

Result: 446 locked Rust packages resolved, 0 unknown. No GPL, AGPL, SSPL, or BUSL packages were found. The only copyleft-option entries were `r-efi` 5.3.0 and 6.0.0 with `MIT OR Apache-2.0 OR LGPL-2.1-or-later`; because MIT/Apache choices are available, this is a review note, not a blocker.

License count summary:

```text
(MIT OR Apache-2.0) AND Unicode-3.0: 1
Apache-2.0: 32
Apache-2.0 / MIT: 1
Apache-2.0 AND ISC: 1
Apache-2.0 OR BSL-1.0: 1
Apache-2.0 OR BSL-1.0 OR MIT: 2
Apache-2.0 OR ISC OR MIT: 7
Apache-2.0 OR MIT: 41
Apache-2.0 OR MIT OR Zlib: 1
Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT: 14
Apache-2.0/MIT: 2
BSD-2-Clause OR Apache-2.0 OR MIT: 2
BSD-3-Clause: 6
BSL-1.0: 1
CC0-1.0 OR MIT-0 OR Apache-2.0: 1
CDLA-Permissive-2.0: 2
ISC: 4
ISC AND (Apache-2.0 OR ISC): 1
ISC AND (Apache-2.0 OR ISC) AND OpenSSL: 1
MIT: 65
MIT AND BSD-3-Clause: 1
MIT OR Apache-2.0: 216
MIT OR Apache-2.0 OR BSD-1-Clause: 1
MIT OR Apache-2.0 OR LGPL-2.1-or-later: 2
MIT OR Apache-2.0 OR Zlib: 2
MIT/Apache-2.0: 15
Unicode-3.0: 18
Unlicense OR MIT: 3
Zlib: 1
Zlib OR Apache-2.0 OR MIT: 1
```

Selected runtime gateway direct dependencies from `apps/gateway/Cargo.toml` include `tokio`, `hyper`, `axum`, `tokio-rustls`, `rustls`, `rcgen`, `ring`, `reqwest`, `clap`, `serde`, `sqlx`, `ap-client`, `ap-proxy-client`, `ap-proxy-protocol`, `ap-noise`, and optional cloud deps. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/apps/gateway/Cargo.toml#L13-L138.

### OneCLI JS parts in all-in-one image

The Docker image is not just the Rust gateway: it builds a Next.js web/API surface plus Prisma and runs both `onecli-gateway` and `node apps/web/server.js`. Sources: Dockerfile lines 30-65, 87-118 and entrypoint lines 57-66:

- https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/docker/Dockerfile#L30-L65
- https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/docker/Dockerfile#L87-L118
- https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/docker/entrypoint.sh#L57-L66

Source lockfile: `onecli/onecli` `pnpm-lock.yaml`, sha256 `0cde8453b9b7359ae821e7bc88138502eee35318fce56e9b5c5c535c9fb9fb15`.

Result: 1,043 locked npm package entries resolved, 0 unknown. GPL/AGPL/SSPL/BUSL were not found. LGPL appears in Sharp/libvips packages used by the JS/web image, not the Rust gateway binary itself:

```text
@img/sharp-libvips-darwin-arm64 1.2.4 LGPL-3.0-or-later
@img/sharp-libvips-darwin-x64 1.2.4 LGPL-3.0-or-later
@img/sharp-libvips-linux-arm 1.2.4 LGPL-3.0-or-later
@img/sharp-libvips-linux-arm64 1.2.4 LGPL-3.0-or-later
@img/sharp-libvips-linux-ppc64 1.2.4 LGPL-3.0-or-later
@img/sharp-libvips-linux-riscv64 1.2.4 LGPL-3.0-or-later
@img/sharp-libvips-linux-s390x 1.2.4 LGPL-3.0-or-later
@img/sharp-libvips-linux-x64 1.2.4 LGPL-3.0-or-later
@img/sharp-libvips-linuxmusl-arm64 1.2.4 LGPL-3.0-or-later
@img/sharp-libvips-linuxmusl-x64 1.2.4 LGPL-3.0-or-later
@img/sharp-wasm32 0.34.5 Apache-2.0 AND LGPL-3.0-or-later AND MIT
@img/sharp-win32-arm64 0.34.5 Apache-2.0 AND LGPL-3.0-or-later
@img/sharp-win32-ia32 0.34.5 Apache-2.0 AND LGPL-3.0-or-later
@img/sharp-win32-x64 0.34.5 Apache-2.0 AND LGPL-3.0-or-later
```

Direct JS runtime manifests include `apps/web/package.json`, `packages/api/package.json`, `packages/db/package.json`, and `packages/ui/package.json`; examples include `next`, `react`, `hono`, `ioredis`, `@1password/sdk`, `@aws-sdk/*`, `stripe`, `zod`, `@prisma/client`. Sources:

- https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/apps/web/package.json
- https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/packages/api/package.json
- https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/packages/db/package.json
- https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/packages/ui/package.json

License conclusion: Rust gateway is permissive for embed/depend. The all-in-one image has LGPL-licensed Sharp/libvips packages, so CE should treat image redistribution obligations separately if distributing the full web image rather than consuming OneCLI as an external service.

## 2. Vault Master-Key Custody

Verified source behavior:

1. Local Docker entrypoint auto-generates a base64 32-byte key if `SECRET_ENCRYPTION_KEY` is absent, stores it in `/app/data/secret-encryption-key`, chmods it `600`, exports it, and reads it back into `SECRET_ENCRYPTION_KEY`. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/docker/entrypoint.sh#L20-L31.
2. Docker Compose mounts named volume `app-data:/app/data`, so the key survives container restarts/reboots as long as the Docker volume survives. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/docker/docker-compose.yml#L24-L45.
3. Node `CryptoService` reads `SECRET_ENCRYPTION_KEY`, base64-decodes it, requires exactly 32 bytes, and uses AES-256-GCM with 12-byte IV and 16-byte tag. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/packages/api/src/lib/crypto.ts#L1-L23 and #L42-L99.
4. Rust gateway `CryptoService::from_env()` reads the same `SECRET_ENCRYPTION_KEY`, validates 32 bytes, and uses `ring::aead::AES_256_GCM`. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/apps/gateway/src/crypto.rs#L1-L49.
5. Main gateway startup fails if `CryptoService::from_env()` fails. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/apps/gateway/src/main.rs#L205-L209.
6. Inline secrets store ciphertext in Postgres `secrets.encrypted_value`; schema says AES-256-GCM via CryptoService. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/packages/db/prisma/schema.prisma#L189-L204.
7. Request-time gateway decrypts inline values through the Rust crypto service; wrong key/corrupt format skips the secret. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/apps/gateway/src/connect.rs#L348-L400.

Custody answer:

- Key derivation: no KDF or passphrase derivation in local OSS path. The key is random 32 bytes from `/dev/urandom`, base64-encoded.
- Storage: Docker named volume mounted at `/app/data`, file `/app/data/secret-encryption-key` with container-level chmod 600. It is adjacent to app data, not OS keychain.
- Unlock: automatic on process start by reading the file/env var. No interactive passphrase, no macOS Keychain, no libsecret, no 1Password unlock for the master key.
- Reboot/headless: should auto-unlock after reboot if Docker volumes persist and the stack starts. Headless Linux does not need UI for vault decrypt. If `/app/data/secret-encryption-key` is lost while Postgres data remains, the entrypoint will generate a new key and existing encrypted inline secrets become undecryptable.
- External vault integrations: Bitwarden/1Password support credential resolution without storing those secret values in OneCLI Postgres, but they do not change custody of OneCLI's inline vault master key. Sources: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/docs/vault-integration.md and https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/apps/gateway/src/vault/mod.rs.

Risk: this is solo-friendly and headless-friendly, but it is not user-presence protected. Host user or container/volume compromise compromises all inline vault secrets.

## 3. arm64 Support

OneCLI gateway/container:

- Publish workflow builds `ghcr.io/onecli/onecli` for `linux/amd64` on `ubuntu-latest` and `linux/arm64` on `ubuntu-24.04-arm`, pushes by digest, uploads digests, and creates a multi-arch manifest with semver and `latest` tags. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/.github/workflows/publish.yml#L13-L124.
- Dockerfile uses Rust and Node Alpine base images, no architecture-specific hardcoding. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/docker/Dockerfile#L7-L31 and #L70-L118.
- Gateway release `v1.40.0` has no GitHub release assets; distribution is the GHCR image plus source tar/zip. Source: `gh release view v1.40.0 --repo onecli/onecli` returned assets `[]`, URL https://github.com/onecli/onecli/releases/tag/v1.40.0.
- GHCR manifest digest verification: UNVERIFIABLE in this environment because Docker lacks `buildx`. Workflow proves build intent, not local pull verification.

OneCLI host CLI:

- `onecli/onecli-cli` latest `v2.3.0` publishes `darwin_arm64`, `linux_arm64`, `darwin_amd64`, `linux_amd64`, Windows assets, and `checksums.txt`; GitHub asset metadata includes sha256 digests. Source: https://github.com/onecli/onecli-cli/releases/tag/v2.3.0.
- NanoClaw's installer supports `process.platform` `darwin` and `linux`, and `process.arch` `x64`/`arm64`, mapping to exact release archive names. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/setup/onecli.ts#L198-L213.

NanoClaw container path:

- README claims macOS/Linux/WSL2 Docker support and Apple Container as opt-in. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/README.md#L134-L176.
- NanoClaw CI is `ubuntu-latest` only; no macOS/arm64 matrix in `.github/workflows/ci.yml`. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/.github/workflows/ci.yml#L7-L39.
- There is an open NanoClaw issue about default OneCLI setup bind mismatch on Linux/docker bridge causing agent non-response. Source: https://github.com/nanocoai/nanoclaw/issues/2903.

Conclusion: OneCLI has linux/arm64 container publishing and macOS arm64 host CLI assets. Apple Silicon solo is plausible through Docker Desktop plus arm64 CLI. CE aarch64 host support is plausible through linux/arm64 image, but CE should verify GHCR manifest digests in its own update pipeline.

## 4. Maturity and Bus Factor

OneCLI:

- Repo created 2026-03-08, latest fetched commit pushed 2026-07-03, 2,437 stars, 129 forks, 8 watchers. Source: `gh repo view onecli/onecli`.
- Local git history: 296 commits; first commit `bef6893` on 2026-03-08; 19 unique GitHub contributors via contributors API; local `git shortlog` showed 22 named authors. Source clone commit `890c5c31...`.
- Releases: 30 GitHub releases; latest `v1.40.0` on 2026-07-02. Recent cadence: v1.40.0 2026-07-02, v1.39.0 2026-06-28, v1.38.0 2026-06-20, v1.37.0 2026-06-16, v1.36.0 2026-06-10.
- Issue ratio: 55 open issues, 32 closed issues by GitHub search API, issue type only.
- Security posture evidence: no `SECURITY.md` found in OneCLI tree; `rg` found no disclosure policy. GitHub security-advisory API returned no public advisories accessible. Vulnerability-alert status API is permission-gated and UNVERIFIABLE.
- Open security/high-risk issues relevant to CE: unauthenticated local admin API (#263), Docker bridge admin API/Postgres exposure (#268), Anthropic prompt-cache header/body alteration (#404). URLs: https://github.com/onecli/onecli/issues/263, https://github.com/onecli/onecli/issues/268, https://github.com/onecli/onecli/issues/404.

NanoClaw:

- Repo created 2026-01-31, latest fetched commit 2026-07-02, 30,116 stars, 12,898 forks, 126 watchers. Source: `gh repo view nanocoai/nanoclaw`.
- Local git history: 1,899 commits; first commit `c17823a` on 2026-01-31; 101 unique GitHub contributors via contributors API; local `git shortlog` showed 172 named authors.
- Releases: 4 GitHub releases; latest `v2.1.17` on 2026-06-17. `RELEASING.md` says releases are manually cut on version bumps, with no fixed schedule. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/RELEASING.md#L1-L48.
- Issue ratio: 285 open issues, 437 closed issues by GitHub search API, issue type only.
- Security docs exist at `docs/SECURITY.md`, including container isolation, OneCLI credential isolation, optional egress lockdown, and pnpm supply-chain controls. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/docs/SECURITY.md#L1-L203.
- Open security issues include local gateway approval bypass (#2761), arbitrary file exfiltration (#2760), hidden MCP env/args approval smuggling (#2762/#2827). Source examples: https://github.com/nanocoai/nanoclaw/issues/2761.

Maturity conclusion: OneCLI is young but active, with frequent releases and enough contributors to avoid single-commit abandonment, but still has open local-security issues directly in the CE threat model. Treat it as a high-trust rented surface requiring CE-owned pinning and active update review.

## 5. Update and Supply-Chain Governance

OneCLI upstream:

- Official install script downloads `docker-compose.yml` from `main`, defaults `ONECLI_VERSION` to `latest`, pulls images, starts compose, and tells users to update by re-running `curl -fsSL https://onecli.sh/install | sh`. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/scripts/install.sh#L22-L31 and #L108-L197.
- Docker Compose image defaults to `ghcr.io/onecli/onecli:${ONECLI_VERSION:-latest}`. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/docker/docker-compose.yml#L24-L45.
- Publish workflow pushes by digest and then creates multi-arch tags, but I found no signature/cosign workflow and release `v1.40.0` has no assets/checksums. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/.github/workflows/publish.yml#L52-L124 and release view for https://github.com/onecli/onecli/releases/tag/v1.40.0.
- Release automation uses release-please on push to main with `ONECLI_OSS_RELEASE`. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/.github/workflows/release.yml#L1-L21.

NanoClaw reference:

- NanoClaw pins sanctioned OneCLI gateway and CLI versions in `versions.json`: `onecli-gateway` 1.36.0, `onecli-cli` 2.2.5 at audited commit. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/versions.json#L1-L4.
- Setup installs gateway by exporting `ONECLI_VERSION=<pin>` before piping `curl -fsSL onecli.sh/install | sh`. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/setup/onecli.ts#L149-L163.
- Setup installs CLI by direct GitHub release download at the pin, but does not verify `checksums.txt` or the GitHub asset digest before copying the binary. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/setup/onecli.ts#L185-L243.
- NanoClaw explicitly says setup does not auto-migrate gateway; `/update-nanoclaw` should diff `versions.json` and route to `docs/onecli-upgrades.md`. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/docs/onecli-upgrades.md#L1-L83.

CE governance recommendation:

- Do not let OneCLI self-update. Do not use `latest` in CE-controlled flows.
- Treat OneCLI as a rented surface in CE's manifest: pin gateway image by immutable digest and source tag/commit, pin OneCLI CLI by exact version plus sha256, and verify before install.
- Use one CE-controlled update mechanism: surface-bump ratification with license/security diff, GHCR digest verification, changelog review, and rollback instructions.
- Forbid runtime update commands inside contained/host-critical paths. Upgrades should be controller-mediated, not agent-mediated.

## 6. Policy-Layer Fit

OneCLI policy expressiveness:

- Policy schema accepts `hostPattern`, `pathPattern`, HTTP method, action `block|rate_limit|manual_approval|allow`, enabled flag, optional agentId, rateLimit plus window minute/hour/day, and conditions array of body contains checks. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/packages/api/src/validations/policy-rule.ts#L1-L67.
- Prisma model stores policy rules by project/org, host/path/method/action, per-agent optional scope, rate limits, metadata, and JSON conditions. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/packages/db/prisma/schema.prisma#L221-L250.
- Gateway policy evaluation priority is block, manual approval, rate limit, explicit allow/default-deny. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/apps/gateway/src/policy.rs#L61-L167.
- Rate-limit keys include org, project, rule id, agent token, and fixed window. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/apps/gateway/src/policy.rs#L117-L144.
- OSS condition matching is currently a stub: `needs_body_buffer` is false and `matches` always true. Body conditions appear to require non-OSS/cloud implementation. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/apps/gateway/src/condition_match.rs#L1-L18.
- Manual approvals in OSS use in-memory DashMap/watch/broadcast state with 180-second timeout; cloud swaps Redis. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/apps/gateway/src/approval.rs#L1-L29 and #L192-L260.

Fit conclusion:

- Enough for solo API credential scoping: host/path/method match, per-agent identity, block/rate/manual-approval/allow, default-deny for credentialed non-LLM hosts.
- Not enough to replace CE broker policy: no CE signed request envelopes, no PR/push authority minting, no ratification semantics, no CE-specific approval wall, no revocation protocol for GitHub App tokens, and OSS body conditions are inert.
- Recommendation: run two policy layers. OneCLI is the API-credential proxy and request-time secret injector. CE broker remains the governance lane for Git/messaging authority, signed requests, revocation, carrier discipline, and push/PR semantics.

## 7. Integration Shape From NanoClaw

Reference flow from NanoClaw:

1. Setup step `onecli` installs or reuses OneCLI, writes `ONECLI_URL` to `.env`, and health-checks `/api/health`. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/setup/onecli.ts#L1-L13 and #L397-L463.
2. Fresh install pins the gateway version, runs `curl -fsSL onecli.sh/install | sh`, installs the CLI at pinned version, sets `onecli config set api-host`, writes `.env`. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/setup/onecli.ts#L149-L243 and #L431-L441.
3. Remote mode installs only the CLI, configures remote API host, optionally logs in with `NANOCLAW_ONECLI_API_TOKEN`, and writes `ONECLI_API_KEY` to `.env`. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/setup/onecli.ts#L294-L353.
4. Auth step checks `onecli secrets list`; creates an Anthropic secret with `onecli secrets create --type anthropic --value <token> --host-pattern api.anthropic.com`. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/setup/auth.ts#L1-L13 and #L79-L186.
5. Subscription sign-in runs `claude setup-token`, extracts token, then saves it to OneCLI. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/setup/register-claude-token.sh#L4-L15 and #L121-L125.
6. Custom endpoint flow stores token as OneCLI generic secret with `Authorization: Bearer {value}`, writes only `ANTHROPIC_BASE_URL` to `.env`, and appends provider registration so containers receive `ANTHROPIC_BASE_URL` and placeholder auth token. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/setup/auto.ts#L1004-L1069 and https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/src/providers/claude.ts#L1-L28.
7. Runtime reads `ONECLI_URL` and `ONECLI_API_KEY`, instantiates `new OneCLI({ url, apiKey })`, ensures a OneCLI agent identity, and calls `applyContainerConfig(args, { addHostMapping: false, agent })`. If it returns false, NanoClaw refuses to spawn the container. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/src/config.ts#L8-L44 and https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/src/container-runner.ts#L483-L499.
8. NanoClaw mounts session and group folders, `container.json` read-only, composed docs read-only, shared skills/read-only source, then applies OneCLI after volume mounts so nested credential stubs are not shadowed. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/src/container-runner.ts#L266-L363 and #L474-L510.

CE contained-solo flow should drive:

- Install/pin OneCLI gateway image and CLI through CE rented-surface mechanism.
- Start gateway with CE-chosen bind addresses, no `latest`.
- Create/verify OneCLI user/API key and agent identity.
- Store model-provider secret in OneCLI; for custom endpoints use generic header rewrite.
- Launch container with OneCLI-generated proxy config and CA/stubs, plus CE broker socket for governance lane.
- Fail closed when OneCLI config cannot be applied or health check fails.

Potential conflict with CE launch guard:

- NanoClaw custom endpoint passes `ANTHROPIC_AUTH_TOKEN=placeholder` into the container. Source: `src/providers/claude.ts` lines 8-16 and 20-27.
- The ce-ops#436 ticket says CE `codex_launch_spec` refuses credential env names into containers, including Anthropic/OpenAI keys. If the guard blocks by env-name rather than value, this placeholder pattern will trip it.
- Required CE condition: either teach the launch guard a narrow audited placeholder exception for OneCLI-managed env names or avoid credential-looking env names entirely by configuring provider SDKs through non-secret config files/stubs that the guard allows. Do not weaken the guard broadly.

## 8. Gaps OneCLI Does Not Cover For CE Solo

Verified/extended gaps:

- GitHub push/PR authority: OneCLI can inject generic/API credentials, but it does not implement CE broker semantics for signed-request verification, envelope/carrier discipline, scoped GitHub App token minting, PR/push/revoke workflows, or controller-owned merge gates. This matches the ce-ops#436 reframe division of labor.
- Messaging credentials: OneCLI handles HTTP/API credentials, but channel adapter credentials, linked-device auth state, and local messaging session stores remain host/NanoClaw/CE concerns. NanoClaw security docs say channel auth sessions are not mounted and remain host-only. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/docs/SECURITY.md#L67-L85.
- Revocation/rotation automation: OneCLI has secret list/create and access assignment primitives, but no CE-specific rotation schedule, no ratified revocation event protocol, and no automatic GitHub App token lifecycle. OneCLI README says it gives one place to manage/rotate, but code evidence here did not show CE-grade automation. Source: https://github.com/onecli/onecli/blob/890c5c31ac501b549534120d25e3b349552340ee/README.md#L28-L44.
- Headless Linux: gateway decrypt is headless-friendly because the key is a file/env var, but subscription auth is interactive/browser/TTY driven in NanoClaw; API-key/paste paths are viable but not fully unattended. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/setup/register-claude-token.sh#L55-L82 and setup/auth.ts.
- Local host trust boundary: OneCLI upstream has open issues alleging unauthenticated local/admin API and Docker bridge/Postgres exposure. These are in-scope for contained solo because untrusted agent containers share the host/container network. Sources: https://github.com/onecli/onecli/issues/263 and https://github.com/onecli/onecli/issues/268.
- Forced egress: NanoClaw documents optional egress lockdown, default false. CE cannot rely on HTTPS_PROXY alone because proxy-unaware tools/raw sockets can bypass it. Source: https://github.com/nanocoai/nanoclaw/blob/aecad864e6371cb2a77ceaff8a38f9c4a8b71774/docs/SECURITY.md#L86-L126.

## Verdict

ADOPT-WITH-CONDITIONS.

Conditions, all checkable:

1. CE owns version and update governance: OneCLI gateway image pinned by immutable digest; OneCLI CLI pinned by exact version and sha256; no `latest`; no runtime self-update; changes flow through CE rented-surface ratification.
2. Verify supply-chain before use: fetch/check GHCR manifest digest for linux/arm64 and linux/amd64; verify CLI `checksums.txt` or GitHub asset digest; record in CE manifest.
3. Keep policy split explicit: OneCLI handles API credential injection/scoping/rate/manual approval. CE broker remains mandatory for GitHub push/PR authority, signed envelopes, revocation, messaging/git credentials, and merge gates.
4. Resolve launch-guard placeholder conflict before implementation: credential-looking env names such as `ANTHROPIC_AUTH_TOKEN=placeholder` must either be narrowly allowlisted as audited OneCLI placeholders or replaced with non-env configuration.
5. Harden network exposure: bind admin API and Postgres away from agent-reachable networks; prefer only the proxy port reachable from contained agents; test against upstream issues #263/#268/#2903.
6. Backup and custody UX: document `/app/data/secret-encryption-key` as the master key; back up it with Postgres volume; warn that loss makes inline secrets undecryptable; do not claim keychain/passphrase protection.
7. Headless path: require API-key/OAuth-token paste or operator-provided token flow for headless Linux; subscription browser sign-in is not unattended.
8. Security watch: block adoption or require compensating controls if upstream leaves unauthenticated admin API/Postgres exposure unresolved for CE's deployment shape.

Fallback trigger:

- Reject and build CE-native thin gateway only if any of these fail: license compliance for the distribution shape, digest/checksum pinning, local API/Postgres exposure isolation, or launch-guard-compatible placeholder injection.

## Appendices

### Appendix A: Rust Gateway Dependency License Notes

Full source of truth is `apps/gateway/Cargo.lock` at commit `890c5c31ac501b549534120d25e3b349552340ee`. The sweep resolved every locked crate. The complete generated table was too large for the executive body; the decisive non-permissive/copy-left scan found only:

```text
r-efi 5.3.0 MIT OR Apache-2.0 OR LGPL-2.1-or-later
r-efi 6.0.0 MIT OR Apache-2.0 OR LGPL-2.1-or-later
```

No GPL, AGPL, SSPL, or BUSL package was found in the Rust gateway lockfile.

### Appendix B: OneCLI JS Lock License Notes

Full source of truth is `pnpm-lock.yaml` at commit `890c5c31ac501b549534120d25e3b349552340ee`. The sweep resolved 1,043 npm package entries, 0 unknown. License count summary:

```text
(MPL-2.0 OR Apache-2.0): 1
0BSD: 1
Apache-2.0: 280
Apache-2.0 AND LGPL-3.0-or-later: 3
Apache-2.0 AND LGPL-3.0-or-later AND MIT: 1
BSD-2-Clause: 11
BSD-3-Clause: 16
BlueOak-1.0.0: 1
CC-BY-4.0: 1
CC0-1.0: 1
ISC: 32
LGPL-3.0-or-later: 10
MIT: 670
MPL-2.0: 13
Python-2.0: 1
SEE LICENSE IN LICENSE: 1
```

LGPL entries are Sharp/libvips platform packages listed in Section 1.

## Stop Line

Report complete. No GitHub writes, no branches, no PRs, no code edits.
