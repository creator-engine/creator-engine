# Implementer brief — repair n15b current-main pairing and carrier

## Assignment

- Unit: N-15b composition probe, harvest repair only
- Starting head: `c0cbb62e164bcddd7c2940b631c7e78c12203d56`
- Required current main: `ed50aec89a02a610d675e735ca929c00c7cf6e57` or later
- Branch: `ce-n15b-composition-probe`
- Role: `.claude/agents/implementer.md`
- Worktree: `/var/tmp/wt-ce-n15b-composition-probe`
- Work class: `S`
- Network, push, PR, review, approval, and merge authority: none

## Exclusive write territory

- `validators/creator_engine_validator/composition_probe.py`
- `validators/tests/unit/test_composition_probe.py`
- `.ce/changelog/ce-n15b-composition-probe.md`
- `.ce/pr-manifests/ce-n15b-composition-probe.md`

No other path.  The apparent materializer deletions in the stale base-to-head
diff are pairing drift, not authorized changes.

## Repair

1. Verify the starting commit itself changes exactly the four authorized paths.
2. Force-refresh the remote tracking ref with
   `git fetch origin +refs/heads/main:refs/remotes/origin/main`.  Require
   `origin/main` to equal `ed50aec89a02a610d675e735ca929c00c7cf6e57` or a
   descendant.
3. Rebase the one implementation commit onto that exact current main.  If any
   conflict occurs, abort and report; do not synthesize a merge or edit outside
   the four paths.
4. Confirm `git diff --name-status origin/main..HEAD` contains exactly the four
   authorized paths and no reverse deletions from already-landed #958.
5. Regenerate the changelog/carrier through
   `carrier_gen.write_carriers(base="origin/main")`; do not hand-list or
   hand-hash it.  Carrier slug must equal the branch, declare class `S`, and
   contain the fenced four-path manifest.
6. Run focused `test_composition_probe.py`, the public-doc confidentiality
   guard, carrier verification, and `git diff --check`.  Preserve implementation
   semantics unless a focused failure proves a defect; stop before any scope
   expansion.

The detached pipeline runner currently owns the host-global full-suite slot.
Do not run full `ce validate-pr` concurrently.  Commit the mechanical
rebase/carrier repair only after focused green and report
`READY-FOR-REQUEUE ce-n15b-composition-probe <full-sha>`.  The controller will
requeue it through the surviving runner, which must produce full CI-parity green
before push/PR.  No push.

Standing preflight directive: the FULL local validator preflight (`ce validate-pr`,
CI-parity) is required before push; in this inherited pipeline the detached
runner is the serialized authoritative preflight owner.  Do not discover gates
via CI.

## Stop lines

Stop on conflict, unexpected main ancestry, any fifth path, red focused test,
credential need, or authority expansion.  Never edit `.github/**`, materializer
files/tests, brain ledger, deploy surfaces, or signed artifacts.

