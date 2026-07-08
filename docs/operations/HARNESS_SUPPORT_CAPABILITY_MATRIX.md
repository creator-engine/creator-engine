# CE harness-support capability matrix

This is the authoritative CE harness-support and promotion matrix. It is rendered from `creator_engine_validator.harness_matrix`; `yellow *` marks deferred or design-stage support, and `red` marks an absent or refused promotion requirement.

A row is gate-capable only when `code-support`, `launch-wired`, `live-proven`, and `promotion-approved` are all `green`, or when the row records an explicit Operator-ratified exception with date and ratification reference.

| provider | ring | code-support | launch-wired | live-proven | promotion-approved | gate-capable | exception |
| --- | --- | --- | --- | --- | --- | --- | --- |
| claude_code | Ring 0 | green | green | green | green | yes | none |
| claude_code | Ring 1 | green | green | green | green | yes | none |
| claude_code | Ring 2 | green | green | green | green | yes | none |
| codex | Ring 0 | green | green | green | green | yes | none |
| codex | Ring 1 | green | green | red | red | no | none |
| codex | Ring 2 | red | red | red | red | no | none |
| codex | containment | green | yellow * | red | red | no | none |
| lane_worker | Ring 0 | green | green | green | green | yes | none |
| lane_worker | Ring 1 | green | green | green | green | yes | none |
| lane_worker | Ring 2 | green | green | green | green | yes | none |
| contained_controller_scaffold | C1 static/dry-run | green | yellow * | red | red | no | none |
| contained_controller_scaffold | C2 | yellow * | red | red | red | no | none |
| contained_controller_scaffold | C3 | yellow * | red | red | red | no | none |
| contained_controller_scaffold | C4 | yellow * | red | red | red | no | none |
| ephemeral_controller_providers | design-stage | yellow * | red | red | red | no | none |

## Provenance

### claude_code - Ring 0
- **code-support** = `green` - validators/creator_engine_validator/claude_launch_spec.py: evaluate_claude_launch + build_governed_claude_command
- **launch-wired** = `green` - validators/creator_engine_validator/claude_launch_spec.py: governed Claude command builder is wired before harness start
- **live-proven** = `green` - validators/creator_engine_validator/claude_launch_spec.py: launch envelope evaluator is covered by committed probes
- **promotion-approved** = `green` - Claude Ring 0 is full per existing matrix
- **gate-capable** = `yes` - all four promotion cells are green
- **exception** = `none` - no Operator-ratified exception recorded

### claude_code - Ring 1
- **code-support** = `green` - validators/creator_engine_validator/hook_pack_confirm.py: confirm_hook_pack
- **launch-wired** = `green` - .claude/settings.json: PreToolUse hook registered
- **live-proven** = `green` - validators/creator_engine_validator/hook_pack_confirm.py: validator-reachable PreToolUse confirmation
- **promotion-approved** = `green` - Claude Ring 1 is full per existing matrix
- **gate-capable** = `yes` - all four promotion cells are green
- **exception** = `none` - no Operator-ratified exception recorded

### claude_code - Ring 2
- **code-support** = `green` - validators/creator_engine_validator/hook_check.py: evaluate(HookContext)
- **launch-wired** = `green` - .claude/settings.json: Stop hook registered
- **live-proven** = `green` - validators/creator_engine_validator/hook_pack_confirm.py: Stop hook confirmation
- **promotion-approved** = `green` - Claude Ring 2 is full per existing matrix
- **gate-capable** = `yes` - all four promotion cells are green
- **exception** = `none` - no Operator-ratified exception recorded

### codex - Ring 0
- **code-support** = `green` - validators/creator_engine_validator/codex_launch_spec.py: evaluate_codex_launch + build_governed_codex_command scrubs ambient repo credentials
- **launch-wired** = `green` - validators/creator_engine_validator/codex_launch_spec.py: governed Codex command builder is wired before harness start
- **live-proven** = `green` - validators/creator_engine_validator/codex_launch_spec.py: Ring 0 evaluator is committed and probed
- **promotion-approved** = `green` - Codex Ring 0 is full per known state
- **gate-capable** = `yes` - all four promotion cells are green
- **exception** = `none` - no Operator-ratified exception recorded

### codex - Ring 1
- **code-support** = `green` - validators/creator_engine_validator/hook_pack_confirm.py: confirm_codex_managed_hook_pack exists
- **launch-wired** = `green` - Operator-authorized pre-act (decision 4, Operator decisions 2026-07-08); containment accepted per C5 promotion (decision 3, same ledger); promotion evidence packet still pending = ticket 480
- **live-proven** = `red` - not live-proven until the ticket 480 evidence packet and Ring 1 smoke are accepted
- **promotion-approved** = `red` - promotion deferred pending containment acceptance and ticket 480
- **gate-capable** = `no` - one or more promotion cells are not green
- **exception** = `none` - no Operator-ratified exception recorded

