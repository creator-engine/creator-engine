# Merge Gate

Confirm independent review, green required checks, and ratification. If any
gate is missing, do not merge. If all gates pass, execute only the ratified
merge action and record the closeout.

## Preflight precondition (before EVERY push, no exemptions)

`ce validate-pr` — the full CI-parity offline suite, whole tree, run on a CLEAN
working tree — MUST go green locally before any PR is pushed: feature PRs,
release / publish PRs, AND controller-authored PRs alike. There is no "it's just
a release / signature ceremony" exemption; a release-publish PR is still a code
change to the install spec and must pass the offline suite first. The offline
suite mirrors `.github/workflows/validate.yml`, so a local green ≈ CI green;
pushing without it wastes a forge round-trip and surfaces failures publicly. See
[`../../../docs/operations/AUTHOR_A_CE_VALID_PR.md`](../../../docs/operations/AUTHOR_A_CE_VALID_PR.md)
for the standing directive and the #603 cautionary example.
