# REWORK BRIEF — PR #774 ce-437-portability-guard (queued for dev-3 when free)

Ticket: ce-ops#437 slice 2 rework. Branch: ce-437-portability-guard (PR #774, live head 6c973b38).
Role: implementer. Work in a fresh worktree off the PR head commit 6c973b3807e75e03276582f61b31b65438d15d5f
(NOT off origin/main — rework harvest cherry-picks only NEW commits onto the live PR head).

Review verdict: CHANGES_REQUESTED (full text on PR #774). Two blocking fixes:

1. checks/portability_plane.py:35 — SUBPROCESS_COMMAND_RE is ^-anchored to bare
   systemctl|setfacl|journalctl; SYSTEMD_RE word-matches only `systemd`. False negatives:
     subprocess.run("sudo systemctl restart ce-broker", shell=True)
     subprocess.run(["/usr/bin/systemctl", "restart", "ce-broker"])
   Fix: detect the command tokens with prefix tolerance (sudo / env wrappers / absolute paths),
   anywhere in command position within string/list literals. Keep tokenizer-based
   comment/docstring exclusion unchanged. Add BOTH lines above as regression test fixtures.
   Re-run the guard on the whole tree after widening — if new true positives surface in
   control-plane files, extend the manifest baseline (dated, reasoned, separate commit); do NOT
   weaken the pattern.

2. test_portability_plane.py — add fail-closed tests: (a) missing manifest → check FAILS,
   (b) malformed manifest (wrong types) → FAILS, (c) stale baseline exemption (entry no longer
   matches source) → FAILS or is reported, matching implemented behavior in _load_manifest/run().

Optional (non-blocking, include if trivial): enforce YYYY-MM-DD on exemption `date`; in-code
comment on the deliberate whole-file self-exemption.

Obligations: update .ce/changelog/ce-437-portability-guard.md fragment; FULL `ce validate-pr`
GREEN one pass before commit-for-harvest; no push (contained) — signal exactly:
READY-FOR-HARVEST ce-437-portability-guard <40-hex-sha> REWORK
Stop line: no changes outside validators/creator_engine_validator/checks/portability_plane.py,
validators/tests/unit/test_portability_plane.py, surfaces/portability-plane-manifest.yaml,
.ce/changelog/ce-437-portability-guard.md.
