# ce-ops#216 integrator escalation seam

- Added a pure v3 forge escalation seam that converts unresolved Unit 2
  resolver outputs into structured controller-action events.
- Escalation events carry repo/change identity, paths, resolver family, reason,
  evidence, severity, event kind, and UTC creation time for technical triage.
- Resolved and not-applicable mechanical resolver outputs do not escalate, while
  malformed unresolved outputs are refused instead of silently parked.
