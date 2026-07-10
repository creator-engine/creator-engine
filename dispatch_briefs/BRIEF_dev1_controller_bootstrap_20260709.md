---
brief_id: BRIEF_dev1_controller_bootstrap_20260709
ticket: ce-496-controller-bootstrap-doc-s1
seat: dev-1
seat_kind: host-self-push
branch: ce-496-controller-bootstrap-doc-s1
size: S
units: 1
priority: TOP
mandate: main-controller-independence-20260709
grounded_on: origin/main@6ffd0fe19b8169d6b50a905e2de4ee4c92ea65d8
queue_position: QUEUED — begin only after ce-478-posture-banner AND ce-470-infra-identity-schema (PR #925) complete
composed_at: 2026-07-09
---

# BRIEF: Controller bootstrap runbook — docs slice 1

> **QUEUE STATUS:** Dev-1 is currently in-compose on ce-478-posture-banner (🔒 as
> of 2026-07-09). PR #925 (ce-470-infra-identity-schema) is OPEN pending review.
> Do NOT begin this work until BOTH of those units are pushed and out of your
> active compose. The controller will re-dispatch this brief when your queue
> clears. File-disjoint check against ce-470 paths is mandatory before starting.

---

## Mandate (2026-07-09)

The DGX reboot halted the factory. A replacement main controller (on the VPS or
any qualifying host) cannot currently spawn and resume the factory because:
- No single runbook exists documenting the full spawn sequence.
- State is DGX-local with no governed hydration path.
- The standby surface provisioning script (PR #920) exists but is not yet merged.
- Identity/credential pointers require spelunking rather than SSOT recall.

This slice (ce-496-controller-bootstrap-doc-s1) delivers the governed runbook
(`docs/operations/CONTROLLER_BOOTSTRAP.md`) and a doc-vs-reality smoke test.

## Ticket content (ce-496, embedded)

**Context (ce-496 program):** The primary controller is an ungoverned bespoke
harness instance. If the DGX is lost (disk failure, reboot storm), the factory
loses its only fully-functional controller. The parity program (ce-496) closes
this gap: controllers must be IaC-deployable and SSOT-fed. This doc slice
captures the human-executable runbook that an operator or replacement controller
follows to spawn a new main controller from scratch on the VPS.

**Deliverable:** `docs/operations/CONTROLLER_BOOTSTRAP.md` — a single governed
runbook covering prerequisites, identity hydration, state hydration, standby
surface provisioning, harness-agnostic launch, takeover drill reference, and
an explicit gap list (secrets until OpenBao, sync push wiring until ce-497 s2).
Plus a validator smoke test (`validators/tests/unit/test_controller_bootstrap_paths.py`)
that gates the doc-vs-reality contract.

---

## Standing obligations (copy verbatim into PR body + checklist)

- [ ] Changelog fragment: `.ce/changelog/ce-496-controller-bootstrap-doc-s1.md`
- [ ] Carrier: `.ce/pr-manifests/ce-496-controller-bootstrap-doc-s1.md`
      slug field MUST be exactly `ce-496-controller-bootstrap-doc-s1`
- [ ] **Declared work class: story** — THIS LINE MUST APPEAR BOLDED IN THE PR BODY.
      Dev-1 has repeatedly omitted this; it is a hard gate requirement. Do not
      submit the PR until this line is present and bold in the PR body.
- [ ] NEVER commit a file named READY (gate signal)
- [ ] No ce-ops issue number references in PR body, commit messages, or doc text
      (use plain descriptions: "controller parity program", "identity SSOT slice",
      "state sync slice 1", etc.)

---

## Files to produce — COMPLETE territory

All four files are new. No existing file is modified by this PR.

```
docs/operations/CONTROLLER_BOOTSTRAP.md                         (new)
validators/tests/unit/test_controller_bootstrap_paths.py        (new)
.ce/changelog/ce-496-controller-bootstrap-doc-s1.md             (new)
.ce/pr-manifests/ce-496-controller-bootstrap-doc-s1.md          (new)
```

**Brain-pin precompute (byte-change rule):** All four targets are new files.
Prior sha256: N/A. PR diff must show only additions — zero deletions from
any existing file.

---

## Frozen / in-flight paths — DO NOT TOUCH

| Path | Owned by |
|---|---|
| `.ce/brain/assertions.yaml` | PR #918 (FROZEN — absolute stop) |
| `validators/creator_engine_validator/ce_cli.py` | PR #918 |
| `docs/operations/CLAUDE_CODE_HOOK_PACK.md` | PR #918 |
| `.claude/hooks/ce-hook-common.sh` | PR #918 |
| `.claude/hooks/ce-pretooluse.sh` | PR #918 |
| `.claude/hooks/ce-stop.sh` | PR #918 |
| `docs/architecture/agent-interaction-model.md` | PR #918 |
| `docs/contracts/forge-claim.md` | PR #918 |
| `validators/creator_engine_validator/continuity_drill_runtime.py` | PR #920 |
| `deploy/dgx-controller-runsc/provision-standby-surface.sh` | PR #920 |
| `tools/mint-forge-token.py` | PR #920 |
| `validators/creator_engine_validator/schemas/identity-registry.schema.yaml` | PR #925 (your ce-470 unit) |
| `docs/governance/identity-registry.example.yaml` | PR #925 (your ce-470 unit) |
| `validators/tests/unit/test_identity_registry_schema.py` | PR #925 |

No `surfaces/manifest.yaml` edit. No AGENTS.md / CLAUDE.md changes.

---

## Document specification: `docs/operations/CONTROLLER_BOOTSTRAP.md`

### Required section structure (headings must match exactly for smoke-test grep)

```
# CONTROLLER_BOOTSTRAP — Replacement Main Controller: Spawn and Resume

## 0. Purpose and scope
## 1. Prerequisites
## 2. Identity hydration
## 3. State hydration
## 4. Standby surface provisioning
## 5. Launch — harness-agnostic
## 6. Takeover drill
## 7. Gap list
## 8. Validation checklist
```

### Section content requirements

**Section 0 — Purpose and scope**
- When to use: DGX host lost, primary controller outage, drill exercise.
- Scope: spawning a replacement main controller. Does not cover seat
  provisioning or tenant onboarding.
- Outcome: a running controller that can resume the factory conveyor from
  centralized state within one shift.

**Section 1 — Prerequisites**
Target host (VPS `ce-dev-1`, 100.72.252.20, tailnet-only):
- `git` 2.40+
- `python3` 3.11+ (uv-managed venv preferred)
- `ce` binary accessible in PATH (installed via `pip install creator-engine`
  or from the repo's `main` branch worktree)
- Overwatch PAT loaded: `set -a; source ~/.ce-keys/overwatch.env; set +a; export GH_TOKEN=$CE_OVERWATCH_PAT`
- SSH access confirmed: `ssh dev1 whoami` returns `cedev2` (or equivalent user)
- `jq` installed (for manifest inspection)
- The `creator-engine` repo clone at a known path (e.g. `/home/cedev2/creator-engine`
  or `/home/ce-dev-1/creator-engine`) checked out to `origin/main`

**Section 2 — Identity hydration**
- Source of truth: `ce-ops` repo, path `infra/identity-registry.yaml`
  (the authoritative CE identity SSOT, per the registry-wins precedence rule)
- Reference the registry precedence rule: when an identity is present in
  `infra/identity-registry.yaml`, that value is authoritative. Controllers
  must NOT derive or override it from env files, memory, or live API calls.
- Recall path: `ce identity lookup <app-name-or-app-id>` (returns non-secret
  fields: app_id, installation_id, pem_custody pointer)
  Status note: recall CLI implementation is a pending slice (identity SSOT
  recall slice); until it lands, consult the registry YAML directly.
- Secrets custody note: PEM files and PAT tokens are NOT in the registry —
  only `pem_custody: file://...` pointers. Secrets are brought to the
  replacement host out-of-band (OpenBao lane is the ratified long-term
  target; see Gap list, Section 7).
- Step: `git -C <ce-ops-clone> show origin/main:infra/identity-registry.yaml | yq '.apps[] | select(.name == "mythos-ce")'`

**Section 3 — State hydration**
- Source: the controller state snapshot committed by `tools/controller/state_sync.py`
  on the dedicated branch `ce-controller-state/<hostname>` of the state target repo.
- Restore command: `python3 tools/controller/state_sync.py --restore --source-branch ce-controller-state/spark-b824 --output-root /home/cedev2/creator-engine`
  (Implementation note: `--restore` flag is the slice 2 inverse operation;
  for slice 1, restore manually: check out the state branch, copy the arc_state/
  directory to `.ce/state/research/`, dispatch_briefs/ to `.ce/briefs/`,
  dispatch_claims/ to `.ce/claims/`, and optionally extract memory.tar.gz.)
- Integrity check: verify manifest.json `sha256` for each restored file.
- Status note: the snapshot tool (state sync slice 1) must be merged before
  this step is available as a one-command operation.

**Section 4 — Standby surface provisioning**
- Script: `deploy/dgx-controller-runsc/provision-standby-surface.sh`
  (added by the standby surface fix PR — dependency note: requires that PR to
  be merged before this step is operational)
- What it does:
  - Creates a dedicated git worktree at `/home/cedev2/ce-standby-main/` pinned
    to `origin/main` (decoupled from the shared mutable checkout).
  - Verifies `ce takeover --dry-run --json` returns `ring0_verify.ok=true` and
    `initial_state=AWAITING-OPERATOR`.
  - Verifies `tools/mint-forge-token.py --help` executes without traceback.
- Invocation: `bash deploy/dgx-controller-runsc/provision-standby-surface.sh --dry-run`
  then without `--dry-run` to provision for real.
- Environment vars: `SHARED_ROOT` (default `/home/cedev2/creator-engine`),
  `STANDBY_ROOT` (default `/home/cedev2/ce-standby-main`).

**Section 5 — Launch (harness-agnostic)**
- Entry command: `ce launch --repo-root <replacement_repo_root>`
- Harness flag (optional): `--harness claude` (Claude Code) or `--harness codex` (Codex)
  Per doctrine, `ce launch` is harness-agnostic; omit flag to use the installed default.
- The controller's SSOT-fed operating files (AGENTS.md, CLAUDE.md, `.claude/agents/`)
  are present in the main-tracked checkout and do not need hand-tuning.
- After launch, confirm AWAITING-OPERATOR posture: `ce posture` (ce-478 output)
  should show `state=AWAITING-OPERATOR, predecessor=<original-controller-host>`.

**Section 6 — Takeover drill**
- Mandatory at first launch: `ce takeover --dry-run --json | python3 -c 'import json,sys; r=json.load(sys.stdin); assert r["ring0_verify"]["ok"] is True'`
- Weekly drill cadence (once two consecutive clean runs pass, monthly):
  run `ce continuity-drill --from ce-controller --harness claude --json`
  with env var `CE_STANDBY_LIVENESS_JSON` populated from the standby's
  `ce takeover --dry-run --json` output.
- A drill is GREEN only when `standby_liveness.ok=true` in the continuity-drill
  output. Raw boolean `CE_STANDBY_LIVENESS=1` is rejected (WARNING status).
- Standby surface reference: `deploy/dgx-controller-runsc/provision-standby-surface.sh`
  ensures the standby's worktree is on `origin/main` before each drill.

**Section 7 — Gap list**
Document these gaps explicitly (do not elide or paper over them):

| Gap | Status | Tracking |
|---|---|---|
| Secrets custody | OpenBao lane is the ratified long-term target. Until it lands, PEM and PAT files are brought to the replacement host out-of-band. Do NOT put secrets in git. | Separate program — OpenBao prereqs done |
| State sync push wiring | Slice 1 snapshot tool writes to local output-dir; the controller manually commits and pushes. Automated push-on-snapshot is slice 2. | State sync slice 2 (not yet dispatched) |
| Identity recall CLI | `ce identity lookup` is not yet implemented. Registry must be read directly via yq/python. | Identity SSOT recall slice (pending) |
| Memory sync | Controller memory (`~/.claude/projects/.../memory/`) requires `--include-memory` flag and is not yet part of the default sync cadence. | State sync slice 1 (opt-in) |
| Parallel worker venue | A freshly deployed controller has no equivalent of the bespoke controller's session-level agent fleet. The parity acceptance test (full harvest→review→gate→closeout cycle) is not yet runnable. | Controller parity program (ongoing) |

**Section 8 — Validation checklist**
```
[ ] ce-ops infra/identity-registry.yaml readable and contains fleet entries
[ ] ce takeover --dry-run --json → ring0_verify.ok=true, initial_state=AWAITING-OPERATOR
[ ] provision-standby-surface.sh --dry-run exits 0
[ ] ce posture → state=AWAITING-OPERATOR (after live launch)
[ ] ce continuity-drill --json → status=GREEN (with standby liveness env set)
[ ] validators/tests/unit/test_controller_bootstrap_paths.py → all pass
```

---

## Smoke test specification: `validators/tests/unit/test_controller_bootstrap_paths.py`

Pattern: doc-vs-reality gate. All tests are `pytest.mark.fast`.

```python
"""Smoke tests: CONTROLLER_BOOTSTRAP.md references reality-grounded paths.

Tests that depend on not-yet-merged PRs use skipif guards so they pass
on current main and become green once the dependency lands.
"""
```

Required test functions:

```python
def test_controller_bootstrap_doc_exists():
    # Assert docs/operations/CONTROLLER_BOOTSTRAP.md exists
    assert (REPO_ROOT / "docs/operations/CONTROLLER_BOOTSTRAP.md").exists()

def test_doc_references_identity_registry_ssot():
    # Assert the doc contains the canonical registry path reference
    content = (REPO_ROOT / "docs/operations/CONTROLLER_BOOTSTRAP.md").read_text()
    assert "infra/identity-registry.yaml" in content

def test_doc_references_provision_standby_script():
    content = (REPO_ROOT / "docs/operations/CONTROLLER_BOOTSTRAP.md").read_text()
    assert "provision-standby-surface.sh" in content

def test_doc_references_state_sync_tool():
    content = (REPO_ROOT / "docs/operations/CONTROLLER_BOOTSTRAP.md").read_text()
    assert "state_sync.py" in content

def test_doc_has_required_sections():
    content = (REPO_ROOT / "docs/operations/CONTROLLER_BOOTSTRAP.md").read_text()
    required_headings = [
        "## 0. Purpose",
        "## 1. Prerequisites",
        "## 2. Identity hydration",
        "## 3. State hydration",
        "## 4. Standby surface provisioning",
        "## 5. Launch",
        "## 6. Takeover drill",
        "## 7. Gap list",
        "## 8. Validation checklist",
    ]
    for heading in required_headings:
        assert heading in content, f"Missing section: {heading!r}"

def test_doc_references_openbao_secrets_gap():
    # Verify the doc explicitly calls out the secrets gap (no secrets in git)
    content = (REPO_ROOT / "docs/operations/CONTROLLER_BOOTSTRAP.md").read_text()
    assert "OpenBao" in content or "openbao" in content.lower()
    assert "Gap list" in content

@pytest.mark.skipif(
    not (REPO_ROOT / "deploy/dgx-controller-runsc/provision-standby-surface.sh").exists(),
    reason="provision-standby-surface.sh not yet merged (pending standby surface PR)"
)
def test_provision_standby_script_exists_on_disk():
    assert (REPO_ROOT / "deploy/dgx-controller-runsc/provision-standby-surface.sh").exists()

@pytest.mark.skipif(
    not (REPO_ROOT / "tools/controller/state_sync.py").exists(),
    reason="state_sync.py not yet merged (pending state sync slice 1)"
)
def test_state_sync_tool_exists_on_disk():
    assert (REPO_ROOT / "tools/controller/state_sync.py").exists()

def test_doc_contains_gap_list_table():
    content = (REPO_ROOT / "docs/operations/CONTROLLER_BOOTSTRAP.md").read_text()
    # Gap list must name the secrets gap explicitly
    assert "Secrets custody" in content or "secrets custody" in content.lower()
    assert "OpenBao" in content

def test_doc_does_not_contain_secrets():
    content = (REPO_ROOT / "docs/operations/CONTROLLER_BOOTSTRAP.md").read_text()
    # No actual secret values — only pointers
    import re
    # Check no github_pat token patterns
    assert not re.search(r'github_pat_[A-Za-z0-9_]{10,}', content)
    # Check no PEM block content
    assert "BEGIN RSA PRIVATE KEY" not in content
    assert "BEGIN PRIVATE KEY" not in content
```

---

## Changelog fragment (`.ce/changelog/ce-496-controller-bootstrap-doc-s1.md`)

```markdown
## ce-496-controller-bootstrap-doc-s1

- docs(operations): add CONTROLLER_BOOTSTRAP.md — replacement main controller runbook

  Adds docs/operations/CONTROLLER_BOOTSTRAP.md: the governed runbook for
  spawning a replacement main controller on the VPS when the DGX is lost.
  Covers prerequisites, identity hydration from the registry SSOT, state
  hydration from the controller state snapshot (state sync slice 1),
  standby surface provisioning (provision-standby-surface.sh), harness-
  agnostic launch via ce launch, takeover drill verification, and an
  explicit gap list (secrets custody → OpenBao lane; live sync push →
  state sync slice 2; identity recall CLI pending).

  Adds validators/tests/unit/test_controller_bootstrap_paths.py: doc-vs-
  reality smoke test that gates the doc's referenced paths/commands against
  the repo. Tests for not-yet-merged dependencies use skipif guards.

  Part of the main-controller independence program (2026-07-09 mandate).

  - **Declared work class:** story
```

---

## PR carrier (`.ce/pr-manifests/ce-496-controller-bootstrap-doc-s1.md`)

```markdown
# PR path manifest — ce-496-controller-bootstrap-doc-s1

slug: ce-496-controller-bootstrap-doc-s1

- **Declared work class:** story

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=<compute via canonical sha256("\n".join(sorted(paths)) + "\n")>

\`\`\`text
.ce/changelog/ce-496-controller-bootstrap-doc-s1.md
.ce/pr-manifests/ce-496-controller-bootstrap-doc-s1.md
docs/operations/CONTROLLER_BOOTSTRAP.md
validators/tests/unit/test_controller_bootstrap_paths.py
\`\`\`
```

Compute AUTHORIZED_PATHS_SHA256:
```python
import hashlib
paths = sorted([
    ".ce/changelog/ce-496-controller-bootstrap-doc-s1.md",
    ".ce/pr-manifests/ce-496-controller-bootstrap-doc-s1.md",
    "docs/operations/CONTROLLER_BOOTSTRAP.md",
    "validators/tests/unit/test_controller_bootstrap_paths.py",
])
print(hashlib.sha256(("\n".join(paths) + "\n").encode()).hexdigest())
```

---

## PR body template (use this verbatim)

```markdown
## Summary

- Add docs/operations/CONTROLLER_BOOTSTRAP.md: governed runbook for spawning
  a replacement main controller on the VPS when the DGX is unavailable.
- Covers: prerequisites, identity hydration from registry SSOT, state
  hydration from the controller snapshot tool, standby surface provisioning,
  harness-agnostic launch, takeover drill, and explicit gap list.
- Add validators/tests/unit/test_controller_bootstrap_paths.py: doc-vs-reality
  smoke test gating doc references against actual repo paths.
- Not-yet-merged dependencies (provision-standby-surface.sh, state_sync.py)
  are skipif-guarded; tests pass on current main.

**Declared work class: story**

## Validation

- `PYTHONPATH=validators .venv/bin/python -m pytest validators/tests/unit/test_controller_bootstrap_paths.py -v`
- `PYTHONPATH=validators .venv/bin/python -m creator_engine_validator.ce_cli validate-pr --repo-root . --declared-work-class S`

## Gate noise

<paste validate-pr output here>

## Closes

Replacement-controller spawn runbook gap — an Operator or replacement
controller can now follow a single governed document to resume the factory
from centralized state after a host loss. Part of the main-controller
independence program (2026-07-09 mandate).
```

---

## Preflight gate

```bash
# From worktree root (origin/main checkout)
PYTHONPATH=validators .venv/bin/python -m pytest \
  validators/tests/unit/test_controller_bootstrap_paths.py -v

PYTHONPATH=validators .venv/bin/python -m creator_engine_validator.ce_cli \
  validate-pr --repo-root . --declared-work-class S
```

Both must pass GREEN. If validate-pr reports path-manifest mismatch, recompute
AUTHORIZED_PATHS_SHA256 and update the carrier. The two skipif tests will show
as SKIPPED (not FAILED) on current main — that is correct behavior.

---

## Stop-lines

1. No secrets in the doc — only pointers and paths.
2. No `assertions.yaml` modifications.
3. No `ce_cli.py` modifications (frozen in PR #918).
4. No `docs/operations/CLAUDE_CODE_HOOK_PACK.md` modifications (PR #918).
5. No ce-ops# issue references in PR body or doc text.
6. **Declared work class: story** must appear bolded in the PR body. This
   line has been omitted from dev-1's recent PRs. It is a hard gate
   requirement — the PR will be rejected at review without it.
7. READY file must NOT be committed.
8. Dual-format obligation: this doc is in `docs/operations/` (prose, not a
   product-facing artifact). Dual-format (md + HTML) applies to product-facing
   docs and welcome packs. An operations runbook in `docs/operations/` does
   not require an HTML twin — markdown-only is correct here.
