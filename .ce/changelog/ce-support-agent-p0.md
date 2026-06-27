---
slug: ce-support-agent-p0
date: 2026-06-27
kind: feature
scope: support-agent
issue: ce-ops#317
---

**`ce ask` support-agent P0 foundations (honest scaffold — substrate only).**

First slice of the doc-grounded `ce ask` support agent
(`.ce/state/research/CE_SUPPORT_AGENT_PLAN_20260627.md`). Builds the substrate;
model wiring + eval are later tickets.

- **P0.1 corpus allowlist.** `support_corpus_allowlist.yaml` declares the
  product-lens "Serve" source set; `support_corpus.py` computes the eligible
  corpus as the **intersection** of product-lens ∩ confidentiality-clean,
  reusing the single-sourced #571/#306 `public_docs_confidentiality` module (no
  fork). Fail-closed via the new `scan-support-corpus` check (wired into
  `ce validate-pr`): a listed doc that is not confidentiality-clean fails.
- **P0.3 read-only profile.** `support_profile.py` configures the Ring-1/Ring-2
  PreToolUse gate as deny-by-default read-only — denies writes/exec/network/`ce`
  subcommands, restricts reads to the corpus root, denies secret paths — reusing
  `hook_check.HookDecision` / `SCOPE_TOOLS` / `is_secret_path`.
- **P0.4 `ce ask` / `ce support` subcommand (dev-gated).** Registered in
  `ce_cli.py` as an honest scaffold ("support agent not yet available
  (scaffold)") that never fabricates an answer. Hidden from `ce --help` via
  `INTERNAL_COMMAND_GROUPS`, per the internal-then-public doctrine.
- **P0.5 system-prompt contract.** `support_system_prompt.md` — the
  cite-or-refuse / "I don't know" / product-lens-only / read-only contract.
