# D4 Ring-1 Promotion Evidence Packet
## Codex harness — Ring-0 → Ring-1 (foreman authority)
### Assembled: 2026-07-08 | Host: spark-b824 (ce-dev-2)

> **ASSEMBLY ONLY.**
> This packet is evidence assembly, not a cell flip.
> The promotion-approved cell in the harness matrix and the
> `CE_CONTROLLER_AUTHORITY` foreman grant are **Operator-only acts**.
> No worker, seat, or automated process may flip them.
> See §4 OPERATOR DECISION below for the exact request.

---

## 1. WHAT IS BEING PROMOTED

**Ring-1** for the `codex` harness means:
- Managed Codex PreToolUse hook-pack is confirmed active before spawn.
- Governed `ce launch --harness codex` writes a validated
  promotion-evidence packet to `.ce/state/controller-evidence/`.
- On valid packet: `CE_CONTROLLER_AUTHORITY=foreman` (write authority).
- On absent/incomplete packet: fails closed to `CE_CONTROLLER_AUTHORITY=read-only`.

**Ring-1 definition sources:**
- Gate columns: `docs/operations/HARNESS_SUPPORT_CAPABILITY_MATRIX.md`
  (code-support / launch-wired / live-proven / promotion-approved)
- Packet schema: `validators/creator_engine_validator/codex_controller_evidence.py`
  (`REQUIRED_FIELD_CLASSES`, `validate_packet`)
- Refusal clause: `docs/operations/SEAT_LAUNCH_GOVERNANCE_RUNBOOK.md` CDX-D-8

---

## 2. CRITERIA vs EVIDENCE

### 2a. Gate columns (harness matrix)

