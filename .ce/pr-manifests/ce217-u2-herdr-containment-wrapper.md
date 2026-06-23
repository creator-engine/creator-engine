# PR path manifest — u2-herdr-containment-wrapper · ce-ops#217 U2 (Cockpit-on-herdr, Posture A)

Per-PR carrier (`.ce/pr-manifests/<branch-slug>.md`, the ce-ops#21 convention). CI runs:

```bash
verify-path-manifest --base <PR base sha> --manifest-dir .ce/pr-manifests --head-ref u2-herdr-containment-wrapper
```

and requires this PR's `base..HEAD` diff to equal exactly the authorized path-set below
(the carrier lists itself); the repo-wide fidelity scan requires the declared count and
SHA256 to match the fenced block.

Ratified gate:
Operator-ratified 2026-06-23 — Cockpit-on-herdr build, ce-ops#217, **Posture A**
(AGPL-3.0 source-available fork). Design-of-record
`.ce/state/research/DESIGN_COCKPIT_ON_HERDR_20260623.md` (§5 build decomposition, U2).
This PR is the **CE-SIDE containment-launch SPEC + a thin wrapper STUB ONLY** — no live
agent session is wired (that is U3); the AGPL `creator-engine/herdr-ce` fork is a separate
repo and is NOT in this diff.

Base:
`44fa40aac7716a9479c35e3c230a8732416441ff` (`origin/main`). The path-set + hash below are
satisfiable at this base.

The change:
U2 ships the CE-substrate containment-launch spec that runs the `creator-engine/herdr-ce`
AGPL multiplexer binary under CE's mandatory containment (bwrap/gVisor → OpenShell), with
the load-bearing **§7 keystone** pinned as a fail-closed invariant: the herdr control
socket is owned by the CE substrate/controller and **never handed to the governed seat**.
The pure plan asserts the invariants; the live launch is a fail-closed stub until U3.

Per-file purpose (the closed path-set — 4 paths):
- **`.ce/changelog/ce217-u2-herdr-containment.md`** *(A)* — the per-PR changelog fragment.
- **`.ce/pr-manifests/ce217-u2-herdr-containment-wrapper.md`** *(A)* — this carrier (self-inclusive).
- **`validators/creator_engine_validator/runner/herdr_containment.py`** *(A)* — the containment-launch spec: `plan_herdr_containment()` (pure, fail-closed on the §7 keystone) + `HerdrContainmentLaunch` (thin stub, `HerdrContainmentNotWired` until U3). Side-effect-free on import.
- **`validators/tests/unit/test_herdr_containment.py`** *(A)* — unit coverage pinning the U2 spec, the §7 fail-closed refusals, no-new-egress, and the stub's fail-closed launch surface.

Canonicalization:
`sha256("\n".join(sorted(unique_paths)) + "\n")`.

AUTHORIZED_PATHS_COUNT=4

AUTHORIZED_PATHS_SHA256=81e03d207b676a7be0c0b87f029bd6c0ac237a59be7f2fb8112bded46938b3df

```text
.ce/changelog/ce217-u2-herdr-containment.md
.ce/pr-manifests/ce217-u2-herdr-containment-wrapper.md
validators/creator_engine_validator/runner/herdr_containment.py
validators/tests/unit/test_herdr_containment.py
```
