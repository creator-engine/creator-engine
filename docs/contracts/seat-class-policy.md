# Seat-Class Policy

The `seat-class-policy-record` carries the deterministic Slice 1 defaults for
foreman delegation. The record declares the launch-pinned `seat_class`, the
fail-closed `default_seat_class: foreman`, depth-bounded foreman recursion, and
the mutation classes for which a foreman must delegate implementation work.

This slice arms `hook_check.py` for WARN-only observation: foreman seats that
attempt implementation work in delegation-required mutation classes are allowed
to proceed, with `wouldHaveDenied: true` and an advisory reason that names worker
delegation. Worker seats and coordination actions do not warn.

The live hook resolves `seat_class` from the launch-pinned brain-bootstrap
payload when `CE_BRAIN_BOOTSTRAP_REF` and `CE_BRAIN_BOOTSTRAP_SHA256` verify.
Missing or invalid bootstrap evidence fails closed to `foreman`.

The WARN-only arm does not hard-deny foreman implementation work, spawn workers,
flip enforcement, enforce action-count thresholds, or enforce line-count
thresholds. Existing hard-deny mechanics such as credential-path reads and
restricted deploy/egress actions remain authoritative and take precedence.
