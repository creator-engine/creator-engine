# Controller Power Continuity Research

Date: 2026-07-06  
Worker: dev-1 architect/research, read-only/report-only  
Tracker: creator-engine/ce-ops#471  
Output: `/home/ce-dev-1/ce-reports/CONTROLLER_POWER_CONTINUITY_RESEARCH_20260706.md`

## Executive summary

The controller should not become less powerful. It should become more precisely shaped: the controller keeps full operational capability, but high-blast actions move through small deterministic verbs, short-lived grants, witnessable evidence, and explicit Operator co-input where human intent is part of the trust model.

The consolidated program in ce-ops#471 should be accepted as four connected workstreams:

1. `ce takeover`: a first-class continuity verb that detects predecessor state, selects the governed harness, verifies Ring-0 posture, hydrates from durable state, enters `AWAITING-OPERATOR` first, re-arms watchers, then emits a posture banner and evidence packet.
2. Signing deputy: an SSHSIG-aware signing service, with `ce-root-v1` never exposed to seats or the raw controller process. OpenBao can hold custody behind the service, but generic Transit signing is not enough because CE emits OpenSSH SSHSIG artifacts. A per-release Operator co-sign artifact bound to `content_sha256`, single-use, short-TTL, and minted on an Operator-controlled channel should be mandatory immediately, including before full controller containment.
3. Host-ops broker: a fixed verb set for convergent host operations, with raw Docker/Podman/containerd sockets excluded. The broker should expose restore-toward-known-good verbs, not host-root primitives.
4. Recursion bottom-out: repair loops should descend into simpler, slower-changing layers and stop at a defined circuit breaker. The bottom rung is Operator/reprovision, not another agent with broader ambient power.

The highest-priority ticket is continuity, not containment. The 2026-07-06 incident was not primarily that a replacement controller could not exist; it was that the correct launch/takeover path was not discoverable during a quota halt. A refusal that prints the exact takeover command is a safety and usability improvement.

Input verification:

- Queue brief hash matched: `02b94801fe26f421db60bf5d514585e83528d1ec5bd89b4e97443b7938baed7f`.
- Full research brief hash matched: `ff85af18f6afd2b4307917efdb3b26a9b44fa2e85f36c9d42d6b6b97bd975091`.
- `docs/adr/ADR-0005` was requested but is not present in this checkout; the available ADR files stop at ADR-0004. This report treats the issue/brief/repo docs as controlling.

## Tension framing

The Operator framing is correct: fully mitigating power-abuse risk by removing power defeats the purpose of a controller. The CE design should instead shape capability along four axes:

- Who may request the action.
- Which exact verb may run.
- Which artifact, content hash, or live object the verb is bound to.
- What evidence and revocation path exists after the action.

This framing rejects both extremes. A raw host controller with ambient credentials is effective but over-broad. A controller stripped of signing, host ops, GitHub mutation, and recovery authority is safe only because it is no longer a controller. The desired point is a high-capability controller whose dangerous powers are mediated by deterministic deputies and whose ordinary workflow is easier than bypassing them.

The already-reached positions A-D should stand:

- A. `ce takeover` is the continuity verb. Raw `role=controller` launch without governed evidence should enter `READ_ONLY_UNTIL_GOVERNED_LAUNCH_CONFIRMED` and print the correct command.
- B. `ce-root-v1` key custody needs a signing deputy now. The per-release Operator co-sign artifact closes a present-day behavioral-only gap, not just a future contained-controller gap.
- C. Host operations need a broker with fixed convergent verbs. Raw DooD is root-equivalent and should be treated as a temporary anti-pattern.
- D. Repair recursion bottoms out by layer simplification: agents and daemons repair fast-moving software; a tiny supervised broker repairs narrow host state; host OS/provisioning and Operator recovery remain the final rung.

## Prior art with citations

Short-lived credentials and response wrapping:

- OpenBao AppRole supports role-bound machine authentication. The documented AppRole model distinguishes pull and push SecretID modes, and the API supports SecretID TTLs and use limits. CE's current OpenBao bringup already mirrors this with 10-minute token TTL, 30-minute max TTL, one-use SecretIDs, and response wrapping. Sources: OpenBao AppRole docs https://openbao.org/docs/auth/approle/ and API docs https://openbao.org/api-docs/auth/approle/.
- OpenBao response wrapping is per-request and uses an `X-Vault-Wrap-TTL` header or CLI `-wrap-ttl`, giving CE a primary pattern for one-use handoff of secret-zero material without storing it in a seat. Source: https://openbao.org/docs/concepts/response-wrapping/.
- GitHub App installation tokens expire after one hour and can be scoped down by repositories and permissions, but cannot exceed the app/installation grant. This is the right model for forge actions: broker mints a short-lived token for one operation envelope rather than handing a PAT to a seat. Source: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation.

SSH CA and signing:

- OpenBao's SSH secrets engine supports signed SSH certificates and OTP modes; the signed-certificate mode lets a client use its own ephemeral key while OpenBao signs a short-lived certificate. This is a strong fit for host-ops broker SSH actions. Sources: https://openbao.org/docs/secrets/ssh/ and https://openbao.org/docs/secrets/ssh/signed-ssh-certificates/.
- OpenBao Transit supports signing/verification operations, but CE release artifacts use OpenSSH SSHSIG. The SSHSIG format is a specific armored detached signature format with a namespace and SSH wire structures. Therefore the signing deputy should be format-aware: it can keep custody in OpenBao or a signer OS user, but it must emit SSHSIG correctly rather than expose a generic raw signing API. Sources: OpenSSH SSHSIG protocol https://github.com/openssh/openssh-portable/blob/master/PROTOCOL.sshsig and OpenBao Transit docs https://openbao.org/docs/secrets/transit/.

Keyless and co-signed attestations:

- Sigstore keyless signing binds an ephemeral key to an OIDC identity via Fulcio and logs signing events in Rekor. This is good prior art for identity-bound, short-lived signing, but CE's `ce-root-v1` trust root is intentionally local and SSHSIG-shaped, so Sigstore is a pattern source rather than a direct replacement. Source: https://docs.sigstore.dev/cosign/signing/overview/.
- Cosign supports in-toto attestations and policy validation over attestations. This maps to CE evidence packets and Operator co-sign artifacts: sign the statement about the artifact, not the controller's self-claim. Source: https://docs.sigstore.dev/cosign/verifying/attestation/.
- Witness provides in-toto attestation creation and verification, policy evaluation, Sigstore keyless support, timestamping, and process attestation. It is a rental/fork candidate for evidence-packet mechanics, but not for the CE root SSHSIG release ceremony. Sources: https://github.com/in-toto/witness and https://witness.dev/docs/docs/tutorials/sigstore-keyless/.

Admission and break-glass:

- Kubernetes admission webhooks and ValidatingAdmissionPolicy illustrate the CE Ring-0/Ring-1 split: admission is a deterministic pre-persist/pre-effect policy point, while webhooks and CEL policies make the policy boundary explicit. Sources: https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/ and https://kubernetes.io/docs/reference/access-authn-authz/validating-admission-policy/.
- Kyverno PolicyException resources provide a structured exception object instead of ad hoc bypass. CE should copy the pattern: break-glass is an object with scope, expiration, and audit, not a raw socket or root shell. Source: https://kyverno.io/docs/guides/exceptions/.
- Microsoft Entra emergency access guidance reinforces that break-glass accounts should be restricted to emergencies, monitored, and not used as normal daily admin flow. CE's equivalent is a broker kill-switch and Operator/reprovision rung, not a standing raw-host controller exception. Source: https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/security-emergency-access.

Agent-fleet/controller practice:

- OpenAI Codex web is a managed cloud agent surface that connects to GitHub and creates pull requests. It validates the market shape of background code agents, but it is not a rent candidate for CE controller continuity because CE needs self-hosted governance, a local merge wall, and controlled credential custody. Source: https://developers.openai.com/codex/cloud.
- GitHub Copilot cloud agent can research, change code on a branch, and create PRs; GitHub's docs explicitly distinguish Copilot review output from required approval, and product material states agent PRs still sit behind existing policies and human approval. This supports CE's "agents author evidence, humans/controlled gate ratify" posture. Sources: https://docs.github.com/copilot/concepts/agents/cloud-agent/about-cloud-agent and https://docs.github.com/copilot/using-github-copilot/code-review/using-copilot-code-review.

## Current-state matrix

