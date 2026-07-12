# Governed review-acting spawn provider contract (M2)

## Status and boundary

This is a **design for ratification**, not an implementation or arming
decision. It fills the provider gap following merged #969's default-OFF
review-pickup acting chain, #970's injected-facts ready-attestation reducer,
and #984/M4's pure `RatifierCandidate` queue. Presently, an absent or
unconfigured provider records attempts and ultimately `retry_exhausted`; it
does not launch a reviewer. That fail-closed behaviour remains until a
controller ratifies and deploys a follow-on carrier.

The provider may obtain a review and return a finding. It may not approve,
merge, sign, ratify, discover ambient credentials, run validation as evidence,
or turn a finding into a gate decision. In particular, it never calls M4
`drive_attestation`: only the controller constructs `ReadyAttestationFacts`
from its own observations and invokes that pure reducer.

## 1. Immutable PR-head worktree

**Decision.** The caller supplies a configured, allowlisted remote and repo,
PR number, immutable 40-hex `head_sha`, base SHA, and carrier facts. The
provider fetches only `head_sha` from that trusted remote, requires
`rev-parse FETCH_HEAD` to equal that SHA, then creates a detached worktree at
the object. It verifies detached `HEAD`, base ancestry, declared carrier
path-set/digest, and clean `git status --porcelain` before reviewer start. The
reviewer mount is read-only and never checks out a movable branch.

For public repositories the allowlisted public remote is sufficient. For a
private repository a controller-provided broker fetches and passes a sealed
local object/worktree reference; the reviewer receives no forge credential.
The provider rechecks object, detached `HEAD`, and claim tuple immediately
before exec and after collection. A mismatch is `STALE_HEAD`, never a retry
against another ref. This conserves `(repo, pr_number, head_sha, base_sha,
carrier_digest)` across the operation and prevents TOCTOU ref movement.

**Alternatives rejected.** `refs/pull/*/head`, branch names, a shared checkout,
reviewer-side cloning, or an unverified caller path are movable, writable, or
over-authorized and are therefore refused.

## 2. Distinct reviewer authority envelope

**Decision.** A request names author and reviewer identities. The provider
refuses equality, absence, or a reviewer outside the controller-supplied
governed reviewer set. The reviewer gets a role-shaped read-only checkout plus
read-only policy/docs inputs and a private bounded result pipe. It has no forge
token, SSH key, signing key, controller key, approval, merge, ratification, or
deployment authority. Claim and result bind the immutable tuple, reviewer ID,
and provider-generated nonce.

The ledger records non-secret reviewer runtime identity/version, request
digest, result digest, exit class, timestamps, and tuple. It never records
tokens, environment values, full command lines, or unbounded output. A finding
is advisory provenance only: `COMMENT` and `REQUEST_CHANGES` are accepted;
`APPROVE` is invalid.

**Alternatives rejected.** Author self-review, mutable shared seats, reviewer
forge credentials, and treating a finding as an approval breach conflict,
confidentiality, or authority boundaries.

## 3. Venue, roots, claims, and lifetime

**Decision.** The controller supplies explicit absolute roots for provider
ledger/state, ephemeral worktrees, bounded result files, and retained evidence.
No root is inferred from `$HOME`, cwd, systemd environment, or repo config.
Names are collision-free:
`review-provider/<repo-hash>/<pr>/<head-sha>/<attempt>/<nonce>`; every created
path is canonicalized and required to remain below its supplied root.

An atomic active-work claim keyed by `(repo, pr_number, head_sha)` is acquired
before fetch and holds owner, reviewer, nonce, attempt, expiry, and request
digest. A durable ledger record is appended before spawn. Restart folds
claim/ledger state, resumes only the exact tuple, and refuses corrupt or
ambiguous state. Concurrency is controller-supplied and bounded; default is
zero (OFF). Roots and capacity enter through a controller-owned adapter, not
ambient authority.

**Alternatives rejected.** PR-number-only names, best-effort lock files,
unbounded workers, and ambient roots permit collisions, races, or privilege
leakage.

## 4. Synchronous findings protocol

The subprocess interface is an argv vector from a fixed executable and fixed
argument positions; no shell, interpolation, or `eval` is allowed. Request and
response are UTF-8 JSON objects, version `1`, one object each, on dedicated
files/pipes. Reviewer stdout is reserved for response; stderr is diagnostic
only. Caps: request 16 KiB, response 64 KiB, stderr 16 KiB, summary 4 KiB,
and each finding detail 32 KiB. Over-limit output is refused and may be
truncated only in a separate diagnostic record, never parsed as valid.

Request schema:

```json
{"version":1,"request_id":"opaque-nonce","repo":"owner/repo","pr_number":123,"head_sha":"40-lower-hex","base_sha":"40-lower-hex","carrier":{"path_count":3,"sha256":"64-lower-hex"},"author":"author-id","reviewer":"reviewer-id","worktree":"provider-private-read-only-path"}
```

