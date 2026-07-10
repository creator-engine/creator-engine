# WORK CLAIM — ce-ops#279 surfaces/render.py (rented-surface governance Phase 4)

**Seat:** dev-3 (VPS contained). **Role:** implementer-foreman.
**You are born a foreman** — fan subtasks out to your own threads/workers where it helps; don't single-thread inline.

## Branch
```
git fetch origin && git checkout -b ce-279-surfaces-render origin/main
```

## Goal (self-contained — do not rely on reading ce-ops)
Implement **`surfaces/render.py`** — a render script that reads `surfaces/manifest.yaml` and emits two artifacts, making the manifest the single authoritative source for both build-time and runtime surface versions:
- `render.py build-args` → stdout: `--build-arg HERDR_SHA=ff924966 --build-arg ZIG_VERSION=0.15.2 …` (for `docker build`)
- `render.py launch-env` → stdout: `export CE_CODEX_VERSION=0.141.0` / `export CE_HERDR_SHA=ff924966` … (sourced by seat launch)

Read `surfaces/manifest.yaml` for the actual schema/fields before coding.

## Validation in render.py
- FAIL with a clear error if any required field is `null` for a surface type expected non-null at build/launch time (exit non-zero).
- WARN (non-fatal) if host-only surfaces (OpenBao / gVisor) are null.

## Integration points (be COMPATIBLE; do NOT implement these callers now)
- `ce surfaces fleet-rollout` (ce-ops#278) will call `render.py launch-env`.
- CI image build (ce-ops#280) will call `render.py build-args`.

## Acceptance criteria
- `build-args` emits a valid `--build-arg KEY=VAL` string for every non-null manifest surface entry that maps to a Dockerfile ARG.
- `launch-env` emits a valid `export KEY=VAL` block for all surfaces.
- Script exits non-zero on missing required fields.

## Allowed paths (nothing else)
`surfaces/render.py`, `surfaces/**` (test fixtures only), `validators/tests/**` (tests for render.py), `.ce/changelog/**`, `.ce/pr-manifests/**`.

## Evidence (DoD)
Run the FULL local preflight `ce validate-pr` (CI-parity, full suite — NOT `-m "not slow"`) GREEN. Declare the work-size class the G5 size gate will DERIVE (rename/relocation-aware — see the rule behind ce-ops#335).

## Stop-line
- Preflight GREEN + self-push works → push `ce-279-surfaces-render` and open ONE PR referencing ce-ops#279. Do NOT approve / merge / enqueue.
- Preflight GREEN but push FAILS (contained-seat auth gap, ce-ops#337) → STOP and report exactly: `READY-FOR-HARVEST: branch ce-279-surfaces-render, <N> commits, preflight GREEN`.
- Preflight RED → STOP and report the failing gate. Do not thrash.