| Criterion | Status | Evidence pointer |
|---|---|---|
| code-support | **MET** | `hook_pack_confirm.confirm_codex_managed_hook_pack` green; `codex_pretooluse.py` wired; merged: ce219-codex-ring1-hookpack + ce219-ring1-codex-enforcement |
| launch-wired | **PARTIAL** | `.codex/requirements.toml` has `allow_managed_hooks_only=true` + PreToolUse matcher incl. `Read`; `run-codex-runsc.sh` hardened (#891 d9e7c6f59); matrix still yellow — containment acceptance not formally confirmed |
| live-proven | **MISSING** | `.ce/state/controller-evidence/` is empty; no `ring1_smoke_result.status=pass` packet on disk |
| promotion-approved | **MISSING** | Operator cell flip not performed; matrix row still `red` / `gate-capable=no` |

### 2b. Packet field classes (codex_controller_evidence.py REQUIRED_FIELD_CLASSES)

| Field class | Status | Note |
|---|---|---|
| argv_after_rewrite | MISSING | No packet on disk |
| managed_hook_confirmed | PARTIAL | `confirm_codex_managed_hook_pack` callable exists; `.codex/requirements.toml` sha computable; real-world `confirmed=true` requires live governed launch |
| cdxd_result | MISSING | Requires governed `ce launch --harness codex` Ring-0 preflight to pass |
| bypass_mode_source | MISSING | No packet; must be `argv`, `config`, or `none` |
| remote_control_status | PARTIAL | Env var domain defined; host-ops broker design landed (#884 5a6dac5ce); no live packet value |
| hook_requirements_sha | PARTIAL | `.codex/requirements.toml` is on-disk (sha256-computable); value not yet persisted in packet |
| hook_script_sha | PARTIAL | `.codex/hooks/ce-pretooluse-codex.py` on-disk (sha256: f9413fa90f…); not yet persisted |
| lifecycle_sentinel_refs | MISSING | Requires sentinel wrapper materialized by a live governed launch |
| ring1_smoke_result | MISSING | Must be `{"status":"pass",...}`; gate from launch_runtime.py lines 2094–2115; no live run recorded |

### 2c. Night-arc PRs — Ring-1 relevance (merged 2026-07-07, post-#880)

| PR | SHA | Why it bears on Ring-1 readiness |
|---|---|---|
| #883 Forge housekeeping runbook | c39ab6883 | Wires forge runbook into `takeover_runtime`; controller lifecycle continuity required before promotion is meaningful |
| #884 Host-ops broker v1 design | 5a6dac5ce | Defines `remote_control_status` brokered/explicit-posture value domain — a required promotion packet field |
| #886 Recursion bottom-out policy | b8f26a5a3 | Governs ephemeral controllers spawned by Ring-1 foreman seats; promotion unlocks foreman; bottom-out rule must precede that |
| #887 Ephemeral controller seam + NanoClaw | 113a6ed42 | Seam design depends on Ring-1 foreman authority; NanoClaw provider architecture presupposes promotion is available |
| #888 Brain memory-layer slice 1 | cc82486e5 | `lifecycle_sentinel_refs` and takeover wiring are required packet fields; brain hydration now wired into takeover chain |
| #891 Runsc launcher durability | d9e7c6f59 | Hardens `deploy/dgx-runsc/run-codex-runsc.sh` durable paths; packet write path stability depends on launcher surviving seat recycling |

### 2d. Pre-cursor PRs merged (2026-07-07, Ring-1 foundation)

| PR | SHA | What it added |
|---|---|---|
| #879 ce-ops#480 evidence packet | 63318f65e | `codex_controller_evidence.py` (+273 lines): packet schema, `validate_packet`, `build_packet`, `write_packet`; `launch_runtime.py` downgrade-to-read-only wiring; 110-line unit test suite |
| #880 ce-ops#479 parity matrix | faf9307d3 | `harness_matrix.py` refactor + `HARNESS_SUPPORT_CAPABILITY_MATRIX.md`; `harness_promotion_matrix.py` gate check; CI `validate.yml` wired; Codex Ring-1 row formally red/deferred |

---

## 3. GAPS

Gaps the criteria demand that have no evidence on main tonight:

1. **No promotion packet on disk.** `.ce/state/controller-evidence/` directory does not exist / is empty. A governed `ce launch --harness codex` run on spark-b824 must complete successfully and write the packet before any field class can be marked present.

2. **`ring1_smoke_result` absent.** The packet's `ring1_smoke_result.status` must be `"pass"`. The launch_runtime build-path (lines 2094–2115) sets this synthetically from sentinel materialization — no such run has occurred.

3. **`launch-wired` still yellow in harness matrix.** `harness_matrix.py` hardcodes the yellow/deferred provenance for the `launch-wired` cell pending "containment acceptance"; this string must change to green before the row becomes gate-capable.

4. **`ce-stop-codex.py` absent.** `codex_controller_evidence.known_gaps()` returns `codex-closeout-hook-gap` for `.codex/hooks/ce-stop-codex.py` missing. This is a Ring-2 gap, not a Ring-1 blocker, but the packet will carry a non-empty `known_gaps` list until it is resolved.

5. **`promotion-approved` cell is red.** This is the Operator act being requested. No code change can set this; it requires the Operator to update `harness_matrix.py` provenance and re-render the matrix doc.

---

## 4. OPERATOR DECISION

**Decision being requested:**
Flip the `codex / Ring 1` row in `harness_matrix.py` from deferred/red to fully green, subject to the Operator confirming:

a. The live `ring1_smoke_result` packet at `.ce/state/controller-evidence/codex-controller-promotion.<host-slug>.json` is valid (`status: valid`, all field classes present).
b. The `launch-wired` provenance string is updated to reflect containment acceptance (replacing the "deferred pending containment acceptance" language).
c. The `promotion-approved` provenance string cites this packet by path and date.

**Files that must change for the promotion cell flip:**
- `validators/creator_engine_validator/harness_matrix.py` — `_codex_rows()` Ring-1 row: `launch_wired`, `live_proven`, `promotion_approved` cell values
- `docs/operations/HARNESS_SUPPORT_CAPABILITY_MATRIX.md` — re-rendered matrix (CI enforces parity)

**The Operator alone holds this authority. No PR may self-approve this row.**
