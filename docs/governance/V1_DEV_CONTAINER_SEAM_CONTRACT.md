# Creator Engine — v1.1 Dev-Container Seam Contract (`V1_DEV_CONTAINER_SEAM_CONTRACT.md`)

Gate: **G1 — Canonical terminology + product-contract lock** (type: **DOC**; lint only).
Authored UTC: 2026-05-24T17:52:25Z.
Lane: Gate 1 documentation-only writer, visible tmux pane, Claude Code Opus 4.7, effort high.
Controlling roadmap: **Option B re-issued definitive roadmap**, SHA256
`5a7e5ba74adcaab32c892c3cf793384eec4f121a6991b1bd5bba34a30fd48e13` (§7).
Canonical baseline: live `refs/heads/main` = `36377f8c4caf6817e01d58072062eb5caccc164b`.
Requirement: **RV1-013** (`specs/_traceability_matrix.md`); decision lock: **DP-3 = B** (ADR-0001 §3).

> **Authority and scope.** This file records the v1.1 project-dev-container **seam** so that v1.0 does
> not block or complicate it later. It re-decides no Source lock and authorizes no implementation.
> **Deferred, not rejected.**

---

## 1. v1.0 containerization scope

v1.0 **containerizes worker/agent execution only**, with **rootless Podman** (rootful refused), under
the Worker-Container Policy: default-deny mounts; read-only unless explicitly `rw`; only the task
worktree + declared paths mounted; host home, broad host filesystem, and any container-engine socket
are **forbidden** mounts; credential allowlist carries **names only, never values**; the controller-key
private key is never injected into any worker; declared egress only; a single pinned, content-addressed
base image (SHA normative). The **host-local Controller seat is not containerized** in v1.0 — control
authority stays host-side; only work execution is isolated.

(Full statement: `docs/governance/V1_PRODUCT_CONTRACT.md` §1–§2; ADR-0001 §2–§3; roadmap §2.7.)

## 2. Full project-dev containerization is a v1.1 / POST-V1 seam

Full project-dev containerization — **`ce dev shell` and `ce dev run` are a v1.1 / post-v1 seam, not
v1.0**. It is **deferred, not rejected**. v1.0 records the seam now so a future `ce dev shell` /
`ce dev run` can be added cleanly in v1.1+ without v1.0 rework. (Restated for grep fidelity:
`ce dev shell` and `ce dev run` are a v1.1 / post-v1 seam, not v1.0.)

- **No `ce dev` command is part of v1.0.** v1.0 must **not** bind `dev` to any other meaning; the
  `ce dev …` namespace is **reserved** for the deferred project-dev container. No `ce dev` command is
  added in v1.0 **unless Source later reopens the boundary** by a fresh decision.
- v1.0 docs (G8, RV1-081) state the deferral explicitly: **mandatory project-dev containerization is
  deferred to v1.1, not rejected.**

## 3. Seam predicates for later v1.1

The v1.1 `ce dev shell` / `ce dev run` project-dev container must satisfy these seam predicates, each
designed to compose with v1.0 boundaries rather than overwrite them:

1. **Isolation.** The dev container occupies a **fourth, distinct boundary** that composes with — and
   never overwrites — the three v1.0 boundaries: host Controller state (host-local), worker/container
   state (`.hermes/workers/`, rootless Podman), and the project workspace (the allocated worktree). It
   reuses the v1.0 Worker-Container Policy as a **dev-profile** of the same isolation model (rootless,
   default-deny mounts, names-only credentials, declared egress, pinned content-addressed base image) —
   not a new isolation model.
2. **Reproducible dev shell.** The dev shell is reproducible under the same offline contract as v1.0
   (uv-first install, `uv.lock` + offline cp314-only wheelhouse; no network fetch under kernel
   authority). The dev environment is built deterministically, not improvised.
3. **No authority bypass.** Entering `ce dev shell` / `ce dev run` grants **no** governance authority:
   it does not ratify, enqueue, land, merge, push, or approve, and it does not exempt any operation
   from Source ratification. Governed lanes are still launched only through `ce lane launch`
   (visible-pane, Pane-Registry-recorded); work performed inside a dev container has authority only
   through the same governed surfaces.
4. **No hidden Controller seat.** The dev container must **not** become a hidden Controller seat. The
   Controller seat remains the host-local harness TUI launched/attached by `ce launch`; a dev container
   is a development workspace, never the kernel and never an out-of-band seat. There is no hidden
   continuation.

## 4. Forward-compatibility with the governed-environment guard

The v1.0 governed-environment guard predicate (DP-3 = B) is designed so the v1.1 dev container is a
**detectable, validatable PASS branch**: the same predicate that today asserts "not an ungoverned host"
gains a "governed dev-container" PASS branch in v1.1. The v1.1 dev profile is therefore additive to the
guard, not a replacement
(`docs/governance/V1_GOVERNED_ENVIRONMENT_GUARD_REQUIREMENT.md` §2, §4).

## 5. References

- `docs/adr/ADR-0001-v1-baseline-and-product-form.md` §3 — DP-3 = B + v1.1 seam add-on (deferred, not rejected).
- `docs/governance/V1_PRODUCT_CONTRACT.md` §2–§4 — DP-3 = B, IN/SEAM/POST-V1 classification.
- `docs/governance/V1_GOVERNED_ENVIRONMENT_GUARD_REQUIREMENT.md` — forward-compatible guard PASS branch.
- `docs/governance/V1_CANONICAL_TERMINOLOGY.md` §2, §6 — Controller seat, governed environment.
- `specs/_traceability_matrix.md` — RV1-013 (this doc).
- `specs/_assumptions.md` §5 — v1.1 dev-container seam (deferred, not rejected).
- Option B re-issued roadmap §7 (v1.1 dev-container seam), §8 (team-mode track) — `5a7e5ba7…`.
