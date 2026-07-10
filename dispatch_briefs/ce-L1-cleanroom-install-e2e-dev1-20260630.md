# SEED BRIEF — L1 clean-room install e2e (verify-path) — SEAT: dev-1

**Lane:** L1 onboarding go-live (HIGHEST, time-boxed today). **Mode:** verify-path-only (D2 ratified — do NOT need to grant any access; just prove the path works as a new user would experience it). **Role:** implementer/verifier. **Branch (only if you produce doc fixes):** `ce-L1-install-e2e-fixes` off CURRENT origin/main.

## Goal (self-contained)
Prove that the FIRST EXTERNAL TEST USER (Nitzan) can install Creator Engine end-to-end **today**, by doing a true clean-room install against the LIVE published installer exactly as a new user would — then report green/broken with evidence, and fix any documentation gaps you find.

## Do this
1. **Clean room.** Use a fresh, isolated environment (new throwaway dir + fresh venv, or a fresh container if available) with NO pre-existing CE checkout/state on PATH. Record the starting environment (OS, arch, python version).
2. **Follow the LIVE published path verbatim.** Fetch and follow `https://creator-engine.dev/llms-install.md` (the live install instructions) step by step, as written. Do NOT use any local repo shortcuts, your existing checkout, or insider knowledge — if a step is unclear or assumes context a new user lacks, that itself is a finding.
3. **Run the full path to a working `ce`.** Through to the point a new user would have a usable, governed `ce` install and could run a first command (e.g. `ce --version` / `ce status` / whatever the docs say to verify success).
4. **Capture evidence.** For every step: the exact command, and the real output (trim noise). Note any step that required manual intervention not in the docs, any error, any ambiguous instruction, any broken/stale link, any platform assumption (e.g. x86_64-only) that would block an aarch64/mac user.
5. **Verdict.** End-to-end GREEN (a new user succeeds unaided) — yes/no. If no, the precise first blocker.

## If you find doc/installer gaps
- For pure-docs/instruction fixes: make them on branch `ce-L1-install-e2e-fixes`, add carrier (`.ce/pr-manifests/ce-L1-install-e2e-fixes.md` via carrier_gen) + changelog, run FULL `ce validate-pr` GREEN, push, and report the PR number. Author≠approver — do NOT self-approve; the controller gates.
- For deeper installer/code gaps (not a quick doc fix): describe precisely in your report so the controller can file a ticket. Do NOT scope-creep into a big build under this brief.

## Stop line
This is verify-path + small-doc-fixes ONLY. Do NOT build L1.a clean-main-install or L1.b auto-track-main here (separate dispatch). Do NOT grant anyone access. Commit any doc fix with `git commit && echo <SHA>` and report the SHA + PR number. Report your evidence + verdict back to the controller.
