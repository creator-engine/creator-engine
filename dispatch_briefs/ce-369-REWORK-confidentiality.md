# REWORK: ce-369-denylist-from-ssot — CONFIDENTIALITY-STOP at harvest (branch was NOT pushed)

Your branch f39e3391 was blocked at the controller's confidentiality gate. Finding: the snapshot
uses UNSALTED hashlib.sha256(value.casefold()) (scripts/gen_identity_denylist.py::_artifact_doc and
identity_denylist.py::digest_token) and the committed artifact publishes token_lengths. Unsalted
digests over short, convention-derived identifiers are dictionary-reversible — this fails the
ratified "non-recoverable representation" bar (same exposure class as the original reverted leak,
one layer removed). Your plaintext handling was otherwise correct (literal scan clean, old
plaintext INTERNAL_LITERAL_TOKENS removal is good, d1b-39 supersede well-formed).

## Fix — two acceptable designs, DEFAULT = (1):
1. (DEFAULT) CI-derived gitignored artifact: do NOT commit the denylist. Generator runs where the
   registry is available and writes a gitignored runtime artifact; the guard fails-open-with-warning
   (or skips with explicit advisory) when the artifact is absent. No hashes in the repo at all.
2. Keyed MAC: HMAC-SHA256 with a key held OUTSIDE the repo (env-var at generation+verify time,
   OpenBao-provisioned). Only if (1) is architecturally worse for the guard's call sites — justify
   in the changelog if you pick this.
Either way: REMOVE token_lengths (and any other distribution metadata) from anything committed.

## Ledger note — LANE REORDERED
Another supersede round (d1b-10/11/12 v4) is landing on main before you. When your rework is ready:
re-merge origin/main, your d1b-39 supersede pair stays but RECOMPUTE the drift-test active-count
from the post-merge baseline (do not assume 76→77; verify and report the numbers).

## Evidence + stop line (unchanged)
Full ce validate-pr GREEN (ssh-keygen exception rule), commit, then:
`READY-FOR-HARVEST ce-369-denylist-from-ssot <full-sha> preflight=<...> count=<n>`
No push, no PR, no other ledger edits.
