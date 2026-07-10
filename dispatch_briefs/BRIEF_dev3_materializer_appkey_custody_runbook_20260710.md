# DISPATCH — dev-3 — 2026-07-10 — unit: materializer App-key custody runbook (slice c) — class S
Role: implementer foreman. Signal: `READY-FOR-HARVEST ce-materializer-appkey-custody-runbook <full-40-hex-sha>`
or `BLOCKED ce-materializer-appkey-custody-runbook <one-line-reason>`.
Branch `ce-materializer-appkey-custody-runbook` off freshly fetched origin/main OR LATER
(>= efd82b0320425278c283beeeabf06324b84a97de — the ADR-0015 merge; fetch first, the ADR is NOT
in older trees). Worktree /var/tmp/wt-ce-materializer-appkey-custody-runbook. Standing preflight
directive: run `ce validate-pr --profile contained-seat` if your environment can; else focused
tests + BLOCKED(env) per protocol. PRE-SIGNAL CHECKLIST: focused confidentiality test green (see
Task 5). QUEUE NOTE: take this unit AFTER completing your current unit (ce-523c).

## Context (embedded)

**What the materializer is.** Read `docs/decisions/ADR-0015-materializer-arming-credential-lease.md`
first (git fetch origin, then `git show origin/main:docs/decisions/ADR-0015-materializer-arming-credential-lease.md`).
When armed, the materializer polls origin/main first-parent history for pending brain-append
intent files under `.ce/brain/append-intents/<branch-slug>.yaml`, acquires a singleton lease,
reads the live ledger tail from `.ce/brain/assertions.yaml`, and builds deterministic typed
records binding each to its source merge commit, intent SHA-256, and branch slug. It pushes a
single direct commit to main with a compare-and-swap parent check; every failure mode enters an
explicit HELD state with a 30-minute closeout window before hard failure. Authority to push
directly to main is Operator-armed and does not exist until the pre-arming slices land.

**ADR-0015 decisions that constrain custody — extract the exact decided text from the ADR and
embed it in the runbook's reference section:**
- Q2 (credential delivery): vault-signer per-call-fetch. App private key stored in OpenBao KV v2;
  the daemon fetches it per signing call (never persisted to disk), pipes to `openssl` via
  `/dev/fd/<N>`, zeroes the in-memory copy. Fail-closed: any vault read error raises a signer
  error before signing; no disk-path fallback. Implementation reference: `vault_signer` in
  `tools/egress-broker/egress_broker/minter.py`.
- Q4 (lease topology): the existing `MaterializerLease`/`daemon_lease.DaemonLease` local
  filesystem lease bound to the current single-host deployment (`MaterializerLease` in
  `validators/creator_engine_validator/brain_intent_materializer.py` wraps
  `daemon_lease.acquire("brain-append", ...)`, lease root `<state-root>/leases/`). Explicit
  single-host decision; revisit trigger = any move to a multi-instance materializer (design open
  question 4 in `docs/design/ce-491-optiona-merge-intent.md`).

**Role-identity convention.** ADR-0013 names `decision_makers: ["ce-gate-architect"]`; ADR-0014
names `ce-runtime-architect`. All records in this runbook name ROLES (`ce-materializer-architect`,
`ce-operator`, `ce-release-signer`) — never seat logins, deployment usernames, or host identifiers.

## Unit

1. Fetch origin/main; read ADR-0015; extract exact Q2/Q4 decision text — these quotes anchor the
   runbook's authority claims.
