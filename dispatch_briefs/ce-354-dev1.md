# BRIEF — dev-1 — Support agent Phase-1: `ce ask` → functional internal pilot (ce-ops#354)

Born-foreman, non-contained (SELF-PUSH as ce-dev-1). Drive to a green PR. This is a substantive feature — read the design SSOT first and stay governed.

## READ FIRST (design SSOT)
`.ce/state/research/CE_SUPPORT_AGENT_PLAN_20260627.md` (the full plan: architecture, corpus, model choice, grounding method, governance, phased build). Also study the shipped P0 substrate you are completing: `support_runtime.py` (the honest scaffold you replace), `support_corpus.py` (eligibility), `support_corpus_allowlist.yaml`, `support_system_prompt.md` (the cite-or-refuse contract), `support_profile.py` (the read-only PreToolUse gate), and how `ce ask`/`ce support` call `run_cli` in ce_cli.py.

## Goal
Turn the honest scaffold into a WORKING internal pilot: `ce ask "<question>"` returns a CITED, product-lens answer grounded in the allowlisted corpus, or a clean "I don't know" when ungrounded. Stays DEV-GATED (internal). Phase-2 eval + public graduation are OUT OF SCOPE (reference as follow-ons).

## Branch
`ce-354-support-agent-phase1` off CURRENT origin/main (git fetch origin main first). Fresh worktree.

## Scope (two pieces)
1. **P0.2 docs→skill-bundle projector** (the prerequisite skipped in P0): a module that takes the corpus that `support_corpus.py` deems eligible (product-lens ∩ confidentiality-clean) and projects it into a skill bundle a fresh-context seat can load. Deterministic, read-only.
2. **Model wiring in `support_runtime.py`**: replace the scaffold so `run_cli` actually answers — launch a GOVERNED fresh-context answering seat (Sonnet 4.6 per the plan) with: the projected corpus-as-skills, the existing `support_system_prompt.md` as the system-prompt contract, and the `support_profile` read-only PreToolUse gate enforced (deny-by-default writes/exec/network; read restricted to corpus roots). Return the model's CITED answer or "I don't know". You MAY choose the invocation mechanism that fits the codebase (governed subprocess vs SDK/API) — but the governance properties below are non-negotiable.

## GOVERNANCE INVARIANTS (non-negotiable — this is a user-facing agent)
- CITE-OR-REFUSE: every answer cites a corpus source, or refuses with "I don't know" — never fabricate. (The system prompt enforces this; your wiring must not bypass it.)
- READ-ONLY: the answering seat runs under `support_profile` — no writes, no exec, no tool-network, no `ce` subcommands; reads restricted to the corpus roots. The ONLY permitted egress is the answering model call itself (the support agent's own inference), exactly as the plan specifies — do not widen it.
- PRODUCT-LENS / ZERO-LEAK: answers draw ONLY from the allowlisted product-lens corpus; no internal docs, no ce-ops# refs, no internal identities/topology in answers.
- DEV-GATED: `ce ask`/`ce support` stay in INTERNAL_COMMAND_GROUPS (hidden from `ce --help`). Do not graduate to public.

## Allowed paths (HARD limit)
- `validators/creator_engine_validator/support_runtime.py` (replace scaffold with real wiring)
- a NEW projector module e.g. `validators/creator_engine_validator/support_bundle.py`
- `validators/tests/unit/test_support_agent_phase1.py` (NEW) + you MAY extend the existing support test file
- `.ce/changelog/ce-354-support-agent-phase1.md`, `.ce/pr-manifests/ce-354-support-agent-phase1.md`
- ce_cli.py ONLY if `run_cli`'s signature must change (minimal; another seat is NOT in ce_cli right now but keep edits tiny + confined to the ask/support handlers). If `run_cli` is already the entrypoint, NO ce_cli change is needed — prefer that.
Do NOT touch the broker, forge/, automerge, or any unrelated module.

## Tests
- The projector yields a bundle from the eligible corpus (and EXCLUDES anything not eligible / on KNOWN_PENDING).
- `ce ask` cite-or-refuse: a grounded question yields a cited answer (mock the model to return a canned cited response — assert the citation/grounding plumbing, not live model output); an ungrounded question yields "I don't know".
- The read-only profile is applied to the answering seat (assert the profile/gate is wired, deny-by-default holds).
- Offline-safe tests (mock the model; no live model call in the test suite).

## SCOPING-DOWN ALLOWANCE
If full model wiring is too large for one clean, green slice, deliver the **projector (P0.2) + the smallest real answering path with the governance invariants intact**, and clearly note in the PR what is deferred to a follow-on. A working narrow pilot > a broken broad one. Do NOT fake green.

## Evidence
- FULL preflight GREEN: `rm -rf validators/*.egg-info validators/build; TMPDIR=/var/tmp PYTHONPATH=validators python -m creator_engine_validator.ce_cli validate-pr --head-ref ce-354-support-agent-phase1`
- Carriers via carrier_gen (dashed slug); single carrier; manifest+body `- **Declared work class:** feature` (model wiring + projector + tests).
- SELF-PUSH as ce-dev-1, open PR (mention ce-ops#354, parent #317), report PR# + SHA + what (if anything) is deferred. Governance invariants intact; dev-gated. No approve/merge. Stay in allowed paths.
