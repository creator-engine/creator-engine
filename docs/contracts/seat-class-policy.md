# Seat-Class Policy

The `seat-class-policy-record` carries the deterministic Slice 1 defaults for
foreman delegation. A valid governed policy is foreman by construction:
`seat_class` and `default_seat_class` must both be `foreman`. The record also
declares depth-bounded foreman recursion and the mutation classes for which a
foreman must delegate implementation work.

Every valid record must include `foreman_dispatch` with `launch_pinned: true`, a
non-empty `contract_ref`, and dispatch surfaces for the `researcher`,
`implementer`, and `reviewer` roles. These surfaces are the explicit capability
names a foreman can use to dispatch substantive work instead of performing it
inline.

This slice arms `hook_check.py` for WARN-only observation: foreman seats that
attempt implementation work in delegation-required mutation classes are allowed
to proceed, with `wouldHaveDenied: true` and an advisory reason that names worker
delegation. Worker seats and coordination actions do not warn.

The live hook resolves runtime `seat_class` from the launch-pinned
brain-bootstrap payload when `CE_BRAIN_BOOTSTRAP_REF` and
`CE_BRAIN_BOOTSTRAP_SHA256` verify. Missing or invalid bootstrap evidence fails
closed to `foreman`; the governed policy record itself may not pin a worker
seat class.

The WARN-only arm does not hard-deny foreman implementation work, spawn workers,
flip enforcement, enforce action-count thresholds, or enforce line-count
thresholds. Existing hard-deny mechanics such as credential-path reads and
restricted deploy/egress actions remain authoritative and take precedence.