2. Author `docs/operations/MATERIALIZER_APPKEY_CUSTODY_RUNBOOK.md` following the house format of
   `docs/operations/SINGLETON_DAEMON_REDEPLOY_RUNBOOK.md` (H1 title, H2 sections). Sections:
   - **Purpose and Scope** — one paragraph: governs the lifecycle of the GitHub App private key
     the armed materializer uses to mint short-lived installation tokens for direct pushes to
     main. Reference ADR-0015 Q2/Q4 by doc path only.
   - **Credential Lifecycle** — Storage: OpenBao KV v2 at the path declared in the daemon
     env-file (`CE_MATERIALIZER_KEY_VAULT_PATH`); env-file holds vault address + mount/path,
     never the key value. Per-call fetch: key fetched at signing time only; never written to any
     file, logged, or held across calls; daemon config carries `private_key_env` (an env-var
     NAME resolving to the vault path reference) per `MaterializerConfig`. Rotation: `ce-operator`
     replaces the key in OpenBao; daemon picks up the new value on the next signing call, no
     restart. Revocation: `ce-operator` revokes the App installation token and the OpenBao secret
     version; daemon enters HELD on the next signing attempt and pages. Break-glass: only
     `ce-operator`, through the approved secret channel documented in
     `docs/devops/openbao-operator-bringup.md`; no agent or worker role may access the raw PEM.
   - **Authority Matrix (by ROLE)** — table: `ce-operator` = store/rotate/revoke/break-glass;
     `ce-materializer-architect` = design + review lease/credential changes; materializer daemon
     role = read the vault path reference from env + request per-call fetch only. Explicitly:
     worker roles (`ce-implementer`, `ce-reviewer`) never hold, touch, or reference the App
     private key or its vault path VALUE. The key never appears in PRs, transcripts, prompts, or
     changelog fragments.
   - **Non-Authorities** — workers never sign; the daemon never holds the key across calls; no
     seat identity, host name, or key value in any tracked file; `private_key_env` carries an
     env-var name only.
   - **Failure and Recovery** — vault read error → signer error → HELD for the affected intent,
     30-minute window before hard failure (see `docs/design/ce-491-optiona-merge-intent.md`);
     recovery: `ce-operator` resolves vault access, clears HELD via the materializer's documented
     recovery path. Lease conflict: `DaemonLeaseStale`/`DaemonLeaseHeld` — follow
     `playbooks/controller/runbooks/conveyor-daemon-stuck-lease.md`. Broken ledger hash chain:
     Operator-only recovery.
3. Register in the operations debt ratchet: add exactly
   `"docs/operations/MATERIALIZER_APPKEY_CUSTODY_RUNBOOK.md",` to the
   `KNOWN_OPERATIONS_EXCEPTIONS` frozenset in
   `validators/creator_engine_validator/public_docs_confidentiality.py`, preserving sort order
   (the same way `SINGLETON_DAEMON_REDEPLOY_RUNBOOK.md` was registered).
4. Dual-format: `docs/operations/` has no HTML counterpart in the site index (only `docs/guide/`
   and `docs/security/` do) — the .md is the only artifact. No HTML emission.
5. Run the focused confidentiality test before signaling:
   `python -m pytest validators/tests/unit/test_public_docs_confidentiality.py::test_tracked_text_files_contain_no_new_confidential_or_internal_references -q`
   Fix any flagged violation before proceeding.

## Files (allowed writes)

- `docs/operations/MATERIALIZER_APPKEY_CUSTODY_RUNBOOK.md` — NEW
- `validators/creator_engine_validator/public_docs_confidentiality.py` — ratchet entry ONLY
- `.ce/changelog/ce-materializer-appkey-custody-runbook.md` — changelog fragment, kind: docs,
  scope: materializer credential custody
- `.ce/pr-manifests/ce-materializer-appkey-custody-runbook.md` — carrier (slug=branch) with
  exactly `- **Declared work class:** S`

Product lens throughout. This is a PUBLIC doc: zero internal ticket refs, zero seat/host
identifiers, zero key material — pointer-to-vault-path only.

## Stop lines

Do NOT flip `ARMING_ENABLED` (stays False in every pre-arming slice). Do NOT edit
`brain_intent_materializer.py` (Unit A), `deploy/materializer/`, or
`deploy/singleton-redeploy/redeploy-singleton.sh` (Unit B). No key value, vault token, or PEM
content anywhere. No push, no sign, no merge. `.github/**`, `forge/**`, `checks/**`,
`pr_preflight.py`, all other in-flight modules, `.ce/brain/assertions.yaml`, brain ledger.

## Signal

After the confidentiality test is green and all four files are committed on
`ce-materializer-appkey-custody-runbook`:
`READY-FOR-HARVEST ce-materializer-appkey-custody-runbook <full-40-hex-sha>`

**In-seat validation note:** use the absolute path `/workspace/creator-engine/.venv/bin/ce` and
`/workspace/creator-engine/.venv/bin/python` — bare `ce` does not resolve in the contained seat.
