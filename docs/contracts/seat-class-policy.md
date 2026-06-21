# Seat-Class Policy

The `seat-class-policy-record` carries the deterministic Slice 1 defaults for
foreman delegation. The record declares the launch-pinned `seat_class`, the
fail-closed `default_seat_class: foreman`, depth-bounded foreman recursion, and
the mutation classes for which a foreman must delegate implementation work.

This contract is shape-only for this slice. It does not arm `hook_check.py`,
spawn workers, enforce action-count thresholds, or enforce line-count thresholds.

