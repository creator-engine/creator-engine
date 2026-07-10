# BRIEF — dev-3 — 2026-07-09 — BATCH 2: host-ops broker v1 arming blockers

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

- **ce-ops#459** (Client-CI: harden SHA256SUMS signature-chain verification): DROPPED —
  already landed on `origin/main` via PR #861 (`ce-459-sha256sums-chain-hardening`, merged
  2026-07-06). Verified: `.ce/changelog/ce-459-sha256sums-chain-hardening.md` and
  `.ce/pr-manifests/ce-459-sha256sums-chain-hardening.md` are present on
  `origin/main:add00a60e`. No work remaining.

- **ce-ops#453** (Guard hash-pinned signed artifacts + surface skipped tests in
  contained-seat preflight): DROPPED — Part B (skip-count transparency) already landed via
  PR #831 (MERGED 2026-07-05). Part A (brief-composition guard in `validate-pr`) remains
  open but: (a) work class "story" — over-scope for a single contained-seat unit;
  (b) `pr_preflight.py` changes carry high probability of needing `assertions.yaml`
  evidence_ref appends, blocked by PR #918 tail lock; (c) no safely-scoped slice can be
  extracted without assertions.yaml risk. Deferred until PR #918 is merged.

---

## DISJOINTNESS ANALYSIS (read before starting)

**Unit C files** (broker arming blockers):
- `tools/host-ops-broker/host_ops_broker/audit.py` (modify: remove "value" substring)
- `tools/host-ops-broker/host_ops_broker/config.py` (modify: add allowlist field + resolution methods)
- `tools/host-ops-broker/host_ops_broker/broker.py` (modify: fix _resolve_target for two verbs)
- `validators/tests/unit/test_host_ops_broker_audit.py` (extend: one new test function)
- `validators/tests/unit/test_host_ops_broker_config.py` (NEW: tests for new config methods)
- `.ce/changelog/ce-504-broker-arming-blockers.md` (new)
- `.ce/pr-manifests/ce-504-broker-arming-blockers.md` (new)
- `.ce/wt-504/READY` or `.ce/wt-504/BLOCKED` (signal)

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
  `validators/tests/integration/test_claude_hook_pack_stop.py`, and related docs
- Harvested ce-515: `validators/tests/integration/test_release_finalize_integration.py`
- Harvested ce-516: `.github/scripts/ceops_autoclose.py`,
  `.github/workflows/ce-ops-autoclose.yml`,
  `validators/tests/unit/test_p2_acceptance_evidence.py`

**Collision verdict:**
- Unit C vs dev-4 batch: **CLEAR** — no shared files.
- Unit C vs PR #918 hermes paths: **CLEAR** — no shared files.
- Unit C vs harvested ce-515/ce-516: **CLEAR** — no shared files.
- `assertions.yaml` is out-of-bounds for this unit.

**Brain-ledger gate (pre-authorized):**
`test_host_ops_broker_audit.py` has no count-pin in `assertions.yaml`. The new
`test_host_ops_broker_config.py` is a test file (not a validator package production module);
no `_versions.py` entry is required — `tools/host-ops-broker/` is standalone. No
`assertions.yaml` append required. Gate clear.

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

4. **Signal file**: write `.ce/wt-<ticket>/READY` or `.ce/wt-<ticket>/BLOCKED` as the
   FINAL commit on your branch before stopping.

**Pre-authorized false-RED classes** (proven in this seat environment — if the ONLY
failures are these gates on files you did NOT touch, note them verbatim and signal READY):
- `control-plane portability` gate on paths outside your diff
- `check-examples` gate failures on paths outside your diff
- `libsodium` gate failures on paths outside your diff

Any failure touching YOUR changed files = fix or BLOCKED. Do not suppress or ignore errors
in your own diff.

---

## UNIT C — host-ops broker v1 slice-2 arming blockers

**Branch:** `ce-504-broker-arming-blockers`
**Worktree:** `/var/tmp/wt-504`
**Work class:** S
**Carrier slug must match branch exactly:** `ce-504-broker-arming-blockers`

### Ticket body (ce-ops#504 — embedded for offline access)

