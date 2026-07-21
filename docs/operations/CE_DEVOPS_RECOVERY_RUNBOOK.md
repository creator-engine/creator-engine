# CE DevOps Recovery Runbook

**Status**: Governed recovery seed.
**Scope**: Evidence-first recovery of seat, credential, broker, interpreter, and
worker-host symptoms. This runbook does not grant signing, approval, merge,
credential minting, gate-surface, or unratified deployment authority.

## 1. Seat Context Exhaustion

### Symptom

A seat reports that its context is full or cannot continue coherently, while its
session remains responsive.

### Diagnostic

Save a concise handoff state, then distinguish context pressure from process
failure. A responsive session is not evidence that it needs relaunching.

### Instrument

Use `/clear` or `/compact` in the existing healthy seat. Do not use `codex
resume` for this case: it preserves context. After the reset, run a trivial
child process from the same harness context.

### Verification

The trivial child completes and the seat can report its renewed state. If it
does not complete after the reset, record the failure as process breakage and
use the canonical launcher only through its approved recovery route.

## 2. Silent Credential Expiry

### Symptom

Source-host actions that previously worked fail without a clear local credential
change.

### Diagnostic

The token-liveness probe is interim controller-local scaffolding, not versioned
repository tooling. Observe the headers and exit-code convention of an
authenticated API call with:

```bash
gh api user -i
```

The script-absent durable contract is:

- Exit `0` means every authentication call succeeded and no warning threshold
  was crossed. `NOT-REPORTED` metadata may be probe-blind and is never health
  evidence.
- Exit `1` means credential expiry is at or under 21 days, inclusive; rotation
  is required before lapse.
- Exit `2` means the credential is rejected, missing, or expired. Treat the
  approval identity as gate-down.

When the expiry header is absent, including for classic PATs and some App
tokens, the probe is blind for that credential. The Operator must verify expiry
in the provider UI rather than infer health. Do not diagnose an authentication
refusal or expiry indication as a repository, package, or broker failure first.

### Instrument

Report the header and exit-code evidence to the Operator. Minting, replacement,
or rotation remains Operator-only. Do not copy a token between roles or invent
a credential fallback. Productizing the probe into versioned repository tooling
is the tracked T5 exit condition.

### Verification

After the Operator-provided replacement route completes, repeat the
authenticated API call and confirm exit `0`, a live identity, and no exposed
credential value. Where expiry is header-blind, retain the Operator's provider
UI verification instead of treating `NOT-REPORTED` as evidence of health.

## 3. Missing or Crashed Egress Broker

### Symptom

A contained seat cannot perform its permitted source-host egress, or broker
health is absent.

### Diagnostic

Use the `ce-egress-broker` deployment pattern. Inspect the live container and
the broker service/socket health. Read the observed peer UID/GID from that live
container or its authoritative runtime record; never infer it from a numbering
sequence or reuse an identity from another seat.

### Instrument

Use only the Operator-ratified broker deployment or repair route for the
observed target. Preserve existing policy and credential boundaries; a broker
restart or redeploy is not permission to change its peer policy.

### Verification

Confirm the service and socket are healthy, the live peer identity matches the
configured expectation, and a no-op push canary succeeds under the existing
least-privilege policy. Retain value-free results only.

## 4. Wrong-Interpreter False Missing Module

### Symptom

A validator command says a module is missing even though the dependency is
installed for the repository validator environment.

### Diagnostic

Confirm the interpreter selected by `CE_VALIDATOR_PYTHON` and the validator
module path before changing packages. A bare `python3` may select a different
environment and create a false missing-module diagnosis.

### Instrument

Invoke validator commands through the dependency interpreter and validator
module path, for example:

```bash
PYTHONPATH=validators "$CE_VALIDATOR_PYTHON" -m creator_engine_validator --list-checks
```

Never use bare `python3` as the validator interpreter.

### Verification

The same command resolves the expected module through
`CE_VALIDATOR_PYTHON`; no package installation or environment mutation was
needed to correct the diagnosis.

## 5. DGX Receipt Tree-Identity Blocker

### Symptom

Validation receipt minting refuses because the mounted tree identity cannot be
accepted.

### Diagnostic

Treat this as a receipt tree-identity control, not as a lint failure or an
invitation to clean state blindly.

### Instrument

Follow [Worker-Host Readiness](./WORKER_HOST_READINESS.md), especially its DGX
receipt/tree-identity procedure. That procedure is the sole detailed recovery
source for this blocker.

### Verification

Use the evidence and clean, classified-tree receipt verification required by
that procedure. Do not duplicate, weaken, or bypass its control here.
