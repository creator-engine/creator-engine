# CE harness-support capability matrix

This is the authoritative CE harness-support matrix. It is rendered from `creator_engine_validator.harness_matrix`; `*` marks a cell whose support is deferred or otherwise not verified by committed wiring.

| harness | Ring 0 | Ring 1 | Ring 2 | containment | native fan-out | status |
| --- | --- | --- | --- | --- | --- | --- |
| claude_code | full | full | full | deferred * | partial | full |
| codex | full | deferred * | none | deferred * | none | partial |
| hermes | partial * | deferred * | deferred * | deferred * | deferred * | deferred * |
| opencode | deferred * | deferred * | deferred * | deferred * | deferred * | deferred * |
| copilot_cli | deferred * | deferred * | deferred * | deferred * | deferred * | deferred * |
| nanoclaw | none | none | none | none | full | none |
| discord | none | none | none | none | full | none |
| slack | none | none | none | none | full | none |

## Provenance

### claude_code
- **ring0** = `full` - validators/creator_engine_validator/claude_launch_spec.py: evaluate_claude_launch + build_governed_claude_command
- **ring1** = `full` - .claude/settings.json: PreToolUse hook-pack confirmed via validators/creator_engine_validator/hook_pack_confirm.py
- **ring2** = `full` - .claude/settings.json: Stop hook + validators/creator_engine_validator/hook_check.py: evaluate(HookContext)
- **containment** = `deferred` [unverified/deferred] - validators/creator_engine_validator/runner/herdr_containment.py: containment plan exists, but live launch still fails closed / is not wired
- **native_fanout** = `partial` - CE fan-out is provided by worker_spawn / lane launch rather than Claude Code native background agents, which Ring 0 refuses for governed seats
- **status** = `full` - rollup of verified Ring 0/1/2 support: 3/3

### codex
- **ring0** = `full` - validators/creator_engine_validator/codex_launch_spec.py: evaluate_codex_launch + build_governed_codex_command scrubs ambient repo credentials
- **ring1** = `deferred` [unverified/deferred] - validators/creator_engine_validator/hook_pack_confirm.py: confirm_codex_managed_hook_pack exists, but the matrix records Codex Ring 1 support as deferred pending containment acceptance
- **ring2** = `none` - validators/creator_engine_validator/codex_launch_spec.py: no Codex-owned Stop/closeout hook surface is wired
- **containment** = `deferred` [unverified/deferred] - validators/creator_engine_validator/runner/herdr_containment.py: containment plan exists, but live launch still fails closed / is not wired
- **native_fanout** = `none` - no Codex native governed fan-out wiring is present in CE
- **status** = `partial` - rollup of verified Ring 0/1/2 support: 1/3

### hermes
- **ring0** = `partial` [unverified/deferred] - validators/creator_engine_validator/hermes_launch_spec.py: Hermes launch evaluator/builder exists, but the matrix classifies Hermes governance extent as unverified until a harness audit promotes it
- **ring1** = `deferred` [unverified/deferred] - Hermes per-tool-call hook support is unverified
- **ring2** = `deferred` [unverified/deferred] - Hermes Stop/final-answer hook support is unverified
- **containment** = `deferred` [unverified/deferred] - validators/creator_engine_validator/runner/herdr_containment.py: containment plan exists, but live launch still fails closed / is not wired
- **native_fanout** = `deferred` [unverified/deferred] - Hermes native fan-out support is unverified
- **status** = `deferred` [unverified/deferred] - Hermes support is explicitly unverified in this matrix

### opencode
- **ring0** = `deferred` [unverified/deferred] - OpenCode launch envelope / cred-scrub support is unverified
- **ring1** = `deferred` [unverified/deferred] - OpenCode per-tool-call hook support is unverified
- **ring2** = `deferred` [unverified/deferred] - OpenCode Stop/closeout support is unverified
- **containment** = `deferred` [unverified/deferred] - OpenCode sandbox / PTY containment support is unverified
- **native_fanout** = `deferred` [unverified/deferred] - OpenCode native fan-out support is unverified
- **status** = `deferred` [unverified/deferred] - OpenCode support is unverified; no CE harness adapter wiring is probed

### copilot_cli
- **ring0** = `deferred` [unverified/deferred] - Copilot CLI launch envelope / cred-scrub support is unverified
- **ring1** = `deferred` [unverified/deferred] - Copilot CLI per-tool-call hook support is unverified
- **ring2** = `deferred` [unverified/deferred] - Copilot CLI Stop/closeout support is unverified
- **containment** = `deferred` [unverified/deferred] - Copilot CLI sandbox / PTY containment support is unverified
- **native_fanout** = `deferred` [unverified/deferred] - Copilot CLI native fan-out support is unverified
- **status** = `deferred` [unverified/deferred] - Copilot CLI support is unverified; no CE harness adapter wiring is probed

### nanoclaw
- **ring0** = `none` - nanoclaw is not an actor harness; no launch envelope applies
- **ring1** = `none` - nanoclaw is not an actor harness; no per-tool-call hook applies
- **ring2** = `none` - nanoclaw is not an actor harness; no Stop/closeout applies
- **containment** = `none` - nanoclaw is not an actor harness; no sandbox / PTY applies
- **native_fanout** = `full` - validators/creator_engine_validator/runner/notify_feed.py: first-class webhook sink covers nanoclaw emission
- **status** = `none` - nanoclaw is an emission-only non-actor surface; there is no Ring 1 actor to gate

### discord
- **ring0** = `none` - discord is not an actor harness; no launch envelope applies
- **ring1** = `none` - discord is not an actor harness; no per-tool-call hook applies
- **ring2** = `none` - discord is not an actor harness; no Stop/closeout applies
- **containment** = `none` - discord is not an actor harness; no sandbox / PTY applies
- **native_fanout** = `full` - validators/creator_engine_validator/runner/notify_feed.py: first-class webhook sink covers discord emission
- **status** = `none` - discord is an emission-only non-actor surface; there is no Ring 1 actor to gate

### slack
- **ring0** = `none` - slack is not an actor harness; no launch envelope applies
- **ring1** = `none` - slack is not an actor harness; no per-tool-call hook applies
- **ring2** = `none` - slack is not an actor harness; no Stop/closeout applies
- **containment** = `none` - slack is not an actor harness; no sandbox / PTY applies
- **native_fanout** = `full` - validators/creator_engine_validator/runner/notify_feed.py: first-class webhook sink covers slack emission
- **status** = `none` - slack is an emission-only non-actor surface; there is no Ring 1 actor to gate