```
Title: broker v1 slice-2 arming blockers: audit false-positive, missing image allowlist,
       dead prefix config (PR #898 review, 2026-07-08)

State: OPEN | Labels: bug, triage:ready, wc:S, ws:containment

Parent: ce-ops#482 (host-ops broker v1)
Ref: creator-engine/creator-engine PR #898 (security review, 2026-07-08)
Design doc: docs/design/host-ops-broker-v1.md

## Summary

Slice 1 of the host-ops broker merged with three MAJOR latent findings. They are currently
unreachable because the deferred verb handlers return 'refused', but they are hard
preconditions for enabling those handlers in slice 2. All three must be resolved before
arming production adapters.

---

## MAJOR 1. Audit false-positive: "value" in _FORBIDDEN_KEY_SUBSTRINGS (audit.py:18)

Symptom: Any adapter dict containing a key whose name includes the substring "value" (e.g.
default_value, exit_value, return_value) will trigger AuditSecretLeak on the final audit
write. The operation succeeds but is reported as degraded/failed, and no audit record is
written.

Impact: Silent audit gap — successful operations become invisible to the audit trail, and
callers receive a false failure signal. Violates the acceptance bar in #482 (every
invocation must produce a structured audit event).

Root cause: _FORBIDDEN_KEY_SUBSTRINGS uses substring matching on key names rather than
exact-key matching combined with token-shape checks on values. The string "value" is too
broad.

Proposed fix: Remove "value" from _FORBIDDEN_KEY_SUBSTRINGS. The value-shape check via
_TOKEN_SHAPE already catches actual token-shaped values. Alternatively, move to exact
forbidden key names plus value-shape check.

---

## MAJOR 2. Missing image/registry allowlist for run-ephemeral-container
           (config.py / broker.py:188)

Symptom: BrokerConfig has no field for an allowed image registry or digest list.
_resolve_target in broker.py:188 only validates the task name; it does not check whether
the requested image comes from a CE-owned registry or matches a digest-pinned allowlist.

Impact: When run-ephemeral-container handler is enabled, any image reference that passes
task-name validation could be run. The design threat model explicitly requires CE-owned
digest-pinned images from allowed registries.

Proposed fix: Add a container_image_allowlist: list[str] field to BrokerConfig (registry
prefix + optional digest pin). Add a resolve_container_image method that rejects requests
whose image does not match the allowlist.

---

## MAJOR 3. Dead state_root_prefixes config — prepare-owned-state-root ignores it
           (broker.py:184)

Symptom: BrokerConfig exposes state_root_prefixes as a config field, but _resolve_target
for prepare-owned-state-root only consults the exact-match state_roots mapping. The prefix
allowlist is never evaluated.

Impact: A path that matches a declared prefix but not an exact entry is silently rejected.
The config is misleading and the resolution logic is inconsistent.

Proposed fix: Align _resolve_target to evaluate state_root_prefixes as a secondary
resolution pass. Add a resolve_state_root config method for testability.
```

### Problem statement (grounded in code on `origin/main:add00a60e`)

**MAJOR 1** — `tools/host-ops-broker/host_ops_broker/audit.py`, line 18:
```python
_FORBIDDEN_KEY_SUBSTRINGS = ("token", "secret", "pem", "private_key", "app_key", "password", "value")
```
The substring `"value"` matches any key whose name contains `value`, including benign fields
like `default_value`, `exit_value`, `return_value`. The `_TOKEN_SHAPE` regex already catches
actual token-shaped values via the value-path check in `assert_secret_free`. The key-name
check with `"value"` is redundant and produces false positives.

**MAJOR 2** — `tools/host-ops-broker/host_ops_broker/config.py`: `BrokerConfig` has no
`container_image_allowlist` field. In `broker.py` at line 188:
```python
if request.verb == "run-ephemeral-container" and request.params["task"] in self.config.maintenance_tasks:
    return {"target_ref": f"task:{request.params['task']}", "unit": None}
```
No registry/allowlist check is performed on `request.params["image"]` (which is
digest-pinned by `verb_schema.py` but not registry-scoped by the broker).

**MAJOR 3** — `broker.py`, line 184:
```python
if request.verb == "prepare-owned-state-root" and request.params["root_name"] in self.config.state_roots:
```
`self.config.state_root_prefixes` (line 26 of `config.py`) exists as a parsed config field
but is never consulted here. A `root_name` matching only by prefix is silently refused
rather than resolved.

### Probe before editing

Run these probes and note results in your READY signal:

```bash
# PROBE 1: confirm "value" still in forbidden list
git show origin/main:tools/host-ops-broker/host_ops_broker/audit.py | grep -n '"value"'
# Expect: hit at line 18

# PROBE 2: confirm no container_image_allowlist in config
git show origin/main:tools/host-ops-broker/host_ops_broker/config.py | grep -n 'image_allow'
# Expect: zero hits

# PROBE 3: confirm prefix not evaluated in _resolve_target
git show origin/main:tools/host-ops-broker/host_ops_broker/broker.py | \
  grep -n 'state_root_prefix\|startswith.*prefix'
# Expect: zero hits (state_root_prefixes is never used in broker.py)

# PROBE 4: confirm verb_schema already validates digest-pin on image field
git show origin/main:tools/host-ops-broker/host_ops_broker/verb_schema.py | \
  grep -n '_DIGEST_IMAGE\|image.*sha256'
# Expect: hits confirming digest-pin validation already present
```

For any item where the probe shows it was already resolved (unlikely), note
`PROBE_ITEM<N>: already_resolved` in the READY signal.

### Deliverable — three items across three files + two test files

#### Item 1: Remove "value" from `_FORBIDDEN_KEY_SUBSTRINGS` in `audit.py`

```python
# tools/host-ops-broker/host_ops_broker/audit.py — line 18
# BEFORE:
_FORBIDDEN_KEY_SUBSTRINGS = ("token", "secret", "pem", "private_key", "app_key", "password", "value")
# AFTER:
_FORBIDDEN_KEY_SUBSTRINGS = ("token", "secret", "pem", "private_key", "app_key", "password")
```

No other changes to `audit.py`.

#### Item 2: Add `container_image_allowlist` + resolution method to `config.py`

Add to `BrokerConfig` dataclass (after `maintenance_tasks`, before `rate_limit_overrides`):
```python
container_image_allowlist: tuple[str, ...] = ()
```

Add to `from_mapping`, after the `maintenance_tasks` line:
```python
container_image_allowlist = tuple(
    _str_list(raw.get("container_image_allowlist", []), "container_image_allowlist")
)
```

Add `container_image_allowlist=container_image_allowlist` to the `cls(...)` call in
`from_mapping`.

Add resolution method to `BrokerConfig` (alongside `resolve_unit`, `resolve_daemon`):
```python
def resolve_container_image(self, image: str) -> str:
    """Return image if it starts with a CE-owned registry prefix; raise BrokerConfigError otherwise."""
    if not self.container_image_allowlist:
        raise BrokerConfigError(
            "container_image_allowlist is empty — no images are CE-owned"
        )
    if any(image.startswith(prefix) for prefix in self.container_image_allowlist):
        return image
    raise BrokerConfigError(
        f"image {image!r} does not match any CE-owned registry in container_image_allowlist"
    )
```

#### Item 3: Add `resolve_state_root` method to `config.py`; fix prefix in `broker.py`

Add resolution method to `BrokerConfig`:
```python
def resolve_state_root(self, root_name: str) -> str:
    """Return root_name if it is CE-owned (exact match or prefix); raise BrokerConfigError otherwise."""
    if root_name in self.state_roots or any(
        root_name.startswith(p) for p in self.state_root_prefixes
    ):
        return root_name
    raise BrokerConfigError(
        f"state root {root_name!r} is not CE-owned (no exact match and no prefix match)"
    )
```

In `broker.py`, replace the `prepare-owned-state-root` branch in `_resolve_target`:
```python
# BEFORE:
if request.verb == "prepare-owned-state-root" and request.params["root_name"] in self.config.state_roots:
    return {"target_ref": f"state-root:{request.params['root_name']}", "unit": None}
# AFTER:
if request.verb == "prepare-owned-state-root":
    root_name = str(request.params["root_name"])
    self.config.resolve_state_root(root_name)  # raises BrokerConfigError if not CE-owned
    return {"target_ref": f"state-root:{root_name}", "unit": None}
```

Add image allowlist check in the `run-ephemeral-container` branch in `_resolve_target`:
```python
# BEFORE:
if request.verb == "run-ephemeral-container" and request.params["task"] in self.config.maintenance_tasks:
    return {"target_ref": f"task:{request.params['task']}", "unit": None}
# AFTER:
if request.verb == "run-ephemeral-container" and request.params["task"] in self.config.maintenance_tasks:
    image = str(request.params.get("image", ""))
    self.config.resolve_container_image(image)  # raises BrokerConfigError if not CE-owned registry
    return {"target_ref": f"task:{request.params['task']}", "unit": None}
```

