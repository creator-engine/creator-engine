# Controller

## What It Does

Defines controller actions for dispatch, merge-gate, seat-refresh, and
courier-forge-op.

## When To Use

Use this playbook when a controller must send governed work to a seat, decide
whether a PR can merge, refresh a low-context seat, or bridge a contained seat's
forge operation through an uncontained courier.

## Preconditions (DoR)

- The controller has the ticket, branch, PR, or operation target.
- Work claim and dispatch authority are explicit.
- Merge-gate has independent review and green validation evidence.
- Courier-forge-op has a contained seat draft and an uncontained courier that
  can execute as the seat identity via the held token.

## Outputs (DoD)

- Dispatch brief and work claim are recorded.
- Merge decision is grounded in independent review, green checks, and
  ratification.
- Seat-refresh emits a resume state and restart instruction.
- Courier-forge-op records the drafted operation, signal, courier execution,
  and sunset note for ADR-0007 model-b.
