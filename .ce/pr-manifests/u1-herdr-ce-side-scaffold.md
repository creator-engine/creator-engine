# PR path manifest — u1-herdr-ce-side-scaffold · ce-ops#217 U1 (Cockpit-on-herdr, Posture A)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref u1-herdr-ce-side-scaffold
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified gate:
Operator-ratified 2026-06-23 — Cockpit-on-herdr build, ce-ops#217, **Posture A**
(AGPL-3.0 source-available fork). Design-of-record
`.ce/state/research/DESIGN_COCKPIT_ON_HERDR_20260623.md` (§5 build decomposition, U1).
This PR is the **CE-SIDE scaffold ONLY** — the AGPL `creator-engine/herdr-ce` fork is a
separate repo (see below) and is NOT in this diff.

Base:
`44fa40aac7716a9479c35e3c230a8732416441ff` (`origin/main`). The path-set + hash below are
satisfiable at this base.

The change:
U1 lays the foundation for Cockpit-on-herdr without wiring anything live. It adds the
CE-side integration-seam scaffold that will drive the herdr-ce AGPL fork over its JSON
Unix socket (replacing `tmux send-keys` and the creator-engine#368 `pty.fork` backend),
documents the HARD AGPL governance boundary, and marks the #368 PTY backend
superseded-in-principle (kept live; U3 retires it).

Per-file purpose (the closed path-set — 6 paths):
- **`.ce/pr-manifests/u1-herdr-ce-side-scaffold.md`** *(A)* — this carrier (self-inclusive).
- **`.ce/changelog/ce217-u1-herdr-ce-scaffold.md`** *(A)* — the per-PR changelog fragment.
- **`docs/architecture/HERDR_GOVERNANCE_BOUNDARY.md`** *(A)* — the LOAD-BEARING AGPL firewall / §7 boundary doc: CE's Python governance stack is a SEPARATE PROCESS over herdr's socket, never linked into the AGPL Rust binary.
- **`validators/creator_engine_validator/runner/herdr_session.py`** *(A)* — the CE-side adapter scaffold (`HerdrSession`: connect / spawn-pane / send / attach / observe), fail-closed with `HerdrNotWired` until U3/U4.
- **`validators/creator_engine_validator/seat_pty_session.py`** *(M)* — marked SUPERSEDED-IN-PRINCIPLE by the herdr seam (doc note + `TODO(ce-ops#217 U3)`); `pty.fork` path kept live, retired by U3.
- **`validators/tests/unit/test_herdr_session.py`** *(A)* — placeholder unit coverage pinning the U1 interface + fail-closed contract.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=6

AUTHORIZED_PATHS_SHA256=56613e0b570f20c73379801cff8d575a7e2a8330bf0ee8a72c33546a59ccd2c0

```text
.ce/changelog/ce217-u1-herdr-ce-scaffold.md
.ce/pr-manifests/u1-herdr-ce-side-scaffold.md
docs/architecture/HERDR_GOVERNANCE_BOUNDARY.md
validators/creator_engine_validator/runner/herdr_session.py
validators/creator_engine_validator/seat_pty_session.py
validators/tests/unit/test_herdr_session.py
```
