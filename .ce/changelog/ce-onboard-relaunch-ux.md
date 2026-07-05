# Onboard relaunch UX

- Declared work class: story.
- Added a safe relaunch path that archives stale launched seat surfaces only when the prior sentinel is verifiably dead and no tmux session is live.
- Kept ambiguous launched surfaces fail-closed with remediation pointing at `ce reap once`.
- Surfaced sentinel tail-event details, including exit code and command, when onboarding launch dies before the single-controller assertion can pass.
- Added a `ce doctor --require-visible-launch --harness ...` PATH precheck for the configured harness binary.
- Regenerated the committed CLI reference for the new `ce doctor --harness` option.
- Added unit coverage for stale archive-and-proceed, ambiguous liveness refusal, exit-127 diagnosis, and doctor harness check pass/fail.
