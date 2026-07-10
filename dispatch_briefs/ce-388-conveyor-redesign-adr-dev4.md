# SEED BRIEF — ce-ops#388: Conveyor daemon security-redesign ADR (arm-safety-by-construction) — SEAT: dev-4

**Deliverable: a DESIGN ADR only (docs). NO changes to conveyor_daemon.py / conveyor.py**
(that code is in-flight on another branch — touching it collides). Branch `ce-388-conveyor-redesign-adr`
off origin/main, ADR under docs/adr/ following the existing numbering/format there.

**Context (self-contained — the problem):** The conveyor go-live daemon (harvest→validate→push→PR
loop) is meant to be ARMED to drive the autonomous fleet. Its security review took FOUR adversarial
rounds, each finding a NEW command-execution/escape class, because the daemon takes execution CONTROL
and CONTENT from an untrusted discovery payload (produced by a contained harvest seat):
- r1: `validate_command` from payload → subprocess argv (RCE).
- r2: `base` → `git rebase --exec`; `remote` → `git push ext::` transport (RCE).
- r3: `bundle_path` → `git fetch ext::`; `repo_path`/`worktree_path` used as unconfined cwd → attacker
  stages a repo whose `.git/config` sets origin=`ext::sh -c '…'` → bypasses the remote pin (RCE).
- r4: the r3 confinement check was TOCTOU — resolved path computed then discarded; downstream git ran
  on the raw payload path → post-check symlink swap re-opened r3 (RCE).
- Deeper (design-level, the reason patching isn't enough): the bundle CONTENTS are seat-authored.
  `land_bundle` does `git fetch <bundle>` importing arbitrary attacker-controlled tracked file content
  into the confined dir that `validate_command` (up to 600s) and the final `git push`/`gh pr create`
  then operate on. Confinement guarantees the filesystem LOCATION is trusted, NOT the CONTENT.

**Threat model to state explicitly:** the harvest seat is CONTAINED but capable and must be treated as
potentially compromised; anything it authors (payload fields AND bundle contents) is UNTRUSTED. The
daemon runs on a trusted host with push/PR authority — an RCE there is a full fleet compromise.

**The ADR must design arm-safety-BY-CONSTRUCTION, propose (with a recommended default per choice):**
1. **Payload = DATA ONLY.** Enumerate exactly which fields the daemon accepts from discovery
   (identifiers: issue #, branch name, PR title/body TEXT) and forbid all execution-control fields
   (commands, remotes, base refs, filesystem paths) — the daemon derives those from its own pinned config.
2. **Daemon-owned working dirs.** The daemon allocates its OWN working/staging dirs from a TRUSTED
   source (fresh clone/worktree off a daemon-pinned repo/remote) and runs ALL git/gh there — never in a
   directory a seat can influence. Specify who creates/owns these dirs and how the seat's bundle is
   brought in.
3. **Untrusted-content handling.** How the seat's bundle content is imported WITHOUT trusting it for
   execution: e.g. run validate_command with repo-local hook/config execution DISABLED
   (`git -c core.hooksPath=/dev/null`, `GIT_CONFIG_NOSYSTEM`, ignore repo-local `.git/config`/attributes),
   sandbox the validation step, treat the landed tree as untrusted INPUT to verification rather than a
   trusted checkout. Address: can a malicious tracked file (hook, config, build script the validator runs)
   still achieve execution?
4. **Remotes/base pinned & resolved only against the daemon-owned checkout.**
5. Independent security review + explicit arming criteria (what must be TRUE before G-N3 arming).
6. Migration note: what of the current disarmed daemon (validate_command/base/remote pins, path
   confinement, TOCTOU fix already landed) is reusable vs must be replaced.

**Ground it:** read the current design doc `.ce/design/conveyor-harvest-push.md` and the current
conveyor modules (READ-ONLY) to cite real function names/flow; cite the 4 findings above. Mark ADR
status: **Proposed — awaiting Operator ratification of the arm-safety model.**

**Branch:** `ce-388-conveyor-redesign-adr` (off origin/main, /var/tmp worktree — NOT /workspace).
**Role:** implementer (docs-only). **Work class:** S (docs). **Obligations:** ADR file + changelog
fragment `.ce/changelog/ce-388-conveyor-redesign-adr.md` + carrier `.ce/pr-manifests/ce-388-conveyor-redesign-adr.md`
(slug == branch, covers all changed paths; if a new ADR trips an ADR-index/docs-reconciliation gate,
add the index entry). Venv: use `.venv/bin/python -m ...`. Run FULL `ce validate-pr` GREEN in one pass
(PYTHONPATH=validators worktree source, not stale installed venv) before commit-for-harvest; note
stale-env discrepancies rather than chasing. Commit (do NOT push — controller harvests) + echo SHA.
Done-report = branch, SHA, files, preflight evidence, and a 3-line summary of the proposed model.
