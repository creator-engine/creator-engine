---
slug: ce220-harness-matrix
date: 2026-06-23
kind: added
scope: harness-support capability matrix
issue: ce-ops#220
---

Adds `ce harness-matrix` — the PROBED single source of truth for which agent
harnesses CE governs and to what extent (ce-ops#220). The matrix is the antidote
to the containment-probe incident (ce-ops#221): governance state must be
DERIVED/probed, never hand-asserted in prose.

- Emits a HARNESS x CAPABILITY matrix (rows: `claude`, `codex`, `lane`; columns:
  Ring-0 launch envelope/cred-scrub, Ring-1 per-tool-call hook, Ring-2
  Stop/closeout, containment, status rollup) DERIVED by inspecting the live
  adapter specs and committed config at runtime, so the matrix can never drift
  from the governance reality the code enforces.
- Every cell carries a provenance note naming the file that proves it; a
  capability that is asserted-but-unverifiable is flagged explicitly (the
  containment cell, whose live gVisor/OpenShell launch is the fail-closed herdr
  U2 stub, is marked `deferred` + unverified — exactly the cell a false
  "contained gVisor" prose claim would have failed).
- Derives claude Ring-1 = `present` from the committed `.claude/settings.json`
  PreToolUse hook-pack, and codex Ring-1 = `managed-non-bypassable` from the
  committed `.codex/requirements.toml` pinning `allow_managed_hooks_only` (else
  the cell is `none`/`present` + unverified — never `managed` on a prose claim).
- Emits Markdown (default) and JSON (`--json`).
- Adds unit coverage asserting the derived-not-hardcoded invariants: claude
  Ring-1 = `present` only with a backing PreToolUse pack, codex Ring-1 =
  `managed-non-bypassable` only with the committed pin, and no capability is ever
  reported present without a backing file.
