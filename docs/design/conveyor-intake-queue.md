# Conveyor Intake Queue

The conveyor intake queue is a file-backed list of ticket units that are ready for dry-run dispatch planning.
It lives by default under `.ce/state/conveyor-daemon/intake-queue/`, or under `CE_CONVEYOR_INTAKE_QUEUE_ROOT` when configured.
The queue has three state directories: `pending/`, `claimed/`, and `done/`.
Controllers stock `pending/` with one YAML unit file per ticket, named `{priority:05d}-{unit_id}.yaml`.
Lower numeric priority sorts first, so the daemon can plan FIFO work by lexicographic filename order.
This slice ensures the queue directories exist, reads `pending/`, and logs `WOULD_DISPATCH` plans for idle seats.
It never claims queue files, sends pane text, writes sockets, or launches seat subprocesses.
The feature is gated by `CE_CONVEYOR_INTAKE_ENABLED=1`; absent that flag, daemon behavior is unchanged.
Live dispatch, claiming, and seat handoff are slice-2 scope.