#### Tests in `test_host_ops_broker_audit.py` (extend existing file)

Add this test function after the existing tests. Import pattern and `_record()` helper are
already present in that file — do not duplicate them:

```python
def test_value_key_does_not_trigger_false_positive(tmp_path):
    """Keys containing 'value' as a substring must not trigger AuditSecretLeak."""
    path = tmp_path / "audit.jsonl"
    rec = _record(
        params_redacted={
            "default_value": "summary",
            "exit_value": 0,
            "return_value": "ok",
        }
    )
    # Must not raise — "value" in a key name is not a credential indicator
    append_audit(path, rec)
    assert path.is_file()
```

#### Tests in `validators/tests/unit/test_host_ops_broker_config.py` (NEW file)

Create this file. It tests the two new resolution methods on `BrokerConfig`:

```python
"""Tests for BrokerConfig resolution methods added in ce-ops#504."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
HOST_OPS_ROOT = ROOT / "tools" / "host-ops-broker"
if str(HOST_OPS_ROOT) not in sys.path:
    sys.path.insert(0, str(HOST_OPS_ROOT))

from host_ops_broker.config import BrokerConfig, BrokerConfigError


def _minimal_raw(**overrides):
    raw = {
        "audit_log_path": "/tmp/test-audit.jsonl",
        "kill_switch_path": "/tmp/test-ks.json",
        "broker_identity": "test-broker",
    }
    raw.update(overrides)
    return raw


# ---------- container_image_allowlist ----------

def test_config_loads_container_image_allowlist():
    cfg = BrokerConfig.from_mapping(
        _minimal_raw(container_image_allowlist=["ghcr.io/creator-engine/", "registry.local/ce-"])
    )
    assert cfg.container_image_allowlist == ("ghcr.io/creator-engine/", "registry.local/ce-")


def test_config_default_container_image_allowlist_is_empty():
    cfg = BrokerConfig.from_mapping(_minimal_raw())
    assert cfg.container_image_allowlist == ()


def test_resolve_container_image_accepts_allowed_prefix():
    cfg = BrokerConfig.from_mapping(
        _minimal_raw(container_image_allowlist=["ghcr.io/creator-engine/"])
    )
    image = "ghcr.io/creator-engine/ce-worker@sha256:" + "a" * 64
    assert cfg.resolve_container_image(image) == image


def test_resolve_container_image_rejects_disallowed_registry():
    cfg = BrokerConfig.from_mapping(
        _minimal_raw(container_image_allowlist=["ghcr.io/creator-engine/"])
    )
    image = "docker.io/randomuser/image@sha256:" + "b" * 64
    with pytest.raises(BrokerConfigError, match="not.*CE-owned registry"):
        cfg.resolve_container_image(image)


def test_resolve_container_image_rejects_all_when_allowlist_empty():
    cfg = BrokerConfig.from_mapping(_minimal_raw())
    image = "ghcr.io/creator-engine/ce-worker@sha256:" + "c" * 64
    with pytest.raises(BrokerConfigError, match="allowlist is empty"):
        cfg.resolve_container_image(image)


# ---------- resolve_state_root (prefix support) ----------

def test_resolve_state_root_accepts_exact_match():
    cfg = BrokerConfig.from_mapping(
        _minimal_raw(state_roots={"ce-work": "/var/ce/work"})
    )
    assert cfg.resolve_state_root("ce-work") == "ce-work"


def test_resolve_state_root_accepts_prefix_match():
    cfg = BrokerConfig.from_mapping(
        _minimal_raw(state_root_prefixes=["ce-tenant-"])
    )
    assert cfg.resolve_state_root("ce-tenant-abc123") == "ce-tenant-abc123"


def test_resolve_state_root_rejects_unknown_root():
    cfg = BrokerConfig.from_mapping(
        _minimal_raw(
            state_roots={"ce-work": "/var/ce/work"},
            state_root_prefixes=["ce-tenant-"],
        )
    )
    with pytest.raises(BrokerConfigError, match="not CE-owned"):
        cfg.resolve_state_root("untrusted-root")


def test_resolve_state_root_prefix_does_not_match_partial_stem():
    """Prefix 'ce-tenant-' must not match 'ce-tenant' (missing trailing separator)."""
    cfg = BrokerConfig.from_mapping(
        _minimal_raw(state_root_prefixes=["ce-tenant-"])
    )
    with pytest.raises(BrokerConfigError):
        cfg.resolve_state_root("ce-tenant")
```

