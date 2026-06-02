# Governed Lane-Launch Protocol

**Status**: Gate 3 (SVC+RUN) normative protocol for the v1.0 `ce` kernel.
Part of the minimum repo-native delivery control plane. Layered onto, and
subordinate to, the Active-Work Ledger, Worktree Allocator, and Pane Registry
substrates. A fresh clone is sufficient to apply this protocol; no external
tracker credential or network state is required.

## a. Purpose

The governed lane-launch primitive is the v1.0 `ce` syscall that turns a
Source-ratified, pre-allocated lane into a **live, operator-visible** working
surface and records that surface as governance evidence. It closes the
traceability-matrix requirements:

- `RV1-030` — `ce lane launch` spawns/attaches a tmux pane, writes a Pane
  Registry record bound to a live Active-Work Ledger claim, and refuses any
  non-visible surface for a visibility-required role.
- `RV1-031` — `ce lane launch` verifies the consumed prompt/handoff pointer
  and its SHA256 before launch and refuses on mismatch **before any side
  effect**.
- `RV1-032` — `ce lane verify` checks the stop line and an optional completion
  report; `ce lane archive` hashes the transcript per
  [`./TRANSCRIPT_ARCHIVE_PROTOCOL.md`](./TRANSCRIPT_ARCHIVE_PROTOCOL.md);
  `ce lane status` reads live lane state.

This protocol is the prose contract for the `ce_cli`, `lane_runtime`,
`tmux_adapter`, and `transcript_archive` modules.

## b. Product boundary (Gate 3)

The lane-launch primitive is intentionally narrow:

- It is a Python `ce` kernel command family. It does **not** implement
  `ce launch` / `ce hud` (the Controller-seat launcher, Gate 6).
- Visible lanes use **tmux**. tmux is mandatory for v1.0 visible-lane
  authority; there is no CE-native TUI.
- It does **not** allocate worktrees or branches (that is `pco_allocate`).
- It does **not** start worker containers (rootless Podman, Gate 5) or run the
  Side-Effect Ledger runtime (Gate 4).
- It **never** launches a provider, model, or credentialed surface, and it
  never prints secrets, tokens, account identifiers, or environment variables.
- All runtime state lives under the ignored `.hermes/` boundary; the launch
  command writes only Pane Registry records under
  `.hermes/active-work-ledger/panes/`.

## c. Source-of-truth relationship

| Upstream source of truth | Role |
|---|---|
| [`./ACTIVE_WORK_LEDGER_PROTOCOL.md`](./ACTIVE_WORK_LEDGER_PROTOCOL.md) | The live, unreleased claim a launched lane must bind to. |
| [`./WORKTREE_ALLOCATOR_PROTOCOL.md`](./WORKTREE_ALLOCATOR_PROTOCOL.md) | `pco_allocator.guard` is reused as the pre-launch conflict guard (PCO-030). |
| [`./PANE_REGISTRY_PROTOCOL.md`](./PANE_REGISTRY_PROTOCOL.md) | The Pane Registry record shape and PCO-046..053 validity surface a launch writes and binds. |
| [`./TRANSCRIPT_ARCHIVE_PROTOCOL.md`](./TRANSCRIPT_ARCHIVE_PROTOCOL.md) | `ce lane archive` implements the archive/hash discipline. |
| [`./CONTROLLER_BOUNDARY_POLICY.md`](./CONTROLLER_BOUNDARY_POLICY.md) | Role-split and visible-surface rules the launch enforces. |

## d. `ce lane launch`

Required arguments: `--controller-id`, `--lane-id`, `--role`, `--prompt`,
`--prompt-sha`, `--repo-root`, `--ledger-root`. Optional: `--handoff` +
`--handoff-sha`, `--command`, `--host-id`, `--pane-id`, `--session`,
`--window`, `--worktree-path`, `--branch`, `--envelope-ref`, `--no-tmux`.
G2.002.1 operating-mode carriers (optional): `--operating-mode` (default
`strict`), `--autonomy-class`, `--lane-kind`, `--tenant-policy`,
`--ratification-evidence`. G2.007.3 reviewer-venue carrier (optional):
`--reviewer-authority-ref` (a reviewer-authority envelope ref for a distinct
reviewer venue; see step 0b and
[`./REVIEWER_VENUE_AUTHORITY.md`](./REVIEWER_VENUE_AUTHORITY.md) §4).

The launch sequence, **with every refusal raised before any side effect**:

0. **Operating-mode floor (G2.002.1).** `--operating-mode` defaults to `strict`.
   An unknown mode, autonomy class, or lane kind is refused
   (`G2-OPERATING-MODE-INVALID` / `G2-AUTONOMY-CLASS-INVALID` /
   `G2-LANE-KIND-INVALID`), as is an active `reserved_future_agent_ratification`
   autonomy (`G2-RESERVED-AUTONOMY-ACTIVE`). `auto` / `transcendence` are refused
   (`G2-AUTO-WITHOUT-OPERATOR-POLICY` / `G2-TRANSCENDENCE-WITHOUT-OPERATOR-POLICY`)
   unless `--tenant-policy` names an Operator-ratified operating-mode policy that
   ratifies the requested mode. A tenant policy that binds an active
   `agent_ratifier` (`G2-AGENT-RATIFIER-ACTIVE`) or names an agent/advisory role
   as a privileged ratifier (`G2-PRIVILEGED-RATIFIER-INVALID`) is refused in
   every mode. These carriers record posture only and mint no authority; the
   Operator-only privileged floor is preserved unchanged.
