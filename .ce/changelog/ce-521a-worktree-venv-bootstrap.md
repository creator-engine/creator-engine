## ce-521a-worktree-venv-bootstrap

- Added linked-worktree validator Python resolution that reuses the main checkout `.venv` instead of building duplicate per-worktree environments.
- Updated local PR preflight defaults so contained worktrees can run validator and pytest commands through the shared main venv when `CE_VALIDATOR_PYTHON` is unset.
- Added focused unit coverage for shared venv resolution, linked-worktree detection, explicit env precedence, and fail-closed repair guidance.