| Surface | Current state | Enforcement layer | Gap |
| --- | --- | --- | --- |
| Claude controller launch | Ring-0 evaluator refuses `--bare`, headless, background agents, remote control, local settings weakening, unsafe skip-permissions, and uncontrolled MCP; `.claude/settings.json` provides PreToolUse and Stop hooks. | Code support and launch-wired; live controller parity depends on launch evidence. | Controller takeover is not a first-class verb. |
| Codex controller launch | `codex_launch_spec.py` has CDX-D Ring-0 evaluator and credential-scrubbed command builder; `.codex/requirements.toml` plus `ce-pretooluse-codex.py` provide a managed PreToolUse path. | Code support exists; launch runtime refuses absent managed hook pack; matrix still records Codex Ring 1 as deferred pending containment acceptance. | Live session may be raw-launched; no Codex Stop/closeout hook; controller promotion evidence is not explicit enough. |
| Harness matrix | `HARNESS_SUPPORT_CAPABILITY_MATRIX.md` says Claude and lane are full for Ring 0/1/2; Codex is Ring 0 full, Ring 1 deferred, Ring 2 none, containment deferred. | Probed code-derived matrix. | Need added columns for `code-support`, `launch-wired`, `live-proven`, `promotion-approved`. |
| Contained controller | `deploy/dgx-controller-runsc` C1 scaffold exists: runsc/gVisor, dedicated home, no host sockets, `gh` fail-closed guard. | Static/dry-run containment scaffold. | C2 credential injection, C3 live parity, C4 cutover remain unproven. |
| Approval wall | `ce-approval-capability` marker binds repo, PR, head SHA, reviewer, expiry, policy SHA. Production source is OpenBao-backed `SecretIdentityBackend`; contained seats cannot mint. | Live daemon path plus value-free public marker. | Good precedent for signing deputy co-input; not sufficient for release signing. |
| OpenBao | Operator bringup runbook, AppRole, KV path map, audit, snapshot/restore guidance exist. `ce-root-v1` transit path is explicitly deferred and not available to dev AppRoles. | Secret spine exists; recovery state still operationally sensitive. | Signing deputy needs a concrete SSHSIG-aware service and recovery drill. |
| Credential injection | ce-ops#228 principle: credentials must never enter container env/metadata. Codex launch spec refuses credential env carriers. ce-ops#436 ratified OneCLI for solo API-credential lane with CE broker retaining governance lane. | Policy and some guards exist. | Full controller credential injection is still C2/blocking for contained controller parity. |
| DevOps privileged-action broker | Contract/schema/slice-1 stub exists; high/irreversible work must be broker-proxied. | Design/schema/offline stub. | Needs host-ops verb implementation and systemd-supervised runtime. |
| C5 daemon cutover | ce-ops#466 closed mixed-UID host prep gap after failed cutover. | Queue-daemon container path improving. | Host ownership/UID operations remain a real broker verb class. |
| De-SPOF | ce-ops#398 Phase A one-liner standup open; ce-ops#397 Phase B ADR open. | Issue-level program. | `ce takeover` should be the continuity layer between standup and multi-coordinator ADR. |

## Design options with usability-vs-safety scoring

Scoring: 1 is poor, 5 is strong. "Efficiency" measures day-to-day controller throughput, not only human convenience.

| Option | Description | Usability | Efficiency | Safety | Recommendation |
| --- | --- | ---: | ---: | ---: | --- |
| O1: Raw controller plus stronger instructions | Keep current raw host controller and rely on briefs, memory, and STOP lines. | 4 | 4 | 1 | Reject as an end-state. It already failed for `ce-root-v1` custody and launch discoverability. |
| O2: Governed raw controller plus `ce takeover` | Keep host-local controller, but require launch/takeover evidence, posture banner, refusal-that-teaches, and continuity drill. | 5 | 5 | 3 | P0 default. It improves safety without waiting for containment. |
| O3: Contained controller only after C2/C3/C4 | Make contained controller the only gate path after credential injection and parity proof. | 3 | 4 | 4 | Target state, but not a blocker for P0 continuity. Raw-host break-glass remains needed until proven. |
| O4: Signing deputy with Operator co-sign | Format-aware SSHSIG service; `ce-root-v1` not readable by seats/controller; per-release co-sign bound to artifact hash. | 4 | 4 | 5 | P1/P2 required. Applies immediately, before controller containment. |
| O5: Generic OpenBao Transit sign endpoint | Use Transit directly and let controller construct signatures. | 3 | 4 | 3 | Insufficient alone because SSHSIG formatting and release ceremony semantics are outside generic sign. Use behind deputy only. |
| O6: Host-ops broker with convergent verbs | Broker exposes `repair-daemon`, `rotate-log`, `restart-service`, `prune-runtime-cache`, `prepare-owned-state-root`, `run-ephemeral-job`, not raw socket. | 4 | 5 | 5 | Strongly recommend. This is capability-shaping, not capability removal. |
| O7: Raw Docker/Podman socket break-glass | Mount/hand raw socket to controller or contained seat during incidents. | 5 | 5 | 1 | Reject except explicit manual Operator host session. Root-equivalent and non-convergent. |
| O8: Ephemeral controllers as stateless workers | Event-spawn controllers from forge/arc manifests; singleton gate remains persistent daemon/approval wall. | 4 | 5 | 4 | Good P2 direction from ce-ops#454. Do not give ephemeral controllers signing or merge-gate custody. |