### codex - Ring 2
- **code-support** = `red` - validators/creator_engine_validator/codex_launch_spec.py: no Codex-owned Stop/closeout hook surface is wired
- **launch-wired** = `red` - no Codex Ring 2 closeout launch wiring
- **live-proven** = `red` - no Codex Ring 2 live proof
- **promotion-approved** = `red` - Codex Ring 2 promotion is not approved
- **gate-capable** = `no` - one or more promotion cells are not green
- **exception** = `none` - no Operator-ratified exception recorded

### codex - containment
- **code-support** = `green` - validators/creator_engine_validator/runner/herdr_containment.py: plan_herdr_containment exists
- **launch-wired** = `yellow` [deferred/design-stage] - containment deferred; live launch still fails closed / is not wired
- **live-proven** = `red` - Codex containment is not live-proven
- **promotion-approved** = `red` - Codex containment promotion is deferred
- **gate-capable** = `no` - one or more promotion cells are not green
- **exception** = `none` - no Operator-ratified exception recorded

### lane_worker - Ring 0
- **code-support** = `green` - validators/creator_engine_validator/lane_runtime.py: launch() runs governed lane Ring 0 refusal before side effects
- **launch-wired** = `green` - validators/creator_engine_validator/lane_runtime.py: governed worker lane launch is wired
- **live-proven** = `green` - validators/creator_engine_validator/lane_runtime.py: worker-lane Ring 0 path is committed and probed
- **promotion-approved** = `green` - lane is approved as worker fan-out, not live controller authority
- **gate-capable** = `yes` - all four promotion cells are green
- **exception** = `none` - no Operator-ratified exception recorded

### lane_worker - Ring 1
- **code-support** = `green` - .claude/settings.json: committed PreToolUse hook-pack
- **launch-wired** = `green` - validators/creator_engine_validator/lane_runtime.py: launch() exports CE_LEDGER_ROOT into the pane env
- **live-proven** = `green` - validators/creator_engine_validator/lane_runtime.py: wrapped harness resolves posture from the real seat claim
- **promotion-approved** = `green` - lane is approved as worker fan-out, not live controller authority
- **gate-capable** = `yes` - all four promotion cells are green
- **exception** = `none` - no Operator-ratified exception recorded

### lane_worker - Ring 2
- **code-support** = `green` - validators/creator_engine_validator/lane_runtime.py: verify() + verify_closeout provide lane closeout checks
- **launch-wired** = `green` - validators/creator_engine_validator/lane_runtime.py: closeout verification is wired for worker lanes
- **live-proven** = `green` - validators/creator_engine_validator/lane_runtime.py: worker-lane closeout checks are committed and probed
- **promotion-approved** = `green` - lane is approved as worker fan-out, not live controller authority
- **gate-capable** = `yes` - all four promotion cells are green
- **exception** = `none` - no Operator-ratified exception recorded

### contained_controller_scaffold - C1 static/dry-run
- **code-support** = `green` - contained-controller scaffold exists only as static/dry-run support
- **launch-wired** = `yellow` [deferred/design-stage] - dry-run scaffold only; no live controller promotion wiring
- **live-proven** = `red` - contained controller scaffold is not live-proven
- **promotion-approved** = `red` - contained controller scaffold is not promotion-approved
- **gate-capable** = `no` - one or more promotion cells are not green
- **exception** = `none` - no Operator-ratified exception recorded

### contained_controller_scaffold - C2
- **code-support** = `yellow` [deferred/design-stage] - C2 scaffold is unproven beyond static/dry-run design
- **launch-wired** = `red` - C2 launch wiring is unproven
- **live-proven** = `red` - C2 is not live-proven
- **promotion-approved** = `red` - C2 promotion is not approved
- **gate-capable** = `no` - one or more promotion cells are not green
- **exception** = `none` - no Operator-ratified exception recorded

### contained_controller_scaffold - C3
- **code-support** = `yellow` [deferred/design-stage] - C3 scaffold is unproven beyond static/dry-run design
- **launch-wired** = `red` - C3 launch wiring is unproven
- **live-proven** = `red` - C3 is not live-proven
- **promotion-approved** = `red` - C3 promotion is not approved
- **gate-capable** = `no` - one or more promotion cells are not green
- **exception** = `none` - no Operator-ratified exception recorded

### contained_controller_scaffold - C4
- **code-support** = `yellow` [deferred/design-stage] - C4 scaffold is unproven beyond static/dry-run design
- **launch-wired** = `red` - C4 launch wiring is unproven
- **live-proven** = `red` - C4 is not live-proven
- **promotion-approved** = `red` - C4 promotion is not approved
- **gate-capable** = `no` - one or more promotion cells are not green
- **exception** = `none` - no Operator-ratified exception recorded

### ephemeral_controller_providers - design-stage
- **code-support** = `yellow` [deferred/design-stage] - ephemeral-controller providers are design-stage only
- **launch-wired** = `red` - ephemeral-controller provider launch wiring is not present
- **live-proven** = `red` - ephemeral-controller providers are not live-proven
- **promotion-approved** = `red` - ephemeral-controller provider promotion is not approved
- **gate-capable** = `no` - one or more promotion cells are not green
- **exception** = `none` - no Operator-ratified exception recorded
