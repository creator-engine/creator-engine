# Fleet model routing — GPT-5.6 adoption

Operator-ratified 2026-07-10. This confidentiality-clean transcription is the
checked-in source cited by the launch-wrapper policy. It contains no seat
identifiers, credentials, or controller-specific routing state.

## Ratified routing table

| Tier | Model · effort | Applies to |
|---|---|---|
| Seat default | **gpt-5.6-terra · high** | All contained seats and implementation units |
| Escalation | **gpt-5.6-sol · medium** | Authority-adjacent code only (gate, broker, wall, signing surfaces), controller-approved per unit |
| Agent-organs / verify | **gpt-5.6-luna** | Mechanical/advisory organs: routine adjudication, triage, and verify-class chores |
| Deferred | terra · xhigh | Not adopted; decide only after the terra-high canary and a comparative unit versus sol-medium |

## Binding constraints

- Every fleet model has a minimum reasoning effort of `medium`; a `low`
  request is clamped and warned at the launch boundary.
- Luna is an explicit verify/mechanical/advisory-organ tier. It must never
  launch a foreman or persistent seat session.
- Terra/high is the standing contained-seat policy. Recreate-on-relaunch
  strips stale raw model/effort argv and reasserts that pair.
