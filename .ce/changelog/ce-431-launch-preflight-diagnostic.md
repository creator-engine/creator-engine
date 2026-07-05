# CE-431 launch preflight diagnostic

- Added `ce launch --preflight` / `ce hud --preflight` to evaluate launch pre-spawn gates without sentinel writes, seat-surface archive/rename, tmux creation, ledger writes, or runtime/container launch.
- Shared live launch gate evaluators with the diagnostic path for harness governance, runtime-policy/resource parsing, seat-surface reuse, and resource-bounding refusal messages.
- Regenerated the committed CLI reference for the new launch flag.
