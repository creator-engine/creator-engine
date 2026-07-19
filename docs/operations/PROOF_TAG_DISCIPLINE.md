# Proof-Tag Discipline for Operator-Facing Claims

**Status**: ratified operating doctrine, 2026-07-19.

Proof-tag discipline governs every factual claim made in an Operator-facing
report — a Completion Report, a status update, a triage decision, or any
other artifact whose reader may act on it without independently re-deriving
the underlying fact. Each factual claim carries exactly one of three tags:
`[CONFIRMED]`, `[STATIC-VERIFIED]`, or `[OP-PROOF-REQ]`.

`[CONFIRMED]` marks a claim verified live in the current session: a command
was run, its output was observed, and the claim states what was observed.
`[STATIC-VERIFIED]` marks a claim verified against code, configuration, or
artifact content rather than live behavior — the claim is grounded in a file
that was read, not a system that was exercised. `[OP-PROOF-REQ]` marks a
vendor claim, an inherited assumption, or any other unverified assertion
that needs Operator-visible proof before anyone relies on it.

Untagged claims in a decision-bearing report are treated as `[OP-PROOF-REQ]`
by default. Silence about verification is not a fourth, weaker tag; it is
the strongest caution the taxonomy has, because an absent tag cannot be
distinguished from an author who forgot to check.

Tags apply at claim granularity, not paragraph granularity. A paragraph that
mixes an observed command result with an inherited assumption carries two
tags, one per claim; tagging the paragraph as a whole hides which half is
actually proven. A report with one claim per line tags trivially; a denser
report still owes each distinct factual assertion its own tag.

The tag names the verification that was performed, not the author's
confidence in the outcome. A `[CONFIRMED]` claim can still be wrong — the
tag says a live check happened, not that the result was favorable. An
`[OP-PROOF-REQ]` claim can still be true — the tag says no Operator-visible
proof exists yet, not that the claim is doubted. Confidence language belongs
in prose; the tag is a verification-method fact.

Origin: adopted from an external solo-harness workflow analysis and ratified
2026-07-19. This document is the tracked prose statement of the doctrine; it
does not itself define a new schema or validator check.