Response schema:

```json
{"version":1,"request_id":"opaque-nonce","repo":"owner/repo","pr_number":123,"head_sha":"40-lower-hex","author":"author-id","reviewer":"reviewer-id","verdict":"COMMENT|REQUEST_CHANGES","summary":"bounded text","findings":[{"path":"relative/path","line":1,"detail":"bounded text"}]}
```

Only exit `0` is normal. Provider outcome codes are `SPAWN_REFUSED`,
`SPAWN_FAILED`, `TIMEOUT`, `STALE_HEAD`, `MALFORMED_RESULT`, `PARTIAL_OUTPUT`,
`REVIEWER_EXIT_NONZERO`, and `UNCERTAIN_COMMENT`. Timeout uses the defined
termination sequence and preserves evidence; it is never a comment. Nonzero
exit, invalid UTF-8/schema/bindings, `APPROVE`, multiple JSON objects, extra
stdout, or partial writes fail closed. Stderr cannot alter a valid response.

**Alternatives rejected.** Free-form stdout, shell templates, permissive
verdicts, and parsing after timeout permit injection or ambiguous provenance.

## 5. Cleanup and conservation

**Decision.** A successfully validated response creates an immutable evidence
record; temporary worktree/result data are deleted after configured retention.
Spawn refusal, timeout, malformed/partial output, stale head, or nonzero exit
first creates a durable terminal-attempt record and retains worktree/result/
stderr metadata for operator evidence, subject to bounded retention and
confidentiality redaction. Cleanup is idempotent: every record retains tuple
and nonce, and retries create a new attempt while preserving prior records.

If a future controller adapter posts a `COMMENT` and loses its response, it
records `UNCERTAIN_COMMENT` before retry. It must consult controller-owned
submission evidence; it never posts again merely because transport failed.
Existing #969 retry limits remain authoritative: exhausted retries preserve
terminal `retry_exhausted` and need operator recovery, not automatic relaunch.
On restart, expired/ambiguous active claims are reconciled only against durable
records; unresolved state is refused and surfaced to the operator.

**Alternatives rejected.** Immediate evidence deletion, at-least-once posting,
silent restart cleanup, and automatic retry after exhaustion lose evidence or
permit duplicates.

## 6. M4 persistence handoff

**Decision.** The controller-owned adapter, not the provider, constructs and
persists `RatifierCandidate(pr_number, head_sha, branch, enqueued_at,
attestation_state, last_checked_at, checked_count)`. It obtains branch and
enqueue timestamp from authoritative PR/head observation, writes under an
exclusive durable queue lock, and deduplicates `(pr_number, head_sha)`. A new
head supersedes an old candidate; same-head updates retain earliest authoritative
enqueue time and merge only monotonic evidence.

Validated reviewer output is attached as advisory finding provenance. It may
keep a candidate pending or surface it to an operator, but cannot invent a
validator result, validator SHA, checks, timestamps, or
`ReadyAttestationFacts`. Only controller observation builds those facts and
only controller authority calls `drive_attestation`. The provider has no queue
write lock or M4 import/actuation privilege.

**Alternatives rejected.** Provider-owned queue state, reviewer-created
candidates, or mapping `COMMENT` to `attested_green` fabricate gate evidence.

## 7. Deployment boundary

**Decision.** The repository adapter owns schema validation, injected roots,
claim/ledger protocol, and pure result handoff. A separately packaged host
helper owns sandbox/process lifecycle only; it cannot discover repository,
reviewer, credentials, or ratifier state. Installation, systemd wiring, and
environment variables are a later controller-only deployment proposal. The
feature is default OFF: no service/timer starts it, and live arming requires
explicit controller capacity, roots, allowlist, monitoring, and rollback.

Rollback disarms new spawns, waits or terminates bounded live children,
preserves evidence/claims, and then removes deployment wiring without deleting
ledger history. The controller watches active-claim age, spawn
refusal/failure/timeout/malformed/uncertain counts, retained-evidence pressure,
retry exhaustion, queue handoff lag, and capacity. An operator—not the
provider—owns alerts and recovery.

**Alternatives rejected.** A repo module managing systemd, an always-on timer,
an ambient-env helper, and self-monitoring/self-restart couple deployment and
authority unsafely.

## State flow and failure handling

```text
pickup item -> exact-head claim -> verified detached worktree -> spawn
    -> bounded JSON collect -> COMMENT / REQUEST_CHANGES -> controller adapter
    -> caller-owned pending RatifierCandidate -> controller-only attestation
```

