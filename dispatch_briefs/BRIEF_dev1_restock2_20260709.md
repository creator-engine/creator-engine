# BRIEF — dev-1 — 2026-07-09 — BATCH 2: posture banner + identity-registry schema slice

Role: **implementer**. SELF-PUSH seat (dev-1 VPS host seat — codex TUI in tmux, repo at
`~/creator-engine`, owns forge identity, self-push capable, full validate-pr capable).
Open PRs **NOT as drafts** — ready-for-review from the start.

---

## BORN-A-FOREMAN EXECUTION MODEL

Drive **two units** sequentially (A then B). Report PER-UNIT: one PR-or-BLOCKED signal per
unit before your session ends.

Signal format:

```
PR <number> <branch>
BLOCKED <branch> <one-line reason>
```

A BLOCKED unit must record the exact blocker before stopping. Each unit is an independent
branch; do NOT cross-commit.

---

## PREFLIGHT PRECONDITION — fetch first

Before starting ANY unit, run:

```bash
git fetch origin
git log origin/main --oneline | head -5
```

Confirm the head commit is `add00a60e670ccf37e985576e2fd0240b54e4974` (review-pickup
dry-run daemon slice 1, PR #917) or a later commit. If a newer commit has landed, proceed —
use the actual current `origin/main` HEAD as the base for all branches.

Auth for all gh operations:
```bash
set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT
```

**Do not touch `.ce/brain/assertions.yaml` in any unit.** PR #918 hermes retirement holds
the ledger exclusively. If any gate demands a ledger append, write BLOCKED immediately.

---

## CANDIDATE DROP LOG (controller pre-verification, 2026-07-09)

No drops for dev-1 this batch. Both units survive verification:

- **ce-ops#478** ([P0] Controller posture banner): OPEN, wc:S, no existing PR. Ticket body
  confirms banner command is P0 arc (#471). Scope-adjusted: does NOT add a `ce` subcommand
  (that would touch `ce_cli.py`, frozen by PR #918); instead implements a standalone
  `ce-posture-banner` entry point. Dependencies on Ring-0 runtime and broker are satisfied
  by env-var + socket-probe approach (no wiring into launch flow needed for S-slice).

- **ce-ops#470** (Infra-identity SSOT auto-recall): OPEN, wc:S, no existing PR. Territory
  is three sub-problems (a) schema extension, (b) recall path, (c) precedence rule. Unit B
  is **sliced to sub-problem (a) + (c) only** — schema extension + precedence-rule header
  + example update. Sub-problem (b) (`ce identity lookup` CLI subcommand) is DEFERRED:
  `ce_cli.py` is frozen by PR #918; recall path will land post-#918 as a follow-on unit.
  Done-when is explicit below.

---

## DISJOINTNESS ANALYSIS (read before starting)

**Unit A files** (posture banner):
- `validators/creator_engine_validator/posture_banner.py` (NEW)
- `validators/pyproject.toml` (add `ce-posture-banner` entry in `[project.scripts]`)
- `validators/tests/unit/test_posture_banner.py` (NEW)
- `.ce/changelog/ce-478-posture-banner.md` (NEW)
- `.ce/pr-manifests/ce-478-posture-banner.md` (NEW)

**Unit B files** (identity registry schema slice):
- `validators/creator_engine_validator/schemas/identity-registry.schema.yaml` (modify)
- `docs/governance/identity-registry.example.yaml` (modify)
- `validators/tests/unit/test_identity_registry_schema.py` (extend)
- `.ce/changelog/ce-470-infra-identity-schema.md` (NEW)
- `.ce/pr-manifests/ce-470-infra-identity-schema.md` (NEW)

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
- dev-3 this batch: `validators/creator_engine_validator/schemas/install-answers.schema.yaml`,
  `validators/creator_engine_validator/approver_ref_minting.py`,
  `validators/tests/unit/test_approver_ref_minting.py`

**Collision verdict:**
- Unit A vs Unit B: **CLEAR** — no shared files.
- Unit A vs hermes set: **CLEAR** — `ce_cli.py` excluded by design; `posture_banner.py` is new.
- Unit A vs dev-4/PRs #919-922: **CLEAR**.
- Unit B vs hermes set: **CLEAR** — schema file and example file not in hermes set.
- Unit B vs dev-3: **CLEAR** — different schema files (`identity-registry` vs `install-answers`).
- `validators/pyproject.toml` (Unit A): not in any frozen or in-flight path set. Safe.
- `assertions.yaml` is out-of-bounds for all units; no evidence_ref listed in
  `assertions.yaml` overlaps Unit A or Unit B paths (confirmed: evidence_refs are
  `probe:*`, `.github/workflows/validate.yml`, `docs/contracts/authoring-a-governed-pr.md`,
  `docs/architecture/work-claim-locks.md`, `.ce/brain/notes/deterministic-citations.md`).

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

3. **Full validate-pr**: dev-1 is a host seat, not resource-limited. Run full
   `ce validate-pr` before self-push; it must be GREEN (or all RED items explained as
   pre-authorized noise on untouched paths — note verbatim under `GATE_NOISE`).

**Pre-authorized false-RED classes** (proven in this seat environment — if the ONLY
failures are these gates on files you did NOT touch, note them verbatim and signal READY):
- `control-plane portability` gate on paths outside your diff
- `check-examples` gate failures on paths outside your diff
- `libsodium` gate failures on paths outside your diff

Any failure touching YOUR changed files = fix or BLOCKED. Do not suppress or ignore errors
in your own diff.

**READY/BLOCKED signal is a PANE SIGNAL ONLY — do NOT commit it as a file in the repo.**

---

## UNIT A — ce-478-posture-banner

**Branch:** `ce-478-posture-banner`
**Worktree:** `~/creator-engine-ce-478-posture-banner` (off `origin/main`)
**Work class:** S
**Carrier slug must match branch exactly:** `ce-478-posture-banner`

### Worktree setup

```bash
git fetch origin
git worktree add ~/creator-engine-ce-478-posture-banner -b ce-478-posture-banner origin/main
cd ~/creator-engine-ce-478-posture-banner
```

---

### Ticket body (ce-ops#478 — embedded for offline access)

```
Title: [P0] Controller posture banner

State: OPEN | Labels: triage:ready, wc:S
Parent program: ce-ops#471 (P0 arc, ratified 2026-07-06)

## Summary

A single deterministic banner command that prints the full posture of a running
controller so that the Operator and continuity tools have a machine-readable ground
truth at any point, including during takeover.

## Acceptance bar

The banner command prints all of the following fields:

| Field | Description |
| --- | --- |
| role | e.g. controller, foreman, worker |
| harness | claude, codex, or harness identifier |
| launch_mode | how the session was launched (governed, raw, etc.) |
| ring0_confirmed | Ring-0 harness validation passed (bool) |
| ring1_active | Ring-1 managed hook active (bool) |
| ring2_closeout_support | Ring-2 / closeout hook available (bool) |
| credential_scrub_status | credential scrub result from launch validator |
| remote_control_status | disabled, brokered, enabled-supervisory-only, etc. |
| approval_wall_armed | approval-wall daemon reachable and armed (bool) |
| signing_deputy_status | unavailable, interim-ce-signer, openbao-backed, etc. |
| allowed_posture | read-only, foreman, gate-capable |

- Banner output is included verbatim in ce takeover evidence packet.
- Banner is emitted on every governed controller launch and on every takeover completion.
- --json flag emits machine-readable form suitable for automation.

## Dependencies

- ce-ops#477 (ce takeover verb — consumes banner output)
- Ring-0 harness runtime (provides confirmation status)
- Host-ops broker (provides remote_control_status and daemon reachability)

## Notes

Usability cost: low.
Safety gain: medium-high — removes ambiguity about current posture during incidents.
```

### This S-slice scope

Implement the standalone `ce-posture-banner` command as a new module; wire via
`validators/pyproject.toml` console_scripts entry. The integration of the banner into
`ce launch` / `ce takeover` command flow is **deferred** (requires `ce_cli.py` — frozen by
PR #918). This unit ships the runnable, testable banner; the wiring into the launch flow
follows post-#918 as a follow-on unit.

### Probe before editing

```bash
# PROBE 1: confirm posture_banner module does not yet exist
git show origin/main:validators/creator_engine_validator/posture_banner.py 2>/dev/null \
  && echo "EXISTS — unexpected" || echo "not_found — proceed"
# Expect: not_found

# PROBE 2: confirm ce_cli.py is frozen (must NOT be in your diff)
git show origin/main:validators/creator_engine_validator/ce_cli.py | grep -c 'def main'
# Expect: 1 — file exists; do NOT touch it

# PROBE 3: confirm [project.scripts] section in pyproject.toml
grep -n 'project.scripts' validators/pyproject.toml
# Expect: hit at [project.scripts] line — add entry there, do not create a new section
```

### Deliverable

#### `validators/creator_engine_validator/posture_banner.py` (NEW)

Implement a `PostureBanner` class and a `main()` entry point.

**Field resolution order for each posture field (first non-None wins):**

| Field | Env var | Fallback |
| --- | --- | --- |
| `role` | `CE_ROLE` | `"unknown"` |
| `harness` | `CE_HARNESS` | `"unknown"` |
| `launch_mode` | `CE_LAUNCH_MODE` | `"unknown"` |
| `ring0_confirmed` | `CE_RING0_CONFIRMED` ("1"=true) | `False` |
| `ring1_active` | `CE_RING1_ACTIVE` ("1"=true) | `False` |
| `ring2_closeout_support` | `CE_RING2_CLOSEOUT_SUPPORT` ("1"=true) | `False` |
| `credential_scrub_status` | `CE_CREDENTIAL_SCRUB_STATUS` | `"unknown"` |
| `remote_control_status` | `CE_REMOTE_CONTROL_STATUS` | `"unknown"` |
| `approval_wall_armed` | `CE_APPROVAL_WALL_ARMED` ("1"=true) | socket probe → False |
| `signing_deputy_status` | `CE_SIGNING_DEPUTY_STATUS` | `"unknown"` |
| `allowed_posture` | `CE_ALLOWED_POSTURE` | `"unknown"` |

For `approval_wall_armed` socket probe: check if
`os.environ.get("CE_BROKER_SOCKET_PATH")` points to a reachable Unix domain socket
(non-blocking `socket.connect_ex` with 0.1 s timeout). If reachable, set `True`; if
missing or unreachable, set `False`. Always falls back to env var override if set.

**CLI interface:**

```python
# entry point: ce-posture-banner
def main(argv=None):
    """
    ce-posture-banner [--json]
    
    Without --json: prints human-readable posture table (one field per line: KEY: VALUE).
    With --json: prints JSON object with all 11 posture fields.
    Exits 0 always (diagnostic tool; does not block on unknown values).
    """
```

The module must be importable as
`from creator_engine_validator.posture_banner import PostureBanner, get_posture` for
use by other modules without launching the CLI.

`get_posture(env=None) -> dict` — accepts an optional dict override of `os.environ`
(used in tests to inject fake env without monkeypatching).

**Do NOT import** `ce_cli`, `ce_onboard`, or any v1/v3-specific module. The module
is `shared` by `_versions.py` classification (no explicit `_versions.py` edit needed —
any module not listed in V1_RUNTIME or V3_RUNTIME is shared by default).

#### `validators/pyproject.toml` (modify)

In the `[project.scripts]` section (alongside `creator-engine-validator`, `ce`, `cev3`),
add exactly ONE new line:

```toml
ce-posture-banner = "creator_engine_validator.posture_banner:main"
```

No other changes to `pyproject.toml`.

#### `validators/tests/unit/test_posture_banner.py` (NEW)

```python
"""Tests for the controller posture banner (ce-ops#478 S-slice)."""
from __future__ import annotations

from creator_engine_validator.posture_banner import get_posture, PostureBanner


REQUIRED_FIELDS = {
    "role", "harness", "launch_mode", "ring0_confirmed", "ring1_active",
    "ring2_closeout_support", "credential_scrub_status", "remote_control_status",
    "approval_wall_armed", "signing_deputy_status", "allowed_posture",
}


def test_get_posture_returns_all_required_fields():
    posture = get_posture(env={})
    assert REQUIRED_FIELDS == set(posture.keys()), (
        f"Missing fields: {REQUIRED_FIELDS - set(posture.keys())}; "
        f"Extra fields: {set(posture.keys()) - REQUIRED_FIELDS}"
    )


def test_get_posture_defaults_when_env_empty():
    posture = get_posture(env={})
    assert posture["role"] == "unknown"
    assert posture["harness"] == "unknown"
    assert posture["launch_mode"] == "unknown"
    assert posture["ring0_confirmed"] is False
    assert posture["ring1_active"] is False
    assert posture["ring2_closeout_support"] is False
    assert posture["credential_scrub_status"] == "unknown"
    assert posture["remote_control_status"] == "unknown"
    assert posture["approval_wall_armed"] is False
    assert posture["signing_deputy_status"] == "unknown"
    assert posture["allowed_posture"] == "unknown"


def test_get_posture_reads_string_fields_from_env():
    env = {
        "CE_ROLE": "controller",
        "CE_HARNESS": "claude",
        "CE_LAUNCH_MODE": "governed",
        "CE_CREDENTIAL_SCRUB_STATUS": "clean",
        "CE_REMOTE_CONTROL_STATUS": "brokered",
        "CE_SIGNING_DEPUTY_STATUS": "interim-ce-signer",
        "CE_ALLOWED_POSTURE": "gate-capable",
    }
    posture = get_posture(env=env)
    assert posture["role"] == "controller"
    assert posture["harness"] == "claude"
    assert posture["launch_mode"] == "governed"
    assert posture["credential_scrub_status"] == "clean"
    assert posture["remote_control_status"] == "brokered"
    assert posture["signing_deputy_status"] == "interim-ce-signer"
    assert posture["allowed_posture"] == "gate-capable"


def test_get_posture_reads_bool_fields_from_env():
    env = {
        "CE_RING0_CONFIRMED": "1",
        "CE_RING1_ACTIVE": "1",
        "CE_RING2_CLOSEOUT_SUPPORT": "1",
        "CE_APPROVAL_WALL_ARMED": "1",
    }
    posture = get_posture(env=env)
    assert posture["ring0_confirmed"] is True
    assert posture["ring1_active"] is True
    assert posture["ring2_closeout_support"] is True
    assert posture["approval_wall_armed"] is True


def test_get_posture_bool_false_on_zero_value():
    env = {
        "CE_RING0_CONFIRMED": "0",
        "CE_RING1_ACTIVE": "0",
        "CE_RING2_CLOSEOUT_SUPPORT": "0",
        "CE_APPROVAL_WALL_ARMED": "0",
    }
    posture = get_posture(env=env)
    assert posture["ring0_confirmed"] is False
    assert posture["ring1_active"] is False
    assert posture["ring2_closeout_support"] is False
    assert posture["approval_wall_armed"] is False


def test_posture_banner_collect_all_required_fields():
    banner = PostureBanner(env={})
    posture = banner.collect()
    assert REQUIRED_FIELDS == set(posture.keys())
```

Add at minimum these 6 test functions. Additional edge-case tests are welcome; do not
remove any.

### Acceptance criteria

1. `python -c "from creator_engine_validator.posture_banner import get_posture; print(get_posture({}))"` prints all 11 required fields.

2. `pytest validators/tests/unit/test_posture_banner.py -v` — all 6+ tests green.

3. `grep 'ce-posture-banner' validators/pyproject.toml` returns a hit in `[project.scripts]`.

4. `grep -r 'from.*ce_cli\|from.*ce_onboard\|import.*ce_cli\|import.*ce_onboard' validators/creator_engine_validator/posture_banner.py` returns zero hits.

5. Full `ce validate-pr` GREEN on the working tree.

6. PR opened (non-draft) with `- **Declared work class:** S` in body; PR title:
   `feat(posture): add ce-posture-banner standalone command (S-slice 1)`.

### Hard constraints

- Do NOT touch `validators/creator_engine_validator/ce_cli.py` (PR #918 frozen).
- Do NOT touch any file in the hermes set (listed in Disjointness Analysis).
- Do NOT modify `_versions.py` — new shared modules do not need an explicit entry.
- Integration of banner into `ce launch` / `ce takeover` is DEFERRED. Do not wire
  the launch flow. This unit only ships the runnable command.
- ZERO ce-ops# references in changelog or carrier body text.

### Stop line (Unit A)

No edits outside these paths:

```
validators/creator_engine_validator/posture_banner.py
validators/pyproject.toml
validators/tests/unit/test_posture_banner.py
.ce/changelog/ce-478-posture-banner.md
.ce/pr-manifests/ce-478-posture-banner.md
```

Absolute stop-lines — do NOT touch:
- `.ce/brain/assertions.yaml`
- `validators/creator_engine_validator/ce_cli.py`
- `validators/creator_engine_validator/ce_onboard.py`
- `validators/creator_engine_validator/_versions.py`
- `deploy/dgx-runsc/run-codex-runsc.sh`, `deploy/vps-runsc/run-vps-runsc.sh`
- `.claude/hooks/**`
- `deploy/daemons/smoke-daemon-container.sh` (dev-4 in-flight)
- Any file in dev-3, dev-4, or PR #919–922 territory

### PR-open signal (Unit A)

After opening the PR, emit to pane:

```
STATUS: DONE
BRANCH: ce-478-posture-banner
PR: <number> ce-478-posture-banner
PROBE_POSTURE_MODULE: <not_found — proceeded | EXISTS — unexpected>
VALIDATE_PR: GREEN
GATE_NOISE: <"none" or verbatim text of false-RED gates on untouched files>
PR <number> ce-478-posture-banner
```

Do NOT commit a READY file to the repo. The pane signal is the only signal.

---

## UNIT B — ce-470-infra-identity-schema (S-slice 1: schema + example + precedence rule)

**Branch:** `ce-470-infra-identity-schema`
**Worktree:** `~/creator-engine-ce-470-infra-identity-schema` (off `origin/main`)
**Work class:** S
**Carrier slug must match branch exactly:** `ce-470-infra-identity-schema`
**Slice scope:** sub-problems (a) schema extension + (c) precedence-rule codification only.
Sub-problem (b) recall path / `ce identity lookup` CLI is DEFERRED (ce_cli.py frozen).

### Worktree setup

```bash
git fetch origin
git worktree add ~/creator-engine-ce-470-infra-identity-schema -b ce-470-infra-identity-schema origin/main
cd ~/creator-engine-ce-470-infra-identity-schema
```

---

### Ticket body (ce-ops#470 — embedded for offline access, abridged)

```
Title: Infra-identity SSOT auto-recall: registry entries surfaced to controllers at
       launch/on-demand (no env-file spelunking)

State: OPEN | Labels: triage:ready, wc:S, ws:secret-identity

## Summary (Operator directive 2026-07-06)

Infra identifiers (concretely: mythos-ce GitHub App — App ID 4103119,
Client ID Iv23liuJp6OxfCWvwfSl, installation 141552951 account-wide on
chmod735-dor, PEM pointer ~/.ce-keys/mythos-ce.2026-06-20.private-key.pem)
must live in a queryable SSOT with an auto-recall layer, not only in
scattered env files.

## Registry gap: what is missing today

`infra/identity-registry.yaml` (ce-ops repo, ratified SSOT, PR#308) has NO
`apps:` entry for any tenant-side App. The `apps:` entries only cover the four
dev-seat forge Apps.

## Scope — three sub-problems

(a) Registry completeness: extend the public schema
    (`validators/creator_engine_validator/schemas/identity-registry.schema.yaml`)
    to accommodate tenant-installed Apps. Add: app_name, client_id, tenant_scope.
    Populate `docs/governance/identity-registry.example.yaml` with mythos-ce entry
    (non-secret values; PEM pointer only — never key material).
    
(b) Recall path: `ce identity lookup <app-name-or-app-id>` sub-command.
    [DEFERRED — ce_cli.py frozen by PR #918]

(c) Precedence rule: codify in the public schema header and example file:
    registry WINS over env files and MEMORY.md. When an infra identifier is
    present in the registry, that value is authoritative.

## References

- PR#308 (registry populated; parent of the gap)
- ce-ops#137 (CE identity registry SSOT, OPEN; schema + roster)
- ce-ops#406 (brain recall surface; coupling point for recall-at-launch, later)
```

### Done-when (this slice)

This unit is complete when ALL of:

1. `validators/creator_engine_validator/schemas/identity-registry.schema.yaml`:
   - The `app` `$defs` entry has optional fields: `app_name` (string), `client_id`
     (string, GitHub OAuth client ID format), `tenant_scope` (enum:
     `selected-repos|account-wide|TODO_VERIFY`)
   - Schema header `description` block contains the precedence-rule statement (see
     deliverable below)

2. `docs/governance/identity-registry.example.yaml` includes a mythos-ce App entry
   with non-secret fields populated (app_id, client_id, installation_id, tenant_scope,
   app_name, pem_custody pointer), plus a `# PRECEDENCE:` comment block.

3. `pytest validators/tests/unit/test_identity_registry_schema.py -v` passes, including
   new tenant-App validation test cases added by this unit.

4. Full `ce validate-pr` GREEN.

5. PR opened (non-draft) with `- **Declared work class:** S` in body.

Sub-problem (b) (`ce identity lookup` CLI) is explicitly DEFERRED and excluded from
Done-when. Record it in the PR body: "CLI recall path (`ce identity lookup`) deferred
to post-PR-918 follow-on unit."

### Probe before editing

```bash
# PROBE 1: confirm app $def lacks tenant fields
git show origin/main:validators/creator_engine_validator/schemas/identity-registry.schema.yaml \
  | grep -E 'app_name|client_id|tenant_scope'
# Expect: zero hits — these fields do not exist yet

# PROBE 2: confirm example file exists
git show origin/main:docs/governance/identity-registry.example.yaml | head -5
# Expect: file exists; capture current content for context before editing

# PROBE 3: confirm test file exists (extend, do not replace)
git show origin/main:validators/tests/unit/test_identity_registry_schema.py | head -10
# Expect: file exists with existing tests

# PROBE 4: confirm ce_cli.py is NOT modified (stop-line check)
grep -rn 'identity' validators/creator_engine_validator/ce_cli.py | head -5
# For reference only — do NOT touch ce_cli.py
```

### Deliverable

#### `validators/creator_engine_validator/schemas/identity-registry.schema.yaml`

Extend the `app` `$defs` entry. Current required fields: `app_id`, `install_id`,
`repo_scope`, `pem_custody`. Add these OPTIONAL fields:

```yaml
  app:
    type: object
    required: [app_id, install_id, repo_scope, pem_custody]
    additionalProperties: false
    properties:
      # existing fields — do not change their definitions
      app_id:        { $ref: "#/$defs/todo_or_integer" }
      install_id:    { $ref: "#/$defs/todo_or_integer" }
      repo_scope:    { $ref: "#/$defs/non_empty_string" }
      pem_custody:
        type: string
        pattern: "^(TODO_VERIFY|vault://[^\\s]+|openbao-ref:[^\\s]+|file://[^\\s]+)$"
      # NEW optional fields below
      app_name:
        $ref: "#/$defs/todo_or_string"
        description: >-
          Human-readable App name / slug (e.g. mythos-ce). Optional but
          recommended for operator readability.
      client_id:
        $ref: "#/$defs/todo_or_string"
        description: >-
          GitHub OAuth App client_id (format: Iv23li... or TODO_VERIFY).
          Non-secret — safe to store in the public registry. Used by the
          recall path to resolve the App without a live API call.
      tenant_scope:
        type: string
        enum: [selected-repos, account-wide, TODO_VERIFY]
        description: >-
          Scope of the App installation: account-wide (all repos of the
          installing account) or selected-repos (subset). TODO_VERIFY if
          not yet confirmed.
```

Note: `pem_custody` pattern should be extended to allow `file://` prefix (the
mythos-ce key is at `file://~/.ce-keys/mythos-ce.2026-06-20.private-key.pem` — the
existing schema only accepts `vault://` and `openbao-ref:` prefixes). If the existing
pattern already accepts `file://`, skip this change and note `PROBE_PEM_PATTERN: already_ok`.

Also add the precedence rule to the top-level schema `description` block. Append to
the existing description (do not replace it):

```yaml
  Precedence rule: when an infra identifier is present in this registry, that value
  is authoritative. Controllers and seats MUST NOT derive or override it from env
  files, MEMORY.md prose, or live API calls. The registry WINS.
```

#### `docs/governance/identity-registry.example.yaml`

Add (or extend) an `apps:` section with a mythos-ce entry. Use TODO_VERIFY only for
values genuinely unknown. Known non-secret values are:

```yaml
apps:
  # dev-seat forge Apps (existing entries — do not change)
  # ...
  
  # Tenant Apps — added by ce-470 schema slice
  - app_name: mythos-ce
    app_id: 4103119
    client_id: Iv23liuJp6OxfCWvwfSl
    install_id: 141552951
    tenant_scope: account-wide
    repo_scope: "chmod735-dor/* (all repos, account-wide installation)"
    pem_custody: "file://~/.ce-keys/mythos-ce.2026-06-20.private-key.pem"
    # PRECEDENCE: this entry is authoritative; env files are stale if they differ.
```

Add a `# PRECEDENCE:` comment block near the top of the file:

```yaml
# PRECEDENCE RULE (ce-470): When an identifier is present in this file, it is
# authoritative. Controllers MUST NOT override registry values from env files,
# MEMORY.md prose, or live API calls. Registry WINS over all other sources.
```

#### `validators/tests/unit/test_identity_registry_schema.py` (extend)

Add new test functions AFTER the existing tests. Do NOT modify existing tests.

```python
# --- tenant App validation (added by ce-470 schema slice) ---

def test_app_with_tenant_fields_valid(valid_registry):
    """An app entry with the new optional tenant fields validates successfully."""
    registry = valid_registry  # obtain your base valid registry fixture
    # Inject a tenant App into the apps list
    tenant_app = {
        "app_id": 4103119,
        "install_id": 141552951,
        "repo_scope": "account-wide",
        "pem_custody": "openbao-ref:ce/mythos-ce-pem",
        "app_name": "mythos-ce",
        "client_id": "Iv23liuJp6OxfCWvwfSl",
        "tenant_scope": "account-wide",
    }
    # (adapt to fit the existing test fixture pattern in the file)
    # Validate the schema accepts this entry — no ValidationError expected.


def test_app_without_tenant_fields_still_valid():
    """Existing app entries (without app_name/client_id/tenant_scope) remain valid."""
    # An app with only the 4 required fields must still pass schema validation.


def test_app_invalid_tenant_scope_rejected():
    """tenant_scope must be one of the allowed enum values."""
    # An app entry with tenant_scope="all" (not in enum) must fail schema validation.
```

Adapt the above to fit the existing fixture and schema-validation pattern in the file.
Read the existing tests first to understand the helper pattern before writing new ones.

### Acceptance criteria

1. `grep -E 'app_name|client_id|tenant_scope' validators/creator_engine_validator/schemas/identity-registry.schema.yaml` returns hits for all three new fields.

2. `grep 'mythos-ce' docs/governance/identity-registry.example.yaml` returns a hit.

3. `grep 'PRECEDENCE' docs/governance/identity-registry.example.yaml` returns a hit.

4. `pytest validators/tests/unit/test_identity_registry_schema.py -v` passes, including the new tenant-App tests.

5. Full `ce validate-pr` GREEN on the working tree.

6. PR opened (non-draft) with `- **Declared work class:** S` in body, plus note: "CLI recall path (`ce identity lookup`) deferred to post-PR-918 follow-on unit."

### Hard constraints

- Do NOT touch `validators/creator_engine_validator/ce_cli.py` (PR #918 frozen). The
  recall path CLI is DEFERRED.
- Do NOT touch any file in the hermes set.
- Do NOT create a new ADR for this unit.
- ZERO ce-ops# references in changelog or carrier body text.
- The `pem_custody` pattern change (adding `file://`) must be backward-compatible —
  existing `vault://` and `openbao-ref:` values must still validate.

### Stop line (Unit B)

No edits outside these paths:

```
validators/creator_engine_validator/schemas/identity-registry.schema.yaml
docs/governance/identity-registry.example.yaml
validators/tests/unit/test_identity_registry_schema.py
.ce/changelog/ce-470-infra-identity-schema.md
.ce/pr-manifests/ce-470-infra-identity-schema.md
```

Absolute stop-lines — same as Unit A, plus:
- `validators/creator_engine_validator/ce_cli.py` (PR #918 frozen; recall-path CLI deferred)
- `validators/creator_engine_validator/schemas/install-answers.schema.yaml` (dev-3 territory)

### PR-open signal (Unit B)

After opening the PR, emit to pane:

```
STATUS: DONE
BRANCH: ce-470-infra-identity-schema
PR: <number> ce-470-infra-identity-schema
PROBE_APP_FIELDS: <zero_hits — proceeded | already_present — unexpected>
PROBE_PEM_PATTERN: <needed_change | already_ok>
VALIDATE_PR: GREEN
GATE_NOISE: <"none" or verbatim text of false-RED gates on untouched files>
CLI_RECALL_PATH: DEFERRED (ce_cli.py frozen by PR #918)
PR <number> ce-470-infra-identity-schema
```

Do NOT commit a READY file to the repo. The pane signal is the only signal.
