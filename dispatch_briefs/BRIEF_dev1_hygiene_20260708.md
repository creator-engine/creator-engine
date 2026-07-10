# BRIEF — dev-1 — 2026-07-08 — 1 TINY unit (self-push lane): post-#891 hygiene pair

Branch `ce-891-hygiene-pair` (work class: XS or tiny). Base on FRESH origin/main
(must contain #891 merge). Self-push per your lane: full preflight (serialized,
TMPDIR=$HOME/tmp, -n 4) → push → PR with carrier+changelog+G5 body line.

1. Add the missing negative test cases in deploy/dgx-runsc/test-seat-logging.sh:
   relative-path rejection for CE_DGX_HOST_WORKTREE_ROOT and (via the vps assertions
   in the same harness) CE_VPS_HOST_WORKTREE_ROOT — mirror the existing
   assert_rejects_relative_log_dir pattern. Runtime guards already exist; only the
   negative tests are missing (noted at the #891 approval).
2. Sweep the pre-existing /home/cedev4 literals out of deploy/dgx-runsc/README.md —
   replace with $HOME / <seat-user> generic placeholders consistent with the rest of
   the doc (confidentiality hygiene; flagged at the #891 approval).

SCOPE: those two files + carrier/changelog ONLY. No launcher script changes.
STOP LINES: standard (no gate acts, no signing). Signal: PR number + head sha.