0b. **Reviewer-venue authority injection (G2.007.3).** When
   `--reviewer-authority-ref` is supplied, the lane must be a distinct reviewer
   venue — `--role reviewer` **and** `--lane-kind review`
   (`is_distinct_reviewer_venue`); otherwise refuse `G3-REVIEWER-VENUE-IDENTITY`.
   The ref must resolve (under `--repo-root` or as an absolute path) to a
   schema-valid reviewer-authority envelope; otherwise refuse
   `G3-REVIEWER-AUTHORITY-INVALID`. Both refusals raise before any side effect.
   On success the validated ref is exported into the pane environment as
   `CE_REVIEWER_AUTHORITY_REF` (via tmux `-e`, never printed) and the venue
   identity is recorded in the ignored governance sidecar; the in-band
   `.claude/hooks/ce-pretooluse.sh` forwards it to the validator as
   `--reviewer-authority-ref`, which injects `ce.reviewer_authority_ref` before
   `hook_check.build_context()`. Fail-closed: with no ref, no authority is
   carried and restricted mechanics stay denied.
1. **Prompt pointer + SHA (RV1-031).** The `--prompt` path must exist; its
   byte-level SHA256 must equal `--prompt-sha`. Refuse on missing path or
   mismatch.
2. **Handoff pointer + SHA (RV1-031).** When `--handoff` is supplied, the path
   must exist and its byte-level SHA256 must equal `--handoff-sha`.
3. **Visibility (RV1-030).** The visibility-required roles are `architect`,
   `implementer`, `reviewer`, and `verification`. A visibility-required role
   must launch a tmux terminal; `--no-tmux` (or any non-tmux terminal) is
   refused.
4. **Live claim binding (RV1-030).** A schema-valid, unreleased Active-Work
   claim must exist at
   `.hermes/active-work-ledger/claims/<controller-id>/<lane-id>.yaml` under
   `--ledger-root`, with matching `controller_id` and `lane_id`. Refuse on a
   missing, unreadable, invalid, released, or mismatched claim.
5. **Conflict guard (PCO-030).** `pco_allocator.guard(ledger_root)` is reused;
   refuse before any pane spawn or write when it reports a conflict.
6. **tmux availability (RV1-030).** For a tmux lane, the tmux binary must be
   available; refuse before the Pane Registry write when it is not.

Only after all refusals pass does the command produce side effects:

7. **Spawn/attach.** A tmux pane/window runs the requested local `--command`.
   When no command is supplied, a safe inert shell placeholder is used; a
   provider/model is never launched by default.
8. **Pane Registry write.** A Pane Registry record is written atomically
   (temp-file + rename; validators skip `*.tmp.*`) to
   `.hermes/active-work-ledger/panes/<controller-id>/<lane-id>.yaml`. The
   record sets `visibility: operator_visible`, `terminal.kind: tmux` with the
   live `session_id`/`window_id`/`pane_id`, binds `claim_ref` to the claim, and
   records `worktree_path`, `branch`, and `envelope_ref` from the claim when
   available plus the bound claim's `claim_record_sha256`. The generated record
   is validated against the Pane Registry schema before it is written.

### Governed Claude lanes: strict MCP config auto-provisioning

When `--command` is a `claude` invocation, the launcher pins the governed
command to `--strict-mcp-config` pointing at a CE-owned config
(`--mcp-config`, else `.hermes/<lane-id>/mcp/ce-mcp.json`). Because the lane runs
with `cwd` set to its worktree, that path must exist **inside the worktree** or
the governed seat cannot bind its MCP servers. The launcher therefore
**auto-provisions** the config before spawn (resolving the path against
`--worktree-path`, else the repo root): if nothing is present it writes the
default `{"mcpServers": {}}` payload (byte-identical to `ce init`); an existing
regular file is left untouched (an Operator- or launcher-supplied config wins);
and a non-regular file at the path is a fail-closed refusal (`CC-D-7`) before any
side effect — it is never clobbered. This removes the prior requirement to
pre-provision the worktree's MCP config by hand before launching a governed lane.

## e. `ce lane status`

Reads the Pane Registry record for `--controller-id`/`--lane-id` under
`--ledger-root` and emits a deterministic text summary by default, or
machine-readable JSON with `--json`. A missing record exits nonzero.

## f. `ce lane verify`

Required arguments: `--controller-id`, `--lane-id`, `--ledger-root`,
`--transcript`, `--stop-line`; optional `--completion-report`. The command
confirms the Pane Registry record exists, the transcript exists and contains
the exact stop line, and — when a completion report is supplied — that it
exists and declares the same stop line. It mutates no tracked files. Missing or
malformed evidence exits nonzero.

## g. `ce lane archive`

Required arguments: `--transcript`, `--archive-root`, `--batch-slug`,
`--role`; optional `--repo-root`. The command copies the transcript bytes
exactly into the archive root, computes the byte-level SHA256 per
[`./TRANSCRIPT_ARCHIVE_PROTOCOL.md`](./TRANSCRIPT_ARCHIVE_PROTOCOL.md), and
emits the archive path and hash. When the archive root is inside a git
repository it must be git-ignored; otherwise the command refuses before
writing. The transcript body is never written to a tracked file.

## h. Acceptance posture

This document satisfies the Gate 3 requirement to add a governed lane-launch
protocol:

- Names the launch refusal order and the live-claim binding in §d.
- Names the read/verify/archive surfaces in §e–§g.
- Names the locked product boundary in §b.
- Is exercised by strict RED→GREEN tests under
  `validators/tests/{unit,integration}` covering prompt/handoff SHA refusals,
  missing/released/mismatched claim refusals, headless and tmux-unavailable
  refusals, conflict-guard refusal, the pane-record write bound to a live
  claim, status reads, verify stop-line checks, and transcript hashing.