| Event | Provider action | Durable result / next state |
| --- | --- | --- |
| unconfigured/refused spawn | no reviewer process | attempt then `spawner_unconfigured`; bounded retry applies |
| spawn failure | retain diagnostic metadata | `SPAWN_FAILED`; retry only exact claim/head |
| timeout | terminate and retain bounded evidence | `TIMEOUT`; no finding/comment |
| malformed result | refuse parse | `MALFORMED_RESULT`/`PARTIAL_OUTPUT`; no handoff |
| restart | fold exact claim and ledger | resume exact tuple or refuse ambiguity |
| uncertain comment | never duplicate submission | `UNCERTAIN_COMMENT`; controller/operator reconciliation |
| stale head | refuse before/after reviewer | `STALE_HEAD`; new head gets a new claim |
| exhausted retries | no relaunch | preserve `retry_exhausted`; operator recovery |
| valid COMMENT | attach provenance only | controller may persist pending candidate |
| valid REQUEST_CHANGES | attach provenance only | no ratifier-ready inference |

## Proposed follow-on build carrier — non-ratified until design approval

The following is a **candidate only**, not permission to edit/deploy:

```text
validators/creator_engine_validator/forge/review_spawn_provider.py
validators/creator_engine_validator/forge/review_pickup.py
validators/creator_engine_validator/forge/review_acting.py
validators/creator_engine_validator/forge/ratifier_queue.py
validators/creator_engine_validator/v3_cli.py
validators/tests/unit/test_review_spawn_provider.py
validators/tests/unit/test_review_acting.py
validators/tests/unit/test_ratifier_queue.py
deploy/systemd/ce-review-spawn-provider.service
deploy/systemd/ce-review-spawn-provider.env.example
docs/operations/review-spawn-provider.md
```

Before a build carrier, ratification must freeze protocol/schema, root
ownership, private-repo broker interface, retention, reviewer identity source,
and deployment/monitoring owner. Its manifest must be generated from its final
path set; this candidate list is non-ratified.

## Acceptance matrix

| Acceptance case | Required evidence |
| --- | --- |
| immutable source | fetch SHA, detached HEAD/base/carrier checks; dirty or moved ref refuses |
| distinct reviewer | author/reviewer equality and unmanaged reviewer refuse; reviewer has read-only/no-forge envelope |
| protocol integrity | version/schema/nonce/head mismatch, `APPROVE`, extra stdout, malformed and oversize output refuse |
| process safety | argv-only execution; timeout/nonzero/partial output preserves bounded evidence without a finding |
| lifecycle | collision, duplicate claim, restart, cleanup and retained evidence are deterministic/idempotent |
| submission conservation | uncertain submission never duplicates; exhausted retry never relaunches |
| M4 boundary | provider cannot write queue/facts or call attestation; caller dedups exact candidate tuple |
| default-OFF deployment | absent arming starts nothing; disarm/rollback preserves ledger and terminates bounded work |
| confidentiality | logs/evidence exclude credentials and redact bounded diagnostics; private fetch hides credential from reviewer |

## Threat model

| Threat | Control |
| --- | --- |
| movable or substituted PR ref | remote allowlist, SHA fetch verification, detached HEAD, before/after recheck |
| reviewer self-dealing | identity inequality and governed-reviewer allowlist |
| credential or host escape | read-only role mount, no forge/signing/controller credentials, explicit roots |
| shell or JSON injection | argv-only execution, fixed schema, size caps, strict enum and one-object stdout |
| duplicate/lost comment | durable attempt/submission record, uncertain state, controller reconciliation |
| restart/claim race | atomic tuple claim, nonce/attempt binding, ledger fold, bounded concurrency |
| fabricated gate evidence | controller-only facts/attestation and provider-free M4 write authority |
| evidence/disk leak | bounded diagnostics, retention, idempotent cleanup, evidence-pressure monitoring |

## Open ratification decisions

1. Which controller component supplies private-repository objects and what
   authenticated transport audit record it retains.
2. Exact retention/capacity for worktrees, result evidence, stderr, terminal
   attempts, including disk-pressure refusal.
3. The authoritative governed-reviewer identity registry and its rotation/
   revocation effect on active claims.
4. Timeout/termination values and whether sandbox attestation is mandatory for
   every reviewer invocation.
5. The controller durable queue backend/lock primitive and the operator SLO
   for uncertain submissions, retry exhaustion, and evidence pressure.
6. Ownership of production service, alert routing, deployment change, and
   recovery runbook; this design assigns none.

## Explicit stop lines

- No code, tests, runtime configuration, generated reference, systemd unit,
  credential, forge action, review submission, or live deployment is authorized
  by this carrier.
- No reviewer may approve, merge, sign, ratify, construct validation facts, or
  call `drive_attestation`.
- Default remains OFF until open decisions and a separate build/deployment
  carrier receive controller ratification.
