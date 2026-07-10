# BRIEF — dev-4 batch 5 — 2026-07-06 ~17:0xZ — 2 units (both P1 of the ratified #471 program)

Foreman: run as concurrent workers where file-disjoint. Commit-only: NO push. Per unit signal:
`READY|BLOCKED-ENV <branch> <sha> <evidence-path>`. Verdicts/evidence to FILES under /var/tmp/.
Stop lines: no approval/merge paths, no signing (sig invalid → report, controller signs), no
settings, no sha-pinned files. Base both branches on FRESH origin/main (it moved: #859/#865/
#866/#867/#869/#870/#871 merged today — fetch first). Each unit: changelog fragment
`.ce/changelog/<slug>.md`, carrier slug == branch, honest declared work class.

Context you cannot fetch (no ce-ops read): both tickets are children of ce-ops#471, ratified as
a block by Operator 2026-07-06. Report: .ce/state/research/CONTROLLER_POWER_CONTINUITY_RESEARCH_20260706.md
(READ IT — it is in your repo checkout after fetch? NO — it is controller-host state, NOT in git.
Work from the embedded acceptance bars below; they are the spec.)

## U1 — ce-ops#479: harness parity-by-layer matrix — branch `ce-479-parity-matrix`
Extend the existing `HARNESS_SUPPORT_CAPABILITY_MATRIX.md` (find it in-repo) so "code support
exists" is never confused with "this live session is promoted to controller authority."
ACCEPTANCE BARS (verbatim from ratified ticket):
- Matrix adds four columns per provider/ring row: `code-support`, `launch-wired`, `live-proven`,
  `promotion-approved`.
- Providers represented: Claude, Codex, lane (worker), contained-controller scaffold,
  ephemeral-controller providers.
- A harness row is gate-capable ONLY if all four cells green, or an explicit Operator-ratified
  exception recorded with date + ratification reference.
- CI-checked: `ce validate-pr` (or equivalent gate) FAILS if a row promotes a harness to
  gate-capable without all-green or a recorded exception. (Follow the version-drift gate #467
  pattern for an unsigned-checker + CI wiring; keep it OUT of the per-path check registry.)
- Known state to encode: Claude Ring 0/1/2 full per existing matrix; Codex Ring 0 full, Ring 1
  deferred pending containment acceptance (promotion evidence packet = ce-ops#480), Ring 2 none,
  containment deferred; contained-controller scaffold static/dry-run only, C2/C3/C4 unproven;
  ephemeral-controller providers design-stage only.
Work class: story.

## U2 — ce-ops#480: codex controller promotion evidence packet — branch `ce-480-codex-promotion-packet`
`ce launch --harness codex` must refuse/downgrade controller authority when the promotion
evidence packet is absent or incomplete. Ratified decisions binding this unit:
- Decision 7: Codex Ring-1 promotion may proceed before full containment acceptance IF the
  evidence packet + Ring-1 smoke are live-proven (parity matrix keeps containment deferred).
- Decision 6: governed authoring controllers keep remote-control DISABLED unless routed through
  a brokered/evidence-preserving surface; read-only supervisory sessions may use remote-control
  with explicit non-authoring posture; status MUST appear as `remote_control_status` in the packet.
ACCEPTANCE BARS — packet records ALL of: `argv_after_rewrite` (post Ring-0 CDX-D rewrite),
`managed_hook_confirmed` (bool + SHA), `cdxd_result`, `bypass_mode_source` (or `none`),
`remote_control_status` (disabled|brokered|explicit posture), `hook_requirements_sha`,
`hook_script_sha`, `lifecycle_sentinel_refs`, `ring1_smoke_result`.
- `ce launch --harness codex` refuses controller authority (downgrades foreman/read-only) when
  packet absent/incomplete — FAIL-CLOSED, failure-direction tests required (absent packet,
  incomplete packet, each missing field class).
- Packet written machine-readable under `.ce/state/controller-evidence/` so `ce takeover`
  (#477, ON MAIN as of today — reuse its evidence conventions incl. generated_at + host_id
  binding) can read it during succession.
- Absence of a `ce-stop-codex.py` closeout hook recorded in the packet as a known gap.
- REUSE the existing launch specs / CDX-D evaluator — wiring, not new governance surface.
Work class: story.