### Acceptance criteria

1. `grep -n '"value"' tools/host-ops-broker/host_ops_broker/audit.py` returns zero hits
   inside `_FORBIDDEN_KEY_SUBSTRINGS` (or `PROBE_ITEM1: already_resolved`).

2. `grep -n 'container_image_allowlist' tools/host-ops-broker/host_ops_broker/config.py`
   returns at least two hits (field definition + from_mapping parse line).

3. `grep -n 'state_root_prefixes\|resolve_state_root' tools/host-ops-broker/host_ops_broker/broker.py`
   returns a hit confirming prefix resolution is wired (or `PROBE_ITEM3: already_resolved`).

4. `pytest validators/tests/unit/test_host_ops_broker_audit.py -v` passes including the
   new `test_value_key_does_not_trigger_false_positive` test.

5. `pytest validators/tests/unit/test_host_ops_broker_config.py -v` passes all 9 tests.

6. `ce validate-pr --profile contained-seat` green on the diff.

### Hard constraints

- Do NOT touch `.ce/brain/assertions.yaml`.
- Do NOT add a `_versions.py` entry — this unit adds only test files and modifies existing
  `tools/host-ops-broker/` modules (standalone package, not under
  `validators/creator_engine_validator/`).
- Do NOT change the existing parametrized test in `test_host_ops_broker_audit.py` —
  only append the new test function.
- Do NOT modify `verb_schema.py` — the digest-pin validation for `run-ephemeral-container`
  is already correct there; this unit adds the registry-scope check in config/broker only.
- Do NOT implement the deferred verb handlers — only add the allowlist/prefix resolution
  infrastructure. Handlers still return `"refused"`.
- ZERO ce-ops# references in changelog or carrier body text.
- Commit early and often — the worktree is in RAM (`/var/tmp`); do not accumulate more than
  a few hundred lines of changes between commits.

### STOP LINE (Unit C)

No pushes, no PRs, no gate acts. Only these paths:

```
tools/host-ops-broker/host_ops_broker/audit.py
tools/host-ops-broker/host_ops_broker/config.py
tools/host-ops-broker/host_ops_broker/broker.py
validators/tests/unit/test_host_ops_broker_audit.py
validators/tests/unit/test_host_ops_broker_config.py
.ce/changelog/ce-504-broker-arming-blockers.md
.ce/pr-manifests/ce-504-broker-arming-blockers.md
.ce/wt-504/READY
.ce/wt-504/BLOCKED
```

Carrier: slug `ce-504-broker-arming-blockers` exactly; every changed path listed; exactly
ONE `- **Declared work class:** S` line.

### READY / BLOCKED signals (Unit C)

**When DONE — write `.ce/wt-504/READY` then emit:**
```
STATUS: READY
BRANCH: ce-504-broker-arming-blockers
COMMIT: <HEAD SHA after final commit>
CARRIER: .ce/pr-manifests/ce-504-broker-arming-blockers.md
PROBE_ITEM1: <open|already_resolved>
PROBE_ITEM2: <open|already_resolved>
PROBE_ITEM3: <open|already_resolved>
PROBE_ITEM4_VERB_SCHEMA: <digest-pin already present|missing>
ITEMS_ADDRESSED: <count of items actually changed>
VALIDATE_PR: GREEN
GATE_NOISE: <"none" or verbatim text of false-RED gates on untouched files>
READY ce-504-broker-arming-blockers <sha> .ce/pr-manifests/ce-504-broker-arming-blockers.md
```
Commit the signal file as the FINAL commit on the branch before stopping.

**When BLOCKED — write `.ce/wt-504/BLOCKED` then emit:**
```
STATUS: BLOCKED
BRANCH: ce-504-broker-arming-blockers
BLOCKER: <one-sentence description>
CONTEXT: <full context, file/line/error>
BLOCKED ce-504-broker-arming-blockers <reason>
```