Best composite path:

1. P0: O2 now.
2. P1: O4 and O6 design/contract with dry-run evidence.
3. P2: O3/O8 after C2 credential injection, C3 live parity, and Phase A drill evidence.

## Tiered ticket program

### P0: continuity verb and drill

Ticket: `ce takeover` continuity verb.

Acceptance bar:

- `ce takeover --from <seat-or-session> --harness <claude|codex> --repo-root <path>` exists with `--dry-run --json`.
- Detects predecessor state from `.ce/state`, lifecycle records, newest resume state by mtime, brain bootstrap, active work ledger, merge queue, approval-wall state, and watcher manifest.
- Selects/validates harness through Ring-0 launch runtime.
- Hydrates state but starts in `AWAITING-OPERATOR` until posture banner and evidence packet are reviewed.
- Re-arms watchers/daemons from a duty manifest, not prose.
- Raw controller launch with missing governed evidence refuses as `READ_ONLY_UNTIL_GOVERNED_LAUNCH_CONFIRMED` and prints the exact `ce takeover` or `ce launch --harness ...` command.
- Scheduled continuity drill proves a replacement can perform one benign governed gate cycle without predecessor chat history.

Usability cost: low; makes the right path discoverable.  
Safety gain: high; removes improvisational recovery.  
Dependencies: ce-ops#398 for standup inputs, brain/bootstrap state, duty manifest, current launch validators.  

Ticket: Controller posture banner.

Acceptance bar:

- Command prints role, harness, launch mode, Ring-0 confirmed, Ring-1 active, Ring-2/closeout support, credential scrub status, remote-control status, approval-wall armed state, signing-deputy status, allowed posture (`read-only`, `foreman`, `gate-capable`).
- Banner is included in `ce takeover` evidence.

Usability cost: low.  
Safety gain: medium-high.

### P1: promotion gates and parity evidence

Ticket: Harness parity-by-layer matrix.

Acceptance bar:

- Extend current matrix or companion report with `code-support`, `launch-wired`, `live-proven`, `promotion-approved`.
- Claude, Codex, lane, contained-controller scaffold, and ephemeral-controller providers are represented.
- A harness cannot be called controller-gate-capable unless all required cells are green or explicitly Operator-ratified with an exception.

Usability cost: low.  
Safety gain: high, because it prevents "support exists" from being confused with "this live session is promoted."

Ticket: Codex controller promotion evidence packet.

Acceptance bar:

- Packet records actual argv after Ring-0 rewrite, managed hook confirmation, CDX-D result, bypass-mode source, remote-control disabled/enabled status, hook requirements SHA, hook script SHA, lifecycle/sentinel references, and Ring-1 smoke result.
- `ce launch --harness codex` refuses or downgrades when packet is missing for controller authority.

Usability cost: medium for first launch, low after automation.  
Safety gain: high.

### P2: signing deputy, broker, and contained/ephemeral control plane

Ticket: SSHSIG signing deputy design and prototype.

Acceptance bar:

- `ce-root-v1` private key is unavailable to controller seats and workers.
- Sign verb input requires artifact canonical bytes hash, spec content SHA, release id, ratification ref, and Operator co-sign artifact.
- Operator co-sign artifact is single-use, short-TTL, content-hash-bound, and minted outside agent context.
- Deputy emits OpenSSH SSHSIG with the correct namespace and records value-free evidence.
- OpenBao custody path is used behind the deputy, or an interim `ce-signer` OS user is documented as a ratified bridge.

