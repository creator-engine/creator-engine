# Merge Gate

Confirm independent review, green required checks, and ratification. If any
gate is missing, do not merge. If all gates pass, execute only the ratified
merge action and record the closeout.

## Authoritative validation evidence

Do not run full local `ce validate-pr` as a standing pre-push, harvest,
controller, or merge-gate prerequisite. Push the committed current head; wait
for required Validate checks; require independent review and ratification.
Record the pushed head SHA and required Validate run URL/status for that exact
head (or required synthetic merge-group head). Local full-suite transcripts are
not accepted as gate evidence; targeted author tests are optional iteration
evidence and cannot substitute for required CI. `ce validate-pr` remains an
optional diagnostic.
