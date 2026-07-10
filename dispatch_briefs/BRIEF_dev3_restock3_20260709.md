# BRIEF — dev-3 — 2026-07-09 — BATCH 3: client-side approver_ref provenance

Role: **implementer**. Contained COMMIT-ONLY seat (ce-vps-codex). No venv activation needed;
use the installed `ce`.

---

## BORN-A-FOREMAN EXECUTION MODEL

You drive one ticket in this batch. Report **PER-TICKET**: one READY or BLOCKED signal per
unit before your session ends. A BLOCKED unit must record the exact blocker before stopping.

Signal format:

```
READY <branch> <40-char-sha> <carrier-path>
BLOCKED <branch> <one-line reason>
```

**READY/BLOCKED is a PANE SIGNAL ONLY — do NOT commit it as a file in the repo.**

---

## PREFLIGHT PRECONDITION — fetch first

Before starting, run:

```bash
git fetch origin
git log origin/main --oneline | head -5
```

Confirm the head commit is `add00a60e670ccf37e985576e2fd0240b54e4974` (review-pickup dry-run
daemon slice 1, #917) or a later commit. If a newer commit has landed since this brief was
composed, proceed — use the actual current `origin/main` HEAD as the base for the branch.

**Do not touch `.ce/brain/assertions.yaml` in this unit.** The brain-ledger tail is
serialized (PR #918 hermes retirement is open). If any gate in this unit demands a ledger
append, write BLOCKED immediately and stop.

---

## CANDIDATE DROP LOG (controller pre-verification, 2026-07-09)

- **ce-ops#433** (confidentiality scanner: ALL public text surfaces + push-protection guard):
  DROPPED — two of three sub-problems already landed on `origin/main`:
  - Part 1 (scanner coverage extension to all tracked files): landed via PR #738
    (`fix: widen public-repo confidentiality scan to all tracked text files`). Confirmed:
    `public_docs_confidentiality.py` docstring states "every tracked text file" and scans
    all tracked files via git ls-files. No remaining coverage gap.
  - Part 2 (push-protection guard): landed via PR #839 (MERGED 2026-07-06).
  - Part 3 (#369 denylist redo, branch `ce-369-denylist-from-ssot`, head `1661d22d`):
    branch is NOT on the remote (not reachable from VPS contained seat). Blocked for
    this seat. Deferred to controller direct harvest.
  Net: no remaining S-sized, VPS-accessible work for this ticket.

- **ce-ops#442** (key custody: technical seam preventing subagent workers from signing):
  DROPPED — all three implementation options conflict with this seat:
  - Option (a) (separate OS user + sudo wrapper): requires OS-level user creation and
    sudo config; cannot be done from a commit-only VPS seat.
  - Option (b) (PreToolUse hook-check deny): touches `.claude/hooks/ce-pretooluse.sh`,
    which is FROZEN by PR #918 hermes set.
  - Option (c) (OpenBao-held key): M+ scope.
  Net: no viable S-sized implementation path for this seat while #918 is open.

- **ce-ops#427** (stale dev-1 claim from 2026-07-05): A claim file exists for dev-1
  (`.ce/claims/ce-427-approver-ref-provenance.md`, queued 2026-07-05 batch 8, no PR ever
  opened). The ticket is OPEN; no branch `ce-427-approver-ref-provenance` exists on the
  remote; work was never started. Claim is stale. This brief RE-ROUTES #427 to dev-3
  with an updated claim.

**Surviving: ce-ops#427** (client-side approver_ref provenance) — OPEN, wc:S, no PR,
S-sized implementation identified, file-disjoint from all in-flight territories.

---

## DISJOINTNESS ANALYSIS (read before starting)

**Unit files** (approver_ref provenance):
- `validators/creator_engine_validator/schemas/install-answers.schema.yaml` (modify: add optional `approver_ref_provenance` to `ratification_binding` $def)
- `validators/creator_engine_validator/approver_ref_minting.py` (NEW)
- `validators/tests/unit/test_approver_ref_minting.py` (NEW)
- `.ce/changelog/ce-427-approver-ref-provenance.md` (NEW)
- `.ce/pr-manifests/ce-427-approver-ref-provenance.md` (NEW)

**Cross-batch in-flight territories (out-of-bounds — do not touch):**
- dev-4 batch: `validators/creator_engine_validator/forge/integrator_belt.py`,
  `validators/tests/unit/test_integrator_belt.py`, `deploy/daemons/smoke-daemon-container.sh`,
  `validators/tests/integration/test_adoption_merge_group_e2e.py`
- PR #918 hermes path set: `.ce/brain/assertions.yaml`, `.claude/hooks/ce-hook-common.sh`,
  `.claude/hooks/ce-pretooluse.sh`, `.claude/hooks/ce-stop.sh`,
  `deploy/dgx-runsc/run-codex-runsc.sh`, `deploy/vps-runsc/run-vps-runsc.sh`,
  `validators/creator_engine_validator/ce_cli.py`,
  `validators/creator_engine_validator/ce_onboard.py`,
  `validators/tests/unit/test_ce_onboard.py`, `validators/tests/unit/test_ce_onboard_cli.py`,
  `validators/tests/unit/test_dgx_runsc.py`, `validators/tests/unit/test_vps_runsc_launcher.py`,
  `validators/tests/integration/test_claude_hook_pack_stop.py`
- PR #919 path set: `deploy/queue-daemon/launch-queue-daemon.sh`,
  `validators/tests/unit/test_queue_daemon_canary_launch.py`
- PR #920 path set: `deploy/dgx-controller-runsc/provision-standby-surface.sh`,
  `tools/mint-forge-token.py`, `validators/creator_engine_validator/continuity_drill_runtime.py`,
  `validators/tests/unit/test_continuity_drill_cli.py`
- PR #921 path set: `validators/tests/integration/test_release_finalize_integration.py`
- PR #922 path set: `tools/host-ops-broker/**`, `validators/tests/unit/test_host_ops_broker_*`
- dev-1 batch 2 path set: `validators/creator_engine_validator/posture_banner.py`,
  `validators/pyproject.toml`, `validators/tests/unit/test_posture_banner.py`,
  `validators/creator_engine_validator/schemas/identity-registry.schema.yaml`,
  `docs/governance/identity-registry.example.yaml`,
  `validators/tests/unit/test_identity_registry_schema.py`

**Collision verdict:**
- Unit vs dev-4 batch: **CLEAR** — no shared files.
- Unit vs PR #918 hermes paths: **CLEAR** — `ce_cli.py`, `ce_onboard.py` excluded by design;
  `install-answers.schema.yaml` and new `approver_ref_minting.py` are not in the hermes set.
- Unit vs PRs #919-922: **CLEAR** — no shared files.
- Unit vs dev-1 batch 2: **CLEAR** — `install-answers.schema.yaml` ≠ `identity-registry.schema.yaml`.
- `docs/contracts/authoring-a-governed-pr.md` is an evidence_ref in `assertions.yaml` (byte-change
  = pin trip). Do NOT touch it. The approver_ref provenance implementation does NOT require
  modifying that file.
- `validators/creator_engine_validator/_versions.py`: no explicit entry needed — new shared
  modules not listed in V1_RUNTIME or V3_RUNTIME are classified shared by default.

---

## STANDING OBLIGATIONS BLOCK — read this before writing any file

Every unit in this brief MUST deliver ALL of the following. Missing any one item is a
harvest blocker.

1. **Changelog fragment**: `.ce/changelog/<branch>.md` — one short paragraph describing
   what changed and why. No ce-ops# references in the text body (product lens).

2. **Carrier / path-manifest**: `.ce/pr-manifests/<branch>.md` — lists every changed path
   (including the changelog fragment itself). Must contain exactly **one** line of the form:
   ```
   - **Declared work class:** <XS|S|M|L>
   ```
   The carrier slug (filename stem) MUST equal the branch name exactly. Zero ce-ops# refs.

3. **Targeted in-seat tests only**: run only the test files touched by your unit (see each
   unit's acceptance criteria). Full suite execution is prohibited in the seat environment
   (resource limits). The controller preflight on `origin/main` is authoritative for the
   full suite.

**Pre-authorized false-RED classes** (proven in this seat environment — if the ONLY
failures are these gates on files you did NOT touch, note them verbatim and signal READY):
- `control-plane portability` gate on paths outside your diff
- `check-examples` gate failures on paths outside your diff
- `libsodium` gate failures on paths outside your diff

Any failure touching YOUR changed files = fix or BLOCKED. Do not suppress or ignore errors
in your own diff.

**READY/BLOCKED signal is a PANE SIGNAL ONLY — do NOT commit it as a file in the repo.**

---

## UNIT — ce-427-approver-ref-provenance

**Branch:** `ce-427-approver-ref-provenance`
**Worktree:** `/var/tmp/wt-427`
**Work class:** S
**Carrier slug must match branch exactly:** `ce-427-approver-ref-provenance`

### Ticket body (ce-ops#427 — embedded for offline access)

```
Title: [G12] client-side approver_ref provenance: bind ratification gesture
       to client identity

State: OPEN | Labels: triage:ready, wc:S

Parent design: ce-ops#421 / .ce/state/research/CLIENT_TENANT_DEPLOYMENT_DESIGN_20260703.md
                (§6.1 ratification_binding)

## Summary

Per design §6.1 (ratified #421). The ratification_binding.approver_ref is an
opaque digest minted by whoever runs the script; for client-as-Operator to be
structurally true, the gesture must be generated/held by the client identity.
Phase 1 closes this for Mythos specifically; this ticket = the general mechanism.

## Current state

ratification_binding in install-answers.schema.yaml has:
  - ratified_prompt_sha: "^[0-9a-f]{64}$"  (SHA256 of ratified prompt)
  - approver_ref: "^[0-9a-f]{64}$"  (opaque digest standing in for ratifying human)
  - educate_acknowledged: true

The approver_ref is currently an opaque, free-form 64-hex digest. There is
nothing in the schema or tooling that binds it to the client App identity.
Any agent can mint an approver_ref value — the "client-as-Operator" trust
property is assertion-only, not structurally enforced.

## Done-when

1. ratification_binding $def in install-answers.schema.yaml has an optional
   approver_ref_provenance sub-object with at minimum: client_id field (the
   GitHub OAuth client_id of the installing App) and gesture_salt field (a
   hex string used as input to derive the approver_ref).

2. A new module provides mint_approver_ref(client_id, ratified_prompt_sha,
   gesture_salt=None) -> str (64-hex) and
   verify_approver_ref(approver_ref, client_id, ratified_prompt_sha,
   gesture_salt=None) -> bool.

3. Schema backward-compat: existing ratification_binding entries WITHOUT
   provenance still validate (approver_ref_provenance is optional).

4. Schema forward: a ratification_binding WITH provenance validates iff the
   client_id and gesture_salt fields are present.

Work class estimate: S.
```

### Design reference (grounded on `origin/main:add00a60e`)

Read `.ce/state/research/CLIENT_TENANT_DEPLOYMENT_DESIGN_20260703.md` §6.1 before
editing. Key invariants from the design:
- The approver_ref digest is the "human ratification gesture token."
- Binding it to `client_id` means: the digest is derived from `sha256(client_id + ":" + ratified_prompt_sha + ":" + gesture_salt)`.
- This makes it impossible to mint a valid approver_ref for App-A using App-B's credentials.
- Backward compat: existing entries without provenance are tolerated (the governance
  WEAKENING still requires human approval; the provenance sub-object adds auditability).

### Probe before editing

```bash
# PROBE 1: confirm ratification_binding $def exists in install-answers schema
git show origin/main:validators/creator_engine_validator/schemas/install-answers.schema.yaml \
  | grep -n 'ratification_binding'
# Expect: hits at $defs entry + $ref usages

# PROBE 2: confirm approver_ref_provenance field does NOT yet exist
git show origin/main:validators/creator_engine_validator/schemas/install-answers.schema.yaml \
  | grep 'approver_ref_provenance'
# Expect: zero hits

# PROBE 3: confirm minting module does not exist
git show origin/main:validators/creator_engine_validator/approver_ref_minting.py 2>/dev/null \
  && echo "EXISTS — unexpected" || echo "not_found — proceed"
# Expect: not_found

# PROBE 4: confirm docs/contracts/authoring-a-governed-pr.md is out-of-bounds
# (evidence_ref in assertions.yaml — do NOT touch)
# (No action needed; just note: that specific file must not appear in your diff)
```

### Deliverable — three items

#### Item 1: Extend `ratification_binding` in `install-answers.schema.yaml`

The `ratification_binding` `$defs` entry currently has:
```yaml
  ratification_binding:
    type: object
    required: [ratified_prompt_sha, approver_ref, educate_acknowledged]
    additionalProperties: false
    properties:
      ratified_prompt_sha:
        type: string
        pattern: "^[0-9a-f]{64}$"
      approver_ref:
        type: string
        pattern: "^[0-9a-f]{64}$"
      educate_acknowledged:
        type: boolean
        const: true
```

Add the optional `approver_ref_provenance` field. The `additionalProperties: false`
means it MUST be listed in `properties`:

```yaml
  ratification_binding:
    type: object
    required: [ratified_prompt_sha, approver_ref, educate_acknowledged]
    additionalProperties: false
    description: |
      # existing description unchanged #
    properties:
      ratified_prompt_sha:
        type: string
        pattern: "^[0-9a-f]{64}$"
        description: SHA256 of the ratified prompt recording the choice.
      approver_ref:
        type: string
        pattern: "^[0-9a-f]{64}$"
        description: >-
          Opaque digest standing in for the ratifying human. When
          approver_ref_provenance is present, this value MUST equal
          sha256(client_id + ":" + ratified_prompt_sha + ":" + gesture_salt).
      educate_acknowledged:
        type: boolean
        const: true
        description: |
          The educate-first copy was shown and acknowledged; a binding
          without it cannot validate (the file cannot skip education).
      approver_ref_provenance:
        type: object
        required: [client_id]
        additionalProperties: false
        description: >-
          Optional. When present, binds the approver_ref to a specific
          client App identity, making the ratification gesture structurally
          verifiable (not just self-asserted). If omitted, the binding is
          accepted but is not client-identity-bound (legacy compat).
        properties:
          client_id:
            type: string
            minLength: 1
            description: >-
              GitHub OAuth App client_id of the client (tenant App) that
              minted the approver_ref. Non-secret. Used to verify the
              approver_ref derivation.
          gesture_salt:
            type: string
            pattern: "^[0-9a-f]{1,128}$"
            description: >-
              Optional hex salt used as the third component of the
              approver_ref derivation: sha256(client_id + ":" +
              ratified_prompt_sha + ":" + gesture_salt). If omitted,
              gesture_salt is treated as the empty string in derivation.
```

No other changes to `install-answers.schema.yaml`.

#### Item 2: `validators/creator_engine_validator/approver_ref_minting.py` (NEW)

```python
"""Approver-ref minting and verification for client-identity-bound ratification.

Implements the client-side approver_ref derivation: the approver_ref is a
SHA-256 digest of the tuple (client_id, ratified_prompt_sha, gesture_salt).
Binding it to client_id makes it impossible to mint a valid approver_ref for
App-A using App-B's credentials.

This module is shared (no v1/v3-specific imports).
"""
from __future__ import annotations

import hashlib


def mint_approver_ref(
    client_id: str,
    ratified_prompt_sha: str,
    gesture_salt: str | None = None,
) -> str:
    """Return a 64-hex approver_ref bound to the given client identity.

    Args:
        client_id: GitHub OAuth App client_id of the tenant App (non-secret).
        ratified_prompt_sha: 64-hex SHA256 of the ratified prompt.
        gesture_salt: Optional additional hex entropy. If None, treated as "".

    Returns:
        64-hex string (SHA256 of the concatenated components).

    Raises:
        ValueError: if client_id is empty, or ratified_prompt_sha is not 64 hex chars.
    """
    if not client_id:
        raise ValueError("client_id must be non-empty")
    if len(ratified_prompt_sha) != 64 or not all(
        c in "0123456789abcdef" for c in ratified_prompt_sha.lower()
    ):
        raise ValueError(
            f"ratified_prompt_sha must be 64 lowercase hex chars, got: {ratified_prompt_sha!r}"
        )
    salt = gesture_salt or ""
    payload = f"{client_id}:{ratified_prompt_sha.lower()}:{salt}"
    return hashlib.sha256(payload.encode()).hexdigest()


def verify_approver_ref(
    approver_ref: str,
    client_id: str,
    ratified_prompt_sha: str,
    gesture_salt: str | None = None,
) -> bool:
    """Return True iff approver_ref matches the expected derivation.

    Args:
        approver_ref: The 64-hex value to verify.
        client_id: GitHub OAuth App client_id used during minting.
        ratified_prompt_sha: 64-hex SHA256 of the ratified prompt.
        gesture_salt: Optional hex salt used during minting. If None, treated as "".

    Returns:
        True if approver_ref matches mint_approver_ref(client_id, ratified_prompt_sha,
        gesture_salt); False otherwise. Never raises on invalid approver_ref input
        (returns False).
    """
    try:
        expected = mint_approver_ref(client_id, ratified_prompt_sha, gesture_salt)
    except ValueError:
        return False
    # Use constant-time comparison to prevent timing-based information leakage.
    return hmac_compare(approver_ref, expected)


def hmac_compare(a: str, b: str) -> bool:
    """Constant-time string comparison (both must be str, not bytes)."""
    import hmac as _hmac
    return _hmac.compare_digest(
        a.encode() if isinstance(a, str) else a,
        b.encode() if isinstance(b, str) else b,
    )
```

#### Item 3: `validators/tests/unit/test_approver_ref_minting.py` (NEW)

```python
"""Tests for approver_ref minting and verification (ce-ops#427 S-slice)."""
from __future__ import annotations

import pytest

from creator_engine_validator.approver_ref_minting import mint_approver_ref, verify_approver_ref

# A well-formed ratified_prompt_sha fixture (64 lowercase hex chars).
_VALID_SHA = "a" * 64


def test_mint_returns_64_hex_chars():
    ref = mint_approver_ref("Iv23liuJpXXXXXXX", _VALID_SHA)
    assert len(ref) == 64
    assert all(c in "0123456789abcdef" for c in ref)


def test_mint_is_deterministic():
    ref1 = mint_approver_ref("Iv23liuJpXXXXXXX", _VALID_SHA, "deadbeef")
    ref2 = mint_approver_ref("Iv23liuJpXXXXXXX", _VALID_SHA, "deadbeef")
    assert ref1 == ref2


def test_mint_differs_by_client_id():
    ref_a = mint_approver_ref("client-a", _VALID_SHA)
    ref_b = mint_approver_ref("client-b", _VALID_SHA)
    assert ref_a != ref_b


def test_mint_differs_by_prompt_sha():
    ref1 = mint_approver_ref("client-a", "a" * 64)
    ref2 = mint_approver_ref("client-a", "b" * 64)
    assert ref1 != ref2


def test_mint_differs_by_gesture_salt():
    ref_no_salt = mint_approver_ref("client-a", _VALID_SHA)
    ref_with_salt = mint_approver_ref("client-a", _VALID_SHA, "cafebabe")
    assert ref_no_salt != ref_with_salt


def test_mint_raises_on_empty_client_id():
    with pytest.raises(ValueError, match="client_id"):
        mint_approver_ref("", _VALID_SHA)


def test_mint_raises_on_invalid_prompt_sha_length():
    with pytest.raises(ValueError, match="64"):
        mint_approver_ref("client-a", "abc")


def test_verify_returns_true_for_correct_inputs():
    client_id = "Iv23liuJp6OxfCWvwfSl"
    salt = "0011aabb"
    ref = mint_approver_ref(client_id, _VALID_SHA, salt)
    assert verify_approver_ref(ref, client_id, _VALID_SHA, salt) is True


def test_verify_returns_false_for_wrong_client_id():
    ref = mint_approver_ref("real-client", _VALID_SHA, "salt")
    assert verify_approver_ref(ref, "fake-client", _VALID_SHA, "salt") is False


def test_verify_returns_false_for_tampered_ref():
    ref = mint_approver_ref("client-a", _VALID_SHA)
    tampered = "0" * 64
    assert verify_approver_ref(tampered, "client-a", _VALID_SHA) is False


def test_verify_returns_false_on_invalid_prompt_sha():
    """verify_approver_ref must not raise on bad inputs — returns False."""
    assert verify_approver_ref("a" * 64, "client-a", "not-a-sha") is False
```

Add at minimum these 11 test functions. Do not remove or modify any.

### Acceptance criteria

1. `grep 'approver_ref_provenance' validators/creator_engine_validator/schemas/install-answers.schema.yaml`
   returns hits (field definition present).

2. A `ratification_binding` WITHOUT `approver_ref_provenance` still validates (backward compat).
   Probe: write a quick Python snippet that validates an existing-shape binding against the schema.

3. A `ratification_binding` WITH `approver_ref_provenance.client_id = "Iv23liuJp6OxfCWvwfSl"`
   validates.

4. `pytest validators/tests/unit/test_approver_ref_minting.py -v` — all 11+ tests green.

5. `ce validate-pr --profile contained-seat` green on the diff.

6. Changelog `.ce/changelog/ce-427-approver-ref-provenance.md` present, no ce-ops# refs in body.

7. Carrier `.ce/pr-manifests/ce-427-approver-ref-provenance.md` present with slug
   `ce-427-approver-ref-provenance`, all changed paths listed, exactly one
   `- **Declared work class:** S` line.

### Hard constraints

- Do NOT touch `docs/contracts/authoring-a-governed-pr.md` — it is an evidence_ref in
  `assertions.yaml`; a byte-change there trips a pin.
- Do NOT touch `.ce/brain/assertions.yaml`.
- Do NOT touch `validators/creator_engine_validator/ce_cli.py` (PR #918 frozen).
- Do NOT touch `validators/creator_engine_validator/ce_onboard.py` (PR #918 frozen).
- Do NOT modify `validators/creator_engine_validator/_versions.py` — new shared modules
  do not need an explicit entry (they are shared by default).
- The schema change MUST preserve `additionalProperties: false` (add field to `properties`,
  not by relaxing the constraint).
- ZERO ce-ops# references in changelog or carrier body text.
- Commit early and often — the worktree is in RAM (`/var/tmp`); do not accumulate more than
  a few hundred lines of changes between commits.

### STOP LINE

No pushes, no PRs, no gate acts. Only these paths:

```
validators/creator_engine_validator/schemas/install-answers.schema.yaml
validators/creator_engine_validator/approver_ref_minting.py
validators/tests/unit/test_approver_ref_minting.py
.ce/changelog/ce-427-approver-ref-provenance.md
.ce/pr-manifests/ce-427-approver-ref-provenance.md
```

Absolute stop-lines — do NOT touch:
- `.ce/brain/assertions.yaml`
- `docs/contracts/authoring-a-governed-pr.md` (evidence_ref — pin trip)
- `validators/creator_engine_validator/ce_cli.py` (PR #918)
- `validators/creator_engine_validator/ce_onboard.py` (PR #918)
- `validators/creator_engine_validator/_versions.py`
- `.claude/hooks/**` (PR #918)
- `deploy/dgx-runsc/run-codex-runsc.sh`, `deploy/vps-runsc/run-vps-runsc.sh` (PR #918)
- `deploy/daemons/smoke-daemon-container.sh` (dev-4 in-flight)
- Any file in dev-1 batch 2 or dev-4 territory (listed in Disjointness Analysis)

Carrier: slug `ce-427-approver-ref-provenance` exactly; every changed path listed; exactly
ONE `- **Declared work class:** S` line.

### READY / BLOCKED signal (pane only — do NOT commit as a file)

**When DONE — emit to pane:**
```
STATUS: READY
BRANCH: ce-427-approver-ref-provenance
COMMIT: <HEAD SHA after final commit>
CARRIER: .ce/pr-manifests/ce-427-approver-ref-provenance.md
PROBE_PROVENANCE_FIELD: <zero_hits — proceeded | already_present — unexpected>
PROBE_MINTING_MODULE: <not_found — proceeded | EXISTS — unexpected>
SCHEMA_BACKWARD_COMPAT: <validated | issue — describe>
VALIDATE_PR: GREEN
GATE_NOISE: <"none" or verbatim text of false-RED gates on untouched files>
READY ce-427-approver-ref-provenance <sha> .ce/pr-manifests/ce-427-approver-ref-provenance.md
```

**When BLOCKED — emit to pane:**
```
STATUS: BLOCKED
BRANCH: ce-427-approver-ref-provenance
BLOCKER: <one-sentence description>
CONTEXT: <full context, file/line/error>
BLOCKED ce-427-approver-ref-provenance <reason>
```