Usability cost: medium; release ceremony gains one explicit co-sign step.  
Safety gain: very high.  
Dependencies: ce-ops#442, OpenBao recovery state, release signing procedure, Operator co-sign decision.

Ticket: Host-ops broker v1.

Acceptance bar:

- Fixed verb set v1 ratified: proposed initial verbs are `status`, `restart-daemon`, `prepare-owned-state-root`, `rotate-attempt-log`, `repair-systemd-unit`, `run-ephemeral-container`, `prune-stopped-owned-containers`, `snapshot-openbao`, `restore-drill-openbao`.
- Each verb has parameter schema, convergence invariant, idempotency expectation, rate limit, audit event, and kill-switch behavior.
- Raw Docker/Podman/containerd socket access is explicitly excluded from seat/controller containers.
- Broker is systemd-supervised and smaller/static relative to the agent layer.

Usability cost: medium initially, low after runbooks point to verbs.  
Safety gain: very high.  
Dependencies: C5 learnings from ce-ops#466, devops privileged-action broker contract, OpenBao if secret minting is needed.

Ticket: Recursion bottom-out policy.

Acceptance bar:

- Defines max repair recursion depth, same-failure detection, and layer transitions.
- Emits `AWAITING-OPERATOR` or circuit-breaker state when bottom-out is reached.
- Watchers distinguish "retryable repair" from "same condition repeated."
- Scheduled drill simulates broken agent, broken daemon, broken broker, and host reprovision path.

Usability cost: low-medium; prevents runaway repair loops.  
Safety gain: high.

Ticket: Ephemeral controller provider seam.

Acceptance bar:

- Providers share mandate-pointer-in and forge-results-out contract.
- Provider 1: self-hosted webhook receiver to canonical runtime image.
- Provider 2: GitHub Actions job for read/report or low-authority sweeps.
- Provider 3: managed agent clouds only as compute rental, never gate/sign custody.
- Singleton gate, approval wall, and signing deputy remain outside ephemeral controllers.

Usability cost: medium.  
Safety gain: medium-high.  
Dependencies: ce-ops#454, ce-ops#397, C2/C3/C4 if gate-adjacent.

## Operator decision list

1. Name the continuity verb: `ce takeover` is recommended. Alternative names should be rejected unless they clearly imply authority transfer, not just launch.
2. Decide whether raw `role=controller` launch without takeover evidence is always read-only or may be temporarily foreman-capable with an explicit Operator break-glass marker. Recommendation: read-only by default.
3. Pick the Operator co-sign artifact form. Recommendation: a detached signed JSON statement with `release_id`, `content_sha256`, `spec_content_sha256`, `expires_at`, `nonce`, `single_use_id`, and Operator identity, minted on an Operator-controlled device/channel.
4. Choose signing deputy custody path. Recommendation: durable OpenBao-backed custody behind an SSHSIG-aware deputy; interim `ce-signer` OS user only if OpenBao recovery blocks implementation.
5. Ratify host-ops broker verb list v1. Recommendation: start with convergent repair/status verbs plus one controlled ephemeral-run verb; defer arbitrary command execution.
6. Define remote-control policy. Recommendation: governed authoring controllers keep remote-control disabled unless routed through a brokered/evidence-preserving surface; read-only supervisory sessions may use remote-control with explicit non-authoring posture.
7. Decide whether Codex Ring-1 promotion can proceed before full containment acceptance. Recommendation: yes for governed raw-controller parity if the evidence packet and smoke test are live-proven, while the matrix separately keeps containment deferred.
8. Set continuity drill cadence. Recommendation: scheduled weekly until two consecutive clean runs, then before every controller substrate promotion.
9. Define bottom-out action. Recommendation: repeated same blocking condition across three repair attempts becomes `AWAITING-OPERATOR`, with no further self-repair dispatch until human reset.
10. Decide rent/fork boundaries. Recommendation: rent/fork Witness for attestation mechanics where helpful, OneCLI for solo API-credential transport as already ratified, OpenBao for short-lived credentials/SSH CA, and GitHub Apps for forge tokens. Build CE-specific takeover, approval wall, SSHSIG deputy, and host-ops broker because they encode CE authority semantics.

